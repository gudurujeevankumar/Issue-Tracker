from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, ProjectMember
from app.models import Project, User

router = APIRouter(prefix="/projects", tags=["Projects"])

class ProjectCreateRequest(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID

    model_config = {"from_attributes": True}

class MemberAddRequest(BaseModel):
    user_id: UUID

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreateRequest, current_user: CurrentUser):
    project = await Project.create(name=body.name, owner=current_user)
    return project

@router.get("", response_model=list[ProjectResponse])
async def list_projects(current_user: CurrentUser):
    owned = await current_user.projects_owned.all()
    joined = await current_user.projects_joined.all()
    return owned + joined

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project: ProjectMember):
    return project

@router.post("/{project_id}/members")
async def add_member(body: MemberAddRequest, project: ProjectMember, current_user: CurrentUser):
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can add members")
    
    user = await User.get_or_none(id=body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await project.members.add(user)
    return {"detail": "Member added"}

@router.delete("/{project_id}/members/{user_id}")
async def remove_member(user_id: UUID, project: ProjectMember, current_user: CurrentUser):
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can remove members")
        
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await project.members.remove(user)
    return {"detail": "Member removed"}
