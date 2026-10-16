from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["applied", "screening", "interview", "offer", "rejected"]


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApplicationIn(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    status: Status = "applied"
    source: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    status: Status | None = None
    source: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    at: datetime


class ApplicationOut(ApplicationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    events: list[EventOut] = []
