import type { Decision } from "@/lib/demo-data";
import { JUDGE_LABELS } from "@/lib/demo-data";

export function DecisionBadge({ decision }: { decision: Decision }) {
  return <span className={`badge badge-${decision}`}>{JUDGE_LABELS[decision]}</span>;
}
