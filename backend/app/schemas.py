from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import Priority, Role


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role
    organization_id: Optional[int] = None
    national_id: Optional[str] = Field(default=None, min_length=8, max_length=20)
    phone: Optional[str] = Field(default=None, min_length=8, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BeneficiaryRegistrationRequest(BaseModel):
    monthly_income: float = Field(ge=0)
    family_members: int = Field(ge=1, le=30)
    medical_condition: Optional[str] = Field(default=None, max_length=600)
    documents_url: str = Field(min_length=5, max_length=300)


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    description: str = Field(min_length=10, max_length=1200)
    priority: Priority
    requested_amount: float = Field(gt=0)
    beneficiary_id: int


class DonateRequest(BaseModel):
    amount: float = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, value: float):
        return round(value, 2)
