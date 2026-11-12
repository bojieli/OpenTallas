"""Partition physical kits (TOPDOWN-PLAN step 3b) and the die assembly kit (step 3d) from die_plan.json.

    python3 tools/die_plan/gen.py phys PLAN.json --out DIR [--rtl-root REPO] [--types t1,t2] [--util U]
    python3 tools/die_plan/gen.py assembly PLAN.json --out DIR --views VIEWDIR

Partition kit DIR/<type>/ (a self-contained ORFS design: mount it at /work, `make DESIGN_CONFIG=/work/config.mk`):
  config.mk     DIE_AREA = the exact plan outline; CORE_AREA inset by CORE_MARGIN_UM (row/site aligned); signals
                M2..partition_signal_max; IO_CONSTRAINTS = io.tcl; PDN_TCL = pdn.tcl; sources copied into rtl/.
  io.tcl        one place_pin per pin bit at the EXACT plan coordinate and layer (schema.pin_positions of the port
                bound to the bus, converted to the type frame).  clk / arst_n are interior pins at the type's clock /
                reset tap (layer CLK_PIN_LAYER, the top partition layer) where the die spine drops onto them.
  pdn.tcl       M1/M2 follow-pins (0.54 pitch), M5/M6 stripes and M7 stripes exported as pins, every pitch dividing the
                die grid (8.64 um) with symmetric offsets: in every R0/MX/MY/R180 instance the stripes sit at the same
                die coordinates, so the die PG (M8/M9 straps, assembly kit) is continuous across abutment.
  constraint.sdc  clk at the plan period; IO relative to a virtual clock with source latency = the clock insertion
                budget (250 ps): a neighbour's boundary flop has the budgeted insertion by contract.  Input / output
                delay = IO_BUDGET x period (0.2 T, the repo's die-context default).
  budget.json   the partition's contract: outline, pins, insertion target +/- tolerance, pin-to-register p90 limit.
Assembly kit DIR/die/: the die top (gen_rtl.die_top), partitions as macros at their exact origin/orient (halo 0),
no standard cells besides the die top's own (none), PDN = die.pg grid on M8/M9 strapping the partitions' M7 pins,
routing of the clock spine and the abutment nets only, then a die STA script over the partitions' routed netlists +
SPEF (sta_die.tcl): timing paths through the face boundary flops.
"""
import hashlib as _hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

import cores as _CR
import schema as S
import taps as T
from schema import DIE_PART



def _rtl_lint_dead_output_vars():
    modules = os.environ.get("OT_RTL_LINT_DEAD_OUTPUT_MODULES", "").split()
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", m) for m in modules):
        raise ValueError("OT_RTL_LINT_DEAD_OUTPUT_MODULES requires module identifiers")
    return ["export OT_RTL_LINT_DEAD_OUTPUT_MODULES = " + " ".join(modules)] if modules else []


def _lec_frontend_vars():
    key = "OT_LEC_SLANG_UNROLL_LIMIT"
    value = os.environ.get(key)
    if value is None:
        return []
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError(f"{key} must be a positive finite integer")
    return [f"export {key} = {int(value)}"]


def _common_flow_file(name, repo):
    """physical/common_flow/<name> of checkout `repo`, from git HEAD in a sparse checkout without it
    (common_flow_src.py, DIE-KV-62 11-02); a copy of this module without the helper: the plain path."""
    try:
        from common_flow_src import common_flow_file
    except ImportError:
        return Path(repo) / "physical/common_flow" / name
    return common_flow_file(name, repo)

CORE_MARGIN_UM = 4.32        # multiple of row 0.27 and site 0.054
IO_BUDGET = 0.2
PIN_LEN_UM = 0.192
LAYER_W = dict(M2=0.018, M3=0.018, M4=0.024, M5=0.024, M6=0.032, M7=0.032, M8=0.04, M9=0.04)


# DIE-KV-63 11-03 (default-on, no-op on legal kits): a FIRM CLAND cell that the resizer upsized IN PLACE after packing
# (repair_design / timing GPL resize FIRM cells, they do not move them) can overlap a TAPCELL or another fixed cell; DPL
# cannot move a FIRM cell, so 3_5 fails DPL-0033 (KV io_cor: 19 dsel INVx1 -> INVx2 over TAPCELLs under the legacy no-fit
# form, which io_cor needs because the resize reserve leaves no status site). Only those overlapping CLAND cells go back
# to PLACED, so DPL moves each to the nearest free site; every CLAND cell that still fits stays FIRM.
CLAND_RELEASE_GROWN_TCL = """
set cg_rows [dict create]
foreach cg_i [$ff_blk getInsts] {
 if {[$cg_i getPlacementStatus] ni {FIRM LOCKED FIXED COVER}} continue
 if {[[$cg_i getMaster] isBlock]} continue
 set cg_b [$cg_i getBBox]
 dict lappend cg_rows [$cg_b yMin] [list [$cg_b xMin] [$cg_b xMax] $cg_i]
}
set cg_bad [dict create]
dict for {cg_y cg_l} $cg_rows {
 set cg_px -1; set cg_pi ""
 foreach cg_e [lsort -integer -index 0 $cg_l] {
  lassign $cg_e cg_x0 cg_x1 cg_i
  if {$cg_pi ne "" && $cg_x0 < $cg_px} {
   foreach cg_c [list $cg_i $cg_pi] {
    if {[$cg_c getPlacementStatus] eq "FIRM" && [string match *u_cland_* [$cg_c getName]]} { dict set cg_bad [$cg_c getName] $cg_c }
   }
  }
  if {$cg_x1 > $cg_px} { set cg_px $cg_x1; set cg_pi $cg_i }
 }
}
dict for {cg_n cg_c} $cg_bad { $cg_c setPlacementStatus PLACED }
puts "OT_CLAND released [dict size $cg_bad] FIRM cland cells grown into an occupied site (in-place resize) for DPL"
"""


def _dpl_args(budgets, tn=None, diamond=False, landing=False, outline=None):
    """FLOW-7 10-30: plan budgets.dpl_legalizer="diamond" -> ORFS DETAIL_PLACEMENT_ARGS lines; absent = [] (kit unchanged).
    DIE-KV-63 11-03: budgets.dpl_legalizer_types names the types (or unsplit base names) that get the diamond legalizer
    while the plan-wide key is absent (KV io_cor 3_5: negotiation stalled at 122 illegal repair buffers / relay flops
    inside FIRM ring bands for 1400 iterations; diamond legal in one pass).
    DIE-QC-65/KITS 11-03: diamond=True (gen phys --dpl-diamond TYPES, per-type CLI opt-in) gives the same line for that kit:
    QC sle_hc2__clcc5e3e61 negotiation DPL stalled at 5,139 illegal cells for 1,400 iterations beside a 35,887-cell FIRM
    landing band 55 um deep, then bad optional access; the diamond legalizer on the same 3_4 DB passes check_placement
    in 434 s (max displacement 35.9 um, HPWL +4 %).
    DIE-QC-66/PLAN 11-03 (DPL class, default-on per OWNER 12.27 b): a kit with FIRM landing bands (landing=True: the
    type has a clock landing_contract) legalizes with the diamond legalizer, and every kit-level diamond call gets the
    whole kit outline as its search window (outline=(w, h) um -> -max_displacement {w h}).  The OpenROAD default window
    (+-500 sites = 27 um, +-100 rows) is smaller than a QC face block (FIRM ring cells + pin registers, ~42 x 55 um at
    ~87 % row use): repair_design wire buffers (BUFx12f/16f, 0.97/1.19 um) dropped inside it had no free row segment
    within 27 um (largest gap 0.918 um) -> DPL-0034/0036 (slw_st_b_v2 13, sle_hc1 61 cells), and the negotiation
    legalizer stalls on the same blocks (DPL-0033).  Diamond places nearest-first, so a cell that finds a site inside the
    default window lands on the same site; the wider window only reaches past a full block.
    DIE-HBM-97 11-09 (COORD NEWFAIL q_b100__physical_v1 197e741898c1, 3_5 'DPL-0312 257 edge spacing + 15 padding
    violations', DPL-0201, then detail_place.tcl:46 'bad optional access'; the same class on q_b002, q_b002pv1, q_b003pv1,
    q_b011pv1, q_su00pv1, q_su10, q_su20, each fixed one by one with --dpl-diamond / dpl_legalizer_types): a kit whose
    type carries a partition FT reservation (FT station flops and repair buffers between macro walls and reserved
    tracks) counts like a landing kit (landing=True), so every fresh gen of such a type gets the diamond legalizer.
    budgets.dpl_legalizer_off_types keeps the ORFS default for named types."""
    v=budgets.get("dpl_legalizer")
    if v is None and tn is not None:
        on=list(budgets.get("dpl_legalizer_types") or [])
        if tn in on or tn.split("__")[0] in on:v="diamond"
    if v is None and diamond:v="diamond"
    if v is None and landing and not _dpl_off(budgets, tn):v="diamond"
    if v is None:return []
    if v!="diamond":raise SystemExit(f"gen phys: budgets.dpl_legalizer {v!r} is not 'diamond'")
    if outline is None:return ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]
    w,h=(int(math.ceil(float(x))) for x in outline)
    return [f"export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer -max_displacement {{{w} {h}}}"]


def _dpl_off(budgets, tn):
    """budgets.dpl_legalizer_off_types: types (or unsplit base names) that keep the ORFS default negotiation DPL
    although they carry FIRM landing bands (explicit plan choice; DIE-QC-66/PLAN 11-03 DPL class default-on)."""
    off=list(budgets.get("dpl_legalizer_off_types") or [])
    return tn is not None and (tn in off or tn.split("__")[0] in off)


def _cland_pinslot(budgets, tn, extra=()):
    """FLOW-11 10-30: ring slot flops fit next to their own bus-bit pin (OT_CLAND_PINSLOT=1).
    DEFAULT-ON since AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 b: class fixes land enabled for all dies; a kit without
    landing-ring bands is unchanged by it). The legacy band-cursor fill is an explicit plan choice:
    budgets.cland_pinslot_off_types names the types (or unsplit base names) that keep it.  budgets.cland_pinslot_types
    and gen phys --cland-pinslot (extra) are kept for old plans/configs; they can only add, never remove."""
    off = list(budgets.get("cland_pinslot_off_types") or [])
    if tn in off or tn.split("__")[0] in off:
        return False
    return True



def _relay_mid_fit(budgets, tn):
    """S81-TYPES-5 11-07 CHANNEL class (relay_mid.tcl FIT), opt-in three ways, absent = unchanged kits: plan-wide
    budgets.relay_mid_fit, per type budgets.relay_mid_fit_types (types or unsplit base names), or per kit-wave row
    through item_env (GEN env OT_RELAY_MID_FIT=1), so a pilot or a class batch needs no plan event."""
    if os.environ.get("OT_RELAY_MID_FIT") == "1" or budgets.get("relay_mid_fit"):
        return True
    on = list(budgets.get("relay_mid_fit_types") or [])
    return tn is not None and (tn in on or tn.split("__")[0] in on)


def _gutter_block_um(budgets, tn):
    """S81-TYPES-5 11-07 NARROW-GUTTER class (gutter_block.tcl + gutter_release.tcl): the gap threshold in um, or None.
    GEN env OT_GUTTER_BLOCK_UM (kit-wave item_env) wins; else budgets.gutter_block_um, for every macro type, or only
    for budgets.gutter_block_types when that list is given."""
    v = os.environ.get("OT_GUTTER_BLOCK_UM")
    if v:
        return float(v) if float(v) > 0 else None
    v = budgets.get("gutter_block_um")
    if not v:
        return None
    on = budgets.get("gutter_block_types")
    if on is not None and not (tn is not None and (tn in on or tn.split("__")[0] in on)):
        return None
    return v


def _gutter_block_min_span_um(budgets):
    """S81-TYPES-7-COLH 11-08 (class C ROM walls): only gaps whose facing span is >= this many um get a gutter
    blockage (GEN env OT_GUTTER_BLOCK_MIN_SPAN_UM wins, else budgets.gutter_block_min_span_um); None = every gap
    (the 11-07 behaviour).  A long span picks the gap between two 221-um ROM-element walls and leaves the short
    ROM/relay gaps, whose logic must stay in place (COLH-1 vS2: blocking every gap < 45 um doubled the wire)."""
    v = os.environ.get("OT_GUTTER_BLOCK_MIN_SPAN_UM") or budgets.get("gutter_block_min_span_um")
    return float(v) if v and float(v) > 0 else None


# FW-ROWS-1 11-09 (DIE-QC-97, COORD class: sle_fw_v2, slw_fw_v3, slw_fw_v2, slw_fw_v1 all GRT-0116 in the N-face
# x_ctl_i / cws0_i ring_ff column strip): every sle_fw* / slw_fw* type takes every 2nd strip row by default.  A plan
# cland_strip_rows_types entry (type or base) still wins, and 1 opts a type out; other families are unchanged.
CLAND_STRIP_ROWS_FAMILY_RE = re.compile(r"^(sle|slw)_fw_")
CLAND_STRIP_ROWS_FAMILY_DEFAULT = 2


def _cland_strip_rows(budgets, tn):
    """DIE-QC-97 11-09 opt-in: the OT_CLAND_STRIP_ROWS of type tn from budgets.cland_strip_rows_types (type, then its
    unsplit base name) else budgets.cland_strip_rows; None (absent or 1) = unchanged kit.  landing_placement.tcl takes
    every n-th row of the N/S ring_ff column strip, clamped to what the band depth fits, so the pin-facing band edge
    is 1/n FIRM instead of 100 % (sle_fw_v2__cl69f5e854 x_ctl_i / cws0_i: 3304 / 2721 flops in an 11.61-um strip,
    GRT-0116 with its 3 overflow edges in that strip's top gcell row)."""
    per = budgets.get("cland_strip_rows_types") or {}
    v = per.get(tn, per.get(tn.split("__")[0])) if tn is not None else None
    if v is None and tn is not None and CLAND_STRIP_ROWS_FAMILY_RE.match(tn):
        v = CLAND_STRIP_ROWS_FAMILY_DEFAULT
    if v is None:
        v = budgets.get("cland_strip_rows")
    return int(v) if v and int(v) > 1 else None


def _cland_pinslot_dense(budgets, tn):
    """DIE-KV-62/stations 11-02 opt-in: budgets.cland_pinslot_dense_types names the types (or unsplit base names) whose
    y-column pinslot rows pack the ring slot flops body to body (OT_CLAND_PINSLOT_DENSE=1, landing_placement.tcl);
    absent/empty = unchanged kits."""
    on = list(budgets.get("cland_pinslot_dense_types") or [])
    return tn in on or tn.split("__")[0] in on

# KW-FIX-24/CONSKIT 11-06 (OWNER standing rule, COORD 21:5x): a type row that failed congestion or setup gets a
# conservative re-kit in the next batch relaunch.  Opt-in per row through the kit wave item_env (gen.py phys env),
# OFF by default: without OT_CONS_KIT=1 the kit (config.mk and every file) is byte-identical.
#   OT_CONS_KIT=1            enable
#   OT_CONS_UTIL=U           PLACE_DENSITY = min(kit value, U)            (default 0.35)
#   OT_CONS_MAX_LAYER=Mk     signal routing ceiling                       (default M6)
#   OT_CONS_PIN_LAYER_ADJ=A  GRT capacity cut on the layers kept above Mk only for pin access (default 0.9)
#   OT_MIDFLOP_RE=re         POST_GLOBAL_PLACE hook cons_midflop.tcl: matching one-sink output flops move to the midpoint of their wire (no netlist change)
# The ceiling never drops below the highest layer the type's own pins use (io.tcl place_pin: face buses, clock /
# reset pins on partition_signal_max, face_layers M8, bump pins; signal pins of staged hard-macro LEFs): GRT stops
# with "Pin .. does not have geometries below the max routing layer" otherwise.  Those pin-only layers stay in
# MAX_ROUTING_LAYER and get set_global_routing_layer_adjustment A in the PRE_GLOBAL_ROUTE hook (cons_grt_pre.tcl), so
# GRT/DRT use them for the pin stub, not for the net.  The density cap is floored at GPL's own lower bound + 0.01
# (cons_gpl_pre.tcl): a target below the cell area (fixed plan outline) is a GPL-0302 stop, not a conservative form.
# Registered faces need no switch: every port is registered at both pins by construction (schema.py conventions,
# face_flops.tcl FIRM at the pin); an extra stage per face is a plan event (lane fixed_cycles / bus pads).
# CONS-OVERMACRO-1 11-09 (DIE-QC-97, GRT-0116 of the CONS kits slw_sc_v3, sle_su_l0 x2, sle_su_l1): a staged hard
# macro whose LEF OBS reaches Mk leaves only M(k+1) (one direction) and M(k+2) (the other) over its whole area, so the
# signal ceiling never drops below M(k+2) (capped at the kit top) and those layers get no pin-access cut.  With the SU
# lanes / SC core (OBS M1-M5) the M7 cut to 10 % left every vertical net that crosses a macro (lane3 c_i feed over
# lane2, the M7-planned rsn/rsf ft over lanes 4-7, the x_su_l1_ctl ft past u_core) about 0.1 x 6000 tracks over a
# 415-um lane, so GRT piled them into the 13-19 um side channels between macro and die edge.
CONS_KIT_UTIL = 0.35
CONS_KIT_MAX_LAYER = "M6"
CONS_KIT_PIN_LAYER_ADJ = 0.9
_CONS_PLACE_PIN_LAYER = re.compile(r"^\s*place_pin\b[^\n]*?\s-layer\s+(M\d+)\b", re.M)


def cons_kit_settings(env=None):
    """OT_CONS_* env -> dict(util, max_layer, pin_layer_adj), or None when OT_CONS_KIT is unset / 0."""
    env = os.environ if env is None else env
    on = str(env.get("OT_CONS_KIT", "")).strip()
    if on in ("", "0"):
        return None
    if on != "1":
        raise ValueError(f"OT_CONS_KIT={on!r}: 1 enables the conservative kit, 0/unset leaves it off")
    util = float(env.get("OT_CONS_UTIL") or CONS_KIT_UTIL)
    if not 0.0 < util <= 1.0:
        raise ValueError(f"OT_CONS_UTIL={util}: must be in (0, 1]")
    layer = str(env.get("OT_CONS_MAX_LAYER") or CONS_KIT_MAX_LAYER)
    if not re.fullmatch(r"M[2-9]", layer):
        raise ValueError(f"OT_CONS_MAX_LAYER={layer!r}: a routing layer M2..M9")
    adj = float(env.get("OT_CONS_PIN_LAYER_ADJ") or CONS_KIT_PIN_LAYER_ADJ)
    if not 0.0 <= adj < 1.0:
        raise ValueError(f"OT_CONS_PIN_LAYER_ADJ={adj}: in [0, 1) (1 leaves no track for the pin access itself)")
    return dict(util=util, max_layer=layer, pin_layer_adj=adj)


def _lef_signal_pin_layers(path):
    """metal layers of the non-PG PIN shapes of a LEF (macro signal / clock pins)."""
    out, pin, pg, cur = set(), None, False, set()
    for line in Path(path).read_text(errors="replace").splitlines():
        tok = line.replace(";", " ").split()
        if not tok:
            continue
        if pin is None:
            if tok[0] == "PIN" and len(tok) > 1:
                pin, pg, cur = tok[1], False, set()
            continue
        if tok[0] == "END" and len(tok) > 1 and tok[1] == pin:
            if not pg:
                out |= cur
            pin = None
        elif tok[0] == "USE" and len(tok) > 1 and tok[1].upper() in ("POWER", "GROUND"):
            pg = True
        elif tok[0] == "LAYER" and len(tok) > 1 and re.fullmatch(r"M\d+", tok[1]):
            cur.add(tok[1])
    return out


def _lnum(ln):
    return int(ln[1:])


def _lef_obs_top(path):
    """highest metal layer of the OBS section(s) of a LEF (hard macro routing obstruction), or None."""
    top, obs = None, False
    for line in Path(path).read_text(errors="replace").splitlines():
        tok = line.replace(";", " ").split()
        if not tok:
            continue
        if tok[0] == "OBS":
            obs = True
        elif obs and tok[0] == "END" and len(tok) == 1:
            obs = False
        elif obs and tok[0] == "LAYER" and len(tok) > 1 and re.fullmatch(r"M\d+", tok[1]):
            if top is None or _lnum(tok[1]) > _lnum(top):
                top = tok[1]
    return top


def cons_kit_apply(cfg, kd, cons, io_text, top, mlef=()):
    """rewrite the kit config lines in place for the conservative form; write cons_kit.json + the two hook wrappers."""
    pins, obs = {}, {}
    for ln in _CONS_PLACE_PIN_LAYER.findall(io_text):
        pins.setdefault(ln, "io.tcl place_pin")
    for p in mlef:
        f = Path(kd) / "macros" / Path(p).name
        if f.is_file():
            for ln in _lef_signal_pin_layers(f):
                pins.setdefault(ln, f"macro LEF {f.name}")
            ot = _lef_obs_top(f)
            if ot:
                obs[f.name] = ot
    floor = max(pins, key=_lnum) if pins else "M2"
    want = cons["max_layer"]
    # CONS-OVERMACRO-1: one routing layer pair above the highest macro OBS stays a signal layer (no pin-access cut)
    over = f"M{_lnum(max(obs.values(), key=_lnum)) + 2}" if obs else None
    sig = max(want, over, key=_lnum) if over else want
    if _lnum(sig) > _lnum(top):
        sig = top
    new_max = max(sig, floor, key=_lnum)
    if _lnum(new_max) > _lnum(top):        # the cap only lowers; a ceiling above the kit top is the kit top
        new_max = top
    access = [f"M{k}" for k in range(_lnum(sig) + 1, _lnum(new_max) + 1)]
    i_max = cfg.index(f"export MAX_ROUTING_LAYER = {top}")
    cfg[i_max] = f"export MAX_ROUTING_LAYER = {new_max}"
    i_pd = next(k for k, c in enumerate(cfg) if c.startswith("export PLACE_DENSITY = "))
    pd0 = float(cfg[i_pd].split("=", 1)[1])
    pd = min(pd0, cons["util"])
    cfg[i_pd] = f"export PLACE_DENSITY = {pd:g}"
    gpl = "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl"
    cfg[cfg.index(gpl)] = "export PRE_GLOBAL_PLACE_TCL = /work/cons_gpl_pre.tcl"
    mf = os.environ.get("OT_MIDFLOP_RE")
    if mf:  # TYPE-CONS-2: register at the midpoint of a one-cycle transport (kit-local placement, no netlist change)
        assert not any(c.startswith("export POST_GLOBAL_PLACE_TCL") for c in cfg), "OT_MIDFLOP_RE: POST_GLOBAL_PLACE_TCL in use"
        cfg += ["export POST_GLOBAL_PLACE_TCL = /work/cons_midflop.tcl", f"export OT_MIDFLOP_RE = {mf}"]
        shutil.copyfile(Path(__file__).with_name("cons_midflop.tcl"), Path(kd) / "cons_midflop.tcl")
    shutil.copyfile(Path(__file__).with_name("cons_gpl_pre.tcl"), Path(kd) / "cons_gpl_pre.tcl")
    cfg += ["# KW-FIX-24/CONSKIT: conservative re-kit (OT_CONS_KIT=1 at generation; cons_kit.json)",
            "export OT_CONS_KIT = 1", f"export OT_CONS_UTIL = {cons['util']:g}",
            f"export OT_CONS_SIGNAL_MAX = {sig}"]
    # TYPE-CONS-4 11-07: ring flops are FIRM, so the density cap above never reaches them; thin their strip too
    # (landing_placement.tcl).  OT_CONS_STRIP_ROWS=1 keeps the packed strip.
    strip = int(os.environ.get("OT_CONS_STRIP_ROWS") or 3)
    if strip > 1:
        cfg += [f"export OT_CLAND_STRIP_ROWS = {strip}"]
    grt = None
    if access:
        grt = next(c for c in cfg if c.startswith("export PRE_GLOBAL_ROUTE_TCL = "))
        cfg[cfg.index(grt)] = "export PRE_GLOBAL_ROUTE_TCL = /work/cons_grt_pre.tcl"
        cfg += [f"export OT_CONS_BASE_PRE_GRT = {grt.split('=', 1)[1].strip()}",
                f"export OT_CONS_PIN_LAYERS = {' '.join(access)}",
                f"export OT_CONS_PIN_LAYER_ADJ = {cons['pin_layer_adj']:g}"]
        shutil.copyfile(Path(__file__).with_name("cons_grt_pre.tcl"), Path(kd) / "cons_grt_pre.tcl")
    rec = {"schema": "opentallas.cons_kit.v1", "enabled": True, "source": "OT_CONS_KIT=1 (gen.py phys env)",
           "cland_strip_rows": strip,
           "place_density": {"kit": pd0, "cap": cons["util"], "used": pd,
                             "floor": "GPL uniform-density lower bound + 0.01 (cons_gpl_pre.tcl, logged OT_CONS_KIT)"},
           "signal_max_layer": {"requested": want, "kit_top": top, "pin_floor": floor,
                                "macro_obs_top": {k: obs[k] for k in sorted(obs)}, "over_macro_floor": over,
                                "signal_max": sig,
                                "pin_layers": {k: pins[k] for k in sorted(pins, key=_lnum)},
                                "max_routing_layer": new_max, "pin_access_layers": access,
                                "pin_access_adjustment": cons["pin_layer_adj"] if access else None},
           "registered_faces": "by construction: every port has a boundary flop at both pins (schema.py), placed FIRM "
                               "at its pin by face_flops.tcl; an extra stage per face is a plan event (lane "
                               "fixed_cycles / bus pads), not a kit switch",
           "pre_global_route_base": grt.split("=", 1)[1].strip() if grt else None}
    (Path(kd) / "cons_kit.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def _cland_fit_mode(budgets, tn=None):
    """landing_placement fit footprint for CLAND cells -> OT_CLAND_FIT_RESERVE value or None.
    DEFAULT 'resize' since AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 b): FLOW-6 widest-drive-variant footprint, so an in-place
    GPL/repair upsize of a FIRM ring cell cannot grow over a tapcell (DPL-0033: KV io_ft INVx1->x3, HEAD n3_turn
    DFFHQNx1->x2).  budgets.cland_fit_reserve = true keeps the DIE-KV-34 whole-reserved-footprint form ('1');
    budgets.cland_fit_resize = false is the explicit legacy no-fit form; both true fails closed (one value per kit).
    DIE-KV-56 10-31 (KIT-WAVE-7 13:41, KV io_cor 'OT_CLAND no legal ... status:landing_ready_ft10_i' under resize, passed
    without it): budgets.cland_fit_resize_off_types names the types (or unsplit base names) that keep the legacy no-fit
    form while the default stays on for every other type (same pattern as cland_pinslot_off_types)."""
    if budgets.get("cland_fit_resize") and budgets.get("cland_fit_reserve"):
        raise SystemExit("gen phys: budgets.cland_fit_resize and budgets.cland_fit_reserve are exclusive "
                         "(one OT_CLAND_FIT_RESERVE value per kit)")
    if budgets.get("cland_fit_reserve"):
        return "1"
    if budgets.get("cland_fit_resize") is False:
        return None
    off = list(budgets.get("cland_fit_resize_off_types") or [])
    if tn is not None and (tn in off or tn.split("__")[0] in off):
        return None
    return "resize"


def _cland_fit_resize(budgets):
    """back-compat: True when the kit gets OT_CLAND_FIT_RESERVE=resize (see _cland_fit_mode)."""
    return _cland_fit_mode(budgets) == "resize"


def type_pins(P, tn):
    """[(port_name, bit_index, layer, x, y, face)] in the TYPE frame for every bus / slot pin of type tn, from its first
    instance (G0 proves every instance identical)."""
    inst = next(n for n, p in P.parts.items() if p["type"] == tn)
    out = []
    for pid, pr in P.ports.items():
        for side in ("src", "dst"):
            if pr[side]["part"] != inst:
                continue
            df = pr["face"] if (side == "src" or pr["src"]["part"] == DIE_PART) else S.OPP[pr["face"]]
            tf = P.type_face(inst, df)
            w, h = P.ptype(inst)["outline_um"]
            line = S.Plan.rect(P, inst)
            for bit, ln, c in P.port_pins(pid):
                pt = ((line[2] if df == "E" else line[0]), c) if df in "EW" else (c, (line[3] if df == "N" else line[1]))
                x, y = P.to_type(inst, pt)
                # snap the face coordinate exactly onto the type edge
                if tf == "E":
                    x = w
                elif tf == "W":
                    x = 0.0
                elif tf == "N":
                    y = h
                else:
                    y = 0.0
                out.append((pr[side]["bus"], bit, ln, round(x, 4), round(y, 4), tf))
    return out


# face_flops.tcl line that runs the landing placement (FLOW-GEN-1 10-28, DIE-HEAD-9 bug 3: at global scope, where the
# face block's ff_blk/ff_dbu live; a bare `source` inside ORFS's hook proc failed "OT_CLAND missing face placement context")
LANDING_PLACEMENT_HOOK = "uplevel #0 {source /work/landing_placement.tcl}"
RCK_BAND_HOOK = "uplevel #0 {source /work/rck_band.tcl}"
def reset_relay_full(rtl_dir):
    """S81-RCK-4 11-07 (opt-in type key reset_relay_full): the kit copy of ot_dp_rrelay_nl becomes one posedge flop.  Same one
    cycle per relay at every posedge; the hop gets T instead of T/2 and routed FF hold repair covers the tap skew (2.9-mm serdes
    types: 405-um hop q->state TT -251..-430 on the T/2 budget).  The native reset check runs on the canonical cell before this."""
    n = 0
    for f in sorted(Path(rtl_dir).glob("*.sv")):
        txt = f.read_text()
        new, k = re.subn(r"(module ot_dp_rrelay_nl \(input wire clk, input wire d, output reg q\);\n).*?(endmodule)",
                         r"\1    always @(posedge clk) q <= d;\n\2", txt, flags=re.S)
        if k:
            f.write_text(new)
            n += k
    if n != 1:
        raise ValueError(f"reset_relay_full: {n} ot_dp_rrelay_nl definitions in {rtl_dir}, expected 1")


CHAIN_EVEN_HOOK = "source /work/chain_even_cfg.tcl\nsource /work/chain_even.tcl"


def chain_even_cfg(spec):
    """S81-RCK-4 11-07 (opt-in type key chain_even = {chains: [[head_re, stage_re]..], groups: [[name, from_re, [stage_re..],
    cone_re, to_re]..]}): the Tcl config of chain_even.tcl.  Regexes stay in a kit file, not config.mk, so '$' survives make."""
    def tcl(v):
        return "{" + " ".join(tcl(x) for x in v) + "}" if isinstance(v, list) else "{" + v + "}"
    out = [f"set ::ot_chain_res {tcl(spec['chains'])}"]
    if spec.get("groups"):
        out.append(f"set ::ot_chain_groups {tcl(spec['groups'])}")
    return "\n".join(out) + "\n"


def rck_band_exports(P, tn):
    """S81-RCK-3 11-06 (opt-in type key rck_band = {inst, rows}): config.mk exports of rck_band.tcl.  The band top is
    the lower edge of the PHY PG region that holds the receiver macro (no core cell above it); [] when the key is absent."""
    rb = P.types[tn].get("rck_band")
    if not rb:
        return []
    doms = [d for d in phy_pg_domains(P, tn) if rb["inst"] in d[4]]
    if len(doms) != 1:
        raise ValueError(f"type {tn}: rck_band inst {rb['inst']} must sit in exactly one PHY PG domain")
    return [f"export OT_RCK_BAND_INST = {rb['inst']}", f"export OT_RCK_BAND_TOP_UM = {_um(doms[0][3][1])}",
            f"export OT_RCK_BAND_ROWS = {int(rb.get('rows', 4))}"]


def logical_strap_names(t):
    """Declared logical strap buses exist independently of optional physical pin sites."""
    from straps import checked
    return sorted(checked([sp["name"] for sp in (t.get("id_straps", []) or []) +
                           (t.get("count_straps", []) or [])]))


def logical_strap_pin_records(t):
    """Logical port inventory; optional physical coordinates never invent or remove ports."""
    from clock_landings import SCALAR_STRAPS
    logical_strap_names(t)  # enforce declared strap naming and uniqueness
    ids = t.get("id_straps", []) or []
    out = []
    for sp in ids + (t.get("count_straps", []) or []):
        width = sp.get("width")
        if not isinstance(width, int) or isinstance(width, bool) or width < 1:
            raise ValueError("logical strap width must be a positive integer")
        scalar = sp not in ids and sp["name"] in SCALAR_STRAPS
        if scalar and width != 1:
            raise ValueError(f"strap {sp['name']} is scalar; width must be 1")
        out.extend(dict(bus=sp["name"], bit=None if scalar else bit) for bit in range(width))
    return out


def strap_pin_sites(P, tn):
    """[(pin, layer, x, y)] interior pin centres of declared ID/count straps (plan straps[].sites_um, one
    [x, y] per bit, on each strap's layer), or [] when the plan declares no sites (opt-in, DIE-HEAD-5 TILEIO 10-28:
    without sites the strap ports had no pin, port_bind counted them as extra).  Tied per instance at the die top."""
    from clock_landings import SCALAR_STRAPS
    out = []
    ids = P.types[tn].get("id_straps", []) or []
    for sp in ids + (P.types[tn].get("count_straps", []) or []):
        xy = sp.get("sites_um")
        if not xy:
            continue
        if len(xy) != sp["width"] or not sp.get("layer"):
            raise ValueError(f"type {tn}: strap {sp['name']} needs layer and exactly {sp['width']} sites_um")
        # FLOW-GEN-1 10-28 (DIE-HEAD-9 bug 1): a count strap the RTL declares scalar gets a pin without a bit index
        # (io.tcl strap_ca_efall[0] on the scalar port was PPL-0061); id straps are always [w-1:0] vectors (gen_rtl)
        if sp not in ids and sp["name"] in SCALAR_STRAPS:
            if sp["width"] != 1:
                raise ValueError(f"type {tn}: strap {sp['name']} is a scalar RTL port, width must be 1")
            out.append((sp["name"], sp["layer"], float(xy[0][0]), float(xy[0][1])))
            continue
        out += [(f"{sp['name']}[{i}]", sp["layer"], float(x), float(y)) for i, (x, y) in enumerate(xy)]
    return out


def reset_spine_pin_sites(P, tn):
    """[(pin, layer, x, y)] interior pin centres of the bound reset-spine ports of a type (plan reset_spine_pins[]: the
    bind's bound-only ri_*/rs_* wrapper pins, one [x, y] per bit).  DIE-KV-51 10-31 (OWNER): such a pin needs a real
    site, not only a port_bind entry.  [] when the type declares none (kit bytes unchanged)."""
    out = []
    for sp in P.types[tn].get("reset_spine_pins", []) or []:
        xy = sp["sites_um"]
        if len(xy) != sp["width"]:
            raise ValueError(f"type {tn}: reset spine pin {sp['name']} needs exactly {sp['width']} sites_um")
        # DIE-KV-88 11-07: same half-pitch class as FLOW-KITFAIL-2 (a narrow pin off its plan track is DRT-0255 at route:
        # ri_head2_u_score_rst_n, ri_pv_u_g0_j_rst_n on M7 at half a pitch).  A site already on a track keeps its bytes.
        import landing_contract as LC
        for i, (x, y) in enumerate(xy):
            x, y = LC.on_track(P, sp["layer"], float(x), float(y))
            out.append((f"{sp['name']}[{i}]", sp["layer"], x, y))
    return out


def _pin_bus_bit(name):
    """strap pin name -> (bus, bit); a scalar pin (no [i]) -> (name, None)."""
    if "[" not in name:
        return name, None
    return name.split("[")[0], int(name.split("[")[1][:-1])


def plan_pin_records(P, tn, pins, bump_sites=()):
    """[{name, layer, x, y}] pin CENTRES of every pin io.tcl places for type tn, computed from the plan: type_pins edge
    points moved PIN_LEN_UM/2 inward, native infrastructure ports, clock/reset taps, reset outs, landing pins and bump
    sites.  The single source of freeze.json pins_canon_sha256 (COORD 10-27 KV-KITS-7 ruling 3)."""
    t = P.types[tn]
    recs = {}

    def add(n, ln, x, y):
        recs[n] = dict(name=n, layer=ln, x=round(float(x), 4), y=round(float(y), 4))

    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        if f in "EW":
            x = x - PIN_LEN_UM / 2 if f == "E" else x + PIN_LEN_UM / 2
        else:
            y = y - PIN_LEN_UM / 2 if f == "N" else y + PIN_LEN_UM / 2
        add(f"{bus}[{bit}]", ln, x, y)
    import infra_rtl as IR
    for ip in IR.type_ports(t):
        add(ip["name"], ip["layer"], *ip["xy_um"])
    top = P.layer_budget["partition_signal_max"]
    for name, x, y in tap_pins(P, tn) + reset_out_pins(P, tn):
        add(name, top, x, y)
    c = t.get("clock", {}).get("landing_contract") or {}
    edge_in = {e["port"] for e in t.get("clock", {}).get("edge_clocks", [])}
    import landing_contract as LC
    for p in c.get("pins", []):
        if p["name"] not in edge_in:
            # io_tcl places landing pins on their layer tracks; the canonical
            # freeze must describe those same physical centres.
            add(p["name"], p["layer"], *LC.on_track(P, p["layer"], *p["xy_um"]))
    for port, i, ln, cx, cy, pw, ph in bump_sites:
        add(f"{port}[{i}]", ln, cx, cy)
    for name, ln, x, y in strap_pin_sites(P, tn):
        add(name, ln, x, y)
    for name, ln, x, y in reset_spine_pin_sites(P, tn):
        add(name, ln, x, y)
    for name, i, ln, x, y in signal_pad_sites(P, tn):
        add(f'{name}[{i}]', ln, x, y)
    import pad_clock as PC
    for p in PC.pins(P, tn):
        add(p['name'] + '[0]', p['layer'], *p['xy_um'])
    return list(recs.values())


def audit_pin_records(face_rows, planned_rows):
    """Keep boundary-flop rows separate from the full planned physical pin audit."""
    from pin_audit import AUDIT_EXCLUDED, pin_key
    rows = [dict(p) for p in face_rows]
    declared = {p["name"]: p for p in planned_rows}
    for row in rows:
        for key in ("native_rects", "native_rects_review", "declared_native_shape"):
            if key in declared.get(pin_key(row), {}):
                value = declared[pin_key(row)][key]
                if key in row and row[key] != value:
                    raise ValueError("conflicting native pin contract: " + pin_key(row))
                row[key] = value
    seen = {pin_key(p) for p in rows}
    if len(seen) != len(rows):
        raise ValueError("duplicate face pin in audit metadata")
    planned = {p["name"] for p in planned_rows}
    if len(planned) != len(planned_rows) or not seen <= planned:
        raise ValueError("face pins disagree with canonical physical pin declarations")
    for p in planned_rows:
        name = p["name"]
        if name in seen or AUDIT_EXCLUDED.fullmatch(name):
            continue
        bus, bit = _pin_bus_bit(name)
        rows.append(dict(bus=bus, bit=bit, layer=p["layer"], x=p["x"], y=p["y"], face="island"))
        for key in ("native_rects", "native_rects_review", "declared_native_shape"):
            if key in p: rows[-1][key] = p[key]
    return rows


def signal_pad_sites(P, tn):
    """Declared digital package pad pins, placed on routing tracks; no hard-macro view is implied."""
    import landing_contract as LC
    out = []
    t = P.types[tn]
    for pd in t.get('pads', []):
        if not pd.get('sites_um'):
            continue
        if pd.get('macro_pin') or len(pd['sites_um']) != pd['width'] or not pd.get('layer'):
            raise ValueError(f"type {tn}: pad {pd['name']} needs one site per bit and a layer, without macro_pin")
        for i, (x, y) in enumerate(pd['sites_um']):
            if not (0 <= x <= t['outline_um'][0] and 0 <= y <= t['outline_um'][1]):
                raise ValueError(f"type {tn}: pad {pd['name']} site outside outline")
            x, y = LC.on_track(P, pd['layer'], x, y)
            out.append((pd['name'], i, pd['layer'], x, y))
    return out


def port_bind_pin_records(P, tn, pins, bump_ports=None):
    """Exact top-level inventory, including physically declared landing and constant pins."""
    t = P.types[tn]
    port_pins = [dict(bus=b, bit=i) for b, i, _l, _x, _y, _f in pins]
    port_pins += [dict(bus=n, bit=None) for n, _x, _y in tap_pins(P, tn) + reset_out_pins(P, tn)]
    port_pins += [dict(bus=b["port"], bit=i) for b in (bump_ports or []) for i in range(b["width"])]
    # gen_rtl emits type-level PHY pads directly (distinct from bound hard-IP
    # bump_ports). They remain exact plan ports even without a data-face flop.
    port_pins += [dict(bus=p["name"], bit=i) for p in t.get("pads", []) for i in range(int(p["width"]))]
    import infra_rtl as IR
    port_pins += [dict(bus=p["name"], bit=None) for p in IR.type_ports(t)]
    port_pins += [dict(bus=p["name"], bit=None)
                  for p in t.get("clock", {}).get("landing_contract", {}).get("pins", [])]
    port_pins += logical_strap_pin_records(t)
    port_pins += [dict(bus=_pin_bus_bit(n)[0], bit=_pin_bus_bit(n)[1]) for n, *_ in reset_spine_pin_sites(P, tn)]
    # Forwarded input clocks may also be listed in edge_clocks: same real pin.
    return list({(p["bus"], p["bit"]): p for p in port_pins}.values())


PORT_BUF_AT_PIN_LINE = "\n# PORT-BUF-AT-PIN: output-port drivers onto their pin face, then DPL\nsource /work/port_buf_at_pin.tcl\n"


CORE_INPUT_PLACE_ANCHOR = "\n# QC-NK-HOLD A+P: core-input lockup latches + pipe registers FIRM at their hard-core pin\nsource /work/core_input_anchor.tcl\n"
CORE_INPUT_PLACE_CHAIN = "\n# QC-NK-HOLD A+P: feeding register chains spread to the pipe register (macro-avoiding route)\nsource /work/core_input_chain.tcl\n"


def core_input_place(raw, tn):
    """QC-NK-HOLD 11-11 A+P placement hooks (OWNER 07:39 pipeline cycle, COORD 07:5x APPROVED): True when type tn gets
    declared pipe registers before its core-input lockup latches (bind.core_input_pipe > 0 on any listed module).
    Then core_input_anchor.tcl (end of face_flops.tcl, PRE_GLOBAL_PLACE) puts every u_lk_nk_ latch 2 um and its
    u_pc_nk_ register 6 um outside the core pin it drives (FIRM, released for DPL), and core_input_chain.tcl
    (PRE_RESIZE, after the kit's own PRE_RESIZE hook) spreads the zero-logic register chain feeding each pipe register (u_d/u_lpad/u_r8b_strap/
    u_pd stages) evenly along a macro-avoiding Manhattan route from its head.  cbn_q11 pilots: unanchored A+P TT
    worst -1681; anchored latch only reg->latch -787; anchored latch+reg -1131 at u_pc D (GPL bunched the 10-stage
    u_d10 chain within 150 um of its head, 1350 um last hop) -> pilot10 (spread at PRE_RESIZE, a chain after a hard-core
    output keeps its first stage at the pin) FF PASS -231.9, NK pins +8.2, TT -833.8 (base -824.1, NK-output class).
    Form A alone (pipe 0) is unchanged."""
    import bind as _B
    cfg = ((raw or {}).get("clock") or {}).get("core_input_lockup") or {}
    return any(_B.core_input_pipe(raw, tn, m) > 0 for m in (cfg.get("modules") or {}))


def write_partition_freeze(P, tn, kd, recs, *, private_clock_mesh=None):
    """plan_pins.json (die-plan pin centres) + freeze.json (schema partition_freeze: outline, pins_file, pins_sha256,
    pins_canon_sha256 of the die-plan pins) for kit_contract.pins_canonical; refuses the kit when io.tcl is not that
    pin set with the consumed master-plan slice applied (kit_contract.slice_expected)."""
    import hashlib
    import kit_contract as KC
    kd = Path(kd)
    w, h = P.types[tn]["outline_um"]
    if private_clock_mesh is not None:
        import hhp_clock_mesh_role as HMR
        HMR.validate_private_request(kd)
        private_clock_mesh["actual_source_config"] = HMR.actual_source_config(kd)
        private_clock_mesh["actual_config_sha256"] = HMR.digest((kd / "config.mk").read_bytes())
        (kd / "private_clock_mesh.json").write_text(json.dumps(private_clock_mesh, indent=1) + "\n")
    body = json.dumps(dict(schema="opentallas.die_plan.partition_plan_pins.v1", die=P.name, type=tn,
                           source=("gen_phys.plan_pin_records (die plan)" if private_clock_mesh is None else
                                   "gen_phys plan pins + exact PRIVATE native clock role certificate"), pins=recs), indent=1) + "\n"
    (kd / "plan_pins.json").write_text(body)
    canon = KC._canon(recs, [w, h])
    # 12.7c: a kit that consumed its master-plan slice places the slice-fixed pins where the slice says
    # (master_slice.slice_placements); every other pin is the die-plan pin
    expect = KC._canon(KC.slice_expected(kd, recs), [w, h])
    placed = KC._canon(KC.placed_pins(kd), [w, h])
    if placed != expect:
        raise ValueError(f"type {tn}: io.tcl placed pins canonical {placed[:12]} != plan pins (+ slice) {expect[:12]}")
    fz = dict(schema="opentallas.partition_freeze.v1", die=P.name, type=tn, outline_um=[w, h],
              pins_file="plan_pins.json", pins_sha256=hashlib.sha256(body.encode()).hexdigest(),
              pins_canon_sha256=canon, pins=len(recs))
    if private_clock_mesh is not None:
        fz["private_clock_mesh"] = private_clock_mesh
    # DIE-QC-59 11-01: a partition kit has the same proven boot reset as its die.
    # Core kits already staged this contract; type kits silently used LEC's four-edge
    # default, leaving reset-less pipeline/SRAM write constants unresolved.
    import kit_reset_contract
    source = kit_reset_contract.die_contract(P.name)   # DIE-HBM-97 11-09: plan die name -> contract dir
    if source is not None:
        reset_contract = kit_reset_contract.stage(kd, P.types[tn]["module"], source, plan_type=True)
        if reset_contract is not None:
            fz["reset_contract"] = reset_contract
    # Match the core-generator recipe form: candidates only, never an EQ waiver.
    # Stage before freeze/hash and asynchronous proof-policy input capture.
    hints = P.types[tn].get("lec_hints")
    if hints:
        body = json.dumps(hints, indent=1) + "\n"
        (kd / "lec_hints.json").write_text(body)
        fz["lec_hints"] = dict(file="lec_hints.json", count=len(hints),
                               sha256=hashlib.sha256(body.encode()).hexdigest())
    # KW-FIX-24 (COORD 11-06 21:2x (5)): GRAY-MSB TWIN class hints (gray FIFO pointer P[msb] == P_g[msb]) by
    # default, merged after the type's own hints (never overriding one); kits without a gray pointer are unchanged.
    import lec_gray_twin
    gray = lec_gray_twin.stage(kd, P.types[tn].get("module", tn))
    if gray is not None:
        fz["lec_hints"] = dict(file="lec_hints.json", count=gray["count"], sha256=gray["sha256"],
                               gray_msb_twin=gray["added"])
    if (kd / "signed_parent_source.json").is_file():
        fz["signed_parent_source"] = json.loads((kd / "signed_parent_source.json").read_text())
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    return fz


def io_tcl(P, tn, pins):
    t = P.types[tn]
    w, h = t["outline_um"]
    lines = [f"# GENERATED by tools/die_plan/gen.py phys: exact pins of partition type {tn} (type frame, um).",
             f"# {len(pins)} signal pins from die_plan {P.name}; neighbours use the same coordinates (abutment)."]
    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        lw = LAYER_W.get(ln, 0.04)
        # pin rectangle {w h}: long side perpendicular to the face, touching the edge
        if f in "EW":
            size, cx = (PIN_LEN_UM, lw), (x - PIN_LEN_UM / 2 if f == "E" else x + PIN_LEN_UM / 2)
            cy = y
        else:
            size, cy = (lw, PIN_LEN_UM), (y - PIN_LEN_UM / 2 if f == "N" else y + PIN_LEN_UM / 2)
            cx = x
        lines.append(f"place_pin -pin_name {{{bus}[{bit}]}} -layer {ln} -location {{{cx:.4f} {cy:.4f}}} "
                     f"-pin_size {{{size[0]:.4f} {size[1]:.4f}}}")
    import infra_rtl as IR
    for ip in IR.type_ports(t):
        x, y = ip["xy_um"]
        lines.append(f"place_pin -pin_name {{{ip['name']}}} -layer {ip['layer']} -location {{{x:.4f} {y:.4f}}} "
                     "-pin_size {0.0480 0.4800}   ;# native infrastructure via-field, die-timed")
    top = P.layer_budget["partition_signal_max"]
    for name, x, y in tap_pins(P, tn):
        lines.append(f"place_pin -pin_name {name} -layer {top} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(top, 0.04):.4f} {tap_pin_height(P, tn, name):.4f}}}   ;# interior: die spine tap")
    for name, x, y in reset_out_pins(P, tn):
        lines.append(f"place_pin -pin_name {name} -layer {top} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(top, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: reset wavefront out")
    for name, ln, x, y in strap_pin_sites(P, tn):
        lines.append(f"place_pin -pin_name {{{name}}} -layer {ln} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(ln, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: ID strap (tied at die top)")
    for name, ln, x, y in reset_spine_pin_sites(P, tn):
        lines.append(f"place_pin -pin_name {{{name}}} -layer {ln} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(ln, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: bound reset spine")
    if t.get("clock", {}).get("landing_contract"):
        import landing_contract as LC
        lines.append(LC.io_tcl(P, tn).rstrip())
    for name, i, ln, x, y in signal_pad_sites(P, tn):
        lines.append(f"place_pin -pin_name {{{name}[{i}]}} -layer {ln} -location {{{x:.4f} {y:.4f}}} "
                     "-pin_size {0.0480 0.4800}   ;# declared digital package signal pad")
    import pad_clock as PC
    if t.get('clock', {}).get('pad_clock') is not None:
        lines.append(PC.io_tcl(P, tn).rstrip())
    return "\n".join(lines) + "\n"


# soft relay instances placed by relay_mid.tcl: the kept ot_s81_rly relays of the S81 frame bands (u_r<k>.u_y_<lane>);
# a plan may override it with budgets.relay_mid_re (first capture = the relay group)
RELAY_MID_RE = r"^(.*[.]u_y_[A-Za-z0-9_]+)[.]"


def _snap_tap(P, x, y, pg_legal=True):
    """Interior tap at a crossing of the top two routing layers, clear of both layers' PG access bands.

    Partition stripes are offset from CORE_AREA (CORE_MARGIN_UM); the face-pin band policy also includes the
    zero-origin phase. Keeping access clear at both phases protects the pin rectangle AND its lower-layer via.
    Hard partition interfaces retain their declared LEF coordinates (pg_legal=False); their owner fixes the view.
    """
    top = P.layer_budget["partition_signal_max"]
    L = P.layers[top]
    below = f"M{int(top[1:]) - 1}"
    Lb = P.layers.get(below, L)

    def snap(v, LL, ln):
        pitch = LL["pitch_um"]
        k = round((v - LL["offset_um"]) / pitch)
        if not pg_legal:
            return round(LL["offset_um"] + k * pitch, 4)
        # Band guards already include the stripe pair, pin half-width and at least two routing pitches.
        def clear(q):
            return not any(S.pg_blocked(ln, q - origin) for origin in (0.0, CORE_MARGIN_UM))
        for radius in range(1000):
            ks = [k] if radius == 0 else [k-radius, k+radius]
            ok = [round(LL["offset_um"] + j*pitch, 4) for j in ks
                  if clear(LL["offset_um"] + j*pitch)]
            if ok:
                return min(ok, key=lambda q: (abs(q-v), q))
        raise ValueError(f"no PG-free interior tap track near {v:g} on {ln}")
    return ((snap(x, L, top), snap(y, Lb, below)) if L["dir"] == "V" else
            (snap(x, Lb, below), snap(y, L, top)))



def clock_legal_axes(P, tn, clear=S.TAP_CLEAR_UM):
    """PG-safe track centres for local clock pins, inside the existing outline clearance.

    The axes use exactly _snap_tap's layers, four-decimal track coordinates,
    and both PG stripe phases. A mathematical zero-width street therefore
    contributes a clock site only if an actual consumed track exists there.
    """
    top = P.layer_budget['partition_signal_max']
    below = f'M{int(top[1:]) - 1}'
    layers = (top, below) if P.layers[top]['dir'] == 'V' else (below, top)
    pg_legal = not P.types[tn].get('hard')
    out = []
    for extent, ln in zip(P.types[tn]['outline_um'], layers):
        ll = P.layers.get(ln, P.layers[top])
        pitch, offset = ll['pitch_um'], ll['offset_um']
        lo, hi = math.ceil((clear-offset)/pitch), math.floor((extent-clear-offset)/pitch)
        tracks = [round(offset+k*pitch, 4) for k in range(lo, hi+1)]
        out.append(tuple(q for q in tracks if not pg_legal or
                         not any(S.pg_blocked(ln, q-origin) for origin in (0.0, CORE_MARGIN_UM))))
    return tuple(out)


def clock_pins(P, tn):
    """every clock tap pin of a type (COORD 10-23 R4 grid, schema.tap_grid), snapped: [(port, x, y)]."""
    return [(n,) + _snap_tap(P, x, y, pg_legal=not P.types[tn].get("hard")) for n, x, y in S.tap_grid(P, tn)]


def tap_points(P, tn):
    """(clock tap 0, reset tap) of a type in its frame, snapped.  The die spine drops onto these interior pins.  A reset
    tap missing, or on a clock tap (two pins on one spot = GRT-0080), sits one lattice step (8.64 um) away."""
    t = P.types[tn]
    h = t["outline_um"][1]
    cks = [(x, y) for _, x, y in S.tap_grid(P, tn)] + [(x, y) for _, x, y, _ in S.core_taps(P, tn)]
    ck = list(cks[0])
    rs = list(t.get("reset", {}).get("tap_um", ck))
    if (t.get("hard") and t.get("reset", {}).get("tap_um") is not None
            and t.get("clock", {}).get("tap_um") is not None
            and any(c.get("lef") and c.get("origin_um") is not None for c in t.get("contents", []))):
        # These are native hard-macro terminal coordinates, not movable buffer
        # sites. Distinct legal LEF pins can be192nm apart; the soft1um collision
        # heuristic and partition-layer snapping must not move either terminal.
        return [tuple(map(float, ck)), tuple(map(float, rs))]
    if any(abs(rs[0] - a) < 1.0 and abs(rs[1] - b) < 1.0 for a, b in cks):
        rs = [ck[0], ck[1] + 8.64 if ck[1] + 8.64 < h - 1 else ck[1] - 8.64]
        if t.get("hard_cores"):     # S81-P8 10-23: the reset tap also sits in a channel, off the clock taps
            rs = list(S.tap_clear(t, rs[0], rs[1], cks, clear=4.32))
    return [_snap_tap(P, *ck, pg_legal=not t.get("hard")),
            _snap_tap(P, *rs, pg_legal=not t.get("hard"))]


def core_tap_pins(P, tn):
    """CP2 early core taps of a type (schema.core_taps; clock.core_taps 'early'), snapped: [(port, x, y)].
    S81-49/kits 11-02: a tap the plan puts on a hard core's edge pin can snap a few tracks INTO a macro whose LEF
    obstructs the entry layer or the via layer below (S81 ve_m/vn_a/vn_b/vq: M5 edge pin, OBS M1-M7, port 0.02-0.4 um
    inside); such a pin is moved to the nearest PG-legal track position whose pin metal clears every obstructing
    macro (<= ENTRY_CLEAR_MAX_UM).  Taps clear of such macros are byte-identical."""
    pg = not P.types[tn].get("hard")
    taps = S.core_taps(P, tn)
    blocks = entry_block_boxes(P, tn) if taps else []
    out = []
    for n, x, y, _ in taps:
        explicit = any(c.get("clock_entry_access") and any(
            q == n and i == c["inst"] and pin == c["clock_entry_access"]["pin"]
            for q, i, pin, _, _ in core_tap_rows(P, tn)) for c in P.types[tn].get("hard_cores", []))
        if explicit:
            # An interior real-pin stack must not be shifted away by generic PG
            # avoidance. Its exact target M6/M7 PG cuts are emitted below.
            sx, sy = float(x), float(y)
            layer = P.layers[P.layer_budget["partition_signal_max"]]
            axis = sx if layer["dir"] == "V" else sy
            k = (axis - layer["offset_um"]) / layer["pitch_um"]
            if abs(k - round(k)) > 1e-6:
                raise ValueError(f"{tn}.{n}: explicit entry off preferred routing track")
        else:
            sx, sy = _snap_tap(P, x, y, pg_legal=pg)
        port_blocks = entry_block_boxes(P, tn, port=n, entry_xy=(sx, sy)) if any(
            c.get("clock_entry_access") for c in P.types[tn].get("hard_cores", [])) else blocks
        if port_blocks and _pin_hits(P, tn, n, sx, sy, port_blocks):
            sx, sy = _clear_core_tap(P, tn, n, x, y, (sx, sy), port_blocks, pg)
        out.append((n, sx, sy))
    return out


ENTRY_CLEAR_MAX_UM = 2.0       # an entry is moved off a macro edge by snapping distance only, never re-planned


def _lef_metal_top(lef_text):
    """highest LAYER Mn carrying OBS or PIN geometry in a one-macro LEF (0: none)."""
    return max([int(v) for v in re.findall(r"\bLAYER\s+M(\d+)\b", lef_text)] or [0])


def _placed_entries(t):
    """{placed inst name: plan entry} for type_macros rows.  DIE-QC-97 11-09: a declared hard core wins over a
    contents[] entry of the same instance name (QC cbx_q10 u_t30: contents qfd_tile_nl_romleaf_rpf, no orient, no
    clock_entry_access, shadowed hard core qfd_tile_nl_a0c MY with the access, so the M7 entry met a solid macro)."""
    ents = {}
    for c in (t.get("hard_cores", []) or []) + (t.get("contents", []) or []):
        ents.setdefault(c.get("physical_inst") or c["inst"], c)
        ents.setdefault(c["inst"], c)
    return ents


def _access_margins(P, top):
    """one routing pitch per access layer (ASAP7 M6/M7 0.064 um = the access_v4 review windows)"""
    dflt = {L["name"]: L for L in S.ASAP7_LAYERS}
    return {k: float((P.layers.get(f"M{k}") or {}).get("pitch_um") or dflt[f"M{k}"]["pitch_um"]) for k in (top - 1, top)}


def clock_entry_lef(P, tn, core, mod, text, x, y, o):
    """DIE-QC-97 11-09: (LEF text, cuts) the kit stages for a hard core with clock_entry_access: the signed view LEF
    with its M(top-1)/M(top) OBS opened only at the access footprints (lef_clock_entry.derive_access_lef).  The pins
    and the Liberty are the signed view's, so the abstract stays paired with the signed lib; the derivation is
    recorded in clock_entry_lef.json.  Without clock_entry_access the text is returned unchanged."""
    access = core.get("clock_entry_access")
    if not access:
        return text, 0
    from lef_clock_entry import derive_access_lef
    top = int(P.layer_budget["partition_signal_max"][1:])
    return derive_access_lef(text, mod, access, top, (float(x), float(y), o), _access_margins(P, top))


def stage_clock_entry_lefs(P, tn, kd, macros, resolve):
    """after macro staging: rewrite kd/macros/<lef> of every hard core with clock_entry_access to its access abstract
    and write the receipt clock_entry_lef.json.  No access in the type: nothing written (byte-identical kits).  A LEF
    shared by instances whose access windows differ is refused (one staged file per LEF name)."""
    ents = _placed_entries(P.types[tn])
    rows, by_file = [], {}
    for inst, mod, lef, lib, x, y, o in macros:
        c = ents.get(inst) or {}
        if not lef or not c.get("clock_entry_access"):
            continue
        staged = Path(kd) / "macros" / resolve(lef).name
        # the staged copy (after view_lef's advisory prune) is the source; re-staging the same file stays idempotent
        src = staged.read_text()
        new, cuts = clock_entry_lef(P, tn, c, mod, src, x, y, o)
        if by_file.setdefault(staged.name, new) != new:
            raise ValueError(f"type {tn}: {staged.name} staged for instances with different clock entry windows")
        staged.write_text(new)
        sha = lambda b: _hashlib.sha256(b.encode() if isinstance(b, str) else b).hexdigest()
        top = int(P.layer_budget["partition_signal_max"][1:])
        from lef_clock_entry import access_windows
        rows.append(dict(inst=inst, module=mod, pin=c["clock_entry_access"]["pin"], lef=str(lef),
                         staged=f"macros/{staged.name}", source_lef_sha256=sha(src), staged_lef_sha256=sha(new),
                         lib=str(lib) if lib else None,
                         lib_sha256=sha(resolve(lib).read_bytes()) if lib and resolve(lib).is_file() else None,
                         obs_cuts=cuts, site=[float(x), float(y), o],
                         windows_um={f"M{k}": [list(w) for w in v] for k, v in access_windows(
                             src, mod, c["clock_entry_access"], top, (float(x), float(y), o), _access_margins(P, top)).items()}))
    # instances of a re-staged LEF that carry no access share the opened abstract: they must be absent
    for inst, mod, lef, *_ in macros:
        if lef and resolve(lef).name in by_file and not (ents.get(inst) or {}).get("clock_entry_access"):
            raise ValueError(f"type {tn}: {inst} shares {resolve(lef).name} with a clock entry core but has no access")
    if rows:
        (Path(kd) / "clock_entry_lef.json").write_text(json.dumps(dict(
            schema="opentallas.clock_entry_lef.v1", type=tn, rows=rows,
            rule="derived parent abstract: signed view LEF, OBS opened only at clock_entry_access footprints grown one "
                 "pitch; PIN blocks and Liberty unchanged (DIE-QC-97 11-09)"), indent=1) + "\n")
    return rows


def entry_block_boxes(P, tn, root=None, port=None, entry_xy=None):
    """[(x0, y0, x1, y1)] type-frame boxes of the placed macros (type_macros) whose metal reaches the partition entry
    layer (layer_budget partition_signal_max) or the via layer below it: LEF OBS/PIN layers, else plan obs_max."""
    t = P.types[tn]
    top = int(P.layer_budget["partition_signal_max"][1:])
    ents = _placed_entries(t)
    base = Path(root) if root else Path(__file__).resolve().parent.parent.parent
    out = []
    for inst, mod, lef, lib, x, y, o in type_macros(P, tn):
        c = ents.get(inst) or {}
        if not c.get("outline_um"):
            continue
        # the staged LEF is the truth (S81 vq: plan obs_max M5, LEF OBS M1-M7); plan obs_max only without a LEF
        om = re.fullmatch(r"M(\d+)", str(c.get("obs_max") or ""))
        try:
            f = _CR.resolve(lef, base)
            mtop = _lef_metal_top(f.read_text(errors="replace")) if f.is_file() else None
        except (OSError, ValueError):
            mtop = None
        if mtop is None:
            mtop = int(om.group(1)) if om else top      # unknown view: treat as obstructing (fail closed)
        access = c.get("clock_entry_access")
        if access and port is not None:
            matched = [(n, i, pin) for n, i, pin, _, _ in core_tap_rows(P, tn)
                       if n == port and i == c["inst"] and pin == access["pin"]]
            if matched:
                from lef_clock_entry import validate_access
                # DIE-QC-97: judged on the access abstract the kit stages (stage_clock_entry_lefs), not the blanket
                validate_access(clock_entry_lef(P, tn, c, mod, f.read_text(), x, y, o)[0], mod, access, top,
                                (float(x), float(y), o), _pin_box(P, tn, port, *entry_xy))
                continue  # only this named utility pin; every other port retains the solid macro
        if mtop < top - 1:
            continue
        w, h = map(float, c["outline_um"])
        if o in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        out.append((float(x), float(y), float(x) + w, float(y) + h))
    return out


def _pin_box(P, tn, name, x, y):
    top = P.layer_budget["partition_signal_max"]
    L = P.layers[top]
    hw = float(L.get("width_um", 0.032)) / 2
    hl = (tap_pin_height(P, tn, name) if name in P.types[tn].get("clock", {}).get("tap_pin_heights_um", {})
          else 4 * PIN_LEN_UM) / 2
    return (x - hw, y - hl, x + hw, y + hl) if L["dir"] == "V" else (x - hl, y - hw, x + hl, y + hw)


def _pin_hits(P, tn, name, x, y, blocks, eps=1e-6):
    a = _pin_box(P, tn, name, x, y)
    return any(min(a[2], b[2]) - max(a[0], b[0]) > -eps and min(a[3], b[3]) - max(a[1], b[1]) > -eps for b in blocks)


def _clear_core_tap(P, tn, name, x, y, snapped, blocks, pg):
    """nearest PG-legal snapped centre (plan tap x, y moved straight out of the obstructing macro) whose pin clears
    every block, within ENTRY_CLEAR_MAX_UM of the plan tap; else the original snap (kit_contract still FAILs it)."""
    a = _pin_box(P, tn, name, x, y)
    hx, hy = (a[2] - a[0]) / 2, (a[3] - a[1]) / 2
    best = None
    for b in blocks:
        if not (min(a[2], b[2]) - max(a[0], b[0]) > -1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > -1e-6):
            continue
        for step in range(0, 40):
            d = 0.012 * step
            for tx, ty in ((x, b[3] + hy + d), (x, b[1] - hy - d), (b[0] - hx - d, y), (b[2] + hx + d, y)):
                if math.hypot(tx - x, ty - y) > ENTRY_CLEAR_MAX_UM:
                    continue
                try:
                    q = _snap_tap(P, tx, ty, pg_legal=pg)
                except ValueError:
                    continue
                if _pin_hits(P, tn, name, q[0], q[1], blocks) or math.hypot(q[0] - x, q[1] - y) > ENTRY_CLEAR_MAX_UM:
                    continue
                w, h = P.types[tn]["outline_um"]
                if not (0 < q[0] < w and 0 < q[1] < h):
                    continue
                k = (math.hypot(q[0] - x, q[1] - y), q)
                best = k if best is None or k < best else best
    return best[1] if best else snapped


def clock_tap_pin_metadata(P, tn):
    """Every physical grid and early-core input already emitted by tap_pins, at its exact snapped centre."""
    return [dict(name=n, xy=[x, y]) for n, x, y in clock_pins(P, tn) + core_tap_pins(P, tn)]


CLOCK_PIN_ALIASES = ("clk", "ck")
_VIEW_CLOCK_PINS = {}


def bound_core_clock_pins(P, tn, inst, pin):
    """KW-FIX-5 11-03 (COORD 23:3x, safe form A): `pin` of a planned early core tap, read against the core's BOUND view.

    -> None when the view has that clock pin or no readable clock pins (plan pin stands, nothing changes);
    otherwise {view pin: TT insertion ps} of the pin(s) the tap must carry.  A plan pin absent from the view leaves the
    tap EMPTY in clock_taps.tcl: the core falls on a grid tap and CTS pads that tap's flops to the core's internal
    latency (col_h9_r0_p2: plan u_e3.ck, view clk 690 ps, clk_t30 flops +655 ps, 27 delay buffers, FF hold -548)."""
    import cores as C
    core = next((c for c in P.types[tn].get("hard_cores", []) or [] if c.get("inst") == inst), None)
    if core is None or pin == "*":
        return None
    key = (core.get("lib"), core.get("lef"), core.get("module"))
    if key not in _VIEW_CLOCK_PINS:     # core_tap_rows is called many times per kit; a view is parsed once
        _VIEW_CLOCK_PINS[key] = C.clock_pins(core, None)
    ck = _VIEW_CLOCK_PINS[key]
    if not ck or pin in ck:
        return None
    bits = sorted(p for p in ck if p.startswith(pin + "["))
    alias = sorted(p for p in ck if p in CLOCK_PIN_ALIASES or p.split("[")[0] in CLOCK_PIN_ALIASES)
    sel = bits or alias or [max(sorted(ck), key=lambda p: ck[p]["rise"])]
    return {p: float(ck[p]["rise"]) for p in sel}


def view_core_tap_values(P, tp, view_tt_ps, corner="TT"):
    """(early, insertion) of a re-bound tap from the current view.  early = min(view insertion - common latency, what
    the tap can deliver); a tap arrives at the clock root at best, so it can be at most the common latency early.  The
    FF insertion uses the plan's FF/TT ratio on the view number, as a tap with no FF value does."""
    if view_tt_ps <= 0:          # a view with the pin but no tree arc (LEF only): the pin binds, the plan values stand
        return S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner)
    c = "FF" if str(corner).upper().startswith("F") else "TT"
    ins = view_tt_ps if c == "TT" else round(S.FF_TT_INSERTION_RATIO * view_tt_ps, 3)
    lat = S.common_latency_ps(P, c)
    return max(0.0, min(ins - lat, lat)), ins


def core_tap_view_report(P, tn):
    """rows of core_tap_view.json / the OT_CORE_TAP_* gen lines: every planned tap whose pin the bound view re-binds."""
    out = []
    for n, _x, _y, tp in S.core_taps(P, tn):
        if "core_group" in tp or tp.get("merged_clock_ports"):
            continue
        for c in sorted((x.get("inst") for x in P.types[tn].get("hard_cores", []) or [] if x.get("inst")), key=len, reverse=True):
            if not tp["name"].startswith(c + "."):
                continue
            plan_pin = tp["name"][len(c) + 1:]
            for pin, tt in (bound_core_clock_pins(P, tn, c, plan_pin) or {}).items():
                early, ins = view_core_tap_values(P, tp, tt)
                out.append(dict(port=n, inst=c, plan_pin=plan_pin, view_pin=pin,
                                plan_insertion_ps=S.core_tap_insertion_ps(tp), view_insertion_ps=ins,
                                plan_early_ps=S.core_tap_early_ps(P, tp), early_ps=early,
                                clamped=ins - S.common_latency_ps(P, "TT") > early))
            break
    return out


def budget_tap_rows(P, tn):
    """Keep budget rows identical with one macro-avoiding grid count per type."""
    density = _density(P.types[tn])
    try:
        grid_count = 0 if density else len(S._grid_taps(P, tn))
    except ValueError:
        # S81 slice_station__t51 native split: two hard children cover the outline, so the R4 grid has no legal site.
        # An explicit type's clock ports come from its taps table alone (tap_grid), so no row is a grid row.  Other
        # explicit types keep their byte-identical budget; any other mode still refuses.
        if P.types[tn].get("clock", {}).get("tap_mode") != "explicit":
            raise
        grid_count = 0
    rows = [dict(name=n, xy=[x, y], kind="density" if density else
                 ("grid" if i < grid_count else "sinks"))
            for i, (n, x, y) in enumerate(S.tap_grid(P, tn))]
    return grid_count, rows


def core_tap_rows(P, tn, corner="TT", pending=None):
    """[(port, core inst, clock pin or '*', early_ps, insertion_ps)] of the type's early core taps: a tap named
    `<inst>` takes every clock pin of that core, `<inst>.<pin>` one pin.  A merged tap on a core with no native view
    (HBM-STREETS-3, COORD 10-27 19:12 ruling 1) keeps its plan clock pins and is appended to `pending` (PENDING-VIEW)."""
    t = P.types[tn]
    insts = [c["inst"] for c in t.get("hard_cores", []) or []]
    if S.bare_hard(t):
        # DIE-KV-60/phy 11-01 (COORD variant C): a bare hard wrapper has no hard_cores[]; its early core tap names the
        # wrapped macro by contents[].physical_inst (the placed instance, e.g. kv3_phy u_bound.u_core) or inst
        insts = sorted({c.get(k) for c in t.get("contents", []) or [] for k in ("physical_inst", "inst") if c.get(k)})
    out = []
    for n, _, _, tp in S.core_taps(P, tn):
        if "core_group" in tp:
            out.extend((n, m["inst"], m["pin"], S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner))
                       for m in tp["core_group"]["members"])
            continue
        nm = tp["name"]
        hit = None
        for i in sorted(insts, key=len, reverse=True):
            if nm == i:
                hit = (i, "*")
            elif nm.startswith(i + "."):
                hit = (i, nm[len(i) + 1:])
            if hit:
                break
        if not hit:
            raise ValueError(f"type {tn}: core tap {nm} names no hard_cores[] (bare hard: contents[]) inst")
        if tp.get("merged_clock_ports"):
            import merged_core_clocks as MC
            for pin in MC.pins_or_pending(P, tn, tp, hit[0], pending):
                out.append((n, hit[0], pin, S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner)))
        else:
            rebound = bound_core_clock_pins(P, tn, hit[0], hit[1])
            if rebound:
                # only a tap that was EMPTY in every earlier kit: a pin the view has keeps its plan values
                out.extend((n, hit[0], pin, *view_core_tap_values(P, tp, tt, corner)) for pin, tt in rebound.items())
            else:
                out.append((n, hit[0], hit[1], S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner)))
    physical = {c["inst"]: content_physical_identity(c)[0] for c in P.types[tn].get("hard_cores", [])
                if "physical_inst" in c or "physical_master" in c}
    return [(n, physical.get(inst, inst), pin, early, insertion) for n, inst, pin, early, insertion in out]



def core_tap_ff_sdc(P, tn):
    """Corner overlay for dedicated core taps; the golden SDC retains its TT basis."""
    seen = set()
    lines = []
    for n, inst, pin, early, ins in core_tap_rows(P, tn, "FF"):
        if n in seen:
            continue
        seen.add(n)
        lines.append(f"# CP2 FF core tap {n} ({inst}/{pin}: internal {ins:g} ps)\n"
                     f"set_clock_latency -source -clock clk {t_lib(-early):.4f} [get_ports {n}]\n")
    if lines and tap_window_ps(P, tn):
        lines.append(f"# plan clock.tap_window {tap_window_ps(P, tn):g} ps on the FF core taps (early end only)\n"
                     + core_tap_window_tcl(P, tn, "FF"))
    return "".join(lines)


def edge_clock_pins(P, tn):
    """[(port, x, y, period_mult)]: the type's PHY-edge clocks (schema clock.edge_clocks), snapped like taps."""
    return [(e["port"],) + _snap_tap(P, *e["tap_um"]) + (int(e.get("period_mult", 1)),)
            for e in P.types[tn].get("clock", {}).get("edge_clocks", [])]


# DIE-QC-75 11-05 (QC coll_s FF hold -320 ps): plain PHY-edge clocks (clk_coll, clk_serdes, clk_d2d: one die-period port with
# no forwarded ring, unlike fclk_in_*) get one tree per region of the same size as the clk taps, balanced to the same plan
# insertion: clock_edge_split.tcl (pre-CTS root buffers) + clock_edge_balance.tcl (POST_CTS pad).  The kit decides by sink
# count, so a small domain is left alone.  Types without such a port generate byte-identical kits.
# Opt-in per die (COORD 11-05): QC only.  KV kv3_sys_SD (clk_clk_phy) has the same port shape; its owner adds the die after
# its own estimate.
EDGE_SPLIT_DIES = {"qwen_compute", "qwen_kvsys"}  # KV-SYSSD-2 11-06 (COORD approved): KV kv3_sys_SD/_v1 clk_clk_phy 5250 sinks
# DIE-KV-84 11-06 (COORD 14:4x hold rule): macro sinks keyed on their clock pin, roots kept out of the macro; opt-in
# per die so QC kits stay byte-same.
EDGE_SPLIT_MACRO_PIN_DIES = {"qwen_kvsys"}


# DIE-KV-84 11-06 (COORD 16:2x(b)): an edge clock the plan declares "cdc": "synchronized" + "cdc_evidence" is
# asynchronous to the core clock clk by design (KV clk_clk_phy: PLL clk_phy 1043 ps; its only crossings are inside
# ot_fdi_phy_cdc's two async FIFOs and 2-flop synchronisers).  Those arcs get a max delay of half the die period with
# latency ignored, which covers both bounds of the module's SDC intent (Gray-bus skew 0.5 T, storage read T - 60).
# They get no hold check and never a clock group.  Only the edge clock <-> clk pair is excepted; default plans are
# byte-same.
EDGE_CDC_CORE_CLOCK = "clk"


def edge_cdc(P, tn):
    """{edge clock port: max delay ps} of the declared synchronized edge clocks of type tn (peer: clk)."""
    out = {}
    for e in P.types[tn].get("clock", {}).get("edge_clocks", []):
        if e.get("cdc") is None:
            continue
        if e["cdc"] != "synchronized" or not str(e.get("cdc_evidence", "")).strip():
            raise ValueError(f"{tn}.{e['port']}: edge clock cdc must be 'synchronized' with a cdc_evidence")
        if int(e.get("period_mult", 1)) != 1 or e.get("source_latency_ps") or e["port"].startswith("fclk_in"):
            raise ValueError(f"{tn}.{e['port']}: edge clock cdc only on a plain die-period edge clock")
        out[e["port"]] = 0.5 * float(P.die["period_ps"])
    return out


def edge_cdc_sdc(P, tn):
    out = ""
    for n, mx in edge_cdc(P, tn).items():
        c, v = EDGE_CDC_CORE_CLOCK, t_lib(mx)
        out += (f"# DIE-KV-84 COORD 16:2x(b): {n} asynchronous to {c} (plan cdc synchronized; evidence in plan cdc_evidence)\n"
                f"set_max_delay -ignore_clock_latency {v:.4f} -from [get_clocks {n}] -to [get_clocks {c}]\n"
                f"set_max_delay -ignore_clock_latency {v:.4f} -from [get_clocks {c}] -to [get_clocks {n}]\n"
                f"set_false_path -hold -from [get_clocks {n}] -to [get_clocks {c}]\n"
                f"set_false_path -hold -from [get_clocks {c}] -to [get_clocks {n}]\n")
    return out


def edge_split_ports(P, tn):
    if P.die.get("name") not in EDGE_SPLIT_DIES:
        return []
    return [n for n, _x, _y, m in edge_clock_pins(P, tn) if m == 1 and not n.startswith("fclk_in")
            and not edge_source_latency(P, tn, n)]


# DIE-HEAD-21 (opt-in plan clock.edge_clocks[].source_latency_ps): a source-forwarded edge clock (count-aligned ring
# write clock) reaches its port at the SENDER's export arrival + wire, not at 0 while its data inputs are timed on the
# vclk insertion (DH19: 2272 ring writers -130.6 ps at source latency 0).  The measured range is a source latency on
# the edge clock: -early = min arrival (OpenSTA/PT use the early source latency for the CAPTURE clock of setup checks
# and the launch of holds), -late = max arrival (capture of holds, launch of setups), so one SDC is pessimistic for
# both checks within a corner.  The corner itself cannot share one SDC (same reason as the vclk, ruling 9.7): TT goes
# into constraint.sdc, FF into the core_taps_ff.sdc corner overlay (OT_CORE_TAP_CORNER_FILE, read by vclk_corner.tcl
# ff / postcts FF gate / sign-off FF; vclk_corner.tcl tt re-applies the constraint.sdc lines).  Absent: no line.
def edge_source_latency(P, tn, port):
    return any(e["port"] == port and "source_latency_ps" in e for e in P.types[tn].get("clock", {}).get("edge_clocks", []))


def edge_clock_latency(P, tn):
    """[(port, {"tt": (early, late), "ff": (early, late)}, basis)] for the type's edge clocks with source_latency_ps."""
    out = []
    for e in P.types[tn].get("clock", {}).get("edge_clocks", []):
        sl = e.get("source_latency_ps")
        if sl is None:
            continue
        if tap_window_ps(P, tn):      # the window's port-level -early/-late lines would override the clock-level arrival
            raise ValueError(f"type {tn}: edge clock {e['port']} source_latency_ps with a plan clock.tap_window")
        v = {}
        for c in ("tt", "ff"):
            a, b = float(sl[c]["early"]), float(sl[c]["late"])
            if not 0 <= a <= b:
                raise ValueError(f"type {tn}: edge clock {e['port']} {c} source latency early {a:g} / late {b:g} ps "
                                 "needs 0 <= early <= late")
            v[c] = (a, b)
        out.append((e["port"], v, sl["basis"]))
    return out


def edge_clock_latency_tcl(P, tn, corner):
    """the -early / -late source latency lines of the type's edge clocks at corner 'tt' | 'ff' ('' without any)."""
    out = ""
    for n, v, basis in edge_clock_latency(P, tn):
        a, b = v[corner]
        out += (f"# forwarded edge clock {n} {corner.upper()} arrival at the port {a:g}..{b:g} ps ({basis}): early = "
                "setup capture, late = hold capture\n"
                f"set_clock_latency -source -early {t_lib(a):.4f} [get_clocks {n}]\n"
                f"set_clock_latency -source -late {t_lib(b):.4f} [get_clocks {n}]\n")
    return out
def tap_pin_height(P, tn, name):
    """Optional actual clock-pin metal height; centres and default geometry stay fixed."""
    value = P.types[tn].get('clock',{}).get('tap_pin_heights_um',{}).get(name,4*PIN_LEN_UM)
    if not math.isfinite(value) or value < 4*PIN_LEN_UM:
        raise ValueError(f'{tn}.{name}: clock pin height must be finite and >= {4*PIN_LEN_UM}')
    return value


def tap_pins(P, tn):
    """[(port, x, y)]: every clock tap (+ early core taps) + the reset tap (+ PHY-edge clock pins)."""
    import reset_tree as RT
    if RT.wavefront(P) and not P.types[tn].get("hard"):     # OWNER DECISION 13: the wavefront reset IN site
        rs = tuple(RT.in_pin(P, tn))
    else:
        rs = tuple(tap_points(P, tn)[1])
    st = [("start_i",) + tuple(RT.start_in_pin(P, tn))] if RT.start_broadcast(P) and not P.types[tn].get("hard") else []
    base_clocks = clock_pins(P, tn) + core_tap_pins(P, tn)
    edge_clocks = [e[:3] for e in edge_clock_pins(P, tn)]
    clocks = base_clocks + edge_clocks
    heights = P.types[tn].get('clock',{}).get('tap_pin_heights_um',{})
    known = {name for name,_,_ in clocks}
    if set(heights)-known:
        raise ValueError(f'{tn}: unknown clock pin height overrides {sorted(set(heights)-known)}')
    w,h=P.types[tn]['outline_um']
    for name,x,y in clocks:
        if name in heights:
            half=tap_pin_height(P,tn,name)/2
            if y-half < -1e-6 or y+half > h+1e-6:
                raise ValueError(f'{tn}.{name}: extended clock pin metal leaves type outline')
    return base_clocks + [("arst_n",) + rs] + st + edge_clocks


def core_reset_sdc(rsts, per):
    """THE core-kit reset IO rule, shared by every core-kit generator (FLOW-GEN-2 (d), COORD 10-28 all-die sweep of
    the HBM-CORES-REBAL-8 fix; OWNER DECISION 13 reset wavefront; die reset contract): a core reset pin is driven by
    the die reset tree's last relay flop (reset_tree.py), so it is a SYNCHRONOUS input timed under the normal data
    IO budget (IO_BUDGET x T, both max and min from the generator's $non_clk_in lines), recovery / removal timed.
    No reset-specific input delay: the old 0.5 T line ("released one cycle ahead, recovery at 1 T") modelled an
    unregistered half-cycle source that the reset tree does not have, and cost 0.3 T of every reset path (HBM
    lanes__canon -464.6 ps).  Returns the SDC comment for the reset ports (empty without reset pins)."""
    if not rsts:
        return ""
    return (f"# reset {' '.join(rsts)}: wavefront relay -> registered synchronous input, "
            f"data IO budget ({IO_BUDGET * per:.4f})\n")


def reset_out_pins(P, tn):
    """[(port, x, y)] interior registered reset OUT pins of a wavefront plan type (reset_tree.out_pins)."""
    import reset_tree as RT
    return RT.out_pins(P, tn) + RT.start_out_pins(P, tn)


# KV-KITS-4 10-27: declared hard-IP LINE SIDE (plan contents[]/hard_cores[].bump_ports, bind.py bump_pins) in the kit
# port contract.  The binder exports each declared bump pin of a hard core as a partition port (bind_report.json
# bump_ports[].part_port, named from the as-built leaf); kit-rtl keeps it as a bound-only wrapper pin.  Without it in
# port_bind_pins.json the pre-floorplan port_bind gate counts the line side as extra ports (kv3_sys_c: 1168 bits of
# u_ucie_rom link_*/far_*).  Names come from the bind (never re-derived here); the plan declaration, the bind report
# and the kit-rtl wrapper must agree or the kit is refused.
def declared_bumps(P, tn):
    """[(inst, module, pin, dir, width)] of the plan type's declared hard-IP line side (contents[] + hard_cores[])."""
    t = P.types[tn]
    out = []
    for e in t.get("contents", []) + t.get("hard_cores", []):
        for b in e.get("bump_ports") or []:
            out.append((e["inst"], e.get("module", e["inst"]), b["pin"], b["dir"], int(b["width"])))
    return out


def kit_bump_ports(P, tn, kit_rtl_filelist):
    """[dict(port, inst, module, pin, dir, width)]: the declared bump pins of a kit-rtl type with the bound partition
    port names, read from <filelist dir>/kit_rtl.json -> bind_out/bind_report.json.  [] when the plan declares none."""
    import gen_rtl
    dec = declared_bumps(P, tn)
    pads = pad_bumps(P, tn, kit_rtl_filelist)
    if not dec:
        return pads
    kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        raise gen_rtl.GenError(f"type {tn}: declares bump_ports but kit-rtl {kj} is missing (bound port names unknown)")
    kr = json.loads(kj.read_text())
    rep_f = Path(kr["bind_out"]) / "bind_report.json"
    if not rep_f.is_file():
        raise gen_rtl.GenError(f"type {tn}: declares bump_ports but {rep_f} is missing")
    rep = json.loads(rep_f.read_text())
    insts = set(kr.get("instances") or [])
    def sid(n):
        return re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_]', '_', n)).strip('_')

    bound = {}
    for b in rep.get("bump_ports", []):
        if b["partition"] not in insts:
            continue
        pin_key = (b["pin"], b["dir"], int(b["width"]))
        candidates = [d for d in dec if d[2:] == pin_key]
        if len(candidates) > 1:
            leaf = b["leaf"].split('.', 1)[-1]
            candidates = [d for d in candidates if sid(d[0].removeprefix('u_bound.')) == leaf]
        if len(candidates) != 1:
            raise gen_rtl.GenError(f"type {tn}: bump {b['leaf']}.{b['pin']} matches {len(candidates)} declarations")
        inst, mod, pin, d, width = candidates[0]
        key = (inst, mod, pin, d, width)
        if bound.setdefault(key, b["part_port"]) != b["part_port"]:
            raise gen_rtl.GenError(f"type {tn}: bump {inst}.{pin} has inconsistent partition port names")
    if set(bound) != set(dec):
        raise gen_rtl.GenError(f"type {tn}: plan bump_ports not all bound: {sorted(set(dec) - set(bound))[:4]}")
    bop = {b["port"]: (b["dir"], int(b["width"])) for b in kr.get("bound_only_pins", [])}
    digital_pads = {p['name']: p for p in P.types[tn].get('pads', []) if p.get('sites_um') and not p.get('macro_pin')}
    out = []
    for (inst, mod, pin, d, width), port in sorted(bound.items(), key=lambda kv: kv[1]):
        if bop.get(port) != (d, width):
            raise gen_rtl.GenError(f"type {tn}: bump port {port} ({d} {width}) is not a bound-only pin of the kit-rtl wrapper")
        if port in digital_pads:
            pd = digital_pads[port]
            if ({'in': 'input', 'out': 'output'}[pd['dir']], pd['width']) != (d, width):
                raise gen_rtl.GenError(f"type {tn}: signal pad {port} does not match bound line-side port")
            # A source-only digital receiver disappears into a wire; this is a physically placed type pad,
            # timed at the existing capture logic, rather than a placed hard macro with an invented LEF.
            continue
        out.append(dict(port=port, inst=inst, module=mod, pin=pin, dir=d, width=width))
    return out + pads


def kit_spare_out_bits(kit_rtl_filelist):
    """DIE-S81-46 (COORD 10-30 14:0x (2)(b) declared spare-out): the plan output bits the kit-rtl wrapper ties to 0,
    from <filelist dir>/kit_rtl.json spare_out_bits (+ narrow_buses for the bit range: bound..plan-1; a plan bus with
    no bound bit is spare as a whole).  face_guard reads them from kit spare_out.json.  [] without kit_rtl.json or
    spare bits (no file: byte-identical kits)."""
    import gen_rtl
    kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        return []
    kr = json.loads(kj.read_text())
    narrow = {x["port"]: (int(x["bound"]), int(x["plan"])) for x in kr.get("narrow_buses") or []}
    out = []
    for e in kr.get("spare_out_bits") or []:
        port, n = e["port"], int(e["bits"])
        lo, hi = narrow.get(port, (0, n))
        if hi - lo != n:
            raise gen_rtl.GenError(f"{kj}: spare_out_bits {port} x{n} != narrow bus range [{hi - 1}:{lo}]")
        out += [f"{port}[{i}]" for i in range(lo, hi)]
    return out


def kit_dead_inputs(kit_rtl_filelist):
    """DIE-S81-51/SPARE 11-03 (COORD 09:3x dead-input declaration form): the kit dead_inputs.json document the bind's
    kit-rtl step wrote into kit_rtl.json "dead_inputs" (the narrow plan input bits beyond the bound payload width that
    the generated wrapper leaves unconnected), or None.  Fail-closed: the receipt wrapper must still hash to its sha256
    and every bit must lie in a proven narrow range or a wholly unbound input whose native ABI, strict mapping and literal unread wrapper are re-proved. face_guard still proves 0 loads/0 drivers."""
    import gen_rtl
    from face_guard import dead_input_list
    kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        return None
    doc = json.loads(kj.read_text()).get("dead_inputs")
    if not doc:
        return None
    try:
        bits = dead_input_list(doc)
    except ValueError as exc:
        raise gen_rtl.GenError(f"{kj}: {exc}") from exc
    rc = doc["proof"]["receipt"]
    wf = Path(rc["wrapper"])
    if not wf.is_file() or _hashlib.sha256(wf.read_bytes()).hexdigest() != rc["sha256"]:
        raise gen_rtl.GenError(f"{kj}: dead_inputs receipt wrapper {wf} missing or sha256 changed")
    ok = {f"{x['port']}[{i}]" for x in rc.get("narrow_buses") or [] for i in range(int(x["bound"]), int(x["plan"]))}
    import kit_dead_inputs
    manifest=json.loads(kj.read_text())
    try:
        ok.update(kit_dead_inputs.validate_unbound(manifest,rc))
        if rc.get('unbound_input_buses'):
            # Re-prove final source reads at GEN, even if an earlier hash was valid.
            kit_dead_inputs.refresh(manifest,wf)
    except (ValueError,OSError) as exc:
        raise gen_rtl.GenError(f"{kj}: {exc}") from exc
    if not set(bits) <= ok:
        raise gen_rtl.GenError(f"{kj}: dead_inputs bits outside proven input ranges: {sorted(set(bits) - ok)[:5]}")
    return doc


# S81-SERDES-PHY-3 10-31 (opt-in pads[].macro_pin {inst, pin}): an AS-BUILT type pad that is wired straight to one pin
# of a placed hard part (physical_parts[].physical_inst / hard_cores[] / contents[] macro view: the S81 PMA line side
# io_pma_rx/tx/tck) is the same line side as a bound bump: no face register, its top pin ON the macro pin
# (bump_pin_sites), face_guard proves the bit drives / loads exactly that one macro pin.  The name is the plan pad
# itself (gen_rtl emits it), so no bind report is needed; a kit-rtl wrapper must carry it as a bound-only pin.
def pad_bumps(P, tn, kit_rtl_filelist=None):
    """[dict(port, inst, module, pin, dir, width)] of the type pads that declare macro_pin.  [] when none do."""
    import gen_rtl
    t = P.types[tn]
    pads = [p for p in t.get("pads", []) if p.get("macro_pin")]
    if not pads:
        return []
    views = {m[0]: m[1] for m in type_macros(P, tn)}
    bop = None
    if kit_rtl_filelist:
        kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
        if kj.is_file():
            bop = {b["port"]: (b["dir"], int(b["width"])) for b in json.loads(kj.read_text()).get("bound_only_pins", [])}
    out = []
    for p in pads:
        inst, pin, w = p["macro_pin"]["inst"], p["macro_pin"]["pin"], int(p["width"])
        if p.get("clock"):
            raise gen_rtl.GenError(f"type {tn}: pad {p['name']}: a macro_pin pad is line-side data, not a clock pad")
        if inst not in views:
            raise gen_rtl.GenError(f"type {tn}: pad {p['name']}: macro_pin inst {inst} has no placed view")
        d = {"in": "input", "out": "output"}[p["dir"]]          # netlist port kind, as the bind report's bump dir
        if bop is not None and bop.get(p["name"]) != (d, w):
            raise gen_rtl.GenError(f"type {tn}: pad {p['name']} ({p['dir']} {w}) is not a bound-only pin of the kit-rtl "
                                   f"wrapper ({bop.get(p['name'])})")
        out.append(dict(port=p["name"], inst=inst, module=views[inst], pin=pin, dir=d, width=w))
    return out


def pad_bump_dt_tcl(bumps):
    """S81-PMATX-DT: PRE_GLOBAL_PLACE Tcl marking the nets of the output macro_pin pads dont_touch.  A marked net must be
    the direct pad net (its port BTerm + exactly one output ITerm of the pad's macro master, nothing else); any other
    shape is an error, and so is a pad whose bit count differs from its width."""
    rows = " ".join("{%s %s %s %d}" % (b["port"], b["module"], b["pin"], b["width"]) for b in bumps)
    return PAD_BUMP_DT_TCL.replace("@ROWS@", rows)


PAD_BUMP_DT_TCL = r"""# GENERATED by tools/die_plan/gen_phys.py (S81-PMATX-DT 11-09): macro_pin OUTPUT pads (die pin == macro pin) keep
# their direct net: dont_touch before buffer_ports / repair_design.  Rows: port macro_master macro_pin width.
uplevel #0 {
set pdt_rows {@ROWS@}
set pdt_blk [ord::get_db_block]
set pdt_total 0
foreach pdt_r $pdt_rows {
  lassign $pdt_r pdt_port pdt_master pdt_pin pdt_w
  set pdt_n 0
  foreach pdt_b [$pdt_blk getBTerms] {
    set pdt_nm [$pdt_b getName]
    set pdt_tail [string range $pdt_nm [string length $pdt_port] end]
    if {[string first $pdt_port $pdt_nm] != 0 || ($pdt_tail ne "" && ![regexp {^\[[0-9]+\]$} $pdt_tail])} continue
    set pdt_net [$pdt_b getNet]
    if {$pdt_net eq "NULL"} { error "OT_PADBUMP_DT: pad $pdt_nm has no net" }
    set pdt_it [$pdt_net getITerms]
    if {[llength $pdt_it] != 1 || [[[[lindex $pdt_it 0] getInst] getMaster] getName] ne $pdt_master
        || ![[lindex $pdt_it 0] isOutputSignal] || ![string match "${pdt_pin}*" [[[lindex $pdt_it 0] getMTerm] getName]]} {
      error "OT_PADBUMP_DT: pad $pdt_nm net [$pdt_net getName] is not the direct $pdt_master/$pdt_pin pad net"
    }
    $pdt_net setDoNotTouch 1
    incr pdt_n
  }
  if {$pdt_n != $pdt_w} { error "OT_PADBUMP_DT: pad $pdt_port marked $pdt_n of $pdt_w bits" }
  incr pdt_total $pdt_n
}
puts "OT_PADBUMP_DT dont_touch $pdt_total macro_pin output pad nets (no port buffer, no repair)"
}
"""


def _lef_macro_pins(lef, module):
    """{pin bit name: (layer, x0, y0, x1, y1)} (first PORT rect) and the SIZE (w, h) of MACRO module in a LEF."""
    text = Path(lef).read_text()
    m = re.search(r"\bMACRO\s+" + re.escape(module) + r"\b(.*?)\bEND\s+" + re.escape(module) + r"\b", text, re.S)
    if m is None:
        raise ValueError(f"{lef}: no MACRO {module}")
    body = m[1]
    sz = re.search(r"\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", body)
    if sz is None:
        raise ValueError(f"{lef}: MACRO {module} has no SIZE")
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$", body, re.S | re.M):
        g = re.search(r"\bLAYER\s+(\S+)\s*;\s*RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)", pm[2])
        if g:
            pins[pm[1]] = (g[1],) + tuple(float(v) for v in g.groups()[1:])
    return pins, (float(sz[1]), float(sz[2]))


def _orient_rect(o, w, h, x0, y0, x1, y1):
    f = {"R0": lambda x, y: (x, y), "MX": lambda x, y: (x, h - y), "MY": lambda x, y: (w - x, y),
         "R180": lambda x, y: (w - x, h - y)}.get(o)
    if f is None:
        raise ValueError(f"bump pin placement: macro orient {o} not supported (R0/MX/MY/R180)")
    (a, b), (c, d) = f(x0, y0), f(x1, y1)
    return min(a, c), min(b, d), max(a, c), max(b, d)


def bump_pin_sites(P, tn, bumps, macros, base):
    """[(port, bit, layer, cx, cy, w, h)] type frame: every bump bit ON its hard core's own LEF pin shape (the bump is
    the hard IP's pin: no partition wiring, the die connects to it from above)."""
    by_inst = {m[0]: m for m in macros}
    out = []
    cache = {}
    for b in bumps:
        if b["inst"] not in by_inst:
            raise ValueError(f"type {tn}: bump {b['port']}: hard core {b['inst']} has no placed view (lef/origin)")
        inst, mod, lef, lib, x, y, o = by_inst[b["inst"]]
        if lef not in cache:
            cache[lef] = _lef_macro_pins(_CR.resolve(lef, base), mod)
        pins, (mw, mh) = cache[lef]
        for i in range(b["width"]):
            key = f"{b['pin']}[{i}]" if f"{b['pin']}[{i}]" in pins or b["width"] > 1 else b["pin"]
            if key not in pins:
                raise ValueError(f"type {tn}: bump {b['port']}[{i}]: {lef} MACRO {mod} has no pin {key}")
            ln, *r = pins[key]
            x0, y0, x1, y1 = _orient_rect(o, mw, mh, *r)
            out.append((b["port"], i, ln, round(x + (x0 + x1) / 2, 4), round(y + (y0 + y1) / 2, 4),
                        round(x1 - x0, 4), round(y1 - y0, 4)))
    return out


M123_TRACKS = """make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.045 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.081 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.117 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.153 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.189 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.225 -y_pitch 0.270
make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.270 -y_pitch 0.270
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
"""


def make_tracks_tcl(P):
    """M4-M9 from the plan's layer table (symmetric offsets = pitch / 2, schema.ASAP7_LAYERS), M1-M3 as the platform."""
    lines = ["# GENERATED by tools/die_plan/gen.py: plan tracks (M4-M9 symmetric: offset = pitch / 2) + platform M1-M3."]
    for n in ("M9", "M8", "M7", "M6", "M5", "M4"):
        L = P.layers.get(n)
        if L:
            lines.append(f"make_tracks {n} -x_offset {_um(L['offset_um'])} -x_pitch {_um(L['pitch_um'])} "
                         f"-y_offset {_um(L['offset_um'])} -y_pitch {_um(L['pitch_um'])}")
    return "\n".join(lines) + "\n" + M123_TRACKS


PDN = """# GENERATED by tools/die_plan/gen.py phys: partition PDN (abutment-continuous, die grid 8.64 um).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {4.32} -offset {2.064}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {1.968}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
"""


# DIE-HEAD-5 PGCUT (DRT-TRIAL-1 10-28, opt-in plan partition_types.<t>.pg_island_cut): the kit M6 PG straps of PDN
# (VDD offset 1.968, VSS one width + spacing after it, pitch 4.32, width 0.288; horizontal) run over the hard cores.
# A signed core's in-core island pins (interior M5 signal/clock pins, e.g. the elemA/elemB centre rst_n) can only be
# reached through an M5->M6 via; where such a pin lies under (or within M6 spacing of) a strap, the only access shorts
# the strap (hd_tile: 5 x M6 Short rst_n vs VDD).  Legal core moves cannot fix it (rows 0.27 x M4 tracks 0.048 ->
# steps of 2.16 = half the strap pitch, and clk / rst_n sit 2.16 apart, so one of them is always covered).  The cut
# removes the strap metal (and its M6 vias) over a window = pin x +- PG_CUT_MARGIN_UM, the strap's own y extent, after
# pdngen (POST_PDN_TCL); the strap stays connected on both sides through its other vias.
PG_M6 = (1.968, 0.288, 0.096, 4.32)          # offset, width, spacing, pitch (PDN M6 line)
PG_CUT_MARGIN_UM = 0.6                       # x: via M6 enclosure + M6 end-of-line spacing + an M7 escape track
PG_CUT_SPACE_UM = 0.072                      # y: M6 min spacing (pin -> strap) that also counts as covered
PG_CUT_EDGE_UM = 2.0                         # an "interior" pin is at least this far from every core edge


def _orient_rect_r(r, w, h, o):
    x0, y0, x1, y1 = r
    xs = {"R0": (x0, x1), "MX": (x0, x1), "MY": (w - x1, w - x0), "R180": (w - x1, w - x0)}[o]
    ys = {"R0": (y0, y1), "MY": (y0, y1), "MX": (h - y1, h - y0), "R180": (h - y1, h - y0)}[o]
    return xs[0], ys[0], xs[1], ys[1]


def lef_interior_pins(path, layer="M5", edge=PG_CUT_EDGE_UM):
    """([(pin, (x0, y0, x1, y1))], (w, h)): macro-frame rects of SIGNAL/CLOCK pins on `layer` at least `edge` from
    every macro edge (the in-core island pins), and the macro SIZE."""
    text = Path(path).read_text(errors="replace")
    w, h = map(float, re.search(r"SIZE\s+([-\d.]+)\s+BY\s+([-\d.]+)", text).groups())
    out = []
    for m in re.finditer(r"\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1\b", text, re.S):
        name, body = m.groups()
        u = re.search(r"USE\s+(\w+)", body)
        if (u.group(1) if u else "SIGNAL") not in ("SIGNAL", "CLOCK"):
            continue
        for lm in re.finditer(r"LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\bEND\b)", body, re.S):
            if lm.group(1) != layer:
                continue
            for r in re.finditer(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", lm.group(2)):
                x0, y0, x1, y1 = map(float, r.groups())
                if min(x0, y0, w - x1, h - y1) >= edge:
                    out.append((name, (x0, y0, x1, y1)))
    return out, (w, h)


def pg_island_cuts(P, tn, root=None):
    """[(inst, pin, (x0, y0, x1, y1))] type-frame cut windows of an opt-in type (pg_island_cut): every interior M5
    pin of a placed hard core, grown by PG_CUT_MARGIN_UM in x and PG_CUT_SPACE_UM in y.  Which straps it hits is
    decided on the actual pdngen geometry (pg_island_cut_tcl), not re-derived here.  [] when not opted in."""
    t = P.types[tn]
    selected = {(c.get("physical_inst") or c["inst"]): c["clock_entry_access"]["pin"]
                for c in t.get("hard_cores", []) if c.get("clock_entry_access")}
    if not t.get("pg_island_cut") and not selected:
        return []
    import cores as C
    cuts = []
    for inst, _mod, lef, _lib, ox, oy, o in type_macros(P, tn):
        if not t.get("pg_island_cut") and inst not in selected:
            continue
        pins, (w, h) = lef_interior_pins(C.resolve(lef, root))
        if not t.get("pg_island_cut"):
            pins = [(pin, r) for pin, r in pins if pin == selected[inst]]
            if not pins:
                raise ValueError(f"{tn}.{inst}: actual clock entry has no interior M5 target pin")
        for pin, r in pins:
            x0, y0, x1, y1 = _orient_rect_r(r, w, h, o)
            cuts.append((inst, pin, (round(x0 + ox - PG_CUT_MARGIN_UM, 4), round(y0 + oy - PG_CUT_SPACE_UM, 4),
                                     round(x1 + ox + PG_CUT_MARGIN_UM, 4), round(y1 + oy + PG_CUT_SPACE_UM, 4))))
    return cuts


def clock_entry_pg_cuts(P, tn):
    """Targeted actual M7 utility windows; other macros/clock pins stay unchanged."""
    cuts=[]
    for core in P.types[tn].get("hard_cores", []):
        access=core.get("clock_entry_access")
        if access:
            for rect in access["footprints_um"]["M7"]:
                cuts.append(dict(inst=core.get("physical_inst") or core["inst"], pin=access["pin"], layer="M7",
                    rect_um=[round(rect[0]-.072,6),round(rect[1]-.072,6),
                             round(rect[2]+.072,6),round(rect[3]+.072,6)]))
    return cuts


def pg_island_cut_tcl(cuts):
    """POST_PDN_TCL: every M6 VDD/VSS strap sbox that overlaps a pin window is split around the window's x span
    (full strap height), then every PG via touching M6 inside a cut is removed."""
    L = ["# GENERATED by tools/die_plan/gen.py phys (DIE-HEAD-5 PGCUT, opt-in pg_island_cut): M6 PG strap cuts over",
         "# in-core island pins (gen_phys.pg_island_cuts).  Runs after pdngen (POST_PDN_TCL).",
         "# ORFS sources POST_PDN_TCL inside a proc: run at global scope so the procs below see pgc_* (FLOW-GEN-1 10-28)",
         "uplevel #0 {",
         "set pgc_b [ord::get_db_block]", "set pgc_u [$pgc_b getDbUnitsPerMicron]",
         "set pgc_cuts {}; set pgc_via 0",
         "proc pgc_layers {s} {",
         "  foreach v [list [$s getTechVia] [$s getBlockVia]] {",
         '    if {$v ne "NULL" && $v ne ""} { return [list [[$v getTopLayer] getName] [[$v getBottomLayer] getName]] }',
         "  }",
         "  return {}",
         "}",
         "proc pgc_window {wx0 wy0 wx1 wy1} {",
         "  global pgc_b pgc_u pgc_cuts",
         "  set X0 [expr {round($wx0*$pgc_u)}]; set Y0 [expr {round($wy0*$pgc_u)}]",
         "  set X1 [expr {round($wx1*$pgc_u)}]; set Y1 [expr {round($wy1*$pgc_u)}]",
         "  foreach net {VDD VSS} {",
         "    set n [$pgc_b findNet $net]",
         '    if {$n eq "NULL" || $n eq ""} continue',
         "    foreach sw [$n getSWires] {",
         "      foreach s [$sw getWires] {",
         "        if {[$s isVia]} continue",
         '        if {[[$s getTechLayer] getName] ne "M6"} continue',
         "        if {[$s xMax] <= $X0 || [$s xMin] >= $X1 || [$s yMax] <= $Y0 || [$s yMin] >= $Y1} continue",
         "        set lay [$s getTechLayer]; set st [$s getWireShapeType]",
         "        set a [$s xMin]; set b [$s yMin]; set c [$s xMax]; set d [$s yMax]",
         "        odb::dbSBox_destroy $s",
         "        if {$a < $X0} { odb::dbSBox_create $sw $lay $a $b $X0 $d $st }",
         "        if {$c > $X1} { odb::dbSBox_create $sw $lay $X1 $b $c $d $st }",
         "        lappend pgc_cuts [list $net $X0 $b $X1 $d]",
         "      }",
         "    }",
         "  }",
         "}"]
    for inst, pin, (x0, y0, x1, y1) in cuts:
        L.append(f"pgc_window {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f}   ;# {inst}.{pin}")
    L += ["foreach cut $pgc_cuts {",
          "  lassign $cut net X0 Y0 X1 Y1",
          "  foreach sw [[$pgc_b findNet $net] getSWires] {",
          "    foreach s [$sw getWires] {",
          "      if {![$s isVia]} continue",
          "      if {[$s xMax] <= $X0 || [$s xMin] >= $X1 || [$s yMax] <= $Y0 || [$s yMin] >= $Y1} continue",
          '      if {"M6" in [pgc_layers $s]} { odb::dbSBox_destroy $s; incr pgc_via }',
          "    }",
          "  }",
          "}",
          'puts "OT_PG_ISLAND_CUT windows=%d strap_cuts=[llength $pgc_cuts] vias_removed=$pgc_via"' % len(cuts), "}"]
    return "\n".join(L) + "\n"


# ASAP7 liberty units (asap7sc7p5t_*.lib: time_unit "1ps", capacitive_load_unit (1,fF)): every SDC value below is in
# ps / fF.  Until 10-23 12:17 the SDCs wrote ns values (period 0.833 = a 0.833-PS clock; KV-P3b), which voided every
# earlier plan-kit / CP1 timing and repair number.
LIB_TIME_UNIT_PS = 1.0
LIB_CAP_UNIT_FF = 1.0
IO_LOAD_FF = 2.0
# Kit SDC clock uncertainty = the sign-off policy held in sdc_lint.py (OWNER 12.24b/c 2026-10-31: nominal setup 0, hold
# 25 unchanged; OT_MARGIN_POLICY=legacy restores setup 60 for A/B only).  Read at call time (unc_setup_ps() / unc_hold_ps()); the two
# module names below are import-time snapshots kept for older readers.
import sdc_lint as _SL  # noqa: E402


def unc_setup_ps():
    """kit SDC setup clock uncertainty (ps) of the sign-off margin policy (sdc_lint.policy_uncertainty)."""
    return _SL.policy_uncertainty()[0]


def unc_hold_ps():
    """kit SDC hold clock uncertainty (ps) of the sign-off margin policy (separate constant, sdc_lint.NOMINAL_UNC_HOLD_PS)."""
    return _SL.policy_uncertainty()[1]


UNC_SETUP_PS, UNC_HOLD_PS = _SL.policy_uncertainty()


def t_lib(ps):
    """a time in ps -> liberty / SDC time units."""
    return float(ps) / LIB_TIME_UNIT_PS


SLEW_MARGIN_PCT, CAP_MARGIN_PCT = 50, 20   # recommended repair_design margins, % of the limit (opt-in, see config)
FT_HOP_IN_SHARE = 0.08   # R3 hop share: an ft hop = last station -> out pin (this side) + the neighbour's face flop.
# COORD 10-23 15:39 FT PORT BUDGET ruling: the neighbour's receiving flop is a FIRM face flop (R2), so the out port
# keeps only that face share (0.08 T: pin -> s0 D + setup); the last L/k segment belongs to this side (0.92 T in).
# min input delay (hold) of every partition input vs vclk (= budgeted insertion).  CP1 r8 (10-23 21:22): with 0 ps
# (neighbour launch at ins - tol, credited back by clk-to-q + abutted wire) the kits padded nothing and the seam hold
# failed -50 TT / -48 FF.  Seam-hold padding (CP1 r9): the neighbour's face flop may launch at the fast end of the
# insertion window with NO clk-to-q / wire credit -> min input delay = -clock.insertion_tol_ps, so the receiving kit
# pads every seam input for the whole window.


def ft_hop_in_share(P):
    """the plan's ft seam receiver share (clock.ft_hop_in_share, COORD RULING 10-24 12:37), else FT_HOP_IN_SHARE."""
    return float(P.clock.get("ft_hop_in_share", FT_HOP_IN_SHARE))


def plain_seam_split(P):
    """Plain-lane input budget event (COORD 11-03 10:49 plain-seam input-face class part 2, DIE-S81-51/PLAN): opt-in
    plan clock.plain_seam_split {rx_in_max_ps, rx_in_raw_max_ps}; absent = {} (kit SDC byte-identical).

    A plain lane is a die port whose receiver bus is an ft slot input that is not a landing-ring input
    (landing_contract.ring_input_ports): station 0 is the in-face register, timed on vclk.  Its receiver input max
    before the tap-window shift becomes min((1 - sh) T, rx_in_raw_max_ps, rx_in_max_ps + window shift), so the written
    external in-budget is <= rx_in_max_ps and the in-face path keeps the freed setup for its hold pads (the window shift
    cancels against the early capture tap, so the raw cap is what the face path gains).  The cut is taken from the
    sender only where the sender bus is an ft slot output (registered: its last station) and every die port of that
    sender type bus is a plain lane: output max = T - the largest receiver input max of those ports.  Any other sender
    keeps its budget, so O + I <= T holds on every seam.  -> {"in": {type: {port: ps}}, "out": {type: {port: ps}}}."""
    cfg = P.clock.get("plain_seam_split")
    if not cfg:
        return {"in": {}, "out": {}}
    got = getattr(P, "_plain_seam_split", None)
    if got is not None:
        return got
    import landing_contract as LC
    T, sh = float(P.die["period_ps"]), ft_hop_in_share(P)
    full = (1 - sh) * T
    cap_w, cap_r = float(cfg["rx_in_max_ps"]), float(cfg.get("rx_in_raw_max_ps", full))
    slots = {tn: {s["name"] for s in t.get("ft_slots", [])} for tn, t in P.types.items()}
    ring = {}
    rin, src = {}, {}
    for pr in P.ports.values():
        s, d = pr["src"], pr["dst"]
        if DIE_PART in (s["part"], d["part"]):
            continue
        rt, st = P.parts[d["part"]]["type"], P.parts[s["part"]]["type"]
        db, sb = d["bus"], s["bus"]
        if rt not in ring:
            ring[rt] = {x.split("[")[0] for _c, sel in LC.ring_input_ports(P, rt) for x in sel}
        plain = db.endswith("_i") and db[:-2] in slots[rt] and db not in ring[rt]
        if plain:
            v = round(min(full, cap_r, cap_w - tap_window_io_shift(P, rt)[0]), 4)
            if v < full - 1e-6:
                rin.setdefault(rt, {})[db] = v
        if sb.endswith("_o") and sb[:-2] in slots[st]:
            src.setdefault((st, sb), []).append((rt, db, plain))
    rout = {}
    for (st, sb), rx in sorted(src.items()):
        if all(p for _r, _b, p in rx):
            v = round(T - max(rin.get(r, {}).get(b, full) for r, b, _p in rx), 4)
            if v > sh * T + 1e-6:
                rout.setdefault(st, {})[sb] = v
    P._plain_seam_split = {"in": rin, "out": rout}
    return P._plain_seam_split


def _ft_delay_lines(kind, ports, base, spl, fmt):
    """ft slot IO delay lines: the base value on the ports the plain-lane split leaves alone, one line per split value."""
    grp = {}
    for p in ports:
        grp.setdefault(spl.get(p), []).append(p)
    out = ""
    for v in [None] + sorted(k for k in grp if k is not None):
        if v in grp:
            out += (f"set_{kind}_delay -max {fmt(base if v is None else v)} -clock vclk "
                    f"[get_ports {{{' '.join(p + '[*]' for p in grp[v])}}}]\n")
    return out


# CLOCK-RESET IO-HOLD 10-25 (opt-in plan clock.seam_hold {sender_ps, seam_ps}; absent = the legacy contract above).
# Seam hold composes from the two kit checks: the sender's output hold (set_output_delay -min -sender_ps, its half
# uncertainty 12.5) guarantees port data >= vclk + 12.5 + sender_ps in its own propagated frame; the receiver's input
# hold (set_input_delay -min sender_ps - seam_ps, its half 12.5) guarantees port -> D >= capture - vclk + t_hold +
# 12.5 + seam_ps - sender_ps.  Summed in the die frame: seam hold slack >= seam_ps - (e_rx - e_tx), e = each kit's
# die-tap delivery error vs its sign-off (RCX-rebound) pin-register mean, i.e. the die related tap skew.  So seam_ps
# only has to cover the die tap skew bound (20 ps, decision 5 balance target) + routed-RCX error (5 ps); the 25 ps
# die hold uncertainty is already the two 12.5 halves.  The legacy contract (sender 0, receiver -tol 40) credits no
# clk->q: a pin-registered output has cq + port buffer 55.5-58 ps at FF (payload536 4_cts), so sender_ps 25 costs no
# sender padding while the receiver pads 40 ps less per seam bit (results/clock_iohold_0810).
SEAM_HOLD_MIN_PS = 25.0


def seam_hold(P):
    """{in_min_ps, out_min_ps, seam_ps, basis}: the kit min input / output delays vs vclk (ps) of the seam hold contract."""
    sh = P.clock.get("seam_hold")
    if not sh:
        tol = float(P.clock["insertion_tol_ps"])
        return dict(in_min_ps=-tol, out_min_ps=HOLD_OUT_MIN_PS, seam_ps=tol - HOLD_OUT_MIN_PS,
                    basis="legacy: receiver pads the whole insertion window (-insertion_tol), sender 0")
    snd, seam = float(sh["sender_ps"]), float(sh["seam_ps"])
    if snd < 0 or seam < SEAM_HOLD_MIN_PS:
        raise ValueError(f"clock.seam_hold: sender_ps {snd:g} must be >= 0 and seam_ps {seam:g} >= "
                         f"{SEAM_HOLD_MIN_PS:g} (die tap skew bound + RCX error)")
    return dict(in_min_ps=snd - seam, out_min_ps=-snd, seam_ps=seam,
                basis=f"clock.seam_hold: sender {snd:g} ps after vclk, seam {seam:g} ps")


# INFRA-FIRST-R4 / COORD RULING 2026-10-26 11:24 (kit hold window; METHODOLOGY 12.4a "hold made safe by STRUCTURE",
# 12.8 d1 timing-contract class): opt-in plan clock.tap_window {window_ps}.  The die delivers the grid taps of one
# partition with a tap-to-tap arrival difference (related-pair damage after CPPR at the last tree node) of up to
# window_ps; the kit SDC with every tap on ONE ideal clock guaranteed nothing for it (W_intra = 0).  The window is a
# source latency range on every grid tap port, fixed in the plan BEFORE build and identical for every type:
#     set_clock_latency -source -early -clock clk -W [get_ports {taps}]   ;   ... -late ... 0 ...
# A path launched on one tap and captured on ANOTHER is then timed with the full W (hold: launch early / capture late;
# setup: launch late / capture early), so the kit's own hold repair covers any die tap pair within W.  Same-tap pairs
# keep their credit: OpenSTA CRPR removes the source-latency range at the common tap port once clocks are propagated
# (probe 2026-10-26, OpenSTA asap7lock: cross-tap hold -80 / same-tap 0 at W 80).  late = 0 keeps every max arrival
# (pin-register insertion gates, tap balance, sign-off clock check: arrival_max) unchanged.  The IO contract is kept
# exactly (one declared seam number, clock.seam_hold.seam_ps): the early tap would tighten the input setup and the
# output hold checks by W, so input max delays are W smaller and output min delays W larger in the SDC
# (tap_window_io_shift); the CONTRACT values (seam_hold, sender guarantees) are unchanged.  Pre-CTS (ideal clocks, no
# CRPR) the window would hit same-tap pairs too, so prects_estimate.tcl zeroes it and pre_cts.tcl restores it before
# the tree is built.  Requires clock.seam_hold (the seam half of the same ruling).
# DIE-S81-10 (COORD 2026-10-28 06:47, METHODOLOGY 12.3 v5.0 lifted the 12.8d early-tap ban): types with CP2 early core
# taps take the same window.  Each core tap port keeps its own early latency e (TT in the golden SDC, FF in
# core_taps_ff.sdc) as its late value and gets early -(e + W) (core_tap_window_tcl), so a core <-> grid-tap or
# core <-> other-core path sees the full W while CRPR still credits same-tap pairs at the common core tap port.
# TAPWIN-1109 (COORD ruling tapwin-1109, DIE-S81-85; OWNER 10-23 related-pair skew + CPPR, 11-03 insertion band at
# die STA): the die window_ps is the declared die tap-to-tap ARRIVAL BAND (absolute insertion range over the die), not
# the related-pair skew of one pair.  Charging it in full on every cross-tap reg2reg path (OpenSTA has no CRPR between
# two different source ports, so -early -W / -late 0 on each tap port costs a cross-tap pair the whole W) failed S81
# iqf__t1 on cross-tap paths only (1390 setup / 2319 hold violators, 10 / ~100 with W credited).  The shared part of
# the band is common to every tap of the type and is credited by CPPR in a related-pair view, so the kit SDC charges
# only the inter-tap related-pair budget X: tap_window_ps = min(window_ps, X) for every type without a MEASURED
# window.  X = clock.tap_window.related_pair_ps, a plan value only.  TAPWIN-FIX-1109 (COORD): there is NO default X.
# The former 40 ps default was not validated (S81 G50 proof, gate chain: iqf__t1 worst 80, unmeasured types median 78,
# 18 of 159 above 180): a type with no measurement and no plan related_pair_ps is charged window_ps, as before TAPWIN.
# Measured windows are kept as they are: clock.tap_window.per_type_ps (ceil10 of the type's
# measured related-pair damage) and per_port_ps (per-port measured damage) ARE the die clock's related-pair
# prediction, not the band.  The band itself and every pair above X are checked at die STA (die_sta_related
# W_intra reads this same function per region; damage > X fails there).  OpenSTA construct (probe tapwin_sta 11-09,
# asap7lock): a clock-level -source -early/-late on [get_clocks clk] and a generated clock per tap with -source the
# master port are NOT credited across ports (cross-tap still pays the full 180), so the per-port form with the
# budget X is the one construct that gives cross-tap X and same-tap 0 (CRPR at the common port).
def tap_window_band_ps(P, tn=None):
    """the plan's DECLARED window (ps): window_ps, or the type's per_type_ps entry; 0.0 without clock.tap_window.  This
    is the die arrival band / measured type window before the related-pair budget (tap_window_ps applies X)."""
    tw = P.clock.get("tap_window")
    if not tw:
        return 0.0
    w = float(tw["window_ps"])
    if tn is not None and tn in (tw.get("per_type_ps") or {}):
        w = float(tw["per_type_ps"][tn])
    per = float(P.die["period_ps"]) if hasattr(P, "die") else float("inf")
    if not 0 <= w <= per / 4:
        raise ValueError(f"clock.tap_window.window_ps {w:g} outside [0, T/4]")
    if not P.clock.get("seam_hold"):
        raise ValueError("clock.tap_window needs clock.seam_hold (COORD 11:24: one declared window for intra AND seam)")
    return w


def tap_related_pair_ps(P):
    """the inter-tap related-pair budget X (ps) the kit SDC charges a cross-tap pair of an unmeasured type: plan
    clock.tap_window.related_pair_ps, None when the plan gives none (TAPWIN-FIX-1109: no default; window_ps is charged)."""
    x = (P.clock.get("tap_window") or {}).get("related_pair_ps")
    if x is None:
        return None
    x = float(x)
    if not 0 <= x:
        raise ValueError(f"clock.tap_window.related_pair_ps {x:g} < 0")
    return x


def tap_window_measured(P, tn):
    """True when type tn carries a MEASURED window (per_type_ps entry or per_port_ps table): kept as declared."""
    tw = P.clock.get("tap_window") or {}
    return tn is not None and (tn in (tw.get("per_type_ps") or {}) or bool((tw.get("per_port_ps") or {}).get(tn)))


def tap_window_ps(P, tn=None):
    """the per-tap latency window W (ps) the kit SDC charges, 0.0 when absent (legacy kits unchanged).
    DIE-S81-41 (COORD 2026-10-31 05:0x, FLOW-15 04:54): clock.tap_window.per_type_ps {type: W_t} overrides the die
    value for type tn (12.24c block arrival contract per block, W_t from the die's measured related-pair damage of
    that type's regions); types not listed keep window_ps.  die_sta_related checks each region against its type's W.
    TAPWIN-1109: an unmeasured type (and the die value, tn None) charges min(window_ps, plan related_pair_ps X); with no
    plan X (TAPWIN-FIX-1109) it charges window_ps.  The full band is tap_window_band_ps."""
    w = tap_window_band_ps(P, tn)
    x = tap_related_pair_ps(P)
    if not w or tap_window_measured(P, tn) or x is None:
        return w
    return min(w, x)


# KW-FIX-4-SDC (COORD RULING 2026-11-03 10:49, plain-seam input-face class): MEASURED per-port window, opt-in plan
# clock.tap_window.per_port_ps {type: {kit clock port: D_p}} (die_sta_related --kit-window-out writes it from the die
# clock proof).  A flat -W on every port charges every cross-port pair the type's worst pair (t30: 133 ps cross-tap on
# the bay hops).  Per port, with late 0 kept on every port, a cross-port pair i -> j is timed with
#     setup: launch late 0, capture early -D_j      hold: launch early -D_i, capture late 0
# so the kit covers the die exactly when D_p >= max over the type's regions and every other tap q of the measured
#     damage(p early) = late(q) - early(p) - CPPR credit(p, q) (+ core-tap earliness offset, as the die kit contract)
# D_p is that maximum (ceil 1 ps, no margin: OWNER 11-02 no hold margin; nominal setup 12.24c).  CPPR: the credit is
# the die proof's range at the pair's last common tree node, so same-root taps (same region root / cppr_node) get the
# root's credit and cross-root taps only the die-root credit; same-PORT pairs keep OpenSTA's CRPR at the common port.
# (OpenSTA cannot credit a common path between two different source ports, so the credit is folded into D_p.)
# Fallback: a type without a per_port_ps entry keeps the flat window_ps / per_type_ps value W_t (byte-identical SDC);
# a listed type's port missing from its table takes W_t on that port (named in an SDC comment).
# IO stays a contract check against vclk; one uniform shift cannot follow per-port windows, so: input max delays are
# shifted by the LARGEST port window (input setup never tighter than before; at most max - D_p optimistic at port p,
# priced in the SDC comment; seams are judged on measured arrivals at die level) and output min delays by the
# SMALLEST (output/sender hold never looser than the contract).  Without a table both shifts are W_t, as before.
def tap_window_port_table(P, tn):
    """{port: D_p}: the type's measured per-port windows (plan clock.tap_window.per_port_ps[tn]); {} = none (flat W)."""
    tw = P.clock.get("tap_window") or {}
    tab = (tw.get("per_port_ps") or {}).get(tn) or {}
    if not tab:
        return {}
    per = float(P.die["period_ps"]) if hasattr(P, "die") else float("inf")
    out = {}
    for n, v in tab.items():
        v = float(v)
        if not 0 <= v <= per / 4:
            raise ValueError(f"clock.tap_window.per_port_ps[{tn}][{n}] {v:g} outside [0, T/4]")
        out[n] = v
    return out


def window_port_names(P, tn):
    """every port that carries a window line: grid / edge window ports, then the early core taps (ordered, unique)."""
    out = [n for _ck, ports in tap_window_ports(P, tn) for n in ports]
    for n, *_r in core_tap_rows(P, tn):
        if n not in out:
            out.append(n)
    return out


def port_window_ps(P, tn, port):
    """the window of one kit clock port: its measured D_p, else the type's flat W_t (fallback)."""
    tab = tap_window_port_table(P, tn)
    return tab[port] if port in tab else tap_window_ps(P, tn)


def tap_window_fallback_ports(P, tn):
    """window ports of a type WITH a per-port table that the table does not list (they take W_t); [] without a table."""
    tab = tap_window_port_table(P, tn)
    return [n for n in window_port_names(P, tn) if n not in tab] if tab else []


def tap_window_max_ps(P, tn=None):
    """the largest per-port window of the type (= W_t without a table): hold-gate screen + input max shift."""
    w = tap_window_ps(P, tn)
    if not w or tn is None or not tap_window_port_table(P, tn):
        return w
    return max(port_window_ps(P, tn, n) for n in window_port_names(P, tn))


def tap_window_min_ps(P, tn=None):
    """the smallest per-port window of the type (= W_t without a table): output min shift."""
    w = tap_window_ps(P, tn)
    if not w or tn is None or not tap_window_port_table(P, tn):
        return w
    return min(port_window_ps(P, tn, n) for n in window_port_names(P, tn))


def tap_window_note(P, tn):
    """SDC / kit-log comment of the window form of type tn ('' without a window)."""
    w = tap_window_ps(P, tn)
    if not w:
        return ""
    if not tap_window_port_table(P, tn):
        if not tap_window_measured(P, tn) and tap_window_band_ps(P, tn) > w:
            return (f"# tap window: related-pair budget {w:g} ps on every window port (TAPWIN-1109: die band "
                    f"{tap_window_band_ps(P, tn):g} ps is common to every tap and checked at die STA; {tn} has no "
                    "measured clock.tap_window.per_type_ps / per_port_ps)\n")
        return (f"# tap window: flat {w:g} ps on every window port (no measured clock.tap_window.per_port_ps for "
                f"{tn}: FALLBACK to the plan window_ps / per_type_ps)\n")
    fb = tap_window_fallback_ports(P, tn)
    hi, lo = tap_window_max_ps(P, tn), tap_window_min_ps(P, tn)
    return (f"# tap window: MEASURED per port (plan clock.tap_window.per_port_ps, die proof damage with CPPR credit), "
            f"{lo:g}..{hi:g} ps; IO shift input -{hi:g} / output +{lo:g} (input setup credit <= {hi - lo:g} ps at the "
            f"smallest-window port)" + (f"; FALLBACK W {w:g} ps on unmeasured ports {' '.join(fb)}" if fb else "") + "\n")


_TW_NOTED = set()


def note_tap_window_fallback(P, tn):
    """kit-log note (stderr, once per die / type) when a windowed type has no measured per-port table: its SDC keeps
    the flat W_t (byte-identical to before KW-FIX-4-SDC)."""
    if not tap_window_ps(P, tn) or tap_window_port_table(P, tn):
        return
    has = bool((P.clock.get("tap_window") or {}).get("per_port_ps"))
    key = (id(P), tn if has else None)
    if key in _TW_NOTED:
        return
    _TW_NOTED.add(key)
    sys.stderr.write(f"TAP_WINDOW FALLBACK {getattr(P, 'name', '?')} "
                     + (f"type {tn}: no clock.tap_window.per_port_ps entry -> flat {tap_window_ps(P, tn):g} ps\n" if has
                        else "die: no measured clock.tap_window.per_port_ps -> flat window_ps / per_type_ps on every "
                        "windowed type\n"))


def tap_window_tcl(P, tn, value_ps=None, core=True):
    """the window's two set_clock_latency lines on the grid tap ports of type tn ('' without a window), then (core)
    the early-core-tap window lines (core_tap_window_tcl, TT).  value_ps overrides the early value (0 = the pre-CTS
    ideal stage).  core=False: grid / edge ports only (the golden SDC writes the core lines after the core taps' own
    source latency, which would otherwise overwrite them).  With a measured per-port table (KW-FIX-4-SDC) each port
    gets its own early end -D_p (ports of equal D share one line); late stays 0."""
    w = tap_window_ps(P, tn)
    if not w:
        return ""
    tab = tap_window_port_table(P, tn) if value_ps is None else {}
    out = ""
    for ck, ports in tap_window_ports(P, tn):
        if tab:
            grp = {}
            for n in ports:
                grp.setdefault(port_window_ps(P, tn, n), []).append(n)
            for v, ps in grp.items():
                out += (f"set_clock_latency -source -early -clock {ck} {t_lib(-v) + 0.0:.4f} "
                        f"[get_ports {{{' '.join(ps)}}}]\n")
        else:
            e = (-w if value_ps is None else -float(value_ps)) + 0.0     # never "-0.0000"
            out += f"set_clock_latency -source -early -clock {ck} {t_lib(e):.4f} [get_ports {{{' '.join(ports)}}}]\n"
        out += f"set_clock_latency -source -late -clock {ck} {t_lib(0.0):.4f} [get_ports {{{' '.join(ports)}}}]\n"
    return out + (core_tap_window_tcl(P, tn, value_ps=value_ps) if core else "")


def core_tap_window_tcl(P, tn, corner="TT", value_ps=None):
    """early-core-tap window lines of type tn at corner ('' without a window or core taps): one line per core tap
    port, set_clock_latency -source -early -clock clk -(early + W) [get_ports tap], written AFTER the port's own
    -source -clock clk -early line (which sets both early and late), so late keeps the core's own early latency and
    only the early end widens by W (the port's measured D_p with a per-port table).  value_ps overrides W (0 = the
    pre-CTS ideal stage: early back to the tap's own)."""
    w = tap_window_ps(P, tn)
    if not w:
        return ""
    out, seen = "", set()
    for n, _inst, _pin, early, _ins in core_tap_rows(P, tn, corner):
        if n in seen:
            continue
        seen.add(n)
        v = port_window_ps(P, tn, n) if value_ps is None else float(value_ps)
        out += f"set_clock_latency -source -early -clock clk {t_lib(-(early + v)) + 0.0:.4f} [get_ports {n}]\n"
    return out


def tap_window_ports(P, tn):
    """[(clock, [ports])] the window applies to: every real clock source port of the type (the grid taps of clk and
    each PHY-edge clock port), so every input / output path sees the same early range and the IO shift stays exact.
    S81-RINGHOLD-3: a forwarded ring write clock is NOT a window port.  Its ring inputs are timed against that same
    forwarded edge at that same port, so launch and capture are one physical edge; a window there is charged in full on
    every ring bit (launch early -W, capture late 0) and OpenSTA has no CPPR on source latency (S81 t29: 180 of 321 ps).
    The window prices the receiver's tap spread, which fclk does not see: fclk<->clk are -ignore_clock_latency."""
    ring = ring_writer_clocks(P, tn)
    return ([("clk", [n for n, _x, _y in clock_pins(P, tn)])] +
            [(n, [n]) for n, _x, _y, _m in edge_clock_pins(P, tn) if n not in ring])


def ring_writer_clocks(P, tn):
    """the forwarded clocks that write a source-synchronous landing ring of type tn (empty set: no forwarded ring)."""
    import landing_contract as LC
    return {ck for ck, _sel in LC.ring_input_ports(P, tn)}


def tap_window_io_shift(P, tn=None):
    """(input max delay shift, output min delay shift) in ps that keep the IO contract exact under the window."""
    w = tap_window_ps(P, tn)
    if w and tn is not None and tap_window_port_table(P, tn):
        return -tap_window_max_ps(P, tn), tap_window_min_ps(P, tn)     # KW-FIX-4-SDC: see tap_window_port_table
    return -w, w


def hold_out_min_sdc_ps(P, tn=None):
    """the output min delay WRITTEN in the kit SDC / gate / sign-off overlay: contract hold_out_min_ps + window."""
    return hold_out_min_ps(P, tn) + tap_window_io_shift(P, tn)[1]


def hold_in_min_ps(P):
    """seam-hold padding: the kit's min input delay vs vclk (ps)."""
    return seam_hold(P)["in_min_ps"]


def hold_out_min_ps(P, tn=None):
    """Contract output-min, tightened by the type's own checked sender guarantee."""
    base = seam_hold(P)["out_min_ps"]
    guarantee = out_hold_check_ps(P, tn) if tn is not None else None
    return base if guarantee is None else min(base, (1 - UNC_SPLIT) * unc_hold_ps() - guarantee)


def out_hold_check_ps(P, tn):
    """Declared guarantee checked by this sender kit, not a measured clock trim."""
    value = (P.types.get(tn, {}).get("clock", {}) or {}).get("out_hold_check_ps")
    return None if value is None else float(value)


# IO-HOLD option A (COORD ruling 2026-10-25 10:23, KITS-SPARE PROPOSAL IO-HOLD-2; opt-in: plan clock.io_hold =
# "sender_min" or env OT_IO_HOLD=sender_min at generation).  The flat receiver min input delay (-insertion_tol, or
# the seam_hold receiver share) assumes the neighbour's face flop may change its output at vclk - 40 ps with no
# clk->q.  Every partition output is a pin register whose own sign-off proves it changes no earlier than
#     vclk + (1 - UNC_SPLIT) x UNC_HOLD_PS - out_min        (its output hold check, kit frame)
# (12.5 ps with the legacy out_min 0; measured payload536 / cfg7bfp registered outputs land 53-65 ps after the bound,
# so the guarantee is far from tight).  Option A: each partition input's min input delay = that guarantee of the
# partition that drives it (per port, from the plan's port list; a sender type's signed view may publish a larger
# measured guarantee as types[].clock.out_hold_guarantee_ps).  Ports driven from the die edge (@die), through a
# planned die channel, or with any instance of the type undriven keep the fallback (seam_hold / legacy) contract.
# What the kits then no longer cover -- the related tap pair skew between sender and receiver and the 12.5-ps
# receiver uncertainty half the sender guarantee already used -- is checked ONCE at the parent: a related-pair FF
# hold check with CPPR on the assembled real views (io_hold_parent.py over die_sta.py).  A kit signed off under A
# counts only once that parent check covers its input seams (COORD 10:23).
IO_HOLD_MODES = ("legacy", "sender_min", "plan_demand")
# HOLD-REPAIR 10-26 (METHODOLOGY 12.4a a1: flow-inserted hold delay on DATA paths, clock untouched): "plan_demand" =
# option A plus the plan-declared seam hold demand D (clock.hold_demand, written by tools/die_plan/hold_demand.py from
# the plan's clock arrival model: CPPR-left OCV pessimism of the non-common clock branches + the declared arrival
# window).  Each partition-driven input takes min input delay = sender guarantee - D, so the RECEIVING tile's own FF
# hold repair pads that input (tile self-contained, option (a) of hold_demand.HOLD_PLACEMENT_RATIONALE); the parent
# check (io_hold_parent.py) still verifies the assembled die.  D is a plan number only: clock.hold_demand.source must
# be "plan" (never a measured arrival or trim, 12.8).  Seams listed in hold_demand.landed are closed by a landed hop
# and keep the fallback contract.  The structural hold gate (hold_gate.tcl) keeps the option A values
# (ot_io_hold_apply_structural): the declared demand is an obligation for the repair, not a structural failure.


def io_hold_mode(P, tn=None):
    """'legacy' (flat in_min on every input, default) or 'sender_min' (option A): plan clock.io_hold > env OT_IO_HOLD."""
    import os
    v = (P.types.get(tn, {}).get("clock", {}) or {}).get("io_hold") if tn is not None else None
    if v is None:
        v = P.clock.get("io_hold")
    if v is None:
        v = os.environ.get("OT_IO_HOLD") or "legacy"
    if v not in IO_HOLD_MODES:
        raise ValueError(f"clock.io_hold / OT_IO_HOLD: '{v}' not in {IO_HOLD_MODES}")
    return v


def sender_out_guarantee_ps(P, snd_type):
    """(ps after vclk, basis): the earliest a registered output of partition type snd_type changes, as its own
    signed-off output hold check guarantees: the signed view's published types[].clock.out_hold_guarantee_ps,
    else the plan contract (1 - UNC_SPLIT) x UNC_HOLD_PS - hold_out_min_ps."""
    ck = P.types.get(snd_type, {}).get("clock", {}) or {}
    checked = out_hold_check_ps(P, snd_type)
    if ck.get("out_hold_guarantee_ps") is not None and (checked is None or float(ck["out_hold_guarantee_ps"]) >= checked):
        return float(ck["out_hold_guarantee_ps"]), f"signed view {snd_type}"
    if checked is not None:
        return checked, f"sender kit check {snd_type}"
    return (1 - UNC_SPLIT) * unc_hold_ps() - hold_out_min_ps(P), "plan contract"


def hold_demand_ps(P, snd_part, rcv_part):
    """HOLD-REPAIR plan_demand: the plan-declared FF seam hold demand D (ps) of the sender -> receiver pair, or None
    when the seam is declared landed.  Keys: 'snd>rcv' (directed) first, then 'a|b' (sorted pair), then default_ps."""
    hd = P.clock.get("hold_demand")
    if not hd:
        raise ValueError("clock.io_hold plan_demand needs clock.hold_demand (tools/die_plan/hold_demand.py)")
    if hd.get("source") != "plan":
        raise ValueError("clock.hold_demand.source must be 'plan': the demand derives from the plan's declared clock "
                         "arrival window, never from a measured trim (12.8)")
    k = "|".join(sorted((snd_part, rcv_part)))
    if k in (hd.get("landed") or ()):
        return None
    pairs = hd.get("pairs") or {}
    v = pairs.get(f"{snd_part}>{rcv_part}", pairs.get(k, hd.get("default_ps")))
    if v is None:
        raise ValueError(f"clock.hold_demand: no declared demand for seam {k} (and no default_ps)")
    if float(v) < 0:
        raise ValueError(f"clock.hold_demand: negative demand {v} for seam {k}")
    return float(v)


# CLOCK-KV-R21 (RULING CLOCK-KV-R20 (a)): opt-in clock.hold_demand source "die_sta" = the per-port-bit FF hold demand
# the SHARED die gate (die_sta_related.py) measured on the assembled die (tools/die_plan/hold_demand_die_sta.py).  The
# plan names the demand file + its sha256 and the provenance (gate JSON sha256, gate tool sha256); the file is checked
# against all three.  Type-hardened (worst instance per template bit).  The kit SDC then TIGHTENS, per bit, the min
# input delay (receiver pads: inputs[type]) or the min output delay (sender pads, receiver is a macro without a P&R
# kit: outputs[type]) by demand_ps, so the kit's own FF hold repair inserts the hold delay on that data path; the
# parent die gate re-verifies with the real kit views.  "unplaced" bits (no kit on either side) are never emitted.
# It is independent of io_hold (legacy / sender_min) and of source "plan" (hold_demand_ps keeps refusing it).
HOLD_DEMAND_DIE_STA_SCHEMA = "opentallas.hold_demand.die_sta.v1"
_DIE_STA_CACHE = {}


def die_sta_hold_demand(P, tn):
    """None (no / plan-source hold_demand) or {'inputs': {sv_bus: {bit: [k, demand_ps]}}, 'outputs': {...}} for tn."""
    import hashlib
    hd = P.clock.get("hold_demand")
    if not hd or hd.get("source") != "die_sta":
        return None
    for k in ("file", "sha256", "gate_json_sha256", "tool_sha256"):
        if not hd.get(k):
            raise ValueError(f"clock.hold_demand source die_sta needs '{k}' (provenance)")
    f = Path(hd["file"])
    if not f.is_absolute():
        f = (Path(P.path).parent if getattr(P, "path", None) else Path.cwd()) / f
    if str(f) not in _DIE_STA_CACHE:
        raw = f.read_bytes()
        if hashlib.sha256(raw).hexdigest() != hd["sha256"]:
            raise ValueError(f"clock.hold_demand die_sta: {f} sha256 differs from the plan's")
        d = json.loads(raw)
        pv = d.get("provenance") or {}
        if d.get("schema") != HOLD_DEMAND_DIE_STA_SCHEMA:
            raise ValueError(f"clock.hold_demand die_sta: {f} schema {d.get('schema')}")
        if pv.get("gate_json_sha256") != hd["gate_json_sha256"] or pv.get("tool_sha256") != hd["tool_sha256"]:
            raise ValueError("clock.hold_demand die_sta: gate JSON / tool sha256 differ between plan and demand file")
        _DIE_STA_CACHE[str(f)] = d
    d = _DIE_STA_CACHE[str(f)]
    return dict(inputs=(d.get("inputs") or {}).get(tn, {}), outputs=(d.get("outputs") or {}).get(tn, {}))


def die_sta_sdc_lines(P, tn, side):
    """per-bit tightening lines (side 'inputs' | 'outputs'), one command per distinct value, after the bus-level -min."""
    dd = die_sta_hold_demand(P, tn)
    if not dd or not dd[side]:
        return ""
    if side == "inputs":
        A = input_hold_min(P, tn)
        base = lambda bus: A[bus]["in_min_ps"] if bus in A else hold_in_min_ps(P)
        cmd = "set_input_delay"
    else:
        base = lambda bus: hold_out_min_sdc_ps(P, tn)
        cmd = "set_output_delay"
    g = {}
    for bus, bits in dd[side].items():
        for bit, (k, dem) in bits.items():
            if k and float(dem) > 0:
                g.setdefault(round(base(bus) - float(dem), 4), []).append(f"{bus}[{int(bit)}]")
    hd = P.clock["hold_demand"]
    out = [f"# HOLD-DEMAND die_sta ({side}): per-bit FF hold demand of the shared die gate (gate json "
           f"{hd['gate_json_sha256'][:12]}, tool {hd['tool_sha256'][:12]}), type-hardened; tightens the bus-level -min"]
    for v, ports in sorted(g.items()):
        out.append(f"{cmd} -min {t_lib(v):.4f} -clock vclk [get_ports {{{' '.join(sorted(ports))}}}]")
    return "\n".join(out) + "\n"


def hold_pad_dont_touch_tcl(P, tn):
    """HOLDFORM-1 (DIE-QC-97 11-10): PRE_FLOORPLAN text keeping the gen_rtl.ot_dp_hd hold-pad cells (u_hdly_<bus>
    HB4xp67) through floorplan remove_buffers, timing-driven unbuffering and every repair / resizer pass, and failing the
    kit when the netlist lost any (N x width per bus, + N for an epoch bit).  "" for a type without hold_hb4 buses (byte-same)."""
    hb = [(int(b["hold_hb4"]), int(b["width"])) for b in P.types[tn].get("buses", [])
          if b.get("dir") == "in" and int(b.get("hold_hb4") or 0) > 0]
    if not hb:
        return ""
    lo, hi = sum(n * w for n, w in hb), sum(n * (w + 1) for n, w in hb)     # without / with the epoch bit
    return ("# HOLDFORM-1: keep the ot_dp_hd hold pads (gen_rtl.HOLD_CELLS)\n"
            "set ot_hb {}\n"
            "foreach i [[ord::get_db_block] getInsts] {\n"
            "  if {[string match *u_hdly_* [$i getName]] && [string match HB*xp67* [[$i getMaster] getName]]} "
            "{ lappend ot_hb $i }\n"
            "}\n"
            "foreach i $ot_hb { $i setDoNotTouch 1 }\n"
            f"puts \"OT_HOLDPAD dont_touch [llength $ot_hb] hold-pad cells (plan {lo}..{hi})\"\n"
            f"if {{[llength $ot_hb] < {lo} || [llength $ot_hb] > {hi}}} {{ error \"OT_HOLDPAD: netlist holds "
            f"[llength $ot_hb] hold-pad cells, plan expects {lo}..{hi}\" }}\n")


def input_hold_min(P, tn, structural=False):
    """IO-HOLD option A: {sv input port: dict(in_min_ps, basis, senders)} for every bus / ft-slot input of type tn
    whose min input delay differs from the fallback hold_in_min_ps(P).  Empty in legacy mode.  One value per port
    (the type is hardened once): the minimum over every instance's driver.  plan_demand (HOLD-REPAIR): each value
    is the sender guarantee minus the plan's seam hold demand D (hold_demand_ps); structural=True returns the plain
    option A values (the structural hold gate's view)."""
    mode = io_hold_mode(P, tn)
    if mode not in ("sender_min", "plan_demand"):
        return {}
    demand = mode == "plan_demand" and not structural
    import gen_rtl
    insts = sorted(n for n, p in P.parts.items() if p["type"] == tn)
    if not insts:
        return {}
    drv = {}                                   # (inst, bus) -> [port records]
    for pid, pr in P.ports.items():
        if pr["dst"]["part"] in insts:
            drv.setdefault((pr["dst"]["part"], pr["dst"]["bus"]), []).append((pid, pr))
    t = P.types[tn]
    # vector inputs only (COORD 15:23 / GEOM-REVIEW-2 15:54 (b)): 1-bit scalars (slot / valid / strobe controls) keep the
    # fallback contract, as rst and the strap_* ID pins (not plan buses) do
    in_buses = [b["name"] for b in t.get("buses", []) if b["dir"] == "in" and int(b.get("width", 2)) > 1]
    in_buses += [s["name"] + "_i" for s in t.get("ft_slots", []) if int(s.get("width", 2)) > 1]
    # DIE-QC-97 11-10: landed (clock-landing ring / landed ft) inputs are timed on their forwarded clock fclk_in_*
    # (landing_contract.ring_input_sdc, ring_hold); ot_io_hold_apply's `set_input_delay -min ... -clock $vclk` without
    # -add_delay would REPLACE those ring delays on the port, so they never take an option-A vclk value.
    landed = set((((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}))
    in_buses = [b for b in in_buses if b not in landed]
    out = {}
    for bus in in_buses:
        vals, why = [], None
        for inst in insts:
            prs = drv.get((inst, bus))
            if not prs:
                why = f"{inst}.{bus} undriven"
                break
            for pid, pr in prs:
                s = pr["src"]["part"]
                dv = (P.clock.get("io_hold_driver_views") or {}).get(pid)
                if s == DIE_PART and dv:
                    # CP1 proof harness: explicit registered upstream driver view of the full plan (COORD 23:26 (3));
                    # the seam itself is checked on the real parent (io_hold_parent.py)
                    g, basis = float(dv["out_hold_guarantee_ps"]), f"driver view {dv['type']} ({dv['basis']})"
                    if demand:
                        d = hold_demand_ps(P, dv["part"], inst)
                        if d is None:
                            why = f"{pid} landed seam"
                            break
                        g, basis = g - d, basis + f" - plan hold demand {d:g}"
                    vals.append((g, basis, dv["type"]))
                    continue
                if s == DIE_PART or s not in P.parts:
                    why = f"{pid} from the die edge"
                elif P.channel_of(pid) is not None:
                    why = f"{pid} through a die channel"
                if why:
                    break
                g, basis = sender_out_guarantee_ps(P, P.parts[s]["type"])
                if demand:
                    d = hold_demand_ps(P, s, inst)
                    if d is None:
                        why = f"{pid} landed seam"
                        break
                    g, basis = g - d, basis + f" - plan hold demand {d:g}"
                vals.append((g, basis, P.parts[s]["type"]))
            if why:
                break
        if why or not vals:
            continue
        g = min(v[0] for v in vals)
        out[gen_rtl.sv_id(bus)] = dict(in_min_ps=round(g, 4), basis=sorted({v[1] for v in vals if v[0] == g})[0],
                                       senders=sorted({v[2] for v in vals}))
    return out


def ring_hold_obligation(P, tn):
    """True when plan clock.ring_hold gives type tn's forwarded ring inputs the measured sender min (the ports
    sdc_lint._io_hold_ctx adds to hold_in_min_ports_ps): an option-A style parent obligation without io_hold.tcl."""
    if P.clock.get("ring_hold") is None:
        return False
    import landing_contract as LC
    return any(sel for _ck, sel in LC.ring_input_ports(P, tn))


def io_hold_tcl(P, tn):
    """kit io_hold.tcl (sender_min / plan_demand kits only): proc ot_io_hold_apply {vclk} re-applies the per-port min
    input delays of input_hold_min after a tool overlay set the fallback on every input (hold_gate.tcl; signoff.py
    reads sdc_lint.json).  plan_demand (HOLD-REPAIR): ot_io_hold_apply carries the STRUCTURAL option A values (the
    only caller is the pre-repair structural gate: the declared demand is padded by the FF GRT repair, not a
    structural failure); ot_io_hold_apply_demand carries the demand values of constraint.sdc / sdc_lint.json."""
    m = input_hold_min(P, tn)
    if not m:
        return None
    mode = io_hold_mode(P, tn)

    def proc(name, vals, msg):
        out = [f"proc {name} {{vclk}} {{"]
        for v, ports in _group_in_min(vals):
            out.append(f"  set_input_delay -min {t_lib(v):.4f} -clock $vclk [get_ports {{{' '.join(p + '[*]' for p in ports)}}}]")
        return out + [f"  puts \"{msg}\"", "}"]
    lines = [f"# GENERATED by tools/die_plan/gen.py phys: IO-HOLD option A per-port min input delays of {tn} "
             f"(plan {P.name}); fallback {hold_in_min_ps(P):g} ps on every other input"]
    if mode != "plan_demand":
        lines += proc("ot_io_hold_apply", m, f"OT_IO_HOLD sender_min ports {len(m)} fallback {hold_in_min_ps(P):g}")
    else:
        st = input_hold_min(P, tn, structural=True)
        lines += ["# HOLD-REPAIR plan_demand: ot_io_hold_apply = structural gate view (option A, demand excluded); "
                  "ot_io_hold_apply_demand = constraint.sdc values (sender guarantee - plan seam hold demand)"]
        lines += proc("ot_io_hold_apply", st, f"OT_IO_HOLD plan_demand structural ports {len(st)} fallback "
                      f"{hold_in_min_ps(P):g}")
        lines += proc("ot_io_hold_apply_demand", m, f"OT_IO_HOLD plan_demand demand ports {len(m)} fallback "
                      f"{hold_in_min_ps(P):g}")
    return "\n".join(lines) + "\n"


def _group_in_min(m):
    """[(in_min_ps, [ports])] sorted, one SDC command per distinct value."""
    g = {}
    for p, d in m.items():
        g.setdefault(d["in_min_ps"], []).append(p)
    return sorted((v, sorted(ps)) for v, ps in g.items())


# FLOW 10-25 (METHODOLOGY ruling 9.7, BRIEFING decision 5e; NEARMISS-STRUCT: 4 of 7 near misses = output pin register
# -> port FF hold against a vclk fixed at 250 ps while the routed FF pin-register mean was 190-220 ps).  The IO virtual
# clock stands for the neighbour's face flop, whose insertion tracks the corner: TT setup is timed against the TT
# insertion, FF hold against the FF insertion.  OpenSTA's -min/-max source latency are early/late, NOT setup/hold
# analysis (probe 2026-10-25: a -max 300 / -min 200 vclk put 300 on the min-path capture), so one SDC cannot carry
# both: constraint.sdc carries the TT value and the FF-only flow steps (FF GRT hold repair, post-CTS FF hold gate) and
# sign-off FF session switch the vclk to the FF value (vclk_corner.tcl).  Pre-route values: the type's measured
# signed view (types[].clock.insertion_ps / insertion_ff_ps, basis in insertion_basis) else the parent / die budget
# (clock.insertion_ps / insertion_ff_ps); FF absent -> FF_TT_INSERTION_RATIO x TT (routed RCX FF/TT pin-register mean
# ratio: ve_s 219.5/270.3 0.81, vmr_cqb 287.2/359.6 0.80, idx_vm 192/234 0.82, crh 240.6/292.5 0.82).  Sign-off
# rebinds each corner to its routed RCX pin-register mean and FAILs when it is more than insertion_tol_ps away from
# the bound value (signoff.py clock check).
FF_TT_INSERTION_RATIO = S.FF_TT_INSERTION_RATIO   # 0.81: one constant (schema)


ROOT_RESET_FALSE_PATH = (
    r"set_false_path -from [get_ports {arst_n}] -to "
    r"[get_pins -hierarchical -regexp {^u_rst_root[./]p\[[01]\]\$_DFF_PN0_/RESETN$}]"
)


def root_async_reset(P, tn):
    """Owner reset rule: only the unique whole-die two-flop async root is exempt.

    Every receiving partition's synchronous arst_n and all forwarded relays remain
    timed. Do not infer a reset waiver from an input name or an RTL comment.
    """
    import reset_tree as RT
    native = RT.bound_native_contract(P, tn)
    if native:
        return native["tree"]["entry"] == "sync"
    if not RT.wavefront(P) or P.types[tn].get("hard"):
        return False
    if RT.pad_false_path_pins(P, tn):
        # a declared die reset pad plan (PATH-KV-POR) already emits the ONE root CDC exception (raw pad ->
        # u_rst_root async + PLL analog); a second one would double the waiver (test_por_gate)
        return False
    if RT.wf_solve(P)["root_type"] != tn:
        return False
    if RT.sync_stages(P, tn) != 2:
        raise ValueError("owner reset contract requires exactly two root synchronizer stages")
    if sum(p["type"] == tn for p in P.parts.values()) != 1:
        raise ValueError("async root reset exception requires a unique root partition type")
    return True


def root_reset_false_path(P, tn):
    """A verified bound root may be nested; the default generator keeps its existing top-level target."""
    import reset_tree as RT
    native = RT.bound_native_contract(P, tn)
    if not native:
        return ROOT_RESET_FALSE_PATH
    if native["tree"]["entry"] != "sync":
        raise ValueError("receiving bound reset remains timed")
    prefix = "[./]".join(re.escape(x) for x in native["entry_path"].split("."))
    return (r"set_false_path -from [get_ports {arst_n}] -to "
            r"[get_pins -hierarchical -regexp {^" + prefix + r"[./]p\[[01]\]\$_DFF_PN0_/RESETN$}]")


def insertion_binding(P, tn):
    """{tt, ff, tol, basis, early_tap_ps}: the type's bound pin-register insertion per corner (ps)."""
    tc = P.types[tn].get("clock", {})
    common = float(P.clock["insertion_ps"])
    if "insertion_ps" in tc:
        tt, basis = float(tc["insertion_ps"]), tc.get("insertion_basis", "type clock.insertion_ps")
    else:
        tt, basis = common, "die clock budget"
    if "insertion_ff_ps" in tc:
        ff, fb = float(tc["insertion_ff_ps"]), tc.get("insertion_basis", "type clock.insertion_ff_ps")
    elif "insertion_ff_ps" in P.clock and "insertion_ps" not in tc:
        ff, fb = float(P.clock["insertion_ff_ps"]), "die clock budget"
    else:
        ff, fb = round(FF_TT_INSERTION_RATIO * tt, 1), f"FF_TT_INSERTION_RATIO {FF_TT_INSERTION_RATIO:g} x TT"
    if not 0 < ff <= tt:
        raise ValueError(f"type {tn}: bound FF insertion {ff:g} ps must be in (0, TT {tt:g}]")
    return dict(tt=tt, ff=ff, tol=float(tc.get("insertion_tol_ps", P.clock["insertion_tol_ps"])),
                basis=dict(tt=basis, ff=fb), early_tap_ps=max(0.0, tt - common))


# COORD 10-23 16:58 SDC PROXY ruling: a seam counts clock uncertainty ONCE.  The kit SDC splits it half/half between
# the sender (clk -> vclk: out ports) and the receiver (vclk -> clk: in ports); clk -> clk keeps the full value.
def _um(v):
    """exact um text for TCL: %g keeps 6 significant digits, so a 14048.64-um origin printed 14048.6 and place_macro
    -exact refused it (TRIAL-HBM 10-24: 23/88 B2 partitions).  4 decimals = 0.1 nm, below every ASAP7 grid."""
    t = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def _place_exact(name, x, y, orient):
    """place an instance at its plan origin in integer DBU (odb setLocation = bbox lower-left after setOrient):
    place_macro's um->dbu conversion truncates (6065.28 um -> 6065279 dbu) and refuses the off-site origin."""
    return (f"set _i [[ord::get_db_block] findInst {{{name}}}]; set _d [[ord::get_db_block] getDbUnitsPerMicron]; "
            f"$_i setPlacementStatus NONE; $_i setOrient {orient}; $_i setLocation [expr {{round({_um(x)} * $_d)}}] [expr {{round({_um(y)} * $_d)}}]; "
            f"$_i setPlacementStatus FIRM")


UNC_SPLIT = 0.5
# FLOW 10-25 F2: ASAP7 per-layer wire RC calibrated to routed RCX (tools/die_plan/setRC_rcx_asap7.tcl), copied into
# every kit as setRC_rcx.tcl; gen.py phys --stock-rc = the platform setRC.tcl (old basis)
RC_CAL_FILE, RC_CAL_KIT = "setRC_rcx_asap7.tcl", "setRC_rcx.tcl"
# FLOW 10-25: default FF-only GRT hold repair margin (run_kit.sh grt CORNERS=bc with the FF-bound vclk); = the
# kit HOLD_SLACK_MARGIN (owner 00:46: repair only 0..5 ps above the SDC).  gen.py phys --hold-mcmm = old MCMM GRT.
# FLOW-HOLD-1 (OWNER 12.19): 5 -> 10 ps for NEW kits (the shared core_flow.HOLD_FF_MARGIN_DEFAULT; 15 where a measured
# GRT->final RC hold loss > 10 ps is documented); signed views stay valid.
HOLD_FF_MARGIN_DEFAULT = 0.0   # OWNER 11-02 (FLOW-22): no +10 ps hold margin; every hold gate is FF hold slack >= 0 (25 ps FF hold uncertainty stays); was 10 (12.19)
# HOLD-REPAIR 10-26 (plan_demand kits only): repair_timing buffer cap and the HB4 hold-pad hook
HOLD_REPAIR_MAX_BUFFER_PERCENT = 100.0
HOLD_PAD_HB4 = Path(__file__).resolve().parents[2] / "physical" / "common_flow" / "hold_pad_hb4.tcl"
# FLOW-INFRA-2 10-25: GRT-RC tap pre-pass (tapbal_grt.tcl) between CTS and the FF GRT step.  Opt-in until the flow
# canaries pass with it (plan clock.tap_grt_pre, or OT_GEN_TAP_GRT_PRE=1 at generation for A/B kits); then default on.
TAP_GRT_PRE_DEFAULT = False


def _tap_grt_pre(P, t):
    """True when the kit runs the GRT-RC tap pre-pass (type clock.tap_grt_pre > plan clock.tap_grt_pre > env > default)."""
    import os
    v = t.get("clock", {}).get("tap_grt_pre", P.clock.get("tap_grt_pre"))
    if v is None:
        e = os.environ.get("OT_GEN_TAP_GRT_PRE")
        v = TAP_GRT_PRE_DEFAULT if e is None else e not in ("", "0")
    return bool(v)


HOLD_OUT_MIN_PS = 0.0   # min output delay of every partition output vs vclk (sdc_lint: must be <= 0)


def _density(t):
    """clock.tap_mode "density" (OWNER decision 5, 10-24): taps placed by sink density (taps.density_taps), no grid."""
    return t.get("clock", {}).get("tap_mode") == "density"


def tap_chain_affinity_exports(t):
    """Default-off, bounded per-bit pre-CTS grouping; no timing-budget change."""
    clock = t.get("clock", {})
    if "tap_chain_affinity" not in clock:
        return []
    spec = clock["tap_chain_affinity"]
    radius = float(spec.get("radius_um", clock.get("tap_radius_um", 200.)))
    limit = int(spec.get("max_group", 24))
    if not 0 < radius <= float(clock.get("tap_radius_um", 200.)):
        raise ValueError("tap_chain_affinity radius must fit the declared tap radius")
    if not 2 <= limit <= min(1200, _tap_cap(t)):
        raise ValueError("tap_chain_affinity group must fit the declared tap capacity")
    return ["export OT_TAP_CHAIN_AFFINITY = 1",
            f"export OT_TAP_CHAIN_RADIUS_UM = {radius:g}",
            f"export OT_TAP_CHAIN_MAX_GROUP = {limit}"]


def tap_group_exports(t):
    """DIE-QC-97 11-10: default-off clock.tap_group {"re": <group regex>} -> OT_TAP_GROUP_RE (clock_taps.tcl
    CLOCK-RESET 10-25 group form: every sink whose instance matches goes, with all bits of its group (capture 1 = key),
    to the tap nearest the group's sink centroid; grouped sinks are pinned against the cap pass).  For compact local
    blocks split over two taps (QC st_b station adders: launch/capture 10-20 um apart on two taps, hold repair then put
    227-417 ps of HB4 on the setup paths).  The canary caveat of clock_taps.tcl applies: use for compact blocks only,
    never long station rows.  The regex must not contain '#', '$' or whitespace (config.mk / make)."""
    clock = t.get("clock", {})
    if "tap_group" not in clock:
        return []
    rx = clock["tap_group"].get("re", "")
    if not rx or any(c in rx for c in "#$ \t\n") or "(" not in rx:
        raise ValueError("clock.tap_group.re must be a non-empty capture regex without '#', '$' or whitespace")
    import re as _re
    _re.compile(rx)
    return [f"export OT_TAP_GROUP_RE = {rx}"]


def tap_pair_affinity_exports(t):
    """QC-TYPES-6 11-07: default-off pre-CTS short-pair tap affinity (clock_taps.tcl -> tap_pair_affinity.tcl).
    Clock pins only; radius and group bounded by the declared tap radius and capacity."""
    clock = t.get("clock", {})
    if "tap_pair_affinity" not in clock:
        return []
    spec = clock["tap_pair_affinity"]
    tap_r = float(clock.get("tap_radius_um", 200.))
    radius = float(spec.get("radius_um", tap_r))
    group = int(spec.get("max_group", 64))
    merge = int(spec.get("merge_max", 128))
    pair_um = float(spec.get("pair_um", 60.))
    depth = int(spec.get("depth", 2))
    # DIE-QC-97 11-10: overfull_grow (default 0 = donate-only): an over-full tap may receive pair components up to
    # floor(initial load * grow) more sinks (tap_pair_plan.tcl OVERFULL ADMISSION; QC sle_hc0 density taps)
    grow = float(spec.get("overfull_grow", 0.))
    # DIE-QC-97 11-11: chains (default false): tap_chain_affinity-owned delay-pad chains join the pair graph with their
    # consumers (tap_pair_plan.tcl CHAINS; clock pins only)
    chains = spec.get("chains", False)
    if not isinstance(chains, bool):
        raise ValueError("tap_pair_affinity chains must be a boolean")
    cap = min(1200, _tap_cap(t))
    if not 0 <= grow <= 0.5:
        raise ValueError("tap_pair_affinity overfull_grow must be in [0, 0.5]")
    if not 0 < radius <= tap_r:
        raise ValueError("tap_pair_affinity radius must fit the declared tap radius")
    if not 2 <= group <= cap or not (merge == 0 or 2 <= merge <= cap):
        raise ValueError("tap_pair_affinity group/merge must fit the declared tap capacity")
    if not 0 < pair_um <= 200 or not 0 <= depth <= 4:
        raise ValueError("tap_pair_affinity pair_um/depth out of range")
    return ["export OT_TAP_PAIR_AFFINITY = 1",
            f"export OT_TAP_PAIR_RADIUS_UM = {radius:g}",
            f"export OT_TAP_PAIR_GROUP = {group}",
            f"export OT_TAP_PAIR_MERGE = {merge}",
            f"export OT_TAP_PAIR_UM = {pair_um:g}",
            f"export OT_TAP_PAIR_DEPTH = {depth}"] + \
        ([f"export OT_TAP_PAIR_OVERFULL_GROW = {grow:g}"] if grow > 0 else []) + \
        (["export OT_TAP_PAIR_CHAINS = 1"] if chains else [])


# COORD 11-09 (HBM-CORES-B): HBM kits hang TYPE-SAFE-1 hop lockup latches (u_fl_rst_*) on their capture tap by
# default (clock_taps.tcl OT_HOP_LATCH_CAPTURE_TAP).  Only a latch whose capture tap differs moves; RTL unchanged.
# Other dies stay opt-in until the first HBM sign-off with it.
# COORD 11-09: vsN1's L201 hop latches (u_fl_L201x1_o_*, vsN2 u_fl_L201x2_o_*) are in the default too.  The re-hung
# launch -> latch hop is hold-padded at GRT by construction (grt_pre.tcl HOPLATCH-HOLD, OT_HOP_LATCH_HOLD_PS).
HOP_LATCH_CAPTURE_TAP_DEFAULT = {"hbm": "u_fl_rst_ u_fl_L201x"}


def _hop_latch_capture_tap(P):
    """OT_HOP_LATCH_CAPTURE_TAP value (space-separated regexes) or None.  GEN env OT_HOP_LATCH_CAPTURE_TAP (wave
    item_env, commas for spaces) wins; "0" or "off" = no line.  Else the die default (HBM dies: u_fl_rst_)."""
    env = os.environ.get("OT_HOP_LATCH_CAPTURE_TAP")
    if env is not None:
        v = " ".join(env.replace(",", " ").split())
        return None if v in ("", "0", "off") else v
    name = str(P.die.get("name") or "").lower()
    for pre, v in HOP_LATCH_CAPTURE_TAP_DEFAULT.items():
        if name.startswith(pre):
            return v
    return None


def _hop_latch_re(slot, k):
    """regex of the bound ft hop latch cells u_fl_<slot>_<face>_<k> (bind.py u_fl_{obus}_{k}, obus = <slot>_<face>)"""
    return f"u_fl_{slot}_[^_]+_{int(k)}[^0-9]"


def _hop_latch_tap_cfg(P, tn):
    """HBM-VSN-XTAP-2 11-11 form A': OT_HOP_LATCH_CAPTURE_TAP value = the die default / GEN env (_hop_latch_capture_tap)
    plus the plan's per-hop capture-tap latches of `tn` (schema.ft_hop_latch_tap); None = no line."""
    base = _hop_latch_capture_tap(P)
    res = [_hop_latch_re(s, k) for s, m in sorted(S.ft_hop_latch_tap(P.raw, tn).items())
           for k, v in sorted(m.items()) if v == "capture"]
    v = " ".join(([base] if base else []) + res)
    return v or None


def _hop_latch_frac_cfg(P, tn):
    """HBM-VSN-XTAP-2 11-11 form A': OT_HOP_LATCH_FRAC_MAP value 're=f ...' (schema.ft_hop_latch_frac); None = none."""
    v = " ".join(f"{_hop_latch_re(s, k)}={float(f):g}" for s, m in sorted(S.ft_hop_latch_frac(P.raw, tn).items())
                 for k, f in sorted(m.items()))
    return v or None


def _tap_cap(t):
    """OT_TAP_MAX_SINKS: the plan's clock.tap_max_sinks, else 3000 (COORD 10-23; applies to grid and added taps);
    density taps default to 1500 (decision 5: ~1000-1500 sinks a tap)."""
    return int(t.get("clock", {}).get("tap_max_sinks", 1500 if _density(t) else 3000))


def _density_cfg(t):
    """config.mk lines of a density kit (none otherwise: defaults unchanged).  The kit's cap pass may move a sink at
    most tap_radius_um further (grid kits: half the pitch); the GRT-RC tap hook (clock.tap_balance_rc, default
    grt_report) runs as POST_GLOBAL_ROUTE."""
    if not _density(t):
        return []
    ck = t.get("clock", {})
    mode = ck.get("tap_balance_rc", "grt_report")
    out = [f"export OT_TAP_REASSIGN_UM = {float(ck.get('tap_radius_um', 200.0)):g}"]
    if mode != "placement":     # grt_post.tcl sources tap_balance_grt.tcl when OT_TAP_GRT_MODE is set
        out += [f"export OT_TAP_GRT_MODE = {mode}"]
    return out


RING_FANOUT_TAG = "# OT_CLAND_RING_FANOUT"


def ring_fanout_sdc(P, tn):
    """DIE-QC-97 CLAND-RING-FO (b): set_max_fanout F [current_design] in the kit SDC of a type with landed rings
    (clock.landing_contract) when the plan sets the die bound clock.landing_ring_fanout_max = F > 0, so repair_design
    builds fanout trees on the ring enable / select / reset nets instead of flat placement buffers.  A design rule, not
    a timing exception (sdc_lint ring_fanout).  0 / absent or no landed ring: no line (byte-same kit SDC)."""
    import clock_landings as CL
    f = CL.ring_fanout_max(P.clock)
    opt = (P.clock or {}).get("landing_ring_sdc_max_fanout", False)
    if not isinstance(opt, bool):
        raise ValueError("clock.landing_ring_sdc_max_fanout must be a boolean")
    # pilot 1 (11-10 CTS): repair_design met the line with BUFx2 splits on long quasi-static nets (strap K -> dsel
    # place, 103 ring slew violators on st_ei), so the line is its own opt-in (default off) beside the bound F
    if not f or not opt or not P.types[tn].get("clock", {}).get("landing_contract"):
        return ""
    return (f"{RING_FANOUT_TAG} plan clock.landing_ring_fanout_max {f} (DIE-QC-97): ring nets built as fanout trees\n"
            f"set_max_fanout {f} [current_design]\n")


def sdc(P, tn, pins):
    """kit SDC.  Bus ports: IO_BUDGET x T each side (both ends register at the face).  ft slot ports (COORD 10-23 R3,
    hop share): the last station drives its out port over the slot's last L/k segment, so the out port keeps only the
    neighbour's face share (output delay FT_HOP_IN_SHARE x T) and the in port arrives after the upstream partition's
    last segment (input delay (1 - FT_HOP_IN_SHARE) x T) into this side's face-registered station 0."""
    per = t_lib(P.die["period_ps"])
    ib = insertion_binding(P, tn)
    lat = t_lib(ib["tt"])
    io = IO_BUDGET * per
    tw_in, _tw_out = tap_window_io_shift(P, tn)
    note_tap_window_fallback(P, tn)
    cks = [n for n, _, _ in clock_pins(P, tn) + core_tap_pins(P, tn)]
    slots = [sv for sv in (s_["name"] for s_ in P.types[tn].get("ft_slots", []))]
    ft_in = " ".join(f"{n}_i[*]" for n in slots)
    ft_out = " ".join(f"{n}_o[*]" for n in slots)
    out = (f"# GENERATED by tools/die_plan/gen.py phys: partition type {tn} of die_plan {P.name}.\n"
           f"# clock taps (R4 grid, one port per tap, local trees): {' '.join(cks)}\n"
           f"create_clock -name clk -period {per:.4f} [get_ports {{{' '.join(cks)}}}]\n"
           f"# neighbour boundary flops run on the bound insertion (TT {ib['tt']:g} ps here; FF {ib['ff']:g} ps via "
           f"the FF-only flow steps; ruling 9.7 / decision 5e): virtual IO clock\n"
           + "".join(f"# PHY-edge clock (plan clock.edge_clocks): synchronous with clk, period {m} x T\n"
                     f"create_clock -name {n} -period {m * per:.4f} [get_ports {n}]\n"
                     for n, _x, _y, m in edge_clock_pins(P, tn)) + edge_clock_latency_tcl(P, tn, "tt") +
           f"create_clock -name vclk -period {per:.4f}\n"
           f"set_clock_latency -source {lat:.4f} [get_clocks vclk]\n"
           + (f"# plan clock.tap_window (COORD 11:24): die tap-to-tap arrival window {tap_window_ps(P, tn):g} ps on every "
              "real clock port, [-W, 0]; IO delays shifted to keep the seam contract (gen_phys.tap_window_ps)\n"
              + (f"# TAPWIN-1109: W = related-pair budget {tap_window_ps(P, tn):g} ps (die band "
                 f"{tap_window_band_ps(P, tn):g} ps common to every tap, CPPR-credited, checked at die STA)\n"
                 if tap_window_band_ps(P, tn) > tap_window_ps(P, tn) else "")
              + (tap_window_note(P, tn) if tap_window_port_table(P, tn) else "")
              + tap_window_tcl(P, tn, core=False) if tap_window_ps(P, tn) else "") +
           f"# clock uncertainty: sign-off margin policy {_SL.margin_policy()} ({_SL.MARGIN_POLICY_RULE})\n"
           f"set_clock_uncertainty {t_lib(unc_setup_ps()):.4f} -setup [all_clocks]\n"
           f"set_clock_uncertainty {t_lib(unc_hold_ps()):.4f} -hold [all_clocks]\n"
           f"# seam paths: uncertainty counted once per seam (COORD 16:58): {UNC_SPLIT:g} on each partition side\n"
           f"set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup {t_lib(UNC_SPLIT * unc_setup_ps()):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup {t_lib((1 - UNC_SPLIT) * unc_setup_ps()):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold {t_lib(UNC_SPLIT * unc_hold_ps()):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold {t_lib((1 - UNC_SPLIT) * unc_hold_ps()):.4f}\n"
           "set non_clk_in [all_inputs -no_clocks]\n"
           f"set_input_delay -max {io + t_lib(tw_in):.4f} -clock vclk $non_clk_in\n"
           f"set_output_delay -max {io:.4f} -clock vclk [all_outputs]\n")
    source_ports = set()
    if core_tap_rows(P, tn) or edge_clock_latency(P, tn):
        out += "# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n"
    for n, inst, pin, early, ins in core_tap_rows(P, tn):
        if n in source_ports:
            continue
        source_ports.add(n)
        out += (f"# CP2 early core tap {n} ({inst}/{pin}: internal {ins:g} ps): the spine delivers it {early:g} ps early\n"
                f"set_clock_latency -source -clock clk {t_lib(-early):.4f} [get_ports {n}]\n")
    if source_ports and tap_window_ps(P, tn):
        out += (f"# plan clock.tap_window {tap_window_ps(P, tn):g} ps on the early core taps: early end -(early + W), "
                "late keeps the tap's own early latency\n" + core_tap_window_tcl(P, tn))
    if slots:
        sh = ft_hop_in_share(P)
        spl = plain_seam_split(P)
        s_in, s_out = spl["in"].get(tn, {}), spl["out"].get(tn, {})
        if not s_in and not s_out:
            out += (f"# ft slots: hop share {sh:g} T at the face, the rest is the last station segment\n"
                    f"set_input_delay -max {(1 - sh) * per + t_lib(tw_in):.4f} -clock vclk [get_ports {{{ft_in}}}]\n"
                    f"set_output_delay -max {sh * per:.4f} -clock vclk [get_ports {{{ft_out}}}]\n")
        else:
            out += (f"# ft slots: hop share {sh:g} T at the face, the rest is the last station segment; plan "
                    f"clock.plain_seam_split (plain-lane input budget event): plain-lane inputs "
                    f"{len(s_in)}, registered plain-lane senders {len(s_out)}\n"
                    + _ft_delay_lines("input", [f"{n}_i" for n in slots], (1 - sh) * per,
                                      {k: t_lib(v) for k, v in s_in.items()}, lambda v: f"{v + t_lib(tw_in):.4f}")
                    + _ft_delay_lines("output", [f"{n}_o" for n in slots], sh * per,
                                      {k: t_lib(v) for k, v in s_out.items()}, lambda v: f"{v:.4f}"))
    # hold (CP1 r6: seam hold -17..-25 ps; the max-only budget above also served as the MIN arrival, so the kit never
    # padded): the neighbour's face flop can launch from the fast end of the insertion window (ins - tol) with a
    # no clk-to-q / wire credit: min input delay hold_in_min_ps (-tol) on every input
    out += (f"set_input_delay -min {t_lib(hold_in_min_ps(P)):.4f} -clock vclk $non_clk_in\n")
    # IO-HOLD option A (opt-in clock.io_hold sender_min): partition-driven inputs take their sender's guaranteed
    # output-min instead; the related tap pair skew is checked at the parent (io_hold_parent.py)
    for v, ports in _group_in_min(input_hold_min(P, tn)):
        out += ((f"# IO-HOLD A: sender guaranteed output-min (+{v:g} ps after vclk)\n" if io_hold_mode(P, tn) != "plan_demand"
                 else f"# HOLD-REPAIR plan_demand: sender guarantee - plan seam hold demand ({v:g} ps vs vclk)\n")
                + f"set_input_delay -min {t_lib(v):.4f} -clock vclk [get_ports {{{' '.join(p + '[*]' for p in ports)}}}]\n")
    out += die_sta_sdc_lines(P, tn, "inputs")
    if root_async_reset(P, tn):
        out += "# Sole asynchronous die-root reset CDC (owner reset rule); forwarded reset remains timed.\n"
        out += root_reset_false_path(P, tn) + "\n"
    # CP1-R10 (sdc_lint): explicit min output delay.  Until 10-24 the plain set_output_delay also set the MIN output
    # delay to +IO_BUDGET x T, which waived the sender's half of the seam hold check (hold uncertainty counted 0.5x
    # at kit level).  0 = the neighbour's face flop holds at the budgeted insertion; tightening only.
    out += (f"set_output_delay -min {t_lib(hold_out_min_sdc_ps(P, tn)):.4f} -clock vclk [all_outputs]\n")
    out += die_sta_sdc_lines(P, tn, "outputs")
    import reset_tree as RT
    fp = RT.pad_false_path_pins(P, tn)
    if fp:
        # PATH-KV-POR 10-25 (CLOCK-RESET amendment): the reset ROOT type of a die reset pad plan: arst_n IS the raw pad.
        # Its only false paths end at the root synchroniser's async pin and the declared PLL analog pin; everything
        # downstream (rst_por_n, the lock qualifier, the wavefront relays) is timed (recovery / removal, data).
        out += ("# die reset pad (reset_tree.pad_false_path_pins): raw pad -> u_rst_root async + PLL analog pin only\n"
                f"set_false_path -from [get_ports arst_n] -to [get_pins {{{' '.join(fp)}}}]\n")
    ids = [sp["name"] for sp in P.types[tn].get("id_straps", [])]
    # MESO-STRAP-1 (OWNER 12.15a): count straps strap_ca_* (clock_landing_plan types[].count_straps), same rule 2
    ids += [sp["name"] for sp in P.types[tn].get("count_straps", [])]
    if ids:
        # HEAD-BIND-4 10-27 (OWNER 10-25 option B rule 2): declared partition ID straps are quasi-static, tied per
        # instance at the die top; the one allowed exception (sdc_lint straps)
        out += ("# OWNER 10-25 option B: per-instance ID straps (plan id_straps), tied at the parent\n"
                f"set_false_path -from [get_ports {{{' '.join(ids)}}}]\n")
    out += (f"set_load {IO_LOAD_FF / LIB_CAP_UNIT_FF:g} [all_outputs]\n"
            "set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $non_clk_in\n")
    out += edge_cdc_sdc(P, tn)
    if P.types[tn].get("clock", {}).get("landing_contract"):
        import landing_contract as LC
        out = LC.sdc(P, tn, out)
    out += ring_fanout_sdc(P, tn)
    import pad_clock as PC
    return PC.sdc(P, tn, out)




def content_physical_identity(c):
    """Optional kit-only physical specialization; logical bind identity remains unchanged."""
    inst, master = c.get("physical_inst"), c.get("physical_master")
    if (inst is None) != (master is None):
        raise ValueError(f"content {c['inst']}: physical_inst and physical_master must be declared together")
    if inst is not None and (not inst or not master):
        raise ValueError(f"content {c['inst']}: empty physical specialization identity")
    return (inst, master) if inst is not None else (c["inst"], c["module"])


_VIEW_LEF = {}


def pinband_macros(P, tn, macros, root=None, check_only=False):
    """PINBAND-1 11-06 (COORD 17:4x, QC-A0C-B6 class, default-on): a placed hard child whose signal M5 pin row lies
    under the partition top-grid M6 PG band (PDN) gets no via up without a VDD/VSS short.  Each such child moves in y
    by the smallest grid-keeping row multiple that clears every row (tools/die_plan/pinband_site.py: inside the kit
    core, gaps to the other macros kept).  Check only (report, no move) for a fully_fixed_macros type, a bump-port
    kit and the macros of a PHY PG domain; OT_PINBAND_SITE=0 = check only everywhere.  -> (macros, report | None)"""
    if not macros:
        return macros, None
    import pinband_site as PBS
    t = P.types[tn]
    base = Path(root) if root else Path(__file__).resolve().parent.parent.parent
    fixed = {i for d in phy_pg_domains(P, tn) for i in d[4]}
    lefs, kids, keep = {}, [], []
    for inst, mod, lef, lib, x, y, o in macros:
        f = _CR.resolve(lef, base) if lef else None
        if not f or not Path(f).is_file():
            continue
        lefs[mod] = Path(f)
        if inst in fixed:
            keep.append(inst)
        kids.append(dict(inst=inst, master=mod, orient=o, x=x, y=y))
    core = kit_core_area(t)
    move = PBS.enabled() and not check_only and not t.get("fully_fixed_macros")
    mv = [k for k in kids if k["inst"] not in keep]
    others = []
    for k in kids:
        if k["inst"] in keep:
            b = PBS.macro_body(lefs[k["master"]].read_text(errors="replace"), k["master"])
            if b:
                kw, kh = PBS.pin_rows(b)[:2]
                others.append((k["x"], k["y"], k["x"] + kw, k["y"] + kh))
    rep = PBS.site(mv, PDN, core, lambda m: lefs[m].read_text(errors="replace"), others=others, move=move)
    rep_fixed = PBS.site([dict(k) for k in kids if k["inst"] in keep], PDN, core,
                         lambda m: lefs[m].read_text(errors="replace"), move=False) if keep else None
    if rep_fixed:
        rep["refused"] += [dict(r, why="PHY PG domain macro (check only)") for r in rep_fixed["refused"]]
        rep["checked"] += rep_fixed["checked"]
    ny = {k["inst"]: k["y"] for k in mv}
    return [(i, m, l, b, x, ny.get(i, y), o) for i, m, l, b, x, y, o in macros], rep


def type_macros(P, tn):
    """content macros of a type the kit must place (COORD 10-23): hard_cores[] and contents[] that carry a hardened
    view (lef).  [(inst, module, lef, lib, x, y, orient)], type frame, origin + track offset.  A macro view without a
    placement is an error: G3 of a kit whose SRAM / ROM / cores float is meaningless."""
    t = P.types[tn]
    out = []

    def own_lef(c):
        # KW6-CODE 11-04: a lib with a view_lef receipt carries its signed view's LEF; the plan entry stays (no block key change)
        k = (c["lef"], c.get("lib"))
        if k not in _VIEW_LEF:
            import view_lef as VL
            import lef_override as LO
            import porous_views as PV
            # POROUS-ALL-1 11-10 (OWNER): opt-in real-shape child abstract (gen env OT_POROUS_VIEWS); unset = unchanged
            _VIEW_LEF[k] = PV.select(LO.select(VL.view_lef_for(c["lef"], c.get("lib"), _CR.resolve), _CR.resolve),
                                     _CR.resolve)
        return _VIEW_LEF[k]
    for c in t.get("hard_cores", []):
        if not c.get("lef"):
            continue
        ox, oy = c.get("track_offset_um", [0.0, 0.0])
        # DIE-KV-49 10-31: optional kit-only physical identity (content_physical_identity form); default unchanged
        pinst, pmaster = content_physical_identity(c) if ("physical_inst" in c or "physical_master" in c) else \
            (c["inst"], c.get("module", c["inst"]))
        out.append((pinst, pmaster, own_lef(c), c.get("lib"), c["origin_um"][0] + ox,
                    c["origin_um"][1] + oy, c.get("orient", "R0")))
    cores = {c["inst"] for c in t.get("hard_cores", [])}
    for c in t.get("contents", []):
        # S81-SERDES-PHY-1 10-31 (opt-in): one logical content placed as several hard leaves of the bound netlist
        for q in c.get("physical_parts", []) or []:
            out.append((q["physical_inst"], q["physical_master"], own_lef(q), q.get("lib"), q["origin_um"][0],
                        q["origin_um"][1], q.get("orient", "R0")))
        if not c.get("lef") or c["inst"] in cores:
            continue
        if "origin_um" not in c:
            raise ValueError(f"type {tn}: macro content {c['inst']} ({c['module']}) has a lef but no origin_um")
        physical_inst, physical_master = content_physical_identity(c)
        out.append((physical_inst, physical_master, own_lef(c), c.get("lib"), c["origin_um"][0], c["origin_um"][1],
                    c.get("orient", "R0")))
    return out


PHY_PG_NOTCH_SITE_UM = 0.054   # ASAP7 placement site width: the notched region edge sits on a site boundary
PHY_PG_NOTCH_ROW_UM = 0.27     # ASAP7 row height: the south-notched region edge sits on a row boundary


def phy_pg_west_notch(t, tn, name, rt, mac_x0, mac_y0=()):
    """S81-RCK-3 11-06 (COORD 09:41 class form for the S81 serdes types; opt-in type key phy_pg_west_notch_um = halo):
    the type's PHY supply region (no core cells) starts at its westmost macro edge minus the halo (floored to the site
    grid) instead of the partition edge.  The strip west of the PMA macros then takes core cells, so the clock drivers
    of the PMA clock pins (pma_rck / ck at the macro west end) land next to them instead of 401/412 um away below the
    region.  The region still covers every macro; die.pg.domains (die mesh, bumps) is unchanged.  Key absent = unchanged.
    S81-RCK-3 11-06 (pilots serdes__t4 vA/vB): phy_pg_south_notch_um = halo does the same for the south edge (lowest
    macro edge minus the halo, floored to the row grid).  vA (west notch only, region bottom 681.372) failed post-CTS GRT
    with 30859 overflow, all of it at x 1200-1500 / y 500-700: the 19-um channel between the decoder SRAMs (top 662.1)
    and the region; vB (region bottom 948.24 = PMA bottom - 4.32) routed GRT with 0 overflow."""
    rt = list(rt)
    halo = t.get("phy_pg_west_notch_um")
    if halo is not None and mac_x0:
        x = round(math.floor(round((min(mac_x0) - float(halo)) / PHY_PG_NOTCH_SITE_UM, 6)) * PHY_PG_NOTCH_SITE_UM, 4) + 0.0
        rt[0] = max(rt[0], x)
    halo = t.get("phy_pg_south_notch_um")
    if halo is not None and mac_y0:
        y = round(math.floor(round((min(mac_y0) - float(halo)) / PHY_PG_NOTCH_ROW_UM, 6)) * PHY_PG_NOTCH_ROW_UM, 4) + 0.0
        rt[1] = max(rt[1], y)
    return rt


def pg_placed_blocks(t):
    """The placed blocks a PHY PG domain is judged by (phy_pg_domains; tools/die_plan/fit_phy_pg_domains.py).

    S81-SERDES-PHY-1 10-31: a content with physical_parts is judged by its placed parts, not its logical lot.
    DIE-HBM-90-TSTRAP 11-07: a content that is the parent of SPLIT sub-cores (hard_cores with physical_inst
    <inst>.u_fcore.<...> or sub_core_parent <inst>; HBM-BIND-3 / DIE-QC-75, the parent design is wires-only glue around
    its subs) is judged by those hard sub-cores, which are in hard_cores themselves; the glue has no macro view of its
    own (HBM ot_pdie_serdes u_lk_* over chn/rx/tx).  A content without such sub-cores is unchanged.
    """
    hard = t.get("hard_cores", []) or []
    parents = {h["sub_core_parent"] for h in hard if h.get("sub_core_parent")}
    parents |= {str(h.get("physical_inst")).split(".u_fcore.")[0] for h in hard if ".u_fcore." in str(h.get("physical_inst") or "")}
    placed = []
    glue = [c for c in t.get("contents", []) if c.get("inst") in parents and not c.get("lef")]
    for c in t.get("contents", []) + hard:
        if any(c is g for g in glue):
            continue
        placed += ([dict(q, inst=q["physical_inst"]) for q in c["physical_parts"]]
                   if c.get("physical_parts") else [c])
    return placed


def phy_pg_clip(t, tn, name, rt, mac_box):
    """S81-TYPES-6 11-07 (COORD 23:0x (2) choice (a), class PHY-REGION-CLOCK-ENTRY; opt-in type key phy_pg_clip_um =
    PG landing margin): for a PHY domain modelled with macros, the hard placement blockage and the voltage region are
    clipped to the bounding box of the domain's PHY macros grown by the margin (snapped outward to the site / row grid)
    on all four sides, inside the die domain rect.  The VDDPHY M6/M7 straps (and the M7 pins the die M8/M9 VDDPHY mesh
    lands on) stay over the macros; core rows and the clock leaf then reach the macro clock/data pins from every side
    instead of from below a region that spans the partition.  Composes with the west/south notch keys (the tighter edge
    wins).  Key absent, or a domain without macros (phy_pg_offmodel) = unchanged."""
    m = t.get("phy_pg_clip_um")
    if m is None or not mac_box:
        return list(rt)
    m = float(m)
    st, rw = PHY_PG_NOTCH_SITE_UM, PHY_PG_NOTCH_ROW_UM
    x0 = round(math.floor(round((min(b[0] for b in mac_box) - m) / st, 6)) * st, 4) + 0.0
    y0 = round(math.floor(round((min(b[1] for b in mac_box) - m) / rw, 6)) * rw, 4) + 0.0
    x1 = round(math.ceil(round((max(b[2] for b in mac_box) + m) / st, 6)) * st, 4) + 0.0
    y1 = round(math.ceil(round((max(b[3] for b in mac_box) + m) / rw, 6)) * rw, 4) + 0.0
    return [max(rt[0], x0), max(rt[1], y0), min(rt[2], x1), min(rt[3], y1)]


def phy_pg_domains(P, tn):
    """PATH-KV-SYSC 10-25 (OWNER decision 7, PHY PG hook): the die.pg.domains that fall inside partition type tn, as
    [(name, power_net, ground_net, rect_type_um, [macro inst fully inside])].  Identical for every instance (a hardened
    type cannot carry per-instance supply variants); empty for every type without a PHY domain (kits unchanged).
    DIE-HEAD-5 opt-in: a type with "phy_pg_offmodel" (a non-empty note: the PHY body is not part of the partition view,
    e.g. the s81_head analog PMA behind the type pads) may hold a domain with no macro; the region then gets its VDDPHY
    straps/pins and the hard placement blockage only (no macro grid).  Default (key absent) unchanged: fail closed."""
    doms = P.die.get("pg", {}).get("domains", []) or []
    if not doms:
        return []
    insts = [n for n, p in P.parts.items() if p["type"] == tn]
    t = P.types[tn]
    per = []
    for inst in insts:
        a = P.rect(inst)
        got = []
        for d in doms:
            b = d["rect_um"]
            r = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
            if r[0] >= r[2] - 1e-6 or r[1] >= r[3] - 1e-6:   # DIE-HEAD-5: abutting neighbour domain (float sliver)
                continue
            u, v = P.to_type(inst, r[:2]), P.to_type(inst, r[2:])
            # S81-SERDES-PHY-3 10-31: + 0.0 folds a mirrored instance's -0.0 into 0.0 (serdes__t14 lk_EN3 MY gave -0.0 and
            # failed the per-instance identity below on the sign of zero alone)
            rt = [round(min(u[0], v[0]), 4) + 0.0, round(min(u[1], v[1]), 4) + 0.0, round(max(u[0], v[0]), 4) + 0.0,
                  round(max(u[1], v[1]), 4) + 0.0]
            mac, mac_x0, mac_y0, mac_box = [], [], [], []
            placed = pg_placed_blocks(t)
            for c in placed:
                if "origin_um" not in c or "outline_um" not in c:
                    continue
                x0, y0 = c["origin_um"]
                cw, ch = c["outline_um"]
                if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
                    cw, ch = ch, cw
                box = [x0, y0, x0 + cw, y0 + ch]
                ov = box[0] < rt[2] and box[2] > rt[0] and box[1] < rt[3] and box[3] > rt[1]
                if not ov:
                    continue
                if not (box[0] >= rt[0] and box[1] >= rt[1] and box[2] <= rt[2] and box[3] <= rt[3]):
                    raise ValueError(f"type {tn}: macro {c['inst']} straddles PG domain {d['name']} {rt}")
                mac.append(content_physical_identity(c)[0] if "physical_inst" in c or "physical_master" in c else c["inst"])
                mac_x0.append(box[0])
                mac_y0.append(box[1])
                mac_box.append(box)
            if not mac and not t.get("phy_pg_offmodel"):
                raise ValueError(f"type {tn}: PG domain {d['name']} holds no macro (a PHY domain powers its PHY macro)")
            rt = phy_pg_west_notch(t, tn, d["name"], rt, mac_x0, mac_y0)
            rt = phy_pg_clip(t, tn, d["name"], rt, mac_box)
            got.append((d["name"], d["nets"][0], d["nets"][1], rt, sorted(mac)))
        per.append(got)
    # DIE-HEAD-5: compare supply/geometry/macros, not the per-instance domain name (die.pg.domains names one per window)
    if any(json.dumps([x[1:] for x in g]) != json.dumps([x[1:] for x in per[0]]) for g in per):
        raise ValueError(f"type {tn}: per-instance PHY PG domains differ; cannot harden one type for them")
    return per[0]


def _tcl_re(s):
    return re.sub(r"([.\[\]()*+?^$|\\])", r"\\\1", s)


def die_islands_tcl(P, tn):
    """Reserve the accepted die clock driver islands in the actual tile placement.

    This does not move the tile clock ports, change tap assignment or rebuild the
    die mesh. The same union of island rectangles is hardened for each type.
    """
    t = P.types[tn]
    rects = t.get("clock", {}).get("die_islands_um", [])
    if not rects:
        return ""
    w, h = t["outline_um"]
    for x0, y0, x1, y1 in rects:
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError(f"{tn}: die clock island outside outline or empty: {[x0, y0, x1, y1]}")
    lines = ["# Generated physical reservation for accepted die clock driver islands.", "uplevel #0 {",
             "set di_b [ord::get_db_block]", "set di_u [[ord::get_db_tech] getDbUnitsPerMicron]",
             "source /work/keepout_phys.tcl", "set di_rects {}",
             "set di_count 0; set di_area 0.0; set di_rows 0"]
    for x0, y0, x1, y1 in rects:
        lines += [f"set di_x0 [expr {{round({x0:g}*$di_u)}}]; set di_y0 [expr {{round({y0:g}*$di_u)}}]",
                  f"set di_x1 [expr {{round({x1:g}*$di_u)}}]; set di_y1 [expr {{round({y1:g}*$di_u)}}]",
                  "odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1",
                  "lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]", "incr di_count",
                  "set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]",
                  "foreach di_r [$di_b getRows] {",
                  "  set di_box [$di_r getBBox]",
                  "  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }",
                  "}"]
    lines += ['ot_clear_keepout_physical $di_b $di_rects die_clock_islands', 'puts "OT_DIE_ISLANDS blockages=$di_count rectangle_area_sum_um2=$di_area row_intersections=$di_rows"', "}"]
    return "\n".join(lines) + "\n"


RESERVED_KINDS = ("die_clock_tree", "landing_ring_bank")


def reserved_sites_tcl(P, tn):
    """Opt-in clock.reserved_sites_um (FALLBACK-HEAD-2): per-type reserved site rectangles, type frame.

    kind die_clock_tree: die clock-tree cell sites (union over every instance of the type, mapped from the die
    tree); a permanent hard placement blockage, physical-only cells cleared, exactly like die_islands_um.
    kind landing_ring_bank: the landing ring storage bank; a GPL-only full blockage created AFTER the landing
    rings are FIRM in it (other logic stays out of the bank), released before DPL (DPL counts fixed cells
    under a blockage as not placed in rows). Returns (pre_tcl, post_landing_tcl, release_tcl); empty strings
    when the key is absent, so a plan without it emits a byte-identical kit.
    """
    t = P.types[tn]
    rows = t.get("clock", {}).get("reserved_sites_um", [])
    if not rows:
        return "", "", ""
    w, h = t["outline_um"]
    hard, bank = [], []
    for r in rows:
        x0, y0, x1, y1 = r["rect_um"]
        if r.get("kind") not in RESERVED_KINDS:
            raise ValueError(f"{tn}: reserved site kind {r.get('kind')} not in {RESERVED_KINDS}")
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError(f"{tn}: reserved site outside outline or empty: {[x0, y0, x1, y1]}")
        (hard if r["kind"] == "die_clock_tree" else bank).append((x0, y0, x1, y1))
    # A die clock-tree hole inside a ring bank is legal: landing_placement.tcl packs the ring around it
    # (cland_avoid_rects) and fails closed when the bank no longer holds the ring.
    def create(rects, var):
        out = []
        for x0, y0, x1, y1 in rects:
            q = f"[expr {{round({x0:g}*$rs_u)}}] [expr {{round({y0:g}*$rs_u)}}] [expr {{round({x1:g}*$rs_u)}}] [expr {{round({y1:g}*$rs_u)}}]"
            out += [f"set rs_k [odb::dbBlockage_create $rs_b {q}]", f"lappend {var} $rs_k", f"lappend rs_rects [list {q}]"]
        return out
    head = ["uplevel #0 {", "set rs_b [ord::get_db_block]", "set rs_u [[ord::get_db_tech] getDbUnitsPerMicron]",
            "set rs_rects {}"]
    pre = post = rel = ""
    if hard:
        pre = "\n".join(["# Generated (gen_phys reserved_sites_um): die clock-tree cell sites, permanent hard blockages.",
                          *head, "source /work/keepout_phys.tcl", "set rs_hard {}", *create(hard, "rs_hard"),
                          "ot_clear_keepout_physical $rs_b $rs_rects reserved_die_clock_tree",
                          # landing_placement.tcl packs ring/status cells around these (opt-in variable, default unset)
                          "set ::cland_avoid_rects $rs_rects",
                          f'puts "OT_RESERVED_SITES kind=die_clock_tree rects={len(hard)} area_um2={sum((c-a)*(d-b) for a,b,c,d in hard):.3f}"',
                          "}"]) + "\n"
    if bank:
        post = "\n".join(["# Generated (gen_phys reserved_sites_um): landing ring banks, GPL-only blockages after FIRM rings.",
                           *head, "set ::rs_bank {}", *create(bank, "::rs_bank"),
                           f'puts "OT_RESERVED_SITES kind=landing_ring_bank rects={len(bank)} area_um2={sum((c-a)*(d-b) for a,b,c,d in bank):.3f}"',
                           "}"]) + "\n"
        # DIE-HEAD-14 10-28: DPL (3_5) runs in a new OpenROAD process, so ::rs_bank from the GPL step (3_3) no longer
        # exists there (hd_tile flow: "released 0 of 1"); the blockages persist in the odb, so they are found by their
        # exact bank rectangles (dbu).  Fails closed unless exactly one blockage per bank rectangle is removed.
        want = " ".join(f"[list [expr {{round({x0:g}*$rs_u)}}] [expr {{round({y0:g}*$rs_u)}}] [expr {{round({x1:g}*$rs_u)}}] "
                        f"[expr {{round({y1:g}*$rs_u)}}]]" for x0, y0, x1, y1 in bank)
        rel = "\n".join(["# Generated (gen_phys reserved_sites_um): release the GPL-only ring-bank blockages before DPL.",
                          "set rs_n 0",
                          "set rs_u [[ord::get_db_tech] getDbUnitsPerMicron]",
                          f"set rs_want [list {want}]",
                          "foreach rs_k [[ord::get_db_block] getBlockages] { set rs_bb [$rs_k getBBox]; "
                          "if {[lsearch -exact $rs_want [list [$rs_bb xMin] [$rs_bb yMin] [$rs_bb xMax] [$rs_bb yMax]]] >= 0} "
                          "{ odb::dbBlockage_destroy $rs_k; incr rs_n } }",
                          f"if {{$rs_n != {len(bank)}}} {{ error \"OT_RESERVED_SITES released $rs_n of {len(bank)} ring-bank blockages\" }}",
                          'puts "OT_RESERVED_SITES released ring-bank blockages $rs_n before DPL"']) + "\n"
    return pre, post, rel


def _pdn_inst_patterns(instances):
    # PDN -instances is a Tcl list of regular expressions, not literal names.
    # ODB stores escaped Verilog brackets as literal backslash-bracket pairs.
    # Brace each list item so Tcl's list parser preserves the regex escapes.
    return " ".join("{^" + _tcl_re(re.sub(r"(?<!\\)([\[\]])", r"\\\1", inst)) + "$}"
                    for inst in instances)


def _macro_pg_layers(lef):
    text = Path(lef).read_text()
    levels = []
    for pin in ("VDD", "VSS"):
        block = re.search(r"\bPIN\s+" + pin + r"\b(.*?)\bEND\s+" + pin + r"\b", text, re.S)
        if block is None:
            raise ValueError(f"{lef}: missing {pin} geometry")
        got = set(re.findall(r"\bLAYER\s+(M[0-9]+)\s*;", block[1]))
        if len(got) != 1:
            raise ValueError(f"{lef}: ambiguous {pin} PG layers {got}")
        levels.extend(got)
    if levels[0] != levels[1] or levels[0] not in ("M5", "M6"):
        raise ValueError(f"{lef}: unsupported PHY PG interface {levels}")
    return levels[0] + " M" + str(int(levels[0][1:]) + 1)


# PG-CORECONN-1 10-28 (opt-in plan partition_types.<t>.core_pg_connect, default off = kit bytes unchanged): the
# kit PDN global_connect binds every hard core's VDD/VSS ITerm to the tile nets (logical), but outside the PHY-domain
# path no macro grid exists, so pdngen drops no via onto the core PG pins: in hd_tile all 10 core PG terms / 744 M5
# pin shapes are untouched by tile PG metal (PDNSim PSM-0069; an LVS open).  Each placed non-PHY macro gets a pdngen
# macro grid on its own LEF PG pin layer L, connected to the tile strap layer above it (M4->M5, M5->M6, M6->M7).
CORE_PG_UP = {"M4": "M5", "M5": "M6", "M6": "M7"}


_LEF_TEXT = {}


def _lef_text(lef):
    """LEF text, cached by (path, mtime, size): the S81 views are 3-8 MB and every macro use re-reads them."""
    st = Path(lef).stat()
    k = (str(lef), st.st_mtime_ns, st.st_size)
    if k not in _LEF_TEXT:
        _LEF_TEXT[k] = Path(lef).read_text(errors="replace")
    return _LEF_TEXT[k]


def macro_pg_pin_layers(lef):
    """{'VDD': {layers}, 'VSS': {layers}} of a macro LEF (PIN VDD / PIN VSS PORT geometry; missing pin -> empty)."""
    text = _lef_text(lef)
    out = {}
    for pin in ("VDD", "VSS"):
        block = re.search(r"\bPIN\s+" + pin + r"\b(.*?)\bEND\s+" + pin + r"\b", text, re.S)
        out[pin] = set(re.findall(r"\bLAYER\s+(M[0-9]+)\s*;", block[1])) if block else set()
    return out


def core_pg_connect_layer(lef):
    """(pin_layer, tile_layer) the macro's PG pins connect on: the highest LEF PG layer that has a tile strap layer
    above it (CORE_PG_UP), identical for VDD and VSS.  ValueError when the LEF has no connectable PG geometry."""
    got = macro_pg_pin_layers(lef)
    pick = {}
    for pin, lays in got.items():
        ok = sorted((l for l in lays if l in CORE_PG_UP), key=lambda l: int(l[1:]))
        if not ok:
            raise ValueError(f"{lef}: {pin} has no PG pin geometry on {'/'.join(CORE_PG_UP)} (found {sorted(lays)}); "
                             "core_pg_connect cannot land it on the tile grid")
        pick[pin] = ok[-1]
    if pick["VDD"] != pick["VSS"]:
        raise ValueError(f"{lef}: VDD on {pick['VDD']} but VSS on {pick['VSS']}; one macro grid needs one layer")
    return pick["VDD"], CORE_PG_UP[pick["VDD"]]


def macro_obs_layers(lef):
    """set of routing layers named in the macro LEF OBS sections."""
    text = _lef_text(lef)
    out = set()
    for blk in re.findall(r"\bOBS\b(.*?)\bEND\b", text, re.S):
        out |= set(re.findall(r"\bLAYER\s+(M[0-9]+)\s*;", blk))
    return out


def core_pg_landing(lef, strict=True):
    """core_pg_connect_layer, plus (implicit default-on only) ValueError when the view obstructs the tile layer above
    its PG pins: a buried-PG view (e.g. M5 PG under an M6/M7 OBS) cannot take the via and would fail pdngen with
    PDN-0006, so the implicit default skips it instead of breaking a kit that never opted in."""
    lo, hi = core_pg_connect_layer(lef)
    if not strict and hi in macro_obs_layers(lef):
        raise ValueError(f"{lef}: {lo} PG pins buried under OBS on {hi}; no landing for core_pg_connect")
    return lo, hi


# PG-CORECONN-3 11-03 (DIE-S81-51, COORD GO 18:44): hierarchical PG publish for M7-top views.  M7 is the tile's top
# PG layer (PDN -pins {M7}); a hardened view whose VDD/VSS straps are on M7 (S81 rom_elem_q / bf_col / capc5r /
# bksel_q, pitch 10.8, not on the tile 8.64 lattice) and that has no OBS-free landing below cannot be landed inside the
# tile (12.1a: tiles never use M8).  Its landing is the die M8 grid, which die_pdn_tcl already vias onto every
# partition M7 PG pin ({parts} macro grid, M7 -> M8).  pg_publish.tcl (POST_PDN_TCL) copies the macro's own M7 PG pin
# shapes onto the tile VDD / VSS pins (bpins, net from the master pin USE), so the abstract carries them and the die
# grid lands on them.  No tile metal is added and no view changes.
CORE_PG_PUBLISH = "M7"


def core_pg_mode(lef, strict=True):
    """('publish', 'M7') for a view whose VDD and VSS both carry M7 geometry and that has no landable lower layer
    (none on CORE_PG_UP, or the tile layer above it is under the view's OBS); else ('grid', lo, hi) =
    core_pg_landing.  ValueError when neither applies (no landable PG geometry)."""
    got = macro_pg_pin_layers(lef)
    if all(CORE_PG_PUBLISH in got[p] for p in ("VDD", "VSS")):
        try:
            lo, hi = core_pg_connect_layer(lef)
        except ValueError:
            return ("publish", CORE_PG_PUBLISH)
        if hi in macro_obs_layers(lef):
            return ("publish", CORE_PG_PUBLISH)
        return ("grid", lo, hi)
    return ("grid",) + tuple(core_pg_landing(lef, strict))


def core_pg_published(P, tn, macros, root=None, exclude=()):
    """[inst] of the type's placed macros that take the M7 publish (core_pg_mode 'publish'); [] when core_pg_connect
    is off."""
    if not core_pg_on(P, tn):
        return []
    import cores as C
    out = []
    for inst, _mod, lef, *_ in macros:
        if inst in exclude:
            continue
        try:
            if core_pg_mode(C.resolve(lef, root), _core_pg_strict(P, tn))[0] == "publish":
                out.append(inst)
        except ValueError:
            pass
    return out


def core_pg_publish_tcl(insts):
    """POST_PDN_TCL of PG-CORECONN-3: for every instance matching each pattern, each M7 shape of each POWER / GROUND
    master pin becomes a FIRM bpin of the tile bterm of the net that ITerm is on (global_connect).  The net must have
    the master pin's USE as its sig type (VDD <- POWER, VSS <- GROUND, never by order).  Fails loud on: no match, an
    unconnected / wrong-type PG ITerm, no tile bterm, an orientation other than R0/MX/MY/R180, no M7 PG shape, or an
    M7 PG shape that overlaps tile M7 PG metal of another supply net."""
    L = ["# GENERATED by tools/die_plan/gen.py phys (PG-CORECONN-3, gen_phys.core_pg_publish_tcl): M7-top macro PG",
         "# straps published as tile VDD/VSS pins; the die M8 grid lands on them (die_pdn_tcl {parts} M7 -> M8).",
         "# Runs after pdngen (POST_PDN_TCL); ORFS sources it inside a proc, so it runs at global scope.",
         "uplevel #0 {",
         "set pgp_b [ord::get_db_block]", f"set pgp_lay [[ord::get_db_tech] findLayer {CORE_PG_PUBLISH}]",
         "set pgp_pins 0; set pgp_insts 0",
         "proc pgp_xf {o W H a b c d} {",
         "  switch -- $o {",
         "    R0 { return [list $a $b $c $d] }",
         "    MX { return [list $a [expr {$H-$d}] $c [expr {$H-$b}]] }",
         "    MY { return [list [expr {$W-$c}] $b [expr {$W-$a}] $d] }",
         "    R180 { return [list [expr {$W-$c}] [expr {$H-$d}] [expr {$W-$a}] [expr {$H-$b}]] }",
         "    default { error \"OT_PG_PUBLISH: orientation $o not supported (R0/MX/MY/R180)\" }",
         "  }",
         "}",
         "# tile M7 PG metal + M7 pins per supply net, collected once after pdngen (before any publish)",
         "array set pgp_m7 {}",
         "foreach on [$pgp_b getNets] {",
         "  if {[$on getSigType] ni {POWER GROUND}} continue",
         "  set rs {}",
         "  foreach sw [$on getSWires] { foreach s [$sw getWires] {",
         "    if {[$s isVia] || [$s getTechLayer] ne $pgp_lay} continue",
         "    lappend rs [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]]",
         "  } }",
         "  set ot [$pgp_b findBTerm [$on getName]]",
         '  if {$ot ne "NULL" && $ot ne ""} {',
         "    foreach bp [$ot getBPins] { foreach x [$bp getBoxes] {",
         "      if {[$x getTechLayer] eq $pgp_lay} { lappend rs [list [$x xMin] [$x yMin] [$x xMax] [$x yMax]] }",
         "    } }",
         "  }",
         "  set pgp_m7([$on getName]) $rs",
         "}",
         "proc pgp_check {who net a b c d} {",
         "  global pgp_m7",
         "  foreach on [array names pgp_m7] {",
         "    if {$on eq [$net getName]} continue",
         "    foreach r $pgp_m7($on) {",
         "      lassign $r p q u v",
         "      if {$u <= $a || $p >= $c || $v <= $b || $q >= $d} continue",
         "      error \"OT_PG_PUBLISH $who: [$net getName] M7 box ($a $b $c $d) overlaps $on M7 ($p $q $u $v)\"",
         "    }",
         "  }",
         "}",
         "proc pgp_publish {pat} {",
         "  global pgp_b pgp_lay pgp_pins pgp_insts",
         "  set hit 0",
         "  foreach i [$pgp_b getInsts] {",
         "    if {![regexp -- $pat [$i getName]]} continue",
         "    incr hit",
         "    set m [$i getMaster]; set bb [$i getBBox]; set o [$i getOrient]",
         "    set X [$bb xMin]; set Y [$bb yMin]; set W [$m getWidth]; set H [$m getHeight]",
         "    set k 0",
         "    foreach it [$i getITerms] {",
         "      set mt [$it getMTerm]; set use [$mt getSigType]",
         '      if {$use ne "POWER" && $use ne "GROUND"} continue',
         "      set who \"[$i getName]/[$mt getName]\"",
         "      set n [$it getNet]",
         '      if {$n eq "NULL" || $n eq ""} { error "OT_PG_PUBLISH $who: $use pin is on no net" }',
         '      if {[$n getSigType] ne $use} { error "OT_PG_PUBLISH $who: master USE $use but net [$n getName] is [$n getSigType]" }',
         "      set bt [$pgp_b findBTerm [$n getName]]",
         '      if {$bt eq "NULL" || $bt eq ""} { error "OT_PG_PUBLISH $who: no tile pin [$n getName] (pdngen -pins)" }',
         '      if {[$bt getNet] ne $n} { error "OT_PG_PUBLISH $who: tile pin [$bt getName] is not on net [$n getName]" }',
         "      foreach mp [$mt getMPins] { foreach x [$mp getGeometry] {",
         "        if {[$x isVia] || [$x getTechLayer] ne $pgp_lay} continue",
         "        lassign [pgp_xf $o $W $H [$x xMin] [$x yMin] [$x xMax] [$x yMax]] a b c d",
         "        set a [expr {$a+$X}]; set b [expr {$b+$Y}]; set c [expr {$c+$X}]; set d [expr {$d+$Y}]",
         "        pgp_check $who $n $a $b $c $d",
         "        set bp [odb::dbBPin_create $bt]",
         "        odb::dbBox_create $bp $pgp_lay $a $b $c $d",
         "        $bp setPlacementStatus FIRM",
         "        incr k; incr pgp_pins",
         "      } }",
         "    }",
         f'    if {{$k == 0}} {{ error "OT_PG_PUBLISH [$i getName]: no {CORE_PG_PUBLISH} PG pin shape" }}',
         "    incr pgp_insts",
         "  }",
         '  if {$hit == 0} { error "OT_PG_PUBLISH: no instance matches $pat" }',
         "}"]
    for inst in insts:
        L.append(f"pgp_publish {_pdn_inst_patterns([inst])}   ;# {inst}")
    L += [f'puts "OT_PG_PUBLISH macros=$pgp_insts/{len(insts)} pins=$pgp_pins layer={CORE_PG_PUBLISH}"',
          f'if {{$pgp_insts < {len(insts)}}} {{ error "OT_PG_PUBLISH: published $pgp_insts of {len(insts)} macros" }}',
          "}"]
    return "\n".join(L) + "\n"


def core_pg_on(P, tn):
    """PG-CORECONN-2 class fix (DIE-S81-51 11-03): core_pg_connect is DEFAULT-ON.  Unset -> True (implicit), explicit
    false keeps the legacy kit bytes.  S81 plan_h2_2249: 136/158 macro-placing types never set it, so 18,993 placed
    macro PG pin sets got no via from the tile grid (physical open; sign-off 'pg' is a logical ITerm->net census and
    does not see it)."""
    v = P.types[tn].get("core_pg_connect")
    return True if v is None else bool(v)


def _core_pg_strict(P, tn):
    """explicit core_pg_connect: true keeps the hard error on a macro LEF without landable PG geometry; the implicit
    default skips such a macro with a pdn.tcl comment (its view must be regenerated with PG pins)."""
    return P.types[tn].get("core_pg_connect") is True


def core_pg_grids(P, tn, macros, root=None, exclude=()):
    """pdn.tcl lines of an opt-in type (core_pg_connect): one CORE macro grid per PG pin layer over the type's placed
    macros (hard_cores + hardened contents, minus `exclude` = PHY-domain macros), add_pdn_connect pin layer -> tile
    strap layer.  [] when not opted in or the type places no macro."""
    if not core_pg_on(P, tn):
        return []
    import cores as C
    groups, skipped, published = {}, [], []
    for inst, _mod, lef, *_ in macros:
        if inst in exclude:
            continue
        try:
            mode = core_pg_mode(C.resolve(lef, root), _core_pg_strict(P, tn))
        except ValueError as ex:
            if _core_pg_strict(P, tn):
                raise
            skipped.append((inst, str(ex)))
            continue
        if mode[0] == "publish":
            published.append(inst)
        else:
            groups.setdefault(mode[1:], []).append(inst)
    t = [f"# PG-CORECONN-2 (default-on): macro {i} skipped, view has no landable PG geometry: {e[:200]}"
         for i, e in skipped]
    t += [f"# PG-CORECONN-3: macro {i} M7 PG straps published as tile VDD/VSS pins (pg_publish.tcl); die M8 lands them"
          for i in published]
    for (lo, hi), insts in sorted(groups.items(), key=lambda kv: int(kv[0][0][1:])):
        g = f"core_pg_{lo}"
        t += [f"# PG-CORECONN-1 (core_pg_connect): {len(insts)} placed macro(s) with {lo} PG pins onto the tile {hi} straps",
              f"define_pdn_grid -macro -name {{{g}}} -instances {{{_pdn_inst_patterns(insts)}}} -voltage_domains {{CORE}} -halo {{0}}",
              f"add_pdn_connect -grid {{{g}}} -layers {{{lo} {hi}}}"]
    return t


def core_pg_unconnected(pdn, macros, root=None, exclude=(), strict=True, published=()):
    """[(inst, pin_layer, tile_layer)] placed non-PHY macros of `macros` that no macro grid of the pdn.tcl text lands
    (no define_pdn_grid -macro whose -instances matches the instance with an add_pdn_connect on its LEF PG layer to
    the strap layer above).  [] = every macro PG pin layer is connected."""
    import cores as C
    grids, conns = {}, {}
    for m in re.finditer(r"define_pdn_grid -macro -name \{(\S+?)\} -instances \{(.*)\} -voltage_domains", pdn):
        grids[m[1]] = [re.compile(p) for p in re.findall(r"\{(\^.*?\$)\}", m[2])]   # ODB-name regexes
    for m in re.finditer(r"add_pdn_connect -grid \{(\S+?)\} -layers \{(M\d+) (M\d+)\}", pdn):
        conns.setdefault(m[1], set()).add((m[2], m[3]))
    bad = []
    for inst, _mod, lef, *_ in macros:
        if inst in exclude:
            continue
        try:
            mode = core_pg_mode(C.resolve(lef, root), strict)
        except ValueError:
            if strict:
                raise
            continue      # implicit default-on: unlandable view already listed as a pdn.tcl comment
        if mode[0] == "publish":      # PG-CORECONN-3: landed by the die M8 grid iff pg_publish.tcl publishes it
            if inst not in published:
                bad.append((inst, mode[1], "die M8 (not published)"))
            continue
        lo, hi = mode[1:]
        name = re.sub(r"(?<!\\)([\[\]])", r"\\\1", inst)
        if not any((lo, hi) in conns.get(g, ()) and any(r.match(name) for r in pats) for g, pats in grids.items()):
            bad.append((inst, lo, hi))
    return bad


def phy_pg_pdn(P, tn, doms, macros, root=None, core_grids=False):
    """Partition PDN with separate PHY supply regions (OWNER decision 7; OpenROAD voltage regions, the die-level form is
    pg_regions.pdn_tcl).  CORE keeps the abutment-continuous grid of PDN everywhere outside the regions (pdngen cuts the
    core domain at other domains' regions); each region gets its own net (VDDPHY) + VSS: M6/M7 straps at the same
    die-phase widths / pitches (M7 exported as pins, so the abstract carries VDDPHY M7 only inside the region and the
    die M8/M9 VDDPHY mesh of die.pg.domains lands on it), a macro grid landing M6 on the macro's top-layer PG pins, and
    a hard placement blockage (no std cell in the region: it has no core followpins).  Content macros outside regions
    get a CORE macro grid (their M4 PG pins -> core M5 straps)."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    phy_insts = sorted({i for d in doms for i in d[4]})
    phy_layers = {m[0]: _macro_pg_layers(_CR.resolve(m[2], root)) for m in macros if m[0] in phy_insts}
    for name, pw, gd, r, mac in doms:
        nov = [i for i in mac if i not in phy_layers]
        if nov:     # S81-KITS-G 10-30: was a raw KeyError (u_phy status 'rework', no lef/lib in the plan)
            raise ValueError(f"PG domain {name} ({tn}): powered content {nov} has no macro view (lef/lib) in this kit")
    core_macros = [m[0] for m in macros if m[0] not in phy_insts]
    excl = "|".join(_tcl_re(i) for i in phy_insts)
    t = ["# GENERATED by tools/die_plan/gen.py phys: partition PDN with separate PHY supply regions (gen_phys.phy_pg_pdn).",
         "source /work/keepout_phys.tcl", "set b [ord::get_db_block]", "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]"]
    for net in sorted({d[1] for d in doms} - {"VDD"}):
        t += [f"set n [$b findNet {net}]", f'if {{$n eq "NULL"}} {{ set n [odb::dbNet_create $b {net}] }}',
              "$n setSigType POWER; $n setSpecial"]
    t += [f"add_global_connection -net {{VDD}} -inst_pattern {{^(?!({excl})$).*}} -pin_pattern {{^VDD$}} -power"
          if phy_insts else "add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power"]
    for name, pw, gd, r, mac in doms:
        if not mac:
            continue
        t += [f"add_global_connection -net {{{pw}}} -inst_pattern {{^({'|'.join(_tcl_re(i) for i in mac)})$}} "
              f"-pin_pattern {{^VDD$}} -power"]
    t += ["add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground", "global_connect",
          "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}"]
    for k, (name, pw, gd, r, mac) in enumerate(doms):
        rn = f"ot_phy_pg_{k}"
        t += [f"set region [odb::dbRegion_create $b {rn}]",
              f"odb::dbBox_create $region " + " ".join(f"[expr {{round({v:g}*$dbu)}}]" for v in r),
              f"set_voltage_domain -name {{{rn}}} -region {{{rn}}} -power {{{pw}}} -ground {{{gd}}}"]
    t += [ln for ln in PDN.splitlines()[5:] if ln.strip()]       # the CORE grid of PDN (after its global connects)
    for k, (name, pw, gd, r, mac) in enumerate(doms):
        rn = f"ot_phy_pg_{k}"
        if mac and len({phy_layers[i] for i in mac}) != 1:
            raise ValueError(f"PG domain {name}: mixed PHY PG interfaces require separate grids")
        t += [f"# PHY supply region {name}: {pw}/{gd} over {' '.join(mac)} (die.pg.domains, OWNER decision 7)",
              f"define_pdn_grid -name {{{rn}}} -voltage_domains {{{rn}}} -pins {{M7}}",
              f"add_pdn_stripe -grid {{{rn}}} -layer {{M6}} -width {{0.288}} -spacing {{0.096}} -pitch {{4.32}} -offset {{1.968}}",
              f"add_pdn_stripe -grid {{{rn}}} -layer {{M7}} -width {{0.288}} -spacing {{0.096}} -pitch {{8.64}} -offset {{4.128}}",
              f"add_pdn_connect -grid {{{rn}}} -layers {{M6 M7}}",
              *([f"define_pdn_grid -macro -name {{{rn}_macro}} -instances {{{_pdn_inst_patterns(mac)}}} -voltage_domains {{{rn}}} -halo {{0}}",
                 f"add_pdn_connect -grid {{{rn}_macro}} -layers {{{phy_layers[mac[0]]}}}"] if mac else
                [f"# off-model PHY body (type phy_pg_offmodel): no macro in {name}, region straps + blockage only"]),
              f"odb::dbBlockage_create $b " + " ".join(f"[expr {{round({v:g}*$dbu)}}]" for v in r),
              "ot_clear_keepout_physical $b [list [list " + " ".join(f"[expr {{round({v:g}*$dbu)}}]" for v in r) + "]] phy_supply_region"]
    if core_grids:      # core_pg_connect: per-LEF-layer CORE macro grids (core_pg_grids) replace the M4-only grid
        t += core_pg_grids(P, tn, macros, root, exclude=set(phy_insts))
    elif core_macros:
        t += ["# CORE content macros: M4 PG pins onto the core M5 straps",
              f"define_pdn_grid -macro -name {{core_macros}} -instances {{{_pdn_inst_patterns(core_macros)}}} -voltage_domains {{CORE}} -halo {{0}}",
              "add_pdn_connect -grid {core_macros} -layers {M4 M5}"]
    return "\n".join(t) + "\n"


def signed_mean_core_taps(P, tn):
    """Select measured means for explicitly SIGNED early or internal core CTS metadata."""
    ck = P.types[tn].get("clock", {}) or {}
    taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
    return bool(ck.get("core_taps") in ("early", "internal") and taps and P.types[tn].get("hard_cores")
                and all("insertion_ff_ps" in tp and str(tp.get("budget_owner", "")).startswith("SIGNED") for tp in taps))


def internal_core_taps_estimate(P, tn):
    """DIE-KV-60/taps (COORD 11-01 class event, default-on): clock.core_taps 'internal' whose core taps are not all
    SIGNED takes the estimate form the other dies use for unsigned early taps (budget_owner = the core or a plan
    budget): the legacy kit path, no mean contract.  Explicit parent_budget taps keep the --trial early-only rule."""
    ck = P.types[tn].get("clock", {}) or {}
    taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
    return bool(ck.get("core_taps") == "internal" and taps and not signed_mean_core_taps(P, tn)
                and not any(str(tp.get("budget_owner", "")).startswith("parent_budget") for tp in taps))


def core_mean_contract_options(P, tn, trial=False):
    """COORD 10-28 03:35: explicit parent budgets may drive non-release probes.

    Existing plans keep their legacy path. Parent-budget early taps take the selected
    view's explicit TT/FF contract (or the plan's own budget when the view has none) in
    trial and release kits alike, as a labelled estimate (signed=False,
    release_qualified=False). The contract reader still rejects ETM extrema as means.
    """
    if signed_mean_core_taps(P, tn):
        return dict(mean_contract=True, require_signed=True)
    ck = P.types[tn].get("clock", {}) or {}
    if ck.get("core_taps") == "internal":
        if internal_core_taps_estimate(P, tn):
            # DIE-KV-60/taps 11-01 (COORD class event, 12.27 default-on): a core not yet SIGNED keeps the estimate
            # form of every early-tap die (plan insertion; legacy kit rows labelled signed=False /
            # release_qualified=False); the type takes SIGNED means once all its cores are signed.
            return dict(mean_contract=False, require_signed=True)
        import core_clock_contract as CC
        raise CC.ContractError(f"{tn}: internal core CTS requires explicit SIGNED TT/FF mean metadata")
    taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
    budget = bool(ck.get("core_taps") == "early" and taps and P.types[tn].get("hard_cores")
                  and all("insertion_ff_ps" in tp and
                          str(tp.get("budget_owner", "")).startswith(("SIGNED", "parent_budget"))
                          for tp in taps)
                  and any(str(tp.get("budget_owner", "")).startswith("parent_budget") for tp in taps))
    if budget:
        # KIT-TRIAGE-1/G3 11-01 (class, default-on; OWNER 12.28b closure first): a release kit of a type whose early core
        # taps carry parent_budget means takes the same estimate form as a --trial kit (12.3 current-real-view latency,
        # 12.4a declared budget, labelled): rows signed=False / release_qualified=False; SIGNED means replace them once
        # the core view is signed.  The tap-vs-selected-mean and liberty-identity checks stay in force.
        return dict(mean_contract=True, require_signed=False)
    return dict(mean_contract=False, require_signed=True)


def core_physical_rows(P, tn, rows):
    """Label clock model consumers by their declared physical identities.

    Contracts are loaded by logical identity first. Preserve that identity for
    provenance; change only the consumer name used by kit taps/STA, not means,
    corners, pin names, source qualification or clock schedules.
    """
    aliases = {c["inst"]: content_physical_identity(c)[0]
               for c in P.types[tn].get("hard_cores", [])
               if "physical_inst" in c or "physical_master" in c}
    return [dict(r, logical_inst=r["inst"], inst=aliases[r["inst"]])
            if r["inst"] in aliases and aliases[r["inst"]] != r["inst"] else r
            for r in rows]


def core_latency_files(P, tn, kd, root=None, mean_contract=False, require_signed=True):
    """Write authoritative TT/FF boundary-register mean contracts for hard cores.

    Opt in with mean_contract=True; strict release export requires matching SIGNED measurements.
    The scalar CTS file uses TT; the JSON and FF file retain corner/source basis.
    ETM max_clock_tree_path is never substituted for a pin-register mean.
    """
    import core_clock_contract as CC
    rows = []
    if P.types[tn].get("hard_cores"):
        if mean_contract:
            rows = CC.latency_table(P, tn, root, require_signed=require_signed)
        else:
            # Existing kits retain their historical bound until their owner opts
            # into a measured mean or an explicit first-route parent budget.
            import cores as C
            rows = C.latency_table(P, tn, root)
            for row in rows:
                row.update(basis="legacy_etm_max_bound", signed=False, release_qualified=False)
    rows = core_physical_rows(P, tn, rows)
    if mean_contract:
        native_models = core_physical_rows(P, tn, CC.native_clock_models(P, tn, root))
        if native_models:
            (kd / "native_clock_models.json").write_text(json.dumps(dict(
                type=tn, rows=native_models), indent=1) + "\n")
    pending_view = []
    taps = core_tap_rows(P, tn, pending=pending_view)
    if pending_view:   # HBM-STREETS-3: PENDING-VIEW cores are reported, never PASS; retap when the signed view lands
        (kd / "merged_clock_pending_view.json").write_text(json.dumps(dict(
            type=tn, status="PENDING-VIEW", rule="COORD 10-27 19:12 HBM-STREETS-2 ruling 1", rows=pending_view),
            indent=1) + "\n")
    rebound = core_tap_view_report(P, tn) if taps and not mean_contract else []
    if rebound:
        (kd / "core_tap_view.json").write_text(json.dumps(dict(type=tn, rows=rebound), indent=1) + "\n")
        for r in rebound:
            print(f"OT_CORE_TAP_PIN {tn} {r['port']} {r['inst']} plan {r['plan_pin']} -> view {r['view_pin']} "
                  f"insertion {r['plan_insertion_ps']:g} -> {r['view_insertion_ps']:g} early {r['plan_early_ps']:g} -> {r['early_ps']:g}")
            if r["clamped"]:
                print(f"OT_CORE_TAP_CLAMP {tn} {r['port']} {r['inst']}/{r['view_pin']}: view insertion {r['view_insertion_ps']:g} "
                      f"needs more than the {r['early_ps']:g} ps a tap can deliver (die STA target, not a stop)")
    if rows and not mean_contract:
        by_pin = {(i, p): n for n, i, p, _e, _s in taps}
        for r in rows:
            if r.get("tap") == "grid" and (r["inst"], r["pin"]) in by_pin:
                r["tap"] = by_pin[(r["inst"], r["pin"])]
    if mean_contract:
        for _port, inst, pin, _early, insertion in taps:
            matching = [r for r in rows if r["inst"] == inst and (pin == "*" or r["pin"] == pin)]
            if not matching or any(abs(r["rise_ps"] - insertion) > .01 for r in matching):
                raise CC.ContractError(f"{tn}/{inst}.{pin}: planned early core tap does not match selected TT mean; regenerate from means")
    if rows:
        (kd / "core_latency.json").write_text(json.dumps(dict(type=tn, edge="rise", target_ps=P.clock["insertion_ps"],
                                                              rows=rows), indent=1) + "\n")
        (kd / "core_latency.txt").write_text(
            ("# inst pin mean_pin_register_insertion_ps tap (TT; corner/source basis in JSON)\n" if mean_contract else
             "# inst pin ETM_MAX_BOUND_ps tap (legacy diagnostic, NOT a mean/SIGNED contract)\n") +
            "".join(f"{r['inst']} {r['pin']} {r['rise_ps']:g} {r['tap']}\n" for r in rows))
    if rows and mean_contract:
        (kd / "core_latency_ff.txt").write_text(
            "# inst pin mean_pin_register_insertion_ps tap (FF; corner/source basis in JSON)\n" +
            "".join(f"{r['inst']} {r['pin']} {r['corners']['ff']['mean_ps']:g} {r['tap']}\n" for r in rows))
    if taps:
        (kd / "core_taps.txt").write_text("# port inst pin|* early_ps insertion_ps   (GENERATED; CP2 early core taps)\n" +
                                          "".join(f"{n} {i} {p} {e:g} {ins:g}" +
                                                  (" exact" if any(p in tp.get("merged_clock_ports", []) and
                                                   (tp["name"] == i or tp["name"].startswith(i + ".")) for tp in P.types[tn].get("clock", {}).get("taps", [])) else "") + "\n"
                                                  for n, i, p, e, ins in taps))
    return dict(rows=rows, taps=taps)


def reg_spine_spec(P, tn):
    """DIE-HEAD-17 opt-in register spine of a type (partition_types.<t>.reg_spine, reg_spine.py spec) or None."""
    return P.types[tn].get("reg_spine") or None


def clock_phase_tcl(P, tn, before_cts=False):
    """Estimate only LOCAL clock trees while they are ideal; clear before CTS.

    Port-specific network latencies persist in OpenSTA propagated-clock timing,
    so they must not be placed in the golden SDC or survive into CTS. Dedicated
    early core taps already include their signed internal tree and are excluded.
    """
    ports = " ".join(n for n, _x, _y in clock_pins(P, tn))
    if before_cts:
        return ("# Clear only the pre-CTS LOCAL network estimate; preserve early core source latencies.\n"
                f"unset_clock_latency -clock clk [get_ports {{{ports}}}]\n"
                + ("# plan clock.tap_window: restore the golden per-tap window before the tree (propagated + CRPR)\n"
                   + tap_window_tcl(P, tn) if tap_window_ps(P, tn) else "") +
                "source /work/clock_taps.tcl\n"
                + ("source /work/clock_edge_split.tcl\n" if edge_split_ports(P, tn) else ""))
    return ("# Pre-CTS ideal LOCAL tree insertion, matching the virtual neighbour clock budget.\n"
            "# Stage-only: pre_cts.tcl removes it before tree construction. Golden SDC stays unchanged.\n"
            f"set_clock_latency -clock clk {t_lib(P.clock['insertion_ps']):.4f} [get_ports {{{ports}}}]\n"
            + ("# plan clock.tap_window: ideal clocks get no CRPR, so the window is zeroed until pre_cts.tcl\n"
               + tap_window_tcl(P, tn, value_ps=0.0) if tap_window_ps(P, tn) else ""))



def _corner_libs(mlib, kd, corner):
    """kit macro timing views of CORNER (tt/ff) for the gate/sign-off lib lists; FAIL when a macro lacks that view."""
    out = []
    for f in mlib:
        m = re.match(r"^(.*)_(tt|typ|ff|ss)(\.lib(?:\.gz)?)$", Path(f).name)
        if not m:
            raise ValueError(f"macro lib {f}: no corner suffix")
        name = f"{m[1]}_{corner}{m[3]}"
        if not (kd / "macros" / name).is_file():
            raise ValueError(f"macro lib {f}: no {corner} view {name} in the kit")
        out.append(str(Path(f).parent / name))
    return out


def grt_nonport_hold_chain(kd, tool_dir=None):
    """KW-FIX-45 11-11 (DIE-HBM-100, opt-in OT_GRT_NONPORT_HOLD=1 in the gen environment / item_env): chain tools/grt_nonport_hold.tcl
    (input-start hold exclusion during the FF GRT repair only) at the END of the kit's effective PRE_GLOBAL_ROUTE_TCL.
    Reads the written config.mk, takes the LAST PRE_GLOBAL_ROUTE_TCL assignment as the base, writes /work/grt_pre_nonport.tcl
    (source base; source /work/grt_nonport_hold.tcl) and appends the override plus OT_GRT_NONPORT_HOLD = 1.  Never called
    without the opt-in, so other kits are byte-identical.  -> the base path chained."""
    kd = Path(kd)
    cfgp = kd / "config.mk"
    base = None
    for ln in cfgp.read_text().splitlines():
        m = re.match(r"^(?:override\s+)?export\s+PRE_GLOBAL_ROUTE_TCL\s*:?=\s*(\S+)\s*$", ln)
        if m:
            base = m.group(1)
    if base is None:
        raise SystemExit("OT_GRT_NONPORT_HOLD=1: the kit config.mk sets no PRE_GLOBAL_ROUTE_TCL to chain")
    hook = Path(tool_dir or Path(__file__).resolve().parent.parent) / "grt_nonport_hold.tcl"
    shutil.copyfile(hook, kd / "grt_nonport_hold.tcl")
    (kd / "grt_pre_nonport.tcl").write_text("# GENERATED (OT_GRT_NONPORT_HOLD=1): the kit's PRE_GLOBAL_ROUTE_TCL, then the shared nonport hold adapter\n"
                                            f"source {base}\nsource /work/grt_nonport_hold.tcl\n")
    with cfgp.open("a") as f:
        f.write("override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_nonport.tcl\nexport OT_GRT_NONPORT_HOLD = 1\n")
    return base


def macro_ff_repair_stage(kd, macros, mlib):
    """Separate the requested FF repair stage from the original macro/CTS config."""
    import gzip
    ff = _corner_libs(mlib, kd, "ff")
    expected = {}
    for name in ff:
        path = kd / "macros" / Path(name).name
        text = gzip.open(path, "rt").read() if path.suffix == ".gz" else path.read_text()
        library = re.search(r'\blibrary\s*\(\s*"?([^\s")]+)', text)
        if not library:
            raise ValueError(f"FF repair: no Liberty library in {path}")
        for master in {m[1] for m in macros}:
            if re.search(r'\bcell\s*\(\s*"?' + re.escape(master) + r'"?\s*\)', text):
                if master in expected:
                    raise ValueError(f"FF repair: duplicate timing master {master}")
                expected[master] = f"{library[1]}/{master}"
    missing = {m[1] for m in macros} - expected.keys()
    if missing:
        raise ValueError(f"FF repair: missing actual FF macro cells {sorted(missing)}")
    (kd / "macro_ff_repair.mk").write_text(
        "include /work/config.mk\n"
        "export OT_MACRO_FF_BASE_PRE_GRT := $(PRE_GLOBAL_ROUTE_TCL)\n"
        "override export CORNER = BC\noverride export CORNERS = bc\n"
        "override export LIB_FILES = $(BC_LIB_FILES)\n"
        "override export ADDITIONAL_LIBS = $(filter /work/macros/%,$(BC_LIB_FILES))\n"
        "override export PRE_GLOBAL_ROUTE_TCL = /work/macro_ff_pre_grt.tcl\n"
        "override export OT_VCLK_CORNER = ff\n")
    guard = ['if {$::env(CORNER) ne "BC" || $::env(CORNERS) ne "bc"} {error "MACRO_FF wrong repair mode"}']
    for master, cell in sorted(expected.items()):
        guard += [f"set cells [get_lib_cells -quiet */{master}]",
                  f'if {{[llength $cells] != 1 || [get_full_name [lindex $cells 0]] ne "{cell}"}} {{error "MACRO_FF wrong or ambiguous cell {master}"}}']
    guard += ['puts "MACRO_FF actual FF master inventory PASS"',
              'source $::env(OT_MACRO_FF_BASE_PRE_GRT)']
    (kd / "macro_ff_pre_grt.tcl").write_text("\n".join(guard) + "\n")
    return expected

KEEP_REGS_HOOK = ("ot_keep_regs.tcl", "ot_pin_regs.tcl", "pin_reg_split.tcl", "ot_rst_copies.tcl", "ot_rst_copies.py")


_INCLUDE = re.compile(r'^[ \t]*`include[ \t]+"([^"]+)"', re.M)



def declared_rom_bits(rtl_dir):
    """Largest words*width of an OWNER D-ROM-2 declared-logic table (tools/mem_compiler/rom_declared_logic.json) whose
    module is defined in the kit RTL (0 if none); gen phys raises SYNTH_MEMORY_MAX_BITS to exactly that size."""
    decl = Path(__file__).resolve().parent.parent / "mem_compiler" / "rom_declared_logic.json"
    tables = json.loads(decl.read_text())["tables"]
    text = "\n".join(f.read_text(errors="replace") for f in sorted(Path(rtl_dir).glob("*.sv")))
    best = 0
    for t in tables:
        if re.search(r"^\s*module\s+" + re.escape(t["module"]) + r"\b", text, re.M):
            # DIE-KV-57 10-31: an entry may carry elab_width = the pre-opt $mem_v2 width the kit gen lint measures
            # (rtl_lint elaboration, before opt trims constant bits); the limit covers both widths
            best = max(best, int(t["words"]) * max(int(t["width"]), int(t.get("elab_width", 0))))
    return best

# DIE-KV-60/hubeo 11-01 (COORD 01:43 one-block item; class fix, default-on per OWNER 12.27 b): flop-array memories that
# are flip-flops BY DESIGN, never SRAM macros (the head is read straight from the array through per-bit-group pointer
# copies; a macro would add a read cycle and change the FIFO timing).  Value = words x width of the elaborated $mem_v2
# the kit gen lint measures; gen phys raises SYNTH_MEMORY_MAX_BITS to exactly the largest one the kit RTL defines (the
# same exact-size form as declared_rom_bits), so any other inferred memory above that size still fails.
DECLARED_FLOP_MEMORIES = {
    # KV hub_Wi control FIFOs: exact audited production shapes. Inferred mux/
    # read-pointer-copy heads are part of their cycle contract; no SRAM latency
    # is introduced. Wider future elaborations still fail the measured limit.
    "qkd_host_rx_class_admission": 16 * 514,       # iq[16], IR_REPL grouped heads
    "qkd_host_qm_ingress16_service_debt": 16 * 514, # q[16], RP_REPL paired 8:1 heads
    "ot_link_afifo": 16 * 514,                    # mem[16], asynchronous/RCOPY head
    "ot_fdi_join2": 16 * 522,                     # qa 522b / qb 521b, 16 entries
    # KV kv3_hub_Eo / kv3_hub_Wo qkd_seq_xs_s u_q: 40 x 128 Q store FIFO (rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv)
    "ot_qkvd_seq_m_sfifo": 40 * 128,
    # S81 T7 svc_lo_dsdv_svc_rs__t7 u_att.sw (TOK-DS-3 11-02): 32 x 512 score-window FIFO, bound native glue of
    # dsdv_svc_att.sv sw[]; the head row is read asynchronously at sw_r into the same-cycle consumer (bound 191_Y), so a
    # synchronous macro would add a read cycle.  Content-hashed glue name: a re-bind with other content no longer matches.
    "ot_bind_native_bfac540d36e9ad5c410d0d97": 32 * 512,
    # KV kv3_hub_C qkd_pv_fin_s sbuf (KV-PLAN-2 11-09, hub_C a7 gen_lint): 32 x 512 per-command sum store
    # (rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv).  Written at SUM_AGE + b, read ASYNCHRONOUSLY at MUL_AGE + b
    # (saved_sum = sbuf[rptr]) straight into the multipliers, and MUL_AGE = SUM_AGE + 1 on the R <= LASTP timeline, so
    # a synchronous macro would add a read cycle to the static calendar.  Flip-flops by design.
    "qkd_pv_fin_s": 32 * 512,
}


def declared_flop_mem_bits(rtl_dir):
    """Largest DECLARED_FLOP_MEMORIES size whose module is defined in the kit RTL (0 if none)."""
    text = "\n".join(f.read_text(errors="replace") for f in sorted(Path(rtl_dir).glob("*.sv")))
    return max((b for m, b in DECLARED_FLOP_MEMORIES.items()
                if re.search(r"^\s*module\s+" + re.escape(m) + r"\b", text, re.M)), default=0)


_LANDING_MOD = re.compile(r"^\s*module\s+ot_dp_clk_landing\b", re.M)


def defines_landing_ring(rtl_dir):
    """DIE-S81-26 10-29 (COORD 10:41 ruling (a) + follow-up): True when the kit RTL defines ot_dp_clk_landing.  gen phys
    then exports OT_LANDING_FF=1: physical/common_flow/ot_keep_regs.tcl maps ONLY the landing modules' ring memories to
    flip-flops before synth's memory check (S81 stations: 4 x 1105-bit rings > the 4096 SYNTH_MEMORY_MAX_BITS default).
    SYNTH_MEMORY_MAX_BITS is not raised, so any other memory above it in the same kit still FAILs."""
    return any(_LANDING_MOD.search(f.read_text(errors="replace")) for f in sorted(Path(rtl_dir).glob("*.sv")))


# DIE-HEAD-85/HSPLIT 11-07 (generator class fix, LEC): RTL state registers that yosys `fsm` re-encodes so the kit LEC
# cannot pair them.  The s81 link gearbox RX hunt FSM (ot_s81ph_link_gbx* reg hunt[1:0], states 0/1/2) became gate
# u_gb.hunt[0..2] one-hot (hunt[0] reset 1) in the HSPLIT kits hd_host_e/hd_host_w; lec.py refused the gold state
# constraint ("allowed states do not cover the native ternary reset-base cube") and the f_rx_v cone stayed 78
# differs (kitsF hd_host_e lec.json).  The S81 coll_e recipe of this same gearbox already pins OT_FSM_NONE_WIRES=hunt.
# gen phys now exports it for every kit whose RTL defines such a module (ot_keep_regs.tcl: fsm_encoding "none" on
# those wires; function unchanged, LEC pairs the RTL bits by name).  The per-item env opt-in still adds names.
# QC-TYPES-11 11-08 (same class, QC glue a6 pre-route LEC NOT EQUIVALENT): yosys fsm re-encoded u_rec.st (3 -> 4 bits,
# ot_qwen_d2d_recovery) and u_ot_pr_core.st (3 -> 5 bits, qfd_sys_face_lctx3_core); every listed differing cone had gold_only st.
_FSM_NONE_BY_MODULE = ((re.compile(r"^\s*module\s+ot_s81ph_link_gbx\w*\b", re.M), ("hunt",)),
                       (re.compile(r"^\s*module\s+(?:ot_qwen_d2d_recovery|qfd_sys_face_lctx3_core)\b", re.M), ("st",)),)


def fsm_none_wires(rtl_dir, extra=None):
    """Wire base names for OT_FSM_NONE_WIRES: the _FSM_NONE_BY_MODULE wires of every module the kit RTL defines,
    then the per-item env names (commas or spaces), de-duplicated in order."""
    names = []
    texts = [f.read_text(errors="replace") for f in sorted(Path(rtl_dir).glob("*.sv"))]
    for rx, wires in _FSM_NONE_BY_MODULE:
        if any(rx.search(t) for t in texts):
            names.extend(wires)
    names.extend((extra or "").replace(",", " ").split())
    return list(dict.fromkeys(names))


_LANDING_BODY = re.compile(r"^\s*module\s+ot_dp_clk_landing\b(.*?)^\s*endmodule\b", re.M | re.S)
_RING_DEPTH = re.compile(r"\bot_meso_ring\s*#\s*\([^;]*?\.DEPTH\s*\(\s*(\d+)\s*\)", re.S)
_PLAIN_RING = re.compile(r"\bot_dp_clk_landing\s*#\s*\((?:[^()]|\([^()]*\))*\)\s*(u_cland_\w+)\s*\((.*?)\)\s*;", re.S)
_RING_D = re.compile(r"\.d\s*\(\s*(\{[^{}]*\}|[A-Za-z_]\w*)\s*\)")


def export_land_slots(t, land_slots):
    """AUTOBUILD-PIPE-1 (GEOM-84 t23, COORD 10-30 23:1x): a type that declares a forwarded-clock EXPORT
    (clock.landing_contract pin dir out, kind clock) but no landing ring still gets a kit land_slots.json (no buses):
    AUTO-GEOM (geom_check.sh -> geom_rules.land_ring_captures) takes face_guard's proved clock_exports only through
    that file, else the declared export (fclk_out_cland_up) reads as an unregistered pin.  No buses = no ring
    exemption; face_guard / signoff treat an empty bus map exactly as no file.  Other kits: unchanged."""
    if land_slots is not None:
        return land_slots
    lc = ((t.get("clock") or {}).get("landing_contract") or {})
    if any(isinstance(x, dict) and x.get("dir") == "out" and x.get("kind") == "clock" for x in lc.get("pins") or []):
        from clock_landings import LAND_SLOTS_SCHEMA
        return {"schema": LAND_SLOTS_SCHEMA, "buses": {}}
    return None


def plain_ring_land_slots(rtl_dir, buses):
    """DIE-S81-26 10-29 (COORD 10:41 ruling (b), face_guard config, not a new check): the PLAIN forwarded-clock landing
    rings of a --kit-rtl type (S81 stations: ot_dp_clk_landing u_cland_<bus> from clock.landing_contract, not the
    count-aligned Landings sidecar of DIE-KV-31 810219984cd).  Every ring whose .d is whole planned face buses (one
    identifier or a {..} concat of identifiers, each in `buses`) declares those buses {D: ring DEPTH, form: hold_mux}
    -- face_guard then proves per bit the D enable-mux slot flops (own-Q hold, exclusive write conditions) exactly as
    for count-aligned rings.  A ring with any other .d expression, or a kit without the ot_dp_clk_landing module /
    a literal ring DEPTH, declares nothing (its bits stay undeclared, so a 1-to-D fan still FAILs).  {} if none."""
    import gen_rtl
    text = "\n".join(f.read_text(errors="replace") for f in sorted(Path(rtl_dir).glob("*.sv")))
    body = _LANDING_BODY.search(text)
    dm = _RING_DEPTH.search(body.group(1)) if body else None
    if not dm:
        return {}
    depth, out = int(dm.group(1)), {}
    for m in _PLAIN_RING.finditer(text):
        # An explicit FREG captures the bus in one ordinary face register;
        # the four-slot ring is internal and grants no pin-guard exemption.
        params = m.group(0).split(m.group(1), 1)[0]
        fm = re.search(r"\.FREG\s*\(\s*([^()]+)\s*\)", params)
        if fm:
            value = fm.group(1).strip()
            if value not in ("0", "1", "1'b0", "1'b1", "1'd0", "1'd1"):
                raise gen_rtl.GenError(f"{m.group(1)}: plain landing FREG needs literal 0/1")
            if value in ("1", "1'b1", "1'd1"):
                continue
        d = _RING_D.search(m.group(2))
        if not d:
            continue
        names = [x.strip() for x in d.group(1).strip("{}").split(",")]
        if names and all(re.fullmatch(r"[A-Za-z_]\w*", x) and x in buses for x in names):
            for x in names:
                out[x] = {"D": depth, "form": "hold_mux"}
    return out


def stage_includes(rtl_files, rtl_dir):
    """DIE-HEAD-7 / RISK-SWEEP-2 10-28: copy every `include "x" a staged source names (transitively) from the source's
    own directory into the kit rtl/ (yosys resolves includes next to the including file); the HEAD hd_serdes kit
    dropped s81_link/ot_s81_gf1024.svh + kp4 *_mat.svh.  A missing include stays missing: KIT_PREFLIGHT fails it."""
    todo, done = [Path(f) for f in rtl_files], set()
    while todo:
        f = todo.pop()
        if f in done or not f.is_file():
            continue
        done.add(f)
        for inc in _INCLUDE.findall(f.read_text(errors="replace")):
            src = f.parent / inc
            dst = Path(rtl_dir) / Path(inc).name
            if src.is_file():
                if not dst.exists():
                    shutil.copyfile(src, dst)
                todo.append(src)


def kit_core_area(t):
    """Exact type outline with optional [W,S,E,N] row/site-aligned core insets.

    Die-edge PHYs may consume the full outline width; the per-type opt-in changes
    placement rows only, without shifting the outline, macro origins or plan pins.
    """
    w,h=t["outline_um"]
    margins=t.get("kit_core_margins_um",[CORE_MARGIN_UM]*4)
    if not isinstance(margins,(list,tuple)) or len(margins)!=4:
        raise ValueError("kit_core_margins_um must be [W,S,E,N]")
    for v,step in zip(margins,(0.054,0.27,0.054,0.27)):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
            raise ValueError("kit_core_margins_um entries must be finite nonnegative numbers")
        if abs(v/step-round(v/step))>1e-6:
            raise ValueError("kit_core_margins_um must align W/E to 0.054 um and S/N to 0.27 um")
    west,south,east,north=margins
    if west+east>=w or south+north>=h:
        raise ValueError("kit_core_margins_um leaves no placement core")
    return [west,south,w-east,h-north]



def write_lec_options(kd, typ):
    """Persist only an explicit per-type proof opt-in; proof receipts still gate it."""
    options = typ.get("lec", {})
    if not isinstance(options, dict) or set(options) - {"superset_vec"} or any(type(v) is not bool for v in options.values()):
        raise ValueError("type lec accepts only boolean superset_vec")
    path = Path(kd) / "lec_options.json"
    if options.get("superset_vec", False):
        path.write_text(json.dumps(dict(superset_vec=True), sort_keys=True) + "\n")
    elif path.exists():
        path.unlink()  # regeneration with the opt-in removed must not retain it



_MODULE_HDR = r"(?<![\w$])module\s+{}\b"


def _module_header(text, mod):
    """'module M #(...)(...);' of mod in text (comments stripped), or None."""
    text = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", text)
    m = re.search(_MODULE_HDR.format(re.escape(mod)), text)
    if not m:
        return None
    i, depth = m.end(), 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == ";" and depth == 0:
            return text[m.start():i + 1]
        i += 1
    return None


def _header_localparams(text, mod, hdr):
    """DIE-HBM-92-GEN 11-08 (HBM q_b002 GEN_LINT "Identifier NKT is implicitly declared" in ot_hbm_idx_tail_native_bb.v):
    the module-scope `localparam ...;` statements of mod's body (text = its source) that the header's port list uses
    (NKT/NCH of ot_hbm_idx_tail_native are body localparams sized into its ports), with the localparams they depend on,
    in source order.  '' when the header uses none (the blackbox stays byte-identical)."""
    text = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", text)
    i = text.find(hdr)
    if i < 0:
        return ""
    end = re.search(r"\bendmodule\b", text[i + len(hdr):])
    body = text[i + len(hdr):i + len(hdr) + (end.start() if end else 0)]
    decls = []
    for m in re.finditer(r"\blocalparam\b([^;]*);", body):
        rest = re.sub(r"^\s*(?:(?:integer|int|logic|bit|signed|unsigned|real)\b\s*|\[[^\]]*\]\s*)*", "", m.group(1))
        names = {it.split("=", 1)[0].strip() for it in _top_items(rest) if "=" in it}
        decls.append((m.group(0), names, set(re.findall(r"[A-Za-z_]\w*", m.group(1)))))
    hm = re.match(r"\s*module\s+[A-Za-z_]\w*\s*(#\s*\()?", hdr)
    ports = hdr
    params = set()
    if hm and hm.group(1):
        j = _paren_end(hdr, hm.end() - 1)
        params = {it.split("=", 1)[0].split()[-1] for it in _top_items(hdr[hm.end():j]) if "=" in it and it.split("=", 1)[0].split()}
        ports = hdr[j + 1:]
    need = set(re.findall(r"[A-Za-z_]\w*", ports)) - params
    take, grew = set(), True
    while grew:
        grew = False
        for k, (_, names, refs) in enumerate(decls):
            if k not in take and names & need:
                take.add(k)
                need |= refs - params
                grew = True
    return "".join(f"    {decls[k][0].strip()}\n" for k in sorted(take))


def _paren_end(text, i):
    """index of the ')' closing the '(' at text[i]"""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _top_items(text):
    out, depth, cur = [], 0, ""
    for ch in text:
        depth += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


_INT_LIT = re.compile(r"[+-]?\d[\d_]*|(?:\d+\s*)?'s?[bodh]\s*[0-9a-fA-F_]+")


def _macro_instance_overrides(text, mod):
    """{param: [override text, one per named override]} of every `mod #(...)` instance in text.  Positional -> {}."""
    text = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", text)
    seen, n = {}, 0
    for m in re.finditer(r"(?<![\w$.])" + re.escape(mod) + r"\s*#\s*\(", text):
        if re.search(r"(?<![\w$])module\s+$", text[max(0, m.start() - 64):m.start()]):
            continue                                   # the definition's own parameter list, not an instance
        i = m.end() - 1
        j = _paren_end(text, i)
        if j < 0:
            return {}
        n += 1
        for it in _top_items(text[i + 1:j]):
            a = re.fullmatch(r"\s*\.\s*([A-Za-z_]\w*)\s*\((.*)\)\s*", it, re.S)
            if not a:
                return {}
            seen.setdefault(a.group(1), []).append(a.group(2).strip())
    return seen


def macro_instance_identity(text, mod):
    """{param: value} of the numeric-literal overrides that EVERY `mod #(...)` instance in text gives the same value
    (the configuration the macro's single signed view was built with).  Positional overrides -> {}."""
    seen = _macro_instance_overrides(text, mod)
    # a non-literal override (.QX(QX) inside another macro's RTL, a parent parameter) says nothing about the identity:
    # OT_SIGNED_PARAM_SERIALIZE still checks its elaborated value at synth.  Literals must all agree.
    out = {}
    for k, v in seen.items():
        lit = {x for x in v if _INT_LIT.fullmatch(x)}
        if len(lit) == 1:
            out[k] = lit.pop()
    return out


def macro_spec_identity(root, mod, text, settled):
    """{param: value} from the core's own legacy kit spec, for parameters the staged instances override without settling a
    literal (.SRAM_MACRO(TX_SRAM) on dsdv_idx_tx_n32, FORM-IDX 11-05): that spec is what the one signed view was built with,
    and the instance text cannot say.  native_bb still compares the ELABORATED override with this default at synth, so a
    parent that really differs from the view still stops; nothing here is taken on trust.  No spec: {} (as before)."""
    if not root:
        return {}
    out = {}
    for spec in sorted(Path(root).glob(f"physical/die_plan/*/cores/legacy/specs/{mod}/spec.json")):
        try:
            params = json.loads(spec.read_text()).get("params") or {}
        except (OSError, ValueError):
            continue
        for k in _macro_instance_overrides(text, mod):
            if k not in settled and isinstance(params.get(k), int):
                out[k] = str(int(params[k]))
    return out


def _header_with_defaults(hdr, ident):
    """hdr ('module M #(...)(...);') with the parameter defaults of `ident` (only parameters it declares)."""
    m = re.match(r"(\s*module\s+[A-Za-z_]\w*\s*#\s*)\(", hdr)
    if not m or not ident:
        return hdr, {}
    i = m.end() - 1
    j = _paren_end(hdr, i)
    items, done = [], {}
    for it in _top_items(hdr[i + 1:j]):
        # a `ifdef-selected declaration stays as written; a bare macro default (`X_DEF) takes the identity: the bb reads alone,
        # so the macro is undefined there and native_bb cannot verify it (DIE-S81-56 11-04, S81 xrt1/xrt3).
        # So does a macro-with-fallback default (`ifdef M `M `else 0 `endif, QC qfd_dv_s5_sc2_leaf HARD_PINREG): the bb reads
        # alone, M is undefined there, native_bb reads the fallback (DIE-QC-74 11-05, 9 SC types).
        if "=" in it and ("`" not in it or re.fullmatch(r"\s*`\w+\s*", it.split("=", 1)[1])
                          or re.fullmatch(r"\s*`ifdef\s+(\w+)\s+`\1\s+`else\s+[^`]*`endif\s*", it.split("=", 1)[1])):
            lhs, rhs = it.split("=", 1)
            names = re.findall(r"[A-Za-z_]\w*", lhs)
            if names and names[-1] in ident and names[-1] not in done:
                done[names[-1]] = ident[names[-1]]
                it = f"{lhs}= {ident[names[-1]]}" + ("\n" if rhs.endswith("\n") else "")
        items.append(it)
    return hdr[:i + 1] + ",".join(items) + hdr[j:], done


def strip_module_definition(text, mod):
    """text without the `module mod ... endmodule` definition(s) (comments and strings respected); (new, n)."""
    spans, i, n = [], 0, len(text)
    while i < n:                                   # comment / string spans
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + 1)
        else:
            i += 1
            continue
        spans.append((i, j))
        i = j
    inside = lambda k: any(a <= k < b for a, b in spans)
    out, pos, cnt = [], 0, 0
    for m in re.finditer(_MODULE_HDR.format(re.escape(mod)), text):
        if m.start() < pos or inside(m.start()):
            continue
        e = next((x for x in re.finditer(r"(?<![\w$])endmodule\b", text[m.end():]) if not inside(m.end() + x.start())),
                 None)
        if e is None:
            raise ValueError(f"module {mod}: no endmodule")
        end = m.end() + e.end()
        body = text[m.start():end]
        if len(re.findall(r"`if(?:n?def)\b", body)) != len(re.findall(r"`endif\b", body)):
            raise ValueError(f"module {mod}: definition straddles a preprocessor conditional; cannot strip it")
        out += [text[pos:m.start()], f"/* {mod}: hard macro, header-only view in {mod}_bb.v (gen_phys) */"]
        pos = end
        cnt += 1
    out.append(text[pos:])
    return "".join(out), cnt


def macro_param_blackboxes(macros, rtl_files, rtl_dir, root=None, physical_ft=(), plan_dir=None):
    """Write rtl_dir/<module>_bb.v for every macro module that the staged RTL instantiates with a parameter override
    and that has no _bb view yet; header copied from the module's own RTL (exact staged files, their dirs, then
    <root>/rtl).  Returns the new files.  Macros without overrides are untouched (byte-identical kits)."""
    rtl_dir = Path(rtl_dir)
    staged = "\n".join(Path(f).read_text(errors="replace") for f in rtl_files
                       if Path(f).suffix in (".sv", ".v") and Path(f).is_file())
    declared_ft = {}
    if any(c.get("physical_ft") for c in physical_ft):
        import core_ft_physical as CF
        declared_ft = CF.contracts(physical_ft, macros, staged, root, plan_dir)
        CF.retain(declared_ft, rtl_dir.parent / "ft_physical")
    have = {Path(f).name for f in rtl_files}
    out = []
    for mod in sorted({m[1] for m in macros}):
        if f"{mod}_bb.v" in have or f"{mod}_bb.sv" in have:
            if mod in declared_ft:
                raise ValueError(f"macro {mod}: explicit FT header conflicts with existing blackbox")
            continue
        if mod not in declared_ft and not re.search(r"(?<![\w$])" + re.escape(mod) + r"\s*#\s*\(", staged):
            continue
        dirs = list(dict.fromkeys(Path(f).parent for f in rtl_files))
        # Multi-module HDL sources need not be named after this physical master
        # (S81 ot_s81sl_ve.sv declares both ot_s81sl_ve_m and ot_s81sl_ve_s).
        # Prefer the exact ordered readset before the established basename fallback.
        cands = list(dict.fromkeys(Path(f) for f in rtl_files
                                   if Path(f).suffix in (".sv", ".v") and Path(f).is_file()))
        cands += [d / n for d in dirs for n in (f"{mod}.sv", f"{mod}.v")]
        if root:
            cands += sorted((Path(root) / "rtl").rglob(f"{mod}.sv")) + sorted((Path(root) / "rtl").rglob(f"{mod}.v"))
        hit = next(((h, c) for h, c in ((_module_header(c.read_text(errors="replace"), mod), c) for c in cands
                                        if c.is_file()) if h), None)
        hdr = hit[0] if hit else None
        if hdr is None:
            raise ValueError(f"macro {mod} is instantiated with parameters but no RTL header was found for its "
                             f"blackbox (searched {len(cands)} files)")
        # DIE-S81-47 11-01 (S81 col class, cfg7_seq_bfp #(.PINREG(1), .LAYOUT(1))): the header defaults are the
        # signed identity that OT_SIGNED_PARAM_SERIALIZE (native_bb, STA-0171) checks before it strips the overrides.
        # The RTL defaults (PINREG 0) are not the configuration the one signed view was built with; every staged
        # instance giving the same numeric literal is.  Parameters the instances disagree on keep the RTL default
        # (a non-default override still stops synth there, as before).
        logical_header = hdr
        lit = macro_instance_identity(staged, mod)
        spec_id = macro_spec_identity(root, mod, staged, lit)
        # byte-identical kits: a spec value equal to the RTL default is no change (.V(V) = 276, .MUT(X) = 0)
        spec_id = {k: v for k, v in spec_id.items()
                   if not re.search(r"(?<![\w$])" + re.escape(k) + r"\s*=\s*" + re.escape(v) + r"\s*(?:,|\)|//|\n)", hdr)}
        hdr, ident = _header_with_defaults(hdr, {**lit, **spec_id})
        if mod in declared_ft:
            hdr = CF.extend_header(hdr, declared_ft[mod], logical_header)
        from_inst = {k: v for k, v in ident.items() if k not in spec_id}
        note = ("// signed identity from the staged instances: " + ", ".join(f"{k}={v}" for k, v in sorted(from_inst.items()))
                + "\n") if from_inst else ""
        if spec_id:
            note += "// signed identity from the core's kit spec: " + ", ".join(f"{k}={v}" for k, v in sorted(spec_id.items())) + "\n"
        dst = rtl_dir / f"{mod}_bb.v"
        # body localparams the port list sizes with (NKT/NCH); '' for every header that is self-contained (unchanged bb)
        lps = _header_localparams(hit[1].read_text(errors="replace"), mod, logical_header)
        dst.write_text(f"// GENERATED by gen_phys.macro_param_blackboxes: header-only view of hard macro {mod}\n"
                       f"{note}(* blackbox *)\n{hdr}\n{lps}endmodule\n")
        out.append(dst)
        # DIE-S81-47 11-01: one definition per module.  The ORFS / lint frontends read the header -lib -overwrite next
        # to a deferred RTL body, but LEC reads every VERILOG_FILES entry as its own read_verilog -defer (and slang
        # reads them as one compilation): header + body = 'Re-definition of module'.  The staged kit copy of the
        # module's RTL drops the body (the Liberty view replaced it in synthesis anyway); other modules stay.
        for f in rtl_files:
            cp = rtl_dir / Path(f).name
            if Path(f).suffix in (".sv", ".v") and cp.is_file() and cp.name != dst.name:
                txt, k = strip_module_definition(cp.read_text(errors="replace"), mod)
                if k:
                    cp.write_text(txt)
    return out


# S81-TYPES-2/3 11-07: kit-local hard core moves, opt-in per row through wave item_env, default off (byte-identical kits).
# OT_MACRO_MOVES = inst:x:y[:orient],... in the type frame; orient given = mirror the core and take the track offset of
# that orient.  Only macro_place.tcl changes, as in the TYPE-CONS-5 t27/t42 pilots: the plan, pins, clock and core taps
# stay at their plan sites, so the die sees the same type.  A tap under a moved core stays there; the pilots route it.
_CORE_TRACK_OFFSET = {"R0": (0.108, 0.012), "MY": (0.132, 0.012), "MX": (0.108, 0.036), "R180": (0.132, 0.036)}


def macro_move_table(t, tn, env=None):
    """-> {placed inst: {inst, from, to, orient, x, y}}, x/y = origin + track offset; {} when OT_MACRO_MOVES is unset."""
    raw = (os.environ if env is None else env).get("OT_MACRO_MOVES", "")
    out = {}
    if not raw:
        return out
    cores = {c.get("inst"): c for c in t.get("hard_cores", []) or []}
    w, h = t["outline_um"]
    # Overlap is judged on the placed boxes (origin + the plan's per-core track offset, as place_macro gets them): a plan
    # can abut two cores through their offsets (S81 bf_col3 u_c / bf16 u_ha: origins 0.888 um inside, placed edges equal).
    pos = {n: [c["origin_um"][0] + c.get("track_offset_um", [0.0, 0.0])[0],
               c["origin_um"][1] + c.get("track_offset_um", [0.0, 0.0])[1]] for n, c in cores.items()}
    # DIE-S81-85 11-09 MOVES-SPLIT: a row written against a core that a later plan event split (ROMQ-GB: u_e1 ->
    # u_e1.u_w + u_e1.u_e) names no hard core any more.  An entry naming the split parent moves its children as one
    # rigid group: delta = (x, y) - group origin (min child origin), each child keeps its plan orient and its plan
    # track offset, so the halves stay abutted as the plan placed them.  An orient on a group entry is refused (a
    # mirror would swap the halves).  A moved core keeping its plan orient keeps the plan's track_offset_um; the
    # orient table applies only on a re-orient (same value for every core whose plan offset is the table's).
    def _move(inst, x, y, orient):
        c = cores[inst]
        cw, ch = c["outline_um"]
        if x < 0 or y < 0 or x + cw > w or y + ch > h:
            raise ValueError(f"type {tn}: OT_MACRO_MOVES {inst} at {x},{y} leaves the outline")
        if orient not in _CORE_TRACK_OFFSET:
            raise ValueError(f"type {tn}: OT_MACRO_MOVES {inst} orient {orient!r}")
        ox, oy = (c.get("track_offset_um") or _CORE_TRACK_OFFSET[orient]) if orient == c.get("orient", "R0") \
            else _CORE_TRACK_OFFSET[orient]
        pos[inst] = [x + ox, y + oy]
        out[c.get("physical_inst", inst)] = {"inst": inst, "from": list(c["origin_um"]), "to": [x, y], "orient": orient,
                                             "x": x + ox, "y": y + oy}

    for e in raw.split(","):
        f = e.split(":")
        kids = sorted(n for n in cores if n.startswith(f[0] + ".")) if f[0] not in cores else []
        if len(f) not in (3, 4) or (f[0] not in cores and not kids):
            raise ValueError(f"type {tn}: OT_MACRO_MOVES entry {e!r}: not inst:x:y[:orient] of a hard core")
        x, y = float(f[1]), float(f[2])
        if kids:
            if len(f) == 4:
                raise ValueError(f"type {tn}: OT_MACRO_MOVES {f[0]} is a split core group ({', '.join(kids)}); "
                                 f"no orient on a group move")
            gx = min(cores[k]["origin_um"][0] for k in kids)
            gy = min(cores[k]["origin_um"][1] for k in kids)
            for k in kids:
                _move(k, round(x + cores[k]["origin_um"][0] - gx, 6), round(y + cores[k]["origin_um"][1] - gy, 6),
                      cores[k].get("orient", "R0"))
            continue
        _move(f[0], x, y, f[3] if len(f) == 4 else cores[f[0]].get("orient", "R0"))
    names = sorted(cores)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ax, ay = pos[a]; aw, ah = cores[a]["outline_um"]
            bx, by = pos[b]; bw, bh = cores[b]["outline_um"]
            if ax < bx + bw - 1e-6 and bx < ax + aw - 1e-6 and ay < by + bh - 1e-6 and by < ay + ah - 1e-6:
                raise ValueError(f"type {tn}: OT_MACRO_MOVES overlap {a} / {b}")
    return out


def txl_mid_exports(cfg, kd, env=None):
    """KW-FIX-43 11-10 (DIE-S81-85 serdes TXL4, COORD): opt-in at generation (OT_TXL_MID=1; OT_TXL_MID_CHAINS = instance
    chains, spaces or commas, default u_txl in the hook): copy txl_mid.tcl into the kit and run it as POST_GLOBAL_PLACE_TCL
    (each relay row and its hop buffers / inverters placed evenly from source to sink; placement only, no netlist change).
    Unset = no lines, the kit is byte-identical."""
    env = os.environ if env is None else env
    if env.get("OT_TXL_MID") != "1":
        return []
    assert not any(c.startswith("export POST_GLOBAL_PLACE_TCL") for c in cfg), "OT_TXL_MID: POST_GLOBAL_PLACE_TCL in use"
    chains = " ".join(env.get("OT_TXL_MID_CHAINS", "").replace(",", " ").split())
    shutil.copyfile(Path(__file__).with_name("txl_mid.tcl"), Path(kd) / "txl_mid.tcl")
    return ["# DIE-S81-85 serdes TXL4: per-hop spacing of the relay rows (txl_mid.tcl)", "export OT_TXL_MID = 1",
            *([f"export OT_TXL_MID_CHAINS = {chains}"] if chains else []), "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl"]


def write_type_kit(P, tn, out, rtl_files, util=0.5, proof=False, root=None, hold_ff_margin=None, margins=None,
                   skip_ir=False, max_wire_um=None, rc_cal=True, master_slice=None, trial=False,
                   bump_ports=None, gpl_plain=False, land_slots=None, plain_rings=False, kit_defines=None,
                   cland_pinslot=(), spare_out=(), private_clock_mesh=None, region_guide=None, dpl_diamond=False,
                   dead_inputs=None, native_cell_cap=None):
    """land_slots (opt-in, DIE-HEAD-21): face_guard declaration {"schema", "buses": {bus: {D, form}}} written as
    kit land_slots.json beside pins.json (clock_landings.Landings.land_slots); None: no file (byte-identical kits)."""
    t = P.types[tn]
    macro_moves = macro_move_table(t, tn)
    if gpl_plain and not t.get("ft_slots"):
        raise ValueError(f"type {tn}: --gpl-plain is for pure-FT corridor kits; the type has no ft_slots")
    import core_clock_groups as CG
    grouped = CG.network_manifest(P, tn)  # reject incomplete endpoint/network data before writing a kit
    ib = insertion_binding(P, tn)
    w, h = t["outline_um"]
    macros = type_macros(P, tn)
    macros, pinband = pinband_macros(P, tn, macros, root, check_only=bool(bump_ports))
    # A physical abstract alone leaves macro paths untimed and prevents load-driven
    # buffering (S81 frame review, 2026-10-24). Reject before writing a partial kit.
    missing_libs = [f"{inst} ({mod})" for inst, mod, lef, lib, x, y, o in macros if not lib]
    if missing_libs:
        raise ValueError(f"type {tn}: macros have LEF but no timing liberty: " + ", ".join(missing_libs))
    ss_libs = [f"{inst} ({lib})" for inst, mod, lef, lib, x, y, o in macros
               if re.search(r"_ss\.lib(?:\.gz)?$", str(lib), re.I)]
    if ss_libs:
        raise ValueError(f"type {tn}: implementation requires TT macro liberty, not SS: " + ", ".join(ss_libs))
    kd = Path(out) / tn
    (kd / "rtl").mkdir(parents=True, exist_ok=True)
    if pinband is not None:
        import pinband_site as _PBS
        _PBS.write_report(kd, pinband)
    write_lec_options(kd, t)
    import reset_tree as RT
    native_reset = RT.bound_native_contract(P, tn)
    if native_reset:
        (kd / "bound_native_reset.json").write_text(json.dumps(native_reset, indent=2) + "\n")
        if native_reset.get("source_authority"):
            import bound_reset_contract as BRC
            BRC.stage(kd / "rtl", native_reset["source_authority"], native_reset)
    mlef, mlib, mplace = [], [], ["# GENERATED by tools/die_plan/gen.py phys: content macros at their plan sites."]
    if macros:
        (kd / "macros").mkdir(exist_ok=True)
        base = Path(root) if root else Path(__file__).resolve().parent.parent.parent
        placed = []                                  # KW-FIX-44 11-10: placements, snapped to the track grid below
        for inst, mod, lef, lib, x, y, o in macros:
            lef_file = None
            for src, lst in ((lef, mlef), (lib, mlib)):
                if src:
                    # an absolute view path (pair.py --core-views) stays as is; a path the source checkout does not
                    # carry (sparse / pruned) resolves from its git store (cores.resolve, DIE-KV-60/adp 11-01)
                    f = _CR.resolve(src, base)
                    if not f.is_file():
                        raise FileNotFoundError(f"type {tn}: macro {inst} view {f} missing")
                    if lst is mlef:
                        lef_file = f
                    if f"/work/macros/{f.name}" not in lst:
                        shutil.copyfile(f, kd / "macros" / f.name)
                        lst.append(f"/work/macros/{f.name}")
                    if lst is mlib:
                        # Keep per-corner timing views beside the declared TT view.
                        # signoff.py selects TT/FF by filename; ORFS still uses only
                        # the declared typical library during implementation.
                        match = re.match(r"^(.*)_(tt|typ|ff|ss)(\.lib(?:\.gz)?)$", f.name)
                        if match:
                            for corner in ("tt", "typ", "ff"):
                                sibling = f.with_name(f"{match[1]}_{corner}{match[3]}")
                                if sibling.is_file() and sibling != f:
                                    shutil.copyfile(sibling, kd / "macros" / sibling.name)
            # ODB keeps an escaped Verilog name's array brackets as \[ \] (a plan inst like g_writer[0].u_mem is not found
            # otherwise: native59 MPL-0020, PATH-QC-A0N59 10-25); escape the bare ones
            inst_db = re.sub(r"(?<!\\)([\[\]])", r"\\\1", inst)
            if inst in macro_moves:
                x, y, o = macro_moves[inst]["x"], macro_moves[inst]["y"], macro_moves[inst]["orient"]
            placed.append({"inst": inst, "inst_db": inst_db, "master": mod, "lef": lef_file, "x": x, "y": y, "o": o})
        # KW-FIX-44 11-10 (COORD, DIE-S81-85 bksel vC2 P at y 201.96: half an M4 pitch off, 1000 DRT-0418 + DRT-0073):
        # a macro whose signal pins miss the kit's routing tracks moves to the nearest on-track origin (row / site grid
        # kept, 2.16 preferred, inside the outline, no overlap); on-grid macros and kits are unchanged
        # (macro_grid_snap.py; OT_MACRO_GRID_SNAP=0 off; receipt macro_grid_snap.json)
        import macro_grid_snap as _MGS
        placed, snap_rows = _MGS.snap_all(placed, (w, h), _MGS.tracks_for(make_tracks_tcl(P)))
        _MGS.write_receipt(kd, snap_rows)
        for r in snap_rows:
            print(f"OT_MACRO_GRID_SNAP type {tn}: {r['inst']} ({r['master']} {r['orient']}) {r['off_track_pins']} pin(s) "
                  f"off track at {r['plan_um']} -> " + (str(r['snapped_um']) if 'snapped_um' in r else
                                                        "UNRESOLVED: " + r['unresolved']))
        for q in placed:
            mplace.append(f"place_macro -macro_name {{{q['inst_db']}}} -location {{{q['x']:.4f} {q['y']:.4f}}} "
                          f"-orientation {q['o']} -exact")
        # KW6-CODE 11-04: advisory LEF/lib compare; a view with no LEF of its own gets its staged copy pruned to the lib's
        # ports.  Clean masters stay byte-identical.  bump kits keep the plain copy (bump pins are on the macro LEF).
        import view_lef as _VL
        _VL.stage_kit_macros(kd, macros, lambda q: _CR.resolve(q, base), prune=not bump_ports)
        import lef_override as _LO
        _LO.write_receipt(kd, macros)     # COORD 11-09 DRT-0073 class: corrected child LEFs this kit took, with both hashes
        import porous_views as _PV
        _PV.write_receipt(kd, macros)     # POROUS-ALL-1: porous_views.json only when OT_POROUS_VIEWS is set
        # DIE-QC-97 11-09: a hard core with clock_entry_access gets its access abstract by construction (cbx_q10 NL
        # DRT-0073: the signed blanket-OBS LEF was staged, the M5 ck had no access point)
        stage_clock_entry_lefs(P, tn, kd, macros, lambda q: _CR.resolve(q, base))
    srcs = []
    for f in rtl_files:
        dst = kd / "rtl" / Path(f).name
        if Path(f).resolve() != dst.resolve():
            shutil.copyfile(f, dst)
        srcs.append(f"/work/rtl/{Path(f).name}")
    stage_includes(rtl_files, kd / "rtl")
    # DIE-HEAD-53 11-01 (HEAD class LEP-BB): a hard macro instantiated with a parameter override (hd_lep0N
    # g_pp[k].u_pair = ot_s81hd_lep_pair #(.CHB(..))) has only a Liberty cell, which declares no parameters, so
    # yosys elaboration (GEN_LINT rtl_check, synth) stops with "does not have a parameter named ..".  Stage a
    # header-only blackbox <module>_bb.v (the native_bb form, read -lib -overwrite like the SRAM _bb views).
    for f in macro_param_blackboxes(macros, rtl_files, kd / "rtl", root, t.get("hard_cores", []),
                                    Path(P.path).parent if getattr(P, "path", None) else None):
        srcs.append(f"/work/rtl/{f.name}")
    rom_bits = max(declared_rom_bits(kd / "rtl"), declared_flop_mem_bits(kd / "rtl"))   # + DIE-KV-60/hubeo flop FIFOs
    landing_ff = defines_landing_ring(kd / "rtl")
    fsm_wires = fsm_none_wires(kd / "rtl", os.environ.get("OT_FSM_NONE_WIRES"))
    pins = type_pins(P, tn)
    bump_sites = bump_pin_sites(P, tn, bump_ports, macros, Path(root) if root else Path(__file__).resolve().parent.parent.parent) \
        if bump_ports else []
    io_text = io_tcl(P, tn, pins)
    for port, i, ln, cx, cy, pw, ph in bump_sites:
        io_text += (f"place_pin -pin_name {{{port}[{i}]}} -layer {ln} -location {{{cx:.4f} {cy:.4f}}} "
                    f"-pin_size {{{pw:.4f} {ph:.4f}}}   ;# interior: hard-IP line side (bump) on the macro pin\n")
    (kd / "io.tcl").write_text(io_text)
    top = P.type_top_layer(tn)
    import m8_grant as MG
    m8g = MG.kit_grant(P, tn)        # LAYER-BUDGET-1: leftover-M8 grant (None = off, kit unchanged)
    if m8g is not None and int(top[1:]) < 8:
        top = "M8"
    pdn = PDN
    if int(top[1:]) > int(P.layer_budget["partition_signal_max"][1:]):
        # face_layers raised this type to M8: keep its own M8 wiring off the die M8 PG bands (schema.PART_PG_BANDS),
        # so the die grid's M8 stripes run over the partition without shorts
        obs = ["", "set blk [ord::get_db_block]", "set dbu [$blk getDbUnitsPerMicron]"]
        smax = int(P.layer_budget["partition_signal_max"][1:])
        for li in range(smax + 1, int(top[1:]) + 1):
            ln = f"M{li}"
            if ln == MG.LAYER and m8g is not None:
                obs.append(MG.obstruction_tcl(m8g))   # die PG + die tracks from the plan grid, not the default band
                continue
            pitch, cen, half = S.PART_PG_BANDS[ln]
            horiz = P.layers[ln]["dir"] == "H"       # H layer: stripes along x -> y bands; V layer -> x bands
            ext, oth = (h, w) if horiz else (w, h)
            obs += [f"# face_layers {top}: obstruct the die {ln} PG bands in the partition (die stripes cross it)",
                    f"set lay [[ord::get_db_tech] findLayer {ln}]"]
            k = math.floor((0 - cen) / pitch)
            while cen + k * pitch - half < ext:
                a0, a1 = max(0.0, cen + k * pitch - half), min(ext, cen + k * pitch + half)
                if a1 > a0:
                    r = (0, a0, oth, a1) if horiz else (a0, 0, a1, oth)
                    obs.append("odb::dbObstruction_create $blk $lay " +
                               " ".join(f"[expr {{round({v:.4f}*$dbu)}}]" for v in r))
                k += 1
        pdn = PDN + "\n".join(obs) + "\n"
    import partition_ft_reserve
    ft_reservation = partition_ft_reserve.reservation(P, tn)
    if ft_reservation is not None:
        (kd / "partition_ft_reservation.json").write_text(json.dumps(ft_reservation, indent=1) + "\n")
        pdn += partition_ft_reserve.tcl(ft_reservation, partition_ft_reserve.macro_boxes(P.types[tn]))
        pdn += partition_ft_reserve.row_bridge_tcl(ft_reservation, w)
    phy_doms = phy_pg_domains(P, tn)
    if phy_doms:
        # PATH-KV-SYSC 10-25 PHY PG hook: separate VDDPHY region(s) of die.pg.domains inside this type
        pdn = phy_pg_pdn(P, tn, phy_doms, macros, root=root,
                         core_grids=core_pg_on(P, tn)) + pdn[len(PDN):]
        (kd / "phy_pg.json").write_text(json.dumps([dict(name=d[0], power=d[1], ground=d[2], rect_type_um=d[3],
                                                          macros=d[4]) for d in phy_doms], indent=1) + "\n")
    elif core_pg_on(P, tn):
        cg = core_pg_grids(P, tn, macros, root)
        if cg:
            pdn += "\n".join(cg) + "\n"
    pg_pub = core_pg_published(P, tn, macros, root, exclude={i for d in phy_doms for i in d[4]})
    if core_pg_on(P, tn):
        bad = core_pg_unconnected(pdn, macros, root, exclude={i for d in phy_doms for i in d[4]},
                                  strict=_core_pg_strict(P, tn), published=set(pg_pub))
        if bad:
            raise ValueError(f"type {tn}: core_pg_connect leaves macro PG pins unconnected: {bad[:4]}")
    (kd / "pdn.tcl").write_text(pdn)
    if m8g is not None:
        (kd / "m8_grant.json").write_text(json.dumps(m8g, indent=1) + "\n")
        shutil.copyfile(Path(__file__).with_name("m8_grant.py"), kd / "m8_grant.py")
    pg_cuts = pg_island_cuts(P, tn, root)
    if pg_cuts:
        (kd / "pg_island_cut.tcl").write_text(pg_island_cut_tcl(pg_cuts))
    post_pdn = ["/work/pg_island_cut.tcl"] if pg_cuts else []
    entry_pg = clock_entry_pg_cuts(P, tn)
    if entry_pg:
        from clock_entry_pg import render as render_entry_pg
        (kd / "clock_entry_pg_cut.json").write_text(json.dumps(
            dict(schema="opentallas.clock_entry_pg_cuts.v1", cuts=entry_pg), indent=2) + "\n")
        (kd / "clock_entry_pg_cut.tcl").write_text(render_entry_pg(entry_pg))
        post_pdn.append("/work/clock_entry_pg_cut.tcl")
    if pg_pub:      # PG-CORECONN-3: M7-top macro PG straps -> tile pins (after any island cut)
        (kd / "pg_publish.tcl").write_text(core_pg_publish_tcl(pg_pub))
        post_pdn.append("/work/pg_publish.tcl")
    if len(post_pdn) > 1:
        (kd / "post_pdn.tcl").write_text("# GENERATED by tools/die_plan/gen.py phys: POST_PDN_TCL steps in order.\n" +
                                         "".join(f"source {f}\n" for f in post_pdn))
    (kd / "make_tracks.tcl").write_text(make_tracks_tcl(P))
    (kd / "constraint.sdc").write_text(sdc(P, tn, pins))
    if core_tap_rows(P, tn) or edge_clock_latency(P, tn):
        (kd / "core_taps_ff.sdc").write_text(core_tap_ff_sdc(P, tn) + edge_clock_latency_tcl(P, tn, "ff"))
    ioh = io_hold_tcl(P, tn)            # IO-HOLD option A: per-port min input delays for the hold_gate / sign-off overlays
    if ioh:
        (kd / "io_hold.tcl").write_text(ioh)
    (kd / "prects_estimate.tcl").write_text(clock_phase_tcl(P, tn))
    shutil.copyfile(Path(__file__).with_name("native_cell_cap.tcl"), kd / "native_cell_cap.tcl")
    # COORD 11-04 06:00 (2): opt-in kit-level cap; without the option the file is byte-identical to before
    (kd / "pre_floorplan_type.tcl").write_text((f"set ::ot_native_cell_limit {int(native_cell_cap)}\n" if native_cell_cap else "")
                                               + "source /work/native_cell_cap.tcl\nsource /work/prects_estimate.tcl\n"
                                               + hold_pad_dont_touch_tcl(P, tn))
    import reset_tree as RT
    leaf_check = ""
    if RT.pipelined(P) or RT.wavefront(P):
        # FLOW-20 11-01: a hard wrapper's reset is the delivered port (bind.py `wire rst_n = arst_n`, no in-kit
        # terminal): reset_taps.tcl measures + reports that hop from the port instead of failing on the missing net
        port = "set rt_port_reset arst_n\n" if P.types[tn].get("hard") else ""
        leaf_check = (f"\nset rt_postplace 1\nset rt_leaf_reach_um {RT.relay_um(P):g}\n{port}"
                      "source /work/reset_taps.tcl\nunset rt_postplace\n")
    group_hook = ""
    if grouped["groups"]:
        (kd / "core_clock_groups.json").write_text(json.dumps(grouped, indent=1) + "\n")
        (kd / "core_clock_groups_apply.tcl").write_text(CG.tcl_text(grouped))
        shutil.copyfile(_common_flow_file("core_clock_groups.tcl", Path(__file__).resolve().parents[2]),
                        kd / "core_clock_groups.tcl")
        group_hook = "\nsource /work/core_clock_groups_apply.tcl\n"
    # DIE-HEAD-17 (opt-in partition_types.<t>.reg_spine): register clock as a plan-placed spine + local trees and the
    # hard-core early taps as dedicated branches (reg_spine.tcl / reg_spine.py, PRE_CTS); absent = kit unchanged.
    rsp_hook = ""
    if reg_spine_spec(P, tn):
        (kd / "reg_spine.json").write_text(json.dumps(reg_spine_spec(P, tn), indent=1, sort_keys=True) + "\n")
        for f in ("reg_spine.py", "reg_spine.tcl"):
            shutil.copyfile(Path(__file__).with_name(f), kd / f)
        rsp_hook = "\nuplevel #0 {source /work/reg_spine.tcl}\n"
    # FLOW-20 11-01: CTS-stage repair_timing leaves the CTS tree alone (cts_repair_protect.tcl; OpenSTA RequiredCmp
    # assert on KV kv3_phy when UnbufferMove removed + restored clock buffers on a macro-launch path)
    crp_hook = "\nuplevel #0 {source /work/cts_repair_protect.tcl}\n"
    # S81 RCK2-1109 (opt-in plan clock.pad_clock pins[].entries): plan-placed second pad-clock entries (pad_clock.py,
    # pad_clock_entry.tcl) before TritonCTS; absent = pre_cts.tcl byte-identical and no hook file in the kit.
    import pad_clock as PC
    pce_hook = PC.entries_tcl(P, tn)
    if pce_hook:
        shutil.copyfile(Path(__file__).with_name("pad_clock_entry.tcl"), kd / "pad_clock_entry.tcl")
        pce_hook = "\n" + pce_hook
    # VSN6-B 11-11 S7: post-place non-tap census + max-wire buffer estimate (cell_census.tcl), loud against 400k
    cc_hook = ("\nif {[file exists /work/cell_census.tcl]} {uplevel #0 {source /work/cell_census.tcl}; ot_cell_census place}"
               " else {puts \"OT_CELL_CENSUS WARN stage=place: cell_census.tcl is not in the kit, no recount\"}\n")
    (kd / "pre_cts.tcl").write_text(clock_phase_tcl(P, tn, before_cts=True) + leaf_check + group_hook + crp_hook
                                    + cc_hook + rsp_hook + pce_hook)
    # CP1-R10 / COORD 10-24: fail-closed SDC lint at kit generation (units, clocks, max+min IO delays, hold,
    # policy uncertainty (OWNER 12.24c setup 0 / hold 25) once per seam, no relaxed periods / exceptions); run_kit.sh re-runs it with the image liberty
    import sdc_lint
    lctx = sdc_lint.kit_context(P, tn)
    (kd / "sdc_lint.json").write_text(json.dumps(lctx, indent=1) + "\n")
    shutil.copyfile(Path(__file__).with_name("sdc_lint.py"), kd / "sdc_lint.py")
    shutil.copyfile(Path(__file__).with_name("rtl_lint.py"), kd / "rtl_lint.py")
    lerr = sdc_lint.lint((kd / "constraint.sdc").read_text(), **lctx)
    if lerr:
        raise sdc_lint.SdcLintError(f"type {tn}: constraint.sdc fails sdc_lint ({len(lerr)}): " + "; ".join(lerr[:8]))
    clat = core_latency_files(P, tn, kd, root, **core_mean_contract_options(P, tn, trial=trial))
    core_area = kit_core_area(t)
    forest = any(Path(f).name == "ot_pl_land_reset_forest.sv" for f in srcs)
    cfg = [f"# GENERATED by tools/die_plan/gen.py phys: partition type {tn} of die_plan {P.name}. Do not edit.",
           f"export DESIGN_NICKNAME = dp_{tn}",
           f"export DESIGN_NAME = {t['module']}",
           "export PLATFORM = asap7",
           "export VERILOG_FILES = " + " ".join(srcs),
           "export VERILOG_DEFINES = " + " ".join(type_verilog_defines(t, kit_defines)),
           "export SDC_FILE = /work/constraint.sdc",
           f"export DIE_AREA = 0 0 {_um(w)} {_um(h)}",
           f"export CORE_AREA = {' '.join(_um(v) for v in core_area)}",
           "export IO_CONSTRAINTS = /work/io.tcl",
           "export PDN_TCL = /work/pdn.tcl",
           *([f"export POST_PDN_TCL = {post_pdn[0] if len(post_pdn) == 1 else '/work/post_pdn.tcl'}"] if post_pdn else []),
           # override: platforms/asap7/config.mk (read AFTER the design config) sets MAKE_TRACKS with a plain
           # export, which silently replaced the plan tracks (M7 offset 0.016, not 0.032) -> every plan pin off-track
           "override export MAKE_TRACKS = /work/make_tracks.tcl",
           "export MIN_ROUTING_LAYER = M2",
           f"export MAX_ROUTING_LAYER = {top}",
           # KW-FIX-8 11-04 (COORD 16:5x, S81 GRT-0116 near misses): opt-in per row through wave item_env, off by default.
           # GRT overflow is not a sign-off gate; with this flag the kit continues to detail route and routed DRC decides.
           # The first two arguments are the ORFS GLOBAL_ROUTE_ARGS default, which this variable replaces.
           *(["export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -allow_congestion"]
             if os.environ.get("OT_GRT_ALLOW_CONGESTION") == "1" else []),
           # KW-FIX-8 11-04 (COORD GRT loop ruling): opt-in per row through wave item_env, off by default.  TritonCTS by
           # default sets CTS_NDR_0 on part of the clock tree (260 of 2462 clock nets on s81sl_leaf t32); GRT then drops it
           # net by net and restarts its 30 iterations each time.  CTS_ARGS replaces the ORFS argument list, so this is
           # the logged default list plus the flag.
           *(["export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none"]
             if os.environ.get("OT_CTS_NO_NDR") == "1" else []),
           # Opt-in for new forms: suppress redundant ORFS summaries before CTS only.
           # Explicit synthesis/geometry/hold checks and stages 4+ reports are unchanged.
           *(["export OT_SKIP_PRECTS_METRICS = 1"]
             if os.environ.get("OT_SKIP_PRECTS_METRICS") == "1" else []),
           f"export PLACE_DENSITY = {util:g}",
           "export SYNTH_HIERARCHICAL = 0",
           *_rtl_lint_dead_output_vars(),
           *_lec_frontend_vars(),
           "export SYNTH_REPEATABLE_BUILD = 1",
           # HEAD-KITS-3 10-28: OWNER D-ROM-2 declared-logic math tables (tools/mem_compiler/rom_declared_logic.json,
           # e.g. the KP4 GF(1024) inverse 1024x10 in every serdes FEC lane) are synthesised logic by decision; the ORFS
           # default SYNTH_MEMORY_MAX_BITS 4096 failed hd_serdes synth on them.  The limit is raised only to the largest
           # declared table defined in this kit's RTL, so any other inferred memory above that size still fails.
           # DIE-KV-60/hubeo 11-01: or the largest DECLARED_FLOP_MEMORIES flop FIFO the kit RTL defines (same exact-size form).
           *([f"export SYNTH_MEMORY_MAX_BITS = {rom_bits}"] if rom_bits > 4096 else []),
           # DIE-S81-26 10-29: declared clock-landing rings -> flip-flops per module (ot_keep_regs.tcl OT_LANDING_FF)
           *(["export OT_LANDING_FF = 1"] if landing_ff else []),
           # DIE-KV-34 10-29 plan budgets.cland_fit_reserve: landing_placement fits each CLAND cell on its whole
           # reserved footprint, so timing-driven GPL upsizing a FIRM ring cell in place cannot grow over a tapcell
           # (KV io_ft kits_gen5 3_5 DPL-0033: INVx1 -> INVx3 over TAPCELL). Absent key = unchanged kit.
           *([f"export OT_CLAND_FIT_RESERVE = {_cland_fit_mode(P.budgets, tn)}"] if _cland_fit_mode(P.budgets, tn) else []),
           # FLOW-6 10-30 budgets.cland_fit_resize (default-on since 12.27 b): fit each CLAND cell on its widest drive variant (HEAD
           # n3_turn v3nofr 3_5 DPL-0033: FIRM DFFHQNx1 abutting a TAPCELL resized to x2 in place). Absent = unchanged.
           # (AUTOBUILD-PIPE-4 10-31 OWNER 12.27 b: 'resize' is the default; see _cland_fit_mode)
           # FLOW-7 10-30 opt-in plan budgets.dpl_legalizer="diamond" (KV-022 SD: negotiation DPL non-convergence
           # around ~12k FIRM landing cells). Absent = unchanged kit.
           # DIE-HBM-97 11-09 (DPL class default-on for FT-reserved types too): see _dpl_args
           *_dpl_args(P.budgets, tn, dpl_diamond, landing=bool(t.get("clock", {}).get("landing_contract"))
                      or bool(ft_reservation), outline=t["outline_um"]),
           # FLOW-11 10-30 (default-on since 12.27 b; budgets.cland_pinslot_off_types opts out) (DIE-HEAD-43 (C)): ring slot flops next to their own
           # bus-bit pin (HEAD turn_a t_i farthest-slot p90 69 um, bit-major band fill). Absent = unchanged kit.
           *(["export OT_CLAND_PINSLOT = 1"] if _cland_pinslot(P.budgets, tn, cland_pinslot) else []),
           # DIE-KV-62/stations 11-02 opt-in budgets.cland_pinslot_dense_types: y-column pinslot rows body to body
           *(["export OT_CLAND_PINSLOT_DENSE = 1"] if _cland_pinslot_dense(P.budgets, tn) else []),
           # DIE-QC-97 11-09 opt-in budgets.cland_strip_rows(_types): thin the N/S ring_ff face strip (conservative kit wins)
           *([f"export OT_CLAND_STRIP_ROWS = {_cland_strip_rows(P.budgets, tn)}"] if _cland_strip_rows(P.budgets, tn) else []),
           "export LEC_CHECK = 0",
           # COORD ruling 4 (10-25): the platform adder map with every DONT_USE cell (HAxp5) as generic logic; run_kit.sh
           # generates it in the image before synth (adder_map_dontuse.py gen) and FAILs a netlist with a DONT_USE cell
           "export ADDER_MAP_FILE = /work/adder_map_dontuse.v",
           # Owner 00:46: uncertainty is in SDC; repair only 0..5 ps above it.
           "export HOLD_SLACK_MARGIN = 5",
           "export SETUP_SLACK_MARGIN = 0",
           "export SKIP_LAST_GASP = 1",
           # ELEM-S81 station405 10-24: repair_design sizes repeaters on the ASAP7 setRC wire model, which the
           # routed RCX exceeds ~1.8x in slew: every routed station405_c1 tile had 86..1830 max-slew violations
           # (worst 438..587 ps vs 320), all 2-pin repeater nets of ~190-196 um that GRT had clean.  Design to 50 % /
           # 20 % of the slew / cap limits so the repeater pitch fits the routed RC (slew ~ L^2: ~140 um).
           # Opt-in (gen.py phys --slew-margin / --cap-margin; COORD: default keeps the old flow, lanes adopt it).
           *([f"export SLEW_MARGIN = {margins[0]:g}"] if margins and margins[0] is not None else []),
           *([f"export CAP_MARGIN = {margins[1]:g}"] if margins and margins[1] is not None else []),
           # CP1-R10 10-24: ORFS synth_odb.tcl eliminate_dead_logic deleted face registers whose q the leaf leaves
           # unused (r10b: 120 in-bus flops); boundary cells dont_touch around that step only
           "export PRE_SYNTH_TCL = /work/face_keep.tcl",
           "export POST_SYNTH_TCL = /work/face_keep_release.tcl",
           # KV-KITS-5 10-27 (COORD sys_c LEC ruling; QC-CORES-2 EQUIVALENT with it): the shared keep-register
           # canonicalize hook puts keep on the flip-flop CELL of every (* keep *) register, so opt_merge cannot fold
           # declared copies (sys_c: 374 of 11287 kept bits merged without it).  Attribute based, so it also holds
           # in $paramod-renamed modules (a keep_module name list matched nothing there).
           "export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl",
           # KV-KITS-5 10-27 (opt-in gen.py phys --gpl-plain TYPES): pure-FT corridor kits (stations FIRM at their
           # plan sites, ~3k um2 movable vs 200k fixed) place on plain wirelength; routability-driven GPL inflated
           # +1495% and diverged on kv3_hub_Ei (GPL-0305 after 2h25m), plain GPL converged in 438 s
           *(["export GPL_ROUTABILITY_DRIVEN = 0", "export GPL_TIMING_DRIVEN = 0"] if gpl_plain else []),
           *(["export SKIP_INCREMENTAL_REPAIR = 1   # proof kit: seam / abutment proof, partition IO budgets not "
              "closed (the post-GRT repair loop otherwise runs for hours on the IO paths)"] if proof else []),
           "export TNS_END_PERCENT = 100",
           # ELEM-S81 station405 10-24 (opt-in gen.py phys --hold-ff-margin PS): hold signs off at FF only, but ORFS
           # repairs hold over every kit corner, and at TT the seam inputs see ~-40 ps hold (vclk is fixed at the plan
           # insertion while the local tree is slower at TT than FF): the TT hold buffers eat the TT setup of the same
           # face flops (station405_c1: 'Unable to repair all hold checks', T7 r4b TT -23.68 after hold).  CTS-stage
           # combined repair is skipped; run_kit.sh runs GRT + repair at CORNERS=bc with this hold margin, then
           # route / finish / abstract on the native corners; TT setup is checked unchanged by signoff.py.
           *(["export SKIP_CTS_REPAIR_TIMING = 1", f"export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}"]
             if hold_ff_margin is not None else []),
           # pin registers FIRM at their faces through GPL, released for DPL (CP1 10-23: GPL left them ~1 mm inside)
           "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl",
           "export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl",
           # R4: one clock port per tap; every sink moves to its nearest tap's net before CTS (local trees)
           "export PRE_FLOORPLAN_TCL = /work/pre_floorplan_type.tcl",
           "export PRE_CTS_TCL = /work/pre_cts.tcl",
           # COORD 10-23: taps sized by sink count (sink-anchored taps: the plan's clock.tap_max_sinks)
           f"export OT_TAP_MAX_SINKS = {_tap_cap(t)}",
           *([f"export OT_HOP_LATCH_CAPTURE_TAP = {_hop_latch_tap_cfg(P, tn)}"] if _hop_latch_tap_cfg(P, tn) else []),
           *([f"export OT_HOP_LATCH_FRAC_MAP = {_hop_latch_frac_cfg(P, tn)}"] if _hop_latch_frac_cfg(P, tn) else []),
           *([f"export OT_EDGE_SPLIT_PORTS = {' '.join(edge_split_ports(P, tn))}"] if edge_split_ports(P, tn) else []),
           *(["export OT_EDGE_SPLIT_MACRO_PIN = 1"] if edge_split_ports(P, tn) and P.die.get("name") in EDGE_SPLIT_MACRO_PIN_DIES else []),
           # COORD 10-23: tap trees balanced to one insertion (delay chains on the short trees, <= tol spread), then
           # FLOW 10-25 F4: zero-logic register pairs onto one leaf (leaf_affinity.tcl; OT_LEAF_AFFINITY=0 = off)
           "export POST_CTS_TCL = /work/cts_post.tcl",
           # DIE-HEAD-17 reg_spine: the plan balances the spine taps and sizes the core early-tap branches, so the
           # flow tap_balance pass (incl. its core re-hang pass) only reports
           *(["export OT_TAP_REPORT_ONLY = 1"] if reg_spine_spec(P, tn) else []),
           f"export OT_TAP_TARGET_PS = {ib['tt']:g}",
           # FLOW 10-25 (ruling 9.7 / decision 5e): bound pin-register insertion per corner (vclk_corner.tcl)
           f"export OT_VCLK_TT = {t_lib(ib['tt']):.4f}",
           f"export OT_VCLK_FF = {t_lib(ib['ff']):.4f}",
           # CLOCK-RESET IO-HOLD 10-25: the seam hold contract the post-CTS FF gate applies (hold_gate.tcl)
           # DIE-HEAD-59 11-03: opt-in per item (item_env, commas for spaces): keep these FSM wires in their RTL encoding
           # DIE-HEAD-85/HSPLIT 11-07: plus the module-defined FSM wires (fsm_none_wires, e.g. the s81 gearbox hunt)
           *([f"export OT_FSM_NONE_WIRES = {' '.join(fsm_wires)}"] if fsm_wires else []),
           # KW-FIX-13 11-05: opt-in per item (item_env, commas for spaces), e.g. -noshare where yosys share does not finish
           *([f"export SYNTH_ARGS = {os.environ['OT_SYNTH_ARGS'].replace(',', ' ')}"] if os.environ.get("OT_SYNTH_ARGS") else []),
           f"export OT_HOLD_IN_MIN = {t_lib(hold_in_min_ps(P)):.4f}",
           # DIE-HEAD-59 11-03: opt-in per item (kit_wave item_env reaches gen only): hold_gate.tcl stop base
           *([f"export OT_HOLD_STOP_PS = {os.environ['OT_HOLD_STOP_PS']}"] if os.environ.get("OT_HOLD_STOP_PS") else []),
           # KW-FIX-43 11-10 LAND-RESERVE: opt-in per item (item_env OT_LAND_RESERVE=1): face_flops.tcl reserves the non-ring
           # landing windows before the station grid and landing_placement.tcl grows start / literal-reset windows
           *(["export OT_LAND_RESERVE = 1"] if os.environ.get("OT_LAND_RESERVE") == "1" else []),
           f"export OT_HOLD_OUT_MIN = {t_lib(hold_out_min_sdc_ps(P, tn)):.4f}",
           *([f"export OT_TAP_WINDOW = {t_lib(tap_window_max_ps(P, tn)):.4f}"] if tap_window_ps(P, tn) else []),
           # FLOW 10-25 F2: placement / CTS / GRT parasitic estimates on the ASAP7 per-layer RC calibrated to routed
           # RCX (setRC_rcx_asap7.tcl; the stock setRC.tcl put clock sinks 11-57 ps above RCX).  ORFS reads
           # LAYER_PARASITICS_FILE (this image) / SET_RC_TCL (newer variables.yaml) instead of the platform setRC.tcl.
           *([f"export LAYER_PARASITICS_FILE = /work/{RC_CAL_KIT}", f"export SET_RC_TCL = /work/{RC_CAL_KIT}"]
             if rc_cal else []),
           # decision 5 (d) (owner 2026-10-24): every local tree balanced to the common latency within a 20 ps window
           # (clock.local_window_ps; insertion_tol_ps stays the kit SDC seam-hold budget), padding step <= 10 ps
           f"export OT_TAP_WINDOW_PS = {float(P.clock.get('local_window_ps', 20.0)):g}",
           f"export OT_TAP_TOL_PS = {float(P.clock.get('local_tol_ps', 10.0)):g}",
           f"export OT_TAP_PITCH_UM = {S.tap_pitch(P, tn):g}",
           *_density_cfg(t),
           # CP2: hard-core internal clock latency (core_latency.txt: inst pin ps tap) for tap_balance.tcl's effective
           # arrival, and the early core taps (core_taps.txt) clock_taps.tcl hangs the core clock pins on
           *(["export OT_CORE_LAT = /work/core_latency.txt"] if clat["rows"] else []),
           *(["export OT_CORE_TAPS = /work/core_taps.txt"] if clat["taps"] else []),
           # signoff setup corner (TT); ORFS asap7 defaults to BC = FF libs, i.e. kit synth / CTS / repair at FF
           "export CORNER = TC",
           # Native TT/FF repair for macro-free kits. Macro parents need their
           # child timing libraries separated explicitly by corner.
           *(["export CORNERS = tc bc",
              "export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)",
              "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)"] if not macros else []),
           *([f"export OT_RELAY_MID_RE = {P.budgets.get('relay_mid_re', RELAY_MID_RE)}"] if macros else []),
           # S81-TYPES-5 11-07 (opt-in plan budgets, absent = unchanged kits): relay clusters fit outside narrow
           # channels (relay_mid.tcl FIT) and macro gaps < gutter_block_um get placement blockages (gutter_block.tcl)
           *(["export OT_RELAY_MID_FIT = 1"] if macros and _relay_mid_fit(P.budgets, tn) else []),
           *([f"export OT_GUTTER_BLOCK_UM = {_gutter_block_um(P.budgets, tn)}"] if macros and _gutter_block_um(P.budgets, tn) else []),
           *([f"export OT_GUTTER_BLOCK_MIN_SPAN_UM = {_gutter_block_min_span_um(P.budgets)}"]
             if macros and _gutter_block_um(P.budgets, tn) and _gutter_block_min_span_um(P.budgets) else []),
           # DIE-HEAD-69 11-05: core_out_land.tcl opt-in (GEN env OT_CORE_OUT_LAND=1 via wave item_env, or plan budgets list)
           *(["export OT_CORE_OUT_LAND = 1"] if macros and (os.environ.get("OT_CORE_OUT_LAND") == "1"
                                                       or tn in (P.budgets.get("core_out_land_types") or ())) else []),
           # PATH-QC-A0N59 10-25: macro kits had no BC_LIB_FILES, so the post-CTS FF hold gate stopped NOT RUN
           # ("hold gate: BC_LIB_FILES missing", native59).  Per-corner gate/sign-off lists only (implementation
           # corner unchanged): std cells of the corner + each macro's sibling corner view copied into macros/.
           *([f"export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) {' '.join(_corner_libs(mlib, kd, 'tt'))}",
              f"export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) {' '.join(_corner_libs(mlib, kd, 'ff'))}"] if macros else []),
           # S81-P9 10-23: landing reset forest leaves re-clustered to identical branch flops by location after GPL
           # (forest_recluster.tcl; only kits whose sources hold ot_pl_land_reset_forest)
           *(["export POST_GLOBAL_PLACE_TCL = /work/forest_recluster.tcl"] if forest else []),
           *([f"export ADDITIONAL_LEFS = {' '.join(mlef)}", f"export ADDITIONAL_LIBS = {' '.join(mlib)}",
              "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl"] if macros else [])]
    if macros:
        (kd / "macro_place.tcl").write_text("\n".join(mplace) + "\n")
        if macro_moves:
            if set(macro_moves) - {m[0] for m in macros}:
                raise ValueError(f"type {tn}: OT_MACRO_MOVES names no placed macro: {sorted(set(macro_moves) - {m[0] for m in macros})}")
            (kd / "macro_moves.json").write_text(json.dumps(macro_moves, indent=1) + "\n")
    # Explicit full fixed-macro contract: use the standard stage pre-hook,
    # preserving the native placement deck and all following ORFS stages.
    import fully_fixed_macros as FFM
    cfg += FFM.install(t,kd,macros,kit_core_area(t),Path(root) if root else Path(__file__).resolve().parents[2])
    cfg += install_gp_noconverge_gate(kd, cfg)
    if skip_ir:
        # opt-in gen.py phys --skip-kit-ir (CODEX-LOG 10-24 root practice): ORFS 6_report's per-kit PDNSim (PSM) IR
        # analysis is skipped (station405: it pushed 6_report past 36 GB, exit 247); PG geometry is unchanged and IR
        # stays NOT RUN for the kit (dedicated TRIAL IR remains required).  Not a timing / sign-off input.
        cfg += ["# kit IR analysis skipped (gen.py phys --skip-kit-ir): IR NOT RUN here; dedicated TRIAL IR remains required",
                "export PWR_NETS_VOLTAGES =", "export GND_NETS_VOLTAGES ="]
    if max_wire_um is not None:
        # opt-in gen.py phys --max-wire-um UM (ELEM-S81 station405 10-24): the post-GRT repair_design also gets
        # -max_wire_length UM (grt_maxwire.tcl overrides ORFS repair_design_helper; same SLEW/CAP margins): routed
        # station kits kept 2-27 max-slew pins on ~150 um single-driver M2/M3 segments the GRT estimate passed.
        cfg += [f"export OT_MAXWIRE_UM = {max_wire_um:g}"]
        shutil.copyfile(Path(__file__).with_name("grt_maxwire.tcl"), kd / "grt_maxwire.tcl")
    # FLOW 10-25: GRT hooks (grt_pre.tcl: FF vclk binding for the FF-only GRT step + optional max-wire repeaters;
    # grt_post.tcl: density GRT-RC tap pass + vclk back to the SDC value before 5_1_grt.sdc is written)
    cfg += ["export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl", "export POST_GLOBAL_ROUTE_TCL = /work/grt_post.tcl"]
    # HOLD-REPAIR 10-26 (12.4a a1): the FF GRT hold repair pads with HB4 (hold_pad_hb4.tcl) and a raised buffer cap;
    # hold_repair_pre.tcl sources grt_pre.tcl first.  Was plan_demand / die_sta-demand kits only (CLOCK-KV-R21).
    # KIT-TRIAGE-1/G5 11-01 (OWNER 12.28b closure first; COORD 05:0x: the HBM-CORES-KITS-40 HB4 hook b26a827db45 is the
    # class form): EVERY gen_phys kit gets it.  16 S81 slice_station kits stopped FAIL_POSTCTS at pre-repair FF WNS
    # -71..-280 ps (exp0 core: BUFx2 stalled at -25.87, HB4 -86.36 -> +0.94 / 0 viol).  dont_use lifted ONLY inside
    # repair_timing -hold; constraints, margins, corners and the routed FF hold acceptance unchanged.
    cfg[cfg.index("export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl")] = "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl"
    cfg += [f"export OT_MAX_BUFFER_PERCENT = {HOLD_REPAIR_MAX_BUFFER_PERCENT:g}"]
    shutil.copyfile(Path(__file__).with_name("hold_repair_pre.tcl"), kd / "hold_repair_pre.tcl")
    shutil.copyfile(_common_flow_file(HOLD_PAD_HB4.name, HOLD_PAD_HB4.parents[2]), kd / "hold_pad_hb4.tcl")
    if _tap_grt_pre(P, t):
        # FLOW-INFRA-2 10-25: tap trees re-balanced on GRT RC before the FF GRT hold repair (tapbal_grt.tcl)
        # + pin-register leaf pad (pinreg_pad.tcl): the gate quantity, not the whole-tree mean
        cfg += ["export OT_TAP_GRT_PRE = 1", "export OT_PINREG_PAD = 1"]
    if P.reset.get("relay_driver"):
        cfg.append("export OT_RESET_PAIR_FIXED = 1")
    if t.get("clock", {}).get("tap_passthrough"):
        # FLOW-GEN-2 (opt-in clock.tap_passthrough): hard-core island ft clock pass-through inputs are followed, not
        # measured as tap sinks (tap_balance.tcl tb_passthru)
        cfg.append("export OT_TAP_PASSTHRU = 1")
    if t.get("clock", {}).get("tap_core_etap"):
        # HEAD-TILE-ETAP as a plan form (DH59-TILE 11-03, opt-in clock.tap_core_etap): tap_balance.tcl early-source core re-hang
        cfg.append("export OT_TAP_CORE_ETAP = 1")
    if t.get("clock", {}).get("pregrt_ff_hold"):
        # HEAD-TILE-PREGRT-HOLD (DH59-TILE 11-03, opt-in clock.pregrt_ff_hold): pregrt_ff_hold.py, run_kit.sh step below
        cfg.append("export OT_PREGRT_FF_HOLD = 1")
    cfg += tap_chain_affinity_exports(t)
    cfg += tap_pair_affinity_exports(t)
    cfg += tap_group_exports(t)
    cfg += rck_band_exports(P, tn)
    import pad_clock as PC
    PC.write_contract(P, tn, kd)
    cons = cons_kit_settings()
    if cons:
        cons_kit_apply(cfg, kd, cons, io_text, top, mlef)
    cfg += txl_mid_exports(cfg, kd)
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    if macros and hold_ff_margin is not None:
        macro_ff_repair_stage(kd, macros, mlib)
    if os.environ.get("OT_GRT_NONPORT_HOLD") == "1":      # opt-in; chained after any macro-FF wrapper written above
        grt_nonport_hold_chain(kd)
    for f in ("face_flops.tcl", "face_flops_release.tcl", "face_keep.tcl", "face_keep_release.tcl", "ft_polarity_local.tcl",
              "clock_taps.tcl", "cell_census.tcl", "tap_chain_affinity.tcl", "tap_pair_affinity.tcl", "tap_pair_plan.tcl", "tap_balance.tcl", "reset_taps.tcl", "vclk_corner.tcl", "postcts_gate.tcl", "core_clock_band.py", "partition_clock_binding.py", "grt_pre.tcl",
              "grt_post.tcl", "cts_post.tcl", "leaf_affinity.tcl", "tapbal_grt.tcl", "subtree_balance.tcl", "pinreg_pad.tcl",
              "pinreg_measure.tcl", "keepout_phys.tcl", "cts_repair_protect.tcl", "pg_connect.tcl", "hold_guard_grt.tcl", "grt_layers.tcl"):
        shutil.copyfile(Path(__file__).with_name(f), kd / f)
        if f == "reset_taps.tcl" and (RT.pipelined(P) or RT.wavefront(P)):
            hook = kd / f
            reset_prefix = f"set rt_leaf_tap {RT.leaf_tap(P, tn)}\n"
            if t.get("reset", {}).get("local_taps_um"):
                # These are terminal relay sites, not additional clock BTerms.
                reset_prefix += "set rt_consumer_taps_um {" + " ".join(
                    f"{{{i} {x:.5f} {y:.5f}}}" for i, (_, x, y) in enumerate(RT.consumer_taps(P, tn))) + "}\n"
            hook.write_text(reset_prefix + hook.read_text())
    if edge_split_ports(P, tn):
        for f in ("clock_edge_split.tcl", "clock_edge_balance.tcl"):
            shutil.copyfile(Path(__file__).with_name(f), kd / f)
        hook = kd / "cts_post.tcl"
        line = "uplevel #0 [list source [file join $cp_dir tap_balance.tcl]]\n"
        body = hook.read_text()
        assert body.count(line) == 1, "cts_post.tcl: tap_balance line"
        hook.write_text(body.replace(line, line + "uplevel #0 [list source [file join $cp_dir clock_edge_balance.tcl]]\n"))
    if t.get("port_buf_at_pin", False) is True:
        # PORT-BUF-AT-PIN (S81-SVCRS-3 11-10, COORD ruling): at PRE_DETAIL_PLACE every output port's single BUF / INV
        # driver more than 10 um from its pin is placed on the pin's face before DPL (placement only, 0 cycles, no
        # new cells; a driver already within 10 um is not touched).  IRG hslice form route 532125bc -> 6878dbfe44:
        # 47 ko_key port slews (worst 502 ps, limit 260; repair_design added 0) -> 0.  OPT-IN per plan type
        # ("port_buf_at_pin": true): on signed S81 types it would move 332-2183 drivers by up to 57 um (dry run 11-10),
        # placement churn on kits that close at the 2 fF IO load.  Appended right after the base hook.
        shutil.copyfile(Path(__file__).resolve().parents[2] / "physical" / "common_flow" / "port_buf_at_pin.tcl",
                        kd / "port_buf_at_pin.tcl")
        with (kd / "face_flops_release.tcl").open("a") as f:
            f.write(PORT_BUF_AT_PIN_LINE)
    islands = die_islands_tcl(P, tn)
    if islands:
        (kd / "die_islands.tcl").write_text(islands)
        hook = kd / "face_flops.tcl"
        hook.write_text("source /work/die_islands.tcl\n" + hook.read_text())
    rs_pre, rs_post, rs_rel = reserved_sites_tcl(P, tn)
    if rs_pre:
        (kd / "reserved_sites.tcl").write_text(rs_pre)
        hook = kd / "face_flops.tcl"
        hook.write_text("source /work/reserved_sites.tcl\n" + hook.read_text())
    if t.get("clock", {}).get("landing_contract"):
        import landing_contract as LC
        (kd / "landing_contract.json").write_text(json.dumps(t["clock"]["landing_contract"], indent=1) + "\n")
        # kit-rtl wrappers declare bound-only one-bit pins as [0:0] vectors -> BTerm "<port>[0]" (KV-022)
        bit0 = LC.bit0_ports((kd / "rtl" / f"{t['module']}.sv").read_text()) if plain_rings else frozenset()
        (kd / "landing_exports.tcl").write_text(LC.export_tcl(P, tn, bit0))
        (kd / "landing_export_check.tcl").write_text(LC.export_check_tcl(P, tn, bit0))  # sourced by cts_post.tcl
        hook = kd / "clock_taps.tcl"
        hook.write_text(hook.read_text() + "\nsource /work/landing_exports.tcl\n")
        import landing_place as LP
        (kd / "landing_placement.tcl").write_text(LP.tcl(P, tn, macro_moves))
        hook = kd / "face_flops.tcl"
        hook.write_text(hook.read_text() + "\n" + LANDING_PLACEMENT_HOOK + "\n")
        # The new cells are packed to actual nonoverlapping rows/sites. Keep
        # them FIRM through DPL; their bands are a timing/reach contract.
        hook = kd / "face_flops_release.tcl"
        hook.write_text(hook.read_text() + """
set cland_refirm 0
set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt r]
foreach cland_line [split [read $cland_fh] "\n"] {
 set cland_fields [split $cland_line "\t"]
 if {![string match "cland:*" [lindex $cland_fields 1]]} continue
 set cland_i [$ff_blk findInst [lindex $cland_fields 0]]
 if {$cland_i eq "NULL"} { error "OT_CLAND placed instance disappeared before DPL" }
 $cland_i setPlacementStatus FIRM; incr cland_refirm
}
close $cland_fh
puts "OT_CLAND preserved $cland_refirm legally packed cells FIRM through DPL"
""" + CLAND_RELEASE_GROWN_TCL)
    # CODEX-PICKUP-KV 11-01 (KV HHP joint event): plan relay_sites keys naming EXISTING clock-landing ring flops
    # (u_cland_*) are placed after the landing placement hook, which would otherwise pack them back into the band
    if t.get("relay_sites"):
        import kit_istations
        post = kit_istations.relay_sites_post_tcl(tn, t)
        if post:
            hook = kd / "face_flops.tcl"
            hook.write_text(hook.read_text() + "\n" + post + "\n")
    if rs_post:
        # after the landing placement hook: the rings are FIRM in their banks before the bank becomes a GPL blockage
        (kd / "reserved_banks.tcl").write_text(rs_post)
        (kd / "reserved_banks_release.tcl").write_text(rs_rel)
        hook = kd / "face_flops.tcl"
        hook.write_text(hook.read_text() + "\nsource /work/reserved_banks.tcl\n")
        hook = kd / "face_flops_release.tcl"
        hook.write_text("source /work/reserved_banks_release.tcl\n" + hook.read_text())
    if t.get("rck_band"):
        # S81-RCK-3 (COORD 09:41 class form): first-stage capture flops of the PHY receiver FIRM under its PG region;
        # face_flops_release.tcl releases them (ot_face_flops.txt rows tagged RCKB) for DPL
        shutil.copyfile(Path(__file__).with_name("rck_band.tcl"), kd / "rck_band.tcl")
        hook = kd / "face_flops.tcl"
        hook.write_text(hook.read_text() + "\n" + RCK_BAND_HOOK + "\n")
    bump_out = [b for b in pad_bumps(P, tn) if b["dir"] == "output"]
    if bump_out:
        # S81-PMATX-DT 11-09 (DIE-S81-85, serdes__t14 a11 G2 u_ptx -> io_pma_tx -249 ps): a macro_pin output pad's die pin
        # IS the macro pin (0 um), but ORFS buffer_ports put its port buffer outside the PMA stack (~270 um down + back,
        # 15 buffers).  dont_touch on those nets at PRE_GLOBAL_PLACE (before buffer_ports / repair_design): no cell, no
        # pin cycle.  Line-side analog pads only (pad_bumps); fails closed when no such net is found.
        (kd / "pad_bump_dt.tcl").write_text(pad_bump_dt_tcl(bump_out))
        hook = kd / "face_flops.tcl"
        hook.write_text("source /work/pad_bump_dt.tcl\n" + hook.read_text())
    if t.get("chain_even"):
        # S81-RCK-4 11-07: register chains get equal hops after GPL, LAST in the release hook (before DPL); no netlist change
        shutil.copyfile(Path(__file__).with_name("chain_even.tcl"), kd / "chain_even.tcl")
        (kd / "chain_even_cfg.tcl").write_text(chain_even_cfg(t["chain_even"]))
        hook = kd / "face_flops_release.tcl"
        hook.write_text(hook.read_text() + "\n" + CHAIN_EVEN_HOOK + "\n")
    if core_input_place(P.raw, tn):
        for f_ in ("core_input_anchor.tcl", "core_input_chain.tcl"):
            shutil.copyfile(Path(__file__).with_name(f_), kd / f_)
        with (kd / "face_flops.tcl").open("a") as f_:
            f_.write(CORE_INPUT_PLACE_ANCHOR)
        # the chain spread runs at PRE_RESIZE (after GPL, before repair_design buffers the new hops; pilot8 at
        # PRE_DETAIL_PLACE left 485 ps BUFx3 stages): appended to the kit's PRE_RESIZE hook (the PLACE-NOCONVERGE gate
        # runs first and may stop the run), or the hook itself when the kit has none
        mk = (kd / "config.mk").read_text()
        m_ = re.search(r"^export PRE_RESIZE_TCL = /work/(\S+)\s*$", mk, re.M)
        if m_ and (kd / m_.group(1)).is_file():
            with (kd / m_.group(1)).open("a") as f_:
                f_.write(CORE_INPUT_PLACE_CHAIN)
        elif m_:
            raise ValueError(f"core_input_place: PRE_RESIZE_TCL {m_.group(1)} is not a kit file")
        else:
            (kd / "config.mk").write_text(mk.rstrip("\n") + "\nexport PRE_RESIZE_TCL = /work/core_input_chain.tcl\n")
    if t.get("reset_relay_full"):
        reset_relay_full(kd / "rtl")
    # MASTER PLAN 12.7c (opt-in --master-slice DIR): the type's slice -> master_slice.json/.tcl, sourced at
    # PRE_GLOBAL_PLACE (face_flops.tcl: after io placement, before GPL); refused without a slice once required
    import master_slice as MS
    ms = MS.kit_apply(kd, tn, [w, h], master_slice, P.raw, trial, kind="partition", gpl_hook=kd / "face_flops.tcl")
    stages = t.get("reset", {}).get("physical_stages", [])
    if stages:
        import fup_reset_groups as FGR
        for stage in stages:
            re.compile(stage["selector"])
            x, y = stage["xy_um"]
            if not (0 <= x <= w and 0 <= y <= h):
                raise ValueError(f"{tn}: private reset stage outside outline")
        # Preserve independent first stages through synthesis. The source module
        # itself carries keep_hierarchy; missing source attributes fail closed.
        text = "\n".join((kd / "rtl" / Path(f).name).read_text() for f in rtl_files)
        for module in t.get("reset", {}).get("keep_modules", []):
            pattern = r"\(\*[^*]*\bkeep_hierarchy\b[^*]*\*\)\s*module\s+" + re.escape(module) + r"\b"
            if not re.search(pattern, text):
                raise ValueError(f"{tn}: private reset module {module} lacks keep_hierarchy source")
        manifest = dict(type=tn, anchors=[[s["selector"], *s["xy_um"]] for s in stages])
        (kd / "reset_physical_stages.json").write_text(json.dumps(manifest, indent=1) + "\n")
        (kd / "reset_physical_stages.tcl").write_text(FGR.tcl(manifest))
        (kd / "reset_physical_stages_release.tcl").write_text(FGR.tcl(manifest, True))
        with (kd / "face_flops.tcl").open("a") as f:
            f.write("\nsource /work/reset_physical_stages.tcl\n")
        with (kd / "face_flops_release.tcl").open("a") as f:
            f.write("\nsource /work/reset_physical_stages_release.tcl\n")
    if region_guide:
        # FLOW-23 (COORD 11-02 23:0x, GEOM-111 class D, opt-in gen phys --region-guide TYPE=SPEC): soft GPL region
        # guides per failing r2r bit slice (tools/die_plan/region_guide.py plan of the kit's last AUTO-GEOM), sourced
        # LAST in face_flops.tcl, released at the end of face_flops_release.tcl (before DPL); no spec = kit unchanged.
        import region_guide as RG
        RG.install(kd, json.loads(Path(region_guide).read_text()), outline=(w, h),
                   src=dict(file=str(region_guide), sha256=_hashlib.sha256(Path(region_guide).read_bytes()).hexdigest()))
    if rc_cal:
        import core_flow   # FLOW-RC-1: fail-closed per-class (signal + clock) RC calibration guard
        core_flow.install_rc(kd, Path(__file__).with_name(RC_CAL_FILE))
    (kd / "clock_binding.json").write_text(json.dumps(dict(type=tn, insertion_ps=dict(tt=ib["tt"], ff=ib["ff"]),
                                                           insertion_tol_ps=ib["tol"], basis=ib["basis"],
                                                           parent_early_tap_ps=ib["early_tap_ps"],
                                                           rule="METHODOLOGY 9.7 / BRIEFING 5e; FLOW 2026-10-25"),
                                                      indent=1) + "\n")
    if _density(t):
        shutil.copyfile(Path(__file__).with_name("tap_balance_grt.tcl"), kd / "tap_balance_grt.tcl")
    if forest:
        shutil.copyfile(Path(__file__).with_name("forest_recluster.tcl"), kd / "forest_recluster.tcl")
    # KV-G3 10-24: FIRM plan internal stations / plan-cell sites of a bound kit (kit_istations.py next to its RTL)
    ist = []
    if t.get('realize_internal_stations'):
        ist = [Path(f).parent / (t['module'] + '.istations.tcl') for f in rtl_files[:1]
               if (Path(f).parent / (t['module'] + '.istations.tcl')).is_file()]
        if not ist:
            raise ValueError(f'{tn}: realized source lacks its exact station placement sidecar')
    if not ist:
        ist = [Path(f).parent / "istations.tcl" for f in rtl_files[:1] if (Path(f).parent / "istations.tcl").is_file()]
    if ist:
        shutil.copyfile(ist[0], kd / "istations.tcl")
        if t.get('realize_internal_stations'):
            # The exported exact kit RTL is later rebound from rtl/. Preserve
            # its per-module placement sidecar across that export boundary.
            shutil.copyfile(ist[0], kd / 'rtl' / (t['module'] + '.istations.tcl'))
    elif t.get("relay_sites"):
        # DIE-KV-60 11-01: plan relay_sites on a bound kit without a native station sidecar (KV hard PHY wrappers)
        import kit_istations
        (kd / "istations.tcl").write_text(kit_istations.relay_sites_only_tcl(tn, t))
    # OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): FIRM sites of the reset entry stage + synchronous relay
    # tree.  kit_rsync writes reset_tree.tcl next to bound kit RTL; a gen_rtl kit of a pipelined plan gets it from the
    # plan (the same tree gen_rtl emitted).
    rtt = [Path(f).parent / "reset_tree.tcl" for f in rtl_files[:1] if (Path(f).parent / "reset_tree.tcl").is_file()]
    import reset_tree as RT
    live_boot_placement = t.get("reset", {}).get("source_live_bootstrap_placement", False)
    if native_reset and live_boot_placement:
        raise ValueError(f"{tn}: source-live omission cannot change captured native reset authority")
    if native_reset:
        # Captured native authority survives isolated plans without a die-level
        # reset solver configuration. Never fall back to a re-solved graph.
        (kd / "reset_tree.tcl").write_text(RT.tcl_text(native_reset["tree"],
            native_paths=native_reset["native_paths"],
            native_nodes=native_reset["physical_nodes"],
            native_sites=native_reset["placement_sites"]))
    elif rtt and not live_boot_placement:
        (kd / "reset_tree.tcl").write_text(RT.project_core_paths(rtt[0].read_text(),
            t.get("hard_cores", []) + t.get("contents", [])))
    elif RT.delivered(P) and not t.get("hard"):
        reset_model = RT.for_type(P, tn)
        unused_bootstrap = []
        if live_boot_placement:
            wrappers = []
            for f in rtl_files:
                text = Path(f).read_text()
                clean = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
                if re.search(r"\bmodule\s+" + re.escape(t['module']) + r"\b", clean):
                    wrappers.append((Path(f), text))
            if len(wrappers) != 1 or native_reset:
                raise ValueError(f'{tn}: source-live reset placement needs one literal top wrapper')
            audit = RT.unused_bootstrap_placements(RT.start_relays(reset_model), wrappers[0][1], t['module'])
            audit['wrapper'] = str(wrappers[0][0])
            (kd / 'reset_source_live_inventory.json').write_text(json.dumps(audit, indent=1) + '\n')
            unused_bootstrap = audit['omitted']
        (kd / "reset_tree.tcl").write_text(RT.tcl_text(reset_model,
            unused_bootstrap=unused_bootstrap))
    # AUTOBUILD-PIPE-5 10-31 (DIE-KV-50 kv3_phy, COORD 04:4x): a hard wrapper (gen phys --hard-wrappers) is a hard
    # partition of the die reset wavefront (reset_tree.wf_solve: leaf, raw delivered reset at reset.tap_um, depth
    # reset.depth); its bound RTL carries its own reset form, so the kit gets no generated reset tree (no file).
    if P.reset.get("relay_driver"):
        shutil.copyfile(Path(__file__).with_name("reset_pair_place.tcl"), kd / "reset_pair_place.tcl")
    if macros:     # S81-P8 10-23: soft relay stations on their source-sink lines (relay_mid.tcl, after face_flops)
        shutil.copyfile(Path(__file__).with_name("relay_mid.tcl"), kd / "relay_mid.tcl")
        if _gutter_block_um(P.budgets, tn):     # S81-TYPES-5 11-07 NARROW-GUTTER class (opt-in)
            shutil.copyfile(Path(__file__).with_name("gutter_block.tcl"), kd / "gutter_block.tcl")
            shutil.copyfile(Path(__file__).with_name("gutter_release.tcl"), kd / "gutter_release.tcl")
        # DIE-HEAD-69 11-05 (COORD ruling (1), hd_tile flt_q): core-output landing flops at their pins (core_out_land.tcl)
        shutil.copyfile(Path(__file__).with_name("core_out_land.tcl"), kd / "core_out_land.tcl")
    # R3: ft station table for face_flops.tcl: slot, stations, in face (route leg order), optional regs_um sites
    ft = ["# slot stations in_face out_face [x y ...]  (GENERATED; type frame um)"]
    for s_ in t.get("ft_slots", []):
        regs = " ".join(f"{_um(x)} {_um(y)}" for x, y in s_.get("regs_um", []))
        ft.append(f"{s_['name']} {int(s_.get('stations', 1)) + S.built_station_extra(P.raw, tn, s_['name'])} {s_.get('in_face', 'W')} {s_.get('out_face', 'E')} "
                  f"{regs}".rstrip())
    (kd / "ft_stations.txt").write_text("\n".join(ft) + "\n")
    from ft_bit_sites import table as ft_bit_sites_table
    # TYPE-SAFE-2 11-06 (OWNER 18:5x, COORD 19:2x (4a)): gen-time ft station spread (ft_spread.py docstring): a slot
    # with station points but no per-bit sites gets a bit column across its bundle at each planned station instead of
    # the ff_put_near clump; stations, hops, RTL and LEC unchanged.  Default on; partition_types.<t>.ft_spread false
    # = the plan sites only.  ft_track_use.json: advisory track-use report (never a gate).
    import ft_spread
    try:
        ft_kit_slots, ft_spread_ledger = ft_spread.spread_type(P, tn, t)
    except Exception as ex:                  # the spread is a form improvement, never a gen failure: plan sites only
        ft_kit_slots = list(t.get("ft_slots", []) or [])
        ft_spread_ledger = [dict(form="clump", reason=f"ft_spread error {type(ex).__name__}: {ex}")]
        print(f"[gen] {tn}: FT_SPREAD ADVISORY {type(ex).__name__}: {ex} (plan sites only)")
    (kd / "ft_bit_sites.tcl").write_text(ft_bit_sites_table(ft_kit_slots))
    if ft_kit_slots:
        try:                                 # advisory report only: never a gen failure
            (kd / "ft_track_use.json").write_text(json.dumps(dict(ft_spread.track_use(ft_kit_slots, ft_spread_ledger),
                                                                  type=tn, spread=ft_spread_ledger), indent=1) + "\n")
        except Exception as ex:
            print(f"[gen] {tn}: FT_TRACK_USE ADVISORY {type(ex).__name__}: {ex}")
    ff_core_taps = {r[0]: r for r in core_tap_rows(P, tn, "FF")}
    budget_grid_count, budget_taps = budget_tap_rows(P, tn)
    bud = dict(schema="opentallas.die_plan.partition_budget.v1", die=P.name, type=tn, module=t["module"],
               outline_um=[w, h], period_ps=P.die["period_ps"], pins=len(pins),
               signal_max=top,
               clock=dict(tap_um=t.get("clock", {}).get("tap_um"), insertion_ps=ib["tt"], insertion_ff_ps=ib["ff"],
                          insertion_basis=ib["basis"], parent_early_tap_ps=ib["early_tap_ps"],
                          common_latency_ps=P.clock["insertion_ps"],
                          insertion_tol_ps=P.clock["insertion_tol_ps"],
                          # one clock port per tap (snapped): the R4 grid first, then any ADDED sink-anchored taps
                          tap_mode=t.get("clock", {}).get("tap_mode", "grid"),
                          tap_pitch_um=S.tap_pitch(P, tn),
                          grid_taps=budget_grid_count,
                          taps=budget_taps,
                          sink_taps=(T.report(P, tn)["taps"] if S.sink_tap_mode(t) else []),
                          taps_snapped=clock_tap_pin_metadata(P, tn),
                          core_taps=[dict(port=n, inst=i, pin=p_, early_ps=e, insertion_ps=ins,
                                          early_ff_ps=ff_core_taps[n][3], insertion_ff_ps=ff_core_taps[n][4])
                                     for n, i, p_, e, ins in clat["taps"]],
                          uncertainty_split=UNC_SPLIT),
               core_latency=clat["rows"],
               pin_reg_p90_um=P.budgets["pin_reg_p90_um"], io_budget=IO_BUDGET,
               instances=[n for n, p in P.parts.items() if p["type"] == tn])
    # Private explicit actual-LEF entry access. Default budget bytes remain unchanged.
    for row in bud["clock"]["core_taps"]:
        core = next((c for c in t.get("hard_cores", []) if c["inst"] == row["inst"]), None)
        if core and core.get("clock_entry_access"):
            if row["pin"] != core["clock_entry_access"]["pin"]:
                raise ValueError("clock entry access pin differs from core tap")
            row["clock_entry_access"] = core["clock_entry_access"]
    # FLOW-11 10-30 (DIE-KV-48-CLK (b)): the type's PHY-edge clock pins (plan clock.edge_clocks, snapped like taps,
    # placed by tap_pins) are plan clock pins too; kit_contract clock_pin_geometry checks them like taps_snapped.
    # No edge clock: no key (byte-identical budget.json).
    _ec = edge_clock_pins(P, tn)
    if _ec:
        bud["clock"]["edge_clocks"] = [dict(name=n, xy=[x, y], period_mult=m) for n, x, y, m in _ec]
    # DH56-IOHP 11-03: a plan clock.ring_hold kit takes the measured sender min on its forwarded ring inputs
    # (sdc_lint._io_hold_ctx hold_in_min_ports_ps), so signoff.py applies the same parent obligation; without the plan
    # digest here that obligation could never be met (io_hold_qualification: 'parent plan differs').
    ring_a = ring_hold_obligation(P, tn)
    if ioh or ring_a:
        from io_hold_qualification import plan_digest
        bud['io_hold'] = dict(mode='sender_min',plan_sha256=plan_digest(P.raw),requires_parent=True)
        if not ioh:
            bud['io_hold']['kind'] = 'ring_hold'
        if ioh and io_hold_mode(P, tn) == 'plan_demand':
            hd = P.clock['hold_demand']
            bud['io_hold'].update(mode='plan_demand', hold_demand=dict(
                derate=hd.get('derate'), cell=hd.get('cell'), windows_ps=hd.get('windows_ps'),
                pairs=len(hd.get('pairs') or {}), landed=len(hd.get('landed') or ())))
    _dsd = die_sta_hold_demand(P, tn)
    if _dsd:
        hd = P.clock['hold_demand']
        bud['hold_demand_die_sta'] = dict(
            file=hd['file'], sha256=hd['sha256'], gate_json_sha256=hd['gate_json_sha256'], tool_sha256=hd['tool_sha256'],
            input_bits=sum(1 for b in _dsd['inputs'].values() for v in b.values() if v[0]),
            output_bits=sum(1 for b in _dsd['outputs'].values() for v in b.values() if v[0]),
            hb4_cells=sum(v[0] for side in ('inputs', 'outputs') for b in _dsd[side].values() for v in b.values()))
    if ms is not None:
        bud["master_plan"] = ms
    if bump_ports:
        bud["bump_ports"] = [dict(b) for b in bump_ports]
    (kd / "budget.json").write_text(json.dumps(bud, indent=1) + "\n")
    shutil.copyfile(Path(__file__).with_name("pin_audit.py"), kd / "pin_audit.py")
    shutil.copyfile(Path(__file__).with_name("native_pin_contract.py"), kd / "native_pin_contract.py")
    # CP1-R10 / COORD 10-24: boundary-register guard on the Yosys netlist (run_kit.sh, right after synth)
    shutil.copyfile(Path(__file__).with_name("face_guard.py"), kd / "face_guard.py")
    shutil.copyfile(Path(__file__).with_name("hard_landing.py"), kd / "hard_landing.py")
    shutil.copyfile(Path(__file__).with_name("selrange_gate.py"), kd / "selrange_gate.py")
    shutil.copyfile(Path(__file__).with_name("native_bb.py"), kd / "native_bb.py")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "orfs_hold_mm.py", kd / "orfs_hold_mm.py")
    # FLOW-CANARY / COORD 10-25: register fanout gate right after face_guard (kv3_astk B: Yosys merged replicas -> 2048 loads)
    shutil.copyfile(Path(__file__).with_name("reg_fanout_gate.py"), kd / "reg_fanout_gate.py")
    for helper in ("port_bind_gate.py", "hold_gate.tcl"):
        shutil.copyfile(Path(__file__).with_name(helper), kd / helper)
    # LEC 10-24: RTL vs synthesised netlist equivalence (run_kit.sh, right after face_guard; NOT EQUIVALENT stops)
    shutil.copyfile(Path(__file__).with_name("lec.py"), kd / "lec.py")
    # FLOW-21 / COORD 11-01: the pre-route LEC runs beside place/CTS/route (lec_async.sh, OT_LEC_ASYNC=0 = inline)
    shutil.copyfile(Path(__file__).with_name("lec_async.sh"), kd / "lec_async.sh")
    shutil.copyfile(Path(__file__).with_name("lec_completed_transfer.py"), kd / "lec_completed_transfer.py")
    shutil.copyfile(Path(__file__).with_name("lec_completed_reference.py"), kd / "lec_completed_reference.py")
    import core_flow; core_flow.stage_grt183(kd)   # FLOW-28 11-04: GRT-0183 fresh-process re-run (run_kit.sh)
    shutil.copyfile(Path(__file__).with_name("adder_map_dontuse.py"), kd / "adder_map_dontuse.py")   # ruling 4 (10-25)
    for f in ("face_keep.tcl", "face_keep_release.tcl"):   # CP1-R10 (restored: lost in main merge 0ce45ab03c)
        shutil.copyfile(Path(__file__).with_name(f), kd / f)
    # Copy the current shared hook and its conditional helpers beside each generated kit.
    for f in KEEP_REGS_HOOK:
        shutil.copyfile(_common_flow_file(f, Path(__file__).resolve().parents[2]), kd / f)
    # SIGNOFF 10-24: uniform sign-off as the final kit-flow step (run_kit.sh after route): signoff.py + its helpers
    from signoff import copy_signoff_bundle
    copy_signoff_bundle(kd, extra=("kit_preflight.py", "legacy_gate.py", "core_clock_band.py"))
    # CRASH-TRIAGE 10-25: 6_report PDNSim IR is deferred out of the route container (partition_ir.py patch +
    # OT_DEFER_PARTITION_IR=1 in run_kit.sh).  10 autopilot CRASH rows (kv3_io_ft/_v1 x8, coll_ftm x2) were killed
    # at the memory cap (25/33/50 GB at --mem 24/32/48) inside analyze_power_grid AFTER 6_final.odb/.spef existed.
    # IR stays NOT_RUN for the kit; partition_ir.py sidecar KIT --mem-gb 64 runs it as its own admitted job.
    shutil.copyfile(Path(__file__).with_name("partition_ir.py"), kd / "partition_ir.py")
    (kd / "pins.json").write_text(json.dumps([dict(bus=b, bit=i, layer=l, x=x, y=y, face=f)
                                              for b, i, l, x, y, f in pins]) + "\n")
    # face buses = planned pins + the type's declared landing-contract inputs (cland_dn_ready_/fault_<n> monitor rings)
    lc_in = {str(x["name"]) for x in P.types[tn].get("clock", {}).get("landing_contract", {}).get("pins", [])
             if x.get("dir") == "in" and x.get("kind") != "clock"}
    plain = plain_ring_land_slots(kd / "rtl", {b for b, *_ in pins} | lc_in) if plain_rings else {}
    if plain:                                   # DIE-S81-26: plain forwarded-clock rings (S81 stations), merged
        from clock_landings import LAND_SLOTS_SCHEMA
        land_slots = dict(land_slots or {"schema": LAND_SLOTS_SCHEMA, "buses": {}})
        clash = sorted(set(plain) & set(land_slots.get("buses", {})))
        if clash:
            import gen_rtl
            raise gen_rtl.GenError(f"type {tn}: buses declared by both the landing sidecar and a plain ring: {clash[:5]}")
        land_slots["buses"] = {**land_slots.get("buses", {}), **plain}
    land_slots = export_land_slots(P.types[tn], land_slots)
    if land_slots is not None:
        import hard_landing
        land_slots = hard_landing.emit(t, land_slots, kd,
                                      Path(root) if root else Path(__file__).resolve().parents[2])
    if land_slots is not None:                  # face_guard reads it beside pins.json (count-aligned landing rings)
        (kd / "land_slots.json").write_text(json.dumps(land_slots, indent=1) + "\n")
    port_pins = port_bind_pin_records(P, tn, pins, bump_ports)
    (kd / "port_bind_pins.json").write_text(json.dumps(port_pins, indent=1) + "\n")
    if spare_out:                               # DIE-S81-46: declared spare-out bits (kit_rtl.json), face_guard
        from face_guard import SPARE_SCHEMA
        (kd / "spare_out.json").write_text(json.dumps(dict(schema=SPARE_SCHEMA, bits=list(spare_out)), indent=1) + "\n")
    if dead_inputs:                             # DIE-S81-51/SPARE: narrow plan input bits kit-rtl leaves unconnected
        (kd / "dead_inputs.json").write_text(json.dumps(dead_inputs, indent=1) + "\n")
    declared_straps = logical_strap_names(t)
    if declared_straps:
        # Logical declaration is required by synthesis/LEC gates even before physical strap sites are planned.
        # Missing sites remain absent from pins.json and keep their ordinary physical qualification obligations.
        (kd / "straps.json").write_text(json.dumps(dict(straps=declared_straps), indent=1) + "\n")
    private_clock_pins, private_clock_info = [], None
    if private_clock_mesh is not None:
        if not trial:
            raise ValueError("private historical clock source requires explicit --trial")
        import hhp_clock_mesh_role as HMR
        private_clock_pins, private_clock_info = HMR.install_generated_partition(kd, private_clock_mesh, tn, macros)
        bud["native_infrastructure"] = dict(pins=len(private_clock_pins), arcs=4, data_cycles_added=0,
            role="exact private intentional clock mesh", qualification="HOLD: actual HEAD joins and timing not run")
        (kd / "budget.json").write_text(json.dumps(bud, indent=1) + "\n")
    import infra_rtl as IR
    infra = IR.type_ports(t)
    if infra:
        if private_clock_mesh is not None:
            raise ValueError("private native clock cut cannot mix with generic infrastructure ports")
        import ft_ports as FT
        decl = FT.declaration(t.get("infra_arcs", []), f"die plan {P.name} type {tn}: explicit native hard-core interfaces")
        if {p["name"] for p in infra} != {p["name"] for p in decl["ports"]}:
            raise ValueError("native infrastructure ports/arcs disagree")
        FT.install(kd, decl)
        (kd / "infra_ports.json").write_text(json.dumps(infra, indent=1) + "\n")
        bud["native_infrastructure"] = dict(pins=len(infra), arcs=len(decl["arcs"]), data_cycles_added=0, timing="die-timed FT interfaces; actual characterisation required")
        (kd / "budget.json").write_text(json.dumps(bud, indent=1) + "\n")
    from ft_full_stage import install as install_ft_full_stage
    install_ft_full_stage(t, getattr(P, "path", None) or str(Path.cwd()/"plan.json"), kd)
    # HEAD-TILE-C9: reviewed canonical placement, scoped to s81_head hd_tile and guarded by recipe/netlist identity.
    import head_tile_c9
    head_tile_c9.install(P, tn, kd)
    import pregrt_ff_hold
    pregrt_ff_hold.install(t, kd)
    planned_pins = plan_pin_records(P, tn, pins, bump_sites) + private_clock_pins
    # pins.json remains the boundary-flop contract consumed by face_guard.
    # The physical audit also checks all other non-exempt declared ABI pins.
    audit_pins = audit_pin_records(json.loads((kd / "pins.json").read_text()), planned_pins)
    (kd / "audit_pins.json").write_text(json.dumps(audit_pins, indent=1) + "\n")
    prepare_signed_parent_source(P, tn, kd, macros, root)
    write_partition_freeze(P, tn, kd, planned_pins, private_clock_mesh=private_clock_info)
    return kd


def prepare_signed_parent_source(P, tn, kd, macros, root=None):
    # Immutable ordinary helper bundles need no new dependency by default.
    if P.types[tn].get('signed_parent_source') is None:
        return None
    try:
        import signed_parent_adapter
    except ImportError as exc:
        raise ValueError('signed_parent_source opt-in requires staged signed_parent_adapter.py') from exc
    return signed_parent_adapter.prepare_generated_type(P, tn, kd, macros, root)


def type_verilog_defines(t, kit_defines=None):
    """One declared source profile for synthesis, RTL lint and the LEC gold reader.  kit_defines (--kit-rtl,
    kit_rtl_defines): the as-built defines the bind elaborated the bound partition with, after the plan's own."""
    values = t.get("verilog_defines", [])
    if isinstance(values, list) and kit_defines:
        values = values + list(kit_defines)
    if not isinstance(values, list) or any(not isinstance(v, str) or
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in values):
        raise ValueError("type verilog_defines must be a list of bare Verilog macro names")
    return list(dict.fromkeys(["-DSYNTHESIS"] + ["-D" + v for v in values]))


def install_gp_noconverge_gate(kd, cfg):
    """KW-FIX-44 PLACE-NOCONVERGE (COORD 11-10): PRE_RESIZE_TCL gate that ends the run at place when global placement
    stopped at the Nesterov iteration cap (GPL-1010) above overflow 0.1, before resize and DPL spend hours on it.
    The kit keeps a PRE_RESIZE_TCL of its own (no gate then); OT_GPL_NOCONV = 0 in the kit config turns the gate off."""
    if any(re.match(r"\s*(?:override\s+)?export\s+PRE_RESIZE_TCL\b", c) for c in cfg):
        return []
    here = Path(__file__).resolve().parent
    shutil.copyfile(here / "gp_noconverge_gate.tcl", kd / "gp_noconverge_gate.tcl")
    shutil.copyfile(here.parent / "autopilot" / "gp_noconverge.py", kd / "gp_noconverge.py")
    return ["# KW-FIX-44 PLACE-NOCONVERGE: GPL at its iteration cap with overflow > 0.1 ends the run before resize",
            "export PRE_RESIZE_TCL = /work/gp_noconverge_gate.tcl"]


RUN_KIT = r"""#!/bin/bash
# GENERATED by gen.py phys. Pre-floorplan gates fail closed. CTS is measured at
# FF before hold repair; structural failures return before global/detail route.
# grt is a measurement screen through standard GRT repair/policy, never DRT, abstract or signoff.
# Heavy: run_kit.sh KITDIR [GOAL=route] [MEM_GB=16] [CPUS=8] through ot-run.
# Kit IR (CRASH-TRIAGE 10-25): 6_report PDNSim is deferred (partition_ir.py; IR NOT_RUN in the kit, run it with
# partition_ir.py sidecar KIT --mem-gb 64 --threads 8).  OT_KIT_IR=inline restores the in-route analysis.
# LEC (10-24): lec.py proves the Yosys netlist equivalent to the kit RTL read with the OTHER HDL frontend, right after
# face_guard: NOT EQUIVALENT stops the kit; UNPROVEN / tool error is a warning in lec/lec.json.  FLOW-21 11-01: by
# default it runs beside place/CTS/route (lec_async.sh) and a NOT EQUIVALENT stops the route where it is.
# Gate exit codes (classify by the FAIL_PREFLOOR / FAIL_POSTCTS marker text): 3 selrange, 4 FF structural hold gate,
# 5 LEC NOT EQUIVALENT, 6 pre-route insertion gate (FLOW 10-25), 7 reg_fanout (FLOW-CANARY 10-25: register > 64 data
# loads on the Yosys netlist = replicas merged by Yosys); other non-zero = sdc_lint / face_guard / flow step rc.
# KW-FIX-4 11-03 (COORD 12:01): an OpenROAD crash in the GRT-RC tap pre-pass (tapbal_grt.tcl; 'Signal N received', e.g.
# the SIGABRT in sta::RequiredCmp::requiredSet on HEAD hd_st_str / hd_st_n3_transit) is a tool failure, not a design
# verdict: 4_cts.odb is restored from the pre-pass copy and the kit takes the plain GRT path (OT_TAPBAL_FALLBACK line,
# tapbal_fallback.log).  'export OT_TAPBAL_FALLBACK = 0' in config.mk keeps the old FAIL_POSTCTS stop.
# KW-FIX-4/BAND 11-03 (OWNER 19:12, all dies): the pre-route insertion gate (post-CTS gate TT/FF on 5_1_grt.odb) is
# ADVISORY: a FAIL line prints OT_POSTCTS_ADVISORY (postcts_advisory.log), no FAIL_POSTCTS / rc 6, the kit routes on and
# signoff.py records the band as signoff.json insertion_band.  'export OT_POSTCTS_BAND_GATE = 1' restores the stop.
# The FF structural hold gate (OT_HOLD_GATE, rc 4) is unchanged.
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-16}; CPUS=${4:-8}
# RESYNTH-GUARD block: a refusal check only, no physical step, so it stays outside the resume runner fingerprint  # KWRS-BEGIN
# KW-FIX-32 RESYNTH-GUARD (COORD 20:2x, DIE-QC-91 20:15): a kit assembled by copying stage checkpoints (cp -p keeps the
# old mtimes) re-synthesises under a make-chain goal when config.mk / sdc / rtl are newer than the restored results, so
# the proved netlist silently changes inside the same kit.  Kits that restored results and have no stage-resume plan
# (resume.json = the do-* path) refuse instead; fresh kits (no results yet) and GOAL=synth are unchanged.
if [ "$GOAL" != synth ] && [ "${OT_ALLOW_RESYNTH:-0}" != 1 ] && [ ! -f "$K/resume.json" ]; then
  RG_O=$(ls -tr "$K"/run/results/asap7/*/base/1_*.v "$K"/run/results/asap7/*/base/[2-5]_*.odb 2>/dev/null | head -1)
  if [ -n "$RG_O" ]; then
    RG_N=$(find "$K/config.mk" "$K"/*.sdc "$K/rtl" -type f -newer "$RG_O" 2>/dev/null | head -3 | tr '\n' ' ')
    if [ -n "$RG_N" ]; then
      echo "RESYNTH-GUARD: make goal $GOAL would rebuild from synth: ${RG_N}newer than the restored $(basename "$RG_O"); drive this kit with do-* targets (or OT_ALLOW_RESYNTH=1 to rebuild it)" >&2
      exit 12
    fi
  fi
fi
# KWRS-END
if [ -f "$K/signed_parent_source.json" ]; then
  if [ "$GOAL" = synth ] && [ "${OT_SIGNED_PARENT_PREP_SYNTH:-0}" = 1 ]; then
    [ -f "$K/signed_parent_synth_prep.sh" ] || { echo 'HELD: missing explicit SYNTH-only PREP helper'; exit 78; }
    exec bash "$K/signed_parent_synth_prep.sh" "$K" "$MEM" "$CPUS"
  fi
  echo 'HELD: signed parent source PREP; native-parent expanded-child EQ and actual flattened parent/die census required'
  exit 78
fi
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=dpkit-$(basename "$K")-$$
# GRT-PATCH-1 11-11 (OWNER 01:1x/01:2x halving-off parallel arm, opt-in): K/grt_transition_mode (written at gen from the  # GRTM
# gen env OT_GRT_TRANSITION_MODE, e.g. kit_wave item_env) or the host env selects the patched router image for the ORFS  # GRTM
# main run ONLY (OpenROAD 6cb3f2b704 + transition-layer mode; image unset-env = stock behaviour) and passes the mode.  # GRTM
# LEC and sign-off keep $IMAGE.  No mode: GIMAGE=$IMAGE and GRTD is empty, so the main run is the stock run.  # GRTM
GIMAGE=$IMAGE; GRTD=(); GRTM=${OT_GRT_TRANSITION_MODE:-$(head -1 "$K/grt_transition_mode" 2>/dev/null)}  # GRTM
if [ -n "$GRTM" ]; then  # GRTM
  case "$GRTM" in off|edge|edge_outline) ;; *) echo "FAIL_PREFLOOR grt transition mode '$GRTM' (off|edge|edge_outline)" | tee -a "$K/FAIL_PREFLOOR"; exit 10;; esac  # GRTM
  GIMAGE=${OT_GRT_IMAGE:-opentallas/orfs:asap7lock-grtoff}  # GRTM
  GID=$(${OT_DOCKER:-docker} image inspect --format '{{.Id}}' "$GIMAGE" 2>/dev/null) && [ -n "$GID" ] || { echo "FAIL_PREFLOOR grt transition image $GIMAGE missing on $(hostname)" | tee -a "$K/FAIL_PREFLOOR"; exit 10; }  # GRTM
  GRTD=(-e OT_GRT_TRANSITION_MODE="$GRTM")  # GRTM
  printf '{"mode": "%s", "image": "%s", "image_id": "%s", "goal": "%s"}\n' "$GRTM" "$GIMAGE" "$GID" "$GOAL" > "$K/grt_transition.json"  # GRTM
  echo "GRTM mode $GRTM image $GIMAGE $GID"  # GRTM
fi  # GRTM
# KW-RESUME-1 OT_STAGE_RESUME_V1: K/resume.json (kit_wave.py stage resume) names the first ORFS step to run; the  # KWRS
# steps before it are hardlinked from the previous attempt.  Every make call then goes through kwrs_make.sh, which  # KWRS
# skips the reused steps and runs the later ones as dependency-free do-* targets (a make dependency check would  # KWRS
# rebuild the reused files and write through the links).  Gates always re-run.  All edits are '# KWRS' lines, the  # KWRS
# KWRS-BEGIN/END block and the ${KWRS_M} token: without them this is the runner without stage resume.  # KWRS
RS=0; KWRS_M=  # KWRS
if [ -f "$K/resume.json" ]; then  # KWRS
  RS=$(python3 -I -c 'import json,sys; print({"floorplan":1,"place":2,"cts":3,"grt":4,"route":5}[json.load(open(sys.argv[1]))["start"]])' "$K/resume.json") || { echo 'FAIL_PREFLOOR stage resume: resume.json unreadable' | tee -a "$K/FAIL_PREFLOOR"; exit 10; }  # KWRS
  case "$GOAL" in floorplan|place|cts|grt|route) ;; *) echo "FAIL_PREFLOOR stage resume: goal $GOAL unsupported" | tee -a "$K/FAIL_PREFLOOR"; exit 10;; esac  # KWRS
  cat > "$K/kwrs_make.sh" <<'KWRS_MAKE'  # KWRS-BEGIN
#!/bin/bash
# kwrs_make.sh RS make VAR=.. TARGET..: stage-resume make filter (generated by run_kit.sh from K/resume.json)
RS=$1; shift; prog=$1; shift; vars=(); tg=(); out=()
for a in "$@"; do case "$a" in *=*) vars+=("$a");; *) tg+=("$a");; esac; done
# KW-FIX-30 11-07 (DIE-KV-89 Wi: PLACE never ran): the done list was /work/.kwrs_done.<parent pid>, and that pid is 1 in every
# container, so a kit copied with an older run's list (spill/back-copy/hand copy) skipped those steps.  Now: the list is
# keyed by this kit's resume.json (r<cksum>; .kwrs_done.<digits> of old runners are never read), a step is written to it
# only after its make call returned 0, and a listed step counts as done only while its stage output is in run/results.
D=${KWRS_DONE:-/work/.kwrs_done.r$(cksum < /work/resume.json 2>/dev/null | cut -d" " -f1)}; touch "$D"
W=$(dirname "$D"); B=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
outf() { case "$1" in do-floorplan) echo 2_floorplan.odb;; do-place) echo 3_place.odb;; do-cts) echo 4_cts.odb;; do-grt) echo 5_1_grt.odb;;
  do-5_2_route) echo 5_2_route.odb;; do-5_3_fillcell) echo 5_3_fillcell.odb;; do-5_route) echo 5_route.odb;; do-5_route.sdc) echo 5_route.sdc;; esac; }
done_ok() { local f; grep -qx -- "$1" "$D" || return 1; f=$(outf "$1"); [ -n "$f" ] && [ -n "$B" ] && [ -s "$B/$f" ]; }
# KW-FIX-22 11-06 (S81-RCK-2): a stage target runs every not-reused step up to it, as plain make would through its
# dependencies (start floorplan + goal route called only '$M cts' -> do-cts without do-floorplan/do-place, 3_place.odb
# missing).  Steps already run in this runner are skipped through the done list.
up() { local n=$1 s; local st=(x do-floorplan do-place do-cts do-grt); for s in 1 2 3 4; do [ "$s" -le "$n" ] && [ "$s" -ge "$RS" ] && echo "${st[$s]}"; done; true; }
for t in "${tg[@]}"; do
  case "$t" in
    synth) m=;;
    floorplan) m=$(up 1);;
    place) m=$(up 2);;
    cts) m=$(up 3);;
    grt) m=$(up 4);;
    route) m="$(up 3) do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc";;
    run) m=run; [ "$RS" -ge 4 ] && printf '%s\n' "${vars[@]}" | grep -q '^RUN_SCRIPT=.*tapbal_grt.tcl$' && m=;;
    do-*|print-*) m=$t;;
    *) echo "STAGE_RESUME make target $t unsupported on a resumed kit" >&2; exit 10;;
  esac
  for x in $m; do
    case "$x" in do-floorplan|do-place|do-cts|do-grt|do-5_*) done_ok "$x" && continue;; esac
    case " ${out[*]} " in *" $x "*) continue;; esac
    out+=("$x")
  done
  [ -n "$m" ] || echo "STAGE_RESUME skip make $t (reused step, start step $RS)"
done
[ "${#out[@]}" -gt 0 ] || exit 0
echo "STAGE_RESUME make ${out[*]}"
$prog "${vars[@]}" "${out[@]}"; rc=$?
if [ "$rc" = 0 ]; then for x in "${out[@]}"; do case "$x" in do-floorplan|do-place|do-cts|do-grt|do-5_*) grep -qx -- "$x" "$D" || echo "$x" >> "$D";; esac; done; fi
exit $rc
KWRS_MAKE
# KWRS-END
  KWRS_M="M=\"bash /work/kwrs_make.sh $RS \$M\"; "  # KWRS
  echo "STAGE_RESUME start step $RS ($(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(",".join(d["reused_steps"]), "from", d["source"]["host"]+":"+d["source"]["kit"])' "$K/resume.json"))"  # KWRS
fi  # KWRS
# KW-FIX-5 11-04: see kwrs_busfit.py below; fit libs in K/.busfit are read by OpenROAD once a stage ODB exists.  # KWRS
cat > "$K/kwrs_busfit.py" <<'KWRS_BUSFIT'  # KWRS-BEGIN
#!/usr/bin/env python3
# kwrs_busfit.py (KW-FIX-5 11-04, generated by run_kit.sh): a child LEF can carry pins its module does not have (hcpost_lane_pr
# r0[15:0], rxsf o_u[31]).  They have no liberty port and OpenSTA all_registers -clock_pins segfaults on them.  fit writes
# K/.busfit/<lib> with those pins added, direction only and NO timing arcs; K/macros stays as it is, because Yosys and LEC read
# it and a wider bus there would bind the black box to the wrong bits.  patch wraps read_liberty from ORFS util.tcl, in OpenROAD
# only (not Yosys), once a stage ODB exists, so nothing links a netlist against a fit lib.  No fit file is written when LEF and lib agree.
import hashlib, json, os, re, shutil, sys, tempfile
BUS = re.compile(r"^([^\[\]]+)\[(\d+)\]$")
def lef_macros(text):
    out = {}
    for m in re.finditer(r"^\s*MACRO\s+(\S+)(.*?)^\s*END\s+\1\s*$", text, re.M | re.S):
        pins = {}
        for p in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", m.group(2), re.M | re.S):
            if re.search(r"^\s*USE\s+(POWER|GROUND)\b", p.group(2), re.M):
                continue
            d = re.search(r"^\s*DIRECTION\s+(\w+)", p.group(2), re.M)
            pins[p.group(1).replace("\\", "")] = (d.group(1).lower() if d else "input")
        out[m.group(1)] = pins
    return out
def close_of(t, i):
    # index of the } closing the { at t[i]
    depth, q = 0, False
    while i < len(t):
        c = t[i]
        if c == '"':
            q = not q
        elif not q:
            if t.startswith("/*", i):
                i = t.index("*/", i) + 1
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise ValueError("unbalanced liberty group")
def group(t, kind, name):
    return re.search(r"\b%s\s*\(\s*\"?%s\"?\s*\)\s*\{" % (kind, re.escape(name)), t)
def bus_range(t, s, e):
    m = re.search(r"\bbus_type\s*:\s*\"?(\w+)\"?\s*;", t[s:e])
    if not m:
        return None, None, None
    ty = group(t, "type", m.group(1))
    if not ty:
        return m.group(1), None, None
    b = t[ty.end():close_of(t, ty.end() - 1)]
    f, o = re.search(r"bit_from\s*:\s*(\d+)", b), re.search(r"bit_to\s*:\s*(\d+)", b)
    return m.group(1), int(f.group(1)), int(o.group(1))
def present(t):
    have = set(re.findall(r"\bpin\s*\(\s*\"?([^\")\s]+)\"?\s*\)\s*\{", t))
    for m in re.finditer(r"\bbus\s*\(\s*\"?(\w+)\"?\s*\)\s*\{", t):
        _, f, o = bus_range(t, m.end(), close_of(t, m.end() - 1))
        if f is not None:
            have |= {f"{m.group(1)}[{i}]" for i in range(min(f, o), max(f, o) + 1)}
    return have
def pin_text(name, d):
    return f'    pin("{name}") {{\n      direction : {d};\n      capacitance : 0.0000;\n    }}\n'
def type_text(name, f, o):
    return (f'  type ("{name}") {{\n    base_type : array;\n    data_type : bit;\n    bit_width : {abs(f - o) + 1};\n'
            f'    bit_from : {f};\n    bit_to : {o};\n  }}\n')
def fit_text(t, pins):
    # -> (liberty text with every missing pin of the LEF pin map added, sorted names added)
    c = re.search(r"\bcell\s*\(\s*\"?[^\")\s]+\"?\s*\)\s*\{", t)
    have = present(t)
    miss = {n: d for n, d in pins.items() if n not in have}
    buses, added = {}, sorted(miss)
    # Textual timed members can already exist outside the declared bus range.
    # Visit every physical LEF bit, while adding pin bodies only when missing.
    for n, d in pins.items():
        m = BUS.match(n)
        if m:
            buses.setdefault(m.group(1), {})[int(m.group(2))] = d
    for n, d in miss.items():
        if not BUS.match(n):
            e = close_of(t, c.end() - 1)
            t = t[:e] + pin_text(n, d) + t[e:]
    for name, bits in sorted(buses.items()):
        g = group(t, "bus", name)
        body = "".join(pin_text(f"{name}[{i}]", bits[i]) for i in sorted(bits, reverse=True)
                       if f"{name}[{i}]" in miss)
        if not g:
            if not body:
                continue
            f, o = max(bits), min(bits)
            e = close_of(t, c.end() - 1)
            ty = f"{name}_busfit"
            d = next(iter(bits.values()))
            t = (t[:e] + type_text(ty, f, o) + f'  bus("{name}") {{\n    bus_type : {ty};\n    direction : {d};\n' + body + "  }\n" + t[e:])
            continue
        s, e = g.end(), close_of(t, g.end() - 1)
        ty, f, o = bus_range(t, s, e)
        if f is None:
            raise ValueError(f"bus {name}: no bit range")
        lo, hi = min(f, o, *bits), max(f, o, *bits)
        nf, no = (hi, lo) if f >= o else (lo, hi)
        if not body and (nf, no) == (f, o):
            continue
        t = t[:e] + body + t[e:]
        new = f"{name}_busfit"
        t = t[:s] + re.sub(r"\bbus_type\s*:\s*\"?\w+\"?\s*;", f"bus_type : {new};", t[s:], count=1)
        tg = group(t, "type", ty)
        t = t[:tg.start()] + type_text(new, nf, no).lstrip() + "  " + t[tg.start():]
    return t, added
def fit(k, out=None):
    k = str(k)
    mdir, out = os.path.join(k, "macros"), out or os.path.join(k, ".busfit")
    shutil.rmtree(out, ignore_errors=True)  # never leave a fit from an older lib behind
    macros = {}
    if not os.path.isdir(mdir):
        return {}
    for n in sorted(os.listdir(mdir)):
        if n.endswith(".lef"):
            macros.update(lef_macros(open(os.path.join(mdir, n), errors="replace").read()))
    report = {}
    for n in sorted(os.listdir(mdir)):
        if not n.endswith(".lib"):
            continue
        p = os.path.join(mdir, n)
        raw = open(p, "rb").read()
        sha = hashlib.sha256(raw).hexdigest()
        t = raw.decode(errors="replace")
        c = re.search(r"\bcell\s*\(\s*\"?([^\")\s]+)\"?\s*\)\s*\{", t)
        dst = os.path.join(out, n)
        if not c or c.group(1) not in macros:
            continue
        ft, added = fit_text(t, macros[c.group(1)])
        if ft == t:
            continue
        os.makedirs(out, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=out)
        with os.fdopen(fd, "w") as f:
            f.write(f"/* OT_BUSFIT lib_sha256 {sha} */\n" + ft)
        os.chmod(tmp, 0o664)
        os.replace(tmp, dst)
        report[n] = {"added": added, "lib_sha256": sha}
    if report:
        with open(os.path.join(out, "report.json"), "w") as f:
            json.dump(report, f, indent=1)
    return report
PROC = "\n".join((
    'if { [llength [info commands ::sta::worst_slack_cmd]] && ![llength [info commands ::ot_busfit_read_liberty]] } {',
    '  rename ::read_liberty ::ot_busfit_read_liberty',
    '  proc ::read_liberty { args } {',
    '    if { [info exists ::env(RESULTS_DIR)] && [llength [glob -nocomplain $::env(RESULTS_DIR)/*.odb]] } {',
    '      set g /work/.busfit/[file tail [lindex $args end]]',
    '      set f [lindex $args end]',
    '      if { [file exists $g] && [file exists $f] } {',
    '        set c [open $g]; gets $c h; close $c',
    '        if { [string first [lindex [exec sha256sum -- $f] 0] $h] >= 0 } { set args [lreplace $args end end $g] }',
    '      }',
    '    }',
    '    uplevel 1 [list ::ot_busfit_read_liberty {*}$args]',
    '  }',
    '}',
    ""))
def patch(path):
    t = open(path).read()
    if "ot_busfit" in t:
        return
    open(path, "w").write(t.rstrip("\n") + "\n" + PROC)
if __name__ == "__main__":
    if sys.argv[1] == "fit":
        r = fit(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print("OT_BUSFIT", json.dumps({k: len(v["added"]) for k, v in r.items()}))
    elif sys.argv[1] == "patch":
        patch(sys.argv[2])
KWRS_BUSFIT
# KWRS-END
python3 -I "$K/kwrs_busfit.py" fit "$K" || echo 'OT_BUSFIT fit failed, macros libs used'  # KWRS
KWRS_F='python3 -I /work/kwrs_busfit.py patch /OpenROAD-flow-scripts/flow/scripts/util.tcl; '  # KWRS
# FLOW-28 11-04: GRT-0183 inside the post-GRT repair gets one fresh-process re-run (physical/common_flow/grt183_make.sh).  # KWRS
KWRS_G="if [ '${OT_GRT183_RESUME:-1}' != 0 ] && [ -f /work/grt183_make.sh ]; then M=\"bash /work/grt183_make.sh \$M\"; fi; "  # KWRS
# Preserve existing gate verdicts when a corrected kit reuses a run directory.
HISTORY="$K/preflight_history/$(date +%Y%m%d_%H%M%S)_$$"
for f in rtl_lint.json sdc_lint.json selrange.json port_bind.json face_guard.json face_guard_odb.json reg_fanout.json; do
  if [ -f "$K/$f" ]; then mkdir -p "$HISTORY"; cp -p "$K/$f" "$HISTORY/$f"; fi
done
# Static checks run before starting the expensive synthesis/route container.
PREFLIGHT="$K/kit_preflight_$(date +%Y%m%d_%H%M%S)_$$.json"
if ! python3 -I "$K/kit_preflight.py" "$K" --out "$PREFLIGHT"; then
  echo 'FAIL_PREFLOOR kit_preflight' | tee -a "$K/FAIL_PREFLOOR"
  exit 10
fi
LEC_SUPERSET_DEFAULT=0
if [ -f "$K/lec_options.json" ]; then
  LEC_SUPERSET_DEFAULT=$(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); assert set(d)=={"superset_vec"} and type(d["superset_vec"]) is bool; print(int(d["superset_vec"]))' "$K/lec_options.json") || { echo 'FAIL_PREFLOOR lec_options' | tee -a "$K/FAIL_PREFLOOR"; exit 10; }
fi
# LEC-IQN proof option forwarding: env wins over the kit's explicit 0/1 selections.
LEC_MATCH_ENV=$(python3 -I - "$K/config.mk" <<'LEC_MATCH_CONFIG'
import os,re,sys
cfg={}
lines=open(sys.argv[1],errors='replace') if os.path.isfile(sys.argv[1]) else ()
for line in lines:
    m=re.match(r'^\s*(?:override\s+)?(?:export\s+)?([A-Z0-9_]+)\s*[:?]?=\s*(.*?)\s*$',line.split('#',1)[0])
    if m:cfg[m[1]]=m[2]
for key in ('OT_LEC_REPLICA_MATCH','OT_LEC_MEM_LANES','OT_LEC_ENABLE_FILL_GUARD'):
    value=os.environ.get(key) or cfg.get(key)
    if not value:continue
    value=value.strip()
    if value not in ('0','1'):raise SystemExit('LEC CONFIG ERROR '+key+' must be 0 or 1')
    print(key+'='+value)
LEC_MATCH_CONFIG
) || { echo 'FAIL_PREFLOOR lec_match_config: OT_LEC_REPLICA_MATCH/OT_LEC_MEM_LANES/OT_LEC_ENABLE_FILL_GUARD must be 0 or 1 (env or config.mk)' | tee -a "$K/FAIL_PREFLOOR"; exit 10; }
LEC_MATCH_DOCKER=()
while IFS= read -r setting; do
  [ -n "$setting" ] || continue
  export "$setting"
  LEC_MATCH_DOCKER+=(-e "$setting")
done <<< "$LEC_MATCH_ENV"
# End LEC-IQN proof option forwarding.
# Explicit proof methods must be implemented by the copied driver, not silently ignored.
LEC_REQUIRED=()
[ "${OT_LEC_REPLICA_MATCH:-0}" = 1 ] && LEC_REQUIRED+=(OT_LEC_REPLICA_MATCH)
[ "${OT_LEC_MEM_LANES:-0}" = 1 ] && LEC_REQUIRED+=(OT_LEC_MEM_LANES)
[ "${OT_LEC_ENABLE_FILL_GUARD:-0}" = 1 ] && LEC_REQUIRED+=(OT_LEC_ENABLE_FILL_GUARD)
[ "${OT_LEC_HINTS_PRESEED:-0}" = 1 ] && LEC_REQUIRED+=(OT_LEC_HINTS_PRESEED)
[ "${OT_LEC_EARLY_COMPARE:-0}" = 1 ] && LEC_REQUIRED+=(OT_LEC_EARLY_COMPARE)
[ "${OT_LEC_SUPERSET_VEC:-$LEC_SUPERSET_DEFAULT}" = 1 ] && LEC_REQUIRED+=(OT_LEC_SUPERSET_VEC)
if [ "${#LEC_REQUIRED[@]}" -gt 0 ]; then
  if ! python3 -I "$K/lec.py" --require-options "${LEC_REQUIRED[@]}"; then
    echo "LEC CONFIG ERROR: copied driver does not support requested options: ${LEC_REQUIRED[*]}" >&2
    echo 'FAIL_PREFLOOR lec_options_unsupported' | tee -a "$K/FAIL_PREFLOOR"
    exit 10
  fi
fi
# FLOW-21 / COORD 11-01 05:1x (closure first): the pre-route LEC no longer gates placement.  The flow container hands
# the LEC command to lec_async.sh at its LEC step and goes straight on to floorplan/place/CTS/route; the LEC runs in its
# admitted flow container (same cgroup).  NOT EQUIVALENT stops the flow container there (FAIL_PREFLOOR LEC NOT EQUIVALENT, rc 5), and
# the kit waits for the LEC verdict before sign-off.  OT_LEC_ASYNC=0 restores the inline LEC; flow + LEC share the admitted memory cap.
export OT_LEC_SUPERSET_VEC="${OT_LEC_SUPERSET_VEC:-$LEC_SUPERSET_DEFAULT}"
LECA=
if { [ "${OT_LEC_ASYNC:-1}" != 0 ] || [ -f "$K/lec_async.on" ] || [ -f "$K/lec_async.identity" ]; } && [ -f "$K/lec_async.sh" ] && [ -f "$K/lec.py" ]; then
  LECA=1; bash "$K/lec_async.sh" start "$K" "$NAME" "$IMAGE" "$MEM" "$CPUS" docker "$GOAL" || exit $?
fi
# KW-FIX-30 11-07 (COORD 15:01 (b), FLOW-CHILD-ETM-CONTEXT from DIE-HBM-87): the GRT clock gate counts a composed child
# ETM only with the parent's flow tag (OT_FLOW_TAG) and the child's signed record (signoff.json, PROVENANCE.json, lec.json at
# the host-absolute paths its view provenance names).  The container saw neither, so such parents could not pass without
# hand edits.  Pass the tag (host env, else K/flow_tag written at gen) and mount each signed child record read-only at its
# own path (KWCHILD).  No provenance sidecar in K/macros = no mount; an unset tag stays unset (the gate says so).
FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}
CHILD_RO=()
while IFS= read -r p; do [ -n "$p" ] && CHILD_RO+=(-v "$p:$p:ro"); done < <(python3 -I - "$K" <<'KWCHILD'
import json, os, sys
from pathlib import Path
K = Path(sys.argv[1]); out = set()
for pf in sorted((K / 'macros').glob('*.provenance.json')):
    try:
        prov = json.loads(pf.read_text())
    except (OSError, ValueError):
        continue
    so = (prov.get('export') or {}).get('signoff')
    if not so:
        continue
    if not os.path.isabs(so):
        so = str((pf.parent / so).resolve())
    rec = Path(so).parent.parent
    if rec.is_dir():
        out.add(str(rec))
    try:
        lec = json.loads((rec / 'PROVENANCE.json').read_text()).get('lec')
    except (OSError, ValueError, AttributeError):
        lec = None
    if lec and os.path.isabs(lec) and Path(lec).exists():
        out.add(str(Path(lec).parent))
k = os.path.realpath(K)
for p in sorted(out):
    r = os.path.realpath(p)
    if r != k and not r.startswith(k + '/') and ':' not in p:
        print(p)
KWCHILD
)
[ ${#CHILD_RO[@]} = 0 ] || echo "KWCHILD read-only child records: ${CHILD_RO[*]}"
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work "${CHILD_RO[@]}" -e OT_FLOW_TAG="$FT" \
  -e HUID=$(id -u) -e HGID=$(id -g) "${LEC_MATCH_DOCKER[@]}" "${GRTD[@]}" -e OT_KIT_IR=${OT_KIT_IR:-defer} -e OT_LEC_HINTS_PRESEED="${OT_LEC_HINTS_PRESEED:-0}" -e OT_LEC_EARLY_COMPARE="${OT_LEC_EARLY_COMPARE:-0}" -e OT_LEC_SUPERSET_VEC="${OT_LEC_SUPERSET_VEC:-$LEC_SUPERSET_DEFAULT}" -w /OpenROAD-flow-scripts/flow "$GIMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; ${KWRS_F}${KWRS_M}${KWRS_G}rc=0; if [ -f /work/orfs_hold_mm.py ] && grep -q 'def patch_intermediate_power' /work/orfs_hold_mm.py; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics.log 2>&1 || { cat /work/orfs_metrics.log; echo 'INTERMEDIATE_POWER optimization unavailable: full power reporting retained'; }; fi; \
  python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl || exit 9; \
  if [ -f /work/partition_ir.py ] && [ \"\$OT_KIT_IR\" = defer ]; then python3 -I /work/partition_ir.py patch /OpenROAD-flow-scripts/flow/scripts && export OT_DEFER_PARTITION_IR=1 || echo 'PARTITION_IR WARNING: patch refused, kit IR runs inline in 6_report'; fi; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR sdc_lint' | tee -a /work/FAIL_PREFLOOR; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/rtl_lint.py /work; rc=\$?; if [ \$rc = 75 ]; then echo 'FAIL_PREFLOOR rtl_lint KILLED (yosys signal, host memory; not a design result)' | tee -a /work/FAIL_PREFLOOR; rc=8; elif [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR rtl_lint (FAIL or NOT RUN)' | tee -a /work/FAIL_PREFLOOR; rc=8; fi; fi; \\\
  SRP=; if [ \$rc = 0 ]; then (python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1; echo \$? > /work/selrange.rc) & SRP=\$!; fi; \
  if [ \$rc = 0 ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR adder_map_dontuse' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist \$(ls /work/run/results/asap7/*/base/1_2_yosys.v | tail -1) --report /work/dont_use_check.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR dont_use_check' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ -n \"\$SRP\" ]; then wait \$SRP; S=\$(cat /work/selrange.rc 2>/dev/null || echo 2); tail -3 /work/selrange.log; if [ \"\$S\" = 75 ]; then echo 'FAIL_PREFLOOR selrange KILLED (yosys signal, host memory; not a design result)' | tee -a /work/FAIL_PREFLOOR; rc=3; elif [ \"\$S\" != 0 ]; then echo 'FAIL_PREFLOOR selrange (FAIL or NOT RUN)' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then python3 -I /work/port_bind_gate.py \"\$N\" /work > /work/port_bind.log 2>&1; rc=\$?; tail -2 /work/port_bind.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR port_bind' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard.py \$N --pins /work/pins.json --out /work/face_guard.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR face_guard' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/reg_fanout_gate.py \$N --out /work/reg_fanout.json > /work/reg_fanout.log 2>&1; rc=\$?; head -12 /work/reg_fanout.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR reg_fanout (register > 64 data loads: merged replicas; or NOT RUN), see reg_fanout.json' | tee -a /work/FAIL_PREFLOOR; rc=7; fi; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; rc=\$?; \
    if [ \$rc = 0 ]; then python3 -I /work/face_guard.py /work/1_synth_odb.v --types-from \$N --pins /work/pins.json --out /work/face_guard_odb.json; rc=\$?; fi; \
    if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR face_guard_odb' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh check-synth /work '$NAME'; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/lec.py ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; } && [ ! -f /work/lec_async.ready ]; then printf '1\\npython3 -I /work/lec.py /work --netlist %s --out /work/lec > /work/lec_run.log 2>&1\\n' \$N > /work/lec_async.ready; echo 'LEC_ASYNC: pre-route LEC runs beside the flow (lec_async.log)'; fi; \
  if [ \$rc = 0 ] && [ -f /work/lec.py ] && [ ! -f /work/lec_async.on ] && [ ! -f /work/lec_async.identity ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json)' | tee -a /work/FAIL_PREFLOOR; rc=5; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = cts ] || [ $GOAL = grt ] || [ $GOAL = route ] || [ $GOAL = finish ]; }; then \
    \$M cts SKIP_CTS_REPAIR_TIMING=1; rc=\$?; \
    if [ \$rc = 0 ] && grep -Eq '^export OT_(TAP_GRT_PRE|PINREG_PAD) = 1' /work/config.mk; then TB=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); [ -z \"\$TB\" ] || cp -p \"\$TB\" /work/4_cts_pretapbal.odb; \
      \$M run RUN_SCRIPT=/work/tapbal_grt.tcl RUN_LOG_NAME_STEM=4_2_tapbal_grt CORNER=TC CORNERS=tc; rc=\$?; \
      TL=\$(ls /work/run/logs/asap7/*/base/4_2_tapbal_grt.log 2>/dev/null | head -1); \
      if [ \$rc != 0 ] && [ -n \"\$TB\" ] && [ -f /work/4_cts_pretapbal.odb ] && [ -n \"\$TL\" ] && ! grep -q '^export OT_TAPBAL_FALLBACK = 0' /work/config.mk && grep -Eq 'Signal [0-9]+ received' \"\$TL\"; then \
        mv -f /work/4_cts_pretapbal.odb \"\$TB\"; echo \"OT_TAPBAL_FALLBACK tapbal_grt.tcl tool crash (rc \$rc: \$(grep -Em1 'Signal [0-9]+ received' \"\$TL\"); \$(grep -Eom1 'sta::[A-Za-z_]+::[A-Za-z_]+' \"\$TL\" | head -1)): 4_cts.odb restored to the CTS result, plain GRT path (no GRT-RC tap pre-pass; crash log kept as /work/4_2_tapbal_grt_crash.log)\" | tee -a /work/tapbal_fallback.log; mv -f \"\$TL\" /work/4_2_tapbal_grt_crash.log; rc=0; fi; \
      rm -f /work/4_cts_pretapbal.odb; \
      if [ \$rc != 0 ]; then echo 'FAIL_POSTCTS GRT-RC tap pre-pass (tapbal_grt.tcl)' | tee -a /work/FAIL_POSTCTS; rc=6; fi; fi; \
    if [ \$rc = 0 ]; then C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc 2>/dev/null | head -1); \
      PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\"\$C\" SDC=\"\$S\" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
        OT_VCLK_TT=\$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk) OT_VCLK_FF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
        OT_HOLD_IN_MIN=\$(sed -n 's/^export OT_HOLD_IN_MIN = //p' /work/config.mk) OT_HOLD_OUT_MIN=\$(sed -n 's/^export OT_HOLD_OUT_MIN = //p' /work/config.mk) \
        OT_TAP_WINDOW=\$(sed -n 's/^export OT_TAP_WINDOW = //p' /work/config.mk) \
        OT_HOLD_STOP_PS=\$(sed -n 's/^export OT_HOLD_STOP_PS = //p' /work/config.mk) \
        LAYER_PARASITICS_FILE=\$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) \
        openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; rc=\$?; tail -3 /work/hold_gate.log; \
      if [ \$rc != 0 ]; then { grep -h 'OT_HOLD_GATE FAIL' /work/hold_gate.log || echo 'NOT RUN (no OT_HOLD_GATE verdict, see hold_gate.log)'; } | sed 's/^/FAIL_POSTCTS FF structural hold gate: /' | tee -a /work/FAIL_POSTCTS; rc=4; fi; fi; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = grt ]; } && grep -q '^export OT_PREGRT_FF_HOLD = 1' /work/config.mk; then C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc 2>/dev/null | head -1); \
    PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\"\$C\" SDC=\"\$S\" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
      OT_VCLK_TT=\$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk) OT_VCLK_FF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
      OT_HOLD_IN_MIN=\$(sed -n 's/^export OT_HOLD_IN_MIN = //p' /work/config.mk) OT_HOLD_OUT_MIN=\$(sed -n 's/^export OT_HOLD_OUT_MIN = //p' /work/config.mk) \
      OT_TAP_WINDOW=\$(sed -n 's/^export OT_TAP_WINDOW = //p' /work/config.mk) \
      LAYER_PARASITICS_FILE=\$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) \
      openroad -exit /work/pregrt_ff_hold.tcl > /work/pregrt_ff_hold.log 2>&1; rc=\$?; grep -h OT_PREGRT_FF_HOLD /work/pregrt_ff_hold.log | tail -3; \
    if [ \$rc != 0 ]; then echo 'FAIL_POSTCTS pre-GRT FF hold step (pregrt_ff_hold.log)' | tee -a /work/FAIL_POSTCTS; rc=6; fi; fi; \
  HM=; if [ \$rc = 0 ]; then HMR=\$(\$M print-OT_HOLD_FF_MARGIN 2> /work/hold_margin_read.log); hmr=\$?; \
    if [ \$hmr != 0 ]; then cat /work/hold_margin_read.log; echo 'FAIL_POSTCTS hold margin Make read' | tee -a /work/FAIL_POSTCTS; rc=9; \
    else HM=\$(printf '%s\\n' \"\$HMR\" | sed -nE 's/^OT_HOLD_FF_MARGIN[[:space:]]*[:=][[:space:]]*//p'); \
      if [ -n \"\$HM\" ] && ! python3 -c 'import math,re,sys; s=sys.argv[1].strip(); valid=re.fullmatch(r\"[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?\",s); x=float(s) if valid else float(\"nan\"); sys.exit(not math.isfinite(x))' \"\$HM\" > /work/hold_margin_value.log 2>&1; then \
        echo \"FAIL_POSTCTS invalid OT_HOLD_FF_MARGIN [\$HM]: expected a finite number\" | tee -a /work/FAIL_POSTCTS; rc=9; fi; fi; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && { [ $GOAL = route ] || [ $GOAL = grt ]; }; then MF=\$M; if [ -f /work/macro_ff_repair.mk ]; then MF=\"\$M DESIGN_CONFIG=/work/macro_ff_repair.mk\"; fi; OT_VCLK_CORNER=ff \$MF grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && { [ $GOAL = route ] || [ $GOAL = grt ]; }; then O5=\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1); \
    BG=\$(grep -c '^export OT_POSTCTS_BAND_GATE = 1' /work/config.mk); rm -f /work/postcts_advisory.log; \
    for c in TT FF; do OT_POSTCTS_BAND_GATE=\$BG OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$O5 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; \
      grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log || echo \"OT_POSTCTS_GATE \$c no result FAIL\" | tee -a /work/postcts_gate_\$c.log; done; \
    if grep -hq 'OT_POSTCTS_GATE.*FAIL' /work/postcts_gate_TT.log /work/postcts_gate_FF.log; then \
      if [ \$BG != 0 ]; then grep -h OT_POSTCTS_GATE /work/postcts_gate_*.log | sed 's/^/FAIL_POSTCTS pre-route insertion gate: /' >> /work/FAIL_POSTCTS; rc=6; \
      else grep -h OT_POSTCTS_GATE /work/postcts_gate_*.log | sed 's/^/OT_POSTCTS_ADVISORY pre-route insertion gate (not a stop, OWNER 11-03 19:12; signoff.json insertion_band): /' | tee -a /work/postcts_advisory.log; fi; fi; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = grt ] || [ $GOAL = route ] || [ $GOAL = finish ]; }; then \
    if [ -z \"\$HM\" ] || [ $GOAL = finish ]; then \$M grt; rc=\$?; fi; \
    if [ \$rc = 0 ]; then python3 -I /work/legacy_gate.py /work grt; rc=\$?; \
      if [ \$rc != 0 ]; then echo 'FAIL_POSTCTS final GRT released TT/FF policy (grt_policy.json)' | tee -a /work/FAIL_POSTCTS; rc=6; fi; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != grt ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/core_infra_post.v ] && [ -f /work/lec.py ]; then python3 -I /work/lec.py /work --netlist /work/core_infra_post.v --out /work/lec_post > /work/lec_post.log 2>&1; lr=\$?; tail -1 /work/lec_post.log; \
    if [ \$lr != 0 ]; then echo \"FAIL_POSTPLACE clock-gate copy LEC exit \$lr (lec_post/lec.json): copies not proved equivalent\" | tee -a /work/FAIL_POSTCTS; rc=5; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/m8_grant.json ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then for L in /work/run/results/asap7/*/base/*.lef; do [ -f \"\$L\" ] && python3 -I /work/m8_grant.py fixlef --grant /work/m8_grant.json \"\$L\"; done; fi; \
  O=\$(ls /work/run/results/asap7/*/base/5_route.odb /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != grt ] && [ -n \"\$O\" ]; then ODB=\$O PINS=/work/audit_pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; rc=\$?; fi; \
  if { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh wait /work '$NAME' '$GOAL' \$rc; fi; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
[ -z "$LECA" ] || rc=$(bash "$K/lec_async.sh" finish "$K" "$rc" 5 "$NAME" "$GOAL")
if [ -n "$GRTM" ] && [ $rc = 0 ]; then GL=$(ls "$K"/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -1)  # GRTM
  if [ -n "$GL" ] && ! grep -q "GRT-9103\] OT transition-layer mode $GRTM " "$GL"; then echo "FAIL_GRT_MODE $GRTM: $GL has no matching GRT-9103 (mode not applied)" | tee -a "$K/FAIL_GRT_MODE"; rc=1; fi  # GRTM
fi  # GRTM
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# Route success alone is not sign-off. Preserve previous failed verdicts.
if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then
  SO="$K/signoff"; [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)_$$"
  # KW-FIX-32 11-07 (COORD 19:0x, FLOW-CHILD-ETM-CONTEXT at sign-off, DIE-HBM-89 q_spb2 vE): signoff.py runs on the
  # host and counts an unexpanded child ETM only with the parent flow tag; give it the GRT gate's FT (env, else
  # K/flow_tag).  The child records are read at their host paths (no mount needed on the host).  Unset FT = as before.
  SIGNOFF_DOCKER=${SIGNOFF_DOCKER:-docker} python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" \
    --out "$SO" --image "$IMAGE" --corners tt,ff ${FT:+--flow-tag "$FT"} > "$SO.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$SO.log" | head -12
fi
exit $rc
"""


_CLAND_RING = re.compile(r"\b(ot_dp_clk_landing_cas?)\s*#\(([^;]*?)\)\s*u_cland_(\w+)\s*\(")


def kit_rtl_land_slots(lands, tn, rtl_files):
    """land_slots of a --kit-rtl type (DIE-KV-31): Landings.land_slots(tn), fail-closed against the bound RTL text.
    Every declared hold_mux ring <b> (cland_dn_ready_/fault_<b> ride ring <b>) must be an ot_dp_clk_landing_ca/_cas
    instance u_cland_<b> with DEPTH == D; every ring_start must name a declared ring; an origin_start origin must be
    an ot_dp_landing_origin[_s] or ot_dp_landing_relay instance; and every count-aligned u_cland_* ring in the bound RTL must be declared
    (no undeclared ring, no declared ring that the binder did not build).  None when the type lands nothing."""
    import copy
    import clock_landings
    import gen_rtl
    ls = copy.deepcopy(lands.land_slots(tn))
    txt = "\n".join(Path(f).read_text(errors="replace") for f in rtl_files if Path(f).suffix in (".sv", ".v"))
    built = {}
    for m in _CLAND_RING.finditer(txt):
        d = re.search(r"\.DEPTH\s*\(\s*(\d+)\s*\)", m.group(2))
        if not d:
            raise gen_rtl.GenError(f"type {tn}: bound ring u_cland_{m.group(3)} ({m.group(1)}) has no literal DEPTH")
        built[m.group(3)] = int(d.group(1))
    # Named hard wrappers preserve the ring at u_cland_<bus>, but no longer
    # instantiate the parameterized base in the parent. The binder checks the
    # exact base/parameters before this rename (param_wrap.wrap_bound).
    raw_plan = getattr(lands, "plan", None) or {}
    for hc in raw_plan.get("partition_types", {}).get(tn, {}).get("hard_cores", []):
        pw = hc.get("param_wrap") or {}
        if pw.get("base") not in ("ot_dp_clk_landing_ca", "ot_dp_clk_landing_cas"):
            continue
        inst = hc.get("physical_inst", "").removeprefix("u_bound.")
        master = hc.get("physical_master") or hc["module"]
        if not inst.startswith("u_cland_") or "." in inst:
            raise gen_rtl.GenError(f"type {tn}: hard landing wrapper has invalid path {inst}")
        if not re.search(r"\b" + re.escape(master) + r"\s+" + re.escape(inst) + r"\s*\(", txt):
            raise gen_rtl.GenError(f"type {tn}: hard landing wrapper {master} {inst} missing from bound RTL")
        r = inst.removeprefix("u_cland_")
        if r in built:
            raise gen_rtl.GenError(f"type {tn}: ring {r} has both native and hard-wrapper instances")
        built[r] = int(pw["params"]["DEPTH"])
    buses = (ls or {}).get("buses", {})
    rings = {}
    for b, v in buses.items():
        if v.get("form") == "hold_mux":
            r = re.sub(r"^cland_dn_(ready|fault)_", "", b)
            if r not in built:
                raise gen_rtl.GenError(f"type {tn}: land_slots ring {r}: no ot_dp_clk_landing_ca/_cas u_cland_{r} "
                                       "in the bound RTL")
            if built[r] != int(v["D"]):
                raise gen_rtl.GenError(f"type {tn}: land_slots ring {r}: D {v['D']} != bound DEPTH {built[r]}")
            rings[r] = built[r]
    for b, v in buses.items():
        if v.get("form") == "ring_start":
            for r in ([v["ring"]] if isinstance(v["ring"], str) else v["ring"]):
                if r not in rings:
                    raise gen_rtl.GenError(f"type {tn}: land_slots {b}: ring_start of undeclared ring {r}")
        elif v.get("form") == "origin_start":
            module = r"ot_dp_landing_relay" if v.get("copies") or v.get("stages") else r"(?:ot_dp_landing_origin(?:_s)?|ot_dp_landing_relay)"
            path = _kit_inst_path(txt, v["origin"], module)
            if path is None:
                raise gen_rtl.GenError(f"type {tn}: land_slots {b}: origin {v['origin']} is not one bound "
                                       "ot_dp_landing_origin[_s] or ot_dp_landing_relay instance under one instance path")
            v["origin"] = path      # face_guard matches the synthesized instance path (kit top -> u_bound -> origin)
            if v.get("copies"):
                copies = []
                for copy in v["copies"]:
                    cp = _kit_inst_path(txt, copy, r"ot_dp_landing_relay")
                    if cp is None:
                        raise gen_rtl.GenError(f"type {tn}: land_slots {b}: copy {copy} is not one bound relay instance")
                    copies.append(cp)
                v["copies"] = copies
            if v.get("stages"):
                stages = []
                for stage in v["stages"]:
                    sp = _kit_inst_path(txt, stage, r"ot_dp_landing_relay")
                    if sp is None:
                        raise gen_rtl.GenError(f"type {tn}: land_slots {b}: stage {stage} is not one bound relay instance")
                    stages.append(sp)
                v["stages"] = stages
    # a FREG-1 ring is behind ordinary face registers (Landings.land_slots declares nothing for it)
    freg = {r for r in built if (clock_landings.ring_write_reg(getattr(lands, "plan", None) or {}, tn, r) or {}).get("freg")}
    extra = sorted(set(built) - set(rings) - freg)
    if extra:
        raise gen_rtl.GenError(f"type {tn}: bound count-aligned rings not declared by the landing sidecar: {extra[:5]}")
    return ls


def _kit_rooted_rtl(text, top):
    """Restrict hierarchy queries to definitions reachable from the explicit kit top."""
    from kit_assembly import _masked_rtl
    masked = _masked_rtl(text)
    definitions = {}
    for match in re.finditer(r"^\s*module\s+(\w+)(.*?)\bendmodule\b", masked, re.S | re.M):
        definitions.setdefault(match[1], []).append(match)
    selected, visiting = set(), set()
    call = re.compile(r"\b(\w+)\s*(?:#\([^;]*?\))?\s+(\w+)\s*\(")

    def visit(name):
        if name in visiting:
            raise ValueError(f"recursive selected kit hierarchy at {name}")
        if name in selected:
            return
        if len(definitions.get(name, [])) != 1:
            raise ValueError(f"selected kit module {name} is missing or duplicated")
        visiting.add(name)
        body = definitions[name][0][2]
        for cell in call.finditer(body):
            # DIE-HBM-91-KCLS 11-08 (class k2): a module that instantiates ITSELF is a generate-terminated recursive
            # tree (ot_hdc_v41x_addtree #(.N(N/2)) u_l/u_r under `else begin : g_rec`); its one definition is already
            # being selected, so the self-cell adds nothing.  Mutual recursion (A -> B -> A) still fails closed.
            if cell[1] == name:
                continue
            if cell[1] in definitions:
                visit(cell[1])
        visiting.remove(name)
        selected.add(name)

    visit(top)
    return "\n".join(text[m.start():m.end()]
                     for name, matches in definitions.items() if name in selected
                     for m in matches)


def _kit_inst_path(txt, inst, mod_re, owner_module=None):
    """Dotted instance path of the ONE `<mod_re> inst (` instance from the kit top of the bound RTL text (each enclosing
    module instantiated exactly once up to a module nobody instantiates, e.g. kit top -> u_bound -> inst); else None.
    owner_module restricts the local name to an already verified reset-forest owner."""
    txt = re.sub(r"//[^\n]*|/\*.*?\*/", "", txt, flags=re.S)       # "bound module X" in a header comment
    mods = {m.group(1): m.group(2) for m in re.finditer(r"^\s*module\s+(\w+)(.*?)\bendmodule\b", txt, re.S | re.M)}
    own = [mn for mn, body in mods.items()
           if (owner_module is None or mn == owner_module) and re.search(rf"\b{mod_re}\s*(?:#\([^;]*?\))?\s*{re.escape(inst)}\s*\(", body)]
    if len(own) != 1:
        return None
    path, mn = [inst], own[0]
    for _ in range(len(mods)):
        up = [(pn, m.group(1)) for pn, body in mods.items() if pn != mn
              for m in re.finditer(rf"\b{re.escape(mn)}\s*(?:#\([^;]*?\))?\s*(\w+)\s*\(", body)]
        if not up:
            return ".".join(reversed(path))
        if len(up) != 1:
            return None
        mn = up[0][0]
        path.append(up[0][1])
    return None


def _bound_reset_identity(tree):
    """A reset tree without what gen adds later: physical_inst on core_resets is resolved before install, the bound receipt never has it."""
    tree = json.loads(json.dumps(tree))
    for c in (tree or {}).get("core_resets") or []:
        c.pop("physical_inst", None)
    return tree


def install_collector_event(P, tn, lands, rtl_files, plan_tree=None):
    """KW-FIX-27 11-07 three-reset-tree class (DIE-S81-73, Codex): the collector RTL comes from the sidecar event tree,
    the native u_rrl_* relays from the captured solve, and install_bound_native_reset puts that solve in the contract's
    collector_tree.  Collector placement (landing_place) therefore names collector nodes from the sidecar event, kept
    apart from the bound_reset mapping, and they must be the collectors the bound RTL holds: a kit that cannot agree
    stops here instead of at OT_CLAND in global place.  No event or inactive collector: nothing changes.

    DIE-S81-85 11-09 (dsdv_slice_kv512_C__t1, plan 65648816, bind6): the bind emits the collectors on
    LC.effective_tree(plan type, table tree) (S81-OTHERFAIL-1: a soft plan landing_contract.collector_tree wins over
    the table copy), and clock_landing_verify checks that same tree.  plan_tree is that plan collector_tree as the plan
    file holds it, taken BEFORE install_bound_native_reset may replace it with the native solve.  Candidate event trees:
    the bind's choice first, then the plain sidecar tree (KW-FIX-27 form); the first whose collectors equal the bound
    RTL is installed.  No plan_tree: only the sidecar tree, as before."""
    import gen_rtl
    import landing_collector as LC
    import landing_place as LP
    info = ((getattr(lands, "collector", None) or {}).get("types") or {}).get(tn)
    contract = P.types[tn].get("clock", {}).get("landing_contract")
    if not info or not contract or not info["mask"].get("active") or lands.dataflow:
        return
    trees = [info["tree"]]
    if plan_tree is not None:
        bind_tree = LC.effective_tree(dict(clock=dict(landing_contract=dict(collector_tree=plan_tree))), info["tree"])
        if bind_tree is not info["tree"]:
            trees.insert(0, bind_tree)
    events = [dict(tree=tr, collector_root_node=info.get("collector_root_node", "rst_root_n"),
                   local_sources=info["local_sources"], children=info["children"]) for tr in trees]
    pat = re.compile(r"\bot_dp_landing_collect\b[^;]*?\b(u_cland_collect_\w+)\s*\(")
    bound = set()
    for f in rtl_files:
        if Path(f).suffix in (".sv", ".v"):
            text = Path(f).read_text(errors="replace")
            if "ot_dp_landing_collect" in text:
                bound.update(pat.findall(text))
    for k, event in enumerate(events):
        expected = LP.collector_instances(event)
        if bound == expected:
            break
    else:
        raise gen_rtl.GenError(f"type {tn}: sidecar collector event differs from the bound collector RTL: "
                               f"event only {sorted(expected - bound)[:5]}, RTL only {sorted(bound - expected)[:5]} "
                               f"({len(expected)} vs {len(bound)}); bind and --clock-landing are from different events"
                               + (" (plan collector_tree checked too)" if len(events) > 1 else ""))
    contract["collector_event"] = event
    src = "the plan collector_tree (bind effective tree)" if len(events) > 1 and k == 0 else "the sidecar event"
    print(f"gen phys: type {tn}: collector placement from {src}, {len(expected)} collectors = bound RTL", flush=True)


def install_bound_native_reset(P, tn, rtl_files, source_contract=None):
    """Opt-in bound reset authority: verify the explicit tree against the ONE native hierarchy.

    Isolated physical plans do not define the native reset entry role. No guessed
    singleton root or newly solved relay topology may replace already bound RTL.
    """
    import copy
    import math
    import gen_rtl
    import reset_tree as RT
    import bound_reset_contract as BRC
    source_contract = source_contract or BRC.kit(rtl_files, tn)
    declared_tree = P.types[tn].get("clock", {}).get("landing_contract", {}).get("collector_tree")
    if source_contract:
        BRC.validate(source_contract, tn)
        tree = copy.deepcopy(source_contract["tree"])
        if declared_tree is not None and any(tree.get(k) != v for k, v in declared_tree.items()):
            # The plan's published collector_tree is a snapshot; bind emits RT.for_type(plan). A snapshot older than the
            # solve is provably stale when the current solve IS the captured tree: the RTL is right, use its tree and say so.
            # Any other difference (bind from another plan, edited graph) still stops.
            try:
                solved = json.loads(json.dumps(RT.for_type(P, tn)))
            except Exception:
                solved = None
            if _bound_reset_identity(solved) != _bound_reset_identity(tree):
                raise gen_rtl.GenError(f"type {tn}: physical collector_tree differs from captured bound reset identity; preserve original IDs/edges/coordinates")
            P.types[tn].setdefault("clock", {}).setdefault("landing_contract", {})["collector_tree"] = copy.deepcopy(tree)
            print(f"gen phys: NOTE type {tn}: published collector_tree is stale, the current solve equals the captured bound reset tree; using the captured tree", flush=True)
    else:
        tree = copy.deepcopy(declared_tree)
    if not isinstance(tree, dict) or tree.get("entry") not in ("sync", "relayed"):
        raise gen_rtl.GenError(f"type {tn}: bound native reset requires explicit collector_tree entry/topology")
    if tree.get("type") != tn or tree.get("sync_stages") != 2:
        raise gen_rtl.GenError(f"type {tn}: bound native reset requires matching type and two entry stages")
    # KV-PLAN-2 11-09 (kv3_hub_C, the die's root type: entry sync + PLL lock): the root lock qualifier is verified
    # exactly instead of refused.  reset_tree._root_entry_lines emits u_rst_root (.sync_rst_n(rst_por_n)) ->
    # ot_dp_lockq #(.STABLE(stable)) u_rst_lockq (.d(rst_por_n), .locked(LOCK_SRC), .q(rst_root_n)) and bind.py drives
    # LOCK_SRC from the one declared leaf output {inst}.{pin}; every one of those facts is checked below.  A tree
    # without lock is unchanged; a lock on a relayed entry (never emitted by reset_tree) still stops.
    lock = tree.get("lock")
    if lock and tree.get("entry") != "sync":
        raise gen_rtl.GenError(f"type {tn}: bound native root lock qualification requires a sync entry")
    if lock and (not isinstance(lock, dict) or not lock.get("inst") or not lock.get("pin")
                 or type(lock.get("stable")) is not int or lock["stable"] < 1
                 or lock.get("stages") != lock["stable"] + RT.LOCKQ_EXTRA):
        raise gen_rtl.GenError(f"type {tn}: bound native root lock qualifier declaration is incomplete "
                               f"(inst, pin, stable >= 1, stages = stable + {RT.LOCKQ_EXTRA})")
    if tree.get("relay_driver"):
        raise gen_rtl.GenError(f"type {tn}: bound native paired reset drivers require a separately qualified placement contract")
    w, h = P.types[tn]["outline_um"]
    for label, xy in [("root", tree.get("root")), ("start_in", tree.get("start_in"))] + [
            (r.get("name", "relay"), r.get("xy")) for r in tree.get("relays", [])]:
        if label == "start_in" and not tree.get("start"):
            continue
        if (not isinstance(xy, (list, tuple)) or len(xy) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xy)
                or not 0 <= xy[0] <= w or not 0 <= xy[1] <= h):
            raise gen_rtl.GenError(f"type {tn}: native reset {label} coordinate outside outline")
    relays = tree.get("relays")
    if (not isinstance(relays, list) or not relays
            or len({r.get("name") for r in relays}) != len(relays)
            or len({r.get("q") for r in relays}) != len(relays)):
        raise gen_rtl.GenError(f"type {tn}: native reset requires unique explicit relay names/nets")
    by_net = {r["q"]: r for r in relays}
    depths = {"rst_root_n": 0}
    def depth(q, visiting):
        if q in depths:
            return depths[q]
        if q not in by_net or q in visiting:
            raise gen_rtl.GenError(f"type {tn}: native reset has missing/cyclic topology at {q}")
        r = by_net[q]
        value = depth(r["d"], visiting | {q}) + 1
        if r.get("depth") != value:
            raise gen_rtl.GenError(f"type {tn}: native reset declared depth differs at {r['name']}")
        depths[q] = value
        return value
    for q in by_net:
        depth(q, set())
    for i in range(len(tree.get("taps", []))):
        if depths.get(f"rst_n_t{i}") != tree.get("depth"):
            raise gen_rtl.GenError(f"type {tn}: native reset tap {i} release depth differs")
    text = "\n".join(Path(f).read_text() for f in rtl_files if Path(f).suffix in (".sv", ".v"))
    scoped_text = text
    top = P.types[tn].get("module")
    if top is not None:
        try:
            scoped_text = _kit_rooted_rtl(text, top)
        except ValueError as exc:
            raise gen_rtl.GenError(f"type {tn}: native reset selected hierarchy: {exc}") from exc
    clean = re.sub(r"//[^\n]*|/\*.*?\*/", "", scoped_text, flags=re.S)
    modules = list(re.finditer(r"^\s*module\s+(\w+)(.*?)\bendmodule\b", clean, re.S | re.M))
    paths, owner = {}, None
    verified_cell_classes = set()

    def canonical_cell(src, module):
        src = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
        found = re.findall(rf"\bmodule\s+{re.escape(module)}\b(.*?)\bendmodule\b", src, re.S)
        return re.sub(r"\s+", "", found[0]) if len(found) == 1 else None

    def check(name, module, ports):
        nonlocal owner
        if module not in verified_cell_classes:
            actual_cell = canonical_cell(text, module)
            if actual_cell is None or actual_cell != canonical_cell(gen_rtl.CELLS + getattr(gen_rtl, "LOCKUP_CELLS", ""), module):
                raise gen_rtl.GenError(f"type {tn}: native reset cell {module} source differs from canonical stage/gate behavior")
            verified_cell_classes.add(module)
        path = _kit_inst_path(scoped_text, name, re.escape(module),
                              owner_module=owner[0] if owner else None)
        if path is None:
            raise gen_rtl.GenError(f"type {tn}: native reset {name}: missing/duplicate/wrong-module hierarchy")
        hits = []
        for m in modules:
            if owner is not None and m.group(1) != owner[0]:
                continue
            for c in re.finditer(rf"\b{re.escape(module)}\s*(?:#\([^;]*?\))?\s*{re.escape(name)}\s*\((.*?)\)\s*;", m.group(2), re.S):
                hits.append((m.group(1), m.group(2), c.group(1)))
        if len(hits) != 1:
            raise gen_rtl.GenError(f"type {tn}: native reset {name}: ambiguous instance")
        actual = dict(re.findall(r"\.(\w+)\s*\(\s*([^()]*)\s*\)", hits[0][2]))
        if any(re.sub(r"\s+", "", actual.get(k, "")) != re.sub(r"\s+", "", v) for k, v in ports.items()):
            raise gen_rtl.GenError(f"type {tn}: native reset {name}: clock/data/reset topology differs")
        prefix = path.rsplit(".", 1)[0] if "." in path else ""
        if owner is not None and owner != (hits[0][0], prefix):
            raise gen_rtl.GenError(f"type {tn}: native reset instances do not share the declared wrapper hierarchy")
        owner = hits[0][0], prefix
        paths[name] = path
        return hits[0][1]

    sync = tree["entry"] == "sync"
    ent = "u_rst_root" if sync else "u_rst_in"
    mod = "ot_dp_rsync_s2" if sync else "ot_dp_rrelay"
    body = check(ent, mod, {"clk": "clk", "async_rst_n" if sync else "d": "arst_n",
                            "sync_rst_n" if sync else "q": "rst_por_n" if lock else "rst_root_n"})
    lock_path = None
    if lock:
        check("u_rst_lockq", "ot_dp_lockq", {"clk": "clk", "d": "rst_por_n", "locked": RT.LOCK_SRC, "q": "rst_root_n"})
        # kept out of native_paths: the qualifier is no relay node (reset_tree.tcl places none for it), and captured
        # receipts of lock-free trees stay comparable
        lock_path = paths.pop("u_rst_lockq")
        stable = re.findall(r"\bot_dp_lockq\s*#\(\s*\.STABLE\(\s*(\d+)\s*\)\s*\)\s*u_rst_lockq\s*\(", body)
        if stable != [str(lock["stable"])]:
            raise gen_rtl.GenError(f"type {tn}: native reset lock qualifier STABLE differs from the tree ({lock['stable']})")
        drv = re.findall(rf"\bassign\s+{RT.LOCK_SRC}\s*=\s*([^;]+);", body)
        net = re.fullmatch(r"\s*(\w+)\s*(?:\[\s*0\s*\])?\s*", drv[0]) if len(drv) == 1 else None
        if net is None:
            raise gen_rtl.GenError(f"type {tn}: native reset lock source {RT.LOCK_SRC} needs exactly one plain driver")
        users = re.findall(rf"\.(\w+)\s*\(\s*{re.escape(net.group(1))}\s*(?:\[[^\]]*\])?\s*\)", body)
        if users.count(lock["pin"]) != 1:
            raise gen_rtl.GenError(f"type {tn}: native reset lock source is not exactly one {lock['inst']}.{lock['pin']} "
                                   "leaf output")
        if len(re.findall(r"\brst_por_n\b", re.sub(r"\bwire\s+rst_por_n\s*;", "", body))) != 2:
            raise gen_rtl.GenError(f"type {tn}: native reset rst_por_n must join only u_rst_root and u_rst_lockq")
    if tree.get("start"):
        check("u_run_root" if sync else "u_run_in", mod,
              {"clk": "clk", "async_rst_n" if sync else "d": "start_i",
               "sync_rst_n" if sync else "q": "run_root"})
    # The verified entry must reach the physical kit ports through the exact
    # native wrapper, never a tied or privately substituted reset/clock input.
    child = owner[0]
    while True:
        parents = []
        for m in modules:
            for call in re.finditer(rf"\b{re.escape(child)}\s*(?:#\([^;]*?\))?\s*(\w+)\s*\((.*?)\)\s*;", m.group(2), re.S):
                parents.append((m.group(1), dict(re.findall(r"\.(\w+)\s*\(\s*([^()]*)\s*\)", call.group(2)))))
        if not parents:
            break
        if len(parents) != 1 or any(re.sub(r"\s+", "", parents[0][1].get(port, "")) != port for port in ("clk", "arst_n")):
            raise gen_rtl.GenError(f"type {tn}: native reset wrapper clock/reset entry is not an exact passthrough")
        child = parents[0][0]
    expected_outs = {f"rst_o_{k}" for k in range(len(tree.get("outs", [])))}
    actual_outs = set(re.findall(r"\boutput\s+(?:wire\s+)?(rst_o_\d+)\b", body))
    if actual_outs != expected_outs:
        raise gen_rtl.GenError(f"type {tn}: native reset output inventory differs")
    expanded = RT.start_relays(tree) if tree.get("start") else relays
    physical_nodes = []
    output_relays = RT.out_relays(tree)
    # RLK-1108 latch form (reset_tree.lockup_hops): the bound RTL carries one hop lockup latch ot_dp_lk in front of
    # each internal hop's capture relay; verify it exactly (launch q -> latch -> relay d) and record its hierarchy so
    # reset_tree.tcl places it at the hop midpoint.  No latch form = no lockup hops = unchanged checks.
    lockup = {r["name"]: RT.lockup_latch_names(r["name"]) for r in RT.lockup_hops(tree)}
    for r in expanded:
        gated = r.get("role") == "gated"
        ports = {"clk": "clk", "d": r["d"], "q": r["q"]}
        if r["name"] in lockup:
            li, lq = lockup[r["name"]]
            check(li, "ot_dp_lk", {"clk": "clk", "d": r["d"], "q": lq})
            ports["d"] = lq
        if gated:
            ports["run"] = r["run"]
        output = output_relays.get(r["q"])
        if output is not None:
            ports["q"] = f"rst_o_{output}"
        check(r["name"], RT.relay_cell(tree, r, gated=gated), ports)
        physical_nodes.append(dict(r, q=ports["q"], d=r.get("dlab", r["d"]), optional=False))
        if output is not None:
            copy_name = r["name"] + "_t"
            check(copy_name, RT.relay_cell(tree, r, gated=gated), dict(ports, q=r["q"]))
            physical_nodes.append(dict(r, name=copy_name, optional=True))
    actual_nodes = set(re.findall(r"\bot_dp_r(?:relay|gate)(?:_drive|_nl)?\s+(u_[rs]rl_\w+)\s*\(", body))
    if actual_nodes != {r["name"] for r in physical_nodes}:
        raise gen_rtl.GenError(f"type {tn}: native reset has undeclared or missing relay nodes")
    entries = set(re.findall(r"\bot_dp_r\w+\s+(u_(?:rst|run)_(?:in|root))\s*\(", body))
    expected_entries = {ent} | ({"u_run_root" if sync else "u_run_in"} if tree.get("start") else set())
    if entries != expected_entries:
        raise gen_rtl.GenError(f"type {tn}: native reset entry role disagrees with the actual wrapper")
    if source_contract and source_contract.get("native_paths") and source_contract["native_paths"] != paths:
        raise gen_rtl.GenError(f"type {tn}: native reset hierarchy differs from captured kit receipt")
    try:
        physical_nodes, placement_sites, placement_review, planned_native_max_hop = BRC.placement(P, tn, tree, physical_nodes, paths, source_contract)
    except ValueError as exc:
        raise gen_rtl.GenError(f"type {tn}: {exc}") from exc
    contract = dict(tree=tree, entry_path=paths[ent], native_paths=paths, physical_nodes=physical_nodes,
                    placement_sites=placement_sites, placement_review=placement_review, planned_native_max_hop_um=planned_native_max_hop,
                    source="captured bound tree + exact native RTL hierarchy/port topology" if source_contract else "explicit collector_tree + exact bound RTL hierarchy/port topology",
                    source_authority=source_contract, core_reset_policy="preserve bound connections; no native core-port rewiring",
                    verified_cell_classes=sorted(verified_cell_classes), opt_in=True)
    if lock:
        contract["lock_qualifier"] = dict(lock, path=lock_path, source=RT.LOCK_SRC)
    if not hasattr(P, "_bound_native_reset_contracts"):
        P._bound_native_reset_contracts = {}
    P._bound_native_reset_contracts[tn] = contract
    return contract


def bound_parent_id_plan(raw, kit_rtl):
    """Project already declared child ID inputs promoted by bind into bound-kit metadata.

    The bind manifest supplies the physical name; plan declarations remain the
    authority for the exact child, identity port and width. No arbitrary bound
    port is accepted, and the caller's plan is never changed.
    """
    import copy
    from parent_id_straps import type_parent_id_straps, with_sub_core_id_leaves
    from bind import short_id
    from bound_r8_straps import project
    raw = project(raw, kit_rtl)
    result = raw
    for tn, filelist in (kit_rtl or {}).items():
        t = raw["partition_types"][tn]
        if not type_parent_id_straps(t):
            continue
        kj = Path(filelist).with_name("kit_rtl.json")
        kr = json.loads(kj.read_text())
        # DIE-HBM-90-TSTRAP 11-07: the bind promotes a sub-core's declared ID on the as-built leaf that holds it
        # (exact asbuilt.sub_core_leaf table, Binder.__init__ sets parent_id_leaf), e.g. plan hard core
        # u_sfucore_Q_lane14__fr (physical_inst u_sfucore_Q_lane14.u_fcore.u_core.u_fr) -> bound leaf
        # u_sfucore_Q_lane14.map_lane_j.  Resolve the declarations with the same table from the producer manifest
        # the kit records, so the manifest row and the plan declaration name the same leaf.  Width, name and the
        # actual kit input are still checked exactly below; no table = unchanged behaviour.
        sub_core_leaf = {}
        if kr.get("asbuilt_manifest"):
            sub_core_leaf = json.loads(Path(kr["asbuilt_manifest"]).read_text()).get("sub_core_leaf") or {}
        t = with_sub_core_id_leaves(t, sub_core_leaf)
        declarations = type_parent_id_straps(t)
        mf = Path(kr["bind_out"]) / "bind_parent_id_straps.json"
        rows = json.loads(mf.read_text()).get("types", {}).get(kr.get("bound_type", tn), {})
        actual = {r["port"]: (r["dir"], r["width"]) for r in kr.get("bound_only_pins", [])}
        additions = []
        declared_top = {r["name"]: r["width"] for r in t.get("id_straps", []) + t.get("count_straps", [])}
        for name, row in rows.items():
            if "leaf" not in row:
                if declared_top.get(name) != row.get("width"):
                    raise ValueError(f"type {tn}: undeclared top-level ID {name} in bind manifest")
                continue
            leaf, port, width = row["leaf"], row["port"], row["width"]
            # A physical alias is represented by the native port in the bind manifest.
            desc = next((d for d in t.get("contents", []) + t.get("hard_cores", [])
                         if d.get("parent_id_leaf", d.get("inst")) == leaf
                         and (d.get("straps") or d.get("parent_id_straps"))), {})
            alias = {v: k for k, v in (desc.get("physical_id_alias") or {}).items()}
            declared = declarations.get(leaf, {}).get(alias.get(port, port))
            if (not declared or declared["width"] != width
                    or name != short_id(f"strap_{leaf}__{port}", 80)
                    or actual.get(name) != ("input", width)):
                raise ValueError(f"type {tn}: bound parent ID {name} disagrees with plan or kit ports")
            if name in declared_top:
                # DIE-QC-61 11-01: the plan already declares this validated child ID as a top-level strap (QC CB batch
                # b1fef12091e: tile_id under count_straps).  Promoting it again duplicated the kit strap list
                # (sdc_lint straps: duplicate names, 12 QC CB types).  Same name + width = already declared.
                if declared_top[name] != width:
                    raise ValueError(f"type {tn}: bound parent ID {name} width {width} != declared {declared_top[name]}")
                continue
            additions.append(dict(name=name, width=width))
        if additions:
            if result is raw:
                result = copy.deepcopy(raw)
            target = result["partition_types"][tn]
            existing = {r["name"]: r for r in target.get("id_straps", [])}
            for row in additions:
                if row["name"] in existing and existing[row["name"]]["width"] != row["width"]:
                    raise ValueError(f"type {tn}: conflicting promoted ID width {row['name']}")
                existing.setdefault(row["name"], row)
            target["id_straps"] = list(existing.values())
    return result


def write_phys(raw, out, rtl_root=None, types=None, util=0.5, proof=False, kit_rtl=None,
               hold_ff_margin=HOLD_FF_MARGIN_DEFAULT, margins=None, skip_ir=False, max_wire_um=None, plan_path=None,
               rc_cal=True, master_slice=None, trial=False, gpl_plain=(), landing=None, hard_wrappers=(), cland_pinslot=(), bound_native_reset=(), private_clock_mesh=None,
               region_guide=None, dpl_diamond=(), native_cell_cap=None, type_overlay=None):
    """gpl_plain: types whose kit places on plain-wirelength GPL (pure-FT corridors, --gpl-plain).
    dpl_diamond: types whose kit legalizes with the diamond DPL (--dpl-diamond; FIRM landing-band DPL stall)."""
    """landing (opt-in, DIE-HEAD-4b, gen phys --clock-landing): the clock_landing_plan sidecar of a composed landed plan.
    The kit wrapper is the SAME landed wrapper gen rtl --clock-landing emits (clock_landings.type_rtl: rings, ring
    reset relays, monitor), every type generated so the sidecar's type check sees all copies, and each kit carries the
    landing ring RTL its wrapper instantiates (LANDING_RTL).  Default None: byte-identical kits."""
    """margins (slew_pct, cap_pct): opt-in repair_design SLEW_MARGIN / CAP_MARGIN (None: not exported)."""
    """kit_rtl {type: filelist}: G3 kits take the bound partition RTL (bind.py kit-rtl: the bound module inside a
    port-only wrapper with the plan type's module name and exact pins) instead of the generated plan wrapper"""
    import gen_rtl
    import master_slice as MS
    # KIT-OVERLAY-1 (opt-in, gen phys --type-overlay FILE): a positions-only intra-type overlay (type_overlay.py) on the
    # die's last strict-bound plan.  Exactly one --types type, validated for that type only (type-scoped schema + G0
    # subset + EQ projection); default None = byte-identical kits, whole-plan validation as before.
    overlay_receipt = None
    if type_overlay is not None:
        import type_overlay as TO
        ov = type_overlay if isinstance(type_overlay, dict) else TO.load_json(type_overlay)
        if not types or list(types) != [ov.get("type")]:
            raise gen_rtl.GenError(f"type overlay for {ov.get('type')!r} requires exactly --types {ov.get('type')}")
        try:
            raw, overlay_receipt = TO.apply_validated(raw, ov)
        except TO.OverlayError as exc:
            raise gen_rtl.GenError(str(exc)) from exc
    if private_clock_mesh:
        if not trial or set(private_clock_mesh) != {"kv3_pc__cl5a95b461"} or not types or set(types) != set(private_clock_mesh):
            raise ValueError("private clock request requires exact single TYPE and explicit --trial/--types")
        if not kit_rtl or set(private_clock_mesh) - set(kit_rtl):
            raise ValueError("private clock request requires the actual bound --kit-rtl readset")
    if not master_slice and not trial and MS.required(raw):     # 12.7c: refuse before writing anything
        raise SystemExit(MS.REFUSE)
    # plan-relative declarations (hard-core pins_file for the reset wavefront) resolve against the plan file
    P = S.Plan(raw, plan_path)
    # KV-KITS-23: hard PHY partitions may contain ordinary mapped boundary glue.
    # Explicit bound RTL is mandatory: a plan-only hard macro must never become
    # a synthesized shell merely because this switch is present.
    native_reset_types = set(bound_native_reset or ())
    for tn in sorted(native_reset_types):
        if tn not in P.types or P.types[tn].get("hard"):
            raise gen_rtl.GenError(f"bound native reset {tn}: requires a declared non-hard bound type")
        if not types or tn not in types or not kit_rtl or tn not in kit_rtl:
            raise gen_rtl.GenError(f"bound native reset {tn}: requires explicit --types and --kit-rtl")
    wrappers = set(hard_wrappers or ())
    for tn in sorted(wrappers):
        if tn not in P.types or not P.types[tn].get("hard"):
            raise gen_rtl.GenError(f"hard wrapper {tn}: must name an existing hard type")
        if not types or tn not in types or not kit_rtl or tn not in kit_rtl:
            raise gen_rtl.GenError(f"hard wrapper {tn}: requires explicit --types and --kit-rtl")
        if not type_macros(P, tn):
            raise gen_rtl.GenError(f"hard wrapper {tn}: requires a placed macro with LEF and TT/FF views")
    if master_slice:                                            # 12.7c: every slice checked before any kit is written
        for tn, t in sorted(P.types.items()):
            if (not t.get("hard") or tn in wrappers) and (not types or tn in types):
                MS.resolve(master_slice, tn, t["outline_um"], raw, trial, kind="partition")
    out = Path(out)
    rtl_dir = out / "_rtl"
    gtypes = types
    if kit_rtl:                # kit-rtl types take the bound RTL: no generated plan wrapper for them
        gtypes = [tn for tn in (types or P.types) if tn not in kit_rtl]
    # DIE-KV-31 (opt-in): --kit-rtl + --clock-landing = declaration only.  The bound RTL already carries the landing
    # rings (the binder ran the same sidecar), so nothing is re-emitted; the sidecar only yields each kit's face_guard
    # land_slots.json, checked against the bound RTL's u_cland_* instances (kit_rtl_land_slots).  Every selected type
    # must then be a kit-rtl type (a generated wrapper would need the landed emitter).
    land_decl_only = landing is not None and bool(kit_rtl)
    if landing is not None:
        if land_decl_only:
            plain = [tn for tn in (types or P.types) if tn not in kit_rtl and not P.types[tn].get("hard")]
            if plain:
                raise gen_rtl.GenError(f"clock landing with --kit-rtl declares land_slots only; types {plain[:5]} "
                                       "have no bound RTL (landing kits use the landed wrapper)")
        else:
            gtypes = None          # the landed emitter checks every copy of every type
    if kit_rtl and gtypes == [] and landing is None:
        # Every selected kit already has its complete bound RTL filelist.
        # Keep the same plan validation, but do not build an unused whole-die
        # top/pad map (including every unrelated partition and reset relay).
        errs = (S.scope_errors_typed(S.validate(raw), types, raw) if overlay_receipt else
                S.scope_errors(S.validate(raw), types))
        if errs:
            raise gen_rtl.GenError("plan invalid:\n  " + "\n  ".join(errs[:20]))
        out.mkdir(parents=True, exist_ok=True)
        files = []
    else:
        # A native physical kit with an explicit type selection consumes only
        # those wrappers/cells. The whole-die top and its reset-open pad map
        # are not inputs to any selected kit. Landed, bound/mixed and full-die
        # callers retain their existing emission paths and validation.
        native_selected_only = bool(types) and not kit_rtl and landing is None
        files = gen_rtl.write_rtl(raw, rtl_dir, rtl_root, gtypes, plan_path=plan_path,
                                  landing=None if land_decl_only else landing,
                                  emit_die_top=not (native_selected_only or
                                                    (land_decl_only and gtypes == [])),
                                  validate_types=types, typed_scope=bool(overlay_receipt))
    # Only the bound kit metadata receives promoted child inputs. The plan-only
    # die emitter retains its original parent declarations and tie values.
    P = S.Plan(bound_parent_id_plan(raw, kit_rtl), plan_path)
    # KW-FIX-1/S81PF 11-02 (default on): a bound kit places its plan macros by their bound netlist path (bind flattens
    # u_r0.u_bn0 -> u_bound.u_u_r0_u_bn0); declared as the kit-only physical identity, receipt in each kit.
    import bound_macro_paths as BMP
    praw, macro_paths = BMP.project(P.raw, kit_rtl)
    if macro_paths:
        P = S.Plan(praw, plan_path)
    lands = None
    if landing is not None:    # DIE-HEAD-21: the same Landings write_rtl just validated -> per-type land_slots.json
        import clock_landings as CL
        lands = CL.Landings(raw, landing)
    cells = rtl_dir / "ot_dp_cells.sv"
    root = Path(rtl_root) if rtl_root else Path(__file__).resolve().parent.parent.parent
    rs = root / "rtl" / "lib" / "ot_reset_sync.sv"
    kits = []
    for tn, t in sorted(P.types.items()):
        if (t.get("hard") and tn not in wrappers) or (types and tn not in types):
            continue
        if kit_rtl and tn in kit_rtl:
            fl = [Path(x) for x in Path(kit_rtl[tn]).read_text().split() if x and not x.startswith(("+", "-"))]
            miss = [str(x) for x in fl if not x.is_file()]
            if miss:
                raise gen_rtl.GenError(f"type {tn}: kit-rtl filelist {kit_rtl[tn]} names missing files {miss[:5]}")
            if fl[0].name != f"{t['module']}.sv":
                raise gen_rtl.GenError(f"type {tn}: kit-rtl filelist must start with the wrapper {t['module']}.sv")
            names = [x.name for x in fl]
            dup = sorted({n for n in names if names.count(n) > 1})
            if dup:
                raise gen_rtl.GenError(f"type {tn}: kit-rtl files share a basename {dup[:5]} (the kit flattens rtl/)")
            mine = fl
        else:
            mine = [cells, rs, rtl_dir / f"{t['module']}.sv"] + [root / s for s in t.get("sources", [])]
            if landing is not None:
                have = {Path(x).resolve() for x in mine}
                mine += [f for f in landing_rtl(root, (rtl_dir / f"{t['module']}.sv").read_text())
                         if Path(f).resolve() not in have]
        import bound_reset_contract as BRC
        captured_reset = BRC.kit(mine, tn)
        # DIE-S81-85: the plan collector_tree the bind walked, kept before a native reset install replaces it
        plan_ctree = json.loads(json.dumps(t.get("clock", {}).get("landing_contract", {}).get("collector_tree")))
        if tn in native_reset_types or captured_reset:
            install_bound_native_reset(P, tn, mine, source_contract=captured_reset)
        if land_decl_only:
            install_collector_event(P, tn, lands, mine, plan_tree=plan_ctree)
        bumps = kit_bump_ports(P, tn, kit_rtl[tn]) if kit_rtl and tn in kit_rtl else None
        kits.append(write_type_kit(P, tn, out, [str(f) for f in mine], util, proof, root, hold_ff_margin, margins,
                                   skip_ir, max_wire_um, rc_cal, master_slice, trial, bump_ports=bumps,
                                   gpl_plain=tn in (gpl_plain or ()),
                                   dpl_diamond=tn in (dpl_diamond or ()),
                                   native_cell_cap=native_cell_cap,
                                   land_slots=(None if lands is None else
                                               kit_rtl_land_slots(lands, tn, mine) if land_decl_only else
                                               lands.land_slots(tn)),
                                   plain_rings=bool(kit_rtl and tn in kit_rtl),
                                   kit_defines=kit_rtl_defines(kit_rtl[tn], mine) if kit_rtl and tn in kit_rtl else None,
                                   cland_pinslot=tuple(cland_pinslot or ()),
                                   region_guide=(region_guide or {}).get(tn),
                                   spare_out=kit_spare_out_bits(kit_rtl[tn]) if kit_rtl and tn in kit_rtl else (),
                                   dead_inputs=kit_dead_inputs(kit_rtl[tn]) if kit_rtl and tn in kit_rtl else None,
                                   private_clock_mesh=(private_clock_mesh or {}).get(tn)))
        if kit_rtl and tn in kit_rtl:
            import count_strap_evidence
            count_strap_evidence.write_for_kit(kits[-1], P.types[tn], Path(kit_rtl[tn]).with_name("kit_rtl.json"))
        if kit_rtl and tn in kit_rtl and (Path(kit_rtl[tn]).parent/'kit_topology.json').is_file():
            import kit_topology
            kit_topology.stage_inventory(Path(kit_rtl[tn]).parent,kits[-1],top=t['module'])
        if overlay_receipt:
            (Path(kits[-1]) / "type_overlay.json").write_text(json.dumps(overlay_receipt, indent=1, sort_keys=True) + "\n")
        if tn in macro_paths:
            (Path(kits[-1]) / BMP.RECEIPT).write_text(json.dumps(macro_paths[tn], indent=1) + "\n")
    (out / "run_kit.sh").write_text(RUN_KIT)
    ft = os.environ.get("OT_FLOW_TAG", "")      # KW-FIX-30: the wave's die flow tag -> K/flow_tag (run_kit.sh passes it)
    if ft:
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", ft):
            raise ValueError(f"OT_FLOW_TAG {ft!r}: not a tag name")
        (out / "flow_tag").write_text(ft + "\n")
    write_grt_transition_mode(out)
    (out / "run_kit.sh").chmod(0o755)
    return kits


GRT_TRANSITION_MODES = ("off", "edge", "edge_outline")


def write_grt_transition_mode(out, env=None):
    """GRT-PATCH-1 11-11: gen env OT_GRT_TRANSITION_MODE (kit_wave item_env) -> K/grt_transition_mode, read by run_kit.sh
    (patched router image for the ORFS main run).  Unset/empty = no file (stock run).  Bad value raises."""
    m = (os.environ if env is None else env).get("OT_GRT_TRANSITION_MODE", "")
    if not m:
        return None
    if m not in GRT_TRANSITION_MODES:
        raise ValueError(f"OT_GRT_TRANSITION_MODE {m!r}: one of {GRT_TRANSITION_MODES}")
    (Path(out) / "grt_transition_mode").write_text(m + "\n")
    return m


_DEFINE_USE = re.compile(r"`(?:ifdef|ifndef|elsif|undef)\s+(\w+)|`(\w+)")


def kit_rtl_defines(kit_rtl_filelist, files):
    """FLOW-KITFAIL-2 10-29 (S81-KITS-A LP lint: `nxt_rw2' implicitly declared, it exists only under
    OT_COLL_NATIVE32): bind.py kit-rtl elaborates the bound partition with the as-built defines (kit_rtl.json
    "defines") but the kit synth / RTL lint / LEC gold read only the plan type's verilog_defines, so a kit whose
    sources test those macros was a different design than the bind.  Returns the kit_rtl.json defines that the kit
    sources actually reference (`ifdef/`ifndef/`elsif/`undef NAME or `NAME), in kit_rtl.json order; [] without
    kit_rtl.json or when no source uses one (such kits keep byte-identical VERILOG_DEFINES)."""
    kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        return []
    defs = [d for d in json.loads(kj.read_text()).get("defines", []) if isinstance(d, str)]
    if not defs:
        return []
    used = set()
    for f in files:
        if Path(f).suffix in (".sv", ".v", ".svh", ".vh") and Path(f).is_file():
            for a, b in _DEFINE_USE.findall(Path(f).read_text(errors="ignore")):
                used.add(a or b)
    return [d for d in dict.fromkeys(defs) if d in used]


LANDING_RTL = ("rtl/common/ot_dp_clk_landing.sv", "rtl/common/ot_dp_clk_landing_ca.sv")
# DIE-HEAD-7 10-28: library RTL the landing rings instantiate (ot_meso_ring / _dsel / _ohor / _sel / _wch live in
# ot_meso_fifo.sv); taken only when the closure reaches it (the HEAD r2 kit dropped it -> RTL_LINT u_ring missing).
LANDING_LIB = ("rtl/common/ot_meso_fifo.sv",)
_LAND_INST = r"^\s*(\w+)\s+(?:#\s*\(|\w+\s*\()"


def landing_rtl(root, wrapper_text):
    """the landing ring RTL files (LANDING_RTL, under root) defining a module the landed wrapper instantiates, plus
    (transitively) the LANDING_LIB files defining what those files instantiate."""
    import re
    def strip(t):
        return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", " ", t, flags=re.S))
    need = set(re.findall(_LAND_INST, strip(wrapper_text), re.M))
    pool = []
    for rel in LANDING_RTL + LANDING_LIB:
        f = Path(root) / rel
        if f.is_file():
            t = strip(f.read_text())
            pool.append((f, set(re.findall(r"^\s*module\s+(\w+)", t, re.M)), set(re.findall(_LAND_INST, t, re.M))))
    taken, grew = set(), True
    while grew:
        grew = False
        for f, defs, uses in pool:
            if f not in taken and need & defs:
                taken.add(f)
                need |= uses
                grew = True
    return [f for f, _, _ in pool if f in taken]


# ------------------------------------------------------------------------------------------------- assembly (3d)
def macro_place_tcl(P):
    lines = ["# GENERATED by tools/die_plan/gen.py assembly: partitions at their exact plan origin / orient (abutted)."]
    for n, p in sorted(P.parts.items()):
        x, y = p["origin_um"]
        lines.append(_place_exact(n, x, y, p.get('orient', 'R0')))
    return "\n".join(lines) + "\n"


def die_pdn_tcl(P, domain_loads=None):
    if domain_loads is not None:
        import pg_regions
        return pg_regions.pdn_tcl(P.die, domain_loads)
    g = P.die.get("pg", {}).get("grid") or [dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32),
                                             dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32)]
    lines = ["# GENERATED by tools/die_plan/gen.py assembly: die PG on the die layers, strapping partition M7 pins.",
             "add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power",
             "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground",
             "global_connect",
             "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}",
             "define_pdn_grid -name {top} -voltage_domains {CORE}"]
    import pg_regions          # ONE PDN RULE (COORD 10-26 13:13): explicit die-lattice offset, spacing and parity
    lines += pg_regions.core_stripes_tcl(dict(P.die, outline_um=[P.W, P.H]), "{top}", g)
    ls = [s["layer"] for s in g]
    for a, b in zip(ls, ls[1:]):
        lines.append(f"add_pdn_connect -grid {{top}} -layers {{{a} {b}}}")
    lines += ["define_pdn_grid -name {parts} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} "
              "-halo {0 0 0 0} -default",
              f"add_pdn_connect -grid {{parts}} -layers {{M7 {ls[0]}}}"]
    return "\n".join(lines) + "\n"


def dropped_taps(P, views):
    """{type: {tap port}} of taps a kit's clock_taps.tcl found without sinks (views/<type>/ot_clock_taps.json, from
    the kit's RESULTS_DIR); a type keeps at least one connected tap."""
    out = {}
    for tn in P.types:
        f = Path(views) / tn / "ot_clock_taps.json"
        if f.is_file():
            d = json.loads(f.read_text())
            names = {n for n, _, _ in S.tap_grid(P, tn)}
            dr = set(d.get("dropped", [])) & names
            if dr and len(dr) < len(names):          # a type keeps at least one connected tap
                out[tn] = dr
    return out


def write_assembly(raw, out, views, rtl_root=None, plan_path=None, pg_map=None):
    """die assembly kit: ORFS config for the die top with every partition as a macro (views/<type>/<module>.lef/.lib
    from each kit's generate_abstract), exact placement, die PG, die IO pins, routing on M2..M9 (abutment nets are
    zero-length; the clock / reset spine drops from M8/M9 onto the interior M7 taps)."""
    import gen_rtl
    P = S.Plan(raw, plan_path)
    domain_loads = None
    if pg_map is not None:
        import pg_regions
        try:
            domain_loads = pg_regions.resolve_loads(P, views, pg_map)
        except ValueError as e:
            raise gen_rtl.GenError(str(e)) from e
    kd = Path(out) / "die"
    (kd / "rtl").mkdir(parents=True, exist_ok=True)
    ep = gen_rtl.bus_epochs(P)
    dropped = dropped_taps(P, views)
    (kd / "rtl" / f"{gen_rtl.sv_id(P.name)}_top.sv").write_text(gen_rtl.die_top(P, ep, dropped))
    (kd / "clock_taps.json").write_text(json.dumps(dict(dropped={k: sorted(v) for k, v in dropped.items()}),
                                                   indent=1) + "\n")
    (kd / "macro_place.tcl").write_text(macro_place_tcl(P))
    (kd / "pdn.tcl").write_text(die_pdn_tcl(P, domain_loads))
    if domain_loads is not None:
        (kd / "pg_bindings.json").write_text(json.dumps(domain_loads, indent=1) + "\n")
    (kd / "make_tracks.tcl").write_text(make_tracks_tcl(P))
    io = ["# GENERATED by tools/die_plan/gen.py assembly: die IO pins at the partition faces on the die edge."]
    for pid, pr in P.ports.items():
        if DIE_PART not in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        bus = pr["src"]["bus"] if pr["src"]["part"] == DIE_PART else pr["dst"]["bus"]
        f = pr["face"]
        for bit, ln, c in P.port_pins(pid):
            lw = LAYER_W.get(ln, 0.04)
            if f in "EW":
                x = P.W - PIN_LEN_UM / 2 if f == "E" else PIN_LEN_UM / 2
                io.append(f"place_pin -pin_name {{{bus}[{bit}]}} -layer {ln} -location {{{x:.4f} {c:.4f}}} "
                          f"-pin_size {{{PIN_LEN_UM:.4f} {lw:.4f}}}")
            else:
                y = P.H - PIN_LEN_UM / 2 if f == "N" else PIN_LEN_UM / 2
                io.append(f"place_pin -pin_name {{{bus}[{bit}]}} -layer {ln} -location {{{c:.4f} {y:.4f}}} "
                          f"-pin_size {{{lw:.4f} {PIN_LEN_UM:.4f}}}")
    (kd / "io.tcl").write_text("\n".join(io) + "\n")
    lefs, libs = [], []
    for tn, t in sorted(P.types.items()):
        v = Path(views) / tn
        for ext, lst in ((".lef", lefs), (".lib", libs)):
            f = v / f"{t['module']}{ext}"
            if f.is_file():
                shutil.copyfile(f, kd / f.name)
            lst.append(f"/work/{t['module']}{ext}")
    per = t_lib(P.die["period_ps"])
    (kd / "constraint.sdc").write_text(f"create_clock -name clk -period {per:.4f} [get_ports clk]\n"
                                       f"set_clock_uncertainty {t_lib(unc_setup_ps()):.4f} -setup [all_clocks]\n"
                                       f"set_clock_uncertainty {t_lib(unc_hold_ps()):.4f} -hold [all_clocks]\n")
    cfg = [f"# GENERATED by tools/die_plan/gen.py assembly: die {P.name}. Do not edit.",
           f"export DESIGN_NICKNAME = dp_{P.name}_die",
           f"export DESIGN_NAME = {gen_rtl.sv_id(P.name)}_top",
           "export PLATFORM = asap7",
           f"export VERILOG_FILES = /work/rtl/{gen_rtl.sv_id(P.name)}_top.sv",
           "export SDC_FILE = /work/constraint.sdc",
           f"export DIE_AREA = 0 0 {_um(P.W)} {_um(P.H)}",
           f"export CORE_AREA = 0 0 {_um(P.W)} {_um(P.H)}",
           "export ADDITIONAL_LEFS = " + " ".join(lefs),
           "export ADDITIONAL_LIBS = " + " ".join(libs),
           "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl",
           "export MACRO_PLACE_HALO = 0 0",
           "export CORNER = TC",
           "export IO_CONSTRAINTS = /work/io.tcl",
           "export PDN_TCL = /work/pdn.tcl",
           # override: platforms/asap7/config.mk (read AFTER the design config) sets MAKE_TRACKS with a plain
           # export, which silently replaced the plan tracks (M7 offset 0.016, not 0.032) -> every plan pin off-track
           "override export MAKE_TRACKS = /work/make_tracks.tcl",
           "export MIN_ROUTING_LAYER = M2",
           "export MAX_ROUTING_LAYER = M9",
           "export SYNTH_HIERARCHICAL = 0",
           "export LEC_CHECK = 0",
           "export SKIP_LAST_GASP = 1"]
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    import spine
    br = spine.branch_table(P, dropped)
    (kd / "spine_branch.json").write_text(json.dumps(br, indent=1) + "\n")
    (kd / "sta_die.tcl").write_text(sta_die_tcl(P, br))
    seams = []
    for pid, pr in sorted(P.ports.items()):
        if DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        kind = "channel" if P.channel_of(pid) else "abutted"
        for bit in range(S.port_pins_count(pr)):
            seams.append(dict(net=f"w_{gen_rtl.sv_id(pid)}[{bit}]", port=pid, kind=kind,
                              src=gen_rtl.sv_id(pr["src"]["part"]), dst=gen_rtl.sv_id(pr["dst"]["part"])))
    (kd / "seams.json").write_text(json.dumps(dict(die=P.name, seams=seams), indent=0) + "\n")
    top_v = gen_rtl.die_top(P, ep, dropped)
    plain = "\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", l) for l in top_v.splitlines()
                      if not l.startswith("`"))
    (kd / "die_top_struct.v").write_text(plain + "\n")
    (kd / "die_flow.tcl").write_text(die_flow_tcl(P, [Path(x).name for x in lefs], [Path(x).name for x in libs]))
    shutil.copyfile(Path(__file__).with_name("abut_audit.py"), kd / "abut_audit.py")
    (kd / "run_die.sh").write_text(RUN_DIE)
    (kd / "run_die.sh").chmod(0o755)
    return kd


def sta_die_tcl(P, branch=None):
    """die STA over the REAL routed partitions: their final netlists + SPEF under the die top (+ the die SPEF), clocks
    propagated through each partition's own tree.  env: CORNER (TT|FF), PARTS (dir with <type>/6_final.v|.spef),
    DIE (dir with the die's 6_final.v|.spef, optional), OUT.
    CP2 spine branch model (branch = spine.branch_table, written to spine_branch.json): env SPINE=branch (the default
    for a pair plan, i.e. one with clock.spine.die_root_um) puts a generated clock on every connected partition tap
    pin with source latency = its offset_ps (the die H-tree branch mismatch, minus the early shift of a core tap); this
    REPLACES the pair die's own short spine RC up to that pin.  SPINE=routed: one clock from the die clk port through
    the routed pair spine (CP1 behaviour; early core taps then see no early shift)."""
    import gen_rtl
    top = f"{gen_rtl.sv_id(P.name)}_top"
    per = t_lib(P.die["period_ps"])
    lines = ["# GENERATED by tools/die_plan/gen.py assembly: die STA on the routed partitions (abutment proof).",
             "# MODE flat: partition 6_final.v + read_spef -path per instance (mock-array load_mock_array style, no -hier)",
             "# MODE etm : the partitions' generate_abstract timing models (.lib) under the die netlist + die SPEF",
             "set MODE [expr {[info exists ::env(MODE)] ? $::env(MODE) : \"flat\"}]",
             "set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM",
             # ETM runs in openroad, whose link_design needs the technology (ORD-2010): tech + std-cell LEF and the
             # partition abstracts as masters of the timing-model cells.  FLAT runs in standalone OpenSTA ('sta'):
             # openroad's link_design flattens the hierarchy, so read_spef -path <instance> finds no instance (STA-0276)
             "set PL /OpenROAD-flow-scripts/flow/platforms/asap7",
             "if {$MODE == \"etm\"} {",
             "  read_lef $PL/lef/asap7_tech_1x_201209.lef",
             "  read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef",
             "}",
             "foreach f [glob $L/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }",
             "if {$MODE == \"etm\"} {"]
    for tn, t in sorted(P.types.items()):
        lines.append(f"  read_lef $::env(DIE)/{t['module']}.lef")
        lines.append(f"  read_liberty $::env(DIE)/{t['module']}.lib")
    lines.append("} else {")
    for tn, t in sorted(P.types.items()):
        lines.append(f"  read_verilog $::env(PARTS)/{tn}/6_final.v")
    lines += ["}",
              f"if {{[info exists ::env(DIE)] && [file exists $::env(DIE)/6_final.v]}} {{",
              f"  read_verilog $::env(DIE)/6_final.v",
              "} else {",
              f"  read_verilog $::env(PARTS)/die_top.v",
              "}",
              f"link_design {top}",
              "if {$MODE == \"flat\"} {"]
    for n, p in sorted(P.parts.items()):
        lines.append(f"  read_spef -path {gen_rtl.sv_id(n)} $::env(PARTS)/{p['type']}/6_final.spef")
    lines.append("}")
    lines += ["if {[info exists ::env(DIE)] && [file exists $::env(DIE)/6_final.spef]} { read_spef $::env(DIE)/6_final.spef }",
              f"create_clock -name clk -period {per:.4f} [get_ports clk]"]
    pair = bool((P.clock.get("spine", {}) or {}).get("die_root_um"))
    lines.append(f"set SPINE [expr {{[info exists ::env(SPINE)] ? $::env(SPINE) : \"{'branch' if pair else 'routed'}\"}}]")
    if branch:
        lines.append(f"# spine branch model: die root {branch['die_root_um']}, {branch['branch_ps_per_mm']:g} ps/mm, "
                     f"leaf {branch['branch_leaf_um']:g} um, ref {branch['ref_branch_ps']:g} ps (spine_branch.json)")
        lines.append("if {$SPINE == \"branch\"} {")
        for n, r in sorted(branch["parts"].items()):
            for port, v in sorted(r["taps"].items()):
                ck = f"ck_{gen_rtl.sv_id(n)}_{port}"
                lines.append(f"  create_generated_clock -name {ck} -source [get_ports clk] -divide_by 1 "
                             f"[get_pins {gen_rtl.sv_id(n)}/{port}]")
                lines.append(f"  set_clock_latency -source {t_lib(v['offset_ps']):.4f} [get_clocks {ck}]   "
                             f";# branch {v['branch_ps']:g} ps ({v['length_um']:g} um), early {v['early_ps']:g}")
        lines.append("}")
    lines += ["puts \"OT_SPINE $SPINE\"",
              "set_propagated_clock [all_clocks]",
              f"set_clock_uncertainty {t_lib(unc_setup_ps()):.4f} -setup [all_clocks]",
              f"set_clock_uncertainty {t_lib(unc_hold_ps()):.4f} -hold [all_clocks]",
              "set_input_delay 0 -clock clk [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]",
              "set_output_delay 0 -clock clk [all_outputs]",
              "set fh [open $::env(OUT) w]",
              "puts $fh \"mode $MODE corner $::env(CORNER) spine $SPINE\"",
              # R4 revised: seam skew on RC = rise-edge clock arrival at the capture CK minus the launch CK (OpenSTA
              # arrival_max_rise of a CK pin can be the falling-edge arrival, + T/2)
              "proc ot_ck {pin} { if {[catch {set a [get_property $pin arrival_max_rise]}] || $a eq \"\"} { return \"\" }; "
              f"set h {per / 2.0:.4f}; if {{$a >= $h}} {{ set a [expr {{$a - $h}}] }}; return $a }}",
              # (endpoint_clock_pin segfaults OpenSTA here: go through the instances' CLK pins by name)
              "proc ot_ckpin {pin} { set i [file dirname $pin]; "
              "foreach c {CLK CK clk} { set q [get_pins -quiet $i/$c]; if {$q ne \"\"} { return $q } }; return \"\" }",
              # skew from NAMES: an arrival query re-runs the search and frees the PathEnd objects (segfault)
              "proc ot_skew {sp ep} { set s [ot_ckpin $sp]; set e [ot_ckpin $ep]; "
              "if {$s eq \"\" || $e eq \"\"} { return NA }; set a [ot_ck $s]; set b [ot_ck $e]; "
              "if {$a eq \"\" || $b eq \"\"} { return NA }; return [format %.1f [expr {$b - $a}]] }"]
    # every abutment port: the worst setup + hold path through its destination pins
    for pid, pr in sorted(P.ports.items()):
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        thr = f"{gen_rtl.sv_id(pr['dst']['part'])}/{gen_rtl.sv_id(pr['dst']['bus'])}[*]"
        for dly in ("max", "min"):
            lines.append(f"set ps [find_timing_paths -through [get_pins {thr}] -path_delay {dly} -group_path_count 1]")
            lines.append(f"set rows {{}}; foreach p $ps {{ lappend rows [list [get_property $p slack] "
                         f"[get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]] }}")
            lines.append(f"foreach r $rows {{ lassign $r sl sp ep; puts $fh \"PORT {pid} {dly} slack $sl "
                         f"skew [ot_skew $sp $ep] from $sp to $ep\" }}")
            lines.append(f"if {{[llength $ps] == 0}} {{ puts $fh \"PORT {pid} {dly} NO_PATH\" }}")
    # R4 face-flop spread (CP1-R10): rise-edge CK arrival over every pin register (u_bin_* / u_bout_* boundary flops)
    # per partition instance, and over the whole die: FFSPREAD <inst|ALL> n lo hi spread (ps, propagated, RC)
    lines += ["set ff_all {}",
              "foreach c [all_registers -cells] { set n [get_full_name $c]; "
              "if {![regexp {^([^/]+)/u_(bin|bout)_} $n -> pi]} { continue }; "
              "set q [ot_ckpin $n/D]; if {$q eq \"\"} { continue }; set a [ot_ck $q]; if {$a eq \"\"} { continue }; "
              "dict lappend ff_all $pi $a; dict lappend ff_all ALL $a }",
              "foreach k [dict keys $ff_all] { set v [lsort -real [dict get $ff_all $k]]; "
              "puts $fh [format \"FFSPREAD %s n %d lo %.1f hi %.1f spread %.1f\" $k [llength $v] [lindex $v 0] "
              "[lindex $v end] [expr {[lindex $v end] - [lindex $v 0]}]] }"]
    lines += ["puts $fh \"WNS [sta::worst_slack_cmd max] WHS [sta::worst_slack_cmd min]\"",
              "close $fh",
              "report_checks -path_delay max -through [get_pins -hierarchical */x_i*] -format full_clock_expanded "
              "-fields {cap slew fanout}",
              "report_checks -path_delay min -through [get_pins -hierarchical */x_i*] -format full_clock_expanded"]
    return "\n".join(lines) + "\n"


def die_flow_tcl(P, lefs, libs):
    """OpenROAD script for the die (CP1 recipe, COORD 10-23): partitions as macros at their exact plan origin / orient
    (place_macro -exact, halo 0), die PG macro grid over every instance + check_power_grid / analyze_power_grid, die IO
    + clock / reset roots, GRT + DRT of the die nets (clock / reset spine, die IO, planned-channel seams; abutted seams
    are pin-to-pin and skipped by GRT/DRT), routed ODB, die netlist and SPEF."""
    import gen_rtl
    top = f"{gen_rtl.sv_id(P.name)}_top"
    root = P.clock.get("spine", {}).get("root_um") or [P.W / 2, P.H / 2]
    L9, L8 = P.layer_budget["die_layers"][-1], P.layer_budget["die_layers"][0]
    t = [f"# GENERATED by tools/die_plan/gen.py assembly: die {P.name}.",
         "set PL /OpenROAD-flow-scripts/flow/platforms/asap7",
         "read_lef $PL/lef/asap7_tech_1x_201209.lef",
         "read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef"]
    t += [f"read_lef /work/{x}" for x in lefs]
    t += ["foreach f [glob $PL/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }"]
    t += [f"if {{[file exists /work/{x}]}} {{ read_liberty /work/{x} }}" for x in libs]
    t += ["read_verilog /work/die_top_struct.v", f"link_design {top}",
          f"initialize_floorplan -die_area {{0 0 {_um(P.W)} {_um(P.H)}}} -core_area {{0 0 {_um(P.W)} {_um(P.H)}}} "
          "-site asap7sc7p5t",
          "source /work/make_tracks.tcl",
          "source /work/io.tcl"]
    for name, L, x, y in die_root_pins(P):
        sz = "{0.04 0.32}" if P.layers[L]["dir"] == "V" else "{0.32 0.04}"
        t.append(f"place_pin -pin_name {name} -layer {L} -location {{{x:.4f} {y:.4f}}} -pin_size {sz}")
    for n, p in sorted(P.parts.items()):
        x, y = p["origin_um"]
        t.append(_place_exact(gen_rtl.sv_id(n), x, y, p.get('orient', 'R0')))
    t += ["set t0 [clock seconds]",
          "source /work/pdn.tcl", "pdngen", "if {[llength [info procs ot_pg_connect_pins]]} { ot_pg_connect_pins }",
          "set ot_pg_nets {VDD VSS}; if {[info exists ot_pg_pin_rects]} { foreach q $ot_pg_pin_rects { lappend ot_pg_nets [lindex $q 0] } }; set ot_pg_nets [lsort -unique $ot_pg_nets]",
          "foreach n $ot_pg_nets { if {[catch {check_power_grid -net $n -error_file /work/pg_$n.rpt} e]} "
          "{ puts \"OT_PG_CHECK_FAIL $n $e\"; if {[info exists ot_pg_pin_rects]} {error $e} } else { puts \"OT_PG_CHECK_OK $n\" } }",
          f"set_routing_layers -signal M2-{L9} -clock M2-{L9}",
          "global_route -allow_congestion -verbose -congestion_report_file /work/die_grt_congestion.rpt",
          "puts \"OT_T_GRT [expr {[clock seconds]-$t0}]\"",
          "detailed_route -output_drc /work/die_drc.rpt -verbose 1",
          "puts \"OT_T_DRT [expr {[clock seconds]-$t0}]\"",
          "write_db /work/die_routed.odb",
          "write_verilog /work/6_final.v",
          "if {[catch {define_process_corner -ext_model_index 0 X; "
          "extract_parasitics -ext_model_file $PL/rcx_patterns.rules; write_spef /work/6_final.spef} e]} "
          "{ puts \"OT_RCX_FAIL $e\" }",
          "source $PL/setRC.tcl",
          "if {[catch {analyze_power_grid -net VDD -source_type STRAPS -error_file /work/psm_VDD.rpt} e]} "
          "{ puts \"OT_PSM_FAIL $e\" } else { puts OT_PSM_OK }",
          "puts OT_DONE"]
    return "\n".join(t) + "\n"


RUN_DIE = r"""#!/bin/bash
# GENERATED by tools/die_plan/gen.py assembly: route the die, audit the seams, die STA two ways (flat stitched: the
# routed partition netlists + per-instance SPEF; ETM: the partitions' abstract .lib + die SPEF) at SS / TT / FF
# (sign-off per AGENTS.md as restated 2026-10-24: setup at TT, hold at FF; SS is reported for information only and
# never gates -- CP1-R10 added the SS run as information).
#   run_die.sh DIEDIR PARTS_DIR [MEM_GB=32] [CPUS=8]   (heavy: through ot-run)   env OT_ORFS_IMAGE picks the image
#   PARTS_DIR/<type>/6_final.v|.spef = each partition kit's routed netlist + SPEF
set -uo pipefail
K=$(cd "$1" && pwd); PARTS=$(cd "$2" && pwd); MEM=${3:-32}; CPUS=${4:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE)" > "$K/image.txt"
docker run --rm --name dpdie-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -v "$PARTS":/parts \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /work "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  /usr/bin/time -v openroad -threads $CPUS -exit /work/die_flow.tcl > /work/die_flow.log 2>&1; echo FLOW_EXIT \$? >> /work/die_flow.log; \
  ODB=/work/die_routed.odb SEAMS=/work/seams.json OUT=/work/abut_audit.json openroad -python -exit /work/abut_audit.py > /work/abut_audit.log 2>&1; \
  for m in flat etm; do T=openroad; [ \$m = flat ] && T='sta -no_splash'; for c in SS TT FF; do MODE=\$m CORNER=\$c PARTS=/parts DIE=/work OUT=/work/sta_\${m}_\$c.txt \$T -exit /work/sta_die.tcl > /work/sta_\${m}_\$c.log 2>&1; done; done; \
  chown -R \$HUID:\$HGID /work"
tail -3 "$K/die_flow.log"; tail -2 "$K/abut_audit.log"; tail -n 3 "$K"/sta_*.txt 2>/dev/null
"""


def mock_lef(P, tn):
    """mock abstract of a partition type (bazel-orfs 'mock abstract'): exact plan pins (same rectangles as io.tcl),
    interior clk / arst_n tap pins, VDD / VSS M7 stripes as the kit PDN writes them, full OBS on M1..M7.  Lets the die
    flow and the seam audit run before the partitions are hardened.  No timing view."""
    t = P.types[tn]
    w, h = t["outline_um"]
    top = P.layer_budget["partition_signal_max"]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {t['module']}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  SIZE {w:.4f} BY {h:.4f} ;"]

    def pin(name, d, use, rects):
        out = [f"  PIN {name}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT"]
        for ln, x0, y0, x1, y1 in rects:
            out += [f"      LAYER {ln} ;", f"        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;"]
        return out + ["    END", f"  END {name}"]
    dirs = {}
    for b in t.get("buses", []):
        dirs[b["name"]] = "INPUT" if b["dir"] == "in" else "OUTPUT"
    for sl in t.get("ft_slots", []):
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "INPUT", "OUTPUT"
    for bus, bit, ln, x, y, f in sorted(type_pins(P, tn), key=lambda p: (p[0], p[1])):
        lw = LAYER_W.get(ln, 0.04) / 2
        r = {"E": (x - PIN_LEN_UM, y - lw, x, y + lw), "W": (x, y - lw, x + PIN_LEN_UM, y + lw),
             "N": (x - lw, y - PIN_LEN_UM, x + lw, y), "S": (x - lw, y, x + lw, y + PIN_LEN_UM)}[f]
        L += pin(f"{bus}[{bit}]", dirs.get(bus, "INPUT"), "SIGNAL", [(ln, *r)])
    tw = LAYER_W.get(top, 0.032) / 2
    for name, x, y in tap_pins(P, tn):
        half=tap_pin_height(P,tn,name)/2
        L += pin(name, "INPUT", "SIGNAL" if name in ("arst_n", "start_i") else "CLOCK",
                 [(top, x - tw, y - half, x + tw, y + half)])
    for name, x, y in reset_out_pins(P, tn):
        L += pin(name, "OUTPUT", "SIGNAL", [(top, x - tw, y - 2 * PIN_LEN_UM, x + tw, y + 2 * PIN_LEN_UM)])
    # PG: the kit's M5 / M6 / M7 stripes (gen_phys.PDN; VSS one width + spacing after VDD)
    for net, j in (("VDD", 0), ("VSS", 1)):
        rects = []
        for ln, dr, pitch, off, wid, sp in (("M5", "V", 4.32, 2.064, 0.12, 0.072), ("M6", "H", 4.32, 1.968, 0.288, 0.096),
                                            ("M7", "V", 8.64, 4.128, 0.288, 0.096)):
            c = off + j * (wid + sp)
            ext = w if dr == "V" else h
            while c + wid / 2 < ext:
                rects.append((ln, c - wid / 2, 0.0, c + wid / 2, h) if dr == "V" else (ln, 0.0, c - wid / 2, w, c + wid / 2))
                c += pitch
        L += pin(net, "INOUT", "POWER" if net == "VDD" else "GROUND", rects)
    L += ["  OBS"] + [f"    LAYER M{i} ;\n      RECT 0 0 {w:.4f} {h:.4f} ;" for i in range(1, int(top[1:]) + 1)]
    L += ["  END", f"END {t['module']}", "END LIBRARY", ""]
    return "\n".join(L)


def write_mock_views(raw, out, phy_io=None):
    P = S.Plan(raw)
    res = []
    for tn, t in P.types.items():
        d = Path(out) / tn
        d.mkdir(parents=True, exist_ok=True)
        lef = mock_lef(P, tn)
        if phy_io is not None:
            import pg_regions
            lef = pg_regions.prototype_lef(P, tn, lef, phy_io)
        (d / f"{t['module']}.lef").write_text(lef)
        res.append(d)
    return res


def pg_free(P, layer, c):
    """coordinate c (across a stripe of `layer`) moved off the die PG stripes of that layer: to the midpoint between
    the two neighbouring stripe centres (all nets), snapped to the layer's track grid."""
    L = P.layers[layer]
    for g in P.die.get("pg", {}).get("grid", []):
        if g["layer"] != layer:
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        step = g["pitch_um"] / k
        j = math.floor((c - g["offset_um"]) / step)
        lo = g["offset_um"] + j * step
        if min(c - lo, lo + step - c) < g["width_um"] / 2 + 0.5:
            c = lo + step / 2
    return round(L["offset_um"] + round((c - L["offset_um"]) / L["pitch_um"]) * L["pitch_um"], 4)


def die_root_pins(P):
    """die clk / rst_n entry pins at the spine root, off the die PG stripes: [(name, layer, x, y)]."""
    root = P.clock.get("spine", {}).get("root_um") or [P.W / 2, P.H / 2]
    L8, L9 = P.layer_budget["die_layers"][0], P.layer_budget["die_layers"][-1]
    out = []
    for name, L, dx in (("clk", L9, 0.0), ("rst_n", L8, 8.64)):
        x, y = root[0] + dx, root[1]
        if P.layers[L]["dir"] == "V":
            x = pg_free(P, L, x)
        else:
            y = pg_free(P, L, y)
        out.append((name, L, x, y))
    return out
