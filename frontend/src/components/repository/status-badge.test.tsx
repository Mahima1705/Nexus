import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./status-badge";
import type { RepositoryStatus } from "@/types/repository";

const EXPECTED_LABELS: Record<RepositoryStatus, string> = {
  pending: "Pending",
  cloning: "Cloning",
  extracting: "Extracting",
  indexing: "Indexing",
  ready: "Ready",
  failed: "Failed",
};

describe("StatusBadge", () => {
  it.each(Object.entries(EXPECTED_LABELS))("renders the correct label for status=%s", (status, label) => {
    render(<StatusBadge status={status as RepositoryStatus} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows a spinner icon for in-progress statuses but not for ready", () => {
    const { container: indexingContainer } = render(<StatusBadge status="indexing" />);
    expect(indexingContainer.querySelector("svg.animate-spin")).not.toBeNull();

    const { container: readyContainer } = render(<StatusBadge status="ready" />);
    expect(readyContainer.querySelector("svg.animate-spin")).toBeNull();
  });
});
