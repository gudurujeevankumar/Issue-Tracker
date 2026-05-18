from tortoise import fields
from tortoise.models import Model

class User(Model):
    id = fields.UUIDField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    hashed_password = fields.CharField(max_length=255)
    
    # Reverse relations
    projects_owned: fields.ReverseRelation["Project"]
    projects_joined: fields.ManyToManyRelation["Project"]
    reported_issues: fields.ReverseRelation["Issue"]
    assigned_issues: fields.ReverseRelation["Issue"]
    activities: fields.ReverseRelation["IssueActivity"]

    class Meta:
        table = "users"

    def __str__(self) -> str:
        return self.email
