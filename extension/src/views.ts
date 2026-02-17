import * as vscode from "vscode";

import { Issue } from "./api";

export type NodeKind = "issue" | "detail";

export class IssueNode extends vscode.TreeItem {
  constructor(
    public readonly issue: Issue,
    public readonly kind: NodeKind,
    public readonly detailText?: string
  ) {
    super(
      kind === "issue" ? issue.title : detailText ?? "",
      kind === "issue" ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None
    );

    if (kind === "issue") {
      this.description = `${issue.impact} | ${issue.category} | ${Math.round(issue.confidence * 100)}%`;
      this.contextValue = "uxpulseIssue";
      this.command = {
        command: "uxpulse.openIssue",
        title: "Open Issue Details",
        arguments: [issue.key],
      };
    } else {
      this.contextValue = "uxpulseIssueDetail";
    }
  }
}

export class IssuesProvider implements vscode.TreeDataProvider<IssueNode> {
  private items: Issue[] = [];
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<IssueNode | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  setIssues(issues: Issue[]): void {
    this.items = issues;
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: IssueNode): vscode.TreeItem {
    return element;
  }

  getChildren(element?: IssueNode): Thenable<IssueNode[]> {
    if (!element) {
      return Promise.resolve(this.items.map((issue) => new IssueNode(issue, "issue")));
    }
    if (element.kind === "detail") {
      return Promise.resolve([]);
    }

    const issue = element.issue;
    const evidenceSummary = `Evidence: ${JSON.stringify(issue.evidence)}`;
    const details = [
      `Screen: ${issue.screen ?? "(none)"}`,
      `Source: ${issue.source ?? "(none)"}`,
      evidenceSummary,
    ];
    return Promise.resolve(details.map((line) => new IssueNode(issue, "detail", line)));
  }
}
