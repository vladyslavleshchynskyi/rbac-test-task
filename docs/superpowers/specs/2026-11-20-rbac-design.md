# Role-based access control (admin / manager / member)

Date: 2026-11-20 · Branch: `feat/rbac`

## Intent

Test task for Ender Turing (see `evios/Fullstack-Dev-Test-Task` README): replace the
binary `is_superuser` model of the Full Stack FastAPI Template with three access
levels, treating the template as an already deployed app with real users. Timebox is
about one hour, so the change stays focused: correctness, migration safety and
backend enforcement matter more than polish.

## Requirements

- **member** — own profile (read / update / change password / delete self) and own items.
- **manager** — everything a member can do, plus view the user list, view any user,
  view metrics. Cannot create, edit or delete users, cannot change roles or status.
- **admin** — everything; manages users, their roles and `is_active`; views metrics;
  sees and edits all items.
- Nobody (including admins) can change their own role or deactivate themselves.
- Authorization is enforced by the backend via FastAPI dependencies. Role and
  `is_active` are read from the DB on every request, so changes apply to existing
  sessions immediately.
- Frontend hides navigation/actions based on permissions served by the backend and
  redirects sensibly on direct navigation to a forbidden page.
- Existing users keep exactly their current level of access after migration.

## Non-goals / anti-goals

- No permissions in the JWT (would go stale after a role change or deactivation).
- No DB tables for roles/permissions, no per-user permission overrides.
- No refactoring of unrelated code, no infrastructure or visual polish.
- `.env` and `.python-version` stay uncommitted; `.gitignore` is not touched.
- No backward-compatible `is_superuser` field in the API.

## Approaches considered

1. **Role checks** (`require_roles(Role.ADMIN, ...)`) and role checks duplicated on
   the frontend. Simplest, but rules live in two places and drift.
2. **Role → permissions map (chosen).** One `ROLE_PERMISSIONS` dict on the backend,
   `require_permission(...)` dependency, and `/users/me` returns the current user's
   permissions so the frontend has no copy of the rules. Changing an access rule is a
   one-line edit.
3. **Permissions in JWT claims.** Rejected: stale after role/status changes, violates
   the "existing sessions" requirement.

For `is_superuser`, option **A** was chosen: migrate to `role`, drop the column,
expose only `role` in the API (the frontend is served by the backend and its client
is regenerated, so there is no external consumer to keep compatible).

## Design

### Data model and migration

- `Role(StrEnum)` in `app/models.py`: `admin`, `manager`, `member`. Member names equal
  values (lower-case) because SQLAlchemy `Enum` persists enum *names*.
- `UserBase.is_superuser` is replaced with `role: Role = Role.member` (DB column
  `role`, Postgres enum type `userrole`, NOT NULL).
- `UserCreate` inherits `role` (admin chooses it). `UserUpdate.role: Role | None`.
  `UserRegister` and `UserUpdateMe` get no `role`/`is_active` — signup always creates a
  member and users cannot elevate themselves.
- New Alembic revision with `down_revision = "fe56fa70289e"`:
  - upgrade: create enum type; add `role` nullable with `server_default 'member'`;
    `UPDATE "user" SET role = 'admin' WHERE is_superuser`; set NOT NULL; drop
    `is_superuser`. Nobody gains or loses privileges: superusers → admin, everyone
    else → member (no managers exist before the migration).
  - downgrade: add `is_superuser` boolean NOT NULL default false;
    `UPDATE ... SET is_superuser = true WHERE role = 'admin'`; drop `role` and the enum
    type. Lossy by design: managers become regular users (least privilege).
- `init_db` creates `FIRST_SUPERUSER` with `role=Role.admin` (env var names unchanged).

### Permissions

New module `app/core/permissions.py`:

```python
class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    METRICS_READ = "metrics:read"
    ITEMS_MANAGE_ALL = "items:manage_all"

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.member: frozenset(),
    Role.manager: frozenset({USERS_READ, METRICS_READ}),
    Role.admin: frozenset(Permission),
}

def has_permission(user: User, permission: Permission) -> bool: ...
```

### Dependencies (`app/api/deps.py`)

- `get_current_user` keeps loading the user from the DB per request. Failure codes
  change so the frontend can tell "session is dead" from "not allowed":
  invalid/expired token → **401**, user not found → **401**, inactive user → **401**
  (previously 403 / 404 / 400). Login with an inactive account still returns 400.
- `require_permission(permission)` returns a dependency that takes `CurrentUser` and
  raises **403** if `has_permission` is false. Used via `dependencies=[...]` or as a
  typed `Annotated` dependency when the handler needs the user.
- `get_current_active_superuser` is removed; all usages move to `require_permission`.

### Endpoint rules

| Endpoint | Rule |
|---|---|
| `GET /users/` | `users:read` |
| `GET /users/{id}` | self, or `users:read` |
| `POST /users/` | `users:manage` |
| `PATCH /users/{id}` | `users:manage`; if target is the current user and the payload changes `role` or `is_active` (value differs from stored) → 403 |
| `DELETE /users/{id}` | `users:manage`; self-delete forbidden (existing) |
| `DELETE /users/me` | allowed except for admins (replaces the superuser check) |
| `GET/PATCH /users/me`, `PATCH /users/me/password`, `POST /users/signup` | unchanged |
| Items CRUD | owner, or `items:manage_all` (replaces `is_superuser` checks) |
| `POST /utils/test-email/`, `POST /password-recovery-html-content/{email}` | `users:manage` |
| `GET /metrics/` (new) | `metrics:read` |

The self-change rule compares values rather than field presence, because the edit
form submits the full user including unchanged `role` and `is_active`.

### `/users/me` and metrics

- `UserPublic` exposes `role`. New `UserMe(UserPublic)` adds
  `permissions: list[Permission]`; it is the response model of `GET /users/me` only
  (lists stay lean).
- New router `app/api/routes/metrics.py`: `GET /metrics/` returns
  `{total_users, active_users, users_by_role: {admin, manager, member}}` — a simple
  stub computed with count queries.

### Frontend

- Regenerate the client with `scripts/generate-client.sh`.
- Helper `hasPermission(user, permission)` (next to `useAuth`); all checks use it.
  The only role-based check is the "danger zone" tab in settings (hidden for admins),
  mirroring the backend `DELETE /users/me` rule.
- `main.tsx`: clear token and redirect to `/login` only on **401**; a 403 shows the
  normal error toast.
- Sidebar: "Admin" (users) when `users:read`; new "Metrics" when `metrics:read`.
- `/admin` `beforeLoad`: redirect to `/` without `users:read`. "Add user" and the row
  actions menu render only with `users:manage`. Role column shows the role badge.
- `AddUser` / `EditUser`: replace the "Is superuser?" checkbox with a role select. In
  `EditUser` for the current user, role and active fields are disabled.
- New route `/_layout/metrics` with `beforeLoad` redirect to `/` without
  `metrics:read`; shows the three numbers.
- Update Playwright specs that reference "Is superuser?" / superuser wording.

### Tests (backend, pytest)

Update existing tests for `role` instead of `is_superuser`, and add focused tests:

- Permission matrix (parametrized by role) for `GET /users/`, `GET /users/{id}`,
  `POST /users/`, `PATCH /users/{id}`, `DELETE /users/{id}`, `GET /metrics/`.
- Self-protection: admin cannot change own role or deactivate self; submitting
  unchanged values succeeds.
- Existing session: a manager's token loses `users:read` immediately after an admin
  demotes them (403), and returns 401 after deactivation.
- No self-elevation: `role` in `POST /users/signup` and `PATCH /users/me` is ignored.
- `GET /users/me` returns the correct `permissions` per role.
- Manager cannot read/edit another user's item; admin can.

Migration is verified manually: on a DB at `fe56fa70289e` with a superuser and a
regular user, run upgrade → check roles → downgrade → check `is_superuser` → upgrade.

### Reviewer setup

- New script `backend/app/seed_demo_users.py`, run explicitly
  (`uv run python app/seed_demo_users.py` from `backend/`, or via
  `docker compose exec backend python app/seed_demo_users.py`). It is **not** part of
  `prestart.sh`, so it never runs on deployments.
- It refuses to run unless `FASTAPI_ENV == "development"`.
- Idempotent: creates `manager@example.com` (manager) and `member@example.com`
  (member) only if a user with that email does not exist; existing users are left
  untouched (no role or password reset). Password is `FIRST_SUPERUSER_PASSWORD`, so
  no new settings are introduced. It also calls `init_db` so the admin exists too.
- Root `README.md` gets a short section for the task: the three roles and what each
  can do, the seed command and demo credentials, and the note that
  `scripts/test.sh` wipes all users in the dev DB (rerun `initial_data.py` and the
  seed afterwards). Commands to run the app and tests are unchanged.

## Left to the builder

- Exact component structure of the role select and metrics page (reuse existing
  shadcn components, no new dependencies).
- Test helper shape for creating users with a role and getting their token headers.
- A small test for the seed script's idempotency (run twice → same users).
- Exact wording of error messages (keep the existing "The user doesn't have enough
  privileges" for 403).
