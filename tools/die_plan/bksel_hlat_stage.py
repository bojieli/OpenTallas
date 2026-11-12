#!/usr/bin/env python3
"""dsdv_bksel_q HLAT as a composer stage (DIE-S81-87 contract):   bksel_hlat_stage.py IN OUT REPORT [--value 0|1]

S81-ARCH-RTL-2 11-12 (DIE-S81-87 / COORD bksel hold, structural): the bk_sel__t2 hard core dsdv_bksel_q gets HLAT 1 =
negative-level lockup latches (ot_s81ph_hlk u_fl_i0 / u_fl_c1 / u_fl_pend / u_fl_o0m) on its measured zero-logic
intra-core hops (vC4r HOLD_SPLIT).  0 cycles: no lane, port or latency row changes (fail-closed: the stage edits ONLY
the declared key).  The kit passes it as VERILOG_TOP_PARAMS HLAT <v> (profiles/bksplit_1108) and sources
bench_hlat/hlat_follow_d.tcl after regional_taps.tcl (latch on its launch flop's clock net, fail-closed legality).
IN = die plan json (json or .gz), OUT = the plan with the key set, REPORT = json (declared keys, edits, cycle delta 0).
Declared keys: hard_params/dsdv_bksel_q/HLAT
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

DECLARED = [r"hard_params/dsdv_bksel_q/HLAT", r"hard_params/dsdv_bksel_q", r"hard_params"]
DECLARED_KEYS = ["hard_params.dsdv_bksel_q.HLAT"]


def load(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b), b


def diff_paths(a, b, path=""):
    if type(a) != type(b):
        yield path
    elif isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                yield f"{path}/{k}"
            else:
                yield from diff_paths(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from diff_paths(x, y, f"{path}/{i}")
    elif a != b:
        yield path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--value", type=int, default=1, choices=[0, 1])
    a = ap.parse_args(argv)
    p0, raw = load(a.inp)
    mods = {c.get("module") for t in p0.get("partition_types", {}).values() for c in (t.get("hard_cores") or [])}
    if "dsdv_bksel_q" not in mods:
        sys.exit("bksel_hlat_stage: no dsdv_bksel_q hard core in the plan (refused)")
    p1 = json.loads(json.dumps(p0))
    hp = p1.setdefault("hard_params", {}).setdefault("dsdv_bksel_q", {})
    old = hp.get("HLAT")
    hp["HLAT"] = a.value
    edits = sorted(set(d.lstrip("/") for d in diff_paths(p0, p1)))
    bad = [e for e in edits if not any(re.fullmatch(r, e) for r in DECLARED)]
    if bad:
        sys.exit(f"bksel_hlat_stage: undeclared edits {bad}")
    txt = json.dumps(p1, indent=1) + "\n"
    out = Path(a.out)
    out.write_bytes(gzip.compress(txt.encode()) if out.suffix == ".gz" else txt.encode())
    rep = dict(stage="bksel_hlat", tool="tools/die_plan/bksel_hlat_stage.py", declared_keys=DECLARED_KEYS,
               edits=edits, old=old, new=a.value, cycle_delta=0, latency_rows_changed=[],
               cores=sorted(c["inst"] for t in p1["partition_types"].values() for c in (t.get("hard_cores") or [])
                            if c.get("module") == "dsdv_bksel_q"),
               in_sha256=hashlib.sha256(raw).hexdigest(), out_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
               kit=dict(VERILOG_TOP_PARAMS_add=f"HLAT {a.value}", post_regional_taps_hook="hlat_follow_d.tcl",
                        rtl="physical/die_plan/s81/cores/legacy/profiles/bksplit_1108/rtl"))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"BKSEL_HLAT_STAGE PASS HLAT {old} -> {a.value} edits {edits} cores {len(rep['cores'])}")


if __name__ == "__main__":
    main()
