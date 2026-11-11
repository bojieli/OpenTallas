#!/usr/bin/env python3
"""DIE-QC-97 FTFR 11-10 plan event (COORD ruling on PLAN-ROUTE-1 finding (4)): re-price ft_fracs on measured cells.

gen_plan.ft_fracs() gave sparse soft partitions a larger share of their M4-M7 tracks for feedthroughs from an estimated
std-cell fill = P.cells x CELL_UM2 0.52 / UTIL / outline.  P.cells were area guesses (~19k for sle_hc1), so dense slice
types read fill 0.02 and the plan granted them 50% of M4-M7 for ft.  Measured kit synth: sle_hc1 381,548 cells /
51,649 um2 std area (0.135 um2 per cell).  gen_plan now takes cells from tools/die_plan/cells.py (measured evidence
first: plan type.cells, then plan_of_record/cells/qc_cells_evidence_1102.json rows whose basis is a measured synth)
at FT_STD_UM2 0.135; types without a measured count keep the old estimate.

This event applies the same rule to an existing plan.  For every type ft_fracs prices (soft, not coll_* except coll_ft*)
with a MEASURED cell count it recomputes fill and the ft share; a type is AFFECTED when the share changes (a crossing
of fill 0.10 or 0.25).  For affected types only it rewrites the two keys ft_fracs writes:
  partition_types[t].ft_track_frac   new share, or the key removed when fill >= 0.25 (G0 default 0.25)
  partition_types[t].note            the ft_fracs fragment "est. std-cell fill F at util U: P% of M4-M7 to ft" replaced
                                     in place by the measured form (marker FTFR-1110), or removed with the key
Nothing else changes; every other type and every other top-level key is byte-identical (json.dumps), which the event
asserts.  Physical-only (track budget of the G0 cut / die_trial models; no kit RTL, verilog_defines, contents, buses,
pins, lanes or latency key is touched - asserted).  It refuses a plan already carrying the marker, a type whose
ft_track_frac is not the ft_fracs one (no matching note fragment), and a plan with nothing to change.
--lower-only keeps only the changes that lower a type's ft share: at 0.135 um2/cell the 0.10 / 0.25 thresholds (set at
CELL_UM2 0.52) read most measured slice types as sparse, so the literal rule also RAISES the ft share of some dense
types (DIE-QC-97 dry run 11-10); COORD picks the form.
    delta_ftfr_1110.py PLAN.json OUT.json [--evidence FILE ...] [--report R.json]
        -> prints {affected, sha256_in, sha256_out}
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_plan as GP  # noqa: E402  (ft_fill / ft_frac_of / ft_note / ft_cells: one rule for generator and event)

MARK = "FTFR-1110"
FRAG = re.compile(r"est\. std-cell fill ([0-9.]+) at util ([0-9.]+): (\d+)% of M4-M7 to ft")
LAYERS = ("M4", "M5", "M6", "M7")
NETLIST_KEYS = ("module", "contents", "verilog_defines", "kit", "hard", "hard_cores", "buses", "ft_slots", "clock",
                "reset", "outline_um", "cells", "landing_base_type")


def priced(tn, t):
    return not (t.get("hard") or (tn.startswith("coll_") and not tn.startswith("coll_ft")))


def per_layer(fr):
    return {L: share(fr) for L in LAYERS}


def share(fr):
    return 0.25 if fr is None else fr


def plan_changes(raw, evidence=None, lower_only=False):
    """-> (changes {type: row}, skipped {type: reason}); rows carry old/new fill, frac, cells, basis.
    lower_only: keep only changes that LOWER the ft share (never grant more ft than the plan has)."""
    pt = raw["partition_types"]
    if any(MARK in (t.get("note") or "") for t in pt.values()):
        raise SystemExit(f"FTFR: plan already carries {MARK} (re-application refused)")
    meas = GP.ft_cells(raw, evidence)
    changes, skipped = {}, {}
    for tn in sorted(pt):
        t = pt[tn]
        if not priced(tn, t) or tn not in meas:
            continue
        cells, basis = meas[tn]
        w, h = t["outline_um"]
        fill = GP.ft_fill(cells, GP.FT_STD_UM2, w, h)
        new = GP.ft_frac_of(fill)
        old = t.get("ft_track_frac")
        frags = FRAG.findall(t.get("note") or "")
        if old is not None and len(frags) != 1:
            skipped[tn] = f"ft_track_frac {old} without exactly one ft_fracs note fragment ({len(frags)})"
            continue
        if old is not None and abs(int(frags[0][2]) / 100 - old) > 1e-9:
            skipped[tn] = f"ft_track_frac {old} != note fragment {frags[0][2]}%"
            continue
        if new == old or (lower_only and share(new) > share(old)):
            continue
        changes[tn] = dict(cells=cells, basis=basis, outline_um=[w, h],
                           old_fill=float(frags[0][0]) if frags else None, new_fill=round(fill, 4),
                           old_frac=old, new_frac=new, old_layers=per_layer(old), new_layers=per_layer(new))
    return changes, skipped


def rewrite_note(note, fill, fr, cells):
    m = list(FRAG.finditer(note or ""))
    if fr is None:
        if not m:
            return note
        s, e = m[0].span()
        head, tail = note[:s], note[e:]
        if head.endswith("; "):
            head = head[:-2]
        elif not head and tail.startswith(";"):
            tail = tail[1:].lstrip(" ")
        return head + tail
    frag = GP.ft_note(fill, fr, cells)
    if not m:
        return ((note or "") + "; " + frag).lstrip("; ")
    s, e = m[0].span()
    return note[:s] + frag + note[e:]


def apply(raw, evidence=None, lower_only=False):
    orig = copy.deepcopy(raw)
    changes, skipped = plan_changes(raw, evidence, lower_only)
    if skipped:
        raise SystemExit(f"FTFR: types with a foreign ft_track_frac (merge by hand): {skipped}")
    if not changes:
        raise SystemExit("FTFR: nothing to change (no measured type crosses fill 0.10 / 0.25)")
    pt = raw["partition_types"]
    for tn, r in changes.items():
        t = pt[tn]
        if r["new_frac"] is None:
            t.pop("ft_track_frac", None)
        else:
            t["ft_track_frac"] = r["new_frac"]
        note = rewrite_note(t.get("note"), r["new_fill"], r["new_frac"], r["cells"])
        if note:
            t["note"] = note
        else:
            t.pop("note", None)
    check(orig, raw, set(changes))
    return raw, changes


def check(orig, new, affected):
    """EQ gate (physical-only): only ft_track_frac / note of affected types differ; netlist keys identical."""
    if set(orig) != set(new):
        raise SystemExit("FTFR: top-level keys changed")
    for k in orig:
        if k != "partition_types" and json.dumps(orig[k], sort_keys=True) != json.dumps(new[k], sort_keys=True):
            raise SystemExit(f"FTFR: top-level key {k} changed")
    po, pn = orig["partition_types"], new["partition_types"]
    if set(po) != set(pn):
        raise SystemExit("FTFR: type set changed")
    for tn in po:
        a, b = po[tn], pn[tn]
        if tn not in affected:
            if json.dumps(a) != json.dumps(b):
                raise SystemExit(f"FTFR: unaffected type {tn} changed")
            continue
        diff = {k for k in set(a) | set(b) if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True)}
        if not diff <= {"ft_track_frac", "note"}:
            raise SystemExit(f"FTFR: {tn} changed keys {sorted(diff)}")
        for k in NETLIST_KEYS:
            if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True):
                raise SystemExit(f"FTFR: {tn} netlist key {k} changed")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--evidence", action="append", default=None)
    p.add_argument("--report")
    p.add_argument("--lower-only", action="store_true",
                   help="apply only changes that lower a type's ft share (no new / larger ft grants)")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    raw, changes = apply(json.loads(src), a.evidence, a.lower_only)
    out = (json.dumps(raw, separators=(",", ":")) + "\n").encode()
    Path(a.output).write_bytes(out)
    rep = {"event": MARK, "sha256_in": hashlib.sha256(src).hexdigest(), "sha256_out": hashlib.sha256(out).hexdigest(),
           "std_um2_per_cell": GP.FT_STD_UM2, "util": GP.UTIL, "lower_only": a.lower_only, "affected": changes}
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({"lower_only": a.lower_only, "affected": sorted(changes), "sha256_in": rep["sha256_in"], "sha256_out": rep["sha256_out"]}))


if __name__ == "__main__":
    main()
