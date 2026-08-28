import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { db } from "@/lib/db";

export async function requireUser() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login");
  }
  return session.user;
}

/** Loads the current user's athlete + profile, or null if onboarding hasn't been completed. */
export async function getCurrentAthlete() {
  const user = await requireUser();
  const athlete = await db.athlete.findUnique({
    where: { userId: user.id },
    include: { profile: true },
  });
  return { user, athlete };
}

/** Like getCurrentAthlete, but redirects into onboarding if no athlete profile exists yet. */
export async function requireAthlete() {
  const { user, athlete } = await getCurrentAthlete();
  if (!athlete) {
    redirect("/onboarding");
  }
  return { user, athlete };
}
