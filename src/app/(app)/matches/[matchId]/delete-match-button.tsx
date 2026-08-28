"use client";

import { useRouter } from "next/navigation";
import { deleteMatchAction } from "@/lib/actions/matches";
import { Button } from "@/components/ui/button";

export function DeleteMatchButton({ matchId }: { matchId: string }) {
  const router = useRouter();

  return (
    <Button
      variant="danger"
      onClick={async () => {
        if (!confirm("Delete this match? Its videos will be kept but unlinked from it.")) return;
        await deleteMatchAction(matchId);
        router.push("/matches");
      }}
    >
      Delete match
    </Button>
  );
}
