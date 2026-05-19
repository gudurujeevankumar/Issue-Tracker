from enum import StrEnum

from tortoise import fields
from tortoise.models import Model


class IssueStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class IssuePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Issue(Model):
    id = fields.UUIDField(primary_key=True)
    title = fields.CharField(max_length=500)
    description = fields.TextField(null=True)
    status = fields.CharEnumField(IssueStatus, default=IssueStatus.TODO, db_index=True)
    priority = fields.CharEnumField(IssuePriority, default=IssuePriority.MEDIUM, db_index=True)
    due_date = fields.DateField(null=True, db_index=True)
    is_archived = fields.BooleanField(default=False, db_index=True)

    project: fields.ForeignKeyRelation["Project"] = fields.ForeignKeyField(  # noqa: F821
        "models.Project", related_name="issues", on_delete=fields.CASCADE
    )
    reporter: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(  # noqa: F821
        "models.User", related_name="reported_issues", on_delete=fields.CASCADE
    )
    assignee: fields.ForeignKeyNullableRelation["User"] = fields.ForeignKeyField(  # noqa: F821
        "models.User",
        related_name="assigned_issues",
        on_delete=fields.SET_NULL,
        null=True,
    )

    created_at = fields.DatetimeField(auto_now_add=True, db_index=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse
    activities: fields.ReverseRelation["IssueActivity"]

    class Meta:
        table = "issues"

    def __str__(self) -> str:
        return self.title


class IssueActivity(Model):
    id = fields.UUIDField(primary_key=True)
    issue: fields.ForeignKeyRelation["Issue"] = fields.ForeignKeyField(
        "models.Issue", related_name="activities", on_delete=fields.CASCADE
    )
    actor: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="activities", on_delete=fields.CASCADE
    )
    field = fields.CharField(max_length=100)
    old_value = fields.TextField(null=True)
    new_value = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, db_index=True)

    class Meta:
        table = "issue_activities"
        # Append-only: never update or delete rows from application code.

    def __str__(self) -> str:
        return f"{self.field}: {self.old_value} → {self.new_value}"
