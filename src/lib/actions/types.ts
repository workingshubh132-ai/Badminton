export type ActionState =
  | { ok: true }
  | { ok: false; error: string; fieldErrors?: Record<string, string[]> };

export const INITIAL_ACTION_STATE: ActionState = { ok: true };
