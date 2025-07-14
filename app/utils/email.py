from typing import Optional
import logging
from config import settings

logger = logging.getLogger(__name__)

async def send_email(
    email_to: str,
    subject: str, 
    body: str,
    template_name: Optional[str] = None,
):
    """
    Заглушка для функционала отправки email.
    В рабочей среде здесь была бы настоящая отправка писем.
    """
    logger.info(f"Будет отправлено письмо на {email_to}")
    logger.info(f"Тема: {subject}")
    logger.info(f"Содержание: {body}")
    if template_name:
        logger.info(f"Используя шаблон: {template_name}")
    
    # В реальной реализации здесь было бы подключение к SMTP серверу
    
    return True


async def send_reset_password_email(
    email_to: str, 
    email: str, 
    token: str
):
    """
    Отправляет письмо для сброса пароля со ссылкой с токеном.
    В данный момент просто логирует попытку.
    """
    project_name = settings.PROJECT_NAME
    reset_link = f"#/reset-password?token={token}"
    
    body = f"""
    <html>
    <body>
    <p>Здравствуйте!</p>
    <p>Вы запросили сброс пароля для Вашего аккаунта на сайте {project_name}.</p>
    <p>Для сброса пароля, перейдите по ссылке: <a href="{reset_link}">Сбросить пароль</a></p>
    <p>Если Вы не запрашивали сброс пароля, проигнорируйте это сообщение.</p>
    <p>С уважением,<br>Команда {project_name}</p>
    </body>
    </html>
    """
    
    logger.info(f"Письмо для сброса пароля будет отправлено на {email_to}")
    logger.info(f"Токен: {token}")
    
    return await send_email(
        email_to=email_to,
        subject=f"{project_name} - Сброс пароля",
        body=body,
    ) 