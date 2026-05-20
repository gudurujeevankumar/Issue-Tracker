import os
from dotenv import load_dotenv

load_dotenv()
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.models import Project, User

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise credentials_exception
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_project_member(
    project_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = await Project.get_or_none(id=project_id).prefetch_related("members")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    is_owner = project.owner_id == current_user.id
    is_member = current_user in project.members
    
    if not (is_owner or is_member):
        raise HTTPException(status_code=403, detail="Not enough permissions to access this project")
        
    return project

ProjectMember = Annotated[Project, Depends(get_project_member)]
