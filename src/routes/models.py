from pydantic import BaseModel
from typing import Optional, Generic, TypeVar


# Generic type for API responses
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
