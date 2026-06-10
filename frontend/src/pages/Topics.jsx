import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import Table from 'react-bootstrap/Table';
import Badge from 'react-bootstrap/Badge';
import api from '../api/client';

const applicationStatusLabels = {
  created: { text: 'Введите код подтверждения', variant: 'warning' },
  student_confirmed: { text: 'Ожидает преподавателя', variant: 'info' },
  teacher_confirmed: { text: 'Преподаватель подтвердил', variant: 'primary' },
  approved: { text: 'Утверждена', variant: 'success' },
  rejected: { text: 'Отклонена', variant: 'danger' },
};

function Topics() {
  const role = localStorage.getItem('role');
  const navigate = useNavigate();
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [applyingId, setApplyingId] = useState(null);

  const loadTopics = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/topic/api/topic/topics');
      if (Array.isArray(data)) {
        setTopics(data);
      } else {
        setError('Неверный формат данных');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки тем');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, []);

  const hasActiveApplication = topics.some(
    (topic) =>
      topic.my_application_status &&
      topic.my_application_status !== 'rejected'
  );

  const handleApply = async (topic) => {
    setApplyingId(topic.id);
    setError('');
    try {
      const { data } = await api.post('/topic/api/topic/applications', {
        topic_id: topic.id,
      });
      const params = new URLSearchParams({
        application_id: data.id,
        topic: topic.title,
      });
      if (data.student_code) {
        params.set('code', data.student_code);
      }
      navigate(`/confirm-application?${params.toString()}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось выбрать тему');
    } finally {
      setApplyingId(null);
    }
  };

  const renderStudentStatus = (topic) => {
    if (topic.my_application_status) {
      const cfg = applicationStatusLabels[topic.my_application_status] || {
        text: topic.my_application_status,
        variant: 'secondary',
      };
      return <Badge bg={cfg.variant}>{cfg.text}</Badge>;
    }
    if (topic.is_taken) {
      return <Badge bg="secondary">Занята</Badge>;
    }
    return <Badge bg="success">Свободна</Badge>;
  };

  const renderStudentAction = (topic) => {
    if (topic.my_application_status === 'approved') {
      return (
        <Button
          size="sm"
          variant="success"
          onClick={() => downloadDocument(topic.my_application_id)}
        >
          Скачать заявление
        </Button>
      );
    }
    if (topic.my_application_status === 'created' && topic.my_application_id) {
      return (
        <Button
          as={Link}
          to={`/confirm-application?application_id=${topic.my_application_id}&topic=${encodeURIComponent(topic.title)}`}
          size="sm"
          variant="warning"
        >
          Ввести код
        </Button>
      );
    }
    if (topic.my_application_status === 'student_confirmed') {
      return <span className="text-muted">Ждём преподавателя</span>;
    }
    if (topic.is_taken) {
      return <span className="text-muted">—</span>;
    }
    if (hasActiveApplication) {
      return <span className="text-muted">Недоступно</span>;
    }
    return (
      <Button
        size="sm"
        variant="primary"
        disabled={applyingId === topic.id}
        onClick={() => handleApply(topic)}
      >
        {applyingId === topic.id ? 'Отправка...' : 'Выбрать'}
      </Button>
    );
  };

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
      <h2>Темы ВКР</h2>
      {error && <Alert variant="danger">{error}</Alert>}

      {topics.length === 0 && role === 'teacher' && (
        <Alert variant="info">
          Вы ещё не добавили ни одной темы.{' '}
          <Button as={Link} to="/add-topic" variant="primary" size="sm">
            Добавить тему
          </Button>
        </Alert>
      )}
      {topics.length === 0 && role !== 'teacher' && <p>Нет доступных тем</p>}

      {topics.length > 0 && (
        <Table striped bordered hover>
          <thead>
            <tr>
              <th>Тема</th>
              <th>Статус</th>
              {role === 'student' && <th>Действие</th>}
            </tr>
          </thead>
          <tbody>
            {topics.map((topic) => (
              <tr key={topic.id}>
                <td>
                  <strong>{topic.title}</strong>
                  {topic.description && (
                    <div className="text-muted small">{topic.description}</div>
                  )}
                </td>
                <td>
                  {role === 'student' ? (
                    renderStudentStatus(topic)
                  ) : topic.is_taken ? (
                    <Badge bg="secondary">Занята</Badge>
                  ) : (
                    <Badge bg="success">Свободна</Badge>
                  )}
                </td>
                {role === 'student' && <td>{renderStudentAction(topic)}</td>}
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {role === 'student' && topics.length > 0 && (
        <Alert variant="light" className="mt-3">
          После «Выбрать» введите код. Когда статус «Утверждена» — тема закреплена за вами.
        </Alert>
      )}
    </div>
  );
}

export default Topics;
