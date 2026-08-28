// Real container-format detection from file bytes — never a filename/MIME
// guess. A client's declared Content-Type is not trusted for validation;
// this is what actually decides whether a file looks like a real video
// container. Deliberately narrow: it recognizes the container formats a
// phone or a common desktop export would realistically produce, and returns
// null (never a guess) for anything else.

export interface DetectedContainerFormat {
  format: "mp4" | "quicktime" | "webm-or-mkv" | "avi";
  mimeType: string;
}

function bytesEqual(buf: Buffer, offset: number, expected: number[]): boolean {
  if (buf.length < offset + expected.length) return false;
  for (let i = 0; i < expected.length; i++) {
    if (buf[offset + i] !== expected[i]) return false;
  }
  return true;
}

function asciiAt(buf: Buffer, offset: number, length: number): string {
  if (buf.length < offset + length) return "";
  return buf.toString("ascii", offset, offset + length);
}

/**
 * Inspects the first bytes of a file and returns the detected container
 * format, or null if nothing recognizable was found. `head` should be at
 * least the first 32 bytes of the file (more is fine, harmless).
 */
export function detectContainerFormat(head: Buffer): DetectedContainerFormat | null {
  // ISO base media file format (MP4, MOV, 3GP, ...): a "ftyp" box atom at
  // byte offset 4, with a 4-byte "major brand" immediately after it.
  if (asciiAt(head, 4, 4) === "ftyp") {
    const brand = asciiAt(head, 8, 4).trim();
    if (brand === "qt") {
      return { format: "quicktime", mimeType: "video/quicktime" };
    }
    return { format: "mp4", mimeType: "video/mp4" };
  }

  // WebM / Matroska: EBML header.
  if (bytesEqual(head, 0, [0x1a, 0x45, 0xdf, 0xa3])) {
    return { format: "webm-or-mkv", mimeType: "video/webm" };
  }

  // AVI: "RIFF" .... "AVI ".
  if (asciiAt(head, 0, 4) === "RIFF" && asciiAt(head, 8, 4) === "AVI ") {
    return { format: "avi", mimeType: "video/x-msvideo" };
  }

  return null;
}
