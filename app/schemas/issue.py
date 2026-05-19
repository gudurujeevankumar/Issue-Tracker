from datetime import date, datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from app.models.issue import IssuePriority, IssueStatus
from app.schemas.user import UserResponse

class IssueCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.TODO
    priority: IssuePriority = IssuePriority.MEDIUM
    due_date: Optional[date] = None
    assignee_id: Optional[UUID] = None

class IssueUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    due_date: Optional[date] = None
    assignee_id: Optional[UUID] = None

class IssueResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: IssueStatus
    priority: IssuePriority
    due_date: Optional[date]
    project_id: UUID
    reporter: UserResponse
    assignee: Optional[UserResponse]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class IssueActivityResponse(BaseModel):
    id: UUID
    issue_id: UUID
    actor: UserResponse
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class IssueFilterParams(BaseModel):
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    assignee_id: Optional[UUID] = None
    due_before: Optional[date] = None
    due_after: Optional[date] = None
