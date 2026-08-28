import Link from "next/link";
import { notFound } from "next/navigation";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import {
  skillCategoryLabel,
  skillLevelLabel,
  confidenceLabel,
  confidenceTone,
  trendLabel,
  trendTone,
  assessmentStatusLabel,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { AssessmentForm } from "./assessment-form";
import { EvidenceForm } from "./evidence-form";

export default async function SkillDetailPage({
  params,
}: {
  params: Promise<{ skillId: string }>;
}) {
  const { skillId } = await params;
  const { athlete } = await requireAthlete();

  const skill = await db.skill.findUnique({ where: { id: skillId } });
  if (!skill) notFound();

  const assessments = await db.skillAssessment.findMany({
    where: { athleteId: athlete.id, skillId },
    orderBy: { assessedAt: "desc" },
    include: { evidence: { orderBy: { createdAt: "desc" } } },
  });

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link href="/skills" className="text-sm text-muted hover:text-foreground">
          ← All skills
        </Link>
        <div className="mt-2 flex items-center gap-2">
          <h1 className="text-xl font-semibold text-foreground">{skill.name}</h1>
          <Badge tone="neutral">{skillCategoryLabel[skill.category]}</Badge>
        </div>
        {skill.description && <p className="mt-1 text-sm text-muted">{skill.description}</p>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New assessment</CardTitle>
        </CardHeader>
        <AssessmentForm skillId={skill.id} />
      </Card>

      <div className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-muted-strong">
          History ({assessments.length})
        </h2>
        {assessments.length === 0 && (
          <p className="text-sm text-muted">No assessments yet for this skill.</p>
        )}
        {assessments.map((assessment) => (
          <Card key={assessment.id}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="neutral">{skillLevelLabel[assessment.level]}</Badge>
              <Badge tone={confidenceTone[assessment.confidence]}>
                {confidenceLabel[assessment.confidence]}
              </Badge>
              <Badge tone={trendTone[assessment.trend]}>{trendLabel[assessment.trend]}</Badge>
              <Badge tone={assessment.status === "PROVISIONAL" ? "warning" : "success"}>
                {assessmentStatusLabel[assessment.status]}
              </Badge>
              <span className="ml-auto text-xs text-muted">
                {new Date(assessment.assessedAt).toLocaleDateString()}
              </span>
            </div>
            <p className="mt-3 text-sm text-foreground">{assessment.summary}</p>

            <div className="mt-4 flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                Evidence ({assessment.evidence.length})
              </h3>
              {assessment.evidence.map((evidence) => (
                <div key={evidence.id} className="rounded-lg bg-surface-raised p-3 text-sm">
                  <span className="text-muted">
                    {evidence.evidenceType.replace(/_/g, " ").toLowerCase()} ·{" "}
                    {new Date(evidence.createdAt).toLocaleDateString()}
                  </span>
                  <p className="mt-1 text-foreground">{evidence.description}</p>
                </div>
              ))}
              <EvidenceForm assessmentId={assessment.id} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
