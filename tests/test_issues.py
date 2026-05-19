import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


async def _setup(client: AsyncClient):
    """Create owner + project, return (headers, project_id)."""
    await register_user(client, "owner@example.com", "owner")
    headers = await auth_headers(client, "owner@example.com")
    proj = await client.post("/projects", json={"name": "P1"}, headers=headers)
    return headers, proj.json()["id"]


async def test_create_and_get_issue(client: AsyncClient):
    headers, proj_id = await _setup(client)

    resp = await client.post(
        f"/projects/{proj_id}/issues",
        json={"title": "Fix login bug", "priority": "HIGH"},
        headers=headers,
    )
    assert resp.status_code == 201
    issue = resp.json()
    assert issue["title"] == "Fix login bug"
    assert issue["priority"] == "HIGH"
    assert issue["status"] == "TODO"

    get_resp = await client.get(f"/projects/{proj_id}/issues/{issue['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == issue["id"]


async def test_update_issue_records_activity(client: AsyncClient):
    headers, proj_id = await _setup(client)

    issue_resp = await client.post(
        f"/projects/{proj_id}/issues",
        json={"title": "Initial title"},
        headers=headers,
    )
    issue_id = issue_resp.json()["id"]

    patch_resp = await client.patch(
        f"/projects/{proj_id}/issues/{issue_id}",
        json={"status": "IN_PROGRESS", "title": "Updated title"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "IN_PROGRESS"

    activity_resp = await client.get(
        f"/projects/{proj_id}/issues/{issue_id}/activity", headers=headers
    )
    assert activity_resp.status_code == 200
    activities = activity_resp.json()["data"]
    fields_changed = {a["field"] for a in activities}
    assert "status" in fields_changed
    assert "title" in fields_changed


async def test_soft_delete_issue(client: AsyncClient):
    headers, proj_id = await _setup(client)

    issue_resp = await client.post(
        f"/projects/{proj_id}/issues", json={"title": "To delete"}, headers=headers
    )
    issue_id = issue_resp.json()["id"]

    del_resp = await client.delete(f"/projects/{proj_id}/issues/{issue_id}", headers=headers)
    assert del_resp.status_code == 204

    # Should 404 after soft delete (excluded from queries)
    get_resp = await client.get(f"/projects/{proj_id}/issues/{issue_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_non_reporter_non_owner_cannot_delete(client: AsyncClient):
    await register_user(client, "owner@example.com", "owner")
    await register_user(client, "member@example.com", "member")
    howner = await auth_headers(client, "owner@example.com")
    hmember = await auth_headers(client, "member@example.com")

    proj = await client.post("/projects", json={"name": "P"}, headers=howner)
    proj_id = proj.json()["id"]

    me = await client.get("/users/me", headers=hmember)
    member_id = me.json()["id"]
    await client.post(f"/projects/{proj_id}/members", json={"user_id": member_id}, headers=howner)

    issue_resp = await client.post(
        f"/projects/{proj_id}/issues", json={"title": "Owner's issue"}, headers=howner
    )
    issue_id = issue_resp.json()["id"]

    del_resp = await client.delete(
        f"/projects/{proj_id}/issues/{issue_id}", headers=hmember
    )
    assert del_resp.status_code == 403


async def test_issue_list_pagination(client: AsyncClient):
    headers, proj_id = await _setup(client)

    for i in range(5):
        await client.post(
            f"/projects/{proj_id}/issues", json={"title": f"Issue {i}"}, headers=headers
        )

    resp = await client.get(
        f"/projects/{proj_id}/issues?page=1&page_size=3", headers=headers
    )
    body = resp.json()
    assert body["total"] == 5
    assert len(body["data"]) == 3
    assert body["page"] == 1
    assert body["page_size"] == 3


async def test_issue_list_filter_by_status(client: AsyncClient):
    headers, proj_id = await _setup(client)

    issue_resp = await client.post(
        f"/projects/{proj_id}/issues", json={"title": "In progress"}, headers=headers
    )
    iid = issue_resp.json()["id"]
    await client.post(
        f"/projects/{proj_id}/issues", json={"title": "Todo"}, headers=headers
    )

    await client.patch(
        f"/projects/{proj_id}/issues/{iid}",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )

    resp = await client.get(
        f"/projects/{proj_id}/issues?status=IN_PROGRESS", headers=headers
    )
    assert resp.json()["total"] == 1
    assert resp.json()["data"][0]["id"] == iid
