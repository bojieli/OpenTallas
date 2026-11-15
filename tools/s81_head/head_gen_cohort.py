#!/usr/bin/env python3
"""HEAD-BIND-1 11-14: the gen.py rtl die (the HEAD as-built) == the wave-prepared kit cohort, per type.

HEAD kit RTL = prepared/published/<module>.sv (gen.py phys bootstrap + head_start_reset_aliases.patch_rtl, checked by
head_wave_kit_rtl.py export) + the raw private patch at export.  The die-level bind/LATCHECK reads the gen.py rtl
output of the same plan + sidecar; this check proves, token for token (comments and whitespace ignored, as the export
check), that every published wrapper equals alias_patch(gen.py rtl wrapper).  A type with no published wrapper is
listed (UNPUBLISHED), not compared.

    head_gen_cohort.py PREPARED_DIR GEN_DIR [--json OUT]       exit 0 all equal, 1 any mismatch
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "die_plan")]
from head_start_reset_aliases import patch_rtl as alias_patch  # noqa: E402
from head_wave_kit_rtl import tokens  # noqa: E402


def compare(prepared, gen):
    prepared, gen = Path(prepared), Path(gen)
    plan = json.loads((prepared / "source_plan.json").read_text())
    rows = []
    for tn, t in sorted(plan["partition_types"].items()):
        mod = t.get("module")
        if t.get("hard") or not mod:
            continue
        pub, g = prepared / "published" / f"{mod}.sv", gen / f"{mod}.sv"
        if not g.is_file():
            rows.append(dict(type=tn, module=mod, verdict="NO_GEN"))
            continue
        if not pub.is_file():
            rows.append(dict(type=tn, module=mod, verdict="UNPUBLISHED"))
            continue
        want = tokens(alias_patch(g.read_text(), t.get("reset_start_raw_exports", [])))
        have = tokens(pub.read_text())
        if want == have:
            rows.append(dict(type=tn, module=mod, verdict="EQUAL"))
        else:
            i = next((k for k, (x, y) in enumerate(zip(want, have)) if x != y), min(len(want), len(have)))
            rows.append(dict(type=tn, module=mod, verdict="DIFF", first_diff_token=i,
                             gen=" ".join(want[max(0, i - 5):i + 5]), published=" ".join(have[max(0, i - 5):i + 5])))
    bad = [r for r in rows if r["verdict"] in ("DIFF", "NO_GEN")]
    return dict(verdict="FAIL" if bad else "PASS", types=len(rows),
                equal=sum(r["verdict"] == "EQUAL" for r in rows),
                unpublished=[r["type"] for r in rows if r["verdict"] == "UNPUBLISHED"], rows=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prepared")
    ap.add_argument("gen")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rep = compare(a.prepared, a.gen)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    for r in rep["rows"]:
        if r["verdict"] != "EQUAL":
            print("COHORT", r["type"], r["verdict"], r.get("gen", ""), "|", r.get("published", ""))
    print("HEAD_GEN_COHORT", json.dumps({k: v for k, v in rep.items() if k != "rows"}))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
