class INEError(Exception):
    """Error de consulta al INE."""


class INEAPIError(INEError):
    """La API respondió con un error o datos inesperados."""
