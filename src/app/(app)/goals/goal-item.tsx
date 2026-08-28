"use client";

import type { Goal } from "@/generated/prisma/client";
import { setGoalStatusAction, deleteGoalAction } from "@/lib/actions/goals";
import { goalCategoryLabel, goalPriorityLabel } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const priorityTone = { LOW: "neutral", MEDIUM: "info", HIGH: "accent" } as const;

export function GoalItem({ goal }: { goal: Goal }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-border bg-surface-raised p-4">
      <div className="flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-medium text-foreground">{goal.title}</h3>
          <Badge tone="neutral">{goalCategoryLabel[goal.category]}</Badge>
          <Badge tone={priorityTone[goal.priority]}>{goalPriorityLabel[goal.priority]}</Badge>
        </div>
        {goal.description && <p className="mt-1.5 text-sm text-muted">{goal.description}</p>}
        {goal.targetDate && (
          <p className="mt-1.5 text-xs text-muted">
            Target: {new Date(goal.targetDate).toLocaleDateString()}
          </p>
        )}
      </div>
      <div className="flex shrink-0 flex-col gap-1.5">
        {goal.status === "ACTIVE" && (
          <>
            <Button
              variant="secondary"
              className="px-2 py-1 text-xs"
              onClick={() => setGoalStatusAction(goal.id, "ACHIEVED")}
            >
              Mark achieved
            </Button>
            <Button
              variant="ghost"
              className="px-2 py-1 text-xs"
              onClick={() => setGoalStatusAction(goal.id, "ABANDONED")}
            >
              Abandon
            </Button>
          </>
        )}
        {goal.status !== "ACTIVE" && (
          <Button
            variant="secondary"
            className="px-2 py-1 text-xs"
            onClick={() => setGoalStatusAction(goal.id, "ACTIVE")}
          >
            Reactivate
          </Button>
        )}
        <Button variant="danger" className="px-2 py-1 text-xs" onClick={() => deleteGoalAction(goal.id)}>
          Delete
        </Button>
      </div>
    </div>
  );
}
