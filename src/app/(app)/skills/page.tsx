import Link from "next/link";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import { skillCategoryLabel, skillLevelLabel, confidenceTone, trendTone, trendLabel } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import type { SkillCategory } from "@/generated/prisma/client";

const CATEGORY_ORDER: SkillCategory[] = ["TECHNICAL", "MOVEMENT", "TACTICAL", "PHYSICAL", "MENTAL"];

export default async function SkillsPage() {
  const { athlete } = await requireAthlete();

  const skills = await db.skill.findMany({ orderBy: { sortOrder: "asc" } });
  const latestAssessments = await db.skillAssessment.findMany({
    where: { athleteId: athlete.id },
    orderBy: { assessedAt: "desc" },
    include: { _count: { select: { evidence: true } } },
  });

  const latestBySkill = new Map<string, (typeof latestAssessments)[number]>();
  for (const assessment of latestAssessments) {
    if (!latestBySkill.has(assessment.skillId)) {
      latestBySkill.set(assessment.skillId, assessment);
    }
  }

  const assessedCount = latestBySkill.size;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Skill assessments</h1>
        <p className="mt-1 text-sm text-muted">
          {assessedCount} of {skills.length} skills have at least one evidence-backed assessment.
          Every assessment here is self-reported and marked provisional until confirmed by match
          evidence, video analysis, or your coach.
        </p>
      </div>

      {CATEGORY_ORDER.map((category) => {
        const categorySkills = skills.filter((s) => s.category === category);
        if (categorySkills.length === 0) return null;

        return (
          <section key={category} className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-muted-strong">{skillCategoryLabel[category]}</h2>
            <div className="overflow-hidden rounded-xl border border-border">
              {categorySkills.map((skill, index) => {
                const latest = latestBySkill.get(skill.id);
                return (
                  <Link
                    key={skill.id}
                    href={`/skills/${skill.id}`}
                    className={`flex items-center justify-between gap-4 px-4 py-3 text-sm transition-colors hover:bg-surface-raised ${
                      index !== 0 ? "border-t border-border" : ""
                    } bg-surface`}
                  >
                    <span className="font-medium text-foreground">{skill.name}</span>
                    <div className="flex items-center gap-2">
                      {latest ? (
                        <>
                          <Badge tone="neutral">{skillLevelLabel[latest.level]}</Badge>
                          <Badge tone={confidenceTone[latest.confidence]}>
                            {latest.confidence.replace("_", " ").toLowerCase()}
                          </Badge>
                          <Badge tone={trendTone[latest.trend]}>{trendLabel[latest.trend]}</Badge>
                          {latest.status === "PROVISIONAL" && <Badge tone="warning">Provisional</Badge>}
                        </>
                      ) : (
                        <Badge tone="neutral">Not yet assessed</Badge>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
