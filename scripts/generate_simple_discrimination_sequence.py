#!/usr/bin/env python3
"""Generate a balanced Simple Discrimination sequence CSV.

The output contains 30 rows total:
- 15 rows of A01,A02
- 15 rows of A02,A01

Rows are randomized and constrained so that no more than 3 identical
rows appear in a row.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter
from typing import Sequence


ROW_TYPES: tuple[tuple[str, str], ...] = (("A01", "A02"), ("A02", "A01"))


def _choose_next_row(
    remaining: Counter,
    current_run_row: tuple[str, str] | None,
    current_run_length: int,
    rng: random.Random,
) -> tuple[str, str]:
    candidates = [row for row in ROW_TYPES if remaining[row] > 0]
    rng.shuffle(candidates)

    for row in candidates:
        if row == current_run_row and current_run_length >= 3:
            continue
        return row

    raise RuntimeError("Unable to build a sequence without exceeding the run-length limit.")


def generate_sequence(seed: int | None = None) -> list[tuple[str, str]]:
    """Generate a randomized 30-row sequence meeting the balance and run limits."""

    rng = random.Random(seed)

    for _ in range(1000):
        remaining: Counter = Counter({ROW_TYPES[0]: 15, ROW_TYPES[1]: 15})
        sequence: list[tuple[str, str]] = []
        current_run_row: tuple[str, str] | None = None
        current_run_length = 0

        try:
            while sum(remaining.values()) > 0:
                row = _choose_next_row(remaining, current_run_row, current_run_length, rng)
                sequence.append(row)
                remaining[row] -= 1

                if row == current_run_row:
                    current_run_length += 1
                else:
                    current_run_row = row
                    current_run_length = 1
        except RuntimeError:
            continue

        return sequence

    raise RuntimeError("Failed to generate a valid sequence after multiple attempts.")


def write_sequence_csv(sequence: Sequence[tuple[str, str]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(sequence)


def validate_sequence(sequence: Sequence[tuple[str, str]]) -> None:
    counts = Counter(sequence)
    if counts[ROW_TYPES[0]] != 15 or counts[ROW_TYPES[1]] != 15:
        raise ValueError(f"Sequence is not balanced: {counts}")

    run_row: tuple[str, str] | None = None
    run_length = 0
    for row in sequence:
        if row == run_row:
            run_length += 1
        else:
            run_row = row
            run_length = 1

        if run_length > 3:
            raise ValueError(f"Sequence contains more than 3 identical rows in a row: {sequence}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a balanced Simple Discrimination sequence CSV"
    )
    parser.add_argument(
        "--output",
        default="Controller/sequences/sequences.csv",
        help="Output CSV path (default: Controller/sequences/sequences.csv)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output",
    )

    args = parser.parse_args()

    sequence = generate_sequence(seed=args.seed)
    validate_sequence(sequence)
    write_sequence_csv(sequence, args.output)

    print(f"Wrote {len(sequence)} rows to {args.output}")
    print("Counts:")
    print(f"  {ROW_TYPES[0][0]},{ROW_TYPES[0][1]}: {sequence.count(ROW_TYPES[0])}")
    print(f"  {ROW_TYPES[1][0]},{ROW_TYPES[1][1]}: {sequence.count(ROW_TYPES[1])}")


if __name__ == "__main__":
    main()