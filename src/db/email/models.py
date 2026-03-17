from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from src.db import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Данные подключения
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # пароль приложения (не шифруем пока)
    server_key: Mapped[str] = mapped_column(String(50), nullable=False)  # yandex, mailru, gmail, custom
    custom_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_port: Mapped[int] = mapped_column(Integer, default=993)

    # Статус подключения
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="email_accounts")

    def __repr__(self) -> str:
        return f"<EmailAccount(id={self.id}, email='{self.email}', user_id={self.user_id})>"