"""Data normalizers and validators for Brazilian government entities."""

import re
import unicodedata
from datetime import datetime
from typing import Optional, Tuple


def normalize_cnpj(cnpj_raw: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Cleans and standardizes a Brazilian CNPJ (Cadastro Nacional da Pessoa Jurídica).
    
    Returns:
        tuple of (cnpj_clean_14, cnpj_formatted, cnpj_raiz_8)
        e.g. ("00000000000191", "00.000.000/0001-91", "00000000")
    """
    if not cnpj_raw:
        return None, None, None

    # Remove non-numeric characters
    cleaned = re.sub(r"\D", "", str(cnpj_raw).strip())

    if not cleaned:
        return None, None, None

    # Pad with leading zeros up to 14 digits if numeric length < 14
    cleaned = cleaned.zfill(14)

    if len(cleaned) != 14:
        return cleaned, cleaned, cleaned[:8] if len(cleaned) >= 8 else None

    formatted = f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}/{cleaned[8:12]}-{cleaned[12:]}"
    cnpj_raiz = cleaned[:8]

    return cleaned, formatted, cnpj_raiz


def normalize_cpf(cpf_raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Cleans and standardizes a Brazilian CPF (Cadastro de Pessoas Físicas).
    Handles masked CPFs (e.g., ***.123.456-** or ***123456**).
    
    Returns:
        tuple of (cpf_clean, cpf_formatted_or_raw)
    """
    if not cpf_raw:
        return None, None

    raw_str = str(cpf_raw).strip()
    is_masked = "*" in raw_str

    if is_masked:
        # Keep asterisks for masked CPFs commonly used in public transparency data
        return raw_str, raw_str

    cleaned = re.sub(r"\D", "", raw_str)
    if not cleaned:
        return None, None

    cleaned = cleaned.zfill(11)
    if len(cleaned) != 11:
        return cleaned, raw_str

    formatted = f"{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}"
    return cleaned, formatted


def normalize_ibge(ibge_code: Optional[str | int]) -> Optional[str]:
    """
    Normalizes IBGE Municipality code.
    IBGE codes can be 6 digits (without verification digit) or 7 digits (with DV).
    Standardizes to string format.
    """
    if not ibge_code:
        return None

    cleaned = re.sub(r"\D", "", str(ibge_code).strip())
    if not cleaned:
        return None

    if len(cleaned) in (6, 7):
        return cleaned
    return cleaned


def parse_currency(value_raw: Optional[str | float | int]) -> float:
    """
    Parses Brazilian currency format (e.g., 'R$ 1.250.450,85' or '1250450.85') to float.
    """
    if value_raw is None:
        return 0.0

    if isinstance(value_raw, (int, float)):
        return float(value_raw)

    val = str(value_raw).strip()
    # Remove R$, spaces, quotes
    val = re.sub(r"[R$\s]", "", val)

    if not val:
        return 0.0

    # Brazilian format: 1.234.567,89 -> 1234567.89
    if "," in val and "." in val:
        val = val.replace(".", "").replace(",", ".")
    elif "," in val and "." not in val:
        val = val.replace(",", ".")

    try:
        return float(val)
    except ValueError:
        return 0.0


def parse_date(date_raw: Optional[str]) -> Optional[str]:
    """
    Normalizes dates to ISO-8601 YYYY-MM-DD.
    Accepts:
    - DD/MM/YYYY
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    """
    if not date_raw:
        return None

    val = str(date_raw).strip()

    # Try ISO
    try:
        if "T" in val:
            val = val.split("T")[0]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
            return val
    except Exception:
        pass

    # Try Brazilian DD/MM/YYYY
    match_br = re.match(r"^(\d{2})/(\d{2})/(\d{4})", val)
    if match_br:
        day, month, year = match_br.groups()
        return f"{year}-{month}-{day}"

    # Try Month/Year MM/YYYY (e.g. Focus indicators) -> convert to first of month YYYY-MM-01
    match_my = re.match(r"^(\d{2})/(\d{4})$", val)
    if match_my:
        month, year = match_my.groups()
        return f"{year}-{month}-01"

    return val


def strip_accents(text: Optional[str]) -> str:
    """Removes diacritics/accents for robust search and comparison."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in normalized if not unicodedata.combining(c)).upper().strip()
