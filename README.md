клонируйте репозиторий:
```
git clone https://github.com/SubMonitor/api.git
cd api
```

создайте .env с:
```
SECRET_KEY = <укажите ключ для jwt>
BACKEND_CORS_ORIGINS = ["*"]
```

и соберите:
```
docker-compose up -d --build
```

документация API http://localhost:8000/docs
