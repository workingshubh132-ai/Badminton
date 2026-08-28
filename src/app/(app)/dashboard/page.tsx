import Link from "next/link";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import {
  confidenceLabel,
  confidenceTone,
  goalCategoryLabel,
  skillLevelLabel,
  trendLabel,
  trendTone,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default async function DashboardPage() {
  const { athlete } = await requireAthlete();

  const [totalSkills, assessments, activeGoals, evidenceCount] = await Promise.all([
    db.skill.count(),
    db.skillAssessment.findMany({
      where: { athleteId: athlete.id },
      orderBy: { assessedAt: "desc" },
      include: { skill: true },
    }),
    db.goal.findMany({
      where: { athleteId: athlete.id, status: "ACTIVE" },
      orderBy: [{ priority: "desc" }, { createdAt: "desc" }],
    }),
    db.evidence.count({
      where: { skillAssessment: { athleteId: athlete.id } },
    }),
  ]);

  const latestBySkill = new Map<string, (typeof assessments)[number]>();
  for (const a of assessments) {
    if (!latestBySkill.has(a.skillId)) latestBySkill.set(a.skillId, a);
  }
  const latest = Array.from(latestBySkill.values());

  const worthDiscussing = latest.filter(
    (a) => a.confidence === "VERY_LOW" || a.confidence === "LOW" || a.trend === "DECLINING",
  );
  const highPriorityGoals = activeGoals.filter((g) => g.priority === "HIGH");

  const coveragePct = totalSkills > 0 ? Math.round((latest.length / totalSkills) * 100) : 0;
  const hasEnoughEvidenceForBottleneck = false; // Requires match/video data — not yet built (M4+).

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">
          Welcome back, {athlete.fullName.split(" ")[0]}
        </h1>
        <p className="mt-1 text-sm text-muted">
          Your evidence-based development record. Self-reported for now — match and video analysis
          land in a later milestone.
        </p>
      </div>

      <Card className="border-accent/30">
        <CardHeader>
          <CardTitle>What is holding you back?</CardTitle>
        </CardHeader>
        {hasEnoughEvidenceForBottleneck ? null : (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-foreground">
              Insufficient evidence for a reliable primary-bottleneck determination.
            </p>
            <p className="text-sm text-muted">
              The bottleneck engine needs recurring evidence across multiple matches — frequency,
              severity, and how often opponents exploit an issue — before it can responsibly name
              one weakness as your biggest limiter. That requires match/video analysis, which isn&apos;t
              built yet (it&apos;s a later milestone). Right now you can log self-reported skill
              assessments; use those honestly rather than as a substitute for this section.
            </p>
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Worth discussing with your coach</CardTitle>
          </CardHeader>
          {worthDiscussing.length === 0 && highPriorityGoals.length === 0 ? (
            <CardDescription>
              Nothing flagged yet. This fills in as you log assessments with low confidence or a
              declining trend, or set high-priority goals.
            </CardDescription>
          ) : (
            <ul className="flex flex-col gap-3">
              {highPriorityGoals.map((goal) => (
                <li key={goal.id} className="text-sm">
                  <Link href="/goals" className="text-foreground hover:underline">
                    {goal.title}
                  </Link>{" "}
                  <span className="text-muted">— high-priority goal ({goalCategoryLabel[goal.category]})</span>
                </li>
              ))}
              {worthDiscussing.map((a) => (
                <li key={a.id} className="text-sm">
                  <Link href={`/skills/${a.skillId}`} className="text-foreground hover:underline">
                    {a.skill.name}
                  </Link>{" "}
                  <span className="text-muted">
                    — {a.trend === "DECLINING" ? "declining trend" : "low-confidence assessment"} (
                    {confidenceLabel[a.confidence]})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Development priorities</CardTitle>
          </CardHeader>
          {activeGoals.length === 0 ? (
            <CardDescription>
              No active goals yet. <Link href="/goals" className="text-accent hover:underline">Add one</Link>.
            </CardDescription>
          ) : (
            <ul className="flex flex-col gap-2">
              {activeGoals.slice(0, 6).map((goal) => (
                <li key={goal.id} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{goal.title}</span>
                  <Badge tone="neutral">{goalCategoryLabel[goal.category]}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Latest match insight</CardTitle>
        </CardHeader>
        <CardDescription>
          No matches uploaded yet. Match upload and analysis are a later milestone — once available,
          the single most important new discovery from your latest match will appear here.
        </CardDescription>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-2xl font-semibold text-foreground">{coveragePct}%</p>
          <p className="mt-1 text-sm text-muted">
            skill coverage ({latest.length}/{totalSkills} skills assessed at least once)
          </p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-foreground">{evidenceCount}</p>
          <p className="mt-1 text-sm text-muted">evidence entries logged</p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-foreground">{activeGoals.length}</p>
          <p className="mt-1 text-sm text-muted">active goals</p>
        </Card>
      </div>

      {latest.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-muted-strong">Recently assessed</h2>
          <div className="overflow-hidden rounded-xl border border-border">
            {latest.slice(0, 8).map((a, i) => (
              <Link
                key={a.id}
                href={`/skills/${a.skillId}`}
                className={`flex items-center justify-between gap-4 bg-surface px-4 py-3 text-sm transition-colors hover:bg-surface-raised ${
                  i !== 0 ? "border-t border-border" : ""
                }`}
              >
                <span className="font-medium text-foreground">{a.skill.name}</span>
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{skillLevelLabel[a.level]}</Badge>
                  <Badge tone={confidenceTone[a.confidence]}>{confidenceLabel[a.confidence]}</Badge>
                  <Badge tone={trendTone[a.trend]}>{trendLabel[a.trend]}</Badge>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
