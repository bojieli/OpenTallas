#!/usr/bin/env python3
"""Launch path with the macro track-alignment gate (2026-10-03, results/uarch/macro_pin_access_audit_20261003).

A successor of the launch path, not an edit: tools/run_abi3_physical.py and
tools/run_abi3_physical_persistent.py stay byte-identical and are called unchanged.

With ``--macro-track-gate`` (default OFF: without it every argument passes through untouched):

1. before launch, every ``--macro-view NAME=DIR`` abstract is audited with
   tools/check_macro_track_alignment.py.  A macro with an allowed R0/MX/MY/R180 orientation in which NO
   origin puts all its pins on track (e.g. the v1 ot_hbm3e_phy_v41x) refuses the launch; mirror-variant
   abstracts are reported (the snap library handles them; the *_v2 sets need nothing);
2. a ``--step-tcl`` hook that is one of the four known defective hooks refuses the launch and names its
   ``*_aligned.tcl`` successor;
3. ``--step-tcl POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl`` is appended, so the run
   fails at floorplan time (OT_MACRO_TRACK_ASSERT) if any placed macro pin centre is off-track.

The gate record (inputs, digests, verdict) is written to ``--macro-track-gate-record`` (default: next to
the launch receipt, or stdout).  With ``--persistent-workdir/--launch-receipt`` the persistent launcher
runs the driver; otherwise the driver runs directly.

    tools/run_abi3_physical_aligned.py --macro-track-gate [--persistent-workdir D --launch-receipt R] <driver args>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_macro_track_alignment as cmta  # noqa: E402

ASSERT_HOOK = "physical/common/ot_macro_track_assert_hook.tcl"
DEFECTIVE_HOOKS = {
    "physical/abi3/w10_wake_q_place.tcl": "physical/abi3/w10_wake_q_place_aligned.tcl",
    "physical/abi3/w10_wake_column_place.tcl": "physical/abi3/w10_wake_column_place_aligned.tcl",
    "physical/v41x_window_bank4_macro_place.tcl": "physical/v41x_window_bank4_macro_place_aligned.tcl",
    "physical/v41x_attn_bank_post_macro_place.tcl": "physical/v41x_attn_bank_post_macro_place_aligned.tcl",
}
MIRRORS = ("R0", "MX", "MY", "R180")


class GateError(Exception):
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _values(argv: list[str], flag: str) -> list[str]:
    out = []
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            out.append(argv[i + 1])
        elif a.startswith(flag + "="):
            out.append(a.split("=", 1)[1])
    return out


def gate(driver_args: list[str]) -> tuple[list[str], dict]:
    rec: dict = {"schema": "opentallas.macro_track_gate.v1", "checker": "tools/check_macro_track_alignment.py",
                 "checker_sha256": sha(ROOT / "tools/check_macro_track_alignment.py"),
                 "assert_hook": ASSERT_HOOK, "assert_hook_sha256": sha(ROOT / ASSERT_HOOK),
                 "snap_library_sha256": sha(ROOT / "physical/common/ot_macro_track_snap.tcl"),
                 "macros": [], "hooks": [], "refusals": [], "warnings": []}
    for spec in _values(driver_args, "--macro-view"):
        name, _, rel = spec.partition("=")
        lef = (ROOT / rel / f"{name}.lef") if not Path(rel).is_absolute() else Path(rel) / f"{name}.lef"
        if not lef.is_file():
            rec["refusals"].append(f"--macro-view {spec}: no {lef}")
            continue
        for m in cmta.parse_lef(lef.read_text()):
            if m["class"] != "BLOCK" or m["name"] != name:
                continue
            a = cmta.audit_macro(m, cmta.ASAP7_TRACKS_NM, cmta.ASAP7_LAYERS, str(lef))
            entry = {"macro": name, "lef": str(lef.relative_to(ROOT)) if lef.is_relative_to(ROOT) else str(lef),
                     "lef_sha256": sha(lef), "allowed_orientations": a["allowed_orientations"], "layers": {}}
            for lay, s in a.get("summary", {}).items():
                entry["layers"][lay] = {"rule_mod_track_nm": s["origin_rule_mod_track_nm"],
                                        "invariant": s["orientation_invariant"],
                                        "no_legal_origin": s["no_legal_origin"]}
                dead = [o for o in s["no_legal_origin"] if o in MIRRORS]
                if dead:
                    rec["refusals"].append(f"{name} ({lef}): {lay} pins have no legal origin in {dead}")
                elif not s["orientation_invariant"]:
                    rec["warnings"].append(f"{name}: {lay} mirror-variant ({s['origin_rule_mod_track_nm']}); "
                                           "place it with physical/common/ot_macro_track_snap.tcl or use the "
                                           "*_v2 abstract")
            rec["macros"].append(entry)
    hooks = _values(driver_args, "--step-tcl")
    for h in hooks:
        point, _, path = h.partition("=")
        rel = str(Path(path).resolve().relative_to(ROOT)) if (ROOT / path).resolve().is_relative_to(ROOT) else path
        rec["hooks"].append({"hook": point, "path": rel})
        if rel in DEFECTIVE_HOOKS:
            rec["refusals"].append(f"{rel} snaps macro origins orientation-blind (pins off-track); "
                                   f"use {DEFECTIVE_HOOKS[rel]}")
        if point == "POST_TAPCELL" and rel != ASSERT_HOOK:
            rec["refusals"].append(f"POST_TAPCELL is taken by {rel}; the gate needs it for {ASSERT_HOOK}")
    rec["verdict"] = "REFUSED" if rec["refusals"] else "PASS"
    if rec["refusals"]:
        return driver_args, rec
    out = list(driver_args)
    if not any(h.startswith("POST_TAPCELL=") for h in hooks):
        out += ["--step-tcl", f"POST_TAPCELL={ASSERT_HOOK}"]
    rec["driver_args"] = out
    return out, rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--macro-track-gate", action="store_true", help="audit abstracts and hooks, add the assert")
    ap.add_argument("--macro-track-gate-record", type=Path, default=None)
    ap.add_argument("--gate-only", action="store_true", help="run the gate and exit (no launch)")
    ap.add_argument("--persistent-workdir", type=Path, default=None)
    ap.add_argument("--launch-receipt", type=Path, default=None)
    a, fwd = ap.parse_known_args(argv)
    if a.macro_track_gate:
        fwd, rec = gate(fwd)
        rec["created_ns"] = time.time_ns()
        text = json.dumps(rec, indent=1, sort_keys=True) + "\n"
        dest = a.macro_track_gate_record or (a.launch_receipt.with_name(a.launch_receipt.name + ".macro_gate.json")
                                              if a.launch_receipt else None)
        if dest:
            dest.write_text(text)
        print(f"MACRO_TRACK_GATE {rec['verdict']} macros={len(rec['macros'])} hooks={len(rec['hooks'])} "
              f"warnings={len(rec['warnings'])}" + (f" record={dest}" if dest else ""), file=sys.stderr)
        for r in rec["refusals"]:
            print(f"MACRO_TRACK_GATE refusal: {r}", file=sys.stderr)
        if rec["verdict"] != "PASS":
            return 3
    if a.gate_only:
        return 0
    if a.persistent_workdir or a.launch_receipt:
        import run_abi3_physical_persistent as persistent
        return persistent.main(["--persistent-workdir", str(a.persistent_workdir),
                                "--launch-receipt", str(a.launch_receipt), *fwd])
    import run_abi3_physical as driver
    return driver.main(fwd)


if __name__ == "__main__":
    sys.exit(main())
