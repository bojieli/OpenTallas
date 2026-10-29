#!/usr/bin/env python3
"""kit_modes: ONE TIMING MODE PER CORNER for every die's core kits (SIGNOFF-MODES-1, 2026-10-27).

Shared form of tools/s81_head/head_eco_modes.py (HEAD-CORE-R16/R17; same config.mk / SDC parsing rules): the IO virtual
clock stands for the neighbour's face flop, so TT setup is timed with vclk = OT_VCLK_TT (constraint.sdc, 250) and FF hold
with vclk = OT_VCLK_FF (= sdc_lint insertion_ff_ps, 202.5).  OpenSTA's set_clock_latency -source is per MODE, not per
corner, so a single-mode two-corner session (CORNERS = tc bc) gives BOTH corners the same vclk latency: with the FF
binding (OT_VCLK_CORNER=ff) TT setup/hold are timed against 202.5; without it FF hold is timed against 250.
Found by HEAD-R17's audit and CHECKED by docker probes (lanes/SIGNOFF-MODES.md): KV run_kit_kv.sh MCMM GRT step and
mk_fd4.sh kits (tc+bc both 202.5), KV mk_eco.sh variant m and KV/QC CTS repair (tc+bc both 250), QC mk_hold_qc.sh
(FF-only, 250).

SIGNOFF-MODES-2 (2026-10-27): a flow-step mode violation is reported (KIT_MODES FAIL, exit 2); the run scripts
treat the CTS step as ADVISORY unless OT_KIT_MODES_STRICT=1 (a wrong-frame repair is QoR, the per-corner sign-off
measures the result), the GRT / ECO steps and the sign-off FF bound / binding as fail-closed.

Legal hold-repairing sessions:
  * two corners -> the orfs_hold_mm two-mode session (OT_HOLD_MM=1, CORNERS 'tc BC', OT_MM_SETUP_CORNER tc): scene tc
    (mode ss) = constraint.sdc (vclk TT); scene BC (mode ff) = constraint.sdc + vclk_ff.sdc (vclk FF) -- `stage`;
    OT_VCLK_CORNER must NOT be ff there (it would set the FF latency in mode ss = TT);
  * FF only (CORNERS bc) -> OT_VCLK_CORNER=ff (vclk_corner.tcl binds OT_VCLK_FF);
  * TT only -> OT_VCLK_CORNER unset / tt.
Everything else FAILS CLOSED (exit 2).  Bindings must agree: config.mk OT_VCLK_TT == constraint.sdc vclk latency ==
sdc_lint insertion_ps; OT_VCLK_FF == sdc_lint insertion_ff_ps (== vclk_ff.sdc, == the sign-off --ff-bound-ps).

  kit_modes.py stage KIT [--no-measured-hold]   two-corner kit -> per-mode block (generators, mk_eco m, mk_fd4)
  kit_modes.py check KIT --step cts|grt|eco [--session 'tc bc'|bc|tc] [--vclk-corner ff|tt|''] [--hold-repair]
  kit_modes.py check KIT --step signoff [--ff-bound-ps X]
Prints 'KIT_MODES ok ...' or 'KIT_MODES FAIL <reason>'.

FLOW-HOLD-1 (OWNER 12.19, COORD 10-29 05:52): a NEWLY staged kit repairs FF hold on MEASURED clock arrivals by default
(the FLOW-SHARED-4 measured-FF reference, vclk_measured_hold.tcl, config.mk OT_MM_MEASURED_HOLD = 1) when its FF reference
is 'rebind'; other references ('bound-ff' hard-core latency contract, 'sdc') keep the bound reference and the record
says why.  `stage --measured-hold` still fails closed on a non-rebind kit; `--no-measured-hold` / stage(measured_hold=
False) is the explicit opt-out.  An already staged kit is never changed (signed views stay valid)."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# a kit copy runs as /work/kit_modes.py (no repository parent): REPO is only needed by `stage` (repository copy)
REPO = HERE.parents[1] if len(HERE.parents) > 1 else HERE
# head_eco_modes.py LAT_RE, generalised to any single IO virtual clock name
LAT_RE = re.compile(r"^\s*set_clock_latency\s+-source\s+([0-9.+-eE]+)\s+\[get_clocks\s+\{?([A-Za-z_][\w]*)\}?\]\s*$")
MARK = "# ---- SIGNOFF-MODES-1 per-mode binding (tools/die_plan/kit_modes.py stage)"
MM_FILES = ("orfs_hold_mm.py", "orfs_hold_mm.tcl")
KIT_FILES = ("kit_modes.py", "kit_modes_eco.tcl")
# a repair CALL statement (not `rename` / `proc` wrappers) that is not setup-only
REPAIR_RE = re.compile(r"^[ \t]*(?:log_cmd[ \t]+)?repair_timing(?:_helper)?(?=[ \t]|$)(?![^\n]*-setup\b)", re.M)
SOURCE_RE = re.compile(r"^\s*source\s+(?:\[file join [^\]]+\s+)?/?(?:work/)?([\w.\-]+\.tcl)\]?\s*$", re.M)


class Fail(Exception):
    pass


def mk_vars(text):
    """last assignment wins, like make (export / override export / plain) -- head_eco_modes.mk_vars."""
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


def vclk_lines(text):
    return [(float(m.group(1)), m.group(2)) for line in text.splitlines() for m in [LAT_RE.match(line)] if m]


def corners(s):
    return [c.lower() for c in (s or "").split()]


def binding(kd):
    """the kit's TT / FF vclk binding, cross-checked (fail closed)."""
    kd = Path(kd)
    for f in ("config.mk", "constraint.sdc", "sdc_lint.json"):
        if not (kd / f).is_file():
            raise Fail(f"{f} missing in {kd} (kit predates the per-corner binding: regenerate)")
    v = mk_vars((kd / "config.mk").read_text())
    vtt = num(v.get("OT_VCLK_TT"), "config.mk OT_VCLK_TT")
    vff = num(v.get("OT_VCLK_FF"), "config.mk OT_VCLK_FF")
    lint = json.loads((kd / "sdc_lint.json").read_text())
    tu = float(lint.get("time_unit_ps") or 1.0)
    if lint.get("insertion_ff_ps") is None:
        raise Fail("sdc_lint.json lacks insertion_ff_ps (FF hold would be timed against the TT vclk): regenerate")
    lff = num(lint.get("insertion_ff_ps"), "sdc_lint insertion_ff_ps") / tu
    ltt = num(lint.get("insertion_ps"), "sdc_lint insertion_ps") / tu
    if not same(vff, lff):
        raise Fail(f"FF binding: config.mk OT_VCLK_FF {vff:g} != sdc_lint insertion_ff_ps {lff:g}")
    if not same(vtt, ltt):
        raise Fail(f"TT binding: config.mk OT_VCLK_TT {vtt:g} != sdc_lint insertion_ps {ltt:g}")
    lat = vclk_lines((kd / "constraint.sdc").read_text())
    if len(lat) != 1 or not same(lat[0][0], vtt):
        raise Fail(f"constraint.sdc vclk source latency {lat} is not exactly one line = OT_VCLK_TT {vtt:g}")
    if not 0 < vff <= vtt:
        raise Fail(f"FF vclk {vff:g} not in (0, TT {vtt:g}]")
    return dict(v=v, tt=vtt, ff=vff, vclk=lat[0][1])


def mm_state(kd, b):
    """True = staged two-mode kit (checked), False = plain kit."""
    v = b["v"]
    if v.get("OT_HOLD_MM", "0") != "1":
        return False
    if corners(v.get("CORNERS")) != ["tc", "bc"] or v.get("OT_MM_SETUP_CORNER") != "tc":
        raise Fail(f"OT_HOLD_MM=1 with CORNERS {v.get('CORNERS')!r} / OT_MM_SETUP_CORNER {v.get('OT_MM_SETUP_CORNER')!r}"
                   " (need 'tc BC' / tc)")
    ffs = v.get("OT_MM_FF_SDC", "")
    if ffs != "/work/vclk_ff.sdc":
        raise Fail(f"OT_MM_FF_SDC {ffs!r} is not the staged /work/vclk_ff.sdc")
    p = Path(kd) / "vclk_ff.sdc"
    lat = vclk_lines(p.read_text()) if p.is_file() else []
    if len(lat) != 1 or not same(lat[0][0], b["ff"]) or lat[0][1] != b["vclk"]:
        raise Fail(f"vclk_ff.sdc {lat} != one line OT_VCLK_FF {b['ff']:g} on {b['vclk']}")
    for f in MM_FILES:
        if not (Path(kd) / f).is_file():
            raise Fail(f"two-mode kit lacks {f}")
    return True


MEASURED_HOLD_DEFAULT = True     # FLOW-HOLD-1 (OWNER 12.19): measured clock arrivals for hold repair on new kits
MEASURED_FLAG = "override export OT_MM_MEASURED_HOLD = 1"


def stage_measured_hold(kd, required=False):
    """stage the measured-FF hold reference (vclk_measured_hold.tcl + vclk_ref.py + OT_MM_MEASURED_HOLD) in a two-mode
    kit -> {measured_hold, measured_hold_ref[, measured_hold_reason]}.  Only 'rebind' kits: else Fail when required,
    otherwise the kit keeps its bound reference (recorded)."""
    kd = Path(kd)
    import importlib.util
    sp = importlib.util.spec_from_file_location("vclk_ref", HERE / "vclk_ref.py")   # generators load this file by path
    vclk_ref = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(vclk_ref)
    try:
        ref = vclk_ref.ff_reference(kd)
    except (vclk_ref.RefError, ValueError, OSError) as e:
        raise Fail(f"measured hold: FF reference undecidable ({e})")
    if ref["ref"] != "rebind":
        if required:
            raise Fail(f"measured hold requires rebind reference, got {ref['ref']}")
        return dict(measured_hold=False, measured_hold_ref=ref["ref"],
                    measured_hold_reason=f"FF reference {ref['ref']!r}: measured hold applies to 'rebind' kits only")
    for name in ("vclk_measured_hold.tcl", "vclk_ref.py"):
        shutil.copyfile(HERE / name, kd / name)
    cfg = kd / "config.mk"
    if MEASURED_FLAG not in cfg.read_text():
        with cfg.open("a") as f:
            f.write(MEASURED_FLAG + "\n")
    # An already-staged kit may carry an earlier MM helper.
    for name in MM_FILES:
        shutil.copyfile(REPO / "tools" / name, kd / name)
    return dict(measured_hold=True, measured_hold_ref="rebind")


def stage(kd, write=True, measured_hold=None):
    """append the per-mode block to a two-corner kit (idempotent: an already staged kit is re-checked only).
    measured_hold None = MEASURED_HOLD_DEFAULT (FLOW-HOLD-1): a newly staged 'rebind' kit also gets the measured-FF hold
    reference; True = required (Fail on a non-rebind kit); False = opt-out."""
    kd = Path(kd)
    b = binding(kd)
    if mm_state(kd, b):
        if measured_hold:
            return dict(staged=False, already=True, **{k: b[k] for k in ("tt", "ff", "vclk")},
                        **stage_measured_hold(kd, required=True))
        return dict(staged=False, already=True, **{k: b[k] for k in ("tt", "ff", "vclk")})
    if MARK in (kd / "config.mk").read_text():
        raise Fail("config.mk carries a broken per-mode block")
    if corners(b["v"].get("CORNERS")) != ["tc", "bc"]:
        raise Fail(f"stage: kit CORNERS {b['v'].get('CORNERS')!r} is not a two-corner kit")
    for k in ("TC_LIB_FILES", "BC_LIB_FILES"):
        if k not in b["v"]:
            raise Fail(f"stage: {k} missing in config.mk")
    if write:
        missing = [f for f in MM_FILES if not (REPO / "tools" / f).is_file()]
        if missing:
            raise Fail(f"stage runs from the repository copy (tools/die_plan/kit_modes.py): {missing} not found under "
                       f"{REPO / 'tools'}")
        for f in MM_FILES:
            shutil.copyfile(REPO / "tools" / f, kd / f)
        shutil.copyfile(REPO / "physical/common_flow/macro_cts_cluster.tcl", kd / "macro_cts_cluster.tcl")
        copy_kit_tools(kd)
        (kd / "vclk_ff.sdc").write_text(
            "# GENERATED by tools/die_plan/kit_modes.py: mode ff vclk = OT_VCLK_FF = sdc_lint insertion_ff_ps\n"
            f"set_clock_latency -source {b['ff']:g} [get_clocks {b['vclk']}]\n")
        with (kd / "config.mk").open("a") as f:
            f.write(f"\n{MARK}: scene tc (mode ss) TT setup vclk {b['tt']:g} / scene BC (mode ff) FF hold vclk {b['ff']:g}\n"
                    "override export CORNERS = tc BC\n"
                    "override export OT_HOLD_MM = 1\n"
                    "override export OT_MM_SETUP_CORNER = tc\n"
                    "override export OT_MM_FF_SDC = /work/vclk_ff.sdc\n")
        mm_state(kd, binding(kd))
    r = dict(staged=write, already=False, tt=b["tt"], ff=b["ff"], vclk=b["vclk"])
    mh = MEASURED_HOLD_DEFAULT if measured_hold is None else measured_hold
    if write and mh:
        r.update(stage_measured_hold(kd, required=measured_hold is True))
    elif write:
        r.update(measured_hold=False, measured_hold_reason="opt-out (--no-measured-hold)")
    return r


def copy_kit_tools(kd):
    for f in KIT_FILES:
        if (HERE / f).resolve() != (Path(kd) / f).resolve():
            shutil.copyfile(HERE / f, Path(kd) / f)


def hook_repairs_hold(kd, name, seen=None):
    """a kit Tcl hook (and the kit files it sources) calls repair_timing / repair_timing_helper without -setup."""
    seen = set() if seen is None else seen
    p = Path(kd) / Path(name).name
    if not name or p.name in seen or not p.is_file():
        return False
    seen.add(p.name)
    t = p.read_text()
    if REPAIR_RE.search(t):
        return True
    return any(hook_repairs_hold(kd, s, seen) for s in SOURCE_RE.findall(t))


def cts_repairs_hold(kd, v):
    if v.get("SKIP_CTS_REPAIR_TIMING", "0") != "1":
        return True
    return any(hook_repairs_hold(kd, v.get(k, "")) for k in ("PRE_CTS_TCL", "POST_CTS_TCL"))


def check(kd, step, session=None, vclk_corner="", hold_repair=None, ff_bound=None):
    kd = Path(kd)
    b = binding(kd)
    mm = mm_state(kd, b)
    v = b["v"]
    if ff_bound is not None and not same(float(ff_bound), b["ff"]):
        raise Fail(f"sign-off FF bound {ff_bound:g} != kit OT_VCLK_FF {b['ff']:g}")
    rec = dict(step=step, tt=b["tt"], ff=b["ff"], mm=mm)
    if step == "signoff":
        # Sign-off correctness = its own per-corner sessions (TT vclk OT_VCLK_TT, FF vclk OT_VCLK_FF, checked above and
        # by the FF bound).  A flow step that repaired in the wrong mode costs QoR (over/under-repair the sign-off then
        # measures), not correctness: recorded as an advisory, never a sign-off FAIL (SIGNOFF-MODES-2).
        if not mm and corners(v.get("CORNERS")) == ["tc", "bc"] and cts_repairs_hold(kd, v):
            rec["advisory"] = ("kit CTS repaired hold in ONE mode over tc+bc (FF hold at the TT vclk): QoR only; "
                               "regenerate with setup-only CTS repair or kit_modes.py stage")
        return rec
    cs = corners(session) if session is not None else corners(v.get("CORNERS"))
    if step == "cts":
        hold_repair = cts_repairs_hold(kd, v) if hold_repair is None else hold_repair
    vc = (vclk_corner or "").lower()
    if vc not in ("", "tt", "ff"):
        raise Fail(f"OT_VCLK_CORNER {vclk_corner!r}")
    if mm and cs == ["tc", "bc"]:
        if vc == "ff":
            raise Fail("two-mode session with OT_VCLK_CORNER=ff: the FF latency would land in mode ss (TT)")
    elif cs == ["tc", "bc"]:
        if vc == "ff":
            raise Fail("single-mode tc+bc session with OT_VCLK_CORNER=ff: TT timed against the FF vclk")
        if hold_repair:
            raise Fail("single-mode tc+bc hold repair: FF hold timed against the TT vclk (stage the kit: kit_modes.py stage)")
    elif cs == ["bc"]:
        if hold_repair and vc != "ff":
            raise Fail("FF-only hold repair without OT_VCLK_CORNER=ff: FF hold timed against the TT vclk")
    elif cs == ["tc"]:
        if vc == "ff":
            raise Fail("TT-only session with OT_VCLK_CORNER=ff")
    else:
        raise Fail(f"session corners {cs}")
    rec.update(session=cs, vclk_corner=vc, hold_repair=bool(hold_repair))
    return rec


def signoff_record(kit, ff_bound=None):
    """signoff.py: {verdict, ...}.  A kit without config.mk (die-level / record re-evaluation) is NOT APPLICABLE."""
    if not kit or not (Path(kit) / "config.mk").is_file():
        return dict(verdict="PASS", applicable=False, reason="no kit config.mk")
    v = mk_vars((Path(kit) / "config.mk").read_text())
    if v.get("OT_VCLK_TT") is None and v.get("OT_VCLK_FF") is None:
        # kit predates the per-corner binding (FLOW 10-25): its FF reference is the sign-off ff_vclk policy's job
        # (ff_reference_problem), not this check
        return dict(verdict="PASS", applicable=False, reason="kit predates the OT_VCLK_TT/OT_VCLK_FF binding")
    try:
        return dict(verdict="PASS", applicable=True, **check(kit, "signoff", ff_bound=ff_bound))
    except Fail as e:
        return dict(verdict="FAIL", applicable=True, reason=str(e))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("stage", "check"))
    ap.add_argument("kit", type=Path)
    ap.add_argument("--step", choices=("cts", "grt", "eco", "signoff"))
    ap.add_argument("--session", default=None)
    ap.add_argument("--vclk-corner", default="")
    ap.add_argument("--hold-repair", action="store_true", default=None)
    ap.add_argument("--ff-bound-ps", type=float, default=None)
    ap.add_argument("--measured-hold", action="store_true", default=None,
                    help="REQUIRE the measured FF reference in coupled TT/FF repair (fail closed on a non-rebind kit); "
                         "default since FLOW-HOLD-1: applied to every newly staged rebind kit")
    ap.add_argument("--no-measured-hold", dest="measured_hold", action="store_false",
                    help="opt out of the measured FF hold reference (bound reference)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "stage":
            r = stage(a.kit, measured_hold=a.measured_hold)
        else:
            if not a.step:
                raise Fail("check needs --step")
            r = check(a.kit, a.step, a.session, a.vclk_corner, a.hold_repair, a.ff_bound_ps)
    except Fail as e:
        print(f"KIT_MODES FAIL {e}")
        return 2
    print("KIT_MODES ok " + " ".join(f"{k} {v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
