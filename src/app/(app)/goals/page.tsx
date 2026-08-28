import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { GoalForm } from "./goal-form";
import { GoalItem } from "./goal-item";

export default async function GoalsPage() {
  const { athlete } = await requireAthlete();
  const goals = await db.goal.findMany({
    where: { athleteId: athlete.id },
    orderBy: [{ status: "asc" }, { createdAt: "desc" }],
  });

  const active = goals.filter((g) => g.status === "ACTIVE");
  const other = goals.filter((g) => g.status !== "ACTIVE");

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Goals</h1>
        <p className="mt-1 text-sm text-muted">
          What you&apos;re deliberately working toward. These are separate from bottlenecks the
          system identifies — a goal here is something you and your coach chose.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add a goal</CardTitle>
        </CardHeader>
        <GoalForm />
      </Card>

      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-strong">Active ({active.length})</h2>
        {active.length === 0 && (
          <p className="text-sm text-muted">No active goals yet — add one above.</p>
        )}
        {active.map((goal) => (
          <GoalItem key={goal.id} goal={goal} />
        ))}
      </div>

      {other.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-muted-strong">Achieved / abandoned</h2>
          {other.map((goal) => (
            <GoalItem key={goal.id} goal={goal} />
          ))}
        </div>
      )}
    </div>
  );
}
