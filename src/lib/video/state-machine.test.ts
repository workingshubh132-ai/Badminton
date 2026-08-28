import { describe, expect, it } from "vitest";
import {
  assertValidVideoStatusTransition,
  canTransitionVideoStatus,
  InvalidVideoStatusTransitionError,
} from "@/lib/video/state-machine";

describe("video status state machine", () => {
  it("allows the normal happy-path pipeline", () => {
    const happyPath: Array<[string, string]> = [
      ["UPLOAD_PENDING", "UPLOADING"],
      ["UPLOADING", "UPLOADED"],
      ["UPLOADED", "VALIDATING"],
      ["VALIDATING", "VALID"],
      ["VALID", "PROCESSING"],
      ["PROCESSING", "READY_FOR_ANALYSIS"],
      ["READY_FOR_ANALYSIS", "ANALYZING"],
      ["ANALYZING", "ANALYZED"],
    ];
    for (const [from, to] of happyPath) {
      expect(canTransitionVideoStatus(from as never, to as never)).toBe(true);
    }
  });

  it("allows the CV-engine-unavailable bounce back to READY_FOR_ANALYSIS", () => {
    expect(canTransitionVideoStatus("ANALYZING", "READY_FOR_ANALYSIS")).toBe(true);
  });

  it("allows re-analysis from ANALYZED", () => {
    expect(canTransitionVideoStatus("ANALYZED", "ANALYZING")).toBe(true);
  });

  it("allows retrying a failed ingest pipeline", () => {
    expect(canTransitionVideoStatus("FAILED", "VALIDATING")).toBe(true);
  });

  it("rejects skipping stages", () => {
    expect(canTransitionVideoStatus("UPLOAD_PENDING", "VALID")).toBe(false);
    expect(canTransitionVideoStatus("UPLOADED", "READY_FOR_ANALYSIS")).toBe(false);
    expect(canTransitionVideoStatus("VALIDATING", "PROCESSING")).toBe(false);
  });

  it("rejects reviving a video out of INVALID other than deleting it", () => {
    expect(canTransitionVideoStatus("INVALID", "VALIDATING")).toBe(false);
    expect(canTransitionVideoStatus("INVALID", "VALID")).toBe(false);
    expect(canTransitionVideoStatus("INVALID", "DELETED")).toBe(true);
  });

  it("treats DELETED as fully terminal", () => {
    const allStatuses = [
      "UPLOAD_PENDING",
      "UPLOADING",
      "UPLOADED",
      "VALIDATING",
      "VALID",
      "INVALID",
      "PROCESSING",
      "READY_FOR_ANALYSIS",
      "ANALYZING",
      "ANALYZED",
      "FAILED",
      "DELETED",
    ] as const;
    for (const status of allStatuses) {
      expect(canTransitionVideoStatus("DELETED", status)).toBe(status === "DELETED" ? false : false);
    }
  });

  it("assertValidVideoStatusTransition throws a descriptive error on an illegal transition", () => {
    expect(() => assertValidVideoStatusTransition("DELETED", "UPLOADING")).toThrow(
      InvalidVideoStatusTransitionError,
    );
    try {
      assertValidVideoStatusTransition("VALID", "ANALYZED");
      throw new Error("should have thrown");
    } catch (error) {
      expect(error).toBeInstanceOf(InvalidVideoStatusTransitionError);
      expect((error as InvalidVideoStatusTransitionError).from).toBe("VALID");
      expect((error as InvalidVideoStatusTransitionError).to).toBe("ANALYZED");
    }
  });

  it("assertValidVideoStatusTransition does not throw on a legal transition", () => {
    expect(() => assertValidVideoStatusTransition("UPLOADED", "VALIDATING")).not.toThrow();
  });
});
