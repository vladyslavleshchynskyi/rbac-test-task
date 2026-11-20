import type { Permission, Role, UserMe } from "@/client"

export const roles: { value: Role; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "member", label: "Member" },
]

export const hasPermission = (
  user: UserMe | null | undefined,
  permission: Permission,
) => user?.permissions.includes(permission) ?? false
