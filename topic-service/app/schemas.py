from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TopicCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TopicResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    teacher_id: str
    status: str
    created_at: datetime
    teacher_name: Optional[str] = None
    is_taken: bool = False
    my_application_status: Optional[str] = None
    my_application_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicationCreate(BaseModel):
    topic_id: str

class ApplicationResponse(BaseModel):
    id: str
    student_id: str
    topic_id: str
    status: str
    student_code: Optional[str] = None
    teacher_code: Optional[str] = None


class TeacherApplicationResponse(BaseModel):
    id: str
    topic_id: str
    topic_title: str
    student_id: str
    student_name: Optional[str] = None
    status: str
    teacher_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)