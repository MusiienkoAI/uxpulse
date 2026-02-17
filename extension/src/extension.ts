import * as path from "path";
import * as vscode from "vscode";

import { fetchIssue, fetchIssues } from "./api";
import { IssuesProvider } from "./views";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new IssuesProvider();
  vscode.window.registerTreeDataProvider("uxpulse.issues", provider);

  const refreshCmd = vscode.commands.registerCommand("uxpulse.refresh", async () => {
    try {
      const issues = await fetchIssues();
      provider.setIssues(issues);
      vscode.window.showInformationMessage(`UXPulse loaded ${issues.length} issues`);
    } catch (err) {
      vscode.window.showErrorMessage(`UXPulse refresh failed: ${toErrorMessage(err)}`);
    }
  });

  const openIssueCmd = vscode.commands.registerCommand("uxpulse.openIssue", async (key: string) => {
    try {
      const issue = await fetchIssue(key);
      const panel = vscode.window.createWebviewPanel(
        "uxpulse.issue",
        `UXPulse: ${issue.title}`,
        vscode.ViewColumn.One,
        { enableScripts: false, enableCommandUris: true }
      );

      const openSourceArg = encodeURIComponent(JSON.stringify([issue.source ?? ""]));
      panel.webview.html = [
        "<html><body style='font-family:Segoe UI,sans-serif;padding:16px'>",
        `<h2>${escapeHtml(issue.title)}</h2>`,
        `<p><b>Category:</b> ${escapeHtml(issue.category)} | <b>Impact:</b> ${escapeHtml(issue.impact)} | <b>Confidence:</b> ${Math.round(issue.confidence * 100)}%</p>`,
        `<p><b>Screen:</b> ${escapeHtml(issue.screen ?? "(none)")}<br/><b>Source:</b> ${escapeHtml(issue.source ?? "(none)")}</p>`,
        "<h3>Evidence</h3>",
        `<pre>${escapeHtml(JSON.stringify(issue.evidence, null, 2))}</pre>`,
        "<h3>Recommendation</h3>",
        `<pre>${escapeHtml(JSON.stringify(issue.recommendation, null, 2))}</pre>`,
        `<p><a href='command:uxpulse.openSource?${openSourceArg}'>Open Source File</a></p>`,
        "</body></html>",
      ].join("");
    } catch (err) {
      vscode.window.showErrorMessage(`Open issue failed: ${toErrorMessage(err)}`);
    }
  });

  const openSourceCmd = vscode.commands.registerCommand("uxpulse.openSource", async (source: string) => {
    if (!source) {
      vscode.window.showWarningMessage("This issue does not contain a source path.");
      return;
    }

    const absPath = resolveSourcePath(source);
    try {
      const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
      await vscode.window.showTextDocument(doc, { preview: true });
    } catch {
      vscode.window.showErrorMessage(`Could not open file: ${absPath}`);
    }
  });

  context.subscriptions.push(refreshCmd, openIssueCmd, openSourceCmd);
  void vscode.commands.executeCommand("uxpulse.refresh");
}

export function deactivate(): void {}

function resolveSourcePath(source: string): string {
  if (path.isAbsolute(source)) {
    return source;
  }
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? "";
  return path.resolve(root, source);
}

function escapeHtml(input: string): string {
  return input.replace(/[&<>"']/g, (c) => {
    const map: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    };
    return map[c] ?? c;
  });
}

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  return String(err);
}
