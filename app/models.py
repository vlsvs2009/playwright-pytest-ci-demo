from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class Status(StrEnum):
    new = "new"
    in_progress = "in_progress"
    done = "done"


Customer = Annotated[str, Field(min_length=2, max_length=80)]
Service = Annotated[str, Field(min_length=2, max_length=120)]
Price = Annotated[float, Field(gt=0, le=100_000), AfterValidator(lambda v: round(v, 2))]


class _StrictModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Credentials(_StrictModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=120)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrderCreate(_StrictModel):
    customer: Customer
    service: Service
    price: Price
    status: Status = Status.new


class OrderUpdate(_StrictModel):
    customer: Customer | None = None
    service: Service | None = None
    price: Price | None = None
    status: Status | None = None


class Order(BaseModel):
    id: int
    customer: str
    service: str
    price: float
    status: Status
    created_at: datetime


class OrderList(BaseModel):
    items: list[Order]
    count: int
