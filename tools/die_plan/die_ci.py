#!/usr/bin/env python3
"""Whole-die prototype CI (lane DIE-CI, owner-approved toolchain item 2026-10-24).

Industry teams re-run a whole-die prototype on every change so integration problems show up early, not at G4.  This
is the single entry point that does it for every die plan on one main sha:

    die_ci.py run [--repo .] [--sha SHA] [--out results/die_ci] [--dies a,b] [--mode commit|nightly]
                  [--g2 auto|all|none] [--sta auto|none] [--views tools/die_plan/die_ci_views.json]
                  [--views-root DIR] [--margins tools/die_plan/die_ci_margins.json] [--prev auto|PATH|none] [--jobs N]
    die_ci.py margins --derive [--libdir DIR] [--out tools/die_plan/die_ci_margins.json]    # lib-derived numbers
    die_ci.py stage-views --host H --dest DIR [--views ...]   # (localhost) copy registered views to the run host
    die_ci.py render RUN_DIR                                  # re-write the Markdown from the JSON

Per die (DIES below; hbm_arch B2 joins automatically once its die_plan.json is on main), every gate is PASS / FAIL /
NOT RUN (<reason>) / N/A (<reason>) / CARRIED (<from sha>):

  g0        check.py --completeness, once; G0 = the ERRORs that are not G0C-class (check.py G0C_CHECKS are WARN in
            plain G0, ERROR under --completeness -- exactly check.py's own semantics), G0C = all ERRORs.
  xdie      (a) the PLAN-TOOL5 in-die cross-die rules (check.py summary.xdie_counts: die_io_plan, cut_lines, reach,
            face_tracks, ft_budget) and (b) xdie_io.py on every rack connection table (SYSTEMS) whose die roles have
            plans; a system whose rack macros are not lk_ windows is N/A (xdie_io covers lk_ circuits only).
  g2        g2.py all --worst 5 --run (die probe + the 5 worst partition types; docker, read-only).  In commit mode a
            die whose plan digest and G2 tools are unchanged since the previous run CARRIES the previous G2 result.
  census    G0 census coverage (census_cov via check.py): declared, unmapped instances, dropped bits.
  latency   G0 latency check + the compiler table: a <die>_latency.json in the plan dir whose plan_digest is the
            current plan's (gen.plan_digest) and whose every lane equals gen.latency_table (Plan.lane_latency).
  sta       abstract-model die STA (lane DIE-STA's tools/die_plan/die_sta.py, ILM abstracts validated equal to flat
            on the KV pair) over every partition with a registered routed view (VIEWS registry), on a sub-top of the
            plan's structural die top that keeps only those partitions; seams to partitions without a view get
            STAND-IN budgets (below).  NOT RUN when die_sta.py is not on this sha.  Margins: see MARGINS.

MARGINS (owner item 2): what the open toolchain cannot sign off is added ON TOP of the AGENTS.md policy (1.2 GHz /
833.333 ps, 60 ps setup / 25 ps hold uncertainty, setup at SS, hold at FF), never instead of it; die_ci refuses a
margins file that would relax anything (check_margins).  Each measured seam is reported twice:
  policy    die_sta.py exactly as DIE-STA runs it (the G4 view);
  margined  the same STA with set_timing_derate (OCV x IR late on cells, OCV early; OCV on nets) inside OpenSTA, minus
            the per-seam crosstalk margin (OpenSTA has no SI delay).  The sta gate verdict is on the margined slack.
The numbers and their derivation are in tools/die_plan/die_ci_margins.json (`die_ci.py margins --derive` recomputes
the liberty-derived values from the ASAP7 NLDM libs).

STAND-IN budgets (seams without measured views; never a PASS): the kit SDC contract of gen_phys.sdc composes as
  setup  true slack >= kit_src + kit_dst - (T - I_max - O_max)     hold  true slack >= kit_src + kit_dst + (O_min - I_min)
so a seam with I_max + O_max >= T (ft hop shares 0.92 T + 0.08 T) is contract-backed with slack I+O-T, hold with
insertion_tol (min input delay -tol, min output delay 0).  A functional bus port (0.2 T + 0.2 T) is not contract-backed;
its stand-in is the R2 face-flop estimate T - unc - neighbour skew - clk->q(SS, seam load) - wire - setup(SS).
Both then subtract the margins the kits cannot see (crosstalk + derate on the seam clocks and clk->q): a negative
stand-in is the IO slack the two kits must leave.

Output: OUT/<YYYY-MM-DD>_<sha12>/ die_ci.json (all dies), <die>.json + <die>.md per die, SUMMARY.md, work/ (raw).
"""
import argparse
import concurrent.futures as cf
import datetime
import glob
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "opentallas.die_ci.v1"

DIES = [
    dict(name="s81", plans=["physical/die_plan/s81/die_plan.json"]),
    dict(name="s81_head", plans=["physical/die_plan/s81_head/die_plan.json"]),
    dict(name="qwen_compute", plans=["physical/die_plan/qwen_compute/die_plan.json"]),
    dict(name="qwen_kvsys", plans=["physical/die_plan/qwen_kvsys/die_plan.json"]),
    dict(name="hbm", plans=["physical/die_plan/hbm/die_plan.json"]),
    # HBM-ARCH B2 redesign: joins when its plan is on main (B2r2 preferred over B2)
    dict(name="hbm_arch_B2", plans=["physical/die_plan/hbm_arch/B2r2/die_plan.json",
                                    "physical/die_plan/hbm_arch/B2/die_plan.json"], optional=True),
]
RACK = "results/arch/release_rack_1021"
SYSTEMS = [
    dict(name="s81", conn=f"{RACK}/connections_s81.csv", roles={"H": "s81_head", "S": "s81", "B": "s81"}),
    dict(name="hbm-ds", conn=f"{RACK}/connections_hbm-ds.csv", roles={"D": "hbm"}),
    dict(name="hbm-ds@B2", conn=f"{RACK}/connections_hbm-ds.csv", roles={"D": "hbm_arch_B2"}),
    dict(name="qwen-rom", conn=f"{RACK}/connections_qwen-rom.csv", roles=None,
         na="rack macros are io_ucie, not lk_ die.io windows (xdie_io.py checks lk_ circuits only)"),
    dict(name="hbm-qwen", conn=f"{RACK}/connections_hbm-qwen.csv", roles=None,
         na="rack macros are 'ot_pdie_serdes Lk' package lanes, not lk_ die.io windows"),
]
G2_TOOLS = ["tools/die_plan/g2.py", "tools/die_plan/gen_phys.py", "tools/die_plan/check.py", "tools/die_plan/schema.py"]
G2_WORST = 5
G2_MEM_DIE = 64
G2_MEM_PART = 32

# AGENTS.md policy (never relaxed here; margins add on top)
POLICY = dict(period_ps=833.333, unc_setup_ps=60.0, unc_hold_ps=25.0, setup_corner="SS", hold_corner="FF")


def sh(cmd, cwd=None, log=None, env=None):
    t0 = time.time()
    if log:
        with open(log, "w") as f:
            r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, text=True, env=env)
        out = ""
    else:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
        out = r.stdout + r.stderr
    return r.returncode, out, round(time.time() - t0, 1)


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def file_digest(paths):
    h = hashlib.sha256()
    for p in paths:
        p = Path(p)
        h.update(p.name.encode())
        h.update(p.read_bytes() if p.is_file() else b"<missing>")
    return h.hexdigest()[:16]


def _import(repo, name):
    """import tools/die_plan/<name>.py of the repo under test (the sha being checked, not this file's copy)."""
    d = str(Path(repo) / "tools/die_plan")
    if d not in sys.path:
        sys.path.insert(0, d)
    import importlib
    return importlib.import_module(name)


# --------------------------------------------------------------------------------------------------------- margins
def _blk(text, head):
    i = text.find(head)
    if i < 0:
        return None
    j = text.find("{", i)
    d, k = 1, j + 1
    while d and k < len(text):
        d += {"{": 1, "}": -1}.get(text[k], 0)
        k += 1
    return text[j + 1:k - 1]


def _tables(body, kind):
    """{table name: (idx1, idx2, values)} of every `name (template) {index_1 ..; index_2 ..; values (..)}` in body."""
    out = {}
    for m in re.finditer(r"(\w+)\s*\(\s*\w+\s*\)\s*\{\s*index_1\s*\(\"([^\"]+)\"\);\s*index_2\s*\(\"([^\"]+)\"\);"
                         r"\s*values\s*\((.*?)\);", body, re.S):
        i1 = [float(x) for x in m.group(2).split(",")]
        i2 = [float(x) for x in m.group(3).split(",")]
        rows = [[float(x) for x in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(4))]
        out[m.group(1)] = (i1, i2, rows)
    return out


def interp2(tab, x, y):
    i1, i2, v = tab

    def seg(ax, q):
        for k in range(len(ax) - 1):
            if q <= ax[k + 1] or k == len(ax) - 2:
                return k, (q - ax[k]) / (ax[k + 1] - ax[k])
    a, fa = seg(i1, x)
    b, fb = seg(i2, y)
    top = v[a][b] + (v[a][b + 1] - v[a][b]) * fb
    bot = v[a + 1][b] + (v[a + 1][b + 1] - v[a + 1][b]) * fb
    return top + (bot - top) * fa


def flop_numbers(lib_text, cell="DFFHQNx1_ASAP7_75t_R", slew=20.0, load_ff=10.0):
    """clk->q (max / min of rise, fall), R_eff (ps/fF, delay slope 5.76 -> 11.52 fF), setup and hold (max of rise /
    fall constraint) of a flop at (slew, load) from one NLDM liberty text."""
    c = _blk(lib_text, f"cell ({cell})")
    if c is None:
        raise SystemExit(f"die_ci margins: {cell} not in liberty")
    q = _blk(c, "pin (QN)") or _blk(c, "pin (Q)")
    t = _tables(q, "delay")
    cq = [interp2(t[k], slew, load_ff) for k in ("cell_rise", "cell_fall") if k in t]
    reff = max((interp2(t[k], slew, 11.52) - interp2(t[k], slew, 5.76)) / 5.76 for k in ("cell_rise", "cell_fall")
               if k in t)
    d = _blk(c, "pin (D)")
    setup = hold = None
    for m in re.finditer(r"timing\s*\(\s*\)\s*\{", d):
        body = _blk(d[m.start():], "timing")
        tt = re.search(r"timing_type\s*:\s*\"?(\w+)", body)
        tabs = _tables(body, "constraint")
        v = max(interp2(x, slew, slew) for x in tabs.values()) if tabs else None
        if tt and tt.group(1).startswith("setup"):
            setup = v
        elif tt and tt.group(1).startswith("hold"):
            hold = v
    cap = re.search(r"\bcapacitance\s*:\s*([\d.]+)", d)
    return dict(cell=cell, slew_ps=slew, load_ff=load_ff, clk_q_max_ps=round(max(cq), 2), clk_q_min_ps=round(min(cq), 2),
                r_eff_ps_per_ff=round(reff, 3), setup_ps=round(setup, 2) if setup is not None else None,
                hold_ps=round(hold, 2) if hold is not None else None, d_cap_ff=float(cap.group(1)) if cap else None)


def derive_margins(libdir, base=None):
    """margins JSON: the policy-independent assumptions (OCV, IR, crosstalk parameters) + the liberty-derived numbers."""
    m = json.loads(json.dumps(base or DEFAULT_MARGINS))
    x = m["xtalk"]
    seam_c = x["c_per_um_ff"] * x["seam_len_um_default"] + 0.6
    lib = {}
    for corner in ("SS", "FF", "TT"):
        p = Path(libdir) / f"asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib"
        txt = gzip_read(p) if p.suffix == ".gz" else p.read_text(errors="replace")
        lib[corner] = flop_numbers(txt, load_ff=round(seam_c, 2))
        lib[corner]["liberty"] = p.name
    m["lib"] = lib
    m["derived_on"] = datetime.date.today().isoformat()
    return m


def gzip_read(p):
    import gzip
    with gzip.open(p, "rt", errors="replace") as f:
        return f.read()


DEFAULT_MARGINS = {
    "schema": "opentallas.die_ci.margins.v1",
    "policy_note": "Margins add ON TOP of AGENTS.md (833.333 ps at SS setup / FF hold, 60 ps setup / 25 ps hold "
                   "uncertainty); die_ci.check_margins rejects any value that would relax the policy.",
    "ocv": {
        "cell_late": 1.05, "cell_early": 0.95, "net_late": 1.03, "net_early": 0.97,
        "why": "Flat OCV (OpenSTA set_timing_derate) because ASAP7 ships no LVF / POCV sigma tables. +/-5 % cell is the "
               "flat derate an AOCV table gives a ~10-stage path (the partition clock trees from the tap to the face "
               "flops are 8-14 stages; flat derates of 5-10 % are the usual range without LVF, cf. Bhasker & Chadha, "
               "Static Timing Analysis for Nanometer Designs, 2009, ch. 10 on OCV derating). +/-3 % on nets. CRPR only "
               "removes the common clock path; seams share only the die clk port (ideal spine), so the whole tree of "
               "each partition is derated -- the dominant term on a seam."
    },
    "ir": {
        "mode": "stated", "vdd_ss_v": 0.63, "vdd_drop_frac": 0.05, "vt_v": 0.25, "alpha": 1.3,
        "why": "No die-level PDN database exists yet (die_plan pg.grid is a plan; no placed die ODB with power for "
               "OpenROAD PDNSim / analyze_power_grid), so PDNSim is NOT RUN and a stated budget is used: 5 % of the "
               "SS supply (31.5 mV at 0.63 V, the total static + dynamic drop a sign-off PDN is designed to). Delay "
               "sensitivity from the alpha-power law (Sakurai & Newton, IEEE JSSC 25(2), 1990), t ~ V / (V - Vt)^a: "
               "d ln t / d ln V = 1 - a V / (V - Vt) = -1.155 at a = 1.3, Vt = 0.25 V (conservative ASAP7 RVT), so a "
               "5 % drop is +5.8 % cell delay, applied as an extra LATE cell derate on data and clock (setup: late "
               "launch + data; hold: late capture clock). When a PDNSim result exists (pdnsim: {worst_drop_mv}) it "
               "replaces vdd_drop_frac.",
        "pdnsim": None
    },
    "xtalk": {
        "c_per_um_ff": 0.178475, "cc_frac": 0.7, "mcf_setup": 2.0, "mcf_hold": 0.0, "seam_len_um_default": 60.0,
        "why": "OpenSTA has no SI delay. Per-seam margin = |MCF - 1| x R_eff x Cc, Cc = cc_frac x c_per_um x L_seam: "
               "c_per_um = ASAP7 M4 0.178 fF/um (ORFS platforms/asap7/setRC.tcl, the seam pin layers M4-M7 are "
               "0.163-0.187); cc_frac 0.7 = sidewall coupling share of a min-pitch 7 nm line with both neighbours "
               "(aspect ratio ~2); Miller coupling factor 2 (opposite switching, setup) / 0 (same direction, hold) is "
               "the worst-case switch-factor bound of Kahng, Muddu & Sarto (DAC 2000); L_seam = 2 x "
               "budgets.pin_reg_p90_um (R2 face flops at both pins, G3 pin-to-reg p90 budget, 30 um per side "
               "default); R_eff = the clk->QN delay slope of DFFHQNx1 at the corner (lib below). This is a bound "
               "for an x1 face flop driving the seam unbuffered; a kit that upsizes the seam driver lowers the real "
               "push. Clock-net coupling is not added (clock trees are inside the derated OCV term)."
    },
    "lib": {
        "SS": {"cell": "DFFHQNx1_ASAP7_75t_R", "clk_q_max_ps": 152.25, "clk_q_min_ps": 144.82,
               "r_eff_ps_per_ff": 6.596, "setup_ps": 16.21, "hold_ps": 18.28},
        "FF": {"cell": "DFFHQNx1_ASAP7_75t_R", "clk_q_max_ps": 71.16, "clk_q_min_ps": 68.92,
               "r_eff_ps_per_ff": 2.77, "setup_ps": 9.92, "hold_ps": 12.28}
    }
}


def load_margins(path):
    m = json.loads(Path(path).read_text()) if path and Path(path).is_file() else json.loads(json.dumps(DEFAULT_MARGINS))
    check_margins(m)
    return m


def check_margins(m):
    """refuse anything that would relax the AGENTS.md policy: derates must be pessimistic, margins >= 0."""
    o, ir, x = m["ocv"], m["ir"], m["xtalk"]
    bad = []
    if o["cell_late"] < 1 or o["net_late"] < 1:
        bad.append("ocv late derate < 1")
    if o["cell_early"] > 1 or o["net_early"] > 1:
        bad.append("ocv early derate > 1")
    if ir.get("vdd_drop_frac", 0) < 0 or (ir.get("pdnsim") or {}).get("worst_drop_mv", 0) < 0:
        bad.append("negative IR drop")
    if x["mcf_setup"] < 1 or x["mcf_hold"] > 1 or x["cc_frac"] < 0 or x["c_per_um_ff"] < 0:
        bad.append("crosstalk factors that reduce delay push")
    for k in ("period_ps", "unc_setup_ps", "unc_hold_ps"):
        if k in m.get("policy", {}) and ((k == "period_ps" and m["policy"][k] > POLICY[k]) or
                                         (k != "period_ps" and m["policy"][k] < POLICY[k])):
            bad.append(f"policy {k} relaxed")
    if bad:
        raise SystemExit("die_ci: margins would relax the AGENTS.md policy: " + "; ".join(bad))
    return True


def ir_factor(m):
    ir = m["ir"]
    v, vt, a = ir["vdd_ss_v"], ir["vt_v"], ir["alpha"]
    sens = a * v / (v - vt) - 1.0
    drop = ir["vdd_drop_frac"]
    if (ir.get("pdnsim") or {}).get("worst_drop_mv") is not None:
        drop = ir["pdnsim"]["worst_drop_mv"] / 1000.0 / v
    return round(1.0 + drop * sens, 4), round(sens, 3), drop


def derates(m):
    irf, _, _ = ir_factor(m)
    o = m["ocv"]
    return dict(cell_late=round(o["cell_late"] * irf, 4), cell_early=o["cell_early"], net_late=o["net_late"],
                net_early=o["net_early"], ir_factor=irf)


def xtalk_ps(m, pin_reg_p90_um=None):
    x = m["xtalk"]
    L = 2.0 * pin_reg_p90_um if pin_reg_p90_um else x["seam_len_um_default"]
    cc = x["cc_frac"] * x["c_per_um_ff"] * L
    s = abs(x["mcf_setup"] - 1.0) * m["lib"]["SS"]["r_eff_ps_per_ff"] * cc
    h = abs(1.0 - x["mcf_hold"]) * m["lib"]["FF"]["r_eff_ps_per_ff"] * cc
    return dict(setup_ps=round(s, 2), hold_ps=round(h, 2), seam_len_um=L, cc_ff=round(cc, 3))


def derate_tcl(m):
    d = derates(m)
    return ("# DIE-CI margins (tools/die_plan/die_ci_margins.json): OCV x IR, on top of the AGENTS.md uncertainty\n"
            f"set_timing_derate -late -cell_delay {d['cell_late']:.4f}\n"
            f"set_timing_derate -early -cell_delay {d['cell_early']:.4f}\n"
            f"set_timing_derate -late -net_delay {d['net_late']:.4f}\n"
            f"set_timing_derate -early -net_delay {d['net_early']:.4f}\n")


def inject_derate(tcl_text, m):
    """add the derates to a die_sta.py STA script after its clock constraints, before its report loop."""
    anchor = "set fh [open"
    if anchor not in tcl_text or "set_clock_uncertainty" not in tcl_text:
        raise SystemExit("die_ci: die_sta.py STA script layout changed (no `set fh [open` anchor); update inject_derate")
    return tcl_text.replace(anchor, derate_tcl(m) + anchor, 1)


# ----------------------------------------------------------------------------------------------- plan / seams / budgets
def plan_seams(P):
    """inter-partition ports = seams: [{port, src, src_bus, dst, dst_bus, width, cls}] (cls ft_in / ft_out / ft / bus)."""
    die = "@die"
    slots = {}
    for tn, t in P.types.items():
        slots[tn] = {s["name"] for s in t.get("ft_slots", [])}
    out = []
    for pid, pr in P.ports.items():
        s, d = pr["src"], pr["dst"]
        if s["part"] == die or d["part"] == die:
            continue
        src_ft = s["bus"].endswith("_o") and s["bus"][:-2] in slots[P.parts[s["part"]]["type"]]
        dst_ft = d["bus"].endswith("_i") and d["bus"][:-2] in slots[P.parts[d["part"]]["type"]]
        cls = "ft" if src_ft and dst_ft else ("ft_out" if src_ft else ("ft_in" if dst_ft else "bus"))
        out.append(dict(port=pid, src=s["part"], src_bus=s["bus"], dst=d["part"], dst_bus=d["bus"],
                        width=pr.get("width"), cls=cls))
    return out


def kit_budget(gen_phys):
    """the kit SDC budget fractions of gen_phys.sdc (IO / ft hop share), the hold padding rule."""
    return dict(io=float(gen_phys.IO_BUDGET), ft_in_share=float(gen_phys.FT_HOP_IN_SHARE),
                hold_out_min_ps=float(gen_phys.HOLD_OUT_MIN_PS))


def standin(seam_cls, P, m, kb):
    """stand-in setup / hold slack (ps) of one unmeasured seam: contract composition or R2 face-flop estimate, minus
    the margins the kits cannot see (crosstalk, derates on the two clock trees and the launching clk->q)."""
    T = min(float(P.die["period_ps"]), POLICY["period_ps"])
    tol = float(P.clock["insertion_tol_ps"])
    ins = float(P.clock["insertion_ps"])
    skew = float(P.clock.get("neighbour_skew_ps", 80))
    # src output max delay O / dst input max delay I of the kit SDCs (fractions of T)
    O = kb["ft_in_share"] if seam_cls in ("ft", "ft_out") else kb["io"]
    I = (1.0 - kb["ft_in_share"]) if seam_cls in ("ft", "ft_in") else kb["io"]
    comp = (I + O - 1.0) * T
    ss, ff = m["lib"]["SS"], m["lib"]["FF"]
    pin_reg = float(P.budgets.get("pin_reg_p90_um", 30.0))
    L = 2 * pin_reg
    wire_ps = 0.5 * 0.0180365 * m["xtalk"]["c_per_um_ff"] * L * L   # Elmore, M4 R (kohm/um) x C (fF/um) -> ps
    xt = xtalk_ps(m, pin_reg)
    d = derates(m)
    clk_setup = ins * (d["cell_late"] - d["cell_early"])          # launch tree late, capture tree early
    clk_hold = ins * (d["cell_late"] - d["cell_early"])           # capture tree late (incl. IR), launch tree early
    m_setup = xt["setup_ps"] + clk_setup + (d["cell_late"] - 1.0) * ss["clk_q_max_ps"]
    m_hold = xt["hold_ps"] + clk_hold + (1.0 - d["cell_early"]) * ff["clk_q_min_ps"]
    if comp >= 0:
        setup, basis = comp, "contract (kit I_max + O_max >= T)"
    else:
        setup = (T - POLICY["unc_setup_ps"] - skew - ss["clk_q_max_ps"] - wire_ps - ss["setup_ps"])
        basis = "R2 face-flop estimate (kit IO budget 0.2T+0.2T does not compose)"
    hold = tol - kb["hold_out_min_ps"]                            # O_min - I_min = 0 - (-tol)
    return dict(cls=seam_cls, basis=basis, setup_policy_ps=round(setup, 1), hold_policy_ps=round(hold, 1),
                margin_setup_ps=round(m_setup, 1), margin_hold_ps=round(m_hold, 1),
                setup_ps=round(setup - m_setup, 1), hold_ps=round(hold - m_hold, 1))


# -------------------------------------------------------------------------------------------------------- views / sub-top
def load_views(path, die):
    if not path or not Path(path).is_file():
        return {}
    reg = json.loads(Path(path).read_text())
    return reg.get("dies", {}).get(die, {})


def resolve_view(die, tn, ent, views_root):
    """local dir with 6_final.v (+ .spef/.sdc) for a registered view: staged copy, or the path on this host."""
    if views_root:
        d = Path(views_root) / die / tn
        if (d / "6_final.v").is_file():
            return d
    host = ent.get("host")
    if (not host or host in (socket.gethostname(), "localhost")) and Path(os.path.expanduser(ent["path"]), "6_final.v").is_file():
        return Path(os.path.expanduser(ent["path"]))
    return None


def filter_top(top_text, keep_modules):
    """keep only the instances of keep_modules in a gen_rtl.die_top / die_sta.write_top structural netlist."""
    pat = re.compile(r"^    (\S+) (\S+) \(\n.*?\n    \);\n?", re.S | re.M)
    kept = []

    def rep(mm):
        if mm.group(1) in keep_modules:
            kept.append(mm.group(2))
            return mm.group(0)
        return ""
    return pat.sub(rep, top_text), kept


def stage_views(views_path, host, dest, cache=None):
    """(run on localhost) copy every registered view (6_final.v/.spef/.sdc) to host:dest/<die>/<type>/."""
    reg = json.loads(Path(views_path).read_text())
    cache = Path(cache or os.path.expanduser("~/.cache/opentallas/die_ci_views"))
    done = []
    for die, ents in reg.get("dies", {}).items():
        for tn, e in ents.items():
            loc = cache / die / tn
            loc.mkdir(parents=True, exist_ok=True)
            src = f"{e['host']}:{e['path']}/" if e.get("host") not in (None, "localhost") else os.path.expanduser(e["path"]) + "/"
            r = subprocess.run(["rsync", "-a", "--include=6_final.v", "--include=6_final.spef", "--include=6_final.sdc",
                                "--exclude=*", src, str(loc) + "/"], capture_output=True, text=True)
            if r.returncode:
                done.append(dict(die=die, type=tn, ok=False, err=r.stderr.strip()[-300:]))
                continue
            subprocess.run(["ssh", host, f"mkdir -p {dest}/{die}/{tn}"], check=True)
            r = subprocess.run(["rsync", "-a", str(loc) + "/", f"{host}:{dest}/{die}/{tn}/"], capture_output=True, text=True)
            done.append(dict(die=die, type=tn, ok=r.returncode == 0, err=r.stderr.strip()[-300:]))
    return done


# ------------------------------------------------------------------------------------------------------------ gates
def gate_g0(repo, plan, work):
    out = work / "g0c"
    out.mkdir(parents=True, exist_ok=True)
    rc, _, sec = sh([sys.executable, str(repo / "tools/die_plan/check.py"), str(plan), "--out", str(out),
                     "--completeness", "--quiet"], cwd=repo, log=out / "check.log")
    rp = out / "g0_report.json"
    if not rp.is_file():
        nr = dict(status=f"NOT RUN (check.py exit {rc}, no report; {out / 'check.log'})")
        return nr, dict(nr), None
    r = json.loads(rp.read_text())
    errs = [i for i in r["findings"] if i["level"] == "ERROR"]
    g0e = [i for i in errs if not i.get("g0c")]
    s = r["summary"]
    g = s.get("g0c", {})
    by = Counter(i["check"] for i in errs)
    g0 = dict(status="PASS" if not g0e else "FAIL", errors=len(g0e), by_check=dict(Counter(i["check"] for i in g0e)),
              warnings=r["warnings"] + len(errs) - len(g0e), seconds=sec, report=str(rp),
              worst_cut=s.get("cuts", {}).get("worst_full"), worst_segment=s.get("cuts", {}).get("worst_partition_segment"),
              types=s.get("types", {}).get("types"), partitions=s.get("types", {}).get("partitions"))
    g0c = dict(status="PASS" if not errs else "FAIL", errors=len(errs), by_check=dict(by),
               clean_types=g.get("clean"), types=g.get("types"), g3_eligible=len(g.get("g3_eligible", [])),
               report=str(rp))
    return g0, g0c, r


def gate_census(rep):
    if rep is None:
        return dict(status="NOT RUN (no G0 report)")
    c = rep["summary"].get("census") or {}
    errs = [i for i in rep["findings"] if i["level"] == "ERROR" and i["check"].startswith("census")]
    srcs = c.get("sources", [])
    if c.get("declared") == "none":
        return dict(status="N/A (census none: " + str(c.get("reason"))[:120] + ")", errors=len(errs))
    if not c.get("declared"):
        return dict(status="FAIL", reason="census not declared", errors=len(errs))
    unm = sum(x.get("unmapped_instances", 0) or 0 for x in srcs)
    dropped = c.get("dropped_bits", sum(x.get("dropped_bits", 0) or 0 for x in srcs))
    st = "PASS" if not errs and not unm and not dropped else "FAIL"
    return dict(status=st, errors=len(errs), dropped_bits=dropped, unmapped_instances=unm,
                inter_bits=sum(x.get("inter_bits", 0) or 0 for x in srcs),
                exempt=sum(sum((x.get("exempt") or {}).values()) for x in srcs), sources=len(srcs))


def gate_latency(repo, plan, rep):
    gen = _import(repo, "gen")
    S = _import(repo, "schema")
    raw = json.loads(Path(plan).read_text())
    dig = gen.plan_digest(raw)
    P = S.Plan(raw)
    tab = gen.latency_table(P)
    g0_lat = [i for i in (rep or {}).get("findings", []) if i["level"] == "ERROR" and i["check"] == "latency"]
    files = []
    for f in sorted(glob.glob(str(Path(plan).parent / "**" / "*_latency.json"), recursive=True)):
        if f.endswith("bind_latency.json"):
            continue
        try:
            j = json.loads(Path(f).read_text())
        except Exception:
            continue
        L = j.get("lanes", {})
        mism = [lid for lid in tab if lid not in L or L[lid].get("cycles") != tab[lid]["cycles"]]
        files.append(dict(file=os.path.relpath(f, repo), plan_digest=j.get("plan_digest"), digest_match=j.get("plan_digest") == dig,
                          lanes=len(L), mismatched_lanes=len(mism), extra_lanes=len(set(L) - set(tab)),
                          example=mism[:3]))
    rec = [f for f in files if f["digest_match"]]
    good = [f for f in rec if not f["mismatched_lanes"] and not f["extra_lanes"]]
    if g0_lat:
        st = "FAIL"
    elif good:
        st = "PASS"
    else:
        st = "FAIL"
    why = None
    if not files:
        why = "no <die>_latency.json in the plan dir (gen.py latency never written for this plan)"
    elif not rec:
        why = "no latency table carries the current plan digest (stale table)"
    elif not good:
        why = "the digest-matching table differs from Plan.lane_latency()"
    return dict(status=st, reason=why, plan_digest=dig, lanes=len(tab), g0_latency_errors=len(g0_lat),
                record=good[0]["file"] if good else None, files=files,
                max_cycles=max((d["cycles"] for d in tab.values()), default=0))


def gate_xdie_in(rep):
    if rep is None:
        return dict(status="NOT RUN (no G0 report)")
    xc = rep["summary"].get("xdie_counts", {})
    keys = ("die_io_plan", "cut_lines", "reach", "face_tracks", "ft_budget")
    n = {k: xc.get(k, 0) for k in keys}
    return dict(status="PASS" if not any(n.values()) else "FAIL", errors=sum(n.values()), by_rule=n)


def run_xdie_io(repo, sysdef, die_plans, work):
    if not sysdef.get("roles"):
        return dict(status=f"N/A ({sysdef['na']})")
    roles = {}
    for r, die in sysdef["roles"].items():
        if die not in die_plans:
            return dict(status=f"N/A (die {die} has no plan on this sha)")
        io = Path(die_plans[die]).parent / "die_io.json"
        if not io.is_file():
            return dict(status="FAIL", reason=f"{die}: no die_io.json", errors=1)
        roles[r] = io
    conn = repo / sysdef["conn"]
    if not conn.is_file():
        return dict(status=f"NOT RUN (no rack table {sysdef['conn']})")
    out = work / f"xdie_io_{sysdef['name'].replace('@', '_')}.json"
    cmd = [sys.executable, str(repo / "tools/die_plan/xdie_io.py"), "--conn", str(conn), "--out", str(out)]
    for r, p in roles.items():
        cmd += ["--role", f"{r}={p}"]
    rc, txt, sec = sh(cmd, cwd=repo)
    if not out.is_file():
        return dict(status=f"NOT RUN (xdie_io exit {rc}: {txt.strip()[-200:]})")
    j = json.loads(out.read_text())
    return dict(status=j["verdict"], errors=j["errors"], circuits=j["summary"]["circuits_checked"],
                warnings=len(j.get("warnings", [])),
                groups=[dict(rule=g["rule"], role=g["role"], n=g["n"], example=g["example"]) for g in j["error_groups"]][:12],
                report=str(out), seconds=sec)


def gate_g2(repo, plan, work, mem_die=G2_MEM_DIE, mem_part=G2_MEM_PART):
    out = work / "g2"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if not shutil.which("docker"):
        return dict(status="NOT RUN (no docker on this host)")
    rc1, _, s1 = sh([sys.executable, str(repo / "tools/die_plan/g2.py"), "die", str(plan), "--out", str(out), "--run",
                     "--mem", str(mem_die)], cwd=repo, log=work / "g2_die.log")
    rc2, _, s2 = sh([sys.executable, str(repo / "tools/die_plan/g2.py"), "part", str(plan), "--out", str(out),
                     "--worst", str(G2_WORST), "--run", "--mem", str(mem_part)], cwd=repo, log=work / "g2_part.log")
    rp = out / "g2_report.json"
    if not rp.is_file():
        return dict(status=f"NOT RUN (g2.py exit {rc1}/{rc2}, no report; see {work}/g2_*.log)")
    r = json.loads(rp.read_text())
    probes = {}
    for k, v in r["probes"].items():
        probes[k] = dict(done=v.get("done"), overflow=v.get("total_overflow"), wirelength_um=v.get("wirelength_um"),
                         no_access=sum((v.get("pin_access_no_ap") or {}).values()), errors=v.get("errors"),
                         reach=v.get("reach"))
    ov = sum((p["overflow"] or 0) for p in probes.values())
    na = sum(p["no_access"] for p in probes.values())
    return dict(status=r["verdict"], probes=len(probes), overflow=ov, no_access=na,
                not_done=sorted(k for k, p in probes.items() if not p["done"]), detail=probes, seconds=s1 + s2,
                report=str(rp))


# ----------------------------------------------------------------------------------------------------------- die STA
def sta_available(repo):
    return (Path(repo) / "tools/die_plan/die_sta.py").is_file()


def gate_sta(repo, die, plan, work, views, views_root, margins, threads=8):
    """abstract-model die STA over the partitions with views + stand-in budgets for every other seam."""
    S = _import(repo, "schema")
    gen_phys = _import(repo, "gen_phys")
    raw = json.loads(Path(plan).read_text())
    P = S.Plan(raw)
    kb = kit_budget(gen_phys)
    seams = plan_seams(P)
    have = {}
    missing_views = {}
    for tn, ent in views.items():
        if tn not in P.types:
            missing_views[tn] = "type not in this plan"
            continue
        d = resolve_view(die, tn, ent, views_root)
        if d is None:
            missing_views[tn] = f"view not on this host ({ent.get('host')}:{ent.get('path')}; stage-views)"
        else:
            have[tn] = d
    vparts = {n for n, p in P.parts.items() if p["type"] in have}
    measured = [s for s in seams if s["src"] in vparts and s["dst"] in vparts]
    rest = [s for s in seams if not (s["src"] in vparts and s["dst"] in vparts)]
    si = {}
    for cls in sorted({s["cls"] for s in rest}):
        si[cls] = standin(cls, P, margins, kb)
    si_rows = [si[s["cls"]] for s in rest]
    res = dict(seams=len(seams), measured_ports=len(measured), standin_ports=len(rest),
               standin={c: dict(v, ports=sum(1 for s in rest if s["cls"] == c)) for c, v in si.items()},
               standin_worst_setup_ps=min((r["setup_ps"] for r in si_rows), default=None),
               standin_worst_hold_ps=min((r["hold_ps"] for r in si_rows), default=None),
               views={tn: str(d) for tn, d in have.items()}, views_unavailable=missing_views,
               xtalk=xtalk_ps(margins, float(P.budgets.get("pin_reg_p90_um", 30.0))), derates=derates(margins),
               ir=dict(zip(("factor", "sensitivity", "drop_frac"), ir_factor(margins)),
                       mode="pdnsim" if (margins["ir"].get("pdnsim") or {}).get("worst_drop_mv") is not None else "stated",
                       pdnsim="NOT RUN: no die-level PDN database (plan pg.grid only)"
                       if not margins["ir"].get("pdnsim") else margins["ir"]["pdnsim"]))
    if not sta_available(repo):
        res["status"] = "NOT RUN (tools/die_plan/die_sta.py not on this sha: lane DIE-STA claude/die-sta-1024)"
        return res
    if not measured:
        res["status"] = ("NOT RUN (no seam between two partitions with routed views; stand-in budgets only)"
                         if seams else "N/A (no seams)")
        return res
    sta = work / "sta"
    if sta.exists():
        shutil.rmtree(sta)
    (sta / "parts").mkdir(parents=True)
    for tn, d in have.items():
        os.symlink(d.resolve(), sta / "parts" / tn)
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "_sta", "--repo", str(repo), "--plan", str(plan),
                           "--work", str(sta), "--margins-json", json.dumps(margins), "--threads", str(threads),
                           "--modules", ",".join(sorted({P.types[t]["module"] for t in have}))],
                          capture_output=True, text=True)
    (sta / "die_ci_sta.log").write_text(proc.stdout + proc.stderr)
    rj = sta / "die_ci_sta.json"
    if not rj.is_file():
        res["status"] = f"NOT RUN (die STA exit {proc.returncode}; {sta / 'die_ci_sta.log'})"
        return res
    r = json.loads(rj.read_text())
    res.update(r)
    xs, xh = res["xtalk"]["setup_ps"], res["xtalk"]["hold_ps"]
    rows = []
    for g in sorted(set(r["policy"]["seams"]) | set(r["margined"]["seams"])):
        row = dict(seam=g)
        for tag in ("policy", "margined"):
            sg = r[tag]["seams"].get(g, {})
            row[f"{tag}_setup_SS"] = sg.get("setup_SS")
            row[f"{tag}_hold_FF"] = sg.get("hold_FF")
            row[f"{tag}_neg"] = sg.get("neg", 0)
        row["final_setup_SS"] = None if row["margined_setup_SS"] is None else round(row["margined_setup_SS"] - xs, 3)
        row["final_hold_FF"] = None if row["margined_hold_FF"] is None else round(row["margined_hold_FF"] - xh, 3)
        rows.append(row)
    res["seam_groups"] = rows

    def worst(k):
        v = [x[k] for x in rows if x[k] is not None]
        return min(v) if v else None
    res["worst"] = {k: worst(k) for k in ("policy_setup_SS", "policy_hold_FF", "final_setup_SS", "final_hold_FF")}
    res["neg_groups"] = sum(1 for x in rows if (x["final_setup_SS"] is not None and x["final_setup_SS"] < 0) or
                            (x["final_hold_FF"] is not None and x["final_hold_FF"] < 0))
    ran = r["policy"].get("ran") and r["margined"].get("ran")
    if not ran:
        res["status"] = "NOT RUN (signoff corners SS + FF did not both complete; see die_ci_sta.log)"
    elif res["neg_groups"]:
        res["status"] = "FAIL"
    elif rest:
        res["status"] = f"PARTIAL ({len(measured)}/{len(seams)} seam ports measured, all >= 0 margined; rest stand-in)"
    else:
        res["status"] = "PASS"
    return res


def cmd_sta_child(a):
    """(subprocess) policy + margined die STA through die_sta.py on the sub-top of the partitions with views."""
    repo = Path(a.repo)
    work = Path(a.work)
    margins = json.loads(a.margins_json)
    ds = _import(repo, "die_sta")
    # policy guard: DIE-STA's constants are the AGENTS.md policy; die_ci never runs a relaxed variant
    if ds.UNC_SETUP_PS < POLICY["unc_setup_ps"] or ds.UNC_HOLD_PS < POLICY["unc_hold_ps"] or \
            ds.PERIOD_PS > POLICY["period_ps"] + 1e-6:
        raise SystemExit("die_ci: die_sta.py constants relax the AGENTS.md policy")
    ds.THREADS = int(a.threads)
    full = work / "die_top_full.v"
    ds.write_top(a.plan, full)
    sub, kept = filter_top(full.read_text(), set(a.modules.split(",")))
    top = work / "die_top_sub.v"
    top.write_text(sub)
    raw = json.loads(Path(a.plan).read_text())
    period = min(float(raw["die"]["period_ps"]), POLICY["period_ps"])
    out = dict(instances=kept, period_ps=period)
    orig = ds.sta_tcl
    for tag in ("policy", "margined"):
        o = work / tag
        o.mkdir(exist_ok=True)
        if tag == "margined" and (work / "policy" / "ilm").is_dir() and not (o / "ilm").exists():
            os.symlink((work / "policy" / "ilm").resolve(), o / "ilm")
        if tag == "margined":
            ds.sta_tcl = lambda *x, **k: inject_derate(orig(*x, **k), margins)
        else:
            ds.sta_tcl = orig
        ns = argparse.Namespace(top=str(top), top_module=None, parts=str(work / "parts"), out=str(o), mode="ilm",
                                corner=["SS", "FF"], period_ps=period, spine_branch=None, die_spef=None, libdir=None,
                                lib=[], rebuild=False)
        t0 = time.time()
        try:
            r = ds.cmd_run(ns)
        except SystemExit as e:
            out[tag] = dict(ran=False, error=str(e), seams={})
            continue
        seams = {}
        for c, cr in r["corners"].items():
            for g, s in cr.get("seams", {}).items():
                for dly, key in (("max", f"setup_{c}"), ("min", f"hold_{c}")):
                    if s.get(dly):
                        seams.setdefault(g, {"neg": 0})[key] = s[dly]["worst"]
                        seams[g]["neg"] += s[dly]["neg"]
        out[tag] = dict(ran=all(r["corners"].get(c, {}).get("exit") == 0 for c in ("SS", "FF")),
                        verdict=r.get("verdict"), seams=seams, seconds=round(time.time() - t0, 1),
                        corners={c: dict(exit=x.get("exit"), seconds=x.get("seconds"), rss_gb=x.get("peak_rss_gb"),
                                         wns_ps=x.get("wns_ps"), whs_ps=x.get("whs_ps"))
                                 for c, x in r["corners"].items()},
                        seam_groups=r.get("seam_groups"), seam_bits=r.get("seam_bits"))
    ds.sta_tcl = orig
    (work / "die_ci_sta.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


# ------------------------------------------------------------------------------------------------------------ run
def resolve_plans(repo, extra=None):
    if extra:                    # --plan NAME=PATH (tests, ad-hoc plans): replaces the DIES list
        return {n: Path(p).resolve() for n, p in (x.split("=", 1) for x in extra)}
    out = {}
    for d in DIES:
        for p in d["plans"]:
            if (Path(repo) / p).is_file():
                out[d["name"]] = Path(repo) / p
                break
    return out


def find_prev(out_root, run_name):
    runs = []
    for f in Path(out_root).glob("*/die_ci.json"):
        if f.parent.name == run_name:
            continue
        try:
            j = json.loads(f.read_text())
            runs.append((j.get("started", ""), f))
        except Exception:
            pass
    return sorted(runs)[-1][1] if runs else None


METRICS = [("g0", "errors"), ("g0c", "errors"), ("g0c", "clean_types"), ("xdie", "errors"), ("g2", "overflow"),
           ("g2", "no_access"), ("census", "dropped_bits"), ("latency", "g0_latency_errors"),
           ("sta", "measured_ports"), ("sta", "neg_groups")]


def metrics(d):
    m = {}
    for g, k in METRICS:
        v = (d.get("gates", {}).get(g) or {}).get(k)
        if isinstance(v, (int, float)):
            m[f"{g}.{k}"] = v
    w = (d.get("gates", {}).get("sta") or {}).get("worst") or {}
    for k, v in w.items():
        if v is not None:
            m[f"sta.{k}"] = v
    return m


def deltas(cur, prev):
    if not prev:
        return None
    a, b = metrics(cur), metrics(prev)
    out = {k: round(a[k] - b[k], 3) for k in a if k in b and a[k] != b[k]}
    st = {}
    for g, v in cur.get("gates", {}).items():
        pv = (prev.get("gates", {}).get(g) or {}).get("status")
        if pv and pv.split(" ")[0] != (v or {}).get("status", "").split(" ")[0]:
            st[g] = f"{pv.split(' ')[0]} -> {v['status'].split(' ')[0]}"
    return dict(prev_sha=prev.get("sha"), metrics=out, status_changes=st, new=sorted(set(a) - set(b)))


def overall(gates):
    sts = [(g or {}).get("status", "NOT RUN") for g in gates.values()]
    if any(s.startswith("FAIL") for s in sts):
        return "FAIL"
    if any(s.startswith("NOT RUN") or s.startswith("PARTIAL") for s in sts):
        return "INCOMPLETE"
    return "PASS"


def run_die(repo, name, plan, work, a, prev_die, g2_mode, views, margins, xdie_sys):
    work.mkdir(parents=True, exist_ok=True)
    raw = json.loads(Path(plan).read_text())
    gen = _import(repo, "gen")
    dig = gen.plan_digest(raw)
    g2tools = file_digest([repo / p for p in G2_TOOLS])
    t0 = time.time()
    gates = {}
    gates["g0"], gates["g0c"], rep = gate_g0(repo, plan, work)
    xin = gate_xdie_in(rep)
    xs = {k: v for k, v in xdie_sys.items() if name in (v.get("_dies") or ())}
    xerr = xin.get("errors", 0) + sum(v.get("errors", 0) or 0 for v in xs.values())
    xst = [xin.get("status", "")] + [v.get("status", "") for v in xs.values()]
    gates["xdie"] = dict(status="FAIL" if any(s.startswith("FAIL") for s in xst) else
                         ("NOT RUN (in-die rules)" if xin["status"].startswith("NOT RUN") else "PASS"),
                         errors=xerr, in_die=xin, systems={k: {kk: vv for kk, vv in v.items() if kk != "_dies"}
                                                           for k, v in xs.items()})
    gates["census"] = gate_census(rep)
    gates["latency"] = gate_latency(repo, plan, rep)
    # G2: nightly / all = run; commit = run if the plan or the G2 tools changed since the previous run, else carry
    pg2 = (prev_die or {}).get("gates", {}).get("g2")
    same = prev_die and prev_die.get("plan_digest") == dig and prev_die.get("g2_tools_digest") == g2tools
    if g2_mode == "none":
        gates["g2"] = dict(status="NOT RUN (--g2 none)")
    elif g2_mode == "auto" and same and pg2 and not pg2.get("status", "").startswith("NOT RUN"):
        c = dict(pg2)
        src = pg2.get("carried_from") or prev_die.get("sha")
        c["carried_from"] = src
        c["status"] = f"{pg2['status'].split(' ')[0]} (CARRIED from {src}: plan + G2 tools unchanged)" \
            if "CARRIED" not in pg2["status"] else pg2["status"]
        gates["g2"] = c
    else:
        gates["g2"] = gate_g2(repo, plan, work)
    if a.sta == "none":
        gates["sta"] = dict(status="NOT RUN (--sta none)")
    else:
        try:
            gates["sta"] = gate_sta(repo, name, plan, work, views.get(name, {}) if isinstance(views, dict) else {},
                                    a.views_root, margins, threads=a.sta_threads)
        except SystemExit as e:
            gates["sta"] = dict(status=f"NOT RUN ({e})")
    d = dict(schema=SCHEMA, die=name, plan=os.path.relpath(plan, repo), sha=a.sha, plan_digest=dig,
             g2_tools_digest=g2tools, gates=gates, seconds=round(time.time() - t0, 1))
    d["verdict"] = overall(gates)
    d["delta"] = deltas(d, prev_die)
    return d


def fmt(v):
    return "-" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else str(v))


def die_md(d):
    g = d["gates"]
    L = [f"# DIE-CI {d['die']} @ {d['sha'][:10]} — {d['verdict']}", "",
         f"plan `{d['plan']}` digest `{d['plan_digest']}`; run {d.get('seconds')} s", "",
         "| gate | status | key numbers |", "|---|---|---|"]

    def row(k, txt):
        L.append(f"| {k} | {(g.get(k) or {}).get('status', 'NOT RUN')} | {txt} |")
    g0, g0c = g.get("g0", {}), g.get("g0c", {})
    row("g0", f"{fmt(g0.get('errors'))} err, {fmt(g0.get('warnings'))} warn; {fmt(g0.get('types'))} types / "
              f"{fmt(g0.get('partitions'))} parts; worst cut {fmt((g0.get('worst_cut') or {}).get('ratio'))}")
    row("g0c", f"{fmt(g0c.get('errors'))} err {g0c.get('by_check') or ''}; {fmt(g0c.get('clean_types'))}/"
               f"{fmt(g0c.get('types'))} types clean")
    x = g.get("xdie", {})
    sysd = "; ".join(f"{k}: {v.get('status')} ({fmt(v.get('errors'))} err / {fmt(v.get('circuits'))} circ)"
                     for k, v in (x.get("systems") or {}).items())
    row("xdie", f"in-die {fmt((x.get('in_die') or {}).get('errors'))} err; {sysd or 'no rack system'}")
    g2 = g.get("g2", {})
    row("g2", f"{fmt(g2.get('probes'))} probes, overflow {fmt(g2.get('overflow'))}, no-access {fmt(g2.get('no_access'))}")
    c = g.get("census", {})
    row("census", f"dropped {fmt(c.get('dropped_bits'))} bits, unmapped {fmt(c.get('unmapped_instances'))}, "
                  f"inter {fmt(c.get('inter_bits'))} bits")
    lt = g.get("latency", {})
    row("latency", f"{fmt(lt.get('lanes'))} lanes; table {lt.get('record') or lt.get('reason')}")
    s = g.get("sta", {})
    w = s.get("worst") or {}
    row("sta", f"{fmt(s.get('measured_ports'))}/{fmt(s.get('seams'))} seam ports measured; worst seam setup@SS "
               f"{fmt(w.get('final_setup_SS'))} ps (policy {fmt(w.get('policy_setup_SS'))}), hold@FF "
               f"{fmt(w.get('final_hold_FF'))} ps (policy {fmt(w.get('policy_hold_FF'))}); stand-in worst "
               f"{fmt(s.get('standin_worst_setup_ps'))} / {fmt(s.get('standin_worst_hold_ps'))} ps")
    if s.get("xtalk"):
        dr = s.get("derates", {})
        L += ["", f"Margins on top of policy (833.333 ps, 60/25 ps unc): crosstalk {s['xtalk']['setup_ps']} ps setup / "
                  f"{s['xtalk']['hold_ps']} ps hold per seam (L {s['xtalk']['seam_len_um']} um); cell derate late "
                  f"{dr.get('cell_late')} (OCV x IR {dr.get('ir_factor')}) / early {dr.get('cell_early')}; IR "
                  f"{(s.get('ir') or {}).get('mode')} (PDNSim: {(s.get('ir') or {}).get('pdnsim')})."]
    if s.get("seam_groups"):
        L += ["", "| seam group | setup@SS final (policy) | hold@FF final (policy) |", "|---|---|---|"]
        for r in sorted(s["seam_groups"], key=lambda r: (r["final_setup_SS"] if r["final_setup_SS"] is not None else 1e9))[:10]:
            L.append(f"| {r['seam']} | {fmt(r['final_setup_SS'])} ({fmt(r['policy_setup_SS'])}) | "
                     f"{fmt(r['final_hold_FF'])} ({fmt(r['policy_hold_FF'])}) |")
    dl = d.get("delta")
    L += [""]
    if dl:
        ch = ", ".join(f"{k} {v}" for k, v in dl["status_changes"].items()) or "no gate status change"
        mm = ", ".join(f"{k} {v:+g}" for k, v in dl["metrics"].items()) or "no metric change"
        L.append(f"Delta vs {str(dl['prev_sha'])[:10]}: {ch}; {mm}.")
    else:
        L.append("Delta: no previous run.")
    return "\n".join(L) + "\n"


def summary_md(run):
    L = [f"# DIE-CI {run['date']} main {run['sha'][:10]} ({run['mode']}) — {run['verdict']}", "",
         f"host {run['host']}, {run['seconds']} s; previous run {run.get('prev_sha') or '-'}", "",
         "| die | verdict | G0 | G0C | xdie | G2 | census | latency | die STA (worst final setup / hold ps) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for n, d in run["dies"].items():
        g = d["gates"]

        def s(k):
            return (g.get(k) or {}).get("status", "-").split(" (")[0]
        w = (g.get("sta") or {}).get("worst") or {}
        L.append(f"| {n} | {d['verdict']} | {s('g0')} | {s('g0c')} ({fmt(g['g0c'].get('errors'))}) | {s('xdie')} "
                 f"({fmt(g['xdie'].get('errors'))}) | {s('g2')} | {s('census')} | {s('latency')} | {s('sta')} "
                 f"({fmt(w.get('final_setup_SS'))} / {fmt(w.get('final_hold_FF'))}) |")
    for n in run.get("absent", []):
        L.append(f"| {n} | NOT PRESENT (plan not on this sha) | | | | | | | |")
    L += ["", "Per-die detail: `<die>.md` / `<die>.json`. Gates: G0 and G0C from one check.py --completeness run; xdie "
              "= PLAN-TOOL5 in-die rules + xdie_io.py rack pairing; G2 = g2.py die + 5 worst partitions; die STA = "
              "die_sta.py ILM sub-top with DIE-CI margins (crosstalk, OCV, IR) on top of the AGENTS.md policy."]
    return "\n".join(L) + "\n"


def cmd_run(a):
    repo = Path(a.repo).resolve()
    a.sha = a.sha or git(repo, "rev-parse", "HEAD") or "unknown"
    date = a.date or datetime.datetime.now().strftime("%Y-%m-%d")
    name = f"{date}_{a.sha[:12]}"
    root = Path(a.out) if os.path.isabs(a.out) else repo / a.out
    rd = root / name
    work = rd / "work"
    work.mkdir(parents=True, exist_ok=True)
    margins = load_margins(a.margins if os.path.isabs(a.margins) else repo / a.margins)
    views_reg = repo / a.views if not os.path.isabs(a.views) else Path(a.views)
    views = json.loads(views_reg.read_text()).get("dies", {}) if views_reg.is_file() else {}
    prev = None
    if a.prev == "auto":
        pf = find_prev(root, name)
        prev = json.loads(pf.read_text()) if pf else None
    elif a.prev and a.prev != "none" and Path(a.prev).is_file():
        prev = json.loads(Path(a.prev).read_text())
    plans = resolve_plans(repo, a.plan)
    names = list(plans) if a.plan else [d["name"] for d in DIES]
    sel = [n for n in names if n in plans and (not a.dies or n in a.dies.split(","))]
    absent = [n for n in names if n not in plans and (not a.dies or n in a.dies.split(","))]
    g2_mode = a.g2
    if g2_mode == "auto" and a.mode == "nightly":
        g2_mode = "all"
    t0 = time.time()
    xsys = {}
    (work / "xdie").mkdir(exist_ok=True)
    for sd in ([] if a.plan else SYSTEMS):
        r = run_xdie_io(repo, sd, plans, work / "xdie")
        r["_dies"] = sorted(set((sd.get("roles") or {}).values()))
        if not r["status"].startswith("N/A (die"):
            xsys[sd["name"]] = r
    dies = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        fut = {ex.submit(run_die, repo, n, plans[n], work / n, a, (prev or {}).get("dies", {}).get(n), g2_mode,
                         views, margins, xsys): n for n in sel}
        for f in cf.as_completed(fut):
            n = fut[f]
            try:
                dies[n] = f.result()
            except Exception as e:      # a crashed die is reported, never silently dropped
                dies[n] = dict(schema=SCHEMA, die=n, plan=str(plans[n]), sha=a.sha, gates={}, verdict="ERROR",
                               error=f"{type(e).__name__}: {e}")
    dies = {n: dies[n] for n in sel}
    run = dict(schema=SCHEMA, date=date, sha=a.sha, mode=a.mode, host=socket.gethostname(),
               started=datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
               seconds=round(time.time() - t0, 1), prev_sha=(prev or {}).get("sha"), g2_mode=g2_mode,
               sta_tool=sta_available(repo), margins=margins, systems={k: {kk: vv for kk, vv in v.items() if kk != "_dies"}
                                                                     for k, v in xsys.items()},
               absent=absent, dies=dies)
    run["verdict"] = "FAIL" if any(d["verdict"] in ("FAIL", "ERROR") for d in dies.values()) else \
        ("INCOMPLETE" if any(d["verdict"] != "PASS" for d in dies.values()) else "PASS")
    write_run(rd, run)
    print(f"DIE-CI {run['verdict']}: {rd / 'SUMMARY.md'}")
    for n, d in dies.items():
        print(f"  {n}: {d['verdict']}  " + "  ".join(f"{k}={(v or {}).get('status', '-').split(' (')[0]}"
                                                    for k, v in d.get("gates", {}).items()))
    return 0


def write_run(rd, run):
    rd = Path(rd)
    (rd / "die_ci.json").write_text(json.dumps(run, indent=1) + "\n")
    for n, d in run["dies"].items():
        (rd / f"{n}.json").write_text(json.dumps(d, indent=1) + "\n")
        if d.get("gates"):
            (rd / f"{n}.md").write_text(die_md(d))
        else:
            (rd / f"{n}.md").write_text(f"# DIE-CI {n} — ERROR\n\n{d.get('error')}\n")
    (rd / "SUMMARY.md").write_text(summary_md(run))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--repo", default=str(HERE.parent.parent))
    r.add_argument("--sha")
    r.add_argument("--date")
    r.add_argument("--out", default="results/die_ci")
    r.add_argument("--dies")
    r.add_argument("--plan", action="append", help="NAME=PATH: run these plans instead of the DIES list")
    r.add_argument("--mode", choices=("commit", "nightly", "manual"), default="manual")
    r.add_argument("--g2", choices=("auto", "all", "none"), default="auto")
    r.add_argument("--sta", choices=("auto", "none"), default="auto")
    r.add_argument("--sta-threads", type=int, default=8)
    r.add_argument("--views", default="tools/die_plan/die_ci_views.json")
    r.add_argument("--views-root")
    r.add_argument("--margins", default="tools/die_plan/die_ci_margins.json")
    r.add_argument("--prev", default="auto")
    r.add_argument("--jobs", type=int, default=6)
    m = sub.add_parser("margins")
    m.add_argument("--derive", action="store_true")
    m.add_argument("--libdir", default=os.path.expanduser("~/.cache/opentallas/asap7_nldm"))
    m.add_argument("--base", default=str(HERE / "die_ci_margins.json"))
    m.add_argument("--out")
    s = sub.add_parser("stage-views")
    s.add_argument("--views", default=str(HERE / "die_ci_views.json"))
    s.add_argument("--host", required=True)
    s.add_argument("--dest", required=True)
    w = sub.add_parser("render")
    w.add_argument("run_dir")
    c = sub.add_parser("_sta")
    for k in ("--repo", "--plan", "--work", "--margins-json", "--modules"):
        c.add_argument(k, required=True)
    c.add_argument("--threads", type=int, default=8)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "_sta":
        return cmd_sta_child(a)
    if a.cmd == "margins":
        base = json.loads(Path(a.base).read_text()) if Path(a.base).is_file() else None
        mm = derive_margins(a.libdir, base) if a.derive else (base or DEFAULT_MARGINS)
        check_margins(mm)
        mm["derived"] = dict(derates=derates(mm), xtalk_default=xtalk_ps(mm), ir=dict(zip(("factor", "sensitivity",
                                                                                         "drop_frac"), ir_factor(mm))))
        txt = json.dumps(mm, indent=1) + "\n"
        if a.out:
            Path(a.out).write_text(txt)
        print(txt)
        return 0
    if a.cmd == "stage-views":
        res = stage_views(a.views, a.host, a.dest)
        print(json.dumps(res, indent=1))
        return 0 if all(x["ok"] for x in res) else 1
    if a.cmd == "render":
        run = json.loads((Path(a.run_dir) / "die_ci.json").read_text())
        write_run(a.run_dir, run)
        return 0


if __name__ == "__main__":
    sys.exit(main())
