from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Создаем URL подключения к базе данных
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

print(f"DEBUG: Подключаемся к БД: {SQLALCHEMY_DATABASE_URL}")

# Создаем движок SQLAlchemy с параметрами для MySQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Проверяем соединения перед использованием
    pool_recycle=300,    # Переиспользуем соединения каждые 5 минут
    pool_timeout=30,     # Таймаут ожидания соединения из пула
    connect_args={
        "connect_timeout": 10,  # Таймаут подключения к MySQL
        "read_timeout": 60,     # Увеличиваем таймаут чтения до 60 сек
        "write_timeout": 60,    # Увеличиваем таймаут записи до 60 сек
        "autocommit": True,     # Автокоммит для избежания блокировок
    }
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 