import test from "node:test";
import assert from "node:assert/strict";
import { validateAnswers, formatCost } from "../src/scripts/playground.js";

test("choice validation preserves labels and rejects ambiguous or excessive choices", () => {
  assert.deepEqual(validateAnswers(" billing\r\ntechnical\n\n"), ["billing", "technical"]);
  assert.throws(() => validateAnswers("one\nONE"), /unique/);
  assert.throws(() => validateAnswers("one"), /2–12/);
  assert.throws(() => validateAnswers(Array.from({ length: 13 }, (_, index) => String(index)).join("\n")), /2–12/);
  assert.throws(() => validateAnswers(`${"x".repeat(101)}\nother`), /100/);
});

test("unknown cost stays unknown and small known charges remain visible", () => {
  assert.equal(formatCost(null), "Unknown");
  assert.equal(formatCost(NaN), "Unknown");
  assert.equal(formatCost(0), "$0.000000");
  assert.equal(formatCost(0.00002), "$0.000020");
});
