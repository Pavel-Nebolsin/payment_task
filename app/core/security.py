import secrets


def is_valid_api_key(provided_key: str, expected_key: str) -> bool:
    """Сравнение ключа за константное время, чтобы исключить timing-атаки."""
    return secrets.compare_digest(provided_key, expected_key)
