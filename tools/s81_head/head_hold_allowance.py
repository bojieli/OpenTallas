#!/usr/bin/env python3
"""HEAD-CORE-R18 2026-10-27: per-view, ledgered allowance for the owner 10-25 structural FF hold stop.

COORD RULING HEAD-CORE-R17 (2) (2026-10-27 07:47 PDT): elemA m2/m12 FF hold -102.8/-103.0 ps vs the -100 ps
structural gate is NOT structural (boundary contract -40 + centre-entry tree +25 ps); ~3 HB4 per input register =
owner-allowed data hold buffers (METHODOLOGY 12.4a a1), ledgered.  Conditions: elemA FF insertion inside 202.5+-20, and
no change to the die IO contract or the vclk binding (one shared die model).

The gate itself (tools/orfs_hold_mm.tcl ot_hold_structural_gate) is NOT relaxed: its default limits stay for every
kit.  This tool checks ONE committed allowance JSON against ONE staged ECO dir and only then writes the Tcl dict the
gate reads through OT_HOLD_ALLOWANCE_TCL.  FAIL-CLOSED checks:
  * schema / required fields; ws floor not below -125 ps and endpoint cap not above the default 2000;
  * the kit's DESIGN_NICKNAME and the kit dir name are the ones the allowance names (per view);
  * vclk binding unchanged: config.mk OT_VCLK_TT/FF, constraint.sdc vclk latency and vclk_ff.sdc latency equal the
    allowance values, and constraint.sdc (the die IO contract) has the recorded sha256;
  * insertion condition: the measured per-sink clock-arrival TSV (meas_ck.tcl, RCX basis, corner FF) has the recorded
    sha256 and its recomputed mean lies inside the band (recorded mean must match the recomputation);
  * the allowance names its ledger entry and ruling.
  head_hold_allowance.py ALLOW.json --kit OUT --tsv FF.tsv [--write OUT/hold_allowance.tcl]
prints 'HEAD_HOLD_ALLOWANCE ok id <id> ...' (exit 0) or 'HEAD_HOLD_ALLOWANCE FAIL <why>' (exit 2)."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from head_eco_modes import mk_vars, sdc_vclk_latencies, same  # noqa: E402

SCHEMA = "ot_hold_allowance/1"
REQ = ("schema", "id", "ruling", "ledger", "design_nickname", "kit_dir", "stage", "limits", "binding", "insertion")
FLOOR_MIN = -125.0
DEFAULT_MAX_N = 2000


class Fail(Exception):
    pass


def sha256(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def insertion_stats(tsv: Path):
    """meas_ck.tcl TSV: pin, net, arrival_max_rise, arrival_max_fall, arrival_min_rise, arrival_min_fall (ps).
    Insertion per sink = arrival_max_rise (the R13/R14 convention: sink clock-pin rise arrival)."""
    basis, v = None, []
    for line in tsv.read_text().splitlines():
        if line.startswith("#"):
            basis = basis or line[1:].strip()
            continue
        f = line.split("\t")
        if len(f) < 6:
            continue
        try:
            v.append(float(f[2]))
        except ValueError:
            raise Fail(f"{tsv.name}: non-numeric arrival {f[2]!r} at {f[0]}")
    if not v:
        raise Fail(f"{tsv.name}: no sinks")
    return dict(basis=basis or "", n=len(v), mean=sum(v) / len(v), min=min(v), max=max(v))


def check(allow_p: Path, kit: Path, tsv: Path):
    a = json.loads(allow_p.read_text())
    miss = [k for k in REQ if k not in a]
    if miss:
        raise Fail(f"allowance lacks {miss}")
    if a["schema"] != SCHEMA:
        raise Fail(f"schema {a['schema']!r} != {SCHEMA}")
    if not str(a["ledger"]).strip() or not str(a["ruling"]).strip():
        raise Fail("allowance must name its ledger entry and ruling")
    lim = a["limits"]
    floor, max_n = float(lim["ws_floor_ps"]), int(lim["max_endpoints"])
    if floor < FLOOR_MIN:
        raise Fail(f"ws floor {floor} below {FLOOR_MIN}: that is a structural failure, not an allowance")
    if max_n > DEFAULT_MAX_N:
        raise Fail(f"endpoint cap {max_n} above the default {DEFAULT_MAX_N}")
    classes = list(lim.get("classes", []))
    if any(c not in ("I2R", "R2R", "R2O", "I2O") for c in classes):
        raise Fail(f"unknown path classes {classes}")
    # per view
    cfg = mk_vars((kit / "config.mk").read_text())
    if cfg.get("DESIGN_NICKNAME") != a["design_nickname"]:
        raise Fail(f"kit DESIGN_NICKNAME {cfg.get('DESIGN_NICKNAME')!r} != allowance {a['design_nickname']!r}")
    kd = kit.resolve().name
    if kd != a["kit_dir"] and not kd.startswith(a["kit_dir"] + "."):
        raise Fail(f"kit dir {kd!r} is not the allowance view {a['kit_dir']!r} (or its .eco* stage)")
    # vclk binding / die IO contract unchanged
    b = a["binding"]
    for k, key in (("OT_VCLK_TT", "ot_vclk_tt"), ("OT_VCLK_FF", "ot_vclk_ff")):
        try:
            got = float(cfg.get(k))
        except (TypeError, ValueError):
            raise Fail(f"config.mk {k} missing")
        if not same(got, float(b[key])):
            raise Fail(f"config.mk {k} {got} != allowance {b[key]} (vclk binding changed)")
    con = kit / "constraint.sdc"
    if sha256(con) != b["constraint_sdc_sha256"]:
        raise Fail("constraint.sdc sha256 differs from the allowance (die IO contract changed)")
    tt = sdc_vclk_latencies(con.read_text())
    if len(tt) != 1 or not same(tt[0], float(b["ot_vclk_tt"])):
        raise Fail(f"constraint.sdc vclk latency {tt} != {b['ot_vclk_tt']}")
    vf = kit / "vclk_ff.sdc"
    if vf.is_file():
        ff = sdc_vclk_latencies(vf.read_text())
        if len(ff) != 1 or not same(ff[0], float(b["ot_vclk_ff"])):
            raise Fail(f"vclk_ff.sdc latency {ff} != {b['ot_vclk_ff']}")
    # insertion condition
    ins = a["insertion"]
    if ins.get("corner") != "FF" or ins.get("statistic") != "mean":
        raise Fail("insertion condition must be the FF mean")
    if sha256(tsv) != ins["tsv_sha256"]:
        raise Fail(f"{tsv} sha256 differs from the allowance record")
    st = insertion_stats(tsv)
    if "RCX" not in st["basis"] or "corner FF" not in st["basis"]:
        raise Fail(f"insertion TSV basis {st['basis']!r} is not RCX corner FF")
    lo, hi = map(float, ins["band_ps"])
    if not (lo <= st["mean"] <= hi):
        raise Fail(f"FF insertion mean {st['mean']:.2f} outside {lo}..{hi}: a tree fix, not an allowance")
    if abs(st["mean"] - float(ins["mean_ps"])) > 0.01 or st["n"] != int(ins["n"]):
        raise Fail(f"recorded insertion mean {ins['mean_ps']} / n {ins['n']} != recomputed {st['mean']:.3f} / {st['n']}")
    return a, st, floor, max_n, classes


def tcl_dict(a, floor, max_n, classes):
    def q(s):
        s = str(s)
        if not re.fullmatch(r"[A-Za-z0-9_.:+-]+", s):
            raise Fail(f"unsafe token for Tcl: {s!r}")
        return s
    return ("# GENERATED by tools/s81_head/head_hold_allowance.py -- do not edit\n"
            f"set ::ot_hold_allowance [dict create id {q(a['id'])} nickname {q(a['design_nickname'])} "
            f"stage {q(a['stage'])} ws_floor_ps {floor:g} max_endpoints {max_n} "
            f"classes [list {' '.join(q(c) for c in classes)}]]\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("allowance", type=Path)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--write", type=Path, default=None)
    o = ap.parse_args(argv)
    try:
        a, st, floor, max_n, classes = check(o.allowance, o.kit, o.tsv)
        txt = tcl_dict(a, floor, max_n, classes)
    except (Fail, KeyError, ValueError, OSError) as e:
        print(f"HEAD_HOLD_ALLOWANCE FAIL {type(e).__name__ if not isinstance(e, Fail) else ''}{e}")
        return 2
    if o.write:
        o.write.write_text(txt)
    print(f"HEAD_HOLD_ALLOWANCE ok id {a['id']} nick {a['design_nickname']} stage {a['stage']} floor {floor:g} "
          f"cap {max_n} classes {','.join(classes) or '-'} ff_insertion_mean {st['mean']:.2f} "
          f"({st['min']:.2f}..{st['max']:.2f}, n {st['n']}) band {a['insertion']['band_ps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
