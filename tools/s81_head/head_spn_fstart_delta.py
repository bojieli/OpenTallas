#!/usr/bin/env python3
"""DIE-HEAD-77 (COORD 11-06 21:2x (1)): HEAD plan event l48uj on l48ui, hd_spn + hd_spn_end only.

The counted-candidate hd_spn vC kit (DIE-HEAD-76-SPNRST, FSTART per-face reset leaves) and the hd_spn_end kits were
built from the Codex station-closeout prepared dir (plan 1b9d5655..., event 'station_closeout': realized internal
stations + reset bootstrap for these two strips), not from l48ui.  This event makes the plan say what those kits are:

  1. partition_types.hd_spn and .hd_spn_end are taken verbatim from the station-closeout plan (same module, outline,
     pins, buses: asserted; only clock / reset / internal_stations / realize_internal_stations differ);
  2. hd_spn clock.landing_local_resets += the 8 fstart_face_* leaves (tools/die_plan/fstart_reset_leaves.py plan):
     one kept reset relay per FSTART face flop, D = nearest same-depth reset-wavefront relay, 0 added cycles, +8 flops
     (COORD 21:2x (1): fix-only plan event, approved).

No other type, die net, pin, outline, strap or sidecar change.  Both wrappers are regenerated with the l48ui sidecar
and must be byte-identical to the kits' RTL (--expect TYPE=SV, asserted); wave_prepare.json / SHA256SUMS refreshed.

usage: head_spn_fstart_delta.py SRC_PREPARED CLOSEOUT_PREPARED ENTRIES_JSON OUT --republish TOOLS_ROOT
                               [--event l48uj] [--expect hd_spn=PATH.sv ...]
"""
import argparse, hashlib, json, shutil, sys
from pathlib import Path

TYPES = ("hd_spn", "hd_spn_end")
FIXED = ("module", "outline_um", "pins", "buses", "replicas", "macros")  # must be equal between bases when present
ALLOWED = {"clock", "reset", "internal_stations", "realize_internal_stations"}


def J(x):
    return json.dumps(x, sort_keys=True)


def take_types(plan, closeout):
    out = {}
    for t in TYPES:
        A, B = plan["partition_types"][t], closeout["partition_types"][t]
        diff = sorted(k for k in set(A) | set(B) if J(A.get(k)) != J(B.get(k)))
        bad = [k for k in diff if k not in ALLOWED]
        if bad:
            raise SystemExit(f"{t}: closeout differs outside {sorted(ALLOWED)}: {bad}")
        plan["partition_types"][t] = json.loads(J(B))
        out[t] = diff
    return out


def add_leaves(plan, entries):
    L = plan["partition_types"]["hd_spn"]["clock"].setdefault("landing_local_resets", [])
    have = {e["name"] for e in L}
    for e in entries:
        if e["name"] in have:
            raise SystemExit(f"hd_spn: leaf {e['name']} already declared")
        if not e["name"].startswith("fstart_face_") or len(e.get("consumers", [])) != 1:
            raise SystemExit(f"bad entry {e}")
        L.append(dict(name=e["name"], raw=e["raw"], xy_um=list(e["xy_um"]), consumers=list(e["consumers"])))
    return len(entries)


def changed(a, b):
    """the -/+ lines of a line diff a -> b (positions dropped): the kit_rtl transform of a published wrapper"""
    import difflib
    return [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path); ap.add_argument("closeout", type=Path)
    ap.add_argument("entries", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--republish", type=Path, required=True)
    ap.add_argument("--event", default="l48uj")
    ap.add_argument("--expect", action="append", default=[],
                    help="TYPE=KIT.sv[,BASE_KIT.sv]: the kit RTL must equal the new wrapper, or (with BASE_KIT, a kit built "
                         "from the closeout plan) differ from it by exactly the kit_rtl transform that BASE_KIT shows "
                         "against the closeout published wrapper")
    a = ap.parse_args(argv)
    root = a.republish.resolve()
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    import head_cland_stage_delta as D
    import schema
    plan = json.loads((a.src / "source_plan.json").read_text())
    closeout = json.loads((a.closeout / "source_plan.json").read_text())
    entries = json.loads(a.entries.read_text())
    diffs = take_types(plan, closeout)
    n = add_leaves(plan, entries)
    schema.Plan(json.loads(J(plan)))                       # schema validation, fail closed
    old_rec = json.loads((a.src / "wave_prepare.json").read_text())
    if a.out.exists():
        D.writable(a.out); shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out, symlinks=True)
    D.writable(a.out)
    (a.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    D.republish(a.out, root, list(TYPES), a.out / "source_sidecar.json")
    rec = json.loads((a.out / "wave_prepare.json").read_text())
    assert rec["sidecar_sha256"] == old_rec["sidecar_sha256"], "sidecar must not change"
    for t, w in old_rec["published_wrappers"].items():
        if t not in TYPES:
            assert rec["published_wrappers"][t] == w, (t, "wrapper changed")
    checks = {}
    for spec in a.expect:
        t, _, ps = spec.partition("=")
        p, _, base_kit = ps.partition(",")
        mod = plan["partition_types"][t]["module"] + ".sv"
        got = rec["published_wrappers"][t]["sha256"]
        want = hashlib.sha256(Path(p).read_bytes()).hexdigest()
        c = dict(kit_rtl=p, kit_sha256=want, plan_sha256=got, equal=got == want)
        if base_kit and not c["equal"]:
            new_t = changed((a.out / "published" / mod).read_text(), Path(p).read_text())
            base_t = changed((a.closeout / "published" / mod).read_text(), Path(base_kit).read_text())
            c.update(base_kit_rtl=base_kit, kit_transform_lines=len(new_t), equal=new_t == base_t)
        checks[t] = c
    rec[a.event] = dict(event=a.event, tool="tools/s81_head/head_spn_fstart_delta.py", types=list(TYPES),
                        base_prepared=str(a.src), base_prepared_plan_sha256=old_rec["prepared_plan_sha256"],
                        closeout_prepared=str(a.closeout),
                        closeout_plan_sha256=D.digest(a.closeout / "source_plan.json"),
                        taken_keys=diffs, fstart_leaves=n, added_flops=n, data_cycles_added=0, kit_checks=checks)
    (a.out / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")
    sums = a.out / "SHA256SUMS"
    if sums.exists():
        lines = []
        for ln in sums.read_text().splitlines():
            h, _, name = ln.partition("  ")
            p = a.out / name
            lines.append(f"{D.digest(p)}  {name}" if p.is_file() and not p.is_symlink() else ln)
        sums.write_text("\n".join(lines) + "\n")
    print(json.dumps(rec[a.event], indent=1))
    if not all(c["equal"] for c in checks.values()):
        raise SystemExit("kit wrapper mismatch: the plan does not regenerate the built kit RTL")


if __name__ == "__main__":
    main()
