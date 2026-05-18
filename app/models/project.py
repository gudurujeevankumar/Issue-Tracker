from tortoise import fields
from tortoise.models import Model

class Project(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=255)
    
    owner: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="projects_owned"
    )
    members: fields.ManyToManyRelation["User"] = fields.ManyToManyField(
        "models.User", related_name="projects_joined", through="project_members"
    )
    
    issues: fields.ReverseRelation["Issue"]

    class Meta:
        table = "projects"

    def __str__(self) -> str:
        return self.name
