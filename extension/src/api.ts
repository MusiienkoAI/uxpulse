import * as vscode from "vscode";

export type Issue = {
  id: number;
  key: string;
  title: string;
  category: string;
  impact: string;
  confidence: number;
  screen?: string | null;
  source?: string | null;
  evidence: Record<string, unknown>;
  recommendation: Record<string, unknown>;
  created_at: string;
};

export function getBaseUrl(): string {
  const cfg = vscode.workspace.getConfiguration("uxpulse");
  return cfg.get<string>("baseUrl", "http://localhost:8000");
}

export async function fetchIssues(): Promise<Issue[]> {
  const url = `${getBaseUrl()}/v1/issues?limit=100`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch issues: ${res.status}`);
  }
  return (await res.json()) as Issue[];
}

export async function fetchIssue(key: string): Promise<Issue> {
  const url = `${getBaseUrl()}/v1/issues/${encodeURIComponent(key)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch issue: ${res.status}`);
  }
  return (await res.json()) as Issue;
}
