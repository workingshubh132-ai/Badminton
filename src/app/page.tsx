import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const PRINCIPLES = [
  {
    title: "Evidence, not vibes",
    body: "Every assessment stores what happened, when, and how confident the system is — never a bare rating.",
  },
  {
    title: "One bottleneck at a time",
    body: "The system tracks every weakness, but always tells you which single issue is limiting you the most right now.",
  },
  {
    title: "Your coach stays the authority",
    body: "This system does not replace your academy coach. It gives you and them a shared, evidence-backed record.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <span className="text-sm font-semibold tracking-wide text-foreground">
            BADMINTON<span className="text-accent">INTEL</span>
          </span>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-muted hover:text-foreground">
              Log in
            </Link>
            <Link href="/signup">
              <Button variant="primary">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-5xl flex-1 flex-col justify-center px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-accent">
          Athlete Performance Intelligence
        </p>
        <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight text-foreground sm:text-5xl">
          What is currently limiting your competitive performance the most?
        </h1>
        <p className="mt-6 max-w-xl text-base text-muted">
          A long-term performance-intelligence system for competitive singles badminton players. Not
          a chatbot, not a workout generator — a structured, evidence-based record of your game that
          gets sharper as you feed it matches, video, and coach observations.
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/signup">
            <Button variant="primary">Create your athlete profile</Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary">I already have an account</Button>
          </Link>
        </div>

        <div className="mt-20 grid gap-4 sm:grid-cols-3">
          {PRINCIPLES.map((principle) => (
            <Card key={principle.title}>
              <h2 className="text-sm font-semibold text-foreground">{principle.title}</h2>
              <p className="mt-2 text-sm text-muted">{principle.body}</p>
            </Card>
          ))}
        </div>
      </main>

      <footer className="border-t border-border px-6 py-6 text-center text-xs text-muted">
        This system does not diagnose injuries, guarantee competitive outcomes, or replace a
        qualified human coach.
      </footer>
    </div>
  );
}
