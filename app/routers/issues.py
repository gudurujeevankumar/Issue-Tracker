from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from tortoise.queryset import QuerySet

from app.core.dependencies import CurrentUser, ProjectMember
from app.models import Issue, IssueActivity, User
from app.models.issue import IssuePriority, IssueStatus
from app.schemas.common import PaginatedResponse
from app.schemas.issue import (
    IssueActivityResponse,
    IssueCreateRequest,
    IssueFilterParams,
    IssueResponse,
    IssueUpdateRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/projects/{project_id}/issues", tags=["Issues"])

# Fields that are tracked in the audit log
_TRACKED_FIELDS: tuple[str, ...] = ("title", "description", "status", "priority", "assignee_id")

# Custom sort ordering for enum fields (higher value = higher priority)
_PRIORITY_ORDER = {
    IssuePriority.CRITICAL: 4,
    IssuePriority.HIGH: 3,
    IssuePriority.MEDIUM: 2,
    IssuePriority.LOW: 1,
}


def _build_issue_response(issue: Issue) -> IssueResponse:
    return IssueResponse(
        id=issue.pk,
        title=issue.title,
        description=issue.description,
        status=issue.status,
        priority=issue.priority,
        due_date=issue.due_date,
        project_id=issue.project_id,
        reporter=UserResponse.model_validate(issue.reporter),
        assignee=UserResponse.model_validate(issue.assignee) if issue.assignee else None,
        is_archived=issue.is_archived,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


async def _get_issue_or_404(project_id: UUID, issue_id: UUID) -> Issue:
    issue = await Issue.get_or_none(
        id=issue_id, project_id=project_id, is_archived=False
    ).prefetch_related("reporter", "assignee")
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


async def _record_activity(
    issue: Issue, actor: "User", field: str, old_val: str | None, new_val: str | None
) -> None:
    if old_val != new_val:
        await IssueActivity.create(
            issue=issue,
            actor=actor,
            field=field,
            old_value=old_val,
            new_value=new_val,
        )


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new issue in a project",
)
async def create_issue(
    body: IssueCreateRequest,
    project: ProjectMember,
    current_user: CurrentUser,
) -> IssueResponse:
    assignee = None
    if body.assignee_id:
        assignee = await User.get_or_none(id=body.assignee_id)
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")

    issue = await Issue.create(
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
        project=project,
        reporter=current_user,
        assignee=assignee,
    )
    await issue.fetch_related("reporter", "assignee")
    return _build_issue_response(issue)


@router.get(
    "",
    response_model=PaginatedResponse[IssueResponse],
    summary="List issues in a project",
    description=(
        "Supports filtering by status, priority, assignee_id, due_before, due_after. "
        "Sort with sort_by and order params."
    ),
)
async def list_issues(
    project: ProjectMember,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    priority: IssuePriority | None = None,
    assignee_id: UUID | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    sort_by: str = Query(
        default="created_at",
        pattern="^(created_at|due_date|priority|status)$",
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> PaginatedResponse[IssueResponse]:
    qs: QuerySet[Issue] = Issue.filter(project=project, is_archived=False)

    if status_filter is not None:
        qs = qs.filter(status=status_filter)
    if priority is not None:
        qs = qs.filter(priority=priority)
    if assignee_id is not None:
        qs = qs.filter(assignee_id=assignee_id)
    if due_before is not None:
        qs = qs.filter(due_date__lte=due_before)
    if due_after is not None:
        qs = qs.filter(due_date__gte=due_after)

    # For DB-sortable fields, delegate to Tortoise; for enum fields, sort in Python
    db_sortable = {"created_at", "due_date"}
    total = await qs.count()

    if sort_by in db_sortable:
        prefix = "-" if order == "desc" else ""
        issues = await qs.prefetch_related("reporter", "assignee").order_by(
            f"{prefix}{sort_by}"
        ).offset((page - 1) * page_size).limit(page_size)
    else:
        # Load all matching, then sort in Python (acceptable at intern-project scale)
        all_issues = await qs.prefetch_related("reporter", "assignee").all()
        reverse = order == "desc"
        if sort_by == "priority":
            all_issues.sort(key=lambda i: _PRIORITY_ORDER[i.priority], reverse=reverse)
        elif sort_by == "status":
            status_order = {IssueStatus.TODO: 1, IssueStatus.IN_PROGRESS: 2, IssueStatus.DONE: 3}
            all_issues.sort(key=lambda i: status_order[i.status], reverse=reverse)
        offset = (page - 1) * page_size
        issues = all_issues[offset : offset + page_size]

    return PaginatedResponse(
        data=[_build_issue_response(i) for i in issues],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Get issue detail",
)
async def get_issue(
    issue_id: UUID,
    project: ProjectMember,
) -> IssueResponse:
    issue = await _get_issue_or_404(project.pk, issue_id)
    return _build_issue_response(issue)


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Update issue fields",
    description="Automatically appends an audit-log entry for every changed field.",
)
async def update_issue(
    issue_id: UUID,
    body: IssueUpdateRequest,
    project: ProjectMember,
    current_user: CurrentUser,
) -> IssueResponse:
    issue = await _get_issue_or_404(project.pk, issue_id)

    updates: dict = {}
    activities: list[tuple[str, str | None, str | None]] = []

    if body.title is not None and body.title != issue.title:
        activities.append(("title", issue.title, body.title))
        updates["title"] = body.title

    if body.description is not None and body.description != issue.description:
        activities.append(("description", issue.description, body.description))
        updates["description"] = body.description

    if body.status is not None and body.status != issue.status:
        activities.append(("status", issue.status, body.status))
        updates["status"] = body.status

    if body.priority is not None and body.priority != issue.priority:
        activities.append(("priority", issue.priority, body.priority))
        updates["priority"] = body.priority

    if body.due_date is not None and body.due_date != issue.due_date:
        activities.append(
            ("due_date", str(issue.due_date) if issue.due_date else None, str(body.due_date))
        )
        updates["due_date"] = body.due_date

    if "assignee_id" in body.model_fields_set:
        old_id = str(issue.assignee_id) if issue.assignee_id else None
        new_id = str(body.assignee_id) if body.assignee_id else None
        if old_id != new_id:
            if body.assignee_id is not None:
                assignee = await User.get_or_none(id=body.assignee_id)
                if assignee is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found"
                    )
            activities.append(("assignee_id", old_id, new_id))
            updates["assignee_id"] = body.assignee_id

    if updates:
        await issue.update_from_dict(updates).save()
        for field, old_val, new_val in activities:
            await _record_activity(issue, current_user, field, old_val, new_val)

    await issue.fetch_related("reporter", "assignee")
    return _build_issue_response(issue)


@router.delete(
    "/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an issue",
    description=(
        "Marks the issue as archived rather than physically removing it. "
        "Only the reporter or project owner may perform this action."
    ),
)
async def delete_issue(
    issue_id: UUID,
    project: ProjectMember,
    current_user: CurrentUser,
) -> None:
    issue = await _get_issue_or_404(project.pk, issue_id)

    is_reporter = issue.reporter_id == current_user.id
    is_owner = project.owner_id == current_user.id

    if not is_reporter and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the issue reporter or project owner may delete this issue",
        )

    issue.is_archived = True
    await issue.save()


@router.get(
    "/{issue_id}/activity",
    response_model=PaginatedResponse[IssueActivityResponse],
    summary="Get the activity log for an issue",
    description="Append-only audit trail of all changes made to this issue.",
)
async def get_activity(
    issue_id: UUID,
    project: ProjectMember,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[IssueActivityResponse]:
    issue = await _get_issue_or_404(project.pk, issue_id)

    qs = IssueActivity.filter(issue=issue).prefetch_related("actor")
    total = await qs.count()
    records = (
        await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    )

    data = [
        IssueActivityResponse(
            id=r.pk,
            issue_id=issue.pk,
            actor=UserResponse.model_validate(r.actor),
            field=r.field,
            old_value=r.old_value,
            new_value=r.new_value,
            created_at=r.created_at,
        )
        for r in records
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)
