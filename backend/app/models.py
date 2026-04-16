from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class Role(str, Enum):
    ADMIN = "admin"
    DONOR = "donor"
    BENEFICIARY = "beneficiary"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    hashed_password: str
    national_id: Optional[str] = Field(default=None, unique=True, index=True)
    role: Role
    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BeneficiaryProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    monthly_income: float = 0
    family_members: int = 1
    medical_condition: Optional[str] = None
    documents_url: Optional[str] = None
    approved: bool = False


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_code: str = Field(unique=True, index=True)
    title: str
    description: str
    priority: Priority
    requested_amount: float
    funded_amount: float = 0
    organization_id: int = Field(foreign_key="organization.id")
    beneficiary_id: int = Field(foreign_key="user.id")
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Donation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    donor_id: int = Field(foreign_key="user.id")
    case_id: Optional[int] = Field(default=None, foreign_key="case.id")
    organization_id: int = Field(foreign_key="organization.id")
    amount: float
    beneficiary_share: float
    organization_share: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
