import { expect, type Page, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser, logOutUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

async function createManager(page: Page, email: string, password: string) {
  await logInUser(page, firstSuperuser, firstSuperuserPassword)
  await page.goto("/admin")
  await page.getByRole("button", { name: "Add User" }).click()
  await page.getByPlaceholder("Email").fill(email)
  await page.getByPlaceholder("Password").first().fill(password)
  await page.getByPlaceholder("Password").last().fill(password)
  await page.getByLabel("Role").click()
  await page.getByRole("option", { name: "Manager" }).click()
  await page.getByLabel("Is active?").check()
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("User created successfully")).toBeVisible()
  await logOutUser(page)
}

test.describe("Member access", () => {
  for (const path of ["/admin", "/metrics"]) {
    test(`Member is redirected from ${path} and stays logged in`, async ({
      page,
    }) => {
      const email = randomEmail()
      const password = randomPassword()
      await createUser({ email, password })
      await logInUser(page, email, password)

      await page.goto(path)

      await expect(page).toHaveURL("/")
      await expect(
        page.getByText("Welcome back, nice to see you again!"),
      ).toBeVisible()
      await expect(page.getByRole("link", { name: "Admin" })).not.toBeVisible()
      await expect(
        page.getByRole("link", { name: "Metrics" }),
      ).not.toBeVisible()
    })
  }
})

test.describe("Manager access", () => {
  test("Manager can view users and metrics but not manage users", async ({
    page,
  }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createManager(page, email, password)
    await logInUser(page, email, password)

    await page.goto("/admin")
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible()
    await expect(
      page.getByRole("button", { name: "Add User" }),
    ).not.toBeVisible()
    await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible()
    await expect(page.getByRole("row").getByRole("button")).toHaveCount(0)

    await page.goto("/metrics")
    await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible()
    await expect(page.getByText("Total users")).toBeVisible()
  })
})
