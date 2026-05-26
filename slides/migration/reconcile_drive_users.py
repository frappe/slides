"""
Reconcile Users + Drive Settings on the target site from a source Drive site.

Run on the target (Suite) site after the general Drive data migration:

    bench --site <target> execute slides.migration.reconcile_drive_users.execute \
        --kwargs '{"source_site": "<source>", "dry_run": 1}'

Behaviour:
- Reads users referenced in Drive/Writer/Slides docs on the source.
- Skips users disabled on source, and identifiers that are not valid emails
  (must be a single well-formed address, no commas/semicolons/whitespace).
- On target, creates missing users as enabled Website Users (no welcome email).
- Adds the Drive User role to any user (new or existing) that lacks it.
- Creates Drive Settings if missing, copying values from the source's Drive
  Settings when available, otherwise defaults.
- Overwrites existing target Drive Settings with source values when the source
  has a Drive Settings row for that user.
- Never overwrites fields on users that already exist on the target.
- Idempotent. Dry-run by default.

Pass create_drive_settings=0 to skip both creating and updating Drive Settings.
Use this in a pre-merge pass so the merge can import Drive Settings docs
directly from the source without target-side conflicts.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint, cstr, validate_email_address

REFERENCE_FIELDS = {
    "Drive File": ("owner", "modified_by"),
    "Drive Permission": ("owner", "modified_by", "user"),
    "Drive Team": ("owner", "modified_by"),
    "Drive Team Member": ("owner", "modified_by", "user"),
    "Drive Document": ("owner", "modified_by"),
    "Drive Document Version": ("owner", "modified_by"),
    "Drive Favourite": ("owner", "modified_by", "user"),
    "Drive Notification": ("owner", "modified_by", "to_user", "from_user"),
    "Drive Settings": ("owner", "modified_by", "user"),
    "Writer Document": ("owner", "modified_by"),
    "Writer Version": ("owner", "modified_by"),
    "Writer Template": ("owner", "modified_by"),
    "Presentation": ("owner", "modified_by"),
}

IGNORED_USERS = {"", "Administrator", "Guest"}

USER_FIELDS = (
    "first_name",
    "last_name",
    "full_name",
    "user_image",
    "language",
    "time_zone",
    "enabled",
)

DRIVE_SETTINGS_FIELDS = ("auto_detect_links", "writer_settings")


def execute(source_site: str, dry_run: int = 1, create_drive_settings: int = 1) -> dict:
    dry_run = cint(dry_run)
    handle_settings = bool(cint(create_drive_settings))
    target_site = frappe.local.site
    if source_site == target_site:
        raise ValueError("source_site and target_site must differ")

    source = _read_source(source_site, target_site)
    plan = _plan(source, handle_settings)
    _report(source_site, target_site, plan, dry_run, handle_settings)

    if dry_run:
        return {"status": "dry_run", **_summary(plan)}

    _apply(plan)
    return {"status": "applied", **_summary(plan)}


# ---- source side -----------------------------------------------------------


def _read_source(source_site: str, target_site: str) -> dict:
    _switch_site(source_site)
    try:
        users = _collect_users()
        info, settings = {}, {}
        for user in users:
            info[user] = frappe.db.get_value("User", user, USER_FIELDS, as_dict=True) or {}
            if frappe.db.exists("Drive Settings", user):
                available = [f for f in DRIVE_SETTINGS_FIELDS if frappe.db.has_column("Drive Settings", f)]
                if available:
                    settings[user] = (
                        frappe.db.get_value("Drive Settings", user, available, as_dict=True) or {}
                    )
        return {"info": info, "settings": settings}
    finally:
        _switch_site(target_site)


def _collect_users() -> set[str]:
    users: set[str] = set()
    for doctype, fields in REFERENCE_FIELDS.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        for field in fields:
            if not frappe.db.has_column(doctype, field):
                continue
            for value in frappe.get_all(doctype, pluck=field):
                value = cstr(value).strip()
                if value and value not in IGNORED_USERS:
                    users.add(value)
    return users


# ---- planning (runs on target) --------------------------------------------


def _plan(source: dict, handle_settings: bool = True) -> dict:
    skipped_invalid: list[str] = []
    skipped_disabled: list[str] = []
    create_users: list[tuple[str, dict]] = []
    add_role: list[str] = []
    create_settings: list[tuple[str, dict]] = []
    update_settings: list[tuple[str, dict]] = []

    for user, src_info in sorted(source["info"].items()):
        if not _valid_email(user):
            skipped_invalid.append(user)
            continue
        if "enabled" in src_info and not cint(src_info.get("enabled")):
            skipped_disabled.append(user)
            continue

        src_settings = source["settings"].get(user, {})

        if not frappe.db.exists("User", user):
            create_users.append((user, src_info))
            add_role.append(user)
            if handle_settings:
                create_settings.append((user, src_settings))
            continue

        if not _has_role(user, "Drive User"):
            add_role.append(user)
        if handle_settings:
            if not frappe.db.exists("Drive Settings", user):
                create_settings.append((user, src_settings))
            elif src_settings:
                update_settings.append((user, src_settings))

    return {
        "referenced": sorted(source["info"]),
        "skipped_invalid": skipped_invalid,
        "skipped_disabled": skipped_disabled,
        "create_users": create_users,
        "add_role": add_role,
        "create_settings": create_settings,
        "update_settings": update_settings,
    }


# ---- apply (runs on target) -----------------------------------------------


def _apply(plan: dict) -> None:
    created_users = 0
    for user, src_info in plan["create_users"]:
        if frappe.db.exists("User", user):
            continue
        _create_website_user(user, src_info)
        created_users += 1

    added_roles = 0
    for user in plan["add_role"]:
        if not frappe.db.exists("User", user):
            continue
        if _has_role(user, "Drive User"):
            continue
        _insert_role(user, "Drive User")
        added_roles += 1

    created_settings = 0
    for user, src_settings in plan["create_settings"]:
        if not frappe.db.exists("User", user):
            continue
        if frappe.db.exists("Drive Settings", user):
            continue
        _insert_drive_settings(user, src_settings)
        created_settings += 1

    updated_settings = 0
    for user, src_settings in plan["update_settings"]:
        if not frappe.db.exists("Drive Settings", user):
            continue
        if _update_drive_settings(user, src_settings):
            updated_settings += 1

    frappe.db.commit()
    frappe.cache.delete_key("users_for_mentions")
    frappe.cache.delete_key("enabled_users")
    frappe.clear_cache(doctype="User")

    print(f"Created users:           {created_users}")
    print(f"Added Drive User roles:  {added_roles}")
    print(f"Created Drive Settings:  {created_settings}")
    print(f"Updated Drive Settings:  {updated_settings}")


def _create_website_user(user: str, src_info: dict) -> None:
    first_name = cstr(src_info.get("first_name")).strip() or _derive_first_name(user)
    last_name = cstr(src_info.get("last_name")).strip()
    full_name = cstr(src_info.get("full_name")).strip() or " ".join(p for p in (first_name, last_name) if p)
    previous = getattr(frappe.flags, "in_import", None)
    frappe.flags.in_import = True
    try:
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": user,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "user_image": src_info.get("user_image"),
                "language": src_info.get("language"),
                "time_zone": src_info.get("time_zone"),
                "enabled": 1,
                "user_type": "Website User",
                "send_welcome_email": 0,
            }
        )
        doc.name = user
        doc.db_insert()
    finally:
        if previous is None:
            frappe.flags.pop("in_import", None)
        else:
            frappe.flags.in_import = previous


def _insert_role(user: str, role: str) -> None:
    frappe.get_doc(
        {
            "doctype": "Has Role",
            "name": frappe.generate_hash(length=10),
            "parent": user,
            "parenttype": "User",
            "parentfield": "roles",
            "role": role,
        }
    ).db_insert()


def _insert_drive_settings(user: str, src_settings: dict) -> None:
    payload = {"doctype": "Drive Settings", "name": user, "user": user}
    for field in DRIVE_SETTINGS_FIELDS:
        value = src_settings.get(field)
        if value is not None:
            payload[field] = value
    frappe.get_doc(payload).db_insert()


def _update_drive_settings(user: str, src_settings: dict) -> bool:
    payload = {
        field: src_settings[field]
        for field in DRIVE_SETTINGS_FIELDS
        if src_settings.get(field) is not None
    }
    if not payload:
        return False
    frappe.db.set_value("Drive Settings", user, payload)
    return True


# ---- helpers ---------------------------------------------------------------


def _has_role(user: str, role: str) -> bool:
    return bool(frappe.db.exists("Has Role", {"parent": user, "role": role}))


def _valid_email(user: str) -> bool:
    if not user or any(c.isspace() for c in user) or "," in user or ";" in user:
        return False
    if user.count("@") != 1:
        return False
    try:
        validated = validate_email_address(user, throw=False) or ""
    except Exception:
        return False
    return validated.strip().lower() == user.strip().lower()


def _derive_first_name(user: str) -> str:
    local = user.split("@", 1)[0]
    return local.replace(".", " ").replace("_", " ").replace("-", " ").title() or user


def _switch_site(site: str) -> None:
    try:
        if getattr(frappe.local, "db", None):
            frappe.db.close()
    except Exception:
        pass
    try:
        frappe.destroy()
    except Exception:
        pass
    frappe.init(site=site)
    frappe.connect()


# ---- reporting -------------------------------------------------------------


def _report(source: str, target: str, plan: dict, dry_run: int, handle_settings: bool = True) -> None:
    mode = "dry-run" if dry_run else "apply"
    existing_role = len(plan["add_role"]) - len(plan["create_users"])
    existing_settings = max(0, len(plan["create_settings"]) - len(plan["create_users"]))

    print(f"Source: {source}  ->  Target: {target}  [{mode}]")
    print(f"  Referenced users on source:         {len(plan['referenced'])}")
    print(f"  Skipped (invalid email):            {len(plan['skipped_invalid'])}")
    print(f"  Skipped (disabled on source):       {len(plan['skipped_disabled'])}")
    print(f"  New users to create on target:      {len(plan['create_users'])}")
    print(f"  Existing users missing Drive role:  {existing_role}")
    if handle_settings:
        print(f"  Existing users missing Drive Settings: {existing_settings}")
        print(f"  Existing Drive Settings to overwrite:  {len(plan['update_settings'])}")
    else:
        print(f"  Drive Settings handling: SKIPPED (create_drive_settings=0)")

    sections = (
        ("Invalid", plan["skipped_invalid"]),
        ("Disabled", plan["skipped_disabled"]),
        ("Will create", [u for u, _ in plan["create_users"]]),
        ("Add Drive User role", plan["add_role"]),
        ("Create Drive Settings", [u for u, _ in plan["create_settings"]]),
        ("Overwrite Drive Settings", [u for u, _ in plan["update_settings"]]),
    )
    for title, values in sections:
        if not values:
            continue
        print(f"\n{title} ({len(values)}):")
        for value in values[:50]:
            print(f"  - {value}")
        if len(values) > 50:
            print(f"  ... {len(values) - 50} more")


def _summary(plan: dict) -> dict:
    return {
        "referenced": len(plan["referenced"]),
        "skipped_invalid": len(plan["skipped_invalid"]),
        "skipped_disabled": len(plan["skipped_disabled"]),
        "create_users": len(plan["create_users"]),
        "add_role": len(plan["add_role"]),
        "create_settings": len(plan["create_settings"]),
        "update_settings": len(plan["update_settings"]),
    }
