import { test, expect } from "@playwright/test";
import path from "node:path";

// M5 coverage: the real Python cv-service, invoked through the real
// PythonCvEngine over HTTP, producing real quality/calibration/tracking
// rows the video detail page renders. Requires CV_SERVICE_URL to point at
// a running cv-service (see cv-service/README or docs/CV_ARCHITECTURE.md
// "Running cv-service locally") — skips honestly, like the rest of this
// suite does for missing ffprobe, rather than failing when it's absent.
test.skip(!process.env.CV_SERVICE_URL, "CV_SERVICE_URL not set — start cv-service locally to run this spec.");

// A clearly-labeled synthetic fixture (see
// cv-service/eval/fixtures/generate_synthetic_fixture.py) — deterministic,
// known-good court geometry, no real human shape. Its expected CV outcome
// (GOOD quality, SUCCESS calibration, zero player tracks) is already
// verified against ground truth by cv-service/eval/evaluate.py and
// cv-service's own pytest suite; this test verifies the *product* renders
// that real result honestly, not that the CV pipeline itself is accurate.
const SYNTHETIC_COURT_CLIP = path.join(
  __dirname,
  "..",
  "cv-service",
  "eval",
  "fixtures",
  "synthetic_court_01.mp4",
);
const password = "correcthorsebattery";

test("a real cv-service analysis run renders honest quality/calibration/tracking results", async ({ page }) => {
  const email = `e2e_cv_${Date.now()}@example.com`;
  await page.goto("/signup");
  await page.fill("#name", "CV E2E Player");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/onboarding");
  await page.fill("#fullName", "CV E2E Player");
  await page.selectOption("#currentLevel", "CLUB_COMPETITIVE");
  await page.getByRole("button", { name: "Create profile" }).click();
  await page.waitForURL("**/dashboard");

  await page.goto("/videos");
  await page.selectOption("#videoType", "TRAINING");
  await page.setInputFiles('input[type="file"]', SYNTHETIC_COURT_CLIP);
  const viewStatusLink = page.getByRole("link", { name: "View status" });
  await viewStatusLink.waitFor({ timeout: 30_000 });
  const videoHref = (await viewStatusLink.getAttribute("href"))!;

  await page.goto(videoHref);
  // Real model inference takes real time — give it a generous window rather
  // than a fake instant result.
  await expect(page.getByText("Analysis complete")).toBeVisible({ timeout: 120_000 });

  await expect(page.getByText("Recording quality")).toBeVisible();
  await expect(page.getByText("Good", { exact: true })).toBeVisible();

  await expect(page.getByText("Court calibration")).toBeVisible();
  await expect(page.getByText("Court detected")).toBeVisible();
  await expect(page.getByText("Moderate confidence")).toBeVisible();

  await expect(page.getByText("Player tracking")).toBeVisible();
  await expect(page.getByText("No people were reliably tracked")).toBeVisible();

  // The overlay renders a real detected court quadrilateral (an SVG
  // polygon), not a placeholder image.
  await expect(page.locator("svg polygon")).toHaveCount(1);

  // Debug details exist but stay collapsed by default — a real
  // processing_metadata payload (engine/model versions, checksum), not a
  // frame-by-frame inspector.
  const debug = page.getByText("Developer / debug details");
  await expect(debug).toBeVisible();
  await expect(page.locator("pre")).not.toBeVisible();
  await debug.click();
  await expect(page.locator("pre")).toBeVisible();
  await expect(page.locator("pre")).toContainText("badminton-cv-service");
});
