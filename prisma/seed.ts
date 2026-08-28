import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });
const db = new PrismaClient({ adapter });

// Skill catalog per spec section 4 (Athlete Performance Model). This is a
// reference table — not user-editable — that SkillAssessment rows point at.
// `key` is a stable slug; renaming `name` later is safe, changing `key` is not.
const SKILLS: Array<{
  key: string;
  name: string;
  category: "TECHNICAL" | "MOVEMENT" | "TACTICAL" | "PHYSICAL" | "MENTAL";
}> = [
  // Technical
  { key: "serve", name: "Serve", category: "TECHNICAL" },
  { key: "return", name: "Return", category: "TECHNICAL" },
  { key: "clear", name: "Clear", category: "TECHNICAL" },
  { key: "smash", name: "Smash", category: "TECHNICAL" },
  { key: "drop", name: "Drop", category: "TECHNICAL" },
  { key: "slice", name: "Slice", category: "TECHNICAL" },
  { key: "stick_smash", name: "Stick Smash", category: "TECHNICAL" },
  { key: "net_shot", name: "Net Shot", category: "TECHNICAL" },
  { key: "net_kill", name: "Net Kill", category: "TECHNICAL" },
  { key: "lift", name: "Lift", category: "TECHNICAL" },
  { key: "drive", name: "Drive", category: "TECHNICAL" },
  { key: "defence_technical", name: "Defence", category: "TECHNICAL" },
  { key: "backhand", name: "Backhand", category: "TECHNICAL" },
  { key: "round_the_head", name: "Round-the-Head", category: "TECHNICAL" },
  { key: "deception", name: "Deception", category: "TECHNICAL" },
  { key: "shot_quality", name: "Shot Quality", category: "TECHNICAL" },
  { key: "shot_consistency", name: "Consistency", category: "TECHNICAL" },

  // Movement
  { key: "split_step_timing", name: "Split-Step Timing", category: "MOVEMENT" },
  { key: "first_movement", name: "First Movement", category: "MOVEMENT" },
  { key: "acceleration", name: "Acceleration", category: "MOVEMENT" },
  { key: "rear_court_movement", name: "Rear-Court Movement", category: "MOVEMENT" },
  { key: "front_court_movement", name: "Front-Court Movement", category: "MOVEMENT" },
  { key: "lateral_movement", name: "Lateral Movement", category: "MOVEMENT" },
  { key: "chasse", name: "Chassé", category: "MOVEMENT" },
  { key: "cross_step", name: "Cross-Step", category: "MOVEMENT" },
  { key: "lunge", name: "Lunge", category: "MOVEMENT" },
  { key: "scissor_movement", name: "Scissor Movement", category: "MOVEMENT" },
  { key: "jump", name: "Jump", category: "MOVEMENT" },
  { key: "landing", name: "Landing", category: "MOVEMENT" },
  { key: "movement_recovery", name: "Recovery (to base)", category: "MOVEMENT" },
  { key: "base_position", name: "Base Position", category: "MOVEMENT" },
  { key: "court_coverage", name: "Court Coverage", category: "MOVEMENT" },
  { key: "balance", name: "Balance", category: "MOVEMENT" },

  // Tactical
  { key: "rally_construction", name: "Rally Construction", category: "TACTICAL" },
  { key: "attack_creation", name: "Attack Creation", category: "TACTICAL" },
  { key: "attack_conversion", name: "Attack Conversion", category: "TACTICAL" },
  { key: "defence_to_attack_transition", name: "Defence-to-Attack Transition", category: "TACTICAL" },
  { key: "shot_selection", name: "Shot Selection", category: "TACTICAL" },
  { key: "opponent_manipulation", name: "Opponent Manipulation", category: "TACTICAL" },
  { key: "pattern_recognition", name: "Pattern Recognition", category: "TACTICAL" },
  { key: "anticipation", name: "Anticipation", category: "TACTICAL" },
  { key: "serve_strategy", name: "Serve Strategy", category: "TACTICAL" },
  { key: "return_strategy", name: "Return Strategy", category: "TACTICAL" },
  { key: "pressure_strategy", name: "Pressure Strategy", category: "TACTICAL" },
  { key: "closing_games", name: "Closing Games", category: "TACTICAL" },
  { key: "momentum_management", name: "Momentum Management", category: "TACTICAL" },

  // Physical
  { key: "speed", name: "Speed", category: "PHYSICAL" },
  { key: "agility", name: "Agility", category: "PHYSICAL" },
  { key: "explosiveness", name: "Explosiveness", category: "PHYSICAL" },
  { key: "endurance", name: "Endurance", category: "PHYSICAL" },
  { key: "strength", name: "Strength", category: "PHYSICAL" },
  { key: "mobility", name: "Mobility", category: "PHYSICAL" },
  { key: "recovery_capacity", name: "Recovery Capacity", category: "PHYSICAL" },
  { key: "fatigue_tolerance", name: "Fatigue Tolerance", category: "PHYSICAL" },

  // Mental / competitive
  { key: "concentration", name: "Concentration", category: "MENTAL" },
  { key: "pressure_response", name: "Pressure Response", category: "MENTAL" },
  { key: "emotional_control", name: "Emotional Control", category: "MENTAL" },
  { key: "competitive_confidence", name: "Confidence", category: "MENTAL" },
  { key: "resilience", name: "Resilience", category: "MENTAL" },
  { key: "decision_making_under_pressure", name: "Decision-Making Under Pressure", category: "MENTAL" },
  { key: "performance_consistency", name: "Performance Consistency", category: "MENTAL" },
];

async function main() {
  for (const [index, skill] of SKILLS.entries()) {
    await db.skill.upsert({
      where: { key: skill.key },
      update: { name: skill.name, category: skill.category, sortOrder: index },
      create: { ...skill, sortOrder: index },
    });
  }
  console.log(`Seeded ${SKILLS.length} skills.`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.$disconnect();
  });
