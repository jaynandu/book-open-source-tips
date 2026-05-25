#!/usr/bin/env python3
"""Find and optionally remove duplicate files in a folder (macOS-friendly)."""

from __future__ import annotations

import argparse
import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        while True:
            chunk = file_obj.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(root: Path) -> list[Path]:
    all_files: list[Path] = []
    for current_dir, _, files in os.walk(root):
        for file_name in files:
            all_files.append(Path(current_dir) / file_name)
    return all_files


def group_duplicates(root: Path) -> DefaultDict[str, list[Path]]:
    size_groups: DefaultDict[int, list[Path]] = defaultdict(list)
    for path in collect_files(root):
        try:
            size_groups[path.stat().st_size].append(path)
        except OSError:
            continue

    hash_groups: DefaultDict[str, list[Path]] = defaultdict(list)
    for _, paths in size_groups.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                hash_groups[sha256_file(path)].append(path)
            except OSError:
                continue

    duplicates: DefaultDict[str, list[Path]] = defaultdict(list)
    for file_hash, paths in hash_groups.items():
        if len(paths) > 1:
            duplicates[file_hash] = sorted(paths)
    return duplicates


def remove_duplicates(duplicates: DefaultDict[str, list[Path]]) -> int:
    removed = 0
    for paths in duplicates.values():
        for duplicate_path in paths[1:]:
            try:
                duplicate_path.unlink()
                removed += 1
            except OSError:
                continue
    return removed


def print_report(duplicates: DefaultDict[str, list[Path]]) -> None:
    if not duplicates:
        print("No duplicate files found.")
        return

    print("Duplicate groups found:")
    for index, paths in enumerate(duplicates.values(), start=1):
        print(f"\nGroup {index} (keeping first file):")
        for file_index, path in enumerate(paths):
            marker = "KEEP" if file_index == 0 else "DUPL"
            print(f"  [{marker}] {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a folder and optionally delete duplicates."
    )
    parser.add_argument("folder", help="Folder to scan for duplicate files")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicates and keep the first file in each duplicate group",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.folder).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        print(f"Folder not found: {root}")
        return 1

    duplicates = group_duplicates(root)
    print_report(duplicates)

    if args.delete and duplicates:
        removed = remove_duplicates(duplicates)
        print(f"\nRemoved {removed} duplicate files.")
    elif args.delete:
        print("\nNothing to delete.")
    else:
        print("\nDry run only. Re-run with --delete to remove duplicate files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
