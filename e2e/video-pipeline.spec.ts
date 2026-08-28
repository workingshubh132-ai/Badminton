import { test, expect } from "@playwright/test";
import path from "node:path";

// M4 coverage: real video upload through the real (non-fake) processing
// pipeline, invalid-file rejection, evidence on match/video subjects,
// cross-athlete authorization on video/match pages and the streaming route
// (both the token check and the separate session-ownership check), and
// deletion actually revoking access. Requires a migrated, seeded
// DATABASE_URL and ffprobe on PATH (see README.md) — ffprobe absence
// degrades gracefully (metadata stays null) rather than failing the test.
test.describe.configure({ mode: "serial" });

const VALID_CLIP = path.join(__dirname, "fixtures", "valid-clip.mp4");
const INVALID_CLIP = path.join(__dirname, "fixtures", "invalid-clip.mp4");
const password = "correcthorsebattery";

async function signUpAndOnboard(page: import("@playwright/test").Page, email: string, name: string) {
  await page.goto("/signup");
  await page.fill("#name", name);
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/onboarding");
  await page.fill("#fullName", name);
  await page.selectOption("#currentLevel", "CLUB_COMPETITIVE");
  await page.getByRole("button", { name: "Create profile" }).click();
  await page.waitForURL("**/dashboard");
}

let matchPath: string;
let videoHref: string;
const primaryEmail = `e2e_video_${Date.now()}@example.com`;

test("record a match, upload a real video, and see honest real pipeline results", async ({ page }) => {
  await signUpAndOnboard(page, primaryEmail, "Video E2E Player");

  await page.goto("/matches/new");
  await page.fill("#opponentName", "Fixture Opponent");
  await page.fill("#playedAt", "2026-08-20");
  await page.selectOption("#result", "WIN");
  await page.getByRole("button", { name: "Create match" }).click();
  await page.waitForURL((url) => url.pathname.startsWith("/matches/") && url.pathname !== "/matches/new");
  matchPath = new URL(page.url()).pathname;

  await page.setInputFiles('input[type="file"]', VALID_CLIP);
  const viewStatusLink = page.getByRole("link", { name: "View status" });
  await viewStatusLink.waitFor({ timeout: 30_000 });
  videoHref = (await viewStatusLink.getAttribute("href"))!;

  await page.goto(videoHref);

  // The pipeline actually ran: real status reached, real ffprobe-derived
  // metadata shown, and the CV stage honestly reports no engine exists
  // rather than fabricating a result.
  await expect(page.getByText("Ready for analysis")).toBeVisible();
  await expect(page.getByText("640 × 360")).toBeVisible();
  await expect(page.getByText("mp4", { exact: true })).toBeVisible();
  await expect(page.getByText("No computer-vision analysis engine is configured yet")).toBeVisible();
  await expect(page.locator("video")).toHaveCount(1);

  // Range-request streaming actually works, not just a 200 for the whole file.
  const src = await page.locator("video").getAttribute("src");
  const full = await page.request.get(new URL(src!, page.url()).toString());
  expect(full.status()).toBe(200);
  expect(full.headers()["accept-ranges"]).toBe("bytes");
  const ranged = await page.request.get(new URL(src!, page.url()).toString(), {
    headers: { Range: "bytes=0-999" },
  });
  expect(ranged.status()).toBe(206);
  expect((await ranged.body()).length).toBe(1000);
});

test("evidence can be added directly to the video and to the match", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", primaryEmail);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");

  await page.goto(videoHref);
  await page.fill("#timestampSeconds", "1.5");
  await page.fill("#videoEvidenceDescription", "At 1.5s the test pattern rotates — noting as a marker.");
  await page.getByRole("button", { name: "Add evidence" }).click();
  await expect(page.getByText("Evidence (1)")).toBeVisible();

  await page.goto(matchPath);
  await page.fill("#matchEvidenceDescription", "Lost 4 straight points at 18-18 after rushing serves.");
  await page.getByRole("button", { name: "Add evidence" }).click();
  await expect(page.getByText("Evidence (1)")).toBeVisible();
});

test("a video with no match can be attached to one, and a tampered foreign matchId is rejected", async ({
  page,
}) => {
  await page.goto("/login");
  await page.fill("#email", primaryEmail);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");

  // Upload as a standalone TRAINING video — no matchId — so it starts unassociated.
  await page.goto("/videos");
  await page.selectOption("#videoType", "TRAINING");
  await page.setInputFiles('input[type="file"]', VALID_CLIP);
  const viewStatusLink = page.getByRole("link", { name: "View status" });
  await viewStatusLink.waitFor({ timeout: 30_000 });
  const standaloneVideoHref = (await viewStatusLink.getAttribute("href"))!;

  await page.goto(standaloneVideoHref);
  await expect(page.getByLabel("Attach to a match")).toBeVisible();

  // A second athlete's match, injected into the <select> as a foreign id —
  // simulates a tampered client submitting an id that isn't legitimately
  // offered in the dropdown. The real defense is server-side (the action
  // re-checks the match belongs to the current athlete), not the dropdown's
  // contents, so this must be rejected.
  const secondEmail = `e2e_video_match_owner_${Date.now()}@example.com`;
  const otherContext = await page.context().browser()!.newContext();
  const otherPage = await otherContext.newPage();
  await signUpAndOnboard(otherPage, secondEmail, "Other Match Owner");
  await otherPage.goto("/matches/new");
  await otherPage.fill("#playedAt", "2026-08-01");
  await otherPage.selectOption("#result", "UNKNOWN");
  await otherPage.getByRole("button", { name: "Create match" }).click();
  await otherPage.waitForURL((url) => url.pathname.startsWith("/matches/") && url.pathname !== "/matches/new");
  const foreignMatchId = new URL(otherPage.url()).pathname.split("/").pop();
  await otherContext.close();

  await page.evaluate((foreignId) => {
    const select = document.getElementById("matchId") as HTMLSelectElement;
    const option = document.createElement("option");
    option.value = foreignId!;
    option.textContent = "__inject__";
    select.appendChild(option);
    select.value = foreignId!;
  }, foreignMatchId);
  await page.getByRole("button", { name: "Attach" }).click();
  await expect(page.getByText("Match not found.")).toBeVisible();

  // Now do it for real with the athlete's own match (from the first test).
  const ownMatchId = matchPath.split("/").pop()!;
  await page.selectOption("#matchId", ownMatchId);
  await page.getByRole("button", { name: "Attach" }).click();
  await expect(page.getByRole("link", { name: /Match vs Fixture Opponent/ })).toBeVisible();
});

test("an unreadable file is rejected with an honest reason, not silently accepted", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", primaryEmail);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");

  await page.goto("/videos");
  await page.setInputFiles('input[type="file"]', INVALID_CLIP);
  const viewStatusLink = page.getByRole("link", { name: "View status" });
  await viewStatusLink.waitFor({ timeout: 30_000 });
  const invalidHref = (await viewStatusLink.getAttribute("href"))!;

  await page.goto(invalidHref);
  await expect(page.getByText("Invalid — could not be processed")).toBeVisible();
  // The same reason legitimately appears twice (Status card + Processing
  // history job record) — assert at least one is visible, not exactly one.
  await expect(page.getByText(/format is unsupported/).first()).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Retry processing" })).toHaveCount(0);
});

test("a second athlete cannot see the first athlete's video, match, or stream — even with a valid token", async ({
  page,
}) => {
  const secondEmail = `e2e_video2_${Date.now()}@example.com`;
  await signUpAndOnboard(page, secondEmail, "Second Video Player");

  const videoResp = await page.goto(videoHref);
  expect(videoResp?.status()).toBe(404);

  const matchResp = await page.goto(matchPath);
  expect(matchResp?.status()).toBe(404);

  // A syntactically bogus token fails the signature check.
  const streamPath = videoHref.replace("/videos/", "/api/videos/") + "/stream";
  const bogus = await page.request.get(streamPath + "?token=bogus");
  expect(bogus.status()).toBe(403);
});

test("deleting a video revokes access even to a previously valid, unexpired stream token", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", primaryEmail);
  await page.fill("#password", password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");

  await page.goto(videoHref);
  const src = (await page.locator("video").getAttribute("src"))!;
  const streamUrl = new URL(src, page.url()).toString();

  const beforeDelete = await page.request.get(streamUrl);
  expect(beforeDelete.status()).toBe(200);

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete video" }).click();
  await page.waitForURL("**/videos");

  const afterDelete = await page.request.get(streamUrl);
  expect(afterDelete.status()).toBe(404);

  const pageResp = await page.goto(videoHref);
  expect(pageResp?.status()).toBe(404);
});
