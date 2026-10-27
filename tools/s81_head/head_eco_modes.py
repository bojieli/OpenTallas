#!/usr/bin/env python3
"""HEAD-CORE-R17 2026-10-27: per-mode timing binding for the s81_head warm post-route ECO (head_post_route_eco.sh).

Same fix as HEAD-CORE-R16 did for head_core_r14_rebuild.sh, here for the ECO (the step that repairs data hold with
HB4 after route):
  scene tc (mode ss) = TT setup under the kit's TT contract (constraint.sdc: vclk source latency OT_VCLK_TT = 250);
  scene BC (mode ff) = FF hold, vclk source latency from vclk_ff.sdc = OT_VCLK_FF = sdc_lint insertion_ff_ps (202.5).
Before R17 the ECO ran a SINGLE-mode two-corner session (CORNERS 'tc bc') whose PRE hook set the FF vclk latency
GLOBALLY, so the TT scene timed hold against 202.5 (phantom TT hold, R16 probe TT -173 vs FF -114 ps) and the hold
repair padded for it.

FAIL-CLOSED: any disagreement between the kit's FF binding sources (config.mk OT_VCLK_FF, sdc_lint.json
insertion_ff_ps, the PRE hook's global latency, an existing vclk_ff.sdc, the sign-off --ff-bound-ps) or a TT contract
that is not OT_VCLK_TT exits 2 and writes nothing.

  head_eco_modes.py OUT [--ff-bound-ps X]
OUT = the staged ECO dir (a copy of the routed kit).  Writes OUT/vclk_ff.sdc, OUT/bind_ff_eco.tcl (the kit PRE hook
with the global vclk latency removed), appends the per-mode block to OUT/config.mk, writes OUT/eco_modes.json, and
prints 'HEAD_ECO_MODES ok ff_bound_ps <v>' (the value the chain passes to signoff.py)."""
import argparse
import json
import re
import sys
from pathlib import Path

LAT_RE = re.compile(r"^\s*set_clock_latency\s+-source\s+([0-9.+-eE]+)\s+\[get_clocks\s+\{?vclk\}?\]\s*$")
ANY_LAT = re.compile(r"\bset_clock_latency\b")
MARK = "# ---- HEAD-CORE-R17 ECO per-mode binding (head_eco_modes.py)"


class Fail(Exception):
    pass


def mk_vars(text):
    """last assignment wins, like make (export / override export / plain)."""
    v = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*[:?]?=\s*(.*?)\s*$", line)
        if m and not line.lstrip().startswith("#"):
            v[m.group(1)] = m.group(2)
    return v


def num(s, what):
    try:
        return float(s)
    except (TypeError, ValueError):
        raise Fail(f"{what} is not a number: {s!r}")


def same(a, b):
    return abs(a - b) < 1e-6


def sdc_vclk_latencies(text):
    return [float(m.group(1)) for line in text.splitlines() for m in [LAT_RE.match(line)] if m]


def prepare(out: Path, ff_bound=None, write=True):
    cfg_p, lint_p = out / "config.mk", out / "sdc_lint.json"
    for p in (cfg_p, lint_p, out / "constraint.sdc"):
        if not p.is_file():
            raise Fail(f"{p.name} missing in {out}")
    cfg = cfg_p.read_text()
    if MARK in cfg:
        raise Fail("config.mk already carries the R17 per-mode block (never re-stage an ECO dir)")
    v = mk_vars(cfg)
    vff = num(v.get("OT_VCLK_FF"), "config.mk OT_VCLK_FF")
    vtt = num(v.get("OT_VCLK_TT"), "config.mk OT_VCLK_TT")
    lint = json.loads(lint_p.read_text())
    lff = num(lint.get("insertion_ff_ps"), "sdc_lint.json insertion_ff_ps")
    ltt = num(lint.get("insertion_ps"), "sdc_lint.json insertion_ps")
    if not same(vff, lff):
        raise Fail(f"FF binding: config.mk OT_VCLK_FF {vff} != sdc_lint insertion_ff_ps {lff}")
    if not same(vtt, ltt):
        raise Fail(f"TT binding: config.mk OT_VCLK_TT {vtt} != sdc_lint insertion_ps {ltt}")
    if ff_bound is not None and not same(ff_bound, vff):
        raise Fail(f"sign-off --ff-bound-ps {ff_bound} != kit OT_VCLK_FF {vff}")
    tt = sdc_vclk_latencies((out / "constraint.sdc").read_text())
    if len(tt) != 1 or not same(tt[0], vtt):
        raise Fail(f"constraint.sdc vclk source latency {tt} is not exactly one line = OT_VCLK_TT {vtt}")
    # the PRE_GLOBAL_ROUTE hook the routed kit ran (bind_ff_actual.tcl family); its global FF latency is dropped
    pre = v.get("PRE_GLOBAL_ROUTE_TCL", "")
    hook = out / Path(pre).name if pre.startswith("/work/") else None
    if hook is None or not hook.is_file():
        raise Fail(f"PRE_GLOBAL_ROUTE_TCL {pre!r} is not a kit file under /work")
    htext = hook.read_text()
    if "hold_pad_hb4.tcl" not in htext:
        raise Fail(f"{hook.name} lacks the HB4-only hold wrapper (hold_pad_hb4.tcl)")
    # a rebuild hook (bind_ff_r14.tcl) sources the GRT repair_design on unscaled RC; the ECO owns its DRV step itself
    keep, dropped = [], []
    for line in htext.splitlines():
        if LAT_RE.match(line):
            lat = float(LAT_RE.match(line).group(1))
            if not same(lat, vff):
                raise Fail(f"{hook.name} global vclk latency {lat} != OT_VCLK_FF {vff}")
            dropped.append(line)
            continue
        if ANY_LAT.search(line) and not line.lstrip().startswith("#"):
            raise Fail(f"{hook.name} sets another clock latency: {line.strip()!r}")
        if re.match(r"^\s*source\s+/work/head_grt_drv_unscaled\.tcl\s*$", line):
            dropped.append(line)
            continue
        if line.startswith('puts "ACTUAL_FF_BOUND') or line.startswith('puts "R16_FF_BOUND'):
            line = 'puts "R17_ECO_FF_BOUND per mode: ff from vclk_ff.sdc, ss keeps the TT contract"'
        keep.append(line)
    sc = v.get("CORNERS", "")
    mm = v.get("OT_HOLD_MM", "0") == "1"
    if mm:
        if sc.split() != ["tc", "BC"] or v.get("OT_MM_SETUP_CORNER") != "tc":
            raise Fail(f"OT_HOLD_MM=1 kit with CORNERS {sc!r} / OT_MM_SETUP_CORNER {v.get('OT_MM_SETUP_CORNER')!r}"
                       " (need 'tc BC' / tc)")
        old = v.get("OT_MM_FF_SDC", "")
        if old and old != "/work/vclk_ff.sdc":
            raise Fail(f"kit OT_MM_FF_SDC {old!r} is not the generated /work/vclk_ff.sdc")
        if (out / "vclk_ff.sdc").is_file():
            ex = sdc_vclk_latencies((out / "vclk_ff.sdc").read_text())
            if len(ex) != 1 or not same(ex[0], vff):
                raise Fail(f"existing vclk_ff.sdc latency {ex} != OT_VCLK_FF {vff}")
    else:
        if sc.split() not in (["tc", "bc"], ["tc", "BC"]):
            raise Fail(f"single-mode kit CORNERS {sc!r} is not 'tc bc'")
        for k in ("TC_LIB_FILES", "BC_LIB_FILES"):
            if k not in v:
                raise Fail(f"convert: {k} missing in config.mk")
    rec = dict(flow="HEAD-CORE-R17 head_eco_modes.py", ot_vclk_tt=vtt, ot_vclk_ff=vff, insertion_ff_ps=lff,
               kit_mm=mm, kit_corners=sc, hook=hook.name, dropped=dropped, ff_bound_ps=vff)
    if write:
        (out / "vclk_ff.sdc").write_text(
            "# GENERATED by head_eco_modes.py (R17): mode ff vclk latency = OT_VCLK_FF = sdc_lint insertion_ff_ps\n"
            f"set_clock_latency -source {vff:g} [get_clocks vclk]\n")
        (out / "bind_ff_eco.tcl").write_text("\n".join(keep) + "\n")
        with cfg_p.open("a") as f:
            f.write(f"\n{MARK}: scene tc (mode ss) TT setup / scene BC (mode ff) FF hold ----\n"
                    "override export CORNERS = tc BC\n"
                    "override export OT_HOLD_MM = 1\n"
                    "override export OT_MM_SETUP_CORNER = tc\n"
                    "override export OT_MM_FF_SDC = /work/vclk_ff.sdc\n"
                    "override export PRE_GLOBAL_ROUTE_TCL = /work/bind_ff_eco.tcl\n")
        (out / "eco_modes.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--ff-bound-ps", type=float, default=None)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    a = ap.parse_args(argv)
    try:
        rec = prepare(a.out, a.ff_bound_ps, write=not a.check)
    except Fail as e:
        print(f"HEAD_ECO_MODES FAIL {e}")
        return 2
    print(f"HEAD_ECO_MODES ok ff_bound_ps {rec['ff_bound_ps']:g} tt_ps {rec['ot_vclk_tt']:g} kit_mm {int(rec['kit_mm'])}"
          f" dropped {len(rec['dropped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
