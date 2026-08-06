import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./button";

describe("Button", () => {
  it("renders its children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("fires onClick when clicked", async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Save</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("disables the button and shows a spinner when isLoading", () => {
    render(<Button isLoading>Save</Button>);

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("respects an explicit disabled prop even without isLoading", () => {
    render(<Button disabled>Save</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("with asChild, renders the child element directly instead of wrapping it in a <button>", () => {
    render(
      <Button asChild>
        <a href="/somewhere">Go</a>
      </Button>
    );

    const link = screen.getByRole("link", { name: "Go" });
    expect(link).toBeInTheDocument();
    expect(link.tagName).toBe("A");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    // The button's visual classes should still apply to the rendered <a>.
    expect(link.className).toContain("inline-flex");
  });
});
