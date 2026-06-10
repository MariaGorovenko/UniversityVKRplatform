import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from 'react-bootstrap/Alert';
import Badge from 'react-bootstrap/Badge';
import Button from 'react-bootstrap/Button';
import Table from 'react-bootstrap/Table';
import api from '../api/client';

const statusLabel = {
  created: 'Создана',
  student_confirmed: 'Студент подтвердил',
  teacher_confirmed: 'Преподаватель подтвердил',
  approved: 'Утверждена',
  rejected: 'Отклонена',
};

function TeacherApplications() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get('/topic/api/topic/teachers/me/applications');
        setApps(data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Не удалось загрузить заявки');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const downloadDocument = async (applicationId) => {
  try {
    const response = await api.get(
      `/topic/api/topic/applications/${applicationId}/document`,
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'application.docx');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    setError(err.response?.data?.detail || 'Не удалось скачать заявление');
  }
};

  if (loading) return <div>Загрузка...</div>;

  return (
    <div>
      <h2>Заявки на мои темы</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      {apps.length === 0 && <Alert variant="info">Пока нет заявок от студентов.</Alert>}
      {apps.length > 0 && (
        <Table striped bordered hover>
          <thead>
            <tr>
              <th>Тема</th>
              <th>Студент</th>
              <th>Статус</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((app) => (
              <tr key={app.id}>
                <td>{app.topic_title}</td>
                <td>{app.student_name || app.student_id}</td>
                <td>
                  <Badge bg={app.status === 'approved' ? 'success' : 'warning'}>
                    {statusLabel[app.status] || app.status}
                  </Badge>
                </td>
                <td>
                  {app.status === 'student_confirmed' ? (
                    <Button
                      as={Link}
                      to={`/confirm-application?application_id=${app.id}&code=${app.teacher_code}&topic=${encodeURIComponent(app.topic_title)}`}
                      size="sm"
                      variant="primary"
                    >
                      Подтвердить кодом
                    </Button>
                  ) : app.status === 'approved' ? (
                    <Button
                      size="sm"
                      variant="success"
                      onClick={() => downloadDocument(app.id)}
                    >
                      Скачать заявление
                    </Button>
                  ) : (
                    'Ожидает студента'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

export default TeacherApplications;
