#!/usr/bin/env python3
"""Summarize curl short-flow TSV measurements by profile and object size."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, TextIO


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def rows(stream: TextIO) -> Iterable[tuple[str, str, float, float, float, float]]:
    reader = csv.reader(stream, delimiter="\t")
    for line_number, row in enumerate(reader, 1):
        if not row or row[0].startswith("#"):
            continue
        if len(row) != 7:
            raise ValueError(f"line {line_number}: expected 7 TSV fields, got {len(row)}")
        profile, size, _run, connect, start, total, speed = row
        yield profile, size, float(connect), float(start), float(total), float(speed)


def open_input(path: str | None) -> TextIO:
    if path is None or path == "-":
        return sys.stdin
    return Path(path).open("r", encoding="utf-8", newline="")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read TSV fields: profile, size, run, time_connect, "
            "time_starttransfer, time_total, speed_download."
        )
    )
    parser.add_argument("input", nargs="?", help="TSV file; default is stdin")
    args = parser.parse_args()

    grouped: dict[tuple[str, str], list[tuple[float, float, float, float]]] = defaultdict(list)
    stream = open_input(args.input)
    close_stream = stream is not sys.stdin
    try:
        for profile, size, connect, start, total, speed in rows(stream):
            grouped[(profile, size)].append((connect, start, total, speed))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if close_stream:
            stream.close()

    if not grouped:
        print("error: no measurements", file=sys.stderr)
        return 2

    print(
        "profile\tsize\tn\tconnect_med_ms\tconnect_p95_ms\t"
        "ttfb_med_ms\ttotal_med_ms\ttotal_p95_ms\tmed_mbps"
    )
    for (profile, size), samples in sorted(grouped.items()):
        connects = [sample[0] for sample in samples]
        starts = [sample[1] for sample in samples]
        totals = [sample[2] for sample in samples]
        speeds = [sample[3] for sample in samples]
        print(
            f"{profile}\t{size}\t{len(samples)}\t"
            f"{statistics.median(connects) * 1000:.1f}\t"
            f"{nearest_rank(connects, 0.95) * 1000:.1f}\t"
            f"{statistics.median(starts) * 1000:.1f}\t"
            f"{statistics.median(totals) * 1000:.1f}\t"
            f"{nearest_rank(totals, 0.95) * 1000:.1f}\t"
            f"{statistics.median(speeds) * 8 / 1_000_000:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
