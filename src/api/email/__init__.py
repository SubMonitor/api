from src.api.email.router import api_email_router
from src.api.email.endpoints import disconnect_email, get_email_detail, get_email_servers, connect_email, search_emails, get_email_accounts, get_folders

__all__ = ["api_email_router"]