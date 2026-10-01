import assert from "node:assert/strict";
import { test } from "node:test";
import { sortRowsByNumericColumn } from "../src/scripts/numeric-sort.js";

function row(provider, accuracy, cost) {
  return {
    provider,
    cells: [
      { textContent: "1", dataset: {} },
      { textContent: provider, dataset: {} },
      { textContent: `${accuracy}%`, dataset: { sortValue: String(accuracy) } },
      { textContent: `$${cost}`, dataset: { sortValue: cost === null ? "" : String(cost) } },
    ],
  };
}

test("sorts the actual numeric column past rank and provider cells, in both directions", () => {
  const rows = [row("cheap", 60, 1), row("accurate", 90, 3), row("middle", 80, 2)];
  assert.deepEqual(sortRowsByNumericColumn(rows, 2, "desc").map(item => item.provider),
    ["accurate", "middle", "cheap"]);
  assert.deepEqual(sortRowsByNumericColumn(rows, 3, "asc").map(item => item.provider),
    ["cheap", "middle", "accurate"]);
  assert.deepEqual(sortRowsByNumericColumn(rows, 3, "desc").map(item => item.provider),
    ["accurate", "middle", "cheap"]);
  assert.equal(rows[0].provider, "cheap");
});

test("unknown values stay last in both directions and known zero stays priced", () => {
  const rows = [row("unknown", 90, null), row("paid", 90, 2), row("free", 90, 0)];
  assert.deepEqual(sortRowsByNumericColumn(rows, 3, "asc").map(item => item.provider),
    ["free", "paid", "unknown"]);
  assert.deepEqual(sortRowsByNumericColumn(rows, 3, "desc").map(item => item.provider),
    ["paid", "free", "unknown"]);
});

test("uses raw values when displayed prices round to the same number", () => {
  const rows = [row("higher", 90, 0.02024), row("lower", 90, 0.02021)];
  rows.forEach(item => { item.cells[3].textContent = "$0.020"; });
  assert.equal(sortRowsByNumericColumn(rows, 3, "asc")[0].provider, "lower");
});

test("formatted fallback values, missing values, nonfinite values, and ties", () => {
  const values = ["n/a", "$1,000.50", "–", "0", "Infinity", "1,000.50", "", "NaN"];
  const rows = values.map((value, index) => ({ index, cells: [{ textContent: value, dataset: {} }] }));
  assert.deepEqual(sortRowsByNumericColumn(rows, 0, "asc").map(item => item.index),
    [3, 1, 5, 0, 2, 4, 6, 7]);
  assert.deepEqual(sortRowsByNumericColumn(rows, 0, "desc").map(item => item.index),
    [1, 5, 3, 0, 2, 4, 6, 7]);
});
