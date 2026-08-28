import { redirect } from "next/navigation";
import Link from "next/link";
import { getCurrentAthlete } from "@/lib/session";
import { createAthleteProfileAction } from "@/lib/actions/profile";
import { ProfileForm } from "@/components/profile-form";

export default async function OnboardingPage() {
  const { athlete } = await getCurrentAthlete();
  if (athlete) {
    redirect("/dashboard");
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/" className="text-sm font-semibold tracking-wide text-foreground">
        BADMINTON<span className="text-accent">INTEL</span>
      </Link>
      <h1 className="mt-8 text-xl font-semibold text-foreground">Set up your athlete profile</h1>
      <p className="mt-1 text-sm text-muted">
        This becomes the identity record everything else attaches to — matches, video, assessments,
        and coach observations, once you add them.
      </p>
      <div className="mt-8">
        <ProfileForm action={createAthleteProfileAction} submitLabel="Create profile" />
      </div>
    </div>
  );
}
