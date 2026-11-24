from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda value: value.lower())]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: NormalizedEmail
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=512)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token lifetime in seconds
