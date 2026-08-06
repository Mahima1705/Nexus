import { Bug, ShieldAlert, Wind, Gauge, BookCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ReviewFinding, ReviewResult } from "@/types/review";

const CATEGORY_CONFIG: {
  key: keyof ReviewResult;
  label: string;
  icon: React.ElementType;
}[] = [
  { key: "bugs", label: "Bugs", icon: Bug },
  { key: "security_issues", label: "Security Issues", icon: ShieldAlert },
  { key: "code_smells", label: "Code Smells", icon: Wind },
  { key: "performance_suggestions", label: "Performance Suggestions", icon: Gauge },
  { key: "best_practices", label: "Best Practices", icon: BookCheck },
];

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "default"> = {
  high: "destructive",
  medium: "warning",
  low: "default",
};

function FindingRow({ finding }: { finding: ReviewFinding }) {
  return (
    <li className="flex items-start justify-between gap-3 py-2 text-sm">
      <span>{finding.description}</span>
      <span className="flex shrink-0 items-center gap-2">
        {finding.line != null && <span className="text-xs text-muted-foreground">L{finding.line}</span>}
        {finding.severity && (
          <Badge variant={SEVERITY_VARIANT[finding.severity] ?? "default"}>{finding.severity}</Badge>
        )}
      </span>
    </li>
  );
}

export function FindingsList({ result }: { result: ReviewResult }) {
  const totalFindings = CATEGORY_CONFIG.reduce((sum, c) => sum + result[c.key].length, 0);

  if (totalFindings === 0) {
    return (
      <Card className="border-success/50 bg-success/5">
        <CardContent className="p-6 text-center text-sm text-success">
          No issues found — this code looks clean.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {CATEGORY_CONFIG.map(({ key, label, icon: Icon }) => {
        const findings = result[key];
        if (findings.length === 0) return null;
        return (
          <Card key={key}>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">
                {label} ({findings.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border">
                {findings.map((finding, i) => (
                  <FindingRow key={i} finding={finding} />
                ))}
              </ul>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
