import { describe, expect, it } from "vitest";
import { errorMessage } from "./api";

describe("errorMessage", () => {
  it("formats provider errors", () => {
    expect(
      errorMessage(502, {
        error: { type: "provider_error", message: "Ollama unavailable" }
      })
    ).toBe("provider_error: Ollama unavailable");
  });

  it("formats FastAPI validation errors", () => {
    expect(
      errorMessage(422, {
        detail: [
          {
            loc: ["body", "messages"],
            msg: "Field required"
          }
        ]
      })
    ).toBe("body.messages: Field required");
  });

  it("formats auth detail errors", () => {
    expect(errorMessage(401, { detail: "Invalid API key" })).toBe(
      "Invalid API key"
    );
  });
});
