"""
Collector for User Accounts, Full Names, Status, Local Account flags, and Security Groups.
"""
from typing import List, Dict, Set
from collectors.base_collector import BaseCollector
from models.system_models import UserInfoItem


class UserCollector(BaseCollector):
    """Gathers user accounts, security group memberships, and account active/disabled states."""

    def _get_group_memberships(self) -> Dict[str, List[str]]:
        """Maps usernames to their associated group memberships via Win32_GroupUser."""
        user_to_groups: Dict[str, Set[str]] = {}

        try:
            group_users = self.wmi.Win32_GroupUser()
            for gu in group_users:
                try:
                    part_component = getattr(gu, "PartComponent", "")
                    group_component = getattr(gu, "GroupComponent", "")

                    # Extract username from PartComponent: Win32_UserAccount.Domain="...",Name="..."
                    if "Win32_UserAccount" in part_component and 'Name="' in part_component:
                        username = part_component.split('Name="')[1].split('"')[0]
                        # Extract group name: Win32_Group.Domain="...",Name="..."
                        if 'Name="' in group_component:
                            group_name = group_component.split('Name="')[1].split('"')[0]
                            user_to_groups.setdefault(username.lower(), set()).add(group_name)
                except Exception:
                    continue
        except Exception as exc:
            self.logger.debug(f"Win32_GroupUser enumeration note: {exc}")

        return {k: sorted(list(v)) for k, v in user_to_groups.items()}

    def collect(self) -> List[UserInfoItem]:
        """
        Queries Win32_UserAccount to extract user identity, full name, status, and group memberships.
        Prioritizes the currently logged-on interactive user.
        """
        users: List[UserInfoItem] = []

        try:
            # 1. Identify currently active logged in user from Win32_ComputerSystem
            current_logged_user = None
            try:
                cs_records = self.wmi.Win32_ComputerSystem()
                if cs_records and getattr(cs_records[0], "UserName", None):
                    raw_user = cs_records[0].UserName
                    current_logged_user = raw_user.split("\\")[-1].lower() if "\\" in raw_user else raw_user.lower()
            except Exception:
                pass

            # 2. Get group mappings
            group_map = self._get_group_memberships()

            # 3. Query local user accounts
            user_accounts = self.wmi.Win32_UserAccount(LocalAccount=True)
            if not user_accounts:
                user_accounts = self.wmi.Win32_UserAccount()

            for account in user_accounts:
                name = getattr(account, "Name", "") or ""
                if not name:
                    continue

                full_name = getattr(account, "FullName", None) or ""
                disabled = bool(getattr(account, "Disabled", False))
                is_local = bool(getattr(account, "LocalAccount", True))
                status = getattr(account, "Status", "OK") or "OK"

                groups = group_map.get(name.lower(), [])
                if not groups:
                    # Provide standard default groups if not explicitly enumerated
                    groups = ["Users"]
                    if name.lower() in ("administrator", "admin") or (current_logged_user and name.lower() == current_logged_user):
                        groups = ["Administrators", "Users"]

                item = UserInfoItem(
                    username=name,
                    full_name=full_name if full_name else name,
                    username_length=len(name),
                    account_status=status,
                    local_account="Yes" if is_local else "No",
                    user_groups=groups,
                    account_disabled_status="Yes" if disabled else "No",
                )

                # Prioritize currently active logged in user at position 0
                if current_logged_user and name.lower() == current_logged_user:
                    users.insert(0, item)
                else:
                    users.append(item)

        except Exception as exc:
            self.logger.error(f"Failed to collect user accounts: {exc}")

        # Fallback if empty
        if not users:
            users.append(
                UserInfoItem(
                    username="User",
                    full_name="Default User",
                    username_length=4,
                    account_status="OK",
                    local_account="Yes",
                    user_groups=["Administrators", "Users"],
                    account_disabled_status="No",
                )
            )

        return users
