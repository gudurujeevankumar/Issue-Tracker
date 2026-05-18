from uuid import UUID
from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr

    model_config = {"from_attributes": True}
