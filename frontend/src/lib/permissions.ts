import { redirect } from "@tanstack/react-router"
import { AxiosError } from "axios"

import { type Permission, type Role, type UserMe, UsersService } from "@/client"

export const roles: { value: Role; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "member", label: "Member" },
]

export const hasPermission = (
  user: UserMe | null | undefined,
  permission: Permission,
) => user?.permissions.includes(permission) ?? false

// Route guard for beforeLoad: runs outside React Query, so it handles 401 itself
export const requirePermission = async (permission: Permission) => {
  let user: UserMe
  try {
    user = (await UsersService.readUserMe()).data
  } catch (error) {
    if (error instanceof AxiosError && error.response?.status === 401) {
      localStorage.removeItem("access_token")
      throw redirect({ to: "/login" })
    }
    throw error
  }
  if (!hasPermission(user, permission)) {
    throw redirect({ to: "/" })
  }
}
