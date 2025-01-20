# Foodgram - Продуктовый помощник

## Описание проекта

Foodgram - это сервис, который позволяет пользователям делиться рецептами, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в избранное и создавать список покупок для удобного планирования похода в магазин.

## Технологии

- Python
- Django
- Django REST Framework
- Djoser
- Docker
- Nginx
- Gunicorn
- PostgreSQL

## Функционал

- **Главная страница**: Отображение списка рецептов, отсортированных по дате публикации, начиная с самых новых.
  
- **Страница рецепта**: Полное описание блюда, возможность добавить его в избранное или в список покупок. Также есть возможность подписаться на автора рецепта.
  
- **Подписка на авторов**: Возможность подписываться на публикации авторов, чтобы получать уведомления о новых рецептах.
  
- **Список избранного**: Создание и управление списком избранных рецептов.
  
- **Список покупок**: Создание списка покупок на основе выбранных рецептов, который можно скачать в формате PDF.
  
- **Фильтрация по тегам**: Фильтрация рецептов по тегам для быстрого поиска интересующих блюд.

## Запуск проекта

Перед запуском убедитесь, что у вас установлены Docker и Docker-Compose.

1. Склонируйте репозиторий.
2. В директории проекта создайте файл `.env` на основе `example.env` и заполните необходимые переменные.
3. Выполните следующие команды для запуска контейнеров:
   ```
   docker-compose -f docker-compose.yml up --build -d
   ```
4. Примените миграцию базы данных:
   ```
   docker-compose -f docker-compose.production.yml exec backend python manage.py makemigrations
   docker-compose -f docker-compose.production.yml exec backend python manage.py migrate
   docker-compose -f docker-compose.production.yml exec backend python manage.py load_csv
   ```
5. Соберите статику:
   ```
   docker-compose -f docker-compose.production.yml exec backend python manage.py collectstatic
   docker-compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
   ```
6. Создайте суперпользователя, введите почту, логин и пароль:
   ```
   docker-compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
   ```

