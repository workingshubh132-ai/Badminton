import { requireAthlete } from "@/lib/session";
import { updateAthleteProfileAction } from "@/lib/actions/profile";
import { ProfileForm } from "@/components/profile-form";

export default async function ProfilePage() {
  const { athlete } = await requireAthlete();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-foreground">Your profile</h1>
      <p className="mt-1 text-sm text-muted">
        Keep this current — the coach-discussion notes and future match analysis reference it.
      </p>
      <div className="mt-8">
        <ProfileForm
          action={updateAthleteProfileAction}
          athlete={athlete}
          profile={athlete.profile}
          submitLabel="Save changes"
        />
      </div>
    </div>
  );
}
