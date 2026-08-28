import type { ConfidenceLevel, EventCategory, ShotType } from "@/generated/prisma/client";

// The implementation-agnostic boundary a real computer-vision engine (M5+)
// plugs into. Nothing in this codebase should ever synthesize a shot
// detection, a court position, or a confidence score outside an
// implementation of this interface — see docs/VIDEO_INTELLIGENCE.md "CV
// engine interface" for the full contract and spec section 25 ("do not
// overbuild") for why NullCvEngine below is the only implementation today.

export interface CVAnalysisInput {
  video: {
    id: string;
    storageKey: string;
    durationSeconds: number | null;
    width: number | null;
    height: number | null;
  };
  athleteId: string;
}

export interface CVDetectedEvent {
  category: EventCategory;
  shotType?: ShotType;
  timestampSeconds: number;
  confidence: ConfidenceLevel;
  courtX?: number;
  courtY?: number;
  metadata?: Record<string, unknown>;
}

export interface CVAnalysisResult {
  /**
   * "completed" — the engine ran and (possibly empty) `events` is a real
   * result. "unavailable" — no engine capable of this work is configured;
   * this is the honest, expected state today, not an error. "failed" — an
   * engine was configured and attempted the work but broke.
   */
  status: "completed" | "unavailable" | "failed";
  events: CVDetectedEvent[];
  warnings: string[];
  message?: string;
  engineName: string;
  engineVersion: string;
}

export interface CVAnalysisEngine {
  readonly name: string;
  readonly version: string;
  analyze(input: CVAnalysisInput): Promise<CVAnalysisResult>;
}

/**
 * The only engine wired up today. It does no video processing at all — it
 * honestly reports that no real engine exists yet, per the product's
 * "insufficient evidence" > "confident-sounding answer" rule (spec section
 * 27). Every real analysis pipeline stage (job creation, status transitions,
 * event-writing) already runs for real against this engine; only the
 * detection logic itself is unbuilt.
 */
export class NullCvEngine implements CVAnalysisEngine {
  readonly name = "null-cv-engine";
  readonly version = "0.0.0";

  async analyze(): Promise<CVAnalysisResult> {
    return {
      status: "unavailable",
      events: [],
      warnings: [],
      message:
        "No computer-vision analysis engine is configured yet. Upload, storage, and validation for this video are complete, and it will be analyzed automatically as soon as a real engine is available.",
      engineName: this.name,
      engineVersion: this.version,
    };
  }
}

export function getCvEngine(): CVAnalysisEngine {
  return new NullCvEngine();
}
