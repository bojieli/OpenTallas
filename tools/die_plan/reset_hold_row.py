"""RESET-HOLD row (QC-RSTCNT 11-24, COORD): write the host-independent root stable counter reset.source.hold into a plan.

  reset_hold_row.py IN_PLAN OUT_PLAN (--cycles N | --bind BINDDIR --top TOP.sv [--margin M] [--round R]) [--report J]

The counter (reset_tree.hold_spec: ot_dp_lockq after u_rst_root, qualifier tied) delays every partition release by
N + LOCKQ_EXTRA running clocks, so the die holds every core reset that long whatever the host does.  --bind derives N
from the measured need of a bind of the SAME wavefront (reset_hold_check: the need does not move with the counter, the
shift is uniform): N = ceil((need + margin - LOCKQ_EXTRA) / round) * round, so each compose regenerates the count from
its final wavefront.  The root type's published collector_tree is republished (retap --republish-reset on that type
only); the other types' trees do not change.  Refused: a plan with a PLL lock (raise reset.source.lock.stable_cycles),
a root type with more than one part (the shift would not be uniform), a non-uniform resulting shift.
Run from a tree / launch root (imports tools/die_plan)."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402


def cycles_from_need(need, margin=32, rnd=32):
    return max(1, int(math.ceil((need + margin - RT.LOCKQ_EXTRA) / rnd)) * rnd)


def apply(old, path, n, note=""):
    """-> (new raw, report) with reset.source.hold = n and the root type's collector_tree republished."""
    import retap
    s0 = (old.get("reset") or {}).get("source") or {}
    if s0.get("lock"):
        raise SystemExit("REFUSE: plan has a PLL lock (reset.source.lock): raise lock.stable_cycles instead")
    P0 = schema.Plan(copy.deepcopy(old), path)
    if not RT.wavefront(P0):
        raise SystemExit("REFUSE: reset.release is not wavefront")
    sol = RT.wf_solve(P0)
    rtype = sol["root_type"]
    parts = sorted(p for p, v in P0.parts.items() if v["type"] == rtype)
    if parts != [sol["root"]]:
        raise SystemExit(f"REFUSE: root type {rtype} has parts {parts}: every part of it would add the counter "
                         "(non-uniform shift); split the root part into its own type first")
    new = copy.deepcopy(old)
    new["reset"].setdefault("source", {})["hold"] = {"stable_cycles": int(n), "note": note or (
        f"RESET-HOLD row: root stable counter (ot_dp_lockq, qualifier tied), every release +{n + RT.LOCKQ_EXTRA} clk")}
    rep = retap.repoint(old, new, path, path, [rtype], republish_reset=True)
    P1 = schema.Plan(copy.deepcopy(new), path)
    errs = RT.check_hold(P1)
    if errs:
        raise SystemExit(f"REFUSE: {errs}")
    pub = (new["partition_types"][rtype].get("clock", {}).get("landing_contract", {}) or {}).get("collector_tree")
    if pub is not None and not ((pub.get("lock") or {}).get("tied") and pub["lock"]["stable"] == n):
        raise SystemExit(f"FAIL: republished collector_tree of {rtype} carries lock {pub.get('lock')}")
    W0, W1 = RT.wf_plan(P0), RT.wf_plan(P1)
    shift = sorted({W1["parts"][p]["release"] - W0["parts"][p]["release"] for p in W0["parts"]})
    out = dict(root_type=rtype, root=sol["root"], stable_cycles=int(n), release_shift=shift,
               max_release=[W0["max_release"], W1["max_release"]], retap=rep.get(rtype), uniform=shift == [n + RT.LOCKQ_EXTRA])
    if not out["uniform"]:
        raise SystemExit(f"FAIL: release shift not uniform {shift}")
    return new, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--cycles", type=int)
    ap.add_argument("--bind")
    ap.add_argument("--top")
    ap.add_argument("--margin", type=int, default=32)
    ap.add_argument("--round", type=int, default=32)
    ap.add_argument("--report")
    ap.add_argument("--note", default="")
    a = ap.parse_args(argv)
    need = None
    if a.cycles is None:
        if not (a.bind and a.top):
            ap.error("--cycles N or --bind DIR --top TOP")
        import reset_hold_check as RHC
        sys.setrecursionlimit(10 ** 7)
        rows = RHC.measure(str(Path(a.bind) / "rtl"), a.top, str(Path(a.bind) / "bind_reset.json"), log=lambda *x: None)
        need = RHC.summary(rows)["need"]
        a.cycles = cycles_from_need(need, a.margin, a.round)
    old = json.loads(Path(a.inp).read_text())
    new, rep = apply(old, a.inp, a.cycles, a.note)
    rep.update(need=need, margin=a.margin if need is not None else None)
    txt = json.dumps(new, indent=1) + "\n"
    Path(a.out).write_text(txt)
    rep["plan_sha12"] = hashlib.sha256(txt.encode()).hexdigest()[:12]
    print("RESET-HOLD ROW", a.out, rep["plan_sha12"], json.dumps({k: v for k, v in rep.items() if k != "retap"}))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
