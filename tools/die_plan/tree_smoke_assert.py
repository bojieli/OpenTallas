#!/usr/bin/env python3
"""tree_smoke_assert: a stale die tree cannot pass the tree smoke (TOOLS-CONVERGE-1116, FABLE-CLOSURE-STRATEGY-0343).

Four trees passed smoke while predating merged fixes: no tt_setup_keep step (r272), an RC table without HEAD x1.13 / KV x1.10 (r276).
This asserts what the tree must carry, from files the kits read:
  tools/die_plan/tt_setup_keep.py exists and gen_phys.py wires it;
  tools/die_plan/rc_signal_scales.json has the die's signal-RC scale (EXPECT_RC) and the core scale.
  tree_smoke_assert.py TREE [--die s81|s81_head|qwen_kvsys|qwen_compute ...]     exit 1 = a stale tree
"""
import argparse
import json
import sys
from pathlib import Path

EXPECT_RC = {"s81": 1.0, "qwen_compute": 1.25, "s81_head": 1.13, "qwen_kvsys": 1.10}
EXPECT_CORE = 1.10
REQUIRED_FILES = ("tools/die_plan/tt_setup_keep.py", "tools/die_plan/tt_setup_repair.tcl")
WIRED = (("tools/die_plan/gen_phys.py", "tt_setup_keep"),)
# FABLE-CLOSURE-1143 r309: S81 serdes types build only from a tree that carries the TXPIPE placement hook (f84ed61a70, main 8b9258eb3ce):
# SERDES_PIPE_CHAINS (gen_phys) names the pipe chains whose placement txl_mid.tcl face mode takes, and its RXNEG entry is the new one
# FABLE-PD-S81-F2s4 (cond 2): a published S81 tree must carry d5bd6d74 (clock_landings accepts no-latch wavefront relays, `_nl`) and
# 55b26f (clock_taps.tcl keeps explicit clock cohorts atomic: ct_group_owned) before the serdes t1/t15 START rows GEN
F2S4_MARKERS = (("tools/die_plan/clock_landings.py", "(?:relay|gate)(?:_nl)?", "d5bd6d74"),
                ("tools/die_plan/clock_taps.tcl", "ct_group_owned", "55b26f"))
HOOK_S81 = (("tools/die_plan/gen_phys.py", '"OT_S81_SERDES_RXNEG": ("u_rxf"'), ("tools/die_plan/gen_phys.py", "SERDES_PIPE_CHAINS"))


def check(tree, dies=None):
    """-> [problem strings]; [] = the tree carries the required fixes"""
    tree = Path(tree)
    out = []
    for rel in REQUIRED_FILES:
        if not (tree / rel).is_file():
            out.append(f"STALE-TREE missing {rel}")
    for rel, word in WIRED:
        try:
            if word not in (tree / rel).read_text(errors="replace"):
                out.append(f"STALE-TREE {rel} does not reference {word}")
        except OSError:
            out.append(f"STALE-TREE missing {rel}")
    if dies is None or "s81" in dies:
        for rel, word in HOOK_S81:
            try:
                if word not in (tree / rel).read_text(errors="replace"):
                    out.append(f"STALE-TREE {rel} lacks the S81 serdes TXPIPE hook ({word}; main 8b9258eb3ce, f84ed61a70)")
            except OSError:
                pass
    if dies is None or "s81" in dies:
        for rel, word, sha in F2S4_MARKERS:
            try:
                if word not in (tree / rel).read_text(errors="replace"):
                    out.append(f"STALE-TREE {rel} lacks {sha} (marker {word!r}): S81 serdes START rows need it before GEN")
            except OSError:
                pass
    try:
        tab = json.loads((tree / "tools/die_plan/rc_signal_scales.json").read_text())
    except (OSError, ValueError) as e:
        return out + [f"STALE-TREE rc_signal_scales.json unreadable: {e}"]
    for die in (dies or sorted(EXPECT_RC)):
        have = (tab.get("type") or {}).get(die)
        if have is None:
            out.append(f"STALE-TREE rc_signal_scales.json has no type entry for {die} (expect x{EXPECT_RC[die]:g})")
        elif abs(float(have) - EXPECT_RC[die]) > 1e-9:
            out.append(f"STALE-TREE rc_signal_scales.json {die} = x{have:g}, expect x{EXPECT_RC[die]:g}")
    if abs(float(tab.get("core", -1)) - EXPECT_CORE) > 1e-9:
        out.append(f"STALE-TREE rc_signal_scales.json core = {tab.get('core')}, expect x{EXPECT_CORE:g}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--die", action="append")
    a = ap.parse_args(argv)
    probs = check(a.tree, a.die)
    for p in probs:
        print(p)
    print("TREE_SMOKE_ASSERT " + ("FAIL" if probs else "OK"))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
