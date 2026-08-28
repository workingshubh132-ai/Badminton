import { describe, expect, it } from "vitest";
import { detectContainerFormat } from "@/lib/video/magic-bytes";

function bufferFromBytes(bytes: number[]): Buffer {
  return Buffer.from(bytes);
}

describe("detectContainerFormat", () => {
  it("detects an MP4 file via its ftyp box", () => {
    // "....ftypisom...."
    const head = Buffer.concat([
      Buffer.from([0x00, 0x00, 0x00, 0x18]),
      Buffer.from("ftyp", "ascii"),
      Buffer.from("isom", "ascii"),
      Buffer.alloc(20),
    ]);
    const result = detectContainerFormat(head);
    expect(result).toEqual({ format: "mp4", mimeType: "video/mp4" });
  });

  it("detects a QuickTime .mov file via the 'qt  ' brand", () => {
    const head = Buffer.concat([
      Buffer.from([0x00, 0x00, 0x00, 0x14]),
      Buffer.from("ftyp", "ascii"),
      Buffer.from("qt  ", "ascii"),
      Buffer.alloc(20),
    ]);
    const result = detectContainerFormat(head);
    expect(result).toEqual({ format: "quicktime", mimeType: "video/quicktime" });
  });

  it("detects a WebM/Matroska file via its EBML header", () => {
    const head = bufferFromBytes([0x1a, 0x45, 0xdf, 0xa3, 0x00, 0x00, 0x00, 0x00]);
    const result = detectContainerFormat(head);
    expect(result).toEqual({ format: "webm-or-mkv", mimeType: "video/webm" });
  });

  it("detects an AVI file via RIFF....AVI ", () => {
    const head = Buffer.concat([
      Buffer.from("RIFF", "ascii"),
      Buffer.from([0x00, 0x00, 0x00, 0x00]),
      Buffer.from("AVI ", "ascii"),
      Buffer.alloc(10),
    ]);
    const result = detectContainerFormat(head);
    expect(result).toEqual({ format: "avi", mimeType: "video/x-msvideo" });
  });

  it("returns null for plain text pretending to be a video", () => {
    const head = Buffer.from("this is not a real video file, just plain text", "ascii");
    expect(detectContainerFormat(head)).toBeNull();
  });

  it("returns null for an empty or too-short buffer", () => {
    expect(detectContainerFormat(Buffer.alloc(0))).toBeNull();
    expect(detectContainerFormat(Buffer.from([0x00, 0x01]))).toBeNull();
  });

  it("returns null for a JPEG (a real file, just not a video)", () => {
    const jpegHead = bufferFromBytes([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]);
    expect(detectContainerFormat(jpegHead)).toBeNull();
  });
});
