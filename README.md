# Hotel Booking API

REST API для бронирования комнат в отеле. Стек: Django, DRF, PostgreSQL.

---

## Запуск через Docker

```bash
docker-compose up --build
```

После запуска:
- Swagger-документация: http://localhost:8000/api/docs/
- Админ-панель: http://localhost:8000/admin/

Создать суперпользователя:

```bash
docker-compose exec web python manage.py createsuperuser
```

---

## Запуск локально

**Требования:** Python 3.12+, PostgreSQL

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Создать БД в PostgreSQL и настроить `hotel_booking/settings.py` (секция `DATABASES`).

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---


## Линтер и форматирование

```bash
flake8 .
black .
```

---

## API Endpoints

### Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register/` | Регистрация |
| POST | `/api/auth/login/` | Получить JWT токены |
| POST | `/api/auth/refresh/` | Обновить access-токен |
| GET | `/api/auth/profile/` | Текущий пользователь |

### Комнаты (доступны без авторизации)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/rooms/` | Список комнат с фильтрацией и сортировкой |
| GET | `/api/rooms/{id}/` | Детали комнаты |

**Query-параметры для `/api/rooms/`:**

| Параметр | Описание |
|----------|----------|
| `check_in` | Дата заезда (YYYY-MM-DD) — фильтр свободных комнат |
| `check_out` | Дата выезда (YYYY-MM-DD) |
| `min_price` | Минимальная цена за сутки |
| `max_price` | Максимальная цена за сутки |
| `capacity` | Количество мест (точное) |
| `min_capacity` | Минимальное количество мест |
| `ordering` | Сортировка: `price_per_day`, `-price_per_day`, `capacity`, `-capacity` |

### Брони (требуется авторизация)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/bookings/` | Список своих броней |
| POST | `/api/bookings/` | Создать бронь |
| GET | `/api/bookings/{id}/` | Детали брони |
| DELETE | `/api/bookings/{id}/` | Отменить бронь |

**Тело запроса для создания брони:**
```json
{
  "room": 1,
  "check_in": "2025-08-01",
  "check_out": "2025-08-05"
}
```

**Authorization header:**
```
Authorization: Bearer <access_token>
```

---

## Административная панель

Суперпользователь может через `/admin/`:
- Добавлять / редактировать / удалять комнаты
- Просматривать и редактировать все брони (включая отмену)
