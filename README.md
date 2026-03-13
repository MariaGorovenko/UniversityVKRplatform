# University VKR Platform

Микросервисная платформа для выбора тем ВКР (выпускных квалификационных работ).

## Текущий статус (март 2026)

- Бэкенд (auth + topic) работает
- Nginx проксирует запросы на /auth/ и /topic/
- PostgreSQL + Alembic настроены
- Общая библиотека shared/jwt_utils подключена
- Запуск одной командой

## Запуск локально

1. Клонируйте репозиторий к себе на локальный компьютер

2. Перейдите в папку infra и скопируйте шаблон .env
    ```bash
    cd infra
    cp .env.example .env

    # Откройте .env и заполните:
    # POSTGRES_PASSWORD — любой сильный пароль
    # JWT_SECRET — сгенерируйте случайный ключ (например: openssl rand -base64 48)
   
3. Запустите проект
    ```bash
    docker compose up -d --build
   
4. Проверьте, что всё поднялось
    ```bash
    docker compose ps
    # Все сервисы должны быть в статусе Up.

5. Проверка работоспособности
    ```bash
    curl http://localhost/auth/health
    curl http://localhost/topic/health
   
    # Ожидаемый результат:
    # {"status":"ok","service":"auth"}
    # {"status":"ok","service":"topic"}

6. Проверка БД:
    ```bash
    docker compose exec postgres psql -U postgres -d vkr_main -c "\dt"
    # Должна быть хотя бы таблица alembic_version.

## Полезные команды

1. Alembic (миграции БД):
    ```bash
    # Посмотреть текущую ревизию
    docker compose exec auth-service alembic -c /app/alembic.ini current
   
    # Применить миграции
    docker compose exec auth-service alembic -c /app/alembic.ini upgrade head
   
2. Логи сервисов:
    ```bash
    docker compose logs -f auth-service
    docker compose logs -f nginx
   
3. Перезапуск одного сервиса:
    ```bash
    docker compose restart auth-service
   
4. Остановка и очистка:
    ```bash
    docker compose down
    
    # Если нужно очистить БД полностью:
    docker compose down --volumes
   
## Структура проекта

- infra/ — docker-compose.yml, nginx, .env, .env.example
- auth-service/ — аутентификация, пользователи, alembic
- topic-service/ — темы, заявки
- shared/ — общие утилиты (jwt_utils.py и т.д.)
- frontend/ — фронтенд (пока пустой или в разработке)