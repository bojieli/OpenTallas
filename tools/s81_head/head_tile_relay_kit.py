#!/usr/bin/env python3
"""Install the reviewed existing-stage corridor layout into a regenerated hd_tile kit.

This changes placement source, never a saved ODB. The caller supplies its reviewed
target table and bank helper. A full post-placement census and fresh reg_spine
assignment remain required before routing.
"""
from pathlib import Path
import argparse
import json
import shutil


def install(kit, targets, banks):
    kit, targets, banks = map(Path, (kit, targets, banks))
    hook = kit / "face_flops.tcl"
    release = kit / "face_flops_release.tcl"
    if not hook.is_file() or not release.is_file() or not (kit / "config.mk").is_file():
        raise ValueError("expected a generated hd_tile kit with face_flops hooks/config.mk")
    rows = [s.split("\t") for s in targets.read_text().splitlines() if s and not s.startswith("#")]
    if not rows or any(len(r) != 3 for r in rows):
        raise ValueError("targets must have exact cell name, x_um, y_um")
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError("duplicate exact cell name in relay targets")
    for _, x, y in rows:
        float(x); float(y)
    here = Path(__file__).resolve().parent
    shutil.copy2(here / "head_tile_relays.tcl", kit / "head_tile_relays.tcl")
    shutil.copy2(here / "head_tile_prepare.tcl", kit / "head_tile_prepare.tcl")
    shutil.copy2(banks, kit / "head_tile_banks.tcl")
    shutil.copy2(targets, kit / "head_tile_relay_targets.tsv")
    begin, end = "# HEAD_TILE_CORRIDOR_BEGIN", "# HEAD_TILE_CORRIDOR_END"
    text = hook.read_text()
    if begin in text:
        start, tail = text.index(begin), text.index(end) + len(end)
        if start and text[start-1] == "\n":
            start -= 1
        if text[tail:tail+2] == "\n\n":
            tail += 2
        elif text[tail:tail+1] == "\n":
            tail += 1
        text = text[:start] + text[tail:]
    block = ("\n" + begin + "\n"
             "# After face/landing flops, before the GPL-only ring-bank reservation is created.\n"
             "set ::env(HEAD_TILE_RELAY_TARGETS) /work/head_tile_relay_targets.tsv\n"
             "uplevel #0 {source /work/head_tile_prepare.tcl}\n"
             "uplevel #0 {source /work/head_tile_banks.tcl}\n"
             "uplevel #0 {source /work/head_tile_relays.tcl}\n" + end + "\n")
    anchor = "source /work/reserved_banks.tcl"
    if anchor in text:
        text = text.replace(anchor, block + "\n" + anchor, 1)
    else:
        text = text.rstrip() + block
    hook.write_text(text)
    # GP timing repair may upsize FIRM flops. Repack from their CURRENT master
    # widths after resizer and after face/ring release, before DPL checks them.
    rb, re = "# HEAD_TILE_POSTRESIZE_BEGIN", "# HEAD_TILE_POSTRESIZE_END"
    rt = release.read_text()
    if rb in rt:
        a, b = rt.index(rb), rt.index(re) + len(re)
        if a and rt[a-1] == "\n":
            a -= 1
        if rt[b:b+1] == "\n":
            b += 1
        rt = rt[:a] + rt[b:]
    post = ("\n" + rb + "\n"
            "# Account for real post-resizer FF master widths; no logic/cycle change.\n"
            "set ::env(HEAD_TILE_RELAY_TARGETS) /work/head_tile_relay_targets.tsv\n"
            "uplevel #0 {source /work/head_tile_prepare.tcl}\n"
            "uplevel #0 {source /work/head_tile_banks.tcl}\n"
            "uplevel #0 {source /work/head_tile_relays.tcl}\n" + re + "\n")
    release.write_text(rt.rstrip() + post)
    copies = sum("g_export.g_copy" in r[0] or "/export_q" in r[0] for r in rows)
    metadata = dict(targeted_flops=len(rows), existing_relay_flops=len(rows)-copies,
                    parallel_state_copies=copies, added_cycles=0,
                    source_hook="face_flops.tcl: after face/landing placements, before GPL-only ring-bank reservation",
                    postresize_hook="face_flops_release.tcl: current-master repack before DPL",
                    fresh_reg_spine_assignment_required=True,
                    postplacement_fullgraph_and_geometry_required=True,
                    route_qualified=False)
    (kit / "head_tile_corridor.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kit", type=Path)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--banks", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(install(args.kit, args.targets, args.banks), sort_keys=True))
