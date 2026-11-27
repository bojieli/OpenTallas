#!/usr/bin/env python3
"""Prepare declared clock-landing RTL for a private thin bind carrier.

Run after staging the explicit as-built manifest and its table, before
bind --strict --types. The caller supplies the authoritative source base.
Only leaf aliases to the same repository-relative file in that base can be
copied. Ordinary bind and its strict path checks retain their existing rules.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile


def clock_landing_libraries(table):
    """Repository-relative extra libraries for a declared clock-landing table."""
    libs = ("rtl/common/ot_meso_fifo.sv", "rtl/common/ot_dp_clk_landing.sv")
    if table.get("count_aligned"):
        libs += ("rtl/common/ot_dp_clk_landing_ca.sv",)
    return libs


def materialize_clock_libraries(tree, asbuilt, source_base):
    """Copy active landing libraries into the private tree, returning relative paths."""
    tree = Path(tree).resolve(strict=True)
    source_base = Path(source_base).resolve(strict=True)
    if tree.is_relative_to(source_base) or source_base.is_relative_to(tree):
        raise ValueError("private tree and authoritative source must be disjoint")
    asbuilt = Path(asbuilt).resolve(strict=True)
    if not asbuilt.is_relative_to(tree):
        raise ValueError("as-built manifest must be inside the private tree")
    manifest = json.loads(asbuilt.read_text())
    table_name = manifest.get("clock_landing_table")
    if not table_name:
        return []
    base_name = manifest.get("base")
    if base_name is not None and Path(base_name).is_absolute():
        raise ValueError("as-built base must be repository-relative")
    base = (asbuilt.parent / base_name).resolve(strict=True) if base_name is not None else tree
    if not base.is_relative_to(tree):
        raise ValueError("as-built base must be inside the private tree")
    table = Path(table_name)
    if table.is_absolute() or ".." in table.parts:
        raise ValueError("clock-landing table must be relative to the as-built base")
    table = (base / table).resolve(strict=True)
    if not table.is_file() or not table.is_relative_to(base):
        raise ValueError("clock-landing table must resolve inside the as-built base")

    copies = []
    for relative in clock_landing_libraries(json.loads(table.read_text())):
        target = base / relative
        current = target.resolve(strict=True)
        if current.is_relative_to(base) and current.is_file():
            continue
        if not target.is_symlink() or target.parent.resolve(strict=True) != target.parent:
            raise ValueError(f"{relative}: materialization requires a leaf alias in the private tree")
        donor = (source_base / relative).resolve(strict=True)
        if current != donor or not donor.is_file() or not donor.is_relative_to(source_base):
            raise ValueError(f"{relative}: alias does not name the declared source file")
        copies.append((target, donor))

    for target, donor in copies:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as staged:
            tmp = Path(staged.name)
        try:
            shutil.copy2(donor, tmp)
            if not target.is_symlink() or target.resolve(strict=True) != donor:
                raise ValueError(f"{target}: source alias changed during materialization")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
    return [str(target.relative_to(base)) for target, _ in copies]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, type=Path, help="private thin bind carrier")
    parser.add_argument("--asbuilt", required=True, type=Path, help="contained explicit as-built manifest")
    parser.add_argument("--source-base", required=True, type=Path, help="authoritative base for exact file copies")
    args = parser.parse_args(argv)
    try:
        staged = materialize_clock_libraries(args.tree, args.asbuilt, args.source_base)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"clock_landing_libraries_materialized": staged}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
