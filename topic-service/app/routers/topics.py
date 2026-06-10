from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ..database import get_db
from ..models import Topic, Application, ApplicationStatus
from ..schemas import (
    TopicCreate,
    TopicResponse,
    ApplicationCreate,
    ApplicationResponse,
    TeacherApplicationResponse,
)
from shared.jwt_utils import get_current_user, get_optional_current_user
import logging
import os
import random
import string

import hashlib
from io import BytesIO
from fastapi.responses import StreamingResponse
from docx import Document

logger = logging.getLogger(__name__)
SEND_EMAIL_CODES = os.getenv("SEND_EMAIL_CODES", "false").lower() == "true"

router = APIRouter(prefix="/api/topic", tags=["topics"])

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

@router.post("/teachers/me/topics", response_model=TopicResponse)
def create_topic(
    topic_data: TopicCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Только преподаватель может создавать темы")
    new_topic = Topic(
        title=topic_data.title,
        description=topic_data.description,
        teacher_id=current_user.get("id")
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)
    return new_topic

@router.get("/topics", response_model=list[TopicResponse])
def list_topics(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_current_user),
):
    topics = db.query(Topic).filter(Topic.status == "active").all()
    taken_topic_ids = {
        row[0]
        for row in db.query(Application.topic_id)
        .filter(Application.status != ApplicationStatus.REJECTED)
        .distinct()
        .all()
    }
    my_apps_by_topic: dict[str, Application] = {}
    if current_user and current_user.get("role") == "student":
        student_id = str(current_user.get("id"))
        for app in db.query(Application).filter(Application.student_id == student_id).all():
            my_apps_by_topic[app.topic_id] = app

    result: list[TopicResponse] = []
    for topic in topics:
        payload = TopicResponse.model_validate(topic)
        payload.is_taken = topic.id in taken_topic_ids
        my_app = my_apps_by_topic.get(topic.id)
        if my_app:
            payload.my_application_status = (
                my_app.status.value if hasattr(my_app.status, "value") else str(my_app.status)
            )
            payload.my_application_id = my_app.id
        result.append(payload)
    return result

@router.get("/topics/{topic_id}", response_model=TopicResponse)
def get_topic(topic_id: str, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return topic

@router.post("/applications", response_model=ApplicationResponse)
def create_application(
    app_data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Только студент может подавать заявку")
    topic = db.query(Topic).filter(Topic.id == app_data.topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    existing = db.query(Application).filter(
        Application.topic_id == app_data.topic_id,
        Application.status != ApplicationStatus.REJECTED
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="На эту тему уже подана заявка")
    student_code = generate_code()
    teacher_code = generate_code()
    new_app = Application(
        student_id=current_user.get("id"),
        topic_id=app_data.topic_id,
        student_code=student_code,
        teacher_code=teacher_code
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    if SEND_EMAIL_CODES:
        from ..utils.email_notify import get_user_email, notify_application_codes

        student_email = current_user.get("email") or get_user_email(db, str(current_user.get("id")))
        teacher_email = get_user_email(db, topic.teacher_id)
        notify_application_codes(
            topic_title=topic.title,
            student_email=student_email,
            teacher_email=teacher_email,
            student_code=student_code,
            teacher_code=teacher_code,
        )

    return new_app

@router.get("/teachers/me/applications", response_model=list[TeacherApplicationResponse])
def list_teacher_applications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Только преподаватель")
    teacher_id = str(current_user.get("id"))
    rows = (
        db.query(Application, Topic)
        .join(Topic, Application.topic_id == Topic.id)
        .filter(Topic.teacher_id == teacher_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return [
        TeacherApplicationResponse(
            id=app.id,
            topic_id=app.topic_id,
            topic_title=topic.title,
            student_id=app.student_id,
            status=app.status.value if hasattr(app.status, "value") else str(app.status),
            teacher_code=app.teacher_code,
        )
        for app, topic in rows
    ]


@router.post("/confirm")
def confirm_code(
    application_id: str,
    code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    role = current_user.get("role")
    if role == "student":
        if app.student_code != code:
            raise HTTPException(status_code=400, detail="Неверный код")
        app.status = ApplicationStatus.STUDENT_CONFIRMED
        app.student_confirmed_at = func.now()
    elif role == "teacher":
        if app.teacher_code != code:
            raise HTTPException(status_code=400, detail="Неверный код")
        app.teacher_confirmed_at = func.now()
        if app.status == ApplicationStatus.STUDENT_CONFIRMED:
            app.status = ApplicationStatus.APPROVED
        else:
            app.status = ApplicationStatus.TEACHER_CONFIRMED
    else:
        raise HTTPException(status_code=403, detail="Нет прав")
    db.commit()
    return {"message": "Код подтверждён", "status": app.status.value}

@router.get("/applications/{application_id}/document")
def download_application_document(
    application_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == application_id).first()

    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if app.status != ApplicationStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Документ доступен только после утверждения заявки")

    topic = db.query(Topic).filter(Topic.id == app.topic_id).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    user_id = str(current_user.get("id"))
    role = current_user.get("role")

    is_student = role == "student" and app.student_id == user_id
    is_teacher = role == "teacher" and topic.teacher_id == user_id

    if not (is_student or is_teacher):
        raise HTTPException(status_code=403, detail="Нет доступа к документу")

    student_hash = hashlib.sha256(app.student_code.encode()).hexdigest()
    teacher_hash = hashlib.sha256(app.teacher_code.encode()).hexdigest()

    document = Document()

    document.add_heading("Заявление на утверждение темы ВКР", level=1)

    document.add_paragraph(f"ID заявки: {app.id}")
    document.add_paragraph(f"ID студента: {app.student_id}")
    document.add_paragraph(f"ID преподавателя: {topic.teacher_id}")
    document.add_paragraph(f"Тема ВКР: {topic.title}")

    if topic.description:
        document.add_paragraph(f"Описание темы: {topic.description}")

    document.add_paragraph(f"Дата подтверждения студентом: {app.student_confirmed_at}")
    document.add_paragraph(f"Дата подтверждения преподавателем: {app.teacher_confirmed_at}")

    document.add_heading("Электронные подписи", level=2)
    document.add_paragraph(f"Подпись студента: SHA256({app.student_code}) = {student_hash}")
    document.add_paragraph(f"Подпись преподавателя: SHA256({app.teacher_code}) = {teacher_hash}")

    file_stream = BytesIO()
    document.save(file_stream)
    file_stream.seek(0)

    filename = f"application_{app.id}.docx"

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )