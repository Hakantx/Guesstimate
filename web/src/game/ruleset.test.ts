import { describe, expect, it } from "vitest";
import { spaceSize, validate } from "./ruleset";

const CLASSIC = { length: 4, alphabet: "123456789", allow_repeats: false };
const REPEATS = { length: 4, alphabet: "12", allow_repeats: true };

describe("spaceSize", () => {
  it("matches the engine on the classic game", () => {
    expect(spaceSize(CLASSIC)).toBe(3024); // 9*8*7*6
  });

  it("is a power when repeats are allowed", () => {
    expect(spaceSize(REPEATS)).toBe(16); // 2^4
  });

  it("matches the 5040 standard variant", () => {
    expect(spaceSize({ length: 4, alphabet: "0123456789", allow_repeats: false }))
      .toBe(5040);
  });
});

describe("validate", () => {
  it("accepts a legal code", () => {
    expect(validate("1234", CLASSIC)).toBeNull();
  });

  it("rejects the wrong length", () => {
    // The original crashed on an empty line; nothing downstream sees a raw
    // string here either.
    expect(validate("", CLASSIC)).toMatch(/4 symbols/);
    expect(validate("12345", CLASSIC)).toMatch(/4 symbols/);
  });

  it("rejects symbols outside the alphabet", () => {
    expect(validate("1230", CLASSIC)).toMatch(/not one of/);
  });

  it("rejects repeats when the ruleset forbids them", () => {
    expect(validate("1123", CLASSIC)).toMatch(/repeated/);
  });

  it("allows repeats when the ruleset permits them", () => {
    expect(validate("1122", REPEATS)).toBeNull();
  });
});
