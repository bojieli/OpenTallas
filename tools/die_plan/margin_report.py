#!/usr/bin/env python3
"""MARGIN-REPORT (FLOW-13, OWNER 12.24c 2026-10-31): price the sign-off margins the nominal gate form dropped.

OWNER 12.24c: SETUP + CLOCK gates run NOMINAL (no spice x1.05 clock factor, no droop data derate, no clock OCV/AOCV,
0 ps core setup uncertainty, optimistic RCX; the 150 ps related-pair gate on DRT+RCX arrivals).  HOLD keeps its margins
(+10 ps kit hold-repair margin, 25 ps SDC hold uncertainty).  This tool re-times one routed design (core mode) or one
die clock proof (die-clock mode) twice -- NOMINAL (gate form) and MARGINS (every pre-12.24c margin restored) -- and
reports what the margins cost, as INFORMATION (never a gate).  The margin values are explicit here, so the report does
not depend on the nominal-default switches of die_sta_related / signoff.

CORE MODE (routed DB):
    margin_report.py core (--run-dir RUN | --base RESULTS_BASE) --die DIE [--kit KIT] [--sdc SDC] [--out DIR]
                     [--host intel2|local] [--emit-only] [--memory 16g] [--clock-stages 6] [--tsv PATH]
  Loads <base>/6_final.odb (+ 6_final.spef; 5_route.odb -> OpenRCX re-extraction, as signoff.py), the exact corner
  liberty of the kit config.mk (signoff.py EXACT_TIMING_LIBRARIES_TCL) and the kit SDC (signoff.discover), then in ONE
  OpenSTA session per corner (TT setup, FF hold; docker ORFS image, memory-capped) times:
    NOMINAL  setup uncertainty 0 (intra-clock and every SDC inter-clock -setup pair), no derate
    MARGINS  setup uncertainty 60 ps (SDC inter-clock seam pairs: 30 ps = half per side, COORD 16:58), plus
             - spice clock factor  die_sta_related SPICE_CLOCK_CAL (BUFx24: TT 1.0485, FF 1.0552) on clock cells+nets
             - clock OCV           flat equivalent of the approved AOCV table clk_aocv_table_g021.json: cell late/early =
                                   1 +/- (3 sigma_r(N)/mu_cell + g d/2) of class --ocv-class (A) at N = --clock-stages
                                   stages and d = die bbox diagonal (6_final.def DIEAREA, or --clock-extent-um); clock
                                   nets late/early = the table's net_flat (1.03 / 0.97).  Multiplied with the spice
                                   factor.  OpenSTA CRPR removes the common-path share, so the flat factor acts on the
                                   non-common branches only.  APPROXIMATION: one depth N for every branch (the table
                                   is per-branch depth/distance); smaller N = larger derate.  Clock droop: shared rule
                                   (12.4a b1), 0 inside one core = one PDN region, so no clock droop term.
             - data droop          data_droop.py DEFAULT / die_ci_margins.json class fractions, TT setup only: every
                                   data cell late x(1 + logic) = 1.10, data nets late x(1 + wire) = 1.05.  All cells
                                   take the logic fraction (repeaters would take 1.05: conservative).
    HOLD (both runs)  set_clock_uncertainty -hold 25 on all clocks (12.24c: hold unchanged); SDC inter-clock hold
             pairs stay as the SDC sets them.  The MARGINS FF session also carries the FF clock factor x OCV (hold has
             no data droop: setup only).  Hold is the raw kit-SDC hold (signoff.py hold_ff_sdc form, without the
             standard boundary-hold overlay).
  min_period_ps = period - margins TT setup WNS (first order: exact for a fixed uncertainty shift; derates scale with
  path delay, so a shorter period does not change them).
  --host H (default intel2): ships this tool + its readers to H:/tmp and runs it there (--host local on H); docker
  `--memory`; the JSON lands next to the run (<kit or base>/margin_report/margin_report.json) and the TSV row is
  appended HERE.  --emit-only writes the Tcl (+ cmd.sh) and stops.

DIE-CLOCK MODE (die_sta_related proof):
    margin_report.py die-clock --die DIE [--tsv PATH] [--die-sta PATH] -- PROOF --plan PLAN --out OUT [owner args]
  Runs die_sta_related twice: as given (nominal; --out OUT/nominal) and with margins (--out OUT/margins; the caller's
  margin flags replaced by --margin-policy legacy (when the script has it) --clock-cal spice --clock-ocv table
  --clock-droop shared --data-droop class).  When the script predates --margin-policy, the nominal run strips the
  caller's margin flags and passes --clock-cal none --clock-ocv none --data-droop none.  Reports the worst related-pair
  TT setup / FF hold margins over the gate classes (intra, seam, landed) of both runs, the gate verdicts as
  die_sta_related computes them, and min period = 833 - worst TT setup slack (margins).

TSV (~/coord/lanes/MARGIN-REPORT-<die>.tsv unless --tsv; header on a new file; this tool never commits it):
  date design db_path mode nominal_setup_wns nominal_hold_wns margins_setup_wns margins_hold_wns margins_pass
  min_period_ps notes
"""
import argparse
import ast
import concurrent.futures as cf
import datetime
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tarfile
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clk_aocv as CA  # noqa: E402
import data_droop as DD  # noqa: E402
import signoff as SO  # noqa: E402

RULE = "OWNER 12.24c (2026-10-31)"
PERIOD_PS = 833.0
UNC_SETUP_MARGIN_PS = 60.0       # pre-12.24c core setup uncertainty (AGENTS.md 60 / 25 ps policy)
UNC_SETUP_NOMINAL_PS = 0.0       # 12.24c gate form
UNC_HOLD_PS = 25.0               # hold unchanged by 12.24c, both runs
SEAM_SETUP_FRACTION = 0.5        # SDC inter-clock seam pairs carry half per side (COORD 16:58)
SPICE_CLOCK_CAL_FALLBACK = {"TT": 1.0485, "FF": 1.0552}
AOCV_TABLE = HERE / "clk_aocv_table_g021.json"
DEFAULT_CLOCK_STAGES = 6
IMAGE = "openroad/orfs:asap7lock"
TSV_COLS = ("date", "design", "db_path", "mode", "nominal_setup_wns", "nominal_hold_wns", "margins_setup_wns",
            "margins_hold_wns", "margins_pass", "min_period_ps", "notes")
BUNDLE = ("margin_report.py", "signoff.py", "data_droop.py", "clk_aocv.py", "die_sta_related.py", "die_ci_margins.json",
          "clk_aocv_table_g021.json")
SSH = "ssh -o ControlPath=none -o BatchMode=yes"


# ---------------------------------------------------------------------------------------------------- margin values
def spice_clock_cal(path=HERE / "die_sta_related.py"):
    """SPICE_CLOCK_CAL of die_sta_related (read from its source: no import chain); fallback the 12.15 b values."""
    try:
        m = re.search(r"^SPICE_CLOCK_CAL\s*=\s*(\{[^}\n]*\})", Path(path).read_text(), re.M)
        if m:
            return {k: float(v) for k, v in ast.literal_eval(m.group(1)).items()}
    except OSError:
        pass
    return dict(SPICE_CLOCK_CAL_FALLBACK)


def data_droop_fracs(margins_path=None):
    """{corner: {'logic': f, 'wire': f}} of the shared data droop model (die_ci_margins.json, else data_droop.DEFAULT)."""
    m = DD.margins(margins_path)
    return {c: DD.fracs(m, "class", c) for c in ("TT", "FF")}


def def_extent_um(def_path):
    """die bbox diagonal (um) from the DEF header (UNITS DISTANCE MICRONS + DIEAREA), None when unreadable."""
    try:
        units, pts = None, None
        with open(def_path, errors="replace") as f:
            for i, line in enumerate(f):
                if units is None:
                    m = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", line)
                    if m:
                        units = float(m.group(1))
                if "DIEAREA" in line:
                    pts = [(float(a), float(b)) for a, b in re.findall(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)", line)]
                    break
                if i > 5000:
                    break
        if not units or not pts:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / units
    except OSError:
        return None


def clock_ocv(corner, stages, extent_um, cls="A", table=AOCV_TABLE):
    """flat clock derate equivalent of the approved AOCV table at one branch depth + extent (see module docstring)."""
    T = CA.load(table)
    rnd = CA.random_frac(T, corner, {cls: int(stages)})
    sysf = CA.sys_frac(T, float(extent_um or 0.0))
    late, early = CA.cell_derate(T, corner, {cls: int(stages)}, float(extent_um or 0.0))
    return dict(cls=cls, stages=int(stages), extent_um=round(float(extent_um or 0.0), 1), random_frac=round(rnd, 5),
                sys_frac=round(sysf, 5), g_per_mm=T["systematic"]["g_per_mm"], cell_late=late, cell_early=early,
                net_late=T["net_flat"]["late"], net_early=T["net_flat"]["early"], table=Path(table).name)


def margin_set(corner, stages=DEFAULT_CLOCK_STAGES, extent_um=None, cls="A", margins_path=None, table=AOCV_TABLE):
    """every margin of the MARGINS run at corner: dict with the derate factors actually emitted."""
    k = spice_clock_cal()[corner]
    o = clock_ocv(corner, stages, extent_um, cls, table)
    dd = data_droop_fracs(margins_path)[corner] if corner == "TT" else {"logic": 0.0, "wire": 0.0}
    return dict(corner=corner, unc_setup_ps=UNC_SETUP_MARGIN_PS, unc_hold_ps=UNC_HOLD_PS, spice_clock_cal=k, ocv=o,
                clock_cell_late=round(k * o["cell_late"], 5), clock_cell_early=round(k * o["cell_early"], 5),
                clock_net_late=round(k * o["net_late"], 5), clock_net_early=round(k * o["net_early"], 5),
                data_cell_late=round(1.0 + dd["logic"], 5), data_net_late=round(1.0 + dd["wire"], 5),
                data_droop=dd, clock_droop="shared rule: 0 inside one core (one PDN region)")


# ------------------------------------------------------------------------------------------------------- SDC reading
_UNC_PAIR = re.compile(r"^\s*set_clock_uncertainty\b(?=.*-from)(?=.*-to)(.*)$", re.M)


def sdc_inter_clock_pairs(sdc_text):
    """[(from clock, to clock)] of the SDC's inter-clock -setup uncertainty lines (kept order, unique)."""
    out = []
    for m in _UNC_PAIR.finditer(sdc_text):
        s = m.group(1)
        if "-setup" not in s and "-hold" in s:
            continue
        f = re.search(r"-from\s+\[get_clocks\s+\{?([^\]\}]+?)\}?\s*\]", s)
        t = re.search(r"-to\s+\[get_clocks\s+\{?([^\]\}]+?)\}?\s*\]", s)
        if f and t and (f.group(1).strip(), t.group(1).strip()) not in out:
            out.append((f.group(1).strip(), t.group(1).strip()))
    return out


def sdc_period_ps(sdc_text, default=PERIOD_PS):
    m = re.search(r"create_clock\b[^\n]*-period\s+([0-9.]+)", sdc_text)
    return float(m.group(1)) if m else default


# ------------------------------------------------------------------------------------------------------- Tcl emission
HEAD_TCL = r"""# MARGIN-REPORT @C@ session (tools/die_plan/margin_report.py, @RULE@): NOMINAL then MARGINS on one routed DB
proc mr {k args} { puts "MR $k [join $args { }]" }
proc mr_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
proc mr_timing {tag} {
  mr ${tag}_WNS_MAX [mr_ps [sta::worst_slack_cmd max]]
  mr ${tag}_WNS_MIN [mr_ps [sta::worst_slack_cmd min]]
  mr ${tag}_TNS_MAX [mr_ps [sta::total_negative_slack_cmd max]]
  mr ${tag}_TNS_MIN [mr_ps [sta::total_negative_slack_cmd min]]
  mr ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  mr ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
@TIMING_LIBRARIES@
ot_lib_load @C@ /out/libraries_@c@.json
read_db /base/@ODB@
@PARASITICS@
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
mr CORNER @C@
mr PARASITICS @PARSRC@
mr DESIGN [current_design]
"""


def _unc_tcl(setup_ps, pairs, seam_ps):
    lines = [f"set_clock_uncertainty -setup {setup_ps:g} [all_clocks]"]
    lines += [f"set_clock_uncertainty -from [get_clocks {{{a}}}] -to [get_clocks {{{b}}}] -setup {seam_ps:g}"
              for a, b in pairs]
    lines.append(f"set_clock_uncertainty -hold {UNC_HOLD_PS:g} [all_clocks]")
    return "\n".join(lines) + "\n"


def run_tcl(tag, ms, pairs):
    """the Tcl of one run (NOMINAL: ms None)."""
    if ms is None:
        t = (f"# ==== RUN NOMINAL ({RULE} gate form: setup uncertainty {UNC_SETUP_NOMINAL_PS:g}, no derate) ====\n"
             "unset_timing_derate\n" + _unc_tcl(UNC_SETUP_NOMINAL_PS, pairs, UNC_SETUP_NOMINAL_PS))
    else:
        o = ms["ocv"]
        t = ("# ==== RUN MARGINS (pre-12.24c margins restored, INFORMATION) ====\n"
             "unset_timing_derate\n"
             + _unc_tcl(ms["unc_setup_ps"], pairs, ms["unc_setup_ps"] * SEAM_SETUP_FRACTION)
             + f"# clock: spice factor {ms['spice_clock_cal']} x AOCV-equivalent flat OCV ({o['table']} class "
               f"{o['cls']}, N={o['stages']}, d={o['extent_um']} um: random {o['random_frac']} + sys {o['sys_frac']}; "
               f"nets {o['net_late']}/{o['net_early']}); clock droop 0 (shared, one region)\n"
             f"set_timing_derate -clock -cell_delay -late {ms['clock_cell_late']:.5f}\n"
             f"set_timing_derate -clock -cell_delay -early {ms['clock_cell_early']:.5f}\n"
             f"set_timing_derate -clock -net_delay -late {ms['clock_net_late']:.5f}\n"
             f"set_timing_derate -clock -net_delay -early {ms['clock_net_early']:.5f}\n")
        if ms["data_droop"]["logic"] > 0 or ms["data_droop"]["wire"] > 0:
            t += (f"# data droop (12.4a b2 class fractions, setup only): logic cells x{ms['data_cell_late']:.4f}, "
                  f"nets x{ms['data_net_late']:.4f}\n"
                  f"set_timing_derate -data -cell_delay -late {ms['data_cell_late']:.5f}\n"
                  f"set_timing_derate -data -net_delay -late {ms['data_net_late']:.5f}\n")
    t += (f"mr_timing {tag}\n"
          f"puts \"MR_PATH_BEGIN {tag}_MAX\"\nreport_checks -path_delay max -format full_clock_expanded -digits 2\n"
          f"puts \"MR_PATH_END\"\n"
          f"puts \"MR_PATH_BEGIN {tag}_MIN\"\nreport_checks -path_delay min -format full_clock_expanded -digits 2\n"
          f"puts \"MR_PATH_END\"\n")
    return t


def session_tcl(corner, ms, pairs, odb="6_final.odb", spef=True):
    if spef:
        par, src = "read_spef /base/6_final.spef", "spef"
    else:
        par, src = (f"source {SO.PLAT}/setRC.tcl\nextract_parasitics -ext_model_file {SO.PLAT}/rcx_patterns.rules\n"
                    f"write_spef /out/rcx_{corner.lower()}.spef\nread_spef /out/rcx_{corner.lower()}.spef"), "rcx"
    t = HEAD_TCL
    for k, v in (("@TIMING_LIBRARIES@", SO.EXACT_TIMING_LIBRARIES_TCL), ("@RULE@", RULE), ("@C@", corner.upper()),
                 ("@c@", corner.lower()), ("@ODB@", odb), ("@PARASITICS@", par), ("@PARSRC@", src)):
        t = t.replace(k, v)
    return t + run_tcl("NOMINAL", None, pairs) + run_tcl("MARGINS", ms, pairs) + "unset_timing_derate\nmr DONE 1\n"


# ----------------------------------------------------------------------------------------------------------- parsing
def _num(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def parse_log(text):
    """{'NOMINAL': {wns_max, wns_min, tns_max, tns_min, nviol_max, nviol_min}, 'MARGINS': {...}, 'corner', 'done'}."""
    out = {"NOMINAL": {}, "MARGINS": {}, "corner": None, "done": False, "parasitics": None}
    for m in re.finditer(r"^MR (\S+)(?: (.*))?$", text, re.M):
        k, v = m.group(1), (m.group(2) or "").strip()
        mm = re.match(r"^(NOMINAL|MARGINS)_(WNS|TNS|NVIOL)_(MAX|MIN)$", k)
        if mm:
            out[mm.group(1)][f"{mm.group(2).lower()}_{mm.group(3).lower()}"] = _num(v)
        elif k == "CORNER":
            out["corner"] = v
        elif k == "PARASITICS":
            out["parasitics"] = v
        elif k == "DONE":
            out["done"] = True
    return out


def min_period_ps(period, setup_wns):
    """first-order minimum closing period: period - setup WNS (exact for a fixed-uncertainty clock shift)."""
    return None if setup_wns is None else round(float(period) - float(setup_wns), 2)


def _pass(s, h):
    return s is not None and h is not None and s >= 0 and h >= 0


def core_result(tt, ff, period, meta):
    """JSON record from the parsed TT (setup) and FF (hold) sessions."""
    runs = {}
    for r in ("NOMINAL", "MARGINS"):
        s, h = tt[r].get("wns_max"), ff[r].get("wns_min")
        runs[r.lower()] = dict(setup_wns_ps=s, setup_tns_ps=tt[r].get("tns_max"), setup_viol=tt[r].get("nviol_max"),
                               hold_wns_ps=h, hold_tns_ps=ff[r].get("tns_min"), hold_viol=ff[r].get("nviol_min"),
                               tt_hold_wns_ps_INFO=tt[r].get("wns_min"), ff_setup_wns_ps_INFO=ff[r].get("wns_max"),
                               verdict="PASS" if _pass(s, h) else "FAIL")
    ms = runs["margins"]["setup_wns_ps"]
    return dict(schema="opentallas.margin_report.v1", mode="core", rule=RULE, status="INFORMATION (never a gate)",
                period_ps=period, runs=runs, margin_cost_setup_ps=None if ms is None or
                runs["nominal"]["setup_wns_ps"] is None else round(runs["nominal"]["setup_wns_ps"] - ms, 2),
                min_period_ps=min_period_ps(period, ms),
                min_period_note="first order: period - MARGINS TT setup WNS; exact for a fixed-uncertainty clock "
                                "shift (derates scale with path delay, unchanged by the period)",
                sessions_done=dict(tt=tt.get("done"), ff=ff.get("done")), **meta)


# --------------------------------------------------------------------------------------------------------------- TSV
def tsv_path(die, tsv=None):
    return Path(tsv) if tsv else Path.home() / "coord" / "lanes" / f"MARGIN-REPORT-{die}.tsv"


def _fmt(v):
    if v is None:
        return "NA"
    if isinstance(v, bool):
        return "PASS" if v else "FAIL"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v).replace("\t", " ").replace("\n", " ")


def tsv_row(rec, design, db_path, mode, notes=""):
    n, m = rec["runs"]["nominal"], rec["runs"]["margins"]
    vals = dict(date=datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"), design=design,
                db_path=db_path, mode=mode, nominal_setup_wns=n["setup_wns_ps"], nominal_hold_wns=n["hold_wns_ps"],
                margins_setup_wns=m["setup_wns_ps"], margins_hold_wns=m["hold_wns_ps"],
                margins_pass=m["verdict"], min_period_ps=rec.get("min_period_ps"), notes=notes)
    return "\t".join(_fmt(vals[c]) for c in TSV_COLS)


def append_tsv(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file() or path.stat().st_size == 0
    with open(path, "a") as f:
        if new:
            f.write("\t".join(TSV_COLS) + "\n")
        f.write(row + "\n")
    return path


def core_notes(rec):
    o = (rec.get("margins") or {}).get("TT", {}).get("ocv", {})
    return (f"{RULE} margin cost (INFO); MARGINS = setup unc 60 + spice clk x{(rec.get('margins') or {}).get('TT', {}).get('spice_clock_cal')}"
            f" + clk OCV flat class {o.get('cls')} N={o.get('stages')} d={o.get('extent_um')}um"
            f" + data droop TT logic/net; hold unc 25 both runs; hold = raw kit SDC (no boundary overlay)")


# ------------------------------------------------------------------------------------------------------- core runner
def _docker_cmd(docker, image, memory, name, mounts, tcl):
    vol = " ".join(f"-v {shlex.quote(h)}:/{c}" + ("" if c in ("out", "sdc") else ":ro") for c, h in mounts)
    return (f"{docker} run --rm --memory {memory} --name {name} {vol} {image} {SO.OPENROAD} -no_init -exit {tcl}")


def core_prepare(a):
    base = Path(a.base).resolve() if a.base else SO.find_base(a.run_dir)
    disc = SO.discover(base, kit=a.kit, sdc=a.sdc)
    if not disc.get("sdc"):
        raise SystemExit("margin_report: no SDC (kit constraint.sdc / 6_final.sdc / --sdc)")
    if not disc.get("kit") or not (Path(disc["kit"]) / "config.mk").is_file():
        raise SystemExit("margin_report: exact corner libraries need the kit config.mk (--kit)")
    sdc_text = Path(disc["sdc"]).read_text()
    pairs = sdc_inter_clock_pairs(sdc_text)
    period = sdc_period_ps(sdc_text)
    ext = a.clock_extent_um
    ext_src = "arg"
    if ext is None:
        ext = def_extent_um(base / "6_final.def")
        ext_src = "6_final.def DIEAREA diagonal" if ext is not None else "none (0: no DEF)"
    out = Path(a.out) if a.out else Path(disc["kit"]) / "margin_report"
    out.mkdir(parents=True, exist_ok=True)
    (out / "sdcdir").mkdir(exist_ok=True)
    (out / "sdcdir" / "golden.sdc").write_text(sdc_text)
    ms = {c: margin_set(c, a.clock_stages, ext, a.ocv_class, a.margins) for c in ("TT", "FF")}
    mounts = [("base", str(base)), ("sdc", str(out / "sdcdir")), ("out", str(out)), ("work", disc["kit"]),
              ("work/config.mk", str(Path(disc["kit"]) / "config.mk"))]
    cmds = {}
    for c in ("TT", "FF"):
        (out / f"margin_{c.lower()}.tcl").write_text(
            session_tcl(c, ms[c], pairs, odb=Path(disc["odb"]).name, spef=bool(disc.get("spef"))))
        cmds[c] = _docker_cmd(a.docker, a.image, a.memory, f"mr_{os.getpid()}_{c.lower()}", mounts,
                              f"/out/margin_{c.lower()}.tcl")
        (out / f"cmd_{c.lower()}.sh").write_text(cmds[c] + "\n")
    meta = dict(design=disc.get("design") or base.parent.name, db_path=disc["odb"], spef=disc.get("spef"),
                sdc=disc["sdc"], sdc_source=disc.get("sdc_source"), kit=disc["kit"], out=str(out),
                inter_clock_setup_pairs=[list(p) for p in pairs], clock_extent_um=ext, clock_extent_source=ext_src,
                margins=ms, image=a.image, memory=a.memory,
                ocv_approximation=("flat clock derate = approved AOCV table (" + AOCV_TABLE.name + ") class "
                                   f"{a.ocv_class} at one branch depth N={a.clock_stages} and d = die bbox diagonal, "
                                   "applied to every clock cell (CRPR removes the common part); per-branch depth and "
                                   "distance are not resolved; clock nets keep the table's flat 1.03/0.97"))
    return out, cmds, period, meta


def core_run_local(a):
    out, cmds, period, meta = core_prepare(a)
    if a.emit_only:
        print(json.dumps(dict(emitted=[str(out / f"margin_{c}.tcl") for c in ("tt", "ff")],
                              cmds=cmds, out=str(out))))
        return None

    def go(c):
        with open(out / f"sta_{c.lower()}.log", "w") as lf:
            rc = subprocess.call(cmds[c], shell=True, stdout=lf, stderr=subprocess.STDOUT)
        return c, rc

    with cf.ThreadPoolExecutor(2) as ex:
        rcs = dict(ex.map(go, ("TT", "FF")))
    parsed = {c: parse_log((out / f"sta_{c.lower()}.log").read_text(errors="replace")) for c in ("TT", "FF")}
    rec = core_result(parsed["TT"], parsed["FF"], period, dict(meta, rc=rcs))
    errs = {c: re.findall(r"\[ERROR[^\n]*", (out / f"sta_{c.lower()}.log").read_text(errors="replace"))[:5]
            for c in ("TT", "FF")}
    rec["errors"] = errs
    (out / "margin_report.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("MR_JSON " + json.dumps(rec))
    return rec


def _bundle_bytes():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for n in BUNDLE:
            if (HERE / n).is_file():
                tf.add(HERE / n, arcname=n)
    return buf.getvalue()


def core_run_remote(a, argv):
    rdir = f"/tmp/margin_report_{os.getpid()}"
    fwd = [x for x in argv]
    i = fwd.index("--host") if "--host" in fwd else None
    if i is not None:
        del fwd[i:i + 2]
    fwd = [x for x in fwd if not x.startswith("--host=")]
    remote = (f"mkdir -p {rdir} && tar -xzf - -C {rdir} && python3 {rdir}/margin_report.py "
              + " ".join(shlex.quote(x) for x in fwd) + " --host local --no-tsv; rc=$?; rm -rf " + rdir + "; exit $rc")
    p = subprocess.run(SSH.split() + [a.host, remote], input=_bundle_bytes(), stdout=subprocess.PIPE)
    text = p.stdout.decode(errors="replace")
    sys.stdout.write("".join(l + "\n" for l in text.splitlines()
                             if not l.startswith(("MR_JSON ", "MARGIN-REPORT "))))
    m = re.search(r"^MR_JSON (.*)$", text, re.M)
    if p.returncode != 0 or not m:
        if a.emit_only and p.returncode == 0:
            return None
        raise SystemExit(f"margin_report: remote run on {a.host} failed rc={p.returncode}")
    return json.loads(m.group(1))


def cmd_core(a, argv):
    rec = core_run_local(a) if a.host in ("local", "localhost") else core_run_remote(a, argv)
    if rec is None:
        return 0
    rec["host"] = a.host
    for r in ("nominal", "margins"):
        x = rec["runs"][r]
        print(f"MARGIN-REPORT {rec['design']} {r.upper()}: TT setup WNS {_fmt(x['setup_wns_ps'])} TNS "
              f"{_fmt(x['setup_tns_ps'])} | FF hold WNS {_fmt(x['hold_wns_ps'])} TNS {_fmt(x['hold_tns_ps'])} | "
              f"{x['verdict']}")
    print(f"MARGIN-REPORT {rec['design']}: min period with margins {_fmt(rec['min_period_ps'])} ps "
          f"(period {rec['period_ps']:g}); JSON {a.host}:{rec['out']}/margin_report.json")
    if not a.no_tsv:
        p = append_tsv(tsv_path(a.die, a.tsv), tsv_row(rec, rec["design"], f"{a.host}:{rec['db_path']}", "core",
                                                        core_notes(rec)))
        print(f"MARGIN-REPORT row -> {p}")
    return 0


# --------------------------------------------------------------------------------------------------- die-clock mode
MARGIN_VALUE_FLAGS = ("--clock-cal", "--clock-ocv", "--clock-droop", "--clock-aocv-table", "--clock-ocv-cell-share",
                      "--droop-regions", "--mesh-signoff", "--pair-unc", "--data-droop", "--margin-policy")
LEGACY_EXPLICIT = ["--clock-cal", "spice", "--clock-ocv", "table", "--clock-droop", "shared", "--data-droop", "class"]
NOMINAL_EXPLICIT = ["--clock-cal", "none", "--clock-ocv", "none", "--data-droop", "none"]


def strip_flags(args, flags=MARGIN_VALUE_FLAGS):
    """args without the given value flags ('--f v' and '--f=v'); returns (kept, removed)."""
    kept, removed, i = [], [], 0
    while i < len(args):
        x = args[i]
        if x in flags:
            removed += args[i:i + 2]
            i += 2
            continue
        if x.split("=", 1)[0] in flags and "=" in x:
            removed.append(x)
            i += 1
            continue
        kept.append(x)
        i += 1
    return kept, removed


def set_out(args, out):
    """args with --out replaced (or appended) by out."""
    kept, _ = strip_flags(args, ("--out",))
    return kept + ["--out", str(out)]


def get_out(args):
    for i, x in enumerate(args):
        if x == "--out" and i + 1 < len(args):
            return args[i + 1]
        if x.startswith("--out="):
            return x.split("=", 1)[1]
    return None


def has_margin_policy(script):
    try:
        return "--margin-policy" in Path(script).read_text()
    except OSError:
        return False


def die_clock_argv(args, out, policy_ok):
    """(nominal argv, margins argv, notes) for die_sta_related (script path not included)."""
    notes = []
    if policy_ok:
        nom = set_out(args, Path(out) / "nominal")
    else:
        kept, removed = strip_flags(args)
        nom = set_out(kept + NOMINAL_EXPLICIT, Path(out) / "nominal")
        notes.append("die_sta_related without --margin-policy: nominal run forced " + " ".join(NOMINAL_EXPLICIT)
                     + (f" (dropped {' '.join(removed)})" if removed else ""))
    kept, removed = strip_flags(args)
    mar = kept + (["--margin-policy", "legacy"] if policy_ok else []) + LEGACY_EXPLICIT
    mar = set_out(mar, Path(out) / "margins")
    if any(x.split("=", 1)[0] in ("--pair-unc", "--mesh-signoff") for x in removed):
        notes.append("margins run replaces the caller's --pair-unc/--mesh-signoff with --clock-ocv table")
    return nom, mar, notes


GATE_CLASSES = ("intra", "seam", "landed")


def die_clock_summary(res):
    """worst TT setup / FF hold margin over the gate classes + verdicts from die_sta_related.json."""
    s = res.get("summary") or {}
    setups, holds, verdicts = [], [], {}
    for k in GATE_CLASSES:
        g = s.get(k)
        if not isinstance(g, dict):
            continue
        v = g.get("verdict")
        verdicts[k] = v
        for f in ("tt_setup_ps", "tt_setup_margin_ps"):
            if _num(g.get(f)) is not None:
                setups.append(float(g[f]))
                break
        for f in ("ff_hold_margin_ps", "ff_hold_all_pairs_diag_ps"):
            if _num(g.get(f)) is not None:
                holds.append(float(g[f]))
                break
    ws, wh = (min(setups) if setups else None), (min(holds) if holds else None)
    gated = [v for v in verdicts.values() if v not in (None, "N/A")]
    ok = bool(gated) and all(v == "PASS" for v in gated)
    return dict(setup_wns_ps=ws, hold_wns_ps=wh, class_verdicts=verdicts,
                verdict="PASS" if ok else "FAIL", margin_policy=s.get("margin_policy"))


def cmd_die_clock(a, rest):
    script = Path(a.die_sta or HERE / "die_sta_related.py")
    out = Path(a.out or get_out(rest) or "margin_report_die_clock")
    pol = has_margin_policy(script)
    nom, mar, notes = die_clock_argv(rest, out, pol)
    runs = {}
    for tag, args in (("nominal", nom), ("margins", mar)):
        cmd = [sys.executable, str(script)] + args
        print("MARGIN-REPORT die-clock " + tag + ": " + " ".join(shlex.quote(x) for x in cmd))
        if a.emit_only:
            continue
        rc = subprocess.call(cmd)
        j = out / tag / "die_sta_related.json"
        if not j.is_file():
            raise SystemExit(f"margin_report: die_sta_related {tag} rc={rc}, no {j}")
        runs[tag] = dict(die_clock_summary(json.loads(j.read_text())), rc=rc, json=str(j))
    if a.emit_only:
        return 0
    rec = dict(schema="opentallas.margin_report.v1", mode="die_clock", rule=RULE, status="INFORMATION (never a gate)",
               period_ps=PERIOD_PS, runs=runs, argv=dict(nominal=nom, margins=mar), margin_policy_flag=pol,
               notes=notes, min_period_ps=min_period_ps(PERIOD_PS, runs["margins"]["setup_wns_ps"]),
               min_period_note="833 - worst related-pair TT setup slack (margins)",
               gate_note="verdicts = die_sta_related gate classes (intra/seam/landed) as it computes them")
    (out / "margin_report.json").write_text(json.dumps(rec, indent=1) + "\n")
    for r in ("nominal", "margins"):
        x = runs[r]
        print(f"MARGIN-REPORT die-clock {r.upper()}: worst TT setup {_fmt(x['setup_wns_ps'])} | FF hold "
              f"{_fmt(x['hold_wns_ps'])} | {x['verdict']} {x['class_verdicts']}")
    print(f"MARGIN-REPORT die-clock: min period with margins {_fmt(rec['min_period_ps'])} ps; JSON {out}/margin_report.json")
    if not a.no_tsv:
        proof = rest[0] if rest and not rest[0].startswith("-") else "?"
        p = append_tsv(tsv_path(a.die, a.tsv), tsv_row(rec, a.design or a.die, proof, "die_clock",
                       f"{RULE} margin cost (INFO); margins = " + ("--margin-policy legacy " if pol else "")
                       + " ".join(LEGACY_EXPLICIT) + ("; " + "; ".join(notes) if notes else "")))
        print(f"MARGIN-REPORT row -> {p}")
    return 0


# ---------------------------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rest = []
    if "--" in argv:
        i = argv.index("--")
        argv, rest = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("core", help="routed DB: NOMINAL vs MARGINS OpenSTA re-time")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-dir")
    g.add_argument("--base")
    c.add_argument("--kit")
    c.add_argument("--sdc")
    c.add_argument("--out", help="output dir (default <kit>/margin_report)")
    c.add_argument("--die", required=True)
    c.add_argument("--host", default="intel2", help="fleet host (default intel2) or local")
    c.add_argument("--emit-only", action="store_true")
    c.add_argument("--image", default=IMAGE)
    c.add_argument("--docker", default="docker")
    c.add_argument("--memory", default="16g")
    c.add_argument("--clock-stages", type=int, default=DEFAULT_CLOCK_STAGES,
                   help="branch depth N for the flat AOCV-equivalent clock derate (default 6)")
    c.add_argument("--clock-extent-um", type=float, help="branch extent d (default die bbox diagonal from 6_final.def)")
    c.add_argument("--ocv-class", default="A")
    c.add_argument("--margins", help="die_ci_margins.json (default tools/die_plan/die_ci_margins.json)")
    c.add_argument("--tsv")
    c.add_argument("--no-tsv", action="store_true")
    d = sub.add_parser("die-clock", help="die_sta_related nominal vs margins; its args after --")
    d.add_argument("--die", required=True)
    d.add_argument("--design")
    d.add_argument("--die-sta", help="die_sta_related.py path (default next to this tool)")
    d.add_argument("--out", help="report dir (default the --out of the die_sta_related args)")
    d.add_argument("--emit-only", action="store_true")
    d.add_argument("--tsv")
    d.add_argument("--no-tsv", action="store_true")
    a = ap.parse_args(argv)
    if a.mode == "core":
        return cmd_core(a, argv)
    if not rest:
        raise SystemExit("margin_report die-clock: give the die_sta_related arguments after --")
    return cmd_die_clock(a, rest)


if __name__ == "__main__":
    sys.exit(main())
