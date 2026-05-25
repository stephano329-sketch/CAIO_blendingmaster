import { cn } from "@/lib/cn";
import type { Decision } from "@/lib/types";

const DECISION_STYLE: Record<Decision, string> = {
  normal: "bg-green-100 text-green-800 ring-green-300",
  caution: "bg-amber-100 text-amber-800 ring-amber-300",
  risk: "bg-red-100 text-red-800 ring-red-300",
};

const DECISION_LABEL: Record<Decision, string> = {
  normal: "정상",
  caution: "주의",
  risk: "위험",
};

export function DecisionBadge({ decision }: { decision: Decision }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset",
        DECISION_STYLE[decision],
      )}
    >
      {DECISION_LABEL[decision]}
    </span>
  );
}

export function Badge({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700",
        className,
      )}
    >
      {children}
    </span>
  );
}
