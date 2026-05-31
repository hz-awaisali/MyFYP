"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.users.schemas import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    registration_number: str = Field(min_length=1, max_length=50)
    program_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair
