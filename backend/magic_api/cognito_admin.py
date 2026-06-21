from __future__ import annotations

from typing import Protocol

from magic_api.models import Role, UserStatus


class IdentityAdmin(Protocol):
    def upsert_user(
        self,
        *,
        username: str,
        role: Role,
        status: UserStatus,
        temporary_password: str | None,
    ) -> None: ...

    def reset_password(self, *, username: str, temporary_password: str) -> None: ...

    def delete_user(self, *, username: str) -> None: ...


# App roles are modeled as exactly one Cognito group from this fixed set.
# Non-role Cognito groups are intentionally preserved.
COGNITO_ROLE_GROUPS = ("admin", "teacher", "student")


class CognitoIdentityAdmin:
    def __init__(self, cognito_client, *, user_pool_id: str) -> None:
        self.cognito = cognito_client
        self.user_pool_id = user_pool_id

    def reset_password(self, *, username: str, temporary_password: str) -> None:
        self.cognito.admin_set_user_password(
            UserPoolId=self.user_pool_id,
            Username=username,
            Password=temporary_password,
            Permanent=False,
        )

    def delete_user(self, *, username: str) -> None:
        try:
            self.cognito.admin_delete_user(UserPoolId=self.user_pool_id, Username=username)
        except self.cognito.exceptions.UserNotFoundException:
            return

    def _reconcile_role_group(self, *, username: str, role: Role) -> None:
        response = self.cognito.admin_list_groups_for_user(
            UserPoolId=self.user_pool_id,
            Username=username,
        )
        existing_groups = {
            group.get("GroupName")
            for group in response.get("Groups", [])
            if isinstance(group, dict)
        }
        for group_name in COGNITO_ROLE_GROUPS:
            if group_name != role and group_name in existing_groups:
                self.cognito.admin_remove_user_from_group(
                    UserPoolId=self.user_pool_id,
                    Username=username,
                    GroupName=group_name,
                )
        self.cognito.admin_add_user_to_group(
            UserPoolId=self.user_pool_id, Username=username, GroupName=role
        )

    def upsert_user(
        self,
        *,
        username: str,
        role: Role,
        status: UserStatus,
        temporary_password: str | None,
    ) -> None:
        user_exists = True
        try:
            self.cognito.admin_get_user(UserPoolId=self.user_pool_id, Username=username)
        except self.cognito.exceptions.UserNotFoundException:
            user_exists = False
            if not temporary_password:
                raise ValueError("temporary_password is required for new Cognito users") from None
            self.cognito.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                TemporaryPassword=temporary_password,
                MessageAction="SUPPRESS",
            )
        if user_exists and temporary_password:
            self.reset_password(username=username, temporary_password=temporary_password)
        self._reconcile_role_group(username=username, role=role)
        if status == "inactive":
            self.cognito.admin_disable_user(
                UserPoolId=self.user_pool_id, Username=username
            )
        else:
            self.cognito.admin_enable_user(UserPoolId=self.user_pool_id, Username=username)
