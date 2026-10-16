#!/usr/bin/env python3
"""Reference tile / cluster flow (OWNER 2026-10-11, agent ref-flow-1011): ONE mandatory way to turn tile or cluster RTL +
a slot contract into a closed, die-placeable hard block, with every flow-mechanics pitfall of 2026-10-11 prevented by
construction (see tools/ref_tile/README.md for the pitfall -> mechanism table).

    ref_tile.py gen  SPEC.json [--area-um2 A]      write the kit physical/ref_tile/<name>/ (+ job.json) from a tile spec
    ref_tile.py job  SPEC.json [--commit C]        (re)write only the closure-loop job spec (kit must exist)
    ref_tile.py export --orfs-dir D --kit K --out V   exact abstract + TT/FF/SS libs + clock insertion + child_lint of V

The kit is plain files under physical/ref_tile/<name>/ and is routed by tools/ref_tile/ref_route.sh through the
existing ORFS path (tools/run_abi3_physical.py, the route_master.sh invocation that closed the Qwen die masters):
  kit.env          route settings (TOP, SRCS, PARAMS, FW/FH, PINS, RLAYERS, PD, hooks, macro / child views)
  clock.sdc        plain route SDC (clock on the spec's clock port, 770 ps over-constraint, 0.2 T boundary)
  signoff.sdc      833.333 ps sign-off SDC (60 / 25 ps, die-context boundary io_ref_skew.sdc)
  place.tcl        macro / hard-child placement (on the asap7 track lattice, escaped/unescaped names matched)
  pdn.tcl          layer-contract power grid (full-length PG stripes on the top layer as pins; present-master guards)
  pre_cts.tcl / pre_grt.tcl / post_drt.tcl   composed step hooks (io_ref boundary, pin-access keepout, fwd clock)
  floorplan.json   the geometry the pre-route gate checks (outline, util, macro rects, channels, pin faces)
  job.json         closure-loop spec ("ref_tile": true) -> drop into the loop intake after committing the kit
  pre_gpl.tcl / pre_dpl.tcl   (recipe 2, pin flops + pin hold stages) the one PRE_GLOBAL_PLACE / PRE_DETAIL_PLACE hook

Kit recipe (kit.env RECIPE=<n>; no line = 1): the generator defaults a kit was built with.  A kit keeps its recipe on every
regeneration; a NEW kit takes RECIPE_LATEST; spec "recipe" overrides (see apply_recipe).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
# git object store for commit lookups (M6 pin-grant source commit).  ROOT can be a materialised, non-git source tree
# (pre_route_gate.submit_check); the caller then points GIT_ROOT at the repository the tree was archived from.
GIT_ROOT = None
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import check_macro_track_alignment as cmta  # noqa: E402
import child_lint  # noqa: E402
import pin_fit  # noqa: E402
import clock_entry_constraints  # noqa: E402

KIT_ROOT = "physical/ref_tile"
QDM = "physical/qwen_die_masters"
# floorplan lattice: die / core / macro origins snap to these (um).  2.16 = lcm(row 0.27, M4 track 0.048, site 0.054)
GRID_Y = 2.16
GRID_X = 0.432          # lcm(site 0.054, M5 track 0.048)
# hard-child origin lattice (hbm-vm8 DRT-0421: tile origins on the 10.8 / 5.4 um strap pitch but 0.032 um off the
# 0.064 um M6/M7 tracks): lcm(site 54, row 270, every track pitch M1-M7 36/48/64, PG strap pitch 5400/10800) nm
CHILD_LATTICE_UM = 43.2
TRACK_LATTICE_UM = 8.64  # lcm(site, row, M1-M7 track pitches): cluster outlines snap to it
CORE_MARGIN = 2.16
CHANNEL_UM = 20.0       # macro-macro and macro-core-edge channel
PIN_EDGE_UM = 20.0      # no macro within this distance of a face that carries pins
HALO_UM = 2.16          # placement halo around every macro (hard blockage)
UTIL_LO, UTIL_HI = 0.45, 0.60
UTIL_TARGET = 0.52
FACES = {"N": "top", "S": "bottom", "E": "right", "W": "left"}
# Kit recipe = the generator DEFAULTS (owner 10-13 finishing recipe, el1013-finishing-recipe part B).
#   1  kits generated before 2026-10-13: hold margin 10 ps, macro halo 2.16 um, no boundary hook unless the spec asks, and
#      io_flop_at_pins cannot be combined with inhold / outhold.  Such a kit regenerates byte-identically (no RECIPE line).
#   2  hold margin 30 ps, macro halo 5.4 um, hold cells at the pins (inhold + outhold) AND the pin flops FIRM at the pins
#      (io_flop_at_pins), combined through the kit-local pre_gpl.tcl / pre_dpl.tcl.  Every item is only a default: the
#      spec's own value wins (inhold / outhold / io_flop_at_pins false switch a hook off).
#      Recipe-2 pin defaults (el1014-root-recipe2, 2026-10-14; native pin budget TT launch <= 220 / capture <= 190 ps):
#        hold_pad      {"cell": HB2xp67}: the pin hold pad of inhold / outhold.  HB4xp67 on every pin cost ~120 ps of the
#                      native budget (Qwen cache R2 123 outputs to 239.6 ps, P12 tx_flit 240.9, FF out hold +36 =
#                      overpadded; HB2: +15.3).  "strong_ports" (regexp) + "basis" (the routed FF report that measured
#                      HB2 short) put HB4 only on those pins.
#        pin_reg_split true: physical/common_flow/pin_reg_split.tcl first in pre_gpl.tcl -- one dedicated launch flop
#                      per output pin (a merged / shared / internally loaded pin flop is cloned), so io_flop_at_pins
#                      anchors every one of them at its own pin (R2: one flop -> INV fanout 7 -> 7 pins, unanchored).
#        keep_pin_regs true: OT_KEEP_PIN_REGS=1 for physical/common_flow/ot_keep_regs.tcl -- synthesis keeps every top-level
#                      register that drives an output port (opt_merge no longer folds equal pin registers).
RECIPE_LATEST = 2
RECIPE_HOLD_PAD = "HB2xp67_ASAP7_75t_R"
HOLD_PAD_STRONG = "HB4xp67_ASAP7_75t_R"
PIN_REG_SPLIT_TCL = "physical/common_flow/pin_reg_split.tcl"
RECIPE_HOLD_MARGIN_NS = 0.030
RECIPE_HALO_UM = 5.4
# a spec that already owns the boundary placement keeps it (no default pin hooks on top of it)
RECIPE_OWN_HOOK_VARS = ("POST_TAPCELL_TCL", "PRE_GLOBAL_PLACE_TCL", "PRE_DETAIL_PLACE_TCL")


class SpecError(ValueError):
    pass


def pin_group_max(s: dict) -> int:
    """Bound ordered pin chunks without changing tracks, density or bit order."""
    n = s.get("route", {}).get("pin_group_max", 32)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 32:
        raise SpecError("route.pin_group_max must be an integer 1..32")
    return n


def snap_up(v: float, g: float) -> float:
    return round(math.ceil(v / g - 1e-9) * g, 4)


def snap(v: float, g: float) -> float:
    return round(round(v / g) * g, 4)


def metal(layer):
    m = re.fullmatch(r"M(\d+)", str(layer or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------------------------- recipe
def kit_recipe(s: dict, out_root: Path | None = None, spec_path: str | None = None) -> int:
    """spec "recipe", else the RECIPE= line of the kit's existing kit.env, else 1 when a kit.env exists (generated before
    recipes), else RECIPE_LATEST (a new kit).  The kit.env NEXT TO a kit's own spec.json comes first: the submit gate
    regenerates a kit extracted at its commit into a temporary directory, with ROOT = the daemon tree (no kits there), and
    an old kit must not be judged against the new-kit defaults."""
    v = s.get("recipe")
    if v is None:
        env = (out_root or ROOT) / kit_dir(s) / "kit.env"
        if spec_path and Path(spec_path).name == "spec.json" and (Path(spec_path).parent / "kit.env").is_file():
            env = Path(spec_path).parent / "kit.env"
        if env.is_file():
            m = re.search(r"^RECIPE=(\d+)\s*$", env.read_text(errors="replace"), re.M)
            v = int(m.group(1)) if m else 1
        else:
            v = RECIPE_LATEST
    if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= RECIPE_LATEST:
        raise SpecError(f"spec: recipe must be an integer 1..{RECIPE_LATEST}, got {v!r}")
    return v


def apply_recipe(s: dict, recipe: int) -> dict:
    """write the recipe's defaults into the spec (in place; idempotent).  Recipe 1 leaves the spec untouched."""
    if recipe < 2:
        return s
    s["recipe"] = recipe
    r = s["route"]
    r.setdefault("hold_margin_ns", RECIPE_HOLD_MARGIN_NS)
    r.setdefault("macro_halo_um", RECIPE_HALO_UM)
    own = [k for k in RECIPE_OWN_HOOK_VARS if k in s.get("orfs_vars", {})]
    if not own:
        s.setdefault("io_flop_at_pins", {"cols": 4, "allow_none": True})
        # route.hold_delay: the RTL already carries its own kept HB delay cells at the boundary
        if not r.get("hold_delay"):
            s.setdefault("inhold", True)
            s.setdefault("outhold", True)
    if s.get("io_flop_at_pins"):
        s.setdefault("keep_pin_regs", True)
        if s.get("inhold") or s.get("outhold"):       # the split runs inside the recipe-2 pin hook (pre_gpl.tcl)
            s.setdefault("pin_reg_split", True)
    if (s.get("inhold") or s.get("outhold")) and "OT_INHOLD_MASTER" not in s.get("orfs_vars", {}):
        s.setdefault("hold_pad", {"cell": RECIPE_HOLD_PAD})
    return s


def hold_pad_vars(s: dict) -> list:
    """spec "hold_pad" {"cell", "out_cell", "strong_ports", "strong_cell", "basis"} -> --orfs-var items for leaf_inhold / leaf_iohold"""
    hp = s.get("hold_pad")
    if not hp or not (s.get("inhold") or s.get("outhold")):
        return []
    if not isinstance(hp, dict):
        raise SpecError('spec: hold_pad must be {"cell": ..., ["strong_ports": regexp, "basis": text]}')
    out = []
    ov = s.get("orfs_vars", {})
    cell = hp.get("cell", RECIPE_HOLD_PAD)
    if not re.fullmatch(r"HB[1-4]xp67_ASAP7_75t_[RLS]L?", str(cell)):
        raise SpecError(f"spec: hold_pad.cell {cell!r} is not an ASAP7 HB hold cell")
    if "OT_INHOLD_MASTER" in ov:
        raise SpecError("spec: hold_pad and orfs_vars OT_INHOLD_MASTER both set the pin pad; keep hold_pad only")
    out.append(f"--orfs-var OT_INHOLD_MASTER={cell}")
    # "out_cell" (S81 VM F6 2026-10-15): the OUTPUT pad (leaf_iohold BUF -> pad -> BUF) may differ from the input pad: a
    # light HB1 gives the flop -> pin path a fixed sender-min hold delay (~38 ps FF) at a launch cost (~55 ps TT) that a
    # 220 ps native launch budget can carry, where the input pad stays HB2.  Default: the input pad (kits unchanged).
    oc = hp.get("out_cell")
    if oc is not None:
        if not s.get("outhold"):
            raise SpecError("spec: hold_pad.out_cell needs outhold")
        if not re.fullmatch(r"HB[1-4]xp67_ASAP7_75t_[RLS]L?", str(oc)):
            raise SpecError(f"spec: hold_pad.out_cell {oc!r} is not an ASAP7 HB hold cell")
        out.append(f"--orfs-var OT_OUTHOLD_MASTER={oc}")
    sp = hp.get("strong_ports")
    if sp:
        try:
            re.compile(sp)
        except re.error as ex:
            raise SpecError(f"spec: hold_pad.strong_ports is not a regexp: {ex}") from ex
        if not str(hp.get("basis", "")).strip():
            raise SpecError("spec: hold_pad.strong_ports needs \"basis\": the routed FF hold report (job, endpoints, slack) "
                            "that measured the default pad short on those pins")
        if re.search(r"[\s'\"]", sp):
            raise SpecError("spec: hold_pad.strong_ports must not contain whitespace or quotes")
        sc = hp.get("strong_cell", HOLD_PAD_STRONG)
        if not re.fullmatch(r"HB[1-4]xp67_ASAP7_75t_[RLS]L?", str(sc)):
            raise SpecError(f"spec: hold_pad.strong_cell {sc!r} is not an ASAP7 HB hold cell")
        out += [f"--orfs-var OT_HOLD_PAD_STRONG_RE={shq(sp)}", f"--orfs-var OT_HOLD_PAD_STRONG_MASTER={sc}"]
    return out


MACRO_EDGE_GUARD_TCL = f"{QDM}/sram_edge_guard.tcl"          # -> physical/common_flow/macro_edge_via_guard.tcl
EDGE_GUARD_RE = re.compile(r"(sram_edge_guard|macro_edge_\w*guard)\.tcl$")


def macro_edge_guard(s: dict) -> bool:
    """recipe 2 default (el1014-root-macro-edge): a leaf tile with hard macros routes with the macro-edge via guard
    (physical/common_flow/macro_edge_via_guard.tcl through qwen_die_masters/sram_edge_guard.tcl: the top routing layer
    is taken out of the GCells straddling each macro edge before GRT and given back after DRT, so no net is assigned an
    over-macro track it can only leave by an M4 jog through the macro OBS).  Measured: the M4 Short / Metal Spacing
    markers at SRAM / ROM pin faces of qkd_sbufp q14, qfd_bl_lane cs2, PARK wide1 Q2/Q3, the slab column and P12 are
    all this shape; the guard costs no GRT capacity a pin needs (xf n12 GRT replay: 112 overflow with it, 111 without).
    A spec that already sources its own edge guard (boundary_tcl *edge*guard*.tcl) keeps it; "macro_edge_guard": false
    opts out (recipe-1 kits regenerate unchanged)."""
    if s.get("recipe", 1) < 2 or s["kind"] != "tile" or not s.get("macros"):
        return False
    if s.get("macro_edge_guard") is False:
        return False
    return not any(EDGE_GUARD_RE.search(str(f)) for f in s.get("boundary_tcl", []))


def pin_hook_wrapper(s: dict) -> bool:
    """recipe 2: pin flops AND pin hold stages -> one kit-local PRE_GLOBAL_PLACE / PRE_DETAIL_PLACE hook"""
    return bool(s.get("io_flop_at_pins") and (s.get("inhold") or s.get("outhold")) and s.get("recipe", 1) >= 2)


def gen_pin_hooks(s: dict) -> dict:
    if not pin_hook_wrapper(s):
        if s.get("pin_hook_before_flops"):
            raise SpecError("pin_hook_before_flops needs the recipe-2 pin-hook wrapper (io_flop_at_pins + inhold/outhold, recipe >= 2)")
        return {}
    hold = "leaf_iohold.tcl" if s.get("outhold") else "leaf_inhold.tcl"
    pre_gpl = ["# ref_tile PRE_GLOBAL_PLACE (kit recipe 2): the hold stages are inserted FIRM at the pins first, then every",
               "# port's single launch / capture flop is traced THROUGH them (OT_OFLOP_HOPS) and fixed at its pin.  ORFS takes",
               "# one hook per step, so the two repo hooks are sourced from this kit file.",
               f"source /src/physical/dsrom_window_source/{hold}",
               f"source /src/{QDM}/io_flop_at_pins.tcl"]
    if s.get("pin_reg_split"):
        # one dedicated launch flop per output pin BEFORE the hold stages walk flop -> port (el1014-root-recipe2)
        pre_gpl.insert(3, f"source /src/{PIN_REG_SPLIT_TCL}")
    # spec "pin_hook_before_flops": repo Tcl hooks sourced after the hold stages and BEFORE the pin flops are fixed
    # (e.g. a relay master's bit-to-pin alignment); safe relative repo paths only, and they join the source-sync list.
    for rel in s.get("pin_hook_before_flops", []):
        if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts or not re.fullmatch(r"[A-Za-z0-9_./-]+", rel):
            raise SpecError("pin_hook_before_flops must name safe relative repo Tcl files")
        if not (ROOT / rel).is_file():
            raise SpecError(f"missing pin hook: {rel}")
        pre_gpl.insert(-1, f"source /src/{rel}")
    pre_dpl = ["# ref_tile PRE_DETAIL_PLACE (kit recipe 2): release the FIRM hold cells / drivers and the pin flops for DPL",
               "source /src/physical/dsrom_window_source/leaf_inhold_release.tcl",
               f"source /src/{QDM}/out_flop_release.tcl"]
    return {"pre_gpl.tcl": "\n".join(pre_gpl) + "\n", "pre_dpl.tcl": "\n".join(pre_dpl) + "\n"}


# --------------------------------------------------------------------------------------------- spec
def load_spec(path: str) -> dict:
    s = json.loads(Path(path).read_text())
    for k in ("name", "top", "sources", "clock_port", "pins"):
        if k not in s:
            raise SpecError(f"spec: missing '{k}'")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", s["name"]):
        raise SpecError("spec: name must be [a-z0-9_]+ (it names the kit dir and the job)")
    s.setdefault("kind", "tile")
    if s["kind"] not in ("tile", "cluster"):
        raise SpecError("spec: kind must be tile or cluster")
    s.setdefault("params", {})
    s.setdefault("macros", [])
    s.setdefault("children", [])
    s.setdefault("route", {})
    pin_group_max(s)
    clock_entry_constraints.signoff_period(s)
    s.setdefault("reset_ports", [])
    s.setdefault("inter", [])
    direct_entries = s.get("clock") in ("entries", "hybrid_entries") and any(m.get("clock_entry") for m in s["macros"])
    if s["kind"] == "cluster" and not s["children"] and not direct_entries:
        raise SpecError("spec: a cluster needs hard children (children[])")
    if s["kind"] == "tile" and s["children"]:
        raise SpecError("spec: a leaf tile has no hard children (use kind cluster)")
    # "clock": "entries" (coordinator 2026-10-13, die clock delivery rule): a WIRES-ONLY cluster has no tree; every hard
    # child gets its clock from its OWN port on the cluster face ("clock_ports": one scalar port per child clock pin, the
    # RTL wires port -> child clock pin).  The die delivers phi - R_i at each entry (R_i = entry wire + the child's routed
    # boundary insertion).  "clock_port" stays the first entry (kit CLKPORT, legacy readers).
    if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        cps = s.get("clock_ports")
        if (s.get("clock") == "multiple_cts_roots" and s["kind"] != "tile" or s.get("clock") == "entries" and s["kind"] != "cluster") or not isinstance(cps, list) or not cps or s["clock_port"] != cps[0]:
            raise SpecError('spec: clock entries/hybrid_entries require kind cluster; multiple_cts_roots requires kind tile; '
                            'each requires clock_ports and clock_port == clock_ports[0]')
        if len(set(cps)) != len(cps) or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", c) for c in cps):
            raise SpecError("spec: clock_ports must be distinct scalar names or literal bus bits")
        if s.get("clock") == "multiple_cts_roots":
            if any(s.get(k) for k in ("sdc_extra", "boundary_tcl", "pre_cts_extra", "forwarded_clock")):
                raise SpecError("multiple_cts_roots owns the clock relationship and boundary; custom timing/clock hooks are unsupported")
            if s.get("clock_cts_roots") is not None:
                raise SpecError("multiple_cts_roots derives every CTS root from clock_ports")
            clock_entry_constraints.domains(s)
        elif s.get("clock") == "hybrid_entries":
            roots = s.get("clock_cts_roots")
            if not isinstance(roots, list) or not roots or not all(isinstance(p, str) for p in roots) or len(set(roots)) != len(roots) or not set(roots) < set(cps):
                raise SpecError("hybrid_entries needs distinct clock_cts_roots, a nonempty proper subset of clock_ports")
            if s["kind"] == "tile":
                if any(s.get(k) for k in ("sdc_extra", "boundary_tcl", "pre_cts_extra", "forwarded_clock")):
                    raise SpecError("hybrid_entries leaf owns clock relationships and boundaries; custom timing hooks are unsupported")
                direct = clock_entry_constraints.direct_macro_clock_entries.load(s, ROOT)
                if {e["port"] for e in direct["entries"]} != set(cps) - set(roots):
                    raise SpecError("hybrid_entries leaf requires explicit raw macro clock entries for every non-CTS port")
                clock_entry_constraints.domains(s)
        elif s.get("clock_cts_roots") is not None:
            raise SpecError("clock_cts_roots requires hybrid_entries")
        if s.get("clock_entry_domains") is not None:
            clock_entry_constraints.domains(s)
    elif s.get("clock_cts_roots") is not None:
        raise SpecError("clock_cts_roots requires hybrid_entries")
    elif s.get("clock_ports"):
        raise SpecError('spec: "clock_ports" requires entries or hybrid_entries')
    if s["pins"] == "auto":   # inputs S, outputs N, clock + resets W (a starting plan; set real faces per the die contract)
        import textbook_lint as TL  # noqa: E402
        mods = TL.rtl_modules([(ROOT / f).read_text(errors="replace") for f in s["sources"] if (ROOT / f).exists()])
        if s["top"] not in mods:
            raise SpecError(f"pins auto: top {s['top']} not found in the sources")
        dirs = TL.module_port_dirs(mods[s["top"]])
        side = set(clock_ports(s) + list(s["reset_ports"]))
        s["pins"] = {"S": [p for p, d in dirs.items() if d == "input" and p not in side],
                     "N": [p for p, d in dirs.items() if d != "input" and p not in side],
                     "W": [p for p in dirs if p in side]}
    bad = [f for f in s["pins"] if f not in FACES and f != "ANY"]
    if bad:
        raise SpecError(f"spec: pins faces must be N/S/E/W (or ANY: placer's choice, all faces), got {bad}")
    for f, names in s["pins"].items():
        for n in names:
            if re.search(r"\[\s*\d+\s*(:\s*\d+\s*)?\]", n):
                raise SpecError(f"spec: pin plan names a bit/range '{n}' on {f}: name ports by base name only (a 1-bit "
                                f"[0:0] port is a scalar after synthesis: PPL-0061 'Pins {{ck[0]}} not found')")
    return s


def contract_slot(s: dict) -> dict | None:
    c = s.get("contract")
    if not c:
        return None
    slot = child_lint.contract_slot(str(ROOT / c["file"]), c["slot"])
    if isinstance(slot, dict) and isinstance(slot.get("layer_cap"), dict):
        # derived contracts (qwen_rom_tp8 v3) carry {"cap": "M5", "view_max_layer": ..., "conforms": ...}: the cap is "cap"
        slot = dict(slot, layer_cap=slot["layer_cap"].get("cap"))
    return slot


def view_name(view: str) -> str:
    return Path(view.rstrip("/")).name


def read_view_lef(view: str) -> dict:
    p = ROOT / view / f"{view_name(view)}.lef"
    if not p.exists():
        raise SpecError(f"view {view}: {p.relative_to(ROOT)} missing")
    return child_lint.parse_lef(p.read_text(errors="replace"), view_name(view))


def track_macro(view: str) -> dict:
    p = ROOT / view / f"{view_name(view)}.lef"
    ms = cmta.parse_lef(p.read_text(errors="replace"))
    return next((m for m in ms if m["name"] == view_name(view)), ms[0])


# --------------------------------------------------------------------------------------------- layer contract
LEGACY_KITS = json.loads((Path(__file__).resolve().parent / "legacy_layer_kits.json").read_text())["kits"]
PIN_LAYERS = {"M5": ("M4", "M5"), "M6": ("M4 M6", "M5")}     # default (IO_PLACER_H, IO_PLACER_V) per tile cap


def tile_cap(s: dict, slot: dict | None) -> tuple[str, str]:
    """(cap, why) for a leaf tile under the 2026-10-12 layer contract (results/arch/hier_contract_1011/layer_usage_1012.md):
    signals AND PG stop at layer_cap = M5 (PG stripes on M5 as pins, pins on M4/M5, parent straps M6, die signals M6/M7
    over the tile, M8/M9 die power + global); M6 only by a die-lead exception (spec or slot layer_cap M6 + layer_cap_grant);
    kits generated before the cut (legacy_layer_kits.json) keep their old PG layer (M6/M7, signals <= M6)."""
    slot = slot or {}
    cap = s.get("layer_cap") or slot.get("layer_cap")
    grant = s.get("m6_pin_grant") or slot.get("m6_pin_grant")
    if grant is not None:
        import m6_pin_grant as M6
        try:
            M6.validate(grant, s["top"])
        except (ValueError, TypeError, KeyError) as ex:
            raise SpecError(str(ex)) from ex
        if cap not in (None, "M5") or s.get("pg_layer") not in (None, "M5"):
            raise SpecError("M6 pin-only grant requires signal/PG layer_cap M5")
        return "M5", "pin-only grant"
    if cap is None and s["name"] not in LEGACY_KITS:
        # re-read: the closure daemon imports this module once, and a native-launch re-kit
        # (tools/ref_tile/rekit_native_launch.py) freezes a closed pre-M5 kit here while it runs
        try:
            LEGACY_KITS.update(json.loads((Path(__file__).resolve().parent / "legacy_layer_kits.json").read_text())["kits"])
        except (OSError, ValueError, KeyError):
            pass
    if cap is None and s["name"] in LEGACY_KITS:
        return LEGACY_KITS[s["name"]], "legacy"
    if cap is None and s.get("pg_layer") not in (None, "M5"):
        raise SpecError(f"layer contract: a NEW leaf tile caps signals and PG at M5 (coordinator 2026-10-12): drop "
                        f"pg_layer {s['pg_layer']}, or set layer_cap M6 with the die lead's layer_cap_grant")
    cap = cap or "M5"
    if cap == "M6":
        if not (s.get("layer_cap_grant") or slot.get("layer_cap_grant")):
            raise SpecError("layer contract: layer_cap M6 is a per-tile exception the die lead grants (pin-dense edge "
                            "relays / stations): give layer_cap_grant '<lead>: <reason>' in the spec or the contract slot")
        return "M6", "granted"
    if cap != "M5":
        raise SpecError(f"layer contract: a leaf tile's layer_cap is M5 (default) or M6 (granted exception), not {cap}")
    return "M5", "contract"


def cluster_signal_cap(s: dict, slot: dict | None = None) -> tuple[str, dict | None]:
    """Upper cluster metals require a digest-bound die contract, never a text waiver.

The grant carries the no-through-traffic and phase-aligned PG obligations. A
probe may measure routing before the phase audit exists, but cannot auto-merge.
"""
    cap = s.get("signal_max_layer") or (slot or {}).get("signal_max_layer") or "M7"
    slot_cap = (slot or {}).get("signal_max_layer")
    if slot_cap is not None and (metal(slot_cap) is None or metal(cap) is None or metal(cap) > metal(slot_cap)):
        raise SpecError(f"cluster signal cap {cap} exceeds contract slot signal_max_layer {slot_cap}")
    if cap in ("M6", "M7"):
        return cap, None
    if cap not in ("M8", "M9"):
        raise SpecError(f"cluster signal cap must be M6/M7, or die-granted M8/M9, not {cap}")
    g = s.get("cluster_layer_grant") or (slot or {}).get("cluster_layer_grant")
    if not isinstance(g, dict) or not g.get("source") or not g.get("sha256"):
        raise SpecError("cluster M8/M9 needs cluster_layer_grant {source, sha256}")
    p = (ROOT / g["source"]).resolve()
    if not p.is_relative_to(ROOT.resolve()) or not p.is_file():
        raise SpecError("cluster layer grant source must be an existing repository file")
    if hashlib.sha256(p.read_bytes()).hexdigest() != g["sha256"]:
        raise SpecError("cluster layer grant source digest mismatch")
    try:
        rec = json.loads(p.read_text())
    except (ValueError, OSError) as ex:
        raise SpecError("cluster layer grant source is not a JSON contract") from ex
    if rec.get("schema") != "opentallas.cluster-layer-grant.v1" or rec.get("signal_cap") != cap:
        raise SpecError("cluster layer grant schema/cap mismatch")
    if s["name"] not in rec.get("masters", []):
        raise SpecError("cluster layer grant does not name this master")
    if rec.get("no_die_signal_through_traffic") is not True or rec.get("die_pg_layers") != ["M8", "M9"]:
        raise SpecError("upper cluster grant must reserve die M8/M9 for PG only over its rectangle")
    pg = rec.get("die_pg", {})
    if not all(isinstance(pg.get(k), (int, float)) and pg[k] > 0 for k in ("width_um", "pitch_um")):
        raise SpecError("cluster grant must declare the die PG width and pitch")
    if rec.get("requires_phase_aligned_die_pg") is not True:
        raise SpecError("cluster grant must require die-core phase aligned PG")
    if not s.get("job", {}).get("hold_merge"):
        import cluster_pg_phase
        try:
            cluster_pg_phase.validate(ROOT, s.get("die_pg_phase_audit", {}), s, g)
        except (ValueError, KeyError, TypeError, OSError) as ex:
            raise SpecError(f"production upper cluster PG geometry audit failed: {ex}; use hold_merge for a probe") from ex
    return cap, {"source": g["source"], "sha256": g["sha256"], "obligations": rec}


def layer_contract(s: dict, slot: dict | None) -> dict:
    """leaf tile: signals AND PG <= layer_cap (M5 default, M6 granted), PG = full-length stripes on the cap layer as pins,
    parent strap = cap + 1; legacy kits: signals M2-M6, PG M6 or M7.
    cluster: children's PG layer L <= M6 each strapped from L+1; cluster PG = M7 stripes as pins; signals M2-M7."""
    pg = s.get("pg_layer") or (slot or {}).get("pg_layer")
    out = {"children": {}}
    if s["kind"] == "tile":
        cap, why = tile_cap(s, slot)
        if why == "legacy":
            out.update(pg_layer=cap, rlayers=("M2", "M6"), strap_layer=f"M{metal(cap) + 1}", layer_cap=cap,
                       cap_basis="legacy kit (pre-2026-10-12 contract; re-route at M5 per m5_reroute_priority.json)")
        else:
            out.update(pg_layer=cap, rlayers=("M2", cap), strap_layer=f"M{metal(cap) + 1}", layer_cap=cap, cap_basis=why)
        if s.get("m6_pin_grant") or (slot or {}).get("m6_pin_grant"):
            out["m6_pin_grant"] = s.get("m6_pin_grant") or slot["m6_pin_grant"]
        if slot:
            ok = {slot.get("layer_cap") or slot.get("pg_layer"), slot.get("view_cap") if why == "legacy" else None}
            if out["pg_layer"] not in ok:
                raise SpecError(f"layer contract: tile cap/PG {out['pg_layer']} != contract slot layer_cap "
                                f"{slot.get('layer_cap') or slot.get('pg_layer')}")
        # An explicit lower signal ceiling does not move the PG mesh or its
        # parent strap. Never use this field to widen an existing route cap.
        sig = s.get("signal_max_layer")
        if sig is not None:
            limit = metal(out["rlayers"][1])
            slot_sig = metal((slot or {}).get("signal_max_layer"))
            if slot_sig is not None:
                limit = min(limit, slot_sig)
            if metal(sig) is None or not 2 <= metal(sig) <= limit:
                raise SpecError(f"tile signal_max_layer {sig!r} must be M2..M{limit}; it cannot loosen the layer contract")
            out.update(rlayers=("M2", sig), signal_max_layer=sig)
        return out
    for ch in s["children"]:
        m = read_view_lef(ch["view"])
        top = child_lint.check_pg(m)["top_layer"]
        if metal(top) is None or metal(top) > 6:
            raise SpecError(f"layer contract: child {view_name(ch['view'])} PG top layer {top}: a cluster child must "
                            f"expose PG on M5/M6 (the cluster straps one layer up on M7; M8/M9 are the die's)")
        out["children"][view_name(ch["view"])] = top
    pg = pg or "M7"
    if pg != "M7":
        raise SpecError("layer contract: a cluster's PG layer is M7 (straps over M5/M6 children; M8/M9 die only)")
    cap, grant = cluster_signal_cap(s, slot)
    out.update(pg_layer="M7", rlayers=("M2", cap), strap_layer="M8")
    if cap == "M6":
        # Signal restriction is independent of the cluster's PG mesh. Export
        # must prove the actual routed signal/clock wires stop below M7 PG.
        out["signal_max_layer"] = cap
    if grant:
        out["cluster_layer_grant"] = grant
    if slot and slot.get("pg_layer") and slot["pg_layer"] != out["pg_layer"]:
        raise SpecError(f"layer contract: spec PG {out['pg_layer']} != contract slot PG {slot['pg_layer']}")
    return out


def clock_rlayers(lc: dict) -> tuple[str, str] | None:
    """Explicit clock routing range for a signal cap below M5, else None (platform default kept).
    ASAP7 fastroute.tcl routes clocks on MIN_CLK_ROUTING_LAYER (M4)..MAX_ROUTING_LAYER, and OpenROAD
    set_routing_layers rejects a clock range whose min is not strictly below its max (ODB-0137, measured
    2026-10-14: M4-M4 and M5-M4 fail, M3-M4 passes). A cap of M4/M3 therefore routes clocks on the top
    two allowed layers (one per direction); a cap below M3 cannot route a clock."""
    cap = metal(lc["rlayers"][1])
    if cap is None or cap >= 5:
        return None
    if cap < 3:
        raise SpecError(f"signal cap {lc['rlayers'][1]} leaves no two-layer clock routing range (needs >= M3)")
    return (f"M{cap - 1}", f"M{cap}")


def pin_layers(s: dict, lc: dict) -> tuple[str, str]:
    """(IO_PLACER_H, IO_PLACER_V) for the kit; every pin layer must be <= the tile's cap (no pin on the parent strap)."""
    r = s["route"]
    cap = lc["rlayers"][1]
    dh, dv = PIN_LAYERS.get(cap if cap in PIN_LAYERS else "M6")
    if lc.get("cap_basis", "").startswith("legacy"):
        dh, dv = PIN_LAYERS["M6"]
    if s.get("signal_max_layer"):
        if metal(cap) == 4:
            dh, dv = "M4", "M3"
        elif metal(cap) == 3:
            dh, dv = "M2", "M3"
        elif metal(cap) < 3:
            dh, dv = cap, cap
    h, v = r.get("pin_h", dh), r.get("pin_v", dv)
    if s["kind"] == "tile":
        pb = r.get("pin_balance") or {}
        used = (h + " " + v + " " + pb.get("h", "") + " " + pb.get("v", "")).split()
        over = sorted({x for x in used if (metal(x) or 0) > metal(lc["rlayers"][1])})
        if over and not (over == ["M6"] and lc.get("m6_pin_grant") and cap == "M5"):
            raise SpecError(f"layer contract: pin layers {over} above the tile's signal cap {lc['rlayers'][1]} "
                            f"(pins on M4/M5 under the M5 cap; the parent reaches them from M6)")
    return h, v


PDN_HEAD = """# generated by tools/ref_tile/ref_tile.py ({name}, {kind}): layer contract PG top {pg} as full-length stripes = the
# block's power pins; {note}
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDDPE$}}
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDDCE$}}
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSSE$}}
global_connect
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{top}} -voltage_domains {{CORE}} -pins {{{pg}}}
add_pdn_stripe -grid {{top}} -layer {{M1}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M2}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M5}} -width {{0.12}} -spacing {{0.072}} -pitch {{{m5_pitch}}} -offset {{0.300}}
"""
# Macro grids exist ONLY for masters present in the block (PDN-0217 'No grid found with name' otherwise: a macro grid
# with no matching instance is never created and its add_pdn_connect aborts).
PDN_GUARD = """proc ot_ref_has_master {pats} {
  foreach inst [[ord::get_db_block] getInsts] {
    set m [[$inst getMaster] getName]
    foreach p $pats { if {[string match $p $m]} { return 1 } }
  }
  return 0
}
proc ot_ref_present {cells} { set out {}; foreach c $cells { if {[ot_ref_has_master $c]} { lappend out $c } }; return $out }
"""


def gen_pdn(s: dict, lc: dict) -> str:
    pg = lc["pg_layer"]
    if s["kind"] == "tile" and pg == "M5":
        note = ("layer cap M5: signals M2-M5 route around the M5 stripes (pins); the parent straps M6, die signals use "
                "M6/M7 over the tile (coordinator 2026-10-12).")
        body = "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
    elif s["kind"] == "tile" and pg == "M6":
        note = "signals M2-M6 route around the M6 stripes; the parent straps M7 (recipe pdn_qkvd_tile_m6.tcl)."
        # route.pg_pitch (5.4 or 10.8, both on the strap lattice): short tiles (< ~3 pitches tall) need 5.4 so the M6
        # PG pins span >= 50% of the height (child_lint (b); dsfd_vm_fsr r4 at 25.92 um: 2 stripes per net = 42%)
        pp = float(s.get("route", {}).get("pg_pitch", 10.8))
        assert pp in (5.4, 10.8), "route.pg_pitch must be 5.4 or 10.8"
        body = (f"add_pdn_stripe -grid {{top}} -layer {{M6}} -width {{0.288}} -spacing {{0.096}} -pitch {{{pp}}} -offset {{2.0}}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\n")
    elif s["kind"] == "tile":
        note = "signals stop at M6 (RLAYERS M2 M6), M7 = PG stripes only; the parent straps M8 (recipe g8p/pdn_gtile.tcl)."
        body = ("add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}\n"
                "add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\nadd_pdn_connect -grid {top} -layers {M6 M7}\n")
    else:
        note = ("cluster: M5/M6 stripes + M7 stripes (pins); each hard child strapped from the layer above its own PG pins "
                "(recipe physical/hgi_idx_hier/pdn_hier.tcl @8d848821f).")
        body = ("add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}\n"
                "add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\nadd_pdn_connect -grid {top} -layers {M6 M7}\n")
    # route.m5_pg_pitch (5.4 default, or 2.7: every other stripe still on the 5.4 lattice): a narrow M5-cap tile (< ~3
    # pitches wide) gets only 2 stripes per net at 5.4, so its M5 PG pins span < 50% of the width and the export
    # child_lint (b) fails (qfd_embed_ingress_code/scale_m5 at 15.12 um: 36%, 2026-10-12)
    m5p = float(s.get("route", {}).get("m5_pg_pitch", 5.4))
    assert m5p in (2.7, 5.4), "route.m5_pg_pitch must be 2.7 or 5.4"
    t = PDN_HEAD.format(name=s["name"], kind=s["kind"], pg=pg, note=note, m5_pitch=f"{m5p:g}") + body + PDN_GUARD
    by_layer: dict = {}
    for cell, top in lc["children"].items():
        by_layer.setdefault(top, []).append(cell)
    for top, cells in sorted(by_layer.items()):
        L = metal(top)
        t += (f"set ot_c [ot_ref_present {{{' '.join(sorted(cells))}}}]\n"
              f"if {{[llength $ot_c]}} {{\n"
              f"  define_pdn_grid -name {{hard_{top.lower()}}} -voltage_domains {{CORE}} -macro -cells $ot_c "
              f"-orient {{R0 R180 MX MY}} -halo {{2.0 2.0 2.0 2.0}}\n"
              f"  add_pdn_connect -grid {{hard_{top.lower()}}} -layers {{M{L} M{L + 1}}}\n}}\n")
    srams = sorted({view_name(m["view"]) for m in s["macros"]})
    if srams:
        t += (f"set ot_s [ot_ref_present {{{' '.join(srams)}}}]\n"
              "if {[llength $ot_s]} {\n"
              "  define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -cells $ot_s -orient {R0 R180 MX MY} "
              "-halo {2.0 2.0 2.0 2.0}\n  add_pdn_connect -grid {sram} -layers {M4 M5}\n}\n")
    return t


# --------------------------------------------------------------------------------------------- floorplan
def outline(s: dict, slot: dict | None, area_um2: float | None, blocks: list) -> tuple[float, float, str]:
    if slot:
        return float(slot["outline"]["w"]), float(slot["outline"]["h"]), f"contract {s['contract']['slot']}"
    og = TRACK_LATTICE_UM if s["kind"] == "cluster" else GRID_Y
    if s.get("outline"):
        o = s["outline"]
        if o.get("exact"):      # a drop-in replacement of a closed view inside a fixed sub-slot (dsfd_vm_clt 80.64 x 230.04)
            return float(o["w"]), float(o["h"]), "spec outline (exact: the closed view's sub-slot)"
        return snap_up(float(o["w"]), og), snap_up(float(o["h"]), og), "spec outline"
    area = area_um2 or s.get("std_area_um2")
    if not area:
        raise SpecError("outline: give outline {w,h}, a contract slot, or std_area_um2 / --area-um2 (the synthesis "
                        "smoke of pre_route_gate.py --remote reports it) with util (default 0.52)")
    util = float(s.get("util", UTIL_TARGET))
    halo = float(s["route"].get("macro_halo_um", HALO_UM)) if s.get("recipe", 1) >= 2 else HALO_UM
    mac = sum((b["w"] + 2 * halo) * (b["h"] + 2 * halo) for b in blocks)
    core = (area + mac) / util
    ar = float(s.get("aspect", 1.0))                   # w / h
    w = math.sqrt(core * ar) + 2 * CORE_MARGIN
    h = core / (w - 2 * CORE_MARGIN) + 2 * CORE_MARGIN
    for b in blocks:                                    # every macro must fit with channels on both sides
        w = max(w, b["w"] + 2 * CHANNEL_UM + 2 * CORE_MARGIN)
        h = max(h, b["h"] + 2 * CHANNEL_UM + 2 * CORE_MARGIN)
    return snap_up(w, og), snap_up(h, og), f"util {util} of std {area:.0f} + macros {mac:.0f} um2"


def blocks_of(s: dict) -> list:
    out = []
    for kind, items in (("macro", s["macros"]), ("child", s["children"])):
        for i, it in enumerate(items):
            m = read_view_lef(it["view"])
            out.append({"kind": kind, "view": it["view"], "master": m["name"], "inst": it.get("inst"),
                        "w": m["W"], "h": m["H"], "at": it.get("at"), "orient": it.get("orient", "R0"),
                        "count": int(it.get("count", 1)), "exact": bool(it.get("at_exact"))})
    # expand counts (identical instances placed in a row)
    exp = []
    for b in out:
        for k in range(b["count"]):
            c = dict(b)
            c["idx"] = k
            if b["count"] > 1 and b.get("at"):
                raise SpecError(f"{b['master']}: count > 1 with a fixed 'at' -- give one entry per instance")
            exp.append(c)
    return exp


ABUT_UM = 0.1           # two macros this close in one axis (and overlapping in the other) are one abutted stack


def abutted_stack(a: dict, b: dict, gx: float, gy: float) -> bool:
    """two MACROS stacked N-S with no cell row between them (0 <= gap <= ABUT_UM, overlapping in x) and no signal /
    clock pin of either on the two touching faces (memory arrays with their pins on W / E: a bank of arrays).  R0 / MY
    keep the LEF's top / bottom faces, MX / R180 swap them (the W / E test is mirror-symmetric); rotated (R90 / R270 ...)
    macros, hard children and side-by-side macros keep the channel rule (their touching faces carry pins / need straps).
    MY admitted 2026-10-14 (s81-gather r4): a mirrored bank faces its pins at the logic between two banks."""
    flip = {"R0": False, "MY": False, "MX": True, "R180": True}
    if a["kind"] != "macro" or b["kind"] != "macro" or a.get("orient", "R0") not in flip or b.get("orient", "R0") not in flip:
        return False
    if not (-1e-6 <= gy <= ABUT_UM + 1e-6 and gx < -1e-6):
        return False
    lo, hi = (a, b) if a["y"] < b["y"] else (b, a)
    for blk, edge in ((lo, "top"), (hi, "bottom")):
        if blk.get("_tm") is None:
            blk["_tm"] = track_macro(blk["view"])
        tm = blk["_tm"]
        if flip[blk.get("orient", "R0")]:                       # the LEF face that ends up touching the neighbour
            edge = "bottom" if edge == "top" else "top"
        for pin in tm["pins"]:
            if pin["use"] not in ("SIGNAL", "CLOCK"):
                continue
            for _layer, (x0, y0, x1, y1) in pin["rects"]:
                on_w_e = x0 <= 200 or x1 >= tm["W"] - 200          # nm: a W / E face pin reaches the side edge
                if (y1 >= tm["H"] - 200 if edge == "top" else y0 <= 200) and not on_w_e:
                    return False
    return True


def on_track(b: dict, x: float, y: float) -> tuple[float, float, int]:
    """nearest origin to (x, y) that puts the block's signal pins on the asap7 tracks (DRT-0255 / 0418 / 0419)"""
    if b.get("_tm") is None:
        b["_tm"] = track_macro(b["view"])
    tm = b["_tm"]
    ox, oy = round(x * 1000), round(y * 1000)
    import macro_grid_lint as mgl  # noqa: E402
    off, dx, dy = mgl.best_shift(tm, b["orient"], ox, oy)
    if dx or dy:
        # keep the shift and stay on the row lattice in y where it costs nothing
        ox, oy = ox + dx, oy + dy
    # best_shift scores shapes while the access rule accepts each pin's best
    # shape per layer. Recheck the chosen origin with that actual pin rule.
    report = cmta.check_placement(tm, b["orient"], ox, oy)
    off = sum(v["offtrack"] for v in report["layers"].values())
    return ox / 1000.0, oy / 1000.0, off


def place_blocks(s: dict, W: float, H: float, blocks: list) -> list:
    """explicit 'at' wins; the rest go in rows away from the pin faces, >= CHANNEL_UM apart and from the core edge"""
    pin_faces = {f for f, v in s["pins"].items() if v}
    if pin_faces & {"ANY"}:
        pin_faces = set(FACES)
    x0c, y0c, x1c, y1c = CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN
    lo_x = x0c + max(CHANNEL_UM, PIN_EDGE_UM if "W" in pin_faces else 0)
    hi_x = x1c - max(CHANNEL_UM, PIN_EDGE_UM if "E" in pin_faces else 0)
    lo_y = y0c + max(CHANNEL_UM, PIN_EDGE_UM if "S" in pin_faces else 0)
    hi_y = y1c - max(CHANNEL_UM, PIN_EDGE_UM if "N" in pin_faces else 0)
    def lat(b):
        return (float(s.get("child_lattice_um", CHILD_LATTICE_UM)),) * 2 if b["kind"] == "child" else (GRID_X, GRID_Y)
    auto = [b for b in blocks if not b.get("at")]
    for b in blocks:
        if b.get("at"):
            b["_xy"] = (float(b["at"][0]), float(b["at"][1]))
    if auto:
        gx = max(lat(b)[0] for b in auto)
        gy = max(lat(b)[1] for b in auto)
        x0, y = snap_up(lo_x, gx), snap_up(lo_y, gy)
        x, row_h = x0, 0.0
        for b in auto:      # lattice-aware row packing: every channel >= CHANNEL_UM AFTER snapping
            if x + b["w"] > hi_x + 1e-6 and x > x0:
                x, y, row_h = x0, snap_up(y + row_h + CHANNEL_UM, gy), 0.0
            b["_xy"] = (x, y)
            x = snap_up(x + b["w"] + CHANNEL_UM, gx)
            row_h = max(row_h, b["h"])
        bx1 = max(b["_xy"][0] + b["w"] for b in auto)
        by1 = max(b["_xy"][1] + b["h"] for b in auto)
        sx = math.floor(max(0.0, (hi_x - bx1) / 2) / gx) * gx
        sy = math.floor(max(0.0, (hi_y - by1) / 2) / gy) * gy
        for b in auto:      # centre the array in the free window, on the lattice
            b["_xy"] = (round(b["_xy"][0] + sx, 4), round(b["_xy"][1] + sy, 4))
    for b in blocks:
        if b["kind"] == "child":
            # a hard tile built on the same lattice: its origin on the common lattice keeps every layer's pins on track
            g = float(s.get("child_lattice_um", CHILD_LATTICE_UM))
            bx, by = snap(b["_xy"][0], g), snap(b["_xy"][1], g)
            r = cmta.check_placement(track_macro(b["view"]) if b.get("_tm") is None else b["_tm"], b["orient"],
                                     round(bx * 1000), round(by * 1000))
            off = sum(v["offtrack"] for v in r["layers"].values())
            if off:   # off-lattice view (not built by this flow): nearest on-track origin instead
                bx, by, off = on_track(b, bx, by)
        elif b.get("exact") and b.get("at"):
            # macro item "at_exact": the origin as given, not snapped to the (0.432, 2.16) macro lattice: an abutted
            # N-S stack needs pitch = array height + 0.024 (abutted_stack); the pins must already be on track there
            bx, by = float(b["at"][0]), float(b["at"][1])
            r = cmta.check_placement(track_macro(b["view"]) if b.get("_tm") is None else b["_tm"], b["orient"],
                                     round(bx * 1000), round(by * 1000))
            off = sum(v["offtrack"] for v in r["layers"].values())
        else:
            bx, by = snap(b["_xy"][0], GRID_X), snap(b["_xy"][1], GRID_Y)
            bx, by, off = on_track(b, bx, by)
        b.update(x=bx, y=by, offtrack=off)
    return blocks


def floorplan_checks(s: dict, W: float, H: float, blocks: list, std_area: float | None) -> list:
    """(severity, check, message, fix) -- the geometry part of the pre-route gate, also run at gen time"""
    out = []
    pin_faces = {f for f, v in s["pins"].items() if v}
    if "ANY" in pin_faces:
        pin_faces = set(FACES)
    x0c, y0c, x1c, y1c = CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN
    # abut_plan: a held diagnostic tile/cluster at a planned channel narrower
    # than CHANNEL_UM, routed to MEASURE that channel.  {"channel_um": c, "edge_um": e, "why": "..."}: tile-tile gaps >= c
    # and tile-edge distances >= e pass as WARN "abut_plan"; only on a cluster whose job carries "hold_merge" (a probe is
    # never a closure candidate), so the 20-um rule still judges every block that can merge.
    ab = s.get("abut_plan") or None
    ab_n = {"channel": 0, "macro_edge": 0}
    if ab is not None:
        if s.get("kind") not in ("tile", "cluster") or not (s.get("job") or {}).get("hold_merge") or not ab.get("why"):
            out.append(("FAIL", "abut_plan", "abut_plan requires a held diagnostic tile/cluster and a 'why'",
                        "drop abut_plan, or make the job a probe (job.hold_merge); production keeps the20um rule"))
            ab = None
    ch_min = float(ab["channel_um"]) if ab else CHANNEL_UM
    edge_min = float(ab.get("edge_um", ab["channel_um"])) if ab else None
    for b in blocks:
        bx0, by0, bx1, by1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
        nm = f"{b['master']}#{b['idx']}"
        if bx0 < x0c - 1e-6 or by0 < y0c - 1e-6 or bx1 > x1c + 1e-6 or by1 > y1c + 1e-6:
            out.append(("FAIL", "macro_outside", f"{nm} at ({bx0},{by0}) leaves the core", "enlarge the outline"))
        for f, d in (("W", bx0 - x0c), ("E", x1c - bx1), ("S", by0 - y0c), ("N", y1c - by1)):
            need = PIN_EDGE_UM if f in pin_faces else CHANNEL_UM
            if edge_min is not None and edge_min - 1e-6 <= d < need - 1e-6:
                ab_n["macro_edge"] += 1
                continue
            if d < need - 1e-6:
                out.append(("FAIL", "macro_edge", f"{nm} {d:.1f} um from the {f} core edge (< {need:.0f} um"
                            + (", a pin face" if f in pin_faces else "") + ")",
                            "move the macro inward / to a face without pins (sliver + pin-access blockage)"))
        if b.get("offtrack"):
            out.append(("FAIL", "macro_grid", f"{nm}: {b['offtrack']} signal pins off the asap7 tracks (M1-M9, each "
                        f"layer's own pitch / offset) at its origin",
                        "no origin fixes it: the view's LEF is off-lattice -- re-export the child on the track grid"))
        if b["kind"] == "child" and any(abs(v / CHILD_LATTICE_UM - round(v / CHILD_LATTICE_UM)) > 1e-6 for v in (b["x"], b["y"])):
            out.append(("WARN", "macro_grid", f"{nm}: origin ({b['x']}, {b['y']}) off the {CHILD_LATTICE_UM} um child "
                        "lattice (lcm of site, row, M1-M7 tracks, strap pitch)", "build the child on the common lattice"))
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            gx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]))
            gy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]))
            gap = max(gx, gy)
            if gap < CHANNEL_UM - 1e-6 and abutted_stack(a, b, gx, gy):
                continue    # the deliberate abutment this check names as its fix: one macro stack, no cells between
            if ab is not None and ch_min - 1e-6 <= gap < CHANNEL_UM - 1e-6:
                ab_n["channel"] += 1
                continue
            if gap < CHANNEL_UM - 1e-6:
                out.append(("FAIL", "channel", f"{a['master']}#{a['idx']} / {b['master']}#{b['idx']} channel {gap:.1f} um "
                            f"(< {CHANNEL_UM:.0f} um)", "spread the macros, or abut two macros N-S deliberately (gap <= 0.1 um, R0 / MY / MX / R180, no pin on the touching faces: abutted_stack)"))
    if ab is not None and (ab_n["channel"] or ab_n["macro_edge"]):
        out.append(("WARN", "abut_plan", f"PROBE: {ab_n['channel']} tile-tile channels in [{ch_min:g}, {CHANNEL_UM:g}) um and "
                    f"{ab_n['macro_edge']} tile-edge distances >= {edge_min:g} um admitted by abut_plan ({ab['why'][:160]})",
                    "the route measures the channel; a block that merges obeys the 20-um rule"))
    core = (x1c - x0c) * (y1c - y0c)
    mac = sum(b["w"] * b["h"] for b in blocks)
    if std_area:
        u = (std_area + mac) / core
        if not (UTIL_LO <= u <= UTIL_HI + 0.05):
            out.append(("FAIL" if u > 0.70 else "WARN", "util",
                        f"utilisation {u:.0%} outside {UTIL_LO:.0%}-{UTIL_HI:.0%} (std {std_area:.0f} + macro {mac:.0f} "
                        f"in core {core:.0f} um2)", "resize the outline to util 0.50-0.55 (drop 'outline', set util)"))
    long_side = max(W, H)
    if long_side > 600 and s["kind"] == "tile":
        out.append(("WARN", "clock_span", f"{W} x {H} um: one clock root over > 600 um",
                    "split into hardened sub-tiles with local roots (kind cluster) or keep the sink count small"))
    return out


# --------------------------------------------------------------------------------------------- generation
def clock_ports(s: dict) -> list:
    """the clock source ports: every entry of a "clock": "entries" cluster, else the one clock_port"""
    return list(s["clock_ports"]) if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") else [s["clock_port"]]


def clock_ports_sdc(s: dict) -> str:
    cps = clock_ports(s)
    return cps[0] if len(cps) == 1 else "{" + " ".join(cps) + "}"


def pin_regex(names) -> str:
    return "^(" + "|".join(re.escape(n) for n in names) + r")(\[|$)"


def kit_dir(s: dict) -> str:
    return f"{KIT_ROOT}/{s['name']}"


def gen_place(s: dict, blocks: list) -> str:
    lines = [f"# generated by tools/ref_tile/ref_tile.py ({s['name']}): fixed macro / hard-child placement on the asap7",
             "# track lattice (origins from check_macro_track_alignment best shift), >= 20 um channels, no macro at a pin",
             "# face.  Instance names are matched with backslashes stripped on BOTH sides (the db holds g\\[1\\].u or g[1].u",
             "# depending on the stage).  A spec instance pattern (glob) picks among same-master instances; else dictionary",
             "# order.  The halo is MACRO_PLACE_HALO (rows cut by tapcell); NO extra placement blockage: a hard blockage over",
             "# the halo covers the row-end endcaps and fails detailed placement (DPL-0004 / DPL-0033, ref gate 2026-10-11).",
             "set b [ord::get_db_block]", "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
             "proc ot_ref_strip {n} { return [string map {\\\\ {}} $n] }",
             "set ot_ref_by {}",
             "set ot_ref_l {}",
             "foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend ot_ref_l [list [ot_ref_strip [$i getName]] $i] } }",
             "foreach p [lsort -dictionary -index 0 $ot_ref_l] {",
             "  set i [lindex $p 1]; dict lappend ot_ref_by [[$i getMaster] getName] $i", "}",
             "set ot_ref_used {}",
             "proc ot_ref_pick {by master pat} {",
             "  upvar ot_ref_used used",
             "  if {![dict exists $by $master]} { error \"ref_tile place: no instance of $master in the netlist\" }",
             "  foreach i [dict get $by $master] {",
             "    set n [ot_ref_strip [$i getName]]",
             "    if {[lsearch -exact $used $n] >= 0} continue",
             "    set sp [ot_ref_strip $pat]",
             "    # exact name first: a generate name g_q[0].u_rq is a glob char class to string match (never matches)",
             "    if {$pat ne \"\" && $sp ne $n && ![string match $sp $n]} continue",
             "    lappend used $n; return $i", "  }",
             "  error \"ref_tile place: no unplaced instance of $master matching '$pat'\"", "}",
             "set ot_ref_n 0"]
    for bl in blocks:
        lines.append(f"set i [ot_ref_pick $ot_ref_by {bl['master']} {{{bl.get('inst') or ''}}}]")
        lines.append(f"$i setOrient {bl['orient']}; $i setLocation [expr {{round({bl['x']} * $dbu)}}] "
                     f"[expr {{round({bl['y']} * $dbu)}}]; $i setPlacementStatus FIRM")
        lines.append(f"puts \"REF_TILE place: [$i getName] {bl['master']} at {bl['x']} {bl['y']} {bl['orient']}\"")
    lines.append("set nb 0; dict for {k v} $ot_ref_by { incr nb [llength $v] }")
    lines.append(f"if {{$nb != {len(blocks)}}} {{ error \"ref_tile place: expected {len(blocks)} macros, netlist has $nb\" }}")
    return "\n".join(lines) + "\n"


def spec_io_budget(s: dict) -> tuple:
    """spec "io_budget" {"in": f, "out": f} of a single-clock tile: the outside share of the sign-off period at the
    boundary (default 0.2 / 0.2, the nominal native pin budget).  Only TIGHTENING (0.2 <= f <= 0.8) is accepted, so a
    tile is never closed against a looser boundary than the nominal one; the same fractions reach the route SDC, the
    post-CTS boundary (io_ref_skew.sdc via OT_IO_IN_BUDGET_PS / OT_IO_OUT_BUDGET_PS) and the sign-off SDC.  Clock-entry
    modes carry it per domain (clock_entry_constraints.domain_io_budget)."""
    io = s.get("io_budget") or {}
    if set(io) - {"in", "out"}:
        raise SpecError(f"spec: io_budget unknown keys {sorted(set(io) - {'in', 'out'})}")
    vals = []
    for k in ("in", "out"):
        f = float(io.get(k, 0.2))
        if not 0.2 <= f <= 0.8:
            raise SpecError(f"spec: io_budget {k} {f} outside [0.2, 0.8] (only tightening is allowed)")
        vals.append(f)
    if io and s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        raise SpecError("spec: io_budget is per clock_entry_domains domain in clock-entry modes")
    return tuple(vals)


def io_budget_env(s: dict) -> dict:
    """OT_IO_*_BUDGET_PS for a tightened single-clock boundary ({} = nominal 0.2 T, kits unchanged)"""
    fin, fout = spec_io_budget(s)
    if (fin, fout) == (0.2, 0.2):
        return {}
    signoff = clock_entry_constraints.signoff_period(s)
    return {"OT_IO_IN_BUDGET_PS": round(signoff * fin, 3), "OT_IO_OUT_BUDGET_PS": round(signoff * fout, 3)}


def gen_sdc(s: dict, period_ps: float) -> str:
    signoff = clock_entry_constraints.signoff_period(s)
    fin, fout = spec_io_budget(s)
    return (f"# generated by tools/ref_tile/ref_tile.py ({s['name']}): route SDC (over-constrained {period_ps} ps; sign-off\n"
            f"# {signoff} in signoff.sdc), 60 / 25 ps uncertainty, boundary {fin} / {fout} x {signoff} ps outside the block.\n"
            f"# After CTS the hooks re-reference the boundary to the propagated tree (qwen_die_masters/io_ref_skew.sdc).\n"
            + "set ::ot_ref_pre_cts 1\n" + clock_entry_constraints.clocks(s, period_ps)
            + "set_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n"
            f"set_input_delay {signoff * fin:.3f} -clock core_clk [all_inputs -no_clocks]\n"
            f"set_output_delay {signoff * fout:.3f} -clock core_clk [all_outputs]\n"
            "set_max_fanout 32 [current_design]\nset_load 80 [all_outputs]\n"
            "set_max_transition 260 [current_design]\n"
            + sdc_extra(s)
            # Extra SDC may declare secondary clocks. Data slew must exclude
            # their sources; explicit source-clock transitions in extra SDC stand.
            + "set_input_transition 150 [all_inputs -no_clocks]\n"
            + clock_entry_constraints.generate(s, ROOT))


def sdc_extra(s: dict) -> str:
    """spec 'sdc_extra': repo SDC files appended (inlined) to clock.sdc and signoff.sdc -- a second clock domain
    (e.g. a CDC adapter's controller clock) after core_clk exists"""
    out = ""
    for f in s.get("sdc_extra", []):
        body = (ROOT / f).read_text()
        if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") and "set ::ot_wc_entry_mode 1" in body:
            continue
        out += f"# ---- sdc_extra {f}\n" + body
    return out


def gen_signoff(s: dict, refglob: str, inter: str) -> str:
    signoff = clock_entry_constraints.signoff_period(s)
    io = "" if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") else (ROOT / QDM / "io_ref_skew.sdc").read_text()
    return (f"# {s['name']}: sign-off at {signoff} ps (generated by tools/ref_tile/ref_tile.py; same form as\n"
            f"# {QDM}/jobs/signoff_sdc.py): clock re-created at the real period, propagated, 60 / 25 ps uncertainty,\n"
            f"# die-context boundary io_ref_skew.sdc with this block's REFGLOB / INTER bound.\n"
            + "set ::ot_ref_pre_cts 0\n" + clock_entry_constraints.clocks(s, signoff)
            + "set_propagated_clock [all_clocks]\nset_clock_uncertainty -setup 60 [all_clocks]\n"
            "set_clock_uncertainty -hold 25 [all_clocks]\nset ::env(OT_IO_SKEW) 90\nset ::env(OT_IO_HOLD_SKEW) 50\n"
            + "".join(f"set ::env({k}) {v}\n" for k, v in io_budget_env(s).items())
            + f"set ::env(OT_REF_GLOB) {{{refglob}}}\nset ::env(OT_IO_INTER) {{{inter}}}\nset ::env(OT_IO_SKEW_INTER) 150\n"
            + io + sdc_extra(s)
            + ("set ::ot_ce_require_wire 1\n" if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") else "")
            + clock_entry_constraints.generate(s, ROOT) + "\nset_propagated_clock [all_clocks]\n")


def io_hold_relief_ps(s: dict) -> int:
    """spec route.io_hold_margin_ns (q14 r8 2026-10-14): the route's FF hold-repair margin on the BOUNDARY (input pin ->
    register, register -> output pin) separate from the internal reg->reg margin route.hold_margin_ns.  Returns the relief
    d = hold_margin - io_hold_margin (ps, >= 0); 0 = one margin for all (the default, kits unchanged).
    Why: recipe-2 margins (30 ps; slab col pr2 60 ps) applied to every IO path padded each pin flop with 3-4 BUFx2 route
    hold cells on top of the fixed HB2 pad: qfd_su_lane_t_io-io1 TT capture S+R 190-299 ps on 555 inputs (wrom_q[100] FF
    hold slack +40, crom_q[2] +103 at sign-off), slab col pr2 TT launch 254 ps on 158 m5 outputs (four route hold BUFx2 per
    output): the native pin budget (launch <= 220 / capture <= 190 at phi - R) fails although the die hold race is already
    carried by the sign-off boundary (+50 ps sender hold skew, 25 ps uncertainty).  Sign-off is UNCHANGED (signoff.sdc):
    only the route-time FF repair scene reads signoff_ffrepair.sdc, whose boundary min delays are relaxed by d, so a
    repaired IO path lands at sign-off FF slack >= io_hold_margin instead of >= hold_margin."""
    r = s.get("route", {})
    if r.get("io_hold_margin_ns") is None or s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        return 0
    d = round((float(r.get("hold_margin_ns", 0.010)) - float(r["io_hold_margin_ns"])) * 1000)
    if d < 0:
        raise SpecError(f"spec: route.io_hold_margin_ns {r['io_hold_margin_ns']} > hold_margin_ns: the boundary is never repaired harder than the core")
    return d


def gen_signoff_ffrepair(s: dict, refglob: str, inter: str) -> str | None:
    """route-time FF hold-repair SDC (OT_MM_FF_SDC) when route.io_hold_margin_ns relieves the boundary; None otherwise"""
    d = io_hold_relief_ps(s)
    if not d:
        return None
    base = gen_signoff(s, refglob, inter)
    old = "set ::env(OT_IO_HOLD_SKEW) 50\n"
    assert base.count(old) == 1
    return (f"# {s['name']}: ROUTE-TIME FF hold-repair SDC (NOT sign-off; generated by tools/ref_tile/ref_tile.py): signoff.sdc\n"
            f"# with the boundary hold requirement relieved by {d} ps = route.hold_margin_ns - route.io_hold_margin_ns, so the\n"
            f"# repair margin on IO paths is io_hold_margin while reg->reg keeps hold_margin.  Sign-off reads signoff.sdc.\n"
            + base.replace(old, f"set ::env(OT_IO_HOLD_SKEW) {50 - d}\nset ::env(OT_IO_IN_HOLD_SKEW) {-d}\n")
            + "set ::env(OT_IO_HOLD_SKEW) 50\nunset -nocomplain ::env(OT_IO_IN_HOLD_SKEW)\n")


def child_insertions(s: dict) -> dict:
    """{child master: clock-pin insertion ps} from each hard child's TT lib (max_clock_tree_path), 0 when absent"""
    out = {}
    for ch in s["children"]:
        v = ch["view"]
        # spec "child_clock_ref": "boundary" (s81 parents 2026-10-13, die clock delivery rule): the target is the child's
        # ROUTED boundary-register insertion R (views/<child>/insertion.json tt.boundary.mean, the sign-off reference of
        # every hop), not the lib's max_clock_tree_path (latest sink of the whole tree: dsfd_coll_cesc0 415 vs R 322 ps,
        # which would hand the core its clock ~90 ps early against the leaves it talks to).  Lib max when no record exists.
        ij = ROOT / v / "insertion.json"
        if s.get("child_clock_ref") == "boundary" and ij.exists():
            b = json.loads(ij.read_text()).get("tt", {}).get("boundary", {})
            if b.get("n") and b.get("mean") is not None:
                out[view_name(v)] = round(float(b["mean"]), 1)
                continue
        p = ROOT / v / f"{view_name(v)}_tt.lib"
        ins = child_lint.clock_insertion(p.read_text(errors="replace")) if p.exists() else {}
        vals = [x["max_ps"] for x in ins.values() if x]
        out[view_name(v)] = round(max(vals), 1) if vals else 0.0
    return out


SPINE_INS = """# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create {ins}]
proc ot_sp_leaf_arrivals {{}} {{
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {{n net}} $::ot_sp_leafnet {{
    set v 0.0
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {{
      set x [get_property $pin arrival_max_rise]
      if {{$x eq "" || $x eq "INF" || $x eq "-INF"}} continue
      set c [get_cells -quiet -of_objects $pin]
      if {{[llength $c]}} {{
        set m [get_property $c ref_name]
        if {{[dict exists $::ot_ref_child_ins $m]}} {{ set x [expr {{$x + [dict get $::ot_ref_child_ins $m]}}] }}
      }}
      if {{$x > $v}} {{ set v $x }}
    }}
    dict set a $n $v
  }}
  return $a
}}
puts "REF_TILE spine: child insertion targets $::ot_ref_child_ins"
"""


HDLY_TCL = "physical/qwen_die_masters/hdly_dont_touch.tcl"


def gen_hooks(s: dict, kd: str) -> dict:
    fwd = bool(s.get("forwarded_clock"))
    spine = s.get("clock", "spine" if s["kind"] == "cluster" else "cts") == "spine"
    pre_cts = ["# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl)"
               + (" + forwarded-clock subtree kept (hbm_w2_rb_station forwarded_subtree.tcl)" if fwd else "")
               + ("; cluster: balanced clock spine with child-insertion leaf targets (sourced FIRST, so the io_ref wrapper"
                  " below wraps it)" if spine else "")]
    files = {}
    if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        pre_cts[0] += "; clock entries: no tree, one port per child clock pin (sourced FIRST)"
        if s.get("clock") in ("hybrid_entries", "multiple_cts_roots"):
            roots = clock_ports(s) if s.get("clock") == "multiple_cts_roots" else s["clock_cts_roots"]
            pre_cts.append("set ::ot_ce_cts_roots {" + " ".join(roots) + "}")
        pre_cts.append("source /src/physical/common_flow/clock_entries.tcl")
    if spine:
        pre_cts += ["source /src/physical/common_flow/clock_spine.tcl", f"source /src/{kd}/spine_ins.tcl"]
        ins = child_insertions(s)
        files["spine_ins.tcl"] = SPINE_INS.format(ins=" ".join(f"{k} {v}" for k, v in sorted(ins.items())))
    # Explicit clock adapters must wrap the established spine before the IO boundary wrapper.
    # These are routed source dependencies, not post-generation hand edits.
    pre_cts += [f"source /src/{f}" for f in s.get("pre_cts_extra", [])]
    multi = s.get("clock") == "multiple_cts_roots"
    if multi:
        pre_cts[0] = "# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS"
        # Every boundary belongs to its actual root. Never apply the legacy
        # single-clock IO shim (including its unrelated tile_id exception).
        pre_cts.append(f"source /src/{QDM}/repair_budget.tcl")
    else:
        pre_cts.append(f"source /src/{QDM}/pre_cts_skew.tcl")
    # spec "boundary_tcl": repo Tcl files that re-apply a second-domain boundary after every io_ref switch (post-CTS
    # wrapper, pre-GRT, post-DRT), so the route times those ports against their own propagated clock, not only sign-off
    btcl = [f"source /src/{f}" for f in s.get("boundary_tcl", [])
            if not (s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") and "set ::ot_wc_entry_mode 1" in (ROOT / f).read_text())]
    if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        files["clock_entry.sdc"] = "set ::ot_ce_require_wire 1\n" + clock_entry_constraints.generate(s, ROOT)
        btcl.append(f"source /src/{kd}/clock_entry.sdc")
    if btcl:
        # pre_cts_skew installs a CTS wrapper that re-reads the single-domain IO
        # SDC after building the tree. Apply additional domains AFTER that wrapper.
        pre_cts += ["rename clock_tree_synthesis ::ot_ref_cts_boundary_orig",
                    "proc clock_tree_synthesis {args} {",
                    "  ::ot_ref_cts_boundary_orig {*}$args", *(["  estimate_parasitics -placement"] if multi else []),
                    "  set ::ot_ref_pre_cts 0", *["  " + x for x in btcl], "}"]
    if fwd:
        pre_cts.append("source /src/physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl")
    pre_grt = ["# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin",
               "# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)",
               ("estimate_parasitics -placement" if multi else f"source /src/{QDM}/pre_ref_skew.tcl"),
               "source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl",
               # el1011-ds-mtp-cbw 2026-10-12: with MAX_ROUTING_LAYER as GRT's top layer FastRoute zeroes that layer over
               # every hard macro (M5 cap + SRAM OBS M1-M4 = full wall; hrow5_cbw-r5b / hgi_seq v2.4 GRT-0116); GRT to
               # MAX+1 at zero capacity restores it, detailed route still stops at MAX (no-op without macros)
               "source /src/physical/common_flow/grt_macro_top_layer.tcl"] + btcl
    post_drt = ["# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC",
                "source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl",
                * ([] if multi else [f"source /src/{QDM}/post_plain.tcl"])] + btcl
    if macro_edge_guard(s):
        # add before GRT, remove after DRT (the wrapper picks the mode from its caller); the hold ECO re-applies it
        pre_grt.append(f"source /src/{MACRO_EDGE_GUARD_TCL}")
        post_drt.append(f"source /src/{MACRO_EDGE_GUARD_TCL}")
    if ((s["kind"] == "tile" and s.get("signal_max_layer")) or
            (s["kind"] == "cluster" and cluster_signal_cap(s, contract_slot(s))[0] == "M6")):
        lc = layer_contract(s, contract_slot(s))
        post_drt += ["source /src/tools/ref_tile/signal_layer_audit.tcl",
                     f"ot_ref_audit_signal_layers {lc['rlayers'][1]} {lc['pg_layer']} [file join $::env(RESULTS_DIR) signal_layer_audit.json]"]
    corridor = s.get("pin_access", {}).get("corridor")
    if corridor:
        for post, hook in ((0, pre_grt), (1, post_drt)):
            cpins = ("set ::ot_smpub_corridor_pins {" + " ".join("{" + p + "}" for p in corridor['pins']) + "}") if corridor.get('pins') else f"set ::ot_smpub_corridor_pin {{{corridor['pin']}}}"
            hook += [cpins,
                     f"set ::ot_smpub_corridor_half {float(corridor.get('half_height_um', 0.864))}",
                     f"set ::ot_smpub_corridor_post {post}", f"source /src/{corridor['script']}"]
    # Each stage's boundary reset must be followed by the complete domain-specific
    # boundary. In particular, POST_CTS must write a correct SDC for the next stage.
    post_plain = ([] if multi else [f"source /src/{QDM}/post_plain.tcl"]) + btcl
    pre_ref = (["estimate_parasitics -placement"] if multi else [f"source /src/{QDM}/pre_ref_skew.tcl"]) + btcl
    stage_hooks = {"post_cts.tcl": post_plain, "post_grt.tcl": post_plain,
                   "pre_drt.tcl": pre_ref, "pre_fill.tcl": pre_ref,
                   "post_fill.tcl": post_plain}
    return {"pre_cts.tcl": "\n".join(pre_cts) + "\n", "pre_grt.tcl": "\n".join(pre_grt) + "\n",
            "post_drt.tcl": "\n".join(post_drt) + "\n",
            **{name: "\n".join(lines) + "\n" for name, lines in stage_hooks.items()},
            **files, **gen_pin_hooks(s)}


def shq(v: str) -> str:
    return "'" + v.replace("'", "'\"'\"'") + "'"


def gen_env(s: dict, kd: str, W: float, H: float, lc: dict, blocks: list) -> str:
    r = s["route"]
    ph, pv = pin_layers(s, lc)
    srcs = " ".join(s["sources"])
    params = " ".join(f"--param {k}={v}" for k, v in s["params"].items())
    # optional "pin_ranges" {port: [lo_um, hi_um]} (along the face, from its left / bottom end): one region per ranged port so
    # a face tile's bus pins sit at the end facing their die neighbour and >= the given margin off the tile corners
    # ([vm8cp] corner-pin DRT-0255 class); ports without a range keep the whole face.
    regs = [pin_regex(g["names"]) + "=" + FACES[g["face"]]
            + (f":{g['range'][0]:g}-{g['range'][1]:g}" if g["range"] else "") for g in pin_regions(s)]
    pins = " ".join(f"--pin-region {shq(r)}" for r in regs)
    if s.get("io_tcl"):
        # el1011-hbm-smh 2026-10-12: run_abi3_physical writes its own IO_CONSTRAINTS (/work/io_constraints.tcl) for any
        # --pin-region, AFTER the --orfs-var one, so the region groups of OT_PIN_GROUP_MAX replaced io_tcl at 3_2: with the
        # M5 cap (one horizontal pin layer) smh_pt_w_ref_p45h's 3,705 W pins at 2 tracks left max 22 contiguous slots and
        # place_pins aborted (PPL-0093, group of 25).  io_tcl alone places every port; the spec "pins" faces still drive
        # the gate's checks.
        pins = ""
    views = sorted({b["view"] for b in blocks})
    extra = ["--orfs-var ADDER_MAP_FILE=", f"--orfs-var PDN_TCL=/src/{kd}/pdn.tcl",
             f"--orfs-var OT_PK_FRAC={s.get('pin_access', {}).get('frac', 0.5)}",
             # keep only the layer ABOVE each face pin clear (what the parent needs and child_lint (f) checks); also
             # blocking the layer below took the tile's own M3 access to a dense M4 face (hfd_hc 239-268 DRC, c95527ec0)
             f"--orfs-var OT_PK_ABOVE_ONLY={0 if s.get('pin_access', {}).get('both_sides') else 1}"]
    if blocks:
        extra.append(f"--orfs-var MACRO_PLACEMENT_TCL=/src/{kd}/place.tcl")
        extra += [f"--macro-view {view_name(v)}={v}" for v in views]
        h = float(s["route"].get("macro_halo_um", HALO_UM))
        extra.append(f"--macro-place-halo {h} {h}")
    if s.get("clock", "spine" if s["kind"] == "cluster" else "cts") == "spine":
        extra.append(f"--orfs-var OT_SPINE_PORT={s['clock_port']}")
        # el1011-q-kvd 2026-10-12: a hard child's clock pin is its OWN spine leaf.  Shared bins balanced the leaf to the
        # child's internal insertion, so the flops next to it ran one insertion EARLY: qkd_d2d_ref (sbuf 505 ps) left 499
        # sbuf read-data flops r_d at TT 1,050 vs 1,560 ps -> R2O FF hold -318 ps that hold repair cannot move.
        if views and s.get("spine_macro_leaf", True):
            extra.append("--orfs-var OT_SPINE_MACRO_LEAF=1")
        # spec "spine_through_icg": the cluster clock enters ONE tile clock gate (ICG) that clocks the rest (SM tile
        # ot_cg_tile): the spine is built on the ICG output net (clock_spine.tcl OT_SPINE_THROUGH_ICG)
        if s.get("spine_through_icg"):
            extra.append("--orfs-var OT_SPINE_THROUGH_ICG=1")
    # spec "defines": RTL defines the top's synthesis needs (e.g. the hardened-child body selected by `ifdef); written after
    # run_abi3's own "VERILOG_DEFINES = -DSYNTHESIS", so it keeps -DSYNTHESIS explicitly (the lint bench uses the same set).
    if s.get("defines"):
        extra.append("--orfs-var " + shq("VERILOG_DEFINES=" + " ".join(["-DSYNTHESIS"] + [f"-D{d}" for d in s["defines"]])))
    # spec "io_tcl" (el1011-hbm-smh): a repo place_pin file for a tile whose pins must sit at exact abutment tracks; it
    # replaces the face-region IO_CONSTRAINTS (the face groups in "pins" still drive the gate's checks and the keepout).
    if s.get("io_tcl"):
        extra.append(f"--orfs-var IO_CONSTRAINTS=/src/{s['io_tcl']}")
    extra += [f"--orfs-var {k}={v}" for k, v in io_budget_env(s).items()]
    # spec "orfs_vars" {NAME: value}: extra ORFS variables the RTL / structure needs; a value that is a repo file path
    # (el1011-hbm-smh POST_TAPCELL hooks) is passed as /src/<path>, anything else verbatim
    for k, v in sorted(s.get("orfs_vars", {}).items()):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", k) or re.search(r"\s", str(v)):
            raise SpecError(f"spec: orfs_vars {k}={v!r}: NAME=[A-Z0-9_]+, value without whitespace")
        vv = f"/src/{v}" if (not str(v).startswith("/") and os.path.isfile(str(v))) else v
        if k == "POST_TAPCELL_TCL" and s.get("io_tcl"):
            # io_tcl + a POST_TAPCELL pin-flop hook: ORFS sources IO_CONSTRAINTS only at 3_2_place_iop, so the hook saw
            # unplaced ports and FIRM-placed every boundary flop on the W face (smh_pt_e_ref_p40-lf: W 7410 / E 0, both
            # register stages + 6,860 hold buffers in one 24-um strip, GRT stuck at ~3,000 markers; the closed hand kit
            # placed pins at floorplan: W 3705 / E 3705).  The kit's post_tapcell.tcl places the exact pins first.
            vv = f"/src/{kd}/post_tapcell.tcl"
            # ... and post_iop.tcl re-applies them after place_pins (el1013-smh-r11, see the kit file below)
            if "POST_IO_PLACEMENT_TCL" not in s.get("orfs_vars", {}):
                extra.append(f"--orfs-var POST_IO_PLACEMENT_TCL=/src/{kd}/post_iop.tcl")
        extra.append(f"--orfs-var {k}={vv}")
    # spec "post_synth_tcl": a repo POST_SYNTH hook, e.g. physical/hbm_accel_die_views/common/inout_retype_post_synth.tcl
    # for a top with inout terminals (ORFS never buffers an inout: the post-GRT repair stops with RSZ-0074 "found route to
    # 2 pins, expected 1" and CTS misbehaves; the closed die-view routes ran it by default through route_view.sh POSTSYN)
    if s.get("post_synth_tcl"):
        extra.append(f"--step-tcl POST_SYNTH={s['post_synth_tcl']}")
    if s["route"].get("hold_delay"):
        # deterministic hold fix by construction (owner 10-10): the RTL's *u_hdly_* HB delay cells are dont_touch'ed at
        # PRE_FLOORPLAN so remove_buffers / repair passes keep them (tputx-cpf hgi_seq v2.3)
        extra.append(f"--step-tcl PRE_FLOORPLAN={HDLY_TCL}")
    # PD means what the spec says: ORFS's PLACE_DENSITY_LB_ADDON (0.05 in run_abi3's config) silently replaces PLACE_DENSITY
    # by lower-bound + addon (qkd_nhb_pbst: PD 0.50 -> target 0.1075, cells spread over 4.9% of the outline, GPL-0305
    # divergence with M2-M6 routing).  The addon is cleared for every kit; spec route.lb_addon re-enables it explicitly.
    # route.synth_keep_modules: hierarchy kept through synthesis (ABC re-ripples a pipelined fp adder once it is flattened
    # into its context; the hbm norm group closed only with its fp add/mul stages kept, idle1012)
    if s["route"].get("synth_keep_modules"):
        extra.append("--orfs-var " + shq("SYNTH_KEEP_MODULES=" + " ".join(s["route"]["synth_keep_modules"])))
    if s["route"].get("lb_addon") is None:
        extra.append("--orfs-var PLACE_DENSITY_LB_ADDON=")
    else:
        extra.append(f"--orfs-var PLACE_DENSITY_LB_ADDON={float(s['route']['lb_addon'])}")
    wrap = pin_hook_wrapper(s)
    if s.get("io_flop_at_pins"):
        # spec "io_flop_at_pins" {"cols": N} (el1011-q-kvd 2026-10-12): every port's single launch / capture flop FIRM at its
        # own pin (qwen_die_masters/io_flop_at_pins.tcl, N staggered rows per face), released to DPL before detailed placement.
        # qkd_d2d_ref-q8-2f8712b99-hs: all 2,674 output face registers (r_d / tx_flit, already relayed from the buffers in RTL)
        # were pulled 200-345 um into the core by timing-driven GPL -> reg->out TT -740 at 770 against the 0.2 T link budget.
        if (s.get("outhold") or s.get("inhold")) and not wrap:
            raise SpecError("spec: io_flop_at_pins and outhold/inhold both use PRE_GLOBAL_PLACE (kit recipe 1); "
                            'set "recipe": 2 to combine them through the kit-local pre_gpl.tcl / pre_dpl.tcl')
        if wrap:
            extra.append(f"--step-tcl PRE_GLOBAL_PLACE={kd}/pre_gpl.tcl")
            extra.append(f"--step-tcl PRE_DETAIL_PLACE={kd}/pre_dpl.tcl")
            # opt-in knobs of io_flop_at_pins.tcl: walk flop <-> port through the inserted BUF / HB4 / BUF stage on top of
            # the <= 3 synthesis INV / BUF (default 4 hops stops inside the stage)
            extra.append("--orfs-var OT_OFLOP_HOPS=8")
        else:
            extra.append("--step-tcl PRE_GLOBAL_PLACE=physical/qwen_die_masters/io_flop_at_pins.tcl")
            extra.append("--step-tcl PRE_DETAIL_PLACE=physical/qwen_die_masters/out_flop_release.tcl")
        if s["io_flop_at_pins"].get("allow_none"):
            # the recipe default: a tile without a single-flop port (pure macro / child feed-through) is not an error
            extra.append("--orfs-var OT_OFLOP_ALLOW_NONE=1")
        extra.append(f"--orfs-var OT_OFLOP_COLS={int(s['io_flop_at_pins'].get('cols', 4))}")
        # "macro_pins": ["pop", ...] -> OT_MPFLOP_PINS: the flop driving each such hard-child input pin is anchored at the pin too
        # (el1011-q-kvd 2026-10-12: sbuf pop is a ~660 ps internal cone; ot_qkvd_d2d PQ drives it from a dedicated flop)
        mp = s["io_flop_at_pins"].get("macro_pins") or []
        if mp:
            if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x) for x in mp):
                raise SpecError("spec: io_flop_at_pins.macro_pins must be plain pin names")
            extra.append(f"--orfs-var OT_MPFLOP_PINS={','.join(mp)}")
        # "macro_out_pins": ["rd_out", ...] -> OT_MPCAP_PINS: the flop capturing each such hard-child output bit is anchored
        # beside the pin (S-ELEM-B 2026-10-15, calendar7: ROM clk->q leaves ~80 ps for wire + capture)
        mo = s["io_flop_at_pins"].get("macro_out_pins") or []
        if mo:
            if not isinstance(mo, list) or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x) for x in mo):
                raise SpecError("spec: io_flop_at_pins.macro_out_pins must be plain bus base names")
            extra.append(f"--orfs-var OT_MPCAP_PINS={','.join(mo)}")
    if s.get("outhold"):
        # spec 'outhold' (hc-cpin 2026-10-12): flop-driven outputs get lead BUF -> HB4 -> BUF FIRM at the pin (R2O hold-only
        # miss at the routed IO ref); with 'inhold' the same hook first runs leaf_inhold.tcl (one PRE_GLOBAL_PLACE hook)
        if not wrap:
            extra.append("--step-tcl PRE_GLOBAL_PLACE=physical/dsrom_window_source/leaf_iohold.tcl")
        extra.append(f"--orfs-var OT_IOHOLD_IN={1 if s.get('inhold') else 0}")
        if not s.get("inhold") and not wrap:
            extra.append("--step-tcl PRE_DETAIL_PLACE=physical/dsrom_window_source/leaf_inhold_release.tcl")
    if s.get("inhold"):
        # spec 'inhold': one dont_touch hold buffer between every data input port and its single capture flop, inserted
        # before global placement (owner 10-10: a hold-only miss on input captures -> delay stage at the inputs, no ECO)
        if not s.get("outhold") and not wrap:
            extra.append("--step-tcl PRE_GLOBAL_PLACE=physical/dsrom_window_source/leaf_inhold.tcl")
        # the hold cell sits AT its input pin with a strong resizable driver after it (vm8 181753c60), FIRM through GPL and
        # released before DPL: seeding it at the capture flop left a long dont_touch-loaded port net -> GPL repair_design
        # RSZ-3006 (s81hc crootrw/crootre d02b035e3), and a bare HB4 driving the long wire costs ~400 ps (vm8 r9)
        drv = s.get("inhold_drv", "BUFx4f_ASAP7_75t_R")
        if "OT_INHOLD_DRV" in s.get("orfs_vars", {}):
            # the spec's own driver (orfs_vars) wins: appending the default after it silently overrode it
            # (qfd_su_cbuf_native_l0_p13_l12_r3 asked BUFx2, the kit ran BUFx4f)
            drv = None
        if drv:
            extra.append(f"--orfs-var OT_INHOLD_DRV={drv}")
            if not wrap:
                extra.append("--step-tcl PRE_DETAIL_PLACE=physical/dsrom_window_source/leaf_inhold_release.tcl")
    extra += hold_pad_vars(s)
    if s.get("keep_pin_regs"):
        extra.append("--orfs-var OT_KEEP_PIN_REGS=1")
    if s.get("pin_reg_split") and not wrap:
        raise SpecError("spec: pin_reg_split runs inside the recipe-2 pin hook (io_flop_at_pins + inhold/outhold, recipe >= 2)")
    refglob = s.get("refglob", "*")
    inter = ",".join(s["inter"]) or "none_*"
    return "\n".join([
        f"# generated by tools/ref_tile/ref_tile.py from {kd}/spec.json -- do not edit; re-run gen",
        f"TOP={s['top']}", f"SRCS={shq(srcs)}", f"PARAMS=({params})", f"FW={W}", f"FH={H}", f"PINS=({pins})",
        f"PINEX={0 if (s['pins'].get('ANY') or s.get('io_tcl')) else 1}", f"INTER={shq(inter)}", f"REFGLOB={shq(refglob)}", f"CLKPORT={s['clock_port']}",
        f"PD={r.get('pd', 0.55)}", f"NC={r.get('threads', 8)}", f"PIN_H={shq(ph)}", f"PIN_V={shq(pv)}", f"PIN_MIN_TRACKS={r.get('pin_min_tracks', 2)}", "STAGES=pnr",
        f"RLAYERS={shq(' '.join(lc['rlayers']))}", f"ROUTE_PERIOD_NS={r.get('period_ps', 770) / 1000.0}",
        *([f"CLOCK_RLAYERS={shq(' '.join(clock_rlayers(lc)))}"] if clock_rlayers(lc) else []),
        f"KIT=/src/{kd}", f"MACROS=({' '.join(views)})", f"EXTRA=({' '.join(extra)})", *pin_balance_env(r, lc),
        *([f"export OT_PIN_GROUP_MAX={pin_group_max(s)}"] if "pin_group_max" in r else []),
        *cts_sink_env(r), *([f"RECIPE={int(s['recipe'])}"] if s.get("recipe", 1) >= 2 else []), ""])


def pin_regions(s: dict) -> list:
    """the --pin-region list of the kit, in order: per face one region for the ports without a pin_ranges entry, then
    one per ranged port.  [{"names", "face", "range": (lo, hi) | None}]"""
    rng = s.get("pin_ranges") or {}
    out = []
    for f, v in s["pins"].items():
        if not v or f == "ANY":
            continue
        plain = [n for n in v if n not in rng]
        if plain:
            out.append({"names": plain, "face": f, "range": None})
        for n in v:
            if n in rng:
                lo, hi = rng[n]
                out.append({"names": [n], "face": f, "range": (float(lo), float(hi))})
    return out


def route_pin_settings(s: dict, lc: dict) -> dict:
    """the pin-placement settings the ROUTE runs with (ref_route.sh + kit.env + run_abi3_physical): the one description
    the gate's --remote run, the local kit check and the submit hook judge a pin plan by (tools/pin_fit.py).
    {"exact": io_tcl places every port, "tracks", "h": [W / E face layers], "v": [N / S], "group_max", "balance"}"""
    r = s["route"]
    ph, pv = pin_layers(s, lc)
    pb = r.get("pin_balance")
    out = {"exact": bool(s.get("io_tcl")), "tracks": float(r.get("pin_min_tracks", 2)), "h": ph.split(), "v": pv.split(),
           "group_max": pin_fit.ROUTE_PIN_GROUP_MAX, "balance": False}
    if pb:
        env = dict(x[len("export "):].split("=", 1) for x in pin_balance_env(r, lc))
        out.update(group_max=int(env["OT_PIN_GROUP_MAX"]), balance=True,
                   h=env["OT_PIN_BALANCE_H"].strip("'").split(), v=env["OT_PIN_BALANCE_V"].strip("'").split())
    return out


def cts_sink_env(r: dict) -> list:
    """optional route.cts_sink {size, diameter_um}: explicit TritonCTS register-sink clustering (CTSA -> ref_route.sh
    CTS_ARGS).  ORFS CTS_CLUSTER_* are ignored once CTS_ARGS is set, and the automatic choice on small macro tiles
    (qfd_vm_bank_t: 32 sinks / 82 um, 2 buffers per path) leaves long leaf nets: TT insertion 243-403 ps."""
    cs = r.get("cts_sink")
    if not cs:
        return []
    # "extra": further clock_tree_synthesis options, validated ("-sink_clustering_levels 2", "-distance_between_buffers 40":
    # qkd_astk_ep 10-13: the last H-tree net strung 8 leaf buffers over ~150 um, its far leaves 70 ps late)
    extra = str(cs.get("extra", "")).strip()
    if extra and not re.fullmatch(r"(-[a-z_]+( [0-9.]+)?)( -[a-z_]+( [0-9.]+)?)*", extra):
        raise SpecError(f"spec: route.cts_sink.extra {extra!r}: '-option [number]' items only")
    # size / diameter_um are optional (s81 gather leaf 10-14: {"extra": "-no_obstruction_aware"} alone keeps the tool's
    # max-cap register clustering and only drops the H-tree detour around the abutted SRAM stacks)
    if ("size" in cs) != ("diameter_um" in cs):
        raise SpecError("spec: route.cts_sink: give both size and diameter_um, or neither (extra only)")
    sz = (f" -sink_clustering_size {int(cs['size'])} -sink_clustering_max_diameter {int(cs['diameter_um'])}"
          if "size" in cs else "")
    if not sz and not extra:
        raise SpecError("spec: route.cts_sink: empty (no size / diameter_um and no extra)")
    return [f"CTSA={shq('-sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75' + sz + (' ' + extra if extra else ''))}"]


def pin_balance_env(r: dict, lc: dict | None = None) -> list:
    """optional route.pin_balance {group_max, h, v}: run_abi3_physical's balanced pin placer (place_pin, uniform over each
    port's range, layer alternating every group_max pins) instead of PPL ordered groups, which put a whole port on ONE
    layer ([vm8cp] 2k-bit relay buses: PPL-0107 / PPL-0093).  Needs disjoint per-port pin_ranges on a face."""
    pb = r.get("pin_balance")
    if not pb:
        return []
    return [f"export OT_PIN_GROUP_MAX={int(pb.get('group_max', 1))}",
            f"export OT_PIN_BALANCE_H={shq(pb.get('h', 'M4' if (lc or {}).get('rlayers', ('', 'M6'))[1] == 'M5' else 'M4 M6'))}", f"export OT_PIN_BALANCE_V={shq(pb.get('v', 'M3 M5'))}"]


def referenced_paths(s: dict, kd: str) -> list:
    """every repo file the routed flow reads (for the source-sync check of the gate)"""
    out = [*s["sources"], *s.get("boundary_tcl", []), *s.get("pre_cts_extra", []), *s.get("pin_hook_before_flops", []), f"{kd}/kit.env", f"{kd}/clock.sdc", f"{kd}/signoff.sdc", *([f"{kd}/signoff_ffrepair.sdc"] if io_hold_relief_ps(s) else []), f"{kd}/pdn.tcl", f"{kd}/pre_cts.tcl",
           *[f"{kd}/{f}" for f in ("post_cts.tcl", "post_grt.tcl", "pre_drt.tcl", "pre_fill.tcl", "post_fill.tcl")],
           f"{kd}/pre_grt.tcl", f"{kd}/post_drt.tcl", "tools/ref_tile/ref_route.sh",
           f"{QDM}/io_ref_skew.sdc", f"{QDM}/io_plain.sdc", f"{QDM}/repair_budget.tcl", f"{QDM}/pre_cts_skew.tcl",
           f"{QDM}/pre_ref_skew.tcl", f"{QDM}/post_plain.tcl",
           "physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl", "physical/common_flow/grt_macro_top_layer.tcl"]
    if macro_edge_guard(s):
        out += [MACRO_EDGE_GUARD_TCL, "physical/common_flow/macro_edge_via_guard.tcl"]
    if ((s["kind"] == "tile" and s.get("signal_max_layer")) or
            (s["kind"] == "cluster" and cluster_signal_cap(s, contract_slot(s))[0] == "M6")):
        out.append("tools/ref_tile/signal_layer_audit.tcl")
    if s.get("forwarded_clock"):
        out.append("physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl")
    if s.get("io_tcl"):
        out.append(s["io_tcl"])
    out += sorted(str(v) for v in s.get("orfs_vars", {}).values() if not str(v).startswith("/") and os.path.isfile(str(v)))
    if s.get("io_flop_at_pins"):
        out += ["physical/qwen_die_masters/io_flop_at_pins.tcl", "physical/qwen_die_masters/out_flop_release.tcl"]
    if s.get("outhold"):
        out += ["physical/dsrom_window_source/leaf_iohold.tcl", "physical/dsrom_window_source/leaf_inhold_release.tcl"]
    if s.get("inhold"):
        out.append("physical/dsrom_window_source/leaf_inhold.tcl")
        if s.get("inhold_drv", "BUFx4f_ASAP7_75t_R") or pin_hook_wrapper(s):
            out.append("physical/dsrom_window_source/leaf_inhold_release.tcl")
    if pin_hook_wrapper(s):
        out += [f"{kd}/pre_gpl.tcl", f"{kd}/pre_dpl.tcl"]
        if s.get("pin_reg_split"):
            out.append(PIN_REG_SPLIT_TCL)
    if s.get("post_synth_tcl"):
        out.append(s["post_synth_tcl"])
    if s["route"].get("hold_delay"):
        out.append(HDLY_TCL)
    if s.get("clock", "spine" if s["kind"] == "cluster" else "cts") == "spine":
        out += ["physical/common_flow/clock_spine.tcl", f"{kd}/spine_ins.tcl"]
    if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots"):
        out += ["physical/common_flow/clock_entries.tcl", f"{kd}/clock_entry.sdc"]
        out += [f"{ch['view']}/insertion.json" for ch in s["children"]]
    for it in s["macros"] + s["children"]:
        v = it["view"]
        out += [f"{v}/{view_name(v)}.lef"] + [f"{v}/{view_name(v)}_{c}.lib" for c in ("ss", "ff", "tt")]
    if s["macros"] or s["children"]:
        out.append(f"{kd}/place.tcl")
    return out


ROUTE_PREFIX = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
                "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl "
                "physical/common_flow/link_budget_hook.tcl'; export OT_ORFS_CORNER_OVERRIDE=TC; ")


def clock_fix_hooks(s: dict) -> str:
    """Explicit multi-root boundaries own IO timing; retain physical clock fixes."""
    hooks = ["physical/common_flow/cg_pushdown.tcl", "physical/common_flow/clk_net_protect.tcl"]
    if not clock_entry_constraints.native_leaf(s):
        hooks.append("physical/common_flow/link_budget_hook.tcl")
    return " ".join(hooks)


def route_prefix(s: dict) -> str:
    if not clock_entry_constraints.native_leaf(s):
        return ROUTE_PREFIX  # existing job command bytes stay unchanged
    return ROUTE_PREFIX.replace("physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl",
                                "physical/common_flow/clk_net_protect.tcl")


def lint_cmd(s: dict) -> str:
    """the auto 'lint' bench: Verilator over exactly what the route synthesises -- the same sources, -DSYNTHESIS (run_abi3's
    VERILOG_DEFINES) plus the spec defines, the top's params, the include dirs of orfs_vars VERILOG_INCLUDE_DIRS.
    -Wno-MODMISSING: hard macros / children are blackboxes in the route (LEF/LIB only), and Verilator links every parsed
    module, also ones outside the top's hierarchy; a module genuinely missing under the top still fails yosys
    'hierarchy -check' in the route.  (10-12: ~30 ref jobs NEEDS_RTL on a lint that omitted the defines that select the
    top's body / named blackbox children.)"""
    defs = ["-DSYNTHESIS"] + [f"-D{d}" for d in s.get("defines", [])]
    inc = [f"-I{d[len('/src/'):] if d.startswith('/src/') else d}"
           for d in str(s.get("orfs_vars", {}).get("VERILOG_INCLUDE_DIRS", "")).split() if d]
    # the top is linted under a one-line wrapper: verilator refuses --top-module on a module that another parsed source
    # instantiates (ot_hgi_hc_tile inside ot_hgi_hc_unit.sv, from claude/el1011-hcvm-hc4 7e3baed71); the top's params
    # become instance overrides (-G only reaches the top level); unconnected wrapper ports are lint warnings only
    pv = ", ".join(f".{k}({v})" for k, v in s.get("params", {}).items())
    inst = f"{s['top']} #({pv}) u_top ();" if pv else f"{s['top']} u_top ();"
    wrap = (f"mkdir -p {{RUN}} && printf '%s\\n' 'module ot_lint_top; {inst} endmodule' > {{RUN}}/ot_lint_top.sv && ")
    return wrap + " ".join(["verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING",
                     *defs, *inc, "--top-module", "ot_lint_top", "{RUN}/ot_lint_top.sv", *s["sources"]]) + " && echo lint-ok"


def route_hold_context(s: dict, kd: str) -> dict:
    """Execution settings shared by route generation and the pre-route CTS gate."""
    return {"HM": str(float(s["route"].get("hold_margin_ns", 0.010))),
            "OT_ROUTE_HOLD_CORNERS": "mm",
            "OT_MM_FF_SDC": f"{kd}/{'signoff_ffrepair.sdc' if io_hold_relief_ps(s) else 'signoff.sdc'}"}


def gen_job(s: dict, kd: str, commit: str | None, blocks: list) -> dict:
    r, j = s["route"], s.get("job", {})
    hold = route_hold_context(s, kd)
    hm = float(hold["HM"])
    tag = j.get("tag", "ref")
    name = f"{s['name']}-{tag}-{(commit or 'COMMIT')[:9]}"
    lint = lint_cmd(s)
    benches = list(j.get("benches") or [])
    if j.get("benches_from"):     # shared bench template (e.g. tools/s81_suhc/hc_gate_benches.json: the HC composition gate)
        have = {b.get("name") for b in benches}
        benches += [b for b in json.loads((ROOT / j["benches_from"]).read_text())["benches"] if b.get("name") not in have]
    if not any(b.get("name") == "lint" for b in benches):
        benches = [{"name": "lint", "cmd": lint, "expect": "pass", "threads": 1, "peak_ram_gb": 4,
                    "needs": ["verilator"]}] + benches
    views = sorted({b["view"] for b in blocks})
    vout = f"{{RUN}}/record/views/{s['top']}"
    mv = " ".join(f"--macro-view {v}" for v in views)
    spec = {
        "name": name, "block": s["top"], "ref_tile": True,
        **({"m6_pin_grant": s["m6_pin_grant"]} if s.get("m6_pin_grant") else {}),
        "owner": j.get("owner", "Claude:ref-flow"),
        "purpose": j.get("purpose", f"reference tile flow ({s['kind']}) kit {kd}"),
        **({"hosts": j["hosts"]} if j.get("hosts") else {}),   # no default host list: the loop places jobs (EPYC2/3 retired 10-12)
        "threads": int(r.get("threads", 8)), "peak_ram_gb": int(r.get("peak_ram_gb", 32)),
        "source": {"branch": j.get("branch", "main"), "commit": commit or "COMMIT",
                   **({"extra_paths": j["extra_paths"]} if j.get("extra_paths") else {})},
        "stages": {
            "bench": benches,
            "calibrate": {"enabled": False, "reason": "ref_tile: boundary referenced in-run to the propagated tree "
                                                      "(io_ref_skew.sdc), as the Qwen die masters"},
            "route": {
                "cmd": route_prefix(s) + f"HM={hm} OT_MM_FF_SDC='{hold['OT_MM_FF_SDC']}' SRC={{SRC}} OT_PIN_GROUP_MAX={pin_group_max(s)} "
                       f"bash tools/ref_tile/ref_route.sh {kd}/kit.env {{LABEL}} {{RUN}}/routes",
                "ok": "grep -q '^flow_rc=0' {RUN}/routes/{LABEL}/status && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/status",
                "logs": ["{RUN}/routes/{LABEL}/flow.log"],
                "threads": int(r.get("threads", 8)), "peak_ram_gb": int(r.get("peak_ram_gb", 32))},
            "collect": {
                "cmd": ("mkdir -p {RUN}/record/route {RUN}/record/views && cp {RUN}/routes/{LABEL}/corner_sta.json "
                        "{RUN}/routes/{LABEL}/status {RUN}/routes/{LABEL}/STATUS {RUN}/routes/{LABEL}/signoff.sdc "
                        "{RUN}/record/route/ && python3 tools/ref_tile/ref_tile.py export --orfs-dir "
                        f"{{RUN}}/routes/{{LABEL}}/work/orfs --kit {kd} --out {vout} {mv} "
                        "> {RUN}/record/route/export.log 2>&1")}},
        "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                    "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                    "checks": [{"name": "ttb_routed_at_TC",
                                "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                    "post_sdc": [f"{kd}/signoff.sdc", "physical/common_flow/link_budget_consistent.sdc"],
                    "macros": views},
        "hold_eco": {"enabled": True, "session": "mm", "reason": "ref_tile: corrected FF hold flow"},
        "budget": {"enabled": False, "reason": "ref_tile: boundary budget 0.2 T applied in-run"},
        "record": [{"from": "{RUN}/record/views", "to": j.get("views_to", f"{kd}/views")},
                   {"from": "{RUN}/record/route", "to": j.get("record_to", f"results/rtl/ref_tile/{s['name']}") + f"/{name}"}],
        "cycles_added": int(j.get("cycles_added", 0)),
        "route_hold_corners": "mm", "route_hold_margin_ns": hm, "route_corner": "TC",
        "notes": j.get("notes", "generated by tools/ref_tile/ref_tile.py"),
        "merge_target": j.get("merge_target"),
        **({"structural_change": j["structural_change"]} if j.get("structural_change") else {}),
    }
    if j.get("no_bench_reason"):
        spec["no_bench_reason"] = j["no_bench_reason"]
    if j.get("benched_by"):     # composition gate (tools/ref_tile/composition_gates.json): the loop appends its benches
        spec["benched_by"] = j["benched_by"]
    if j.get("hold_merge"):     # a physical probe that never merges (not a closure candidate)
        spec["hold_merge"] = j["hold_merge"]
    # closure loop STRUCTURE_REPEAT lint (owner 10-13): after two failed routes the next submission states what changed
    # in the structure; the sentence is written once in the tile spec (top level, or under "job") and must reach job.json
    sc = s.get("structural_change") or j.get("structural_change")
    if isinstance(sc, str) and sc.strip():
        spec["structural_change"] = sc.strip()
    # closure loop CLOSED_STANDS gate (owner 10-12 / gate 10-13): a block that already has a CLOSED, published job is
    # routed again only with a reason the loop can verify; written once in the tile spec (top level, or under "job")
    rr = s.get("reroute_reason") or j.get("reroute_reason")
    if isinstance(rr, dict) and rr.get("kind"):
        spec["reroute_reason"] = rr
    return spec


def gen(spec_path: str, area_um2: float | None = None, commit: str | None = None, out_root: Path = ROOT,
        write: bool = True) -> dict:
    s = load_spec(spec_path)
    apply_recipe(s, kit_recipe(s, out_root, spec_path))
    slot = contract_slot(s)
    lc = layer_contract(s, slot)
    if lc.get("m6_pin_grant"):
        import m6_pin_grant as M6
        raw_spec = json.loads(Path(spec_path).read_text())
        if M6.spec_digest(raw_spec) != lc["m6_pin_grant"]["source_spec_sha256"]:
            raise SpecError("M6 pin-only grant physical source-spec SHA256 mismatch")
        import subprocess
        source_commit = lc["m6_pin_grant"]["source_commit"]
        git_root = str(GIT_ROOT or ROOT)
        exists = subprocess.run(["git", "-C", git_root, "cat-file", "-e", source_commit + "^{commit}"],
                                capture_output=True)
        if exists.returncode:
            raise SpecError("M6 pin-only grant source commit does not exist")
        source_paths = list(s["sources"])
        source_paths += [s[k] for k in ("io_tcl", "post_synth_tcl") if s.get(k)]
        source_paths += [v for v in s.get("orfs_vars", {}).values() if isinstance(v, str)
                         and v.endswith((".tcl", ".sdc"))]
        for path in source_paths:
            path = path.removeprefix("/src/")
            file = ROOT / path
            original = subprocess.run(["git", "-C", git_root, "show", f"{source_commit}:{path}"],
                                      capture_output=True)
            if original.returncode or not file.is_file() or original.stdout != file.read_bytes():
                raise SpecError(f"M6 pin-only grant source differs from approved commit: {path}")
        s["m6_pin_grant"] = lc["m6_pin_grant"]
    blocks = blocks_of(s)
    W, H, why = outline(s, slot, area_um2, blocks)
    place_blocks(s, W, H, blocks)
    std = area_um2 or s.get("std_area_um2")
    findings = floorplan_checks(s, W, H, blocks, std)
    kd = kit_dir(s)
    fp = {"schema": "opentallas.ref_tile.floorplan.v1", "name": s["name"], "top": s["top"], "kind": s["kind"],
          "die": [0, 0, W, H], "core": [CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN], "why": why,
          "std_area_um2": std, "layer_contract": {k: (list(v) if isinstance(v, tuple) else v) for k, v in lc.items()},
          "pins": s["pins"], "clock_port": s["clock_port"],
          **({"clock_ports": clock_ports(s)} if s.get("clock") in ("entries", "hybrid_entries", "multiple_cts_roots") else {}),
          **({"clock_cts_roots": list(s["clock_cts_roots"])} if s.get("clock") == "hybrid_entries" else {}),
          "blocks": [{k: b[k] for k in ("kind", "view", "master", "inst", "idx", "x", "y", "w", "h", "orient", "offtrack")}
                     for b in blocks],
          "findings": [list(f) for f in findings], "referenced": referenced_paths(s, kd)}
    files = {"kit.env": gen_env(s, kd, W, H, lc, blocks), "pdn.tcl": gen_pdn(s, lc),
             "clock.sdc": gen_sdc(s, float(s["route"].get("period_ps", 770))),
             "signoff.sdc": gen_signoff(s, s.get("refglob", "*"), ",".join(s["inter"]) or "none_*"),
             **gen_hooks(s, kd), "floorplan.json": json.dumps(fp, indent=1) + "\n",
             "spec.json": json.dumps(({**raw_spec, "m6_pin_grant": lc["m6_pin_grant"]} if lc.get("m6_pin_grant")
                                      else {k: v for k, v in s.items()}), indent=1) + "\n"}
    ffr = gen_signoff_ffrepair(s, s.get("refglob", "*"), ",".join(s["inter"]) or "none_*")
    if ffr:
        files["signoff_ffrepair.sdc"] = ffr
    if blocks:
        files["place.tcl"] = gen_place(s, blocks)
    if s.get("io_tcl") and s.get("orfs_vars", {}).get("POST_TAPCELL_TCL"):
        files["post_tapcell.tcl"] = (
            "# ref_tile: exact abutment pins first (IO_CONSTRAINTS is otherwise sourced only at 3_2_place_iop, where it\n"
            "# re-applies the same placement), then the spec's POST_TAPCELL hook (boundary flops FIRM at their pins)\n"
            f"source /src/{s['io_tcl']}\n"
            f"source /src/{s['orfs_vars']['POST_TAPCELL_TCL']}\n"
            "# then unplace the pins again: 3_2_place_iop re-sources io_tcl, and place_pins aborts in createIOGroup when\n"
            "# a pin group's (clk / reset) ports are already placed (smh_pt_e_ref_p40s gate, signal 6)\n"
            "# signal ports only: POWER/GROUND BTerm pins (made by pdngen at 2_4) are never re-created by io_tcl or\n"
            "# place_pins; a pinless VDD/VSS BTerm makes AntennaChecker::designIsPlaced() false -> ANT-0008 at 5_1_grt\n"
            "foreach bt [[ord::get_db_block] getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }\n")
        # el1013-smh-r11 2026-10-13: this ORFS sources IO_CONSTRAINTS at 2_1_floorplan ONLY (floorplan.tcl), not at
        # 3_2_place_iop, so after the unplace above place_pins placed EVERY port by wirelength and the exact plan was lost
        # (smh_tile_eg_ref r10: 7,766 of 7,766 ports re-placed; clk / cgi on the W face, gin on the E face on M4, 50 of the
        # 200 gout on S; the boundary flops stayed FIRM at the planned positions).  POST_IO_PLACEMENT: place the exact pins
        # again, check every port is back on its planned spot, and rewrite the stage result the next step loads.
        files["post_iop.tcl"] = (
            "# ref_tile: re-apply the exact abutment pin plan after place_pins (IO_CONSTRAINTS is sourced only at\n"
            "# 2_1_floorplan; the POST_TAPCELL hook unplaced the ports so place_pins could run) and save the stage result\n"
            "set ot_blk [ord::get_db_block]\n"
            "foreach bt [$ot_blk getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }\n"
            f"source /src/{s['io_tcl']}\n"
            "set ot_n 0; set ot_miss {}\n"
            "foreach bt [$ot_blk getBTerms] {\n"
            "  if {[$bt getSigType] in {POWER GROUND}} continue\n"
            "  if {[llength [$bt getBPins]] == 0} { lappend ot_miss [$bt getName] } else { incr ot_n }\n"
            "}\n"
            "if {[llength $ot_miss]} { error \"REF_TILE exact pin plan: [llength $ot_miss] ports left unplaced ([lrange $ot_miss 0 4])\" }\n"            "foreach bt [$ot_blk getBTerms] { if {[$bt getSigType] in {POWER GROUND} && [llength [$bt getBPins]] == 0} { error \"REF_TILE power port [$bt getName] lost its pdn pin (ANT-0008 at grt)\" } }\n"
            "puts \"REF_TILE exact pin plan re-applied after place_pins: $ot_n ports\"\n"
            "orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb\n"
            "write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl\n")
    job = gen_job(s, kd, commit, blocks)
    files["job.json"] = json.dumps(job, indent=1) + "\n"
    if write:
        d = out_root / kd
        d.mkdir(parents=True, exist_ok=True)
        for k, v in files.items():
            (d / k).write_text(v)
    return {"kit": kd, "outline": [W, H], "why": why, "findings": findings, "files": sorted(files), "job": job["name"]}


# --------------------------------------------------------------------------------------------- export
def export(orfs_dir: str, kit: str, out: str, macro_views: list) -> int:
    """exact-shape abstract (write_abstract_lef, never -bloat_occupied_layers) + TT/FF/SS timing models from the routed
    odb + spef at the VERDICT's constraint sequence (tools/tt_views/view_export.py), the routed clock insertion (ck_insertion.py), then child_lint of the result."""
    import subprocess
    fp = json.loads((ROOT / kit / "floorplan.json").read_text())
    top = fp["top"]
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "tools/tt_views/view_export.py"), "--orfs-dir", orfs_dir, "--name", top,
           "--out", str(o), "--interface-sdc", str(ROOT / kit / "signoff.sdc"), "--corners", "ss,ff,tt"]
    lc = fp.get("layer_contract", {})
    if lc.get("signal_max_layer"):
        cmd += ["--signal-max-layer", lc["signal_max_layer"], "--pg-max-layer", lc["pg_layer"],
                "--signal-audit-tcl", str(ROOT / "tools/ref_tile/signal_layer_audit.tcl")]
    # EXPORT-SDC (2026-10-13): view_export replays the route's VERDICT constraint sequence (closure-loop run: routed
    # 6_final.sdc, SPEF, post-SDCs, io_ref_routed.sdc last) and fails when its TT / FF slack differs from the verdict.
    # Outside a loop run there is no verdict to replay: the same order from the kit (never signoff.sdc INSTEAD of the
    # routed SDC: s81su SMT exported FF -19.69 against a +3.66 verdict that way).
    for f in (ROOT / kit / "signoff.sdc", ROOT / "physical/common_flow/io_ref_routed.sdc"):
        cmd += ["--post-sdc", str(f)]
    grant = fp.get("layer_contract", {}).get("m6_pin_grant")
    if grant:
        cmd += ["--pin-only-tech"]
    for v in macro_views:
        cmd += ["--macro-view", str(ROOT / v)]
    rc = subprocess.run(cmd).returncode
    base = next(Path(orfs_dir).glob("results/asap7/*/base"), None)
    ck = ROOT / "tools/closure_loop/ck_insertion.py"
    if base is not None and ck.exists():
        insertion = o / "insertion.json"
        insertion.unlink(missing_ok=True)  # a failed measurement cannot retain a prior route's clock record
        # --raw-source: the published R is the physical tree from the clock pin (the die delivers phi - R), never an
        # arrival a compensated entry SDC (set_clock_latency -source -R) pulled to ~0
        cr = subprocess.run([sys.executable, str(ck), "--base", str(base), "--routed", "--all-clocks", "--raw-source",
                             "--output", str(insertion)])
        if cr.returncode:
            (o / "CLOCK_INSERTION_FAILED").write_text(f"clock measurement exit {cr.returncode}; no insertion.json published\n")
        else:
            (o / "CLOCK_INSERTION_FAILED").unlink(missing_ok=True)
    lef = o / f"{top}.lef"
    if lef.exists() and not grant:
        # PIN-STUB (73e17f447): write_abstract_lef writes a face pin's own same-layer route stub as OBS over the pin
        # (ot_qkvd_sbuf DRT-0073); move it into the pin's PORT before the lint (child_lint (f) refuses it)
        subprocess.run([sys.executable, str(ROOT / "tools/hier_contract/abstract_pin_stub.py"), str(lef), str(lef)])
    routed_def = None
    if grant and base is not None:
        # Require final detailed-route geometry; never GRT or an abstract reconstructed from pins.
        candidates = [base / n for n in ("6_final.def", "5_route.def") if (base / n).exists()]
        if candidates:
            import shutil
            routed_def = str(o / "pin_only_routed.def")
            shutil.copyfile(candidates[0], routed_def)
        (o / "m6_pin_grant.json").write_text(json.dumps(grant, indent=1) + "\n")
    res = child_lint.lint(str(lef), str(o), cap="M5" if grant else None,
                          pin_grant=grant, routed_def=routed_def,
                          tech_lef=str(o / "pin_only_tech.lef") if grant and (o / "pin_only_tech.lef").exists() else None) if lef.exists() else {"verdict": "FAIL", "fails": ["no LEF exported"]}
    (o / "child_lint.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"REF_TILE export {top}: views rc={rc} child_lint {res['verdict']} "
          + "; ".join(res.get("fails", []) + res.get("warns", []))[:800])
    return 0 if (rc == 0 and res["verdict"] == "PASS") else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("spec")
    g.add_argument("--area-um2", type=float)
    g.add_argument("--commit")
    j = sub.add_parser("job")
    j.add_argument("spec")
    j.add_argument("--commit", required=True)
    j.add_argument("--area-um2", type=float)
    e = sub.add_parser("export")
    e.add_argument("--orfs-dir", required=True)
    e.add_argument("--kit", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--macro-view", action="append", default=[])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "gen":
            r = gen(a.spec, a.area_um2, a.commit)
            for sev, chk, msg, fix in r["findings"]:
                print(f"REF_TILE {sev} {chk}: {msg} -> {fix}")
            print(f"REF_TILE kit {r['kit']} outline {r['outline'][0]} x {r['outline'][1]} um ({r['why']}); job {r['job']}")
            return 1 if any(f[0] == "FAIL" for f in r["findings"]) else 0
        if a.cmd == "job":
            r = gen(a.spec, a.area_um2, a.commit, write=False)
            s = load_spec(a.spec)
            apply_recipe(s, kit_recipe(s, None, a.spec))
            job = gen_job(s, kit_dir(s), a.commit, place_blocks(s, *r["outline"], blocks_of(s)))
            p = ROOT / kit_dir(s) / "job.json"
            p.write_text(json.dumps(job, indent=1) + "\n")
            print(f"REF_TILE job {job['name']} -> {p.relative_to(ROOT)}")
            return 0
        return export(a.orfs_dir, a.kit, a.out, a.macro_view)
    except SpecError as ex:
        print(f"REF_TILE FAIL spec: {ex}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
