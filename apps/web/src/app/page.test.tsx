import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("identifica o produto e o fluxo principal", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Research Quest" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Envie documentos TXT ou Markdown")).toBeVisible();
    expect(screen.getByText("Receba uma resposta com as fontes")).toBeVisible();
  });
});
