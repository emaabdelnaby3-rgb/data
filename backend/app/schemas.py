from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import PaymentMethod, Priority


class DonorRegisterRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    national_id: str = Field(min_length=14, max_length=14)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, min_length=8, max_length=20)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    description: str = Field(min_length=10, max_length=1200)
    priority: Priority
    requested_amount: float = Field(gt=0)
    beneficiary_id: int


class DonateRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_method: PaymentMethod

    @field_validator("amount")
    @classmethod
    def round_amount(cls, value: float):
        return round(value, 2)
