import test from "node:test";
import assert from "node:assert/strict";
import { validateAnswers, formatCost, comparisonAvailabilityStatus, trialOfferText } from "../src/scripts/playground.js";

test("choice validation preserves labels and rejects ambiguous or excessive choices", () => {
  assert.deepEqual(validateAnswers(" billing\r\ntechnical\n\n"), ["billing", "technical"]);
  assert.throws(() => validateAnswers("one\nONE"), /unique/);
  assert.throws(() => validateAnswers("one"), /2–12/);
  assert.throws(() => validateAnswers(Array.from({ length: 13 }, (_, index) => String(index)).join("\n")), /2–12/);
  assert.throws(() => validateAnswers(`${"x".repeat(101)}\nother`), /100/);
});

test("trial offer uses configured limits without requiring personal usage", () => {
  assert.equal(trialOfferText({client_budget_usd: 0.5, total_client_calls: 40}), "$0.50 lifetime trial · Up to 40 model calls · No daily refill.");
  assert.equal(trialOfferText({client_budget_usd: 0.25, total_client_calls: 12}), "$0.25 lifetime trial · Up to 12 model calls · No daily refill.");
});

test("availability explains disabled comparisons including partial shared capacity", () => {
  const limits = {calls_used: 0, call_limit: 4, reserved_per_call_usd: 0.025, remaining_usd: 0.1, account: null};
  assert.match(comparisonAvailabilityStatus("live", limits, 4, false), /Sign in/);
  assert.match(comparisonAvailabilityStatus("live", {...limits, calls_used: 4}, 4, false), /currently unavailable/);
  assert.match(comparisonAvailabilityStatus("live", {...limits, calls_used: 1}, 4, true), /Select fewer models/);
  assert.match(comparisonAvailabilityStatus("live", limits, 4, true), /Loading/);
  const account = {calls_used: 38, call_limit: 40, remaining_usd: 0.5};
  assert.match(comparisonAvailabilityStatus("live", {...limits, account}, 4, true), /remaining calls/);
  assert.match(comparisonAvailabilityStatus("live", {...limits, account: {...account, remaining_usd: 0.01}}, 1, true), /budget/);
  assert.equal(comparisonAvailabilityStatus("demo", limits, 1, false), "Ready to compare your decision.");
});

test("unknown cost stays unknown and small known charges remain visible", () => {
  assert.equal(formatCost(null), "Unknown");
  assert.equal(formatCost(NaN), "Unknown");
  assert.equal(formatCost(0), "$0.000000");
  assert.equal(formatCost(0.00002), "$0.000020");
});
