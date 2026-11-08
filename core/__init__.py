"""Core module for Brazilian Government Open Data Skills."""

from .config import settings
from .db import get_db, DatabaseManager
from .normalizers import normalize_cnpj, normalize_cpf, normalize_ibge, parse_currency

__all__ = [
    "settings",
    "get_db",
    "DatabaseManager",
    "normalize_cnpj",
    "normalize_cpf",
    "normalize_ibge",
    "parse_currency",
]
