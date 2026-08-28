import { test, expect } from "@playwright/test";

// End-to-end coverage of the M1/M2 golden path: an account is created, onboarding produces an
// athlete profile, a goal and an evidence-backed skill assessment are logged, the dashboard
// reflects them honestly (including the "insufficient evidence" bottleneck state), and the
// session survives a sign-out/sign-in round trip. Requires a migrated, seeded database — see
// README.md "Setup".
test.describe.configure({ mode: "serial" });

const email = `e2e_${Date.now()}@example.com`;
const password = "correcthorsebattery";

test("signup, onboarding, goal, skill assessment, and dashboard reflect real evidence", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /what is currently limiting/i })).toBeVisible();

  await page.getByRole("link", { name: "Get started" }).click();
  await page.waitForURL("**/signup");
  await page.fill("#name", "E2E Player");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Create account" }).click();

  await page.waitForURL("**/onboarding");
  await page.fill("#fullName", "E2E Player");
  await page.selectOption("#currentLevel", "CLUB_COMPETITIVE");
  await page.getByRole("button", { name: "Create profile" }).click();
  await page.waitForURL("**/dashboard");

  // The bottleneck engine has no match/video evidence yet — the dashboard must say so honestly
  // rather than fabricate a "primary weakness."
  await expect(page.getByText(/insufficient evidence for a reliable primary-bottleneck/i)).toBeVisible();

  await page.goto("/goals");
  await page.fill("#title", "Stop overrunning the backhand corner in defence");
  await page.selectOption("#category", "MOVEMENT");
  await page.selectOption("#priority", "HIGH");
  await page.getByRole("button", { name: "Add goal" }).click();
  await expect(page.getByText("Stop overrunning the backhand corner in defence")).toBeVisible();

  await page.goto("/skills");
  // The link's accessible name also includes its status badge (e.g. "Smash Not yet assessed"),
  // and "Stick Smash" is a separate row, so match on the skill-name text node specifically.
  await page
    .getByRole("link")
    .filter({ has: page.getByText("Smash", { exact: true }) })
    .click();
  await page.waitForURL("**/skills/**");

  await page.selectOption("#level", "DEVELOPING");
  await page.selectOption("#confidence", "LOW");
  await page.selectOption("#trend", "DECLINING");
  await page.fill(
    "#summary",
    "Smash gets read easily in rear court because preparation is slow and telegraphed.",
  );
  await page.selectOption("#evidenceType", "MATCH_OBSERVATION");
  await page.fill(
    "#evidenceDescription",
    "Opponent blocked 4 of 5 smashes in the Aug 20 match by anticipating early.",
  );
  await page.getByRole("button", { name: "Save assessment" }).click();

  // An assessment can never exist without its evidence attached.
  await expect(page.getByText("Evidence (1)")).toBeVisible();
  await expect(
    page.getByText("Opponent blocked 4 of 5 smashes in the Aug 20 match by anticipating early."),
  ).toBeVisible();

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Worth discussing with your coach" })).toBeVisible();
  const worthDiscussingItem = page.locator("li", { hasText: "declining trend" });
  await expect(worthDiscussingItem.getByRole("link", { name: "Smash" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL("/");

  await page.goto("/login");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");
  await expect(page.getByRole("heading", { name: /welcome back, e2e/i })).toBeVisible();
});

test("dashboard nav does not overlap on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");

  const nav = page.locator("nav").first();
  const heading = page.getByRole("heading", { name: /welcome back/i });
  const navBox = await nav.boundingBox();
  const headingBox = await heading.boundingBox();
  expect(navBox).not.toBeNull();
  expect(headingBox).not.toBeNull();
  // The nav row must sit entirely above the page content — regression check for the header
  // wrapping/overlapping bug found during manual mobile testing.
  expect(navBox!.y + navBox!.height).toBeLessThanOrEqual(headingBox!.y);
});
