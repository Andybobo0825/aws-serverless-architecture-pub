import pytest

from magic_api.models import ClassAccess, UserProfile, Week
from magic_api.repositories import InMemoryRepository


@pytest.fixture
def repo():
    repository = InMemoryRepository()
    repository.users["student-jul"] = UserProfile(
        username="student-jul", role="student", classes=["jul"], device_id="device-jul"
    )
    repository.users["student-aug"] = UserProfile(
        username="student-aug", role="student", classes=["aug"], device_id="device-aug"
    )
    repository.users["student-both"] = UserProfile(
        username="student-both", role="student", classes=["jul", "aug"], device_id="device-both"
    )
    repository.users["teacher01"] = UserProfile(username="teacher01", role="teacher")
    repository.users["admin01"] = UserProfile(username="admin01", role="admin")
    repository.weeks["week-001"] = Week(week_id="week-001", week_number=1, title="Week 1")
    repository.weeks["week-002"] = Week(week_id="week-002", week_number=2, title="Week 2")
    repository.weeks["week-003"] = Week(week_id="week-003", week_number=3, title="Week 3")
    repository.class_access["jul"] = ClassAccess(class_id="jul", open_week_ids=["week-001"])
    repository.class_access["aug"] = ClassAccess(class_id="aug", open_week_ids=["week-002"])
    return repository
