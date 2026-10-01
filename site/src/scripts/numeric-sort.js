function numericCellValue(cell) {
  const rawValue = cell?.dataset.sortValue ?? cell?.textContent ?? "";
  const text = rawValue.replace(/[$,%]/g, "").trim();
  if (!text) return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

export function sortRowsByNumericColumn(rows, columnIndex, direction) {
  const multiplier = direction === "desc" ? -1 : 1;
  return [...rows].sort((leftRow, rightRow) => {
    const leftValue = numericCellValue(leftRow.cells[columnIndex]);
    const rightValue = numericCellValue(rightRow.cells[columnIndex]);
    // Missing values belong last in both directions; ties keep their order.
    if (leftValue === null) return rightValue === null ? 0 : 1;
    if (rightValue === null) return -1;
    return multiplier * (leftValue - rightValue);
  });
}
