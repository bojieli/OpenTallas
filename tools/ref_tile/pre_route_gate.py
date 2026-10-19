#!/usr/bin/env python3
"""Pre-route gate (tools/ref_tile, ref-flow-1011 2026-10-11): reject the known flow / structure pitfalls in minutes,
before a multi-hour route.  Clear PASS / WARN / FAIL with the fix for every finding.

    pre_route_gate.py KIT_DIR_OR_SPEC [--job JOB.json] [--remote HOST [--cts] [--synth-cap S] [--mem GB] [--disk GB]] [--json OUT]
    pre_route_gate.py --job JOB.json                 (any closure-loop spec: source-sync + generic checks only)

LOCAL (seconds; also run by the closure loop at submit for "ref_tile": true jobs):
  floorplan     outline / util 45-60% / >= 20 um channels / no macro at a pin face / macros on the asap7 track lattice
  layer         leaf signals AND PG <= layer_cap (M5 default, M6 by die-lead grant, legacy kits M6/M7 PG) via explicit
                RLAYERS, PG = full-length stripes on the cap layer, pins <= cap, parent strap = cap + 1; cluster PG M7
                over M5/M6 children; PDN macro grids only for present masters (PDN-0217); kit routing layers are explicit
  pins          pin plan vs the top module's ports: every base name exists, every port in exactly one face, no x[0]
                names (PPL-0061), the clock port planned
  rtl           textbook_lint.py rtl: runtime-indexed wide part-selects (yosys SHARE stall), hard-child #() overrides
  children      tools/hier_contract/child_lint.py (a)-(g) on every hard child; TT/FF/SS libs of every macro view
  slot_fit      (submit only, owner 2026-10-13) a tile with a slot in a die contract fits it: outline, pin faces, pin
                layers, layer cap, estimated clock insertion (tools/hier_contract/slot_fit.py); a mismatch is REFUSED
                unless the spec carries "slot_change_request" (then WARN + a line in the die lead's log)
  sources       every file the flow reads (kit hooks, the scripts they source, views, RTL) exists and lies inside the
                job's synced source paths (the loop copies only source.paths + extra_paths: hbm-no3 'No rule to make
                target /src/physical/redesign_ds/coll_split/pin_access_pregrt.tcl')
REMOTE (--remote HOST, minutes, on the fleet via ot-heavy): the real ORFS synthesis under a time cap (a SHARE stall
fails here, not after hours), floorplan + PDN + IO placement of the kit (PDN-0217/0233/0006, PPL-0061 surface here),
then the netlist textbook lint (clock root size / span, high fanout + reset on datapath, logic behind pins, ICG enable
from a port, logic depth, > 500 um wire per stage) on the synthesized netlist + the placed-IO floorplan, and the pin
plan against the SYNTHESIZED port names.  MEASURED CLOCK RULE (owner 2026-10-17 0dq, textbook_lint.clock_rule_eval):
FAIL only on a pin-flop (child-flop per linked pair for a parent) spread > 80 ps at TT or FF, or a neighbour-boundary
mismatch (native_pin_audit --relative-to); > 15,000 sinks on one root or insertion > 300 ps is a WARN (guidance).  A --remote run writes <kit>/gate_result.json (commit it: the submit gate reads it).  --cts continues through CTS and reports clock insertion spread (ck_insertion)
and the worst-path classes.
Exit 0 PASS / WARN, 1 FAIL, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import ref_tile as RT  # noqa: E402
import child_lint  # noqa: E402
import textbook_lint as TL  # noqa: E402
import pin_fit as PF  # noqa: E402
import source_binding as SB  # noqa: E402
import clock_entry_constraints as CE  # noqa: E402
import keep_module_audit as KA  # noqa: E402
HO = SB.overlay_module()

DEFAULT_SRC_PATHS = ("tools", "rtl", "physical", "Makefile")
# the textbook checks whose refuse tier the gate enforces (calibrated: zero closed-set refusals, see README)
# reset_landing (ROOT-RST 2026-10-19, Gate-Rule: tightening requires=reset_landing): a reset input reaching more than
# rst_land_max (2) sinks without a pin landing register FAILS the gate (textbook_lint reset_landing; kit fix: ref_tile
# "reset_landing": {"enable": true} inserts the 2-stage landing at synthesis)
GATE_REFUSE = ("clock_domain", "high_fanout", "wire_reach", "reset_landing")
RELAUNCH_WAIT_S = int(os.environ.get("OT_GATE_RELAUNCH_WAIT_S", "900"))
DAEMON_TREE = Path(os.environ.get("OT_CLOSURE_DAEMON_TREE", "/home/ubuntu/wt-claude-closure-daemon-1010"))
# flow helpers the loop ships into every job snapshot (closure_loop.py ship_fpl / HELPERS); the remote gate does the same
SHIP_HELPERS = ("tools/orfs_hold_mm.py", "tools/orfs_hold_mm.tcl", "tools/fp_margin_lint.py", "tools/fp_margin_lint.tcl",
                "tools/textbook_lint.py", "physical/common_flow/macro_cts_cluster.tcl")


class Gate:
    def __init__(self):
        self.items = []

    def add(self, sev, check, msg, fix=""):
        self.items.append({"severity": sev, "check": check, "message": msg, "fix": fix})

    @property
    def verdict(self):
        s = {i["severity"] for i in self.items}
        return "FAIL" if "FAIL" in s else ("WARN" if "WARN" in s else "PASS")

    def print(self):
        for i in self.items:
            print(f"GATE {i['severity']} {i['check']}: {i['message']}" + (f"  -> FIX: {i['fix']}" if i["fix"] else ""))
        print(f"PRE_ROUTE_GATE: {self.verdict} ({sum(i['severity'] == 'FAIL' for i in self.items)} fail, "
              f"{sum(i['severity'] == 'WARN' for i in self.items)} warn)")


# --------------------------------------------------------------------------------------------- pins
def synthesis_std_area(chip_area: float, blocks: list, root=ROOT) -> float:
    """Yosys chip area includes each hard instance's Liberty area.

    A hardened child's Liberty area is its occupied logical area; its LEF
    rectangle includes whitespace. Subtract the Liberty areas before adding
    the physical envelopes to utilization, otherwise children count twice.
    Preserve the conservative old behavior when a library area is unavailable.
    """
    logical = 0.0
    for b in blocks:
        view = b.get("view")
        if not view:
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        directory = root / view
        lib = directory / (directory.name + "_tt.lib")
        if not lib.exists():
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        match = re.search(r"\barea\s*:\s*([\d.eE+-]+)", lib.read_text())
        if not match:
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        logical += float(match.group(1))
    if logical > chip_area + 0.01:
        raise ValueError(f"synthesis chip area {chip_area} is smaller than summed macro Liberty area {logical}")
    return max(0.0, chip_area - logical)


class PortMap(dict):
    """Port widths plus the actual declared index bounds for literal clock bits."""
    def __init__(self, ports, ranges=None):
        super().__init__(ports)
        self.ranges = ranges or {}


def module_port_ranges(body):
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)
    params = TL.module_params(body)
    hdr = body[:body.find(";")] if ";" in body else body
    out = {}
    for blob in (hdr, body):
        for m in re.finditer(r"\b(input|output|inout)\b([^;]*?)(?=;|\)\s*$|\binput\b|\boutput\b|\binout\b)", blob, re.S):
            seg = m[2]
            dims = re.findall(r"\[([^\]:]+):([^\]]+)\]", seg)
            bounds = None
            if len(dims) == 1:
                a, b = (TL._eval_int(x, params) for x in dims[0])
                if a is not None and b is not None:
                    bounds = [min(a, b), max(a, b)]
            names = re.sub(r"\[[^\]]*\]", " ", seg)
            for name in re.findall(r"\b([A-Za-z_]\w*)\b", names):
                if name not in TL._KW and name not in out:
                    out[name] = bounds
        if out:
            break
    return out


def rtl_ports(sources, top, root=None, dirs=False, defines=None):
    root = root or ROOT
    texts = []
    for f in sources:
        p = root / f
        if p.exists():
            texts.append(p.read_text(errors="replace"))
    # A spec with "defines" selects its interface by `ifdef (as synthesis and the kit lint do, ref_tile.py VERILOG_DEFINES):
    # run the real Verilog preprocessor with the same -DSYNTHESIS + spec defines, else the text parser takes the
    # `ifdef/`endif tokens for port names (HROW ACK candidates 066ec43c5).  No defines: the plain text parse, unchanged.
    # No spec defines but an `ifdef in the sources (a default-off port group in the header, dsfd_vm_be_sl
    # OT_SPVM_RESET_ACK, s81-grpA r3): preprocess with -DSYNTHESIS alone, as synthesis does; if the preprocessor cannot
    # run on these sources, keep the plain text parse (unchanged behaviour).
    implicit = not defines and any("`ifdef" in tx or "`ifndef" in tx for tx in texts)
    if defines or implicit:
        files = [root / f for f in sources if (root / f).exists()]
        inc = sorted({str(p.parent) for p in files})
        cmd = ["iverilog", "-g2012", "-E", "-o", "-", "-DSYNTHESIS"]
        cmd += ["-D" + d for d in (defines or [])] + ["-I" + p for p in inc] + [str(p) for p in files]
        try:
            run = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            run = None
        if run is None or run.returncode:
            if not implicit:
                raise RT.SpecError("RTL port preprocessing failed: " + (run.stderr[-2000:] if run else "iverilog missing"))
        else:
            texts = [run.stdout]
    # a module named through a macro (`define X top ... module `X: dsfd_coll_cb / cbf) is not seen by the text parser
    texts = [re.sub(r"\bmodule\s+`(\w+)", lambda m: f"module {top}" if re.search(
        rf"`define\s+{m.group(1)}\s+{re.escape(top)}\b", tx) else m.group(0), tx) for tx in texts]
    mods = TL.rtl_modules(texts)
    if top not in mods:
        return None
    return TL.module_port_dirs(mods[top]) if dirs else PortMap(TL.module_ports(mods[top]), module_port_ranges(mods[top]))


def check_pins(g: Gate, spec: dict, ports: dict | None, where="RTL"):
    if ports is None:
        g.add("FAIL", "pins", f"top module {spec['top']} not found in the {where} sources", "fix 'top' / 'sources'")
        return
    if RT.literal_pin_bits(spec):
        try:
            RT.validate_literal_pin_plan(spec, ports if where == "synthesized netlist" else None, ROOT)
        except RT.SpecError as e:
            g.add("FAIL", "pins", str(e), "preserve complete actual pin coverage, exact IO source and named M6 contacts")
    else:
        plan = {}
        for f, names in spec["pins"].items():
            for n in names:
                plan.setdefault(n, []).append(f)
        if spec["pins"].get("ANY"):
            g.add("WARN", "pins", f"{len(spec['pins']['ANY'])} port group(s) left to the IO placer (ANY): {spec['pins']['ANY'][:4]}",
                  "give every bus a face (and an offset range) from the die contract before the die integrates it")
        for n, fs in plan.items():
            if len(fs) > 1:
                g.add("FAIL", "pins", f"port {n} planned on {len(fs)} faces {fs}", "one face per port")
            if n not in ports:
                near = [p for p in ports if p.startswith(n.rstrip("[0]"))][:3]
                g.add("FAIL", "pins", f"pin plan names '{n}', not a port of {spec['top']} ({where})"
                      + (f"; ports like it: {near}" if near else ""), "name ports by their (scalar) base name")
        miss = [p for p in ports if p not in plan]
        if miss:
            g.add("FAIL", "pins", f"{len(miss)} ports not in the pin plan (exhaustive regions fail the floorplan): {miss[:8]}",
                  "assign every port to a face")
    one = [p for p, (w, vec) in ports.items() if vec and w == 1]
    if one:
        g.add("WARN", "pins", f"1-bit vector ports {one[:6]}: retain declared indices for literal clock entries; "
              "check actual mapped pin names for a hand pin list", "use the actual RTL and mapped pin names")
    for clock in RT.clock_ports(spec):
        # Entry-clock specs use literal bits, while the RTL header parser returns
        # vector base names. Keep pin-face plans grouped by base name, but accept
        # an in-range bit of a vector as an actual clock entry.
        bit = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]", clock)
        exists = clock in ports
        if bit and bit[1] in ports:
            width, vector = ports[bit[1]]
            bounds = getattr(ports, "ranges", {}).get(bit[1])
            exists = bool(vector and bounds and bounds[0] <= int(bit[2]) <= bounds[1])
        if not exists:
            g.add("FAIL", "pins", f"clock port {clock} is not a port of {spec['top']}", "fix clock_port")


# --------------------------------------------------------------------------------------------- pin fit / pin flops
def strict_widths(sources, top, params=None, root=None):
    """{port: (width, is_vector)} of the top with the SPEC's parameters applied, or None when the header is not fully
    resolved (submit_lint.top_ports: ANSI header, parameter defaults + overrides, packed dimensions multiplied; anything
    it does not model raises).  The pin-fit estimate refuses a kit, so it reads widths only from this parser: the
    textbook parser (rtl_ports) evaluates the module DEFAULTS -- hgi_dma_back_b2 (NB=8, VCR=8) and qfd_tt_up4_leaf (NL=4)
    came out 3-6x too wide, and both tiles are CLOSED."""
    sys.path.insert(0, str(HERE.parent / "closure_loop"))
    try:
        import submit_lint as SL
    except Exception:  # noqa: BLE001
        return None
    root = root or ROOT
    for f in sources:
        p = root / f
        if not p.exists() or p.suffix not in (".sv", ".v"):
            continue
        text = p.read_text(errors="replace")
        if not re.search(r"\bmodule\s+(?:automatic\s+)?" + re.escape(top) + r"\b", text):
            continue
        try:
            ports = SL.top_ports(text, top, {k: str(v) for k, v in (params or {}).items()})
        except Exception:  # noqa: BLE001  (ExprError and anything else: no estimate)
            return None
        return {n: (w, lsb >= 0) for n, w, lsb in ports} or None
    return None


FACE_LEN = {"W": 1, "E": 1, "N": 0, "S": 0}      # index into (W, H) of the face's length


def kit_pin_plan(spec: dict, ports: dict | None, outline, lc: dict | None = None):
    """(route pin settings, [{names, face, range, n, lo, hi, len, layers}]) of a kit, placed as the ROUTE places them
    (RT.route_pin_settings: the same functions that write kit.env).  n is None when a port width is not known."""
    lc = lc or RT.layer_contract(spec, RT.contract_slot(spec))
    st = RT.route_pin_settings(spec, lc)
    regs = []
    for r in RT.pin_regions(spec):
        ln = float(outline[FACE_LEN[r["face"]]])
        ws = [(ports or {}).get(n, (None, False))[0] for n in r["names"]]
        lo, hi = r["range"] if r["range"] else (0.0, ln)
        regs.append({**r, "n": None if any(w is None for w in ws) else sum(ws), "lo": lo, "hi": hi, "len": ln,
                     "layers": st["h"] if r["face"] in ("W", "E") else st["v"]})
    return st, regs


def check_pin_fit(g: Gate, spec: dict, ports: dict | None, outline, lc: dict | None = None):
    """GATE = ROUTE (flowfix 2026-10-13): the pin plan is judged with the route's own pin-placement settings.  The
    route chunks every region into ordered groups of 32 (OT_PIN_GROUP_MAX) and place_pins needs one section on one
    layer per group; the gate ran with one group per region, so a face filled to ~96 % of its slots passed the gate
    and died in the route (PPL-0093: qkd_seq_fan-kc2 23 of 1,623 pins, smh_pt_w, s81hc_ctpl, coll_tp8_col_mgb,
    qkd_land_grp).  tools/pin_fit.py holds the model (a lower bound: it never refuses a placeable plan)."""
    try:
        st, regs = kit_pin_plan(spec, ports, outline, lc)
    except RT.SpecError:
        return None                      # reported by the kit regeneration
    if st["exact"]:
        return st, regs
    if ports is None:
        g.add("INFO", "pin_fit", "pin fit not estimated: the top's port widths are not resolved from its header with the "
              "spec parameters (the --remote run places the pins with the route's settings)")
        return st, regs
    bad, unknown = [], []
    for r in regs:
        if r["n"] is None:
            unknown.append("/".join(r["names"][:3]))
            continue
        f = PF.region_fit(r["n"], r["lo"], r["hi"], r["len"], r["layers"], st["tracks"], st["group_max"], st["balance"])
        r["fit"] = f
        if not f["fits"]:
            where = f"{r['face']} face {r['len']:g} um" + (f" range {r['lo']:g}-{r['hi']:g}" if r["range"] else "")
            bad.append(f"{where} ({', '.join(r['names'][:4])}{', ...' if len(r['names']) > 4 else ''}): {f['why']}")
    for b in bad[:4]:
        g.add("FAIL", "pin_fit", "the route's pin placement cannot place this plan (PPL-0093 / PPL-0111 / PPL-0086 at "
              "3_2_place_iop; route "
              f"OT_PIN_GROUP_MAX={st['group_max']}{' + balanced place_pin' if st['balance'] else ''}, "
              f"{st['tracks']:g} track(s) a pin): {b}", PF.FIX_TEXT)
    if unknown:
        g.add("INFO", "pin_fit", f"pin fit not estimated for {len(unknown)} region(s) with a width the RTL parser could "
              f"not resolve ({', '.join(unknown[:4])}): the --remote run places them with the route's settings")
    return st, regs


# PIN ORDER (ROOT-PINORDER 2026-10-19, HBM-HCRING finding): an ABUTTED bus needs a defined bit order across its face.
# The route's PPL placement chunks a region into ordered groups of 32 (OT_PIN_GROUP_MAX) and places the groups
# independently (closed hbfd_rly_1136_WE: 13 descents in its 1,136-b bus), so two abutted tiles meet chunk-scrambled
# even when both are R0, and an R180 / MX / MY neighbour meets them fully reversed.  A port is ABUTTED when the kit
# places it at a planned position facing its neighbour (a "pin_ranges" entry) or lists it in "abutted_ports".  Wider
# than 32 bits, it must be placed in bit order: route.pin_balance (place_pin, bit k at lo + (hi-lo)(k+.5)/n; for a face
# against a mirrored neighbour also mirror the range and list the port in pin_order_desc) or an exact io_tcl.  A port
# that really is channel-routed (not abutted) may be named in "pin_order_waiver" {port: reason}.
PIN_ORDER_MAX_UNORDERED = 32
PIN_ORDER_FIX = ("add route.pin_balance {group_max 1, h, v} (disjoint per-port pin_ranges on the face); for a face that "
                 "abuts an R180 / MX / MY neighbour mirror the range and list the port in pin_order_desc; check the die "
                 "joint with tools/hier_contract/abutted_joint_audit.py; or name a channel-routed port in "
                 "pin_order_waiver {port: reason}")


def check_pin_order(g: Gate, spec: dict, plan):
    """FAIL when an abutted bus wider than 32 bits has no defined bit order in the route (see PIN ORDER above)."""
    if not plan:
        return
    st, regs = plan
    if st["exact"] or st["balance"]:
        return
    abut = set(spec.get("pin_ranges") or {}) | set(spec.get("abutted_ports") or [])
    waive = spec.get("pin_order_waiver") or {}
    if not isinstance(waive, dict) or any(not isinstance(v, str) or len(v.strip()) < 8 for v in waive.values()):
        g.add("FAIL", "pin_order", "pin_order_waiver must be {port: reason} with a real reason", PIN_ORDER_FIX)
        return
    bad, unknown = [], []
    for r in regs:
        for n in r["names"]:
            if n not in abut or n in waive:
                continue
            w = r["n"] if len(r["names"]) == 1 else None
            if w is None:
                unknown.append(n)
            elif w > PIN_ORDER_MAX_UNORDERED:
                bad.append(f"{n} ({w} b, {r['face']} face)")
    if bad:
        g.add("FAIL", "pin_order", f"{len(bad)} abutted bus(es) wider than {PIN_ORDER_MAX_UNORDERED} b without a defined "
              f"bit order (route OT_PIN_GROUP_MAX {st['group_max']} scatters chunks of 32): {', '.join(bad[:6])}"
              + (", ..." if len(bad) > 6 else ""), PIN_ORDER_FIX)
    if unknown:
        g.add("WARN", "pin_order", f"bit order not judged for {len(unknown)} abutted port(s) with an unresolved width "
              f"({', '.join(unknown[:4])}); the route places them in chunks of {st['group_max']}", PIN_ORDER_FIX)


OFLOP_TCL = "physical/qwen_die_masters/io_flop_at_pins.tcl"


def check_oflop(g: Gate, spec: dict, plan, dirs: dict | None, outline, tcl_text: str | None):
    """RECIPE 2 ON A DENSE FACE (flowfix 2026-10-13): kit recipe 2 puts the pin hold stages (out BUF + HB4 + BUF, in HB4
    + BUF) FIRM at the pins and then the pin flops FIRM at the same pins.  From ~6 b/um the legalised hold stages take
    more than the flops' default 1 um gap: flops and stages interleave, every flop -> stage -> pin chain crosses the
    column behind the face several times and global route fails there (GRT-0116: qkd_seq_fan-kc3 at 10.4 b/um, s81su
    swtl / swth / qbtl, qfd_vm_rr4_t-r41).  io_flop_at_pins.tcl now derives gap / columns from the face (tools/pin_fit.py
    oflop_plan); this check estimates the same numbers at submit and WARNs with the settings when the kit's hook cannot
    spread them.  It never refuses: on the 1,101 ref jobs of 10-12/13 the estimate flags all 7 face GRT-0116 routes but
    also 69 CLOSED ones (it assumes a hold stage and a pin flop on every port; the hook counts the real cells)."""
    if not plan or not RT.pin_hook_wrapper(spec) or not (spec.get("inhold") or spec.get("outhold")):
        return
    st, regs = plan
    ov = spec.get("orfs_vars", {})
    cols = int((spec.get("io_flop_at_pins") or {}).get("cols", PF.OFLOP_COLS))
    try:
        gap_set = float(ov["OT_OFLOP_GAP"]) if "OT_OFLOP_GAP" in ov else None
    except (TypeError, ValueError):
        gap_set = None
    auto = bool(tcl_text and "OT_OFLOP_AUTO" in tcl_text) and str(ov.get("OT_OFLOP_AUTO", "1")) != "0"
    W, H = float(outline[0]), float(outline[1])
    worst = {}
    for r in regs:
        if not r.get("n"):
            continue
        ds = {(dirs or {}).get(n) for n in r["names"]}
        stage = max([PF.STAGE_OUT_UM if (d != "input" and spec.get("outhold")) else 0.0 for d in ds]
                    + [(PF.STAGE_IN_UM if spec.get("inhold_drv", "x") else 0.378) if (d != "output" and spec.get("inhold")) else 0.0
                       for d in ds])
        if not stage:
            continue
        d = PF.face_density(r["n"], r["hi"] - r["lo"], r["layers"], st["tracks"], st["balance"])
        p = PF.oflop_plan(d, stage, r["face"] in ("W", "E"), cols)
        if p["dense"] and p["depth"] > worst.get(r["face"], ({"depth": 0},))[0]["depth"]:
            worst[r["face"]] = (p, d, r)
    for face, (p, d, r) in sorted(worst.items()):
        deep = (W if face in ("W", "E") else H) - 2 * RT.CORE_MARGIN
        what = (f"{face} face {d:.1f} pins/um ({', '.join(r['names'][:3])}): recipe-2 hold stages take {p['depth']} um "
                f"behind the face, the pin flops need gap {p['gap']} um and {p['cols']} columns")
        # OT_OFLOP_GAP / cols are one setting for every face of the kit: name the largest
        setting = (f'"orfs_vars": {{"OT_OFLOP_GAP": "{max(x[0]["gap"] for x in worst.values())}"}} and '
                   f'"io_flop_at_pins": {{"cols": {max(x[0]["cols"] for x in worst.values())}}}')
        if p["band"] > PF.OFLOP_DEPTH_MAX * deep:
            g.add("WARN", "oflop", f"{what} = {p['band']} um, more than {PF.OFLOP_DEPTH_MAX:.0%} of the {deep:.1f} um core "
                  "behind the face (GRT-0116 class)", "a longer edge or pins on two layers (lower face density), or "
                  "drop the pin hold stages of this face (\"outhold\": false + route.hold_delay in RTL)")
        elif gap_set is not None and gap_set < 0.8 * p["gap"]:
            g.add("WARN", "oflop", f"{what}, but the kit pins OT_OFLOP_GAP={gap_set:g}: the flops are stacked on the hold "
                  "stages (GRT-0116 behind the face: qkd_seq_fan-kc3)", f"drop OT_OFLOP_GAP (the hook derives it) or set {setting}")
        elif gap_set is None and not auto:
            g.add("WARN", "oflop", f"{what}, but this source's {OFLOP_TCL} has no automatic spread"
                  + (" (OT_OFLOP_AUTO=0)" if tcl_text and "OT_OFLOP_AUTO" in tcl_text else "")
                  + ": gap 1.0 um stacks the flops on the hold stages (GRT-0116 behind the face: qkd_seq_fan-kc3)",
                  f"rebase the kit on main (io_flop_at_pins.tcl with OT_OFLOP_AUTO) or set {setting}")
        else:
            g.add("INFO", "oflop", what + (f" (kit OT_OFLOP_GAP={gap_set:g})" if gap_set is not None else " (derived in the flow)"))


# --------------------------------------------------------------------------------------------- sources
PATH_RE = re.compile(r"(?:/src/|\{SRC\}/|\$SRC/|\$\{SRC\}/)?\b((?:physical|tools|rtl|results|configs)/[\w./+-]+\."
                     r"(?:tcl|sdc|sh|py|v|sv|svh|vh|env|lef|lib|json))\b")


def git_show(commit, path):
    if not commit:
        p = ROOT / path
        return p.read_text(errors="replace") if p.is_file() else None
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def referenced_closure(seeds, commit=None, args_env=None):
    """every repo path reachable from the seeds through the files they name (tcl source, sh, env, sdc; a .py named by
    a command is scanned one level deep -- generators such as hbm_w2_station_hier_physical.py write the hooks into
    their run.sh -- and paths found only in a .py are checked for the sync set, not for existence)"""
    seen, missing, weak = set(), set(), set()
    soft = set()     # found only inside a generator .py and not a flow script (.tcl/.sdc/.sh/.env): may be an unused option
    todo = [(s, 0, False) for s in seeds]
    while todo:
        p, depth, from_py = todo.pop()
        p = p.replace("//", "/")
        if p in seen:
            continue
        txt = git_show(commit, p)
        if txt is None:
            if "$" not in p and "*" not in p:
                (weak if from_py else missing).add(p)
            continue
        seen.add(p)
        if from_py and (not p.endswith((".tcl", ".sh", ".env", ".sdc")) or depth > 0 and p.endswith(".sv")):
            soft.add(p)
        if p.endswith((".tcl", ".sh", ".env", ".sdc")) or (p.endswith(".py") and depth == 0):
            body = re.sub(r"(?m)^\s*#.*$", "", txt)
            for m in PATH_RE.finditer(body):
                q = m.group(1)
                if "$" not in q and "{" not in q:
                    # ${VAR:-default}: the default only applies when the caller does not set VAR -> soft
                    dflt = body[max(0, m.start() - 2):m.start()] == ":-"
                    todo.append((q, depth + 1, from_py or p.endswith(".py") or dflt))
            if p.endswith("route_master.sh") and args_env:
                todo.append((f"physical/qwen_die_masters/cfg/{args_env}.env", depth + 1, False))
    return seen, missing - seen, soft


def check_sources(g: Gate, job: dict, extra_seeds=(), commit=None):
    src = job.get("source") or {}
    synced = [str(x).rstrip("/") for x in list(src.get("paths", DEFAULT_SRC_PATHS)) + list(src.get("extra_paths", []))]
    cmds = []
    st = job.get("stages") or {}
    for k in ("route", "calibrate", "collect"):
        if isinstance(st.get(k), dict) and st[k].get("cmd"):
            cmds.append(st[k]["cmd"])
    for b in st.get("bench") or []:
        cmds.append(b.get("cmd", ""))
    seeds = set(extra_seeds)
    cfg = None
    for c in cmds:
        for m in PATH_RE.finditer(c.replace("{SRC}/", "")):
            seeds.add(m.group(1))
        m = re.search(r"route_master\.sh\s+(\S+)", c)
        if m:
            cfg = m.group(1)
    for p in (job.get("verdict") or {}).get("post_sdc") or []:
        seeds.add(p)
    seen, missing, soft = referenced_closure(sorted(seeds), commit, cfg)
    out_all = sorted(p for p in seen if not any(p == s or p.startswith(s + "/") for s in synced))
    if True:   # the loop ships these flow helpers into every job (closure_loop HELPERS / tt_overlay TTB_FILES)
        soft |= {f"physical/common_flow/{n}" for n in ("macro_sliver_block.tcl", "edge_sliver_block.tcl",
                                                       "macro_cts_cluster.tcl", "io_ref_routed.sdc")}
        soft |= {f"physical/common_flow/{n}" for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                       "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc")}
    outside = [p for p in out_all if p not in soft]
    if missing:     # WARN: a recipe may write the file at run time (generated SDC / run script)
        g.add("WARN", "sources", f"{len(missing)} referenced file(s) do not exist"
              + (f" at {commit}" if commit else "") + f": {sorted(missing)[:6]}", "commit them / fix the path")
    if outside:
        g.add("FAIL", "sources", f"{len(outside)} referenced file(s) outside the synced source paths {synced}: "
              f"{outside[:6]} (the loop copies only source.paths + extra_paths; the route dies with 'No rule to make "
              f"target /src/...')", "add their directories to source.extra_paths (or drop source.paths for the default)")
    return {"referenced": len(seen), "missing": sorted(missing), "outside": outside}


# --------------------------------------------------------------------------------------------- kit checks
MULTI_ROOT_PROOF = "related crossing lacks actual finite"
MULTI_ROOT_DEFERRAL = "RELATED_PATH_DEFERRED"


def stale_multi_root_sdcs(kd: Path) -> list:
    """Kit SDCs baked by ref_tile.py before f489fa9d5: they carry the multi-root related-crossing finite-path proof
    without the multi-mode pre-scene deferral, so under the gate/production OT_HOLD_MM session (read_sdc -mode ss before
    any scene) find_timing_paths returns nothing and 1_synth/synth_odb dies with 'OT_MULTI_ROOT: related crossing lacks
    actual finite max STA path' although the same netlist + SDC pass a single-scene replay (TT head h3, xcol_{e,w}_rq,
    2026-10-15).  The generator is current; only the committed kit bytes are stale."""
    out = []
    for f in sorted(kd.glob("*.sdc")):
        t = f.read_text(errors="replace")
        # independent-domain leaves never reach the proof (any crossing is refused structurally first)
        if MULTI_ROOT_PROOF in t and MULTI_ROOT_DEFERRAL not in t and "set ::ot_ce_related_data 1" in t:
            out.append(f.name)
    return out



def stale_native_cts_sdcs(kd: Path, spec: dict) -> list:
    """Require operational current generated policy, only for native leaf CTS kits.

    These modes prohibit custom SDC hooks. Compare the complete generated SDCs,
    including stage flags, executable procedure and its invocation: a log marker,
    commented correction, no-op, or later re-propagation is not sufficient proof.
    This local/new-submit check never walks accepted jobs or changes frozen SDCs.
    """
    if not RT.clock_entry_constraints.native_leaf(spec):
        return []
    expected = {
        "clock.sdc": RT.gen_sdc(spec, float(spec.get("route", {}).get("period_ps", 770))),
        "clock_entry.sdc": "set ::ot_ce_require_wire 1\n" + RT.ce_generate(spec),
        "signoff.sdc": RT.gen_signoff(spec, spec.get("refglob", "*"), ",".join(spec.get("inter", [])) or "none_*"),
    }
    return [name for name, text in expected.items()
            if not (kd / name).is_file() or (kd / name).read_bytes() != text.encode()]


PIN_REGS_FAIL_AFTER = "2026-10-16T19:50:00-07:00"   # OWNER RULE 19:50 PT 10-15 + 24 h of WARN


def check_pin_regs(g: Gate, kd: Path, spec: dict, now=None):
    """OWNER RULE 19:50 PT 2026-10-15: every new tile registers every input and every output at its pin.  A leaf-tile
    kit whose route does not insert pin registers (kit.env without OT_PIN_REGS=1) and records no opt-out reason is WARNed
    until PIN_REGS_FAIL_AFTER and refused after it; re-kit it (ref_tile.py gen with recipe 3).  CLOSED tiles stand (they
    are not re-routed); a loop successor of an already-routed parent stays a WARN."""
    import datetime as dt
    if spec.get("kind", "tile") != "tile":
        return
    try:
        env = (kd / "kit.env").read_text()
    except OSError:
        return
    pr = spec.get("pin_regs") or {}
    from kit_orfs_vars import parse
    try:
        enabled = parse(env).get("OT_PIN_REGS") == "1"
    except ValueError as ex:
        g.add("FAIL", "pin_regs", str(ex))
        return
    if enabled:
        g.add("INFO", "pin_regs", "pin registers on every data input and output (+1 cycle each; kit pin_regs.json)")
        return
    if pr.get("enable") is False and str(pr.get("reason", "")).strip():
        g.add("INFO", "pin_regs", f"pin registers opted out: {pr['reason'][:300]}")
        return
    late = (now or dt.datetime.now().astimezone()) >= dt.datetime.fromisoformat(PIN_REGS_FAIL_AFTER)
    sev = "FAIL" if late and not spec.get("auto_react_parent") else "WARN"
    g.add(sev, "pin_regs", f"{RT.PIN_REGS_RULE}: this kit's ports are not registered at the pins and no opt-out is recorded"
          + ("" if late else f" (WARN until {PIN_REGS_FAIL_AFTER}, then refused)"),
          "re-kit with recipe 3 (python3 tools/ref_tile/ref_tile.py gen <spec> with \"recipe\": 3, or delete kit.env "
          "for a new kit), or record \"pin_regs\": {\"enable\": false, \"reason\": \"...\"}")


def check_port_latency(g: Gate, kd: Path, spec: dict, out: str, commit=None, now=None, binding=None):
    """PORT-LATENCY (ROOT 2215): a kit that inserts pin registers (kit.env OT_PIN_REGS=1) must leave the elaborated
    per-port table of its synthesis (ot_pin_regs.tsv + wrapper); it is exported here with tools/ref_tile/port_latency.py
    (g.port_latency -> gate_result.json "port_latency") so the per-port stages are visible before the route.  A missing or
    malformed table is a WARN until PIN_REGS_FAIL_AFTER, then a FAIL: the compilers would otherwise see no stages."""
    import base64
    import datetime as dt
    import tempfile
    import zlib
    try:
        env = (kd / "kit.env").read_text()
    except OSError:
        return
    from kit_orfs_vars import parse
    try:
        enabled = parse(env).get("OT_PIN_REGS") == "1"
    except ValueError as ex:
        g.add("FAIL", "port_latency", str(ex))
        return
    if not enabled:
        declared = spec.get("pin_regs")
        if isinstance(declared, dict) and declared.get("enable") is not False:
            g.add("FAIL", "port_latency", "spec enables pin registers but kit lacks a literal OT_PIN_REGS=1 option")
        return
    late = (now or dt.datetime.now().astimezone()) >= dt.datetime.fromisoformat(PIN_REGS_FAIL_AFTER)
    sev = "FAIL" if late else "WARN"
    m = re.search(r"^GATE_PIN_REGS_B64 (\S+) (\S+)\s*$", out, re.M)
    if not m:
        g.add(sev, "port_latency", "kit inserts pin registers (OT_PIN_REGS=1) but synthesis left no ot_pin_regs.tsv / "
              "ot_pin_regs_wrapper.v: the compilers would see no per-port stages",
              "check that physical/common_flow/ot_keep_regs.tcl sourced ot_pin_regs.tcl in 1_synth (OT_PIN_REGS line in the log)")
        return
    sys.path.insert(0, str(ROOT / "tools/ref_tile"))
    import port_latency as PL
    with tempfile.TemporaryDirectory() as td:
        tab, wrap = Path(td) / "ot_pin_regs.tsv", Path(td) / "ot_pin_regs_wrapper.v"
        tab.write_bytes(zlib.decompress(base64.b64decode(m.group(1))))
        wrap.write_bytes(zlib.decompress(base64.b64decode(m.group(2))))
        src = commit if commit and re.fullmatch(r"[0-9a-f]{40}", str(commit)) else "0" * 40
        try:
            rep = PL.export(tab, wrap, spec["top"], src)
            def role_source(path):
                # Bind role-defining SDC to the exact archived synthesis bytes,
                # including snapshots without a clean provenance commit.
                if binding is not None:
                    files = _BlobFiles(binding.get("files") or [])
                    try:
                        return files[path].decode() if path in files else None
                    except (KeyError, UnicodeError):
                        return None
                    finally:
                        files.close()
                return git_show(commit, path)
            rep["control_roles"] = PL.validate_roles(rep, wrap, spec, role_source)
        except ValueError as ex:
            g.add("FAIL", "port_latency", f"elaborated pin-register table rejected: {ex}", "fix ot_pin_regs.tcl output / the kit")
            return
    if src != commit:
        rep["source_commit"] = None
        rep["source_note"] = f"gate snapshot {commit}: not a git commit; the route's CLOSED record carries the bound report"
    g.port_latency = rep
    regs = {d: sum(1 for p in rep["ports"].values() if p["dir"] == d and p["register_edges"]) for d in ("input", "output")}
    g.add("INFO", "port_latency", f"elaborated pin registers: {regs['input']} input / {regs['output']} output ports +1 edge; "
          f"{sum(1 for p in rep['ports'].values() if not p['register_edges'])} ports pass through (clock/reset/excluded/inout)")


XCLK_RE = re.compile(r"^GATE_XCLK (launch=.*)$", re.M)


def check_cross_clock(g: Gate, spec: dict, out: str, cts: bool):
    """CROSS-CLOCK GATE (CX-IJ-ROOT 2026-10-18; Gate-Rule: tightening, scoped to multi-clock kits).  Same-tile reg->reg
    paths BETWEEN two clocks of the tile (e.g. clk_s 1.2 GHz stream / clk_q 0.9 GHz serial under related_pll_ratio) are
    timed by tools/ref_tile/cross_clock_paths.tcl after CTS under the kit's own signoff.sdc, i.e. with the sign-off
    related edge windows and the distinct-entry reserve that SDC applies (setup 150/210, hold 100 inter-clock
    uncertainty) -- the margins are read from the generated SDC, never re-stated here.  A crossing covered by an SDC
    exception (false path / multicycle / max-min delay / clock groups: the declared CDC, epoch or landing rule) is not
    counted.  An undeclared pair with setup slack < 0 FAILS (HBM SU cxport dl/rc 761317600: gate WARN, route TT -166.7 /
    -173.4 on the 3:4 crossing inside one leaf); undeclared hold < 0 WARNs (route hold repair).  Kits with one clock
    (one declared clock port and one register clock in STA) are unchanged: no item at all."""
    scope = re.search(r"^GATE_XCLK_SCOPE clocks=(\d+)(?: names=(\S*))?", out, re.M)
    sta_clocks = int(scope.group(1)) if scope else 0
    ports = ([spec["clock_port"]] if spec.get("clock_port") else []) + list(spec.get("clock_ports") or [])
    multi = len(dict.fromkeys(ports)) >= 2 or sta_clocks >= 2
    if not multi:
        return
    if not cts:
        g.add("WARN", "cross_clock", "multi-clock kit: same-tile cross-clock reg->reg paths are timed only by a --cts gate "
              "(signoff.sdc inter-clock margins after CTS)", "rerun the gate with --cts")
        return
    if not re.search(r"^GATE_XCLK_DONE", out, re.M):
        g.add("WARN", "cross_clock", "multi-clock kit: the cross-clock reg->reg analysis did not complete (see the remote "
              "pc.log: signoff.sdc read / STA error)", "fix the signoff SDC read and re-gate with --cts")
        return
    if sta_clocks < 2:
        g.add("INFO", "cross_clock", f"{sta_clocks} clock(s) reach registers in STA: no same-tile cross-clock reg->reg path")
        return
    fails = []
    for line in XCLK_RE.findall(out):
        r = dict(re.findall(r"(\w+)=(\S+)", line))
        pair = f"{r.get('launch')}->{r.get('capture')}"
        timed, declared, bad = int(r.get("timed", 0)), int(r.get("declared", 0)), int(r.get("violating", 0))
        worst = None if r.get("worst_ps", "-") == "-" else float(r["worst_ps"])
        unc = r.get("uncertainty_ps", "-")
        capped = " (path cap reached: count is a lower bound)" if r.get("capped") == "1" else ""
        dk = r.get("declared_kinds", "-")
        decl = f"; {declared} declared ({dk}) not counted" if declared else ""
        if r.get("kind") == "max" and worst is not None and worst < 0:
            fails.append(pair)
            g.add("FAIL", "cross_clock",
                  f"{bad} undeclared {pair} reg->reg endpoint(s) fail SETUP at TT under signoff.sdc (inter-clock "
                  f"uncertainty {unc} ps): worst {worst:.1f} ps {r.get('startpoint')} -> {r.get('endpoint')}{capped}{decl}",
                  "a direct cross-clock crossing with logic does not close in one leaf (3:4 VCO-tick window minus the "
                  "distinct-entry reserve): split into one-root halves with a banked seam (S81 x34 / HBM cxdl 1018), "
                  "move the crossing to an epoch bank (related_pll_dividers), or declare and price a multicycle/landing rule")
        elif r.get("kind") == "min" and worst is not None and worst < 0:
            g.add("WARN", "cross_clock",
                  f"{bad} undeclared {pair} reg->reg endpoint(s) fail HOLD before route repair (inter-clock uncertainty "
                  f"{unc} ps): worst {worst:.1f} ps at {r.get('endpoint')}{capped}{decl}",
                  "route hold repair must buffer these; a same-endpoint setup FAIL makes that impossible")
        elif timed or declared:
            g.add("INFO", "cross_clock", f"{pair} {r.get('kind')}: {timed} undeclared timed path(s), worst "
                  f"{'-' if worst is None else f'{worst:.1f}'} ps (uncertainty {unc} ps){decl}")
    if not fails:
        g.add("INFO", "cross_clock", f"{sta_clocks} register clocks ({scope.group(2) or ''}): no undeclared cross-clock "
              "reg->reg setup violation under signoff.sdc")


def check_memory_ff(g: Gate, out: str):
    """MEMORY-FF LINT (ROOT 2026-10-17, coordinator from S-ELEM): yosys memory inference folded a register into an
    inferred ROM/memory read port (MEMORY_DFF after PROC_ROM / MEMORY_BMUX2ROM).  The named RTL register disappears, and the
    table decode can land in a half-cycle or un-pipelined hop (S81 dsfd_engram_lkp_static14 st6: roll_h absorbed, TT
    -57.9 ps on 2,355 endpoints).  Reported before routing so the lead confirms or rewrites the table."""
    merges = re.findall(r"^GATE_MEMFF Checking read port `([^']+)'\[(\d+)\] in module `\\?([^']+)': (merg\w+ [\w ]*FF to cell)",
                        out, re.M)
    roms = sum(int(n) for n in re.findall(r"^GATE_MEMFF Converted (\d+) switch", out, re.M))
    if not merges:
        if roms:
            g.add("INFO", "memory_ff", f"yosys converted {roms} case table(s) to ROM; no register was folded into a read port")
        return
    where = sorted({f"{mod}:{port}[{i}] ({how})" for port, i, mod, how in merges})
    g.add("WARN", "memory_ff",
          f"yosys MEMORY_DFF folded {len(merges)} register(s) into inferred memory/ROM read ports "
          f"({roms} case table(s) became ROMs): " + "; ".join(where[:8]) + (f" (+{len(where) - 8} more)" if len(where) > 8 else "")
          + " -- the RTL register is gone from the netlist and its table decode may sit in a half-cycle / un-pipelined hop",
          "write the table as a one-hot AND-OR select (static14 st7) or keep the register out of the inferred memory "
          "(e.g. (* rom_style = \"logic\" *) on the table / (* keep *) on the register) and re-gate")


def _kit_env(kd: Path) -> str | None:
    try:
        return (kd / "kit.env").read_text()
    except OSError:
        return None


def check_keep_static(g: Gate, kd: Path, spec: dict):
    """KEEP-MODULE AUDIT, static half (ROOT-KEEP 10-18): a keep entry the RTL instantiates with #(...) elaborates as
    $paramod\\NAME\\..., which ORFS SYNTH_KEEP_MODULES ("NAME" / "NAME\\$*") never matches under the verilog frontend."""
    env = _kit_env(kd)
    entries = KA.keep_entries(env, spec)
    if not entries:
        return
    try:
        from kit_orfs_vars import parse
        frontend = parse(env or "").get("SYNTH_HDL_FRONTEND", "")
    except ValueError:
        frontend = ""
    if frontend == "slang":
        g.add("INFO", "keep_modules", f"{len(entries)} keep entries under the slang frontend (NAME$<n> names match)")
        return
    hits = KA.parameterised_instances(entries, spec.get("sources"), ROOT)
    for e, where in sorted(hits.items()):
        g.add("FAIL", "keep_modules", f"keep entry {e} is instantiated with a #(...) parameter override ({', '.join(where[:4])}"
              f"{' ...' if len(where) > 4 else ''}): yosys elaborates it as $paramod\\{e}\\..., SYNTH_KEEP_MODULES matches "
              "nothing and the copy is flattened / merged back (HBM lgtap r2, 6a79110b8)",
              "unparameterise the kept module (lgtap LGTAP2) or put (* keep_hierarchy *) on its module definition")


def check_keep_modules(g: Gate, kd: Path, spec: dict, out: str):
    """KEEP-MODULE AUDIT, post-synthesis half: every keep entry must match a surviving module or cell type."""
    entries = KA.keep_entries(_kit_env(kd), spec)
    if not entries:
        return
    m = re.search(r"^GATE_KEEP_NETLIST (.*)$", out, re.M)
    summary = None
    if m:
        try:
            summary = json.loads(m.group(1))
        except ValueError:
            summary = None
    warns = re.findall(r"^GATE_KEEPWARN (.*)$", out, re.M)
    for sev, msg in KA.judge(entries, summary, warns):
        g.add(sev, "keep_modules", msg, "unparameterise the kept module or put (* keep_hierarchy *) on its definition; "
              "check the entry names a module the top actually instantiates" if sev == "FAIL" else "")


def check_kit_shell(g: Gate, kd: Path):
    syntax = subprocess.run(["bash", "-n", str(kd / "kit.env")], capture_output=True, text=True)
    if syntax.returncode or syntax.stderr.strip():
        g.add("FAIL", "kit_shell", "kit.env is not valid Bash: " + syntax.stderr.strip()[-400:],
              "regenerate with the current quoted EXTRA generator, commit, then run an exact source-bound gate")
        return False
    return True


def check_kit(g: Gate, kd: Path, job: dict | None, commit=None):
    stale = stale_multi_root_sdcs(kd)
    if stale:
        g.add("FAIL", "kit_sdc", f"{stale} predate the multi-mode pre-scene deferral of the OT_MULTI_ROOT related-crossing "
              "proof (f489fa9d5): ORFS synth_odb fails 'related crossing lacks actual finite max STA path' under OT_HOLD_MM",
              "rebase on main and re-run ref_tile.py gen for this kit, commit, then gate")
    spec = RT.load_spec(str(kd / "spec.json"))
    try:
        fresh = RT.gen(str(kd / "spec.json"), spec.get("std_area_um2"), write=False)
    except RT.SpecError as ex:
        g.add("FAIL", "spec", str(ex), "fix the tile spec")
        return spec
    stale_native = stale_native_cts_sdcs(kd, spec)
    if stale_native:
        g.add("FAIL", "native_cts_sdc", f"{stale_native} differ from current generated native CTS stage policy "
              "(4af58769b): declared standard CTS roots must be ideal before CTS, while raw hard-entry roots "
              "and require-wire/postCTS checks retain actual propagation; a marker alone is insufficient",
              "rebase on main; run python3 tools/ref_tile/ref_tile.py gen <this kit's spec.json>; "
              "review unchanged RTL/pins/periods, commit regenerated kit, then run a fresh source-bound --cts gate "
              "and submit a new normal successor; preserve original accepted/frozen jobs")
    for sev, chk, msg, fix in fresh["findings"]:
        g.add(sev, chk, msg, fix)
    check_pin_regs(g, kd, spec)
    fp = json.loads((kd / "floorplan.json").read_text())
    if [round(x, 3) for x in fp["die"][2:]] != [round(x, 3) for x in fresh["outline"]]:
        g.add("FAIL", "kit", f"kit outline {fp['die'][2:]} != regenerated {fresh['outline']}", "re-run ref_tile.py gen")
    env = (kd / "kit.env").read_text()
    check_kit_shell(g, kd)
    if "pin_group_max" in spec.get("route", {}):
        pgm = re.search(r"^export OT_PIN_GROUP_MAX=(\d+)$", env, re.M)
        if not pgm or int(pgm[1]) != RT.pin_group_max(spec):
            g.add("FAIL", "pin_group", "kit ordered pin chunk limit differs from route.pin_group_max", "re-run ref_tile.py gen")
    if "PLACE_DENSITY_LB_ADDON=" not in env:
        g.add("FAIL", "density", "kit leaves ORFS's PLACE_DENSITY_LB_ADDON in force: the placer target becomes lower-bound + "
              "0.05, not the spec PD (qkd_nhb_pbst 0.50 -> 0.1075, GPL-0305)", "re-run ref_tile.py gen")
    lc = fp["layer_contract"]
    rl = re.search(r"^RLAYERS='M2 (M[2-9])'$", env, re.M)
    if not rl:
        g.add("FAIL", "layer", "kit.env has no explicit RLAYERS M2..M2-M9 (a script default would override the "
              "layer contract)", "re-run ref_tile.py gen")
    elif spec["kind"] == "tile":
        fresh_lc = RT.layer_contract(spec, RT.contract_slot(spec))
        if rl.group(1) != fresh_lc["rlayers"][1] or lc.get("pg_layer") != fresh_lc["pg_layer"]:
            g.add("FAIL", "layer", f"kit routes signals to {rl.group(1)} / PG {lc.get('pg_layer')} but the layer contract "
                  f"gives cap {fresh_lc['rlayers'][1]} / PG {fresh_lc['pg_layer']} ({fresh_lc.get('cap_basis')}; new tiles "
                  "cap at M5, M6 only with layer_cap_grant)", "re-run ref_tile.py gen")
        cap_n = int(rl.group(1)[1:])
        if cap_n < 5:
            cr = re.search(r"^CLOCK_RLAYERS='(M[2-9]) (M[2-9])'$", env, re.M)
            try:
                want = RT.clock_rlayers(fresh_lc)
            except RT.SpecError as e:
                want = None
                g.add("FAIL", "layer", str(e), "raise the tile's signal cap to >= M3")
            if want and (not cr or cr.groups() != want):
                g.add("FAIL", "layer", f"signal cap {rl.group(1)} needs CLOCK_RLAYERS='{want[0]} {want[1]}' (OpenROAD needs a "
                      "two-layer clock range; the ASAP7 default M4..cap fails ODB-0137 at floorplan)", "re-run ref_tile.py gen")
        pins_used = set()
        for k in ("PIN_H", "PIN_V", "export OT_PIN_BALANCE_H", "export OT_PIN_BALANCE_V"):
            mm = re.search(rf"^{k}='([^']*)'", env, re.M)
            pins_used |= set(mm.group(1).split()) if mm else set()
        over = sorted(x for x in pins_used if re.fullmatch(r"M\d+", x) and int(x[1:]) > cap_n)
        if over and not (over == ["M6"] and fresh_lc.get("m6_pin_grant")):
            g.add("FAIL", "layer", f"pin layers {over} above the tile cap {rl.group(1)}: the parent strap layer would "
                  "carry pins", "pins on M4/M5 (route.pin_h / pin_v / pin_balance)")
    elif rl is not None and spec["kind"] == "cluster":
        if RT.cluster_level(spec) == 2:      # two-level cluster (Q-CLUSTER 2026-10-17): signals M7, PG M8
            cap, grant, want_pg = "M7", None, "M8"
        else:
            (cap, grant), want_pg = RT.cluster_signal_cap(spec, RT.contract_slot(spec)), "M7"
        if rl.group(1) != cap or lc.get("pg_layer") != want_pg:
            g.add("FAIL", "layer", "cluster kit signals/PG differ from its audited layer contract", "re-run ref_tile.py gen")
        if grant:
            g.add("INFO", "layer_grant", f"digest-bound {cap} grant {grant['source']}; no die signals through rectangle; phase-aligned die PG required")
    g.add("INFO", "layer", f"{spec['kind']}: PG {lc['pg_layer']} stripes as pins, signals {lc['rlayers'][0]}-"
          f"{lc['rlayers'][1]}, parent strap {lc['strap_layer']}"
          + (f", cap {lc['layer_cap']} ({lc.get('cap_basis')})" if lc.get("layer_cap") else "")
          + (f"; children PG {lc['children']}" if lc.get("children") else ""))
    pdn = (kd / "pdn.tcl").read_text()
    if re.search(r"define_pdn_grid[^\n]*-macro", pdn) and "ot_ref_present" not in pdn:
        g.add("FAIL", "pdn", "macro grid without a present-master guard (PDN-0217)", "re-run gen")
    # pins vs RTL
    ports = rtl_ports(spec["sources"], spec["top"], defines=spec.get("defines"))
    check_pins(g, spec, ports)
    # pin plan vs the ROUTE's pin placement (same settings as the route: one source of truth), recipe-2 pin-flop spread
    plan = check_pin_fit(g, spec, strict_widths(spec["sources"], spec["top"], spec.get("params")), fresh["outline"])
    check_pin_order(g, spec, plan)
    tcl = ROOT / OFLOP_TCL
    check_oflop(g, spec, plan, rtl_ports(spec["sources"], spec["top"], dirs=True, defines=spec.get("defines")), fresh["outline"],
                tcl.read_text(errors="replace") if tcl.is_file() else None)
    # RTL lint
    files = [str(ROOT / f) for f in spec["sources"] if (ROOT / f).exists()]
    hard = sorted({RT.view_name(c["view"]) for c in spec["children"]})
    r = TL.rtl_lint(files, hard, spec.get("hard_define"), top=spec["top"])
    check_keep_static(g, kd, spec)
    for k, v in r["findings"].items():
        sev = "FAIL" if k == "hard_child_params" else "WARN"
        fix = ("decoded constant-index slices; the --remote synthesis smoke decides (a SHARE stall FAILs there)"
               if k == "runtime_partselect" else "no #() on hard children under the hard define")
        for line in v[:2]:
            g.add(sev, "rtl", f"{k}: {line}", fix)
    # children + macro views
    for it in spec["children"]:
        v = it["view"]
        lef = ROOT / v / f"{RT.view_name(v)}.lef"
        res = child_lint.lint(str(lef), str(ROOT / v))
        if res["verdict"] != "PASS":
            g.add("FAIL", "children", f"{RT.view_name(v)} child_lint: " + "; ".join(res["fails"])[:600],
                  "re-export the child through tools/ref_tile (exact abstract, PG stripes, keepout, TT/FF/SS)")
        for w in res["warns"]:
            g.add("WARN", "children", f"{RT.view_name(v)}: {w}", "export the child's clock insertion (ref_tile export)")
    for it in spec["macros"] + spec["children"]:
        v = it["view"]
        miss = [c for c in ("ss", "ff", "tt") if not (ROOT / v / f"{RT.view_name(v)}_{c}.lib").exists()]
        if miss:
            g.add("FAIL", "libs", f"{RT.view_name(v)}: no {', '.join(miss)} lib", "export all three corners")
    if job is not None:
        if not job.get("ref_tile"):
            g.add("WARN", "job", "job spec lacks \"ref_tile\": true", "submit the generated job.json")
        if "tools/ref_tile/ref_route.sh" not in job["stages"]["route"]["cmd"]:
            g.add("FAIL", "job", "route command is not tools/ref_tile/ref_route.sh", "use the generated job.json")
        check_sources(g, job, fp.get("referenced", []), commit)
    return spec


# GATE STEP CAP (ROOT 2026-10-15): seconds one capped gate step (CTS run, trial GRT) may take before it is a stall
GATE_STEP_CAP_S = int(os.environ.get("OT_GATE_STEP_CAP_S", "14400"))


# --------------------------------------------------------------------------------------------- remote
REMOTE_SH = r"""set -uo pipefail
R={R}; mkdir -p $R/src $R/bin
# Keep the original full measurement stream on the host. GNU tee -p continues
# writing this file if SSH closes its output pipe; the admitted job must finish
# and retain its terminal receipt rather than dying at the next echo.
exec > >(tee -p "$R/execution.log") 2>&1
# Intentional early exits (for example failed floorplan geometry) are terminal
# too. The trap records script status; tool status remains in GATE_*_RC.
trap 'rc=$?; echo "GATE_SCRIPT_RC=$rc"; echo GATE_DONE' EXIT
ACTUAL=$(sha256sum $R.tgz | cut -d' ' -f1)
[ "$ACTUAL" = "{ARCHIVE_SHA256}" ] || {{ echo GATE_SOURCE_BINDING_FAIL; exit 1; }}
echo "GATE_SOURCE_ARCHIVE_SHA256=$ACTUAL"
tar -xzf $R.tgz -C $R/src || exit 1
rm -f $R.tgz
cat > $R/bin/docker <<'EOS'
#!/bin/bash
for e in ${{PATH//:/ }}; do if [ -x "$e/docker" ] && ! [ "$e/docker" -ef "$0" ]; then
  if [ "${{1:-}}" = run ]; then shift; exec "$e/docker" run -e LEC_CHECK=0 -e OT_CTS_MACRO_CLUSTER "$@"; fi
  exec "$e/docker" "$@"; fi; done; exit 127
EOS
chmod +x $R/bin/docker; export PATH=$R/bin:$PATH
# GATE STEP CAP (ROOT 2026-10-15): a CTS / trial-GRT step that has not finished in {STEP_CAP} s is a stall (a 15 h
# dsfd_vm_write_dispatch_b24 gate sat in the DPL negotiation legalizer at 150k illegal cells after repair_design tripled
# the instance count); kill the named container and report GATE_STALL instead of holding a fleet slot for days
ot_capped() {{  # ot_capped NAME docker run --name NAME ...
  local n=$1 t0=$(date +%s) rc; shift
  timeout -k 60 {STEP_CAP} "$@"; rc=$?
  if [ $(( $(date +%s) - t0 )) -ge {STEP_CAP} ]; then docker kill "$n" >/dev/null 2>&1; echo "GATE_STALL $n exceeded {STEP_CAP} s"; fi
  return $rc
}}
docker image inspect --format 'GATE_TOOL_IMAGE_ID={{{{.Id}}}} GATE_TOOL_IMAGE_DIGESTS={{{{json .RepoDigests}}}}' {IMG} 2>/dev/null
printf 'GATE_TOOL_CTS_MACRO_CLUSTER=%s\n' "${{OT_CTS_MACRO_CLUSTER:-}}"
cd $R/src && echo {COMMIT} > SOURCE_COMMIT
T0=$(date +%s)
# the gate builds the tree at the ROUTE's corner (ref_tile.py ROUTE_PREFIX: setup at TT, owner option B): a cluster spine
# balanced at SS against the children's TT insertion targets measured a mixed-corner spread (dsfd_sp_pq_c, dscoll_ces0_sp)
export OT_ORFS_CORNER_OVERRIDE=TC
# pin groups exactly as the job's route command sets them (ref_tile.gen_job; the kit.env's own export wins in both)
SRC=$R/src SYNTH_TIMEOUT={CAP} OT_PIN_GROUP_MAX={PGM} bash tools/ref_tile/ref_route.sh {KIT}/kit.env gate $R/routes floorplan; FRC=$?
echo "GATE_FLOW_RC=$FRC GATE_FLOW_S=$(( $(date +%s) - T0 ))"
C=$R/routes/gate/work/orfs; B=$(ls -d $C/results/asap7/*/base 2>/dev/null | head -1)
grep -hE "^\[ERROR|Error:|ERROR \[|timed out|TimeoutExpired|exceeded" $R/routes/gate/flow.log $C/*.log 2>/dev/null | head -8 | sed 's/^/GATE_FLOWERR /'
[ $FRC -eq 0 ] || exit 0
NB=${{B#$C/}}
docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow {IMG} bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/$NB/3_2_place_iop.odb" > $R/iop.log 2>&1; echo "GATE_IOP_RC=$?"
grep -hE "\[ERROR" $R/iop.log | head -4 | sed 's/^/GATE_FLOWERR /'
printf 'read_db /work/%s/3_2_place_iop.odb\nsource /src/tools/fp_margin_lint.tcl\not_fp_lint_dump /work/gate_dump.json\nexit\n' $NB > $C/gate_dump.tcl
docker run --rm -v $R/src:/src:ro -v $C:/work {IMG} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_dump.tcl > $R/dump.log 2>&1; DUMPRC=$?; echo "GATE_DUMP_RC=$DUMPRC"
[ "$DUMPRC" -eq 0 ] || exit 0
# Validate the actual placed-IO dump before CTS or any PASS evidence is accepted.
python3 tools/fp_margin_lint.py pins $C/gate_dump.json --out $R/pin_geometry.json > $R/pin_geometry.log 2>&1; PINRC=$?
sed 's/^/GATE_FP /' $R/pin_geometry.log
echo "GATE_PIN_GEOMETRY_RC=$PINRC"
[ -s $R/pin_geometry.json ] && python3 -c 'import json,sys;print("GATE_PIN_GEOMETRY_RESULT "+json.dumps(json.load(open(sys.argv[1])),separators=(",",":")))' $R/pin_geometry.json
[ "$PINRC" -eq 0 ] || exit 0
# LAYOUT IMAGES (owner rule 20:45 10-15): the floorplan the route starts from (macros, pins, PG) -> PNG on the gate side
ot_layout() {{  # ot_layout ODB TAG: tools/ref_tile/layout_dump.tcl on the odb, json back as one zlib+base64 line
  printf 'read_db /work/%s\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' "$1" > $C/gate_layout_$2.tcl
  docker run --rm -e OT_LAYOUT_OUT=/work/gate_layout_$2.json -e OT_LAYOUT_CLOCKS={CLKS} -e OT_LAYOUT_TOP={TOP} -v $R/src:/src:ro -v $C:/work {IMG} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_layout_$2.tcl > $R/layout_$2.log 2>&1
  [ -s $C/gate_layout_$2.json ] && python3 -c "import zlib,base64,sys;print('GATE_LAYOUT_B64 '+sys.argv[2]+' '+base64.b64encode(zlib.compress(open(sys.argv[1],'rb').read(),9)).decode())" $C/gate_layout_$2.json $2
}}
ot_layout $NB/3_2_place_iop.odb floorplan
python3 tools/textbook_lint.py check --netlist $B/1_2_yosys.v --dump $C/gate_dump.json --out $R/textbook.json --mode refuse --refuse-checks {RC} {BRP} | sed 's/^/GATE_TB /'
python3 - $B/1_2_yosys.v {TOP} <<'EOP'
import re,sys,json
t=open(sys.argv[1]).read(); m=re.search(r"module\s+\\?"+re.escape(sys.argv[2])+r"\s*\((.*?)\);(.*?)endmodule",t,re.S)
ports={{}}; ranges={{}}
if m:
  for d in re.finditer(r"\b(input|output|inout)\b\s*(?:signed\s*)?(\[[^\]]*\])?\s*([^;]+);",m.group(2)):
    for n in d.group(3).split(","): ports[n.strip().lstrip("\\")]=[1 if not d.group(2) else None, bool(d.group(2))]
    if d.group(2):
      bounds=re.fullmatch(r"\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]",d.group(2))
      if bounds:
        a,b=map(int,bounds.groups())
        for n in d.group(3).split(","): ranges[n.strip().lstrip("\\")]=[min(a,b),max(a,b)]
print("GATE_PORTS "+json.dumps(ports))
print("GATE_PORT_RANGES "+json.dumps(ranges))
EOP
grep -h "Chip area\|chip area" $C/reports/asap7/*/base/synth_stat.txt 2>/dev/null | tail -1 | sed 's/^/GATE_AREA /'
# MEMORY-FF LINT (ROOT 2026-10-17, S-ELEM static14 TT -57.9): yosys PROC_ROM / MEMORY_BMUX2ROM turn a case table into a
# $mem ROM and MEMORY_DFF then folds the neighbouring register into its read port; the register vanishes from the netlist
grep -h "merging output FF to cell\|merged .*FF to cell\|merging .*FF to cell\|^Converted [0-9]* switch" $C/logs/asap7/*/base/1_*yosys*.log 2>/dev/null | head -60 | sed 's/^/GATE_MEMFF /'
# KEEP-MODULE AUDIT (ROOT-KEEP 10-18, HBM lgtap 6a79110b8): every kit keep entry must survive synthesis as hierarchy; a
# $paramod-renamed module is missed by SYNTH_KEEP_MODULES (yosys only warns) and its replicated copies get merged back
grep -h "did not match any module" $C/logs/asap7/*/base/1_*yosys*.log 2>/dev/null | sort -u | head -40 | sed 's/^/GATE_KEEPWARN /'
python3 tools/ref_tile/keep_module_audit.py netlist $B/1_2_yosys.v {TOP}
# PORT-LATENCY (ROOT 2215): the elaborated pin-register table + wrapper of this synthesis (ot_pin_regs.tcl) come back for
# tools/ref_tile/port_latency.py; the closure loop records the same export from the route at CLOSE for the compilers
[ -s $B/ot_pin_regs.tsv ] && [ -s $B/ot_pin_regs_wrapper.v ] && python3 -c "import zlib,base64,sys;print('GATE_PIN_REGS_B64 '+' '.join(base64.b64encode(zlib.compress(open(f,'rb').read(),9)).decode() for f in sys.argv[1:]))" $B/ot_pin_regs.tsv $B/ot_pin_regs_wrapper.v
if [ "{CTS}" = 1 ]; then
  ot_capped gate_cts_${{R##*/}} docker run --rm --name gate_cts_${{R##*/}} -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow {IMG} bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts" > $R/cts.log 2>&1; echo "GATE_CTS_RC=$?"
  grep -h "\[ERROR" $R/cts.log | head -3 | sed 's/^/GATE_CTSERR /'
  grep -h "^OT_SPINE iter\|^REF_TILE spine" $R/cts.log | tail -2 | sed 's/^/GATE_SPINE /'
  grep -h "OT_SPINE done port" $R/cts.log $C/logs/asap7/*/base/4_1_cts.log 2>/dev/null | head -1 | sed 's/^/GATE_SPINE_DONE /'
  grep -h "^global_placement -density\|Placement target density" $R/cts.log | head -2 | sed 's/^/GATE_GPLD /'
  python3 tools/closure_loop/ck_insertion.py --base $B --all-clocks --raw-source --output $R/ck.json > $R/ck.log 2>&1; echo "GATE_CK_RC=$?"
  python3 -c "import json;d=json.load(open('$R/ck.json'));print('GATE_CK '+'; '.join(c+' insertion all '+str(d[c]['all']['min'])+'..'+str(d[c]['all']['max'])+' ps (spread '+str(round(d[c]['all']['max']-d[c]['all']['min'],1))+'), boundary mean '+str(d[c]['boundary']['mean']) for c in ('ss','tt','ff') if isinstance(d.get(c),dict) and d[c].get('all'))+'; macro_clk flag '+str((d.get('macro_clk') or {{}}).get('flag')))" 2>/dev/null
  python3 -c "import json;d=json.load(open('$R/ck.json'));[print('GATE_CK_DOMAIN '+json.dumps({{'source':pin,'clock':r.get('clock'),'tt':r.get('tt'),'ff':{{k:(r.get('ff') or {{}}).get(k) for k in ('boundary','all','child_flop','macros')}}}})) for pin,r in d.get('clock_measurements',{{}}).items()]" 2>/dev/null
  docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/{KIT}/signoff.sdc -v $R/src:/src:ro -v $C:/work {IMG} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/ref_tile/path_classes.tcl > $R/pc.log 2>&1
  grep -E "^GATE_(PC|XCLK)" $R/pc.log
  ot_layout $NB/4_1_cts.odb placed
fi
# TRIAL ROUTE (owner rule 20:45 10-15; every kit since ROOT-0330-GRT 10-18, was parent / cluster kits only): place +
# global-route here (no detailed route): overflow, per-layer usage and the congestion hotspots come back; overflow > 0
# refuses the kit.  Single tiles (HBM qcore r5, S81 bk g2, KV landh0_548, Qwen h16b) passed the gate and failed GRT hours
# into the route; the trial costs minutes.  ROOT-0630 (coordinator HANDOFF 0gi, 10-18): a SINGLE-tile kit's trial is a
# congestion screen and runs SKIP_INCREMENTAL_REPAIR=1 (first GRT only, no post-GRT repair_design / repair_timing /
# incremental re-route: ~2 min instead of ~25); parent / cluster kits keep the full trial.
if [ "{TRIAL}" = 1 ]; then
  GT0=$(date +%s)
  ot_capped gate_grt_${{R##*/}} docker run --rm --name gate_grt_${{R##*/}} -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow {IMG} bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base GLOBAL_ROUTE_ARGS='-allow_congestion -verbose' GENERATE_ARTIFACTS_ON_FAILURE=1 {GRTX}grt" > $R/grt.log 2>&1; echo "GATE_GRT_RC=$? GATE_GRT_S=$(( $(date +%s) - GT0 ))"
  GL=$(ls $C/logs/asap7/*/base/5_1_grt.log 2>/dev/null | head -1)
  [ -n "$GL" ] && grep -E "^(M[0-9]+|Total) +[0-9]+ +[0-9]+ +[0-9.]+%" $GL | tail -12 | sed 's/^/GATE_GRT_LAYER /'
  [ -n "$GL" ] && grep -hE "GRT-0116|Total overflow|overflow" $GL | tail -3 | sed 's/^/GATE_GRT_NOTE /'
  CR=$(ls $C/reports/asap7/*/base/congestion.rpt 2>/dev/null | head -1)
  [ -n "$CR" ] && python3 -c "import zlib,base64,sys;print('GATE_CONG_B64 '+base64.b64encode(zlib.compress(open(sys.argv[1],'rb').read()[:20000000],9)).decode())" $CR
  ot_layout $NB/5_1_grt.odb placed
fi
"""


def ship_tar(paths, overlay_payloads=None, overlay_modes=None):
    import io
    import tarfile
    if overlay_payloads is None:
        plan, overlay_payloads = HO.capture_plan(DAEMON_TREE, ROOT, paths=[h for h in SHIP_HELPERS if (DAEMON_TREE / h).exists()])
        overlay_modes = {f["path"]: f["mode"] for f in plan["files"]}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for p in sorted(set(paths)):
            if any(p != q and p.startswith(q.rstrip("/") + "/") for q in paths):
                continue
            src = ROOT / p
            if src.exists():
                tf.add(str(src), arcname=p, filter=lambda ti: None if ("/views/" in ti.name and ti.name.endswith(".gds"))
                       or "__pycache__" in ti.name or "source_binding_history" in Path(ti.name).parts
                       or "gate_layout" in Path(ti.name).parts
                       or Path(ti.name).name in SB.EXCLUDED else ti)
        for h in SHIP_HELPERS:      # the loop's shipped flow helpers win over the snapshot's copies
            f = DAEMON_TREE / h
            if f.exists():
                payload = overlay_payloads[h]
                ti = tarfile.TarInfo(h)
                ti.size = len(payload)
                ti.mode = overlay_modes[h] if overlay_modes is not None else f.stat().st_mode & 0o777
                tf.addfile(ti, io.BytesIO(payload))
    return buf.getvalue()


def gate_consumed(data: bytes, kd: Path, spec: dict, referenced, entries) -> dict:
    """The staged files this gate consumes (SB.consumed_closure over the archive bytes): the kit directory (spec.json,
    kit.env, SDCs, hooks, pin files), the spec's RTL file list and its `include closure, the floorplan's referenced
    closure, child/macro view directories, the job's source.extra_paths, the tools REMOTE_SH runs and the daemon
    overlays.  The route binding compares only these; any other staged-file difference is reported, not refused."""
    kit = str(kd.relative_to(ROOT))
    try:
        job = json.loads((kd / "job.json").read_text())
    except (OSError, ValueError):
        job = {}
    extra = [str(x) for x in ((job.get("source") or {}).get("extra_paths") or [])]
    views = [it["view"] for it in list(spec.get("macros") or []) + list(spec.get("children") or []) if it.get("view")]
    seeds = list(spec.get("sources") or []) + sorted(referenced) + list(SB.GATE_TOOLS) + list(SHIP_HELPERS)
    paths = SB.consumed_closure(SB.archive_contents(data), seeds, [kit, *views, *extra], PATH_RE)
    # the kit's job.json is the route's job spec, not a gate input (no remote step reads it; submit_check re-checks the
    # submitted job itself): its tag/purpose edits never invalidate a gate
    return SB.consumed_record(paths - {f"{kit}/job.json"}, entries, "staged archive closure at gate time")


class _BlobFiles(dict):
    """{path: bytes} view of a staged manifest whose payloads are read lazily from the git object store by blob id."""
    def __init__(self, entries):
        super().__init__()
        self.blobs = {e["path"]: e["git_blob"] for e in entries if e.get("kind") == "file"}
        self.proc = None

    def __contains__(self, k):
        return k in self.blobs

    def __iter__(self):
        return iter(self.blobs)

    def __getitem__(self, k):
        if not dict.__contains__(self, k):
            if self.proc is None:
                self.proc = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "--batch"],
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            self.proc.stdin.write((self.blobs[k] + "\n").encode())
            self.proc.stdin.flush()
            head = self.proc.stdout.readline().split()
            if len(head) != 3 or head[1] != b"blob":
                raise KeyError(f"staged blob {self.blobs[k]} of {k} not in the object store")
            data = self.proc.stdout.read(int(head[2]))
            self.proc.stdout.read(1)
            dict.__setitem__(self, k, data)
        return dict.__getitem__(self, k)

    def close(self):
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.wait()


def reconstruct_consumed(binding: dict, kd: Path) -> dict | None:
    """The consumed-file record of a gate that predates it (snapshot v1 without "consumed"), derived by the same closure
    from the gate's own staged bytes (manifest git blobs, read back from the object store) -- never from today's tree.
    None when any needed staged blob is unavailable: the gate is then validated exactly as before (full snapshot)."""
    # kd may be the submit hook's materialised copy (a temp dir): the kit path is the staged spec.json path it ends with
    kits = sorted({e["path"][:-len("/spec.json")] for e in binding.get("files") or []
                   if e["path"].endswith(f"/{kd.name}/spec.json") and kd.as_posix().endswith(e["path"][:-len("/spec.json")])},
                  key=len, reverse=True)
    if not kits:
        return None
    kit = kits[0]
    files = _BlobFiles(binding.get("files") or [])
    try:
        spec = json.loads(files[f"{kit}/spec.json"])
        fp = json.loads(files[f"{kit}/floorplan.json"]) if f"{kit}/floorplan.json" in files else {}
        job = json.loads(files[f"{kit}/job.json"]) if f"{kit}/job.json" in files else {}
        extra = [str(x) for x in ((job.get("source") or {}).get("extra_paths") or [])]
        views = [it["view"] for it in list(spec.get("macros") or []) + list(spec.get("children") or []) if it.get("view")]
        seeds = list(spec.get("sources") or []) + list(fp.get("referenced") or []) + list(SB.GATE_TOOLS) + \
            list(binding.get("daemon_overlays") or [])
        paths = SB.consumed_closure(files, seeds, [kit, *views, *extra], PATH_RE) - {f"{kit}/job.json"}
    except (KeyError, ValueError, TypeError, OSError):
        return None
    finally:
        files.close()
    return SB.consumed_record(paths, binding["files"], "reconstructed from the gate's staged manifest blobs")


def absent_working_inputs(seeds):
    # The archive is made from the working tree, not git show.  A sparse checkout
    # can contain the hook but omit a committed helper that the hook sources.
    # Check those transitive inputs before choosing a host or shipping a run.
    seen, _, soft = referenced_closure(sorted(seeds), SB.git_head(ROOT))
    overlaid = {p for p in SHIP_HELPERS if (DAEMON_TREE / p).is_file()}
    return sorted(p for p in seen - soft - overlaid if not (ROOT / p).is_file())


def gate_route_clock_hooks(script: str, spec: dict) -> str:
    """Run the same supported physical clock hooks as a multi-root route job."""
    if spec.get("clock") != "multiple_cts_roots":
        return script
    marker = "export OT_ORFS_CORNER_OVERRIDE=TC\n"
    if script.count(marker) != 1:
        raise ValueError("remote gate clock-hook insertion marker changed")
    return script.replace(marker, marker + "export OT_CTS_FIX_HOOKS=" + shlex.quote(RT.clock_fix_hooks(spec)) + "\n", 1)


def gate_route_hold_context(script: str, spec: dict, kd: str) -> str:
    """Use production hold settings, never the ref_route.sh 10ps fallback.

    This is not OT_CAL_CTS_ONLY insertion measurement. The formal gate builds
    placement/CTS with the route's actual MM scenes, margin and physical hooks.
    """
    marker = "export OT_ORFS_CORNER_OVERRIDE=TC\n"
    if script.count(marker) != 1:
        raise ValueError("remote gate runtime-context insertion marker changed")
    values = RT.route_hold_context(spec, kd)
    if spec.get("clock") != "multiple_cts_roots":
        values["OT_CTS_FIX_HOOKS"] = RT.clock_fix_hooks(spec)
    text = "".join("export " + k + "=" + shlex.quote(v) + "\n" for k, v in values.items())
    return script.replace(marker, marker + text, 1)


def gate_disk_budget(spec: dict, data: bytes, override=None) -> dict:
    """GiB required before shipping and before unpacking; ot-run accepts integer GiB.

    Keep the ordinary 20 GiB work/output reserve. Add the actual compressed
    snapshot and an upper estimate of its unpacked 4 KiB allocation before
    choosing a host. A further GiB covers metadata and integer df rounding.
    This is an admission check, not a disk reservation against other jobs.
    """
    import io
    import tarfile
    value = override if override is not None else spec.get("gate_disk_gb", 20)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        raise RT.SpecError("gate_disk_gb / --disk must be a positive finite number of GiB")
    reserve = math.ceil(value)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        unpacked = sum(((m.size + 4095) // 4096) * 4096 + 4096 for m in tf)
    gib = 1024 ** 3
    return {"reserve_gb": reserve, "archive_bytes": len(data), "unpacked_bytes": unpacked,
            "pick_gb": reserve + math.ceil((len(data) + unpacked) / gib) + 1,
            "runtime_gb": reserve + math.ceil(unpacked / gib) + 1}


def remote(g: Gate, kd: Path, spec: dict, host: str, cap: int, mem: int, cts: bool, disk=None):
    fp = json.loads((kd / "floorplan.json").read_text())
    absent = absent_working_inputs(set(fp["referenced"]))
    if absent:
        g.add("FAIL", "sources", f"{len(absent)} committed input(s) absent from the working-tree archive: {absent[:8]}",
              "materialize the referenced files in the sparse checkout before rerunning the gate")
        return
    ref = set(fp["referenced"])
    # Ship the same transitive Tcl/shell dependencies checked by the local gate.
    # A custom PRE_GLOBAL_PLACE hook may source helpers outside its own folder.
    ref |= referenced_closure(sorted(ref))[0]
    dirs = {"tools", "rtl", str(kd.relative_to(ROOT)), "physical/qwen_die_masters", "physical/common_flow",
            "physical/hbm_accel_die_views/stations/bench", "physical/hbm_w2_rb_station_20261006"}
    dirs |= {str(Path(p).parent) for p in ref}
    ts = time.strftime("%Y%m%d-%H%M%S")
    R = f"/srv/opentallas-scratch/claude/ref_gate/{spec['name']}-{ts}"
    start_commit = SB.git_head(ROOT)
    daemon_commit = SB.git_head(DAEMON_TREE)
    route_plan, overlay_payloads = HO.capture_plan(DAEMON_TREE, ROOT)
    data = ship_tar(dirs, overlay_payloads, {f["path"]: f["mode"] for f in route_plan["files"]})
    budget = gate_disk_budget(spec, data, disk)
    auto = host == "auto"
    threads = int(spec.get("route", {}).get("threads", 8))
    # Probe the actual scratch filesystem, not / (the two can be different).
    # This parent already exists before the per-run directory is uploaded.
    pick_cmd = ["ot-run", "--mem", str(mem), "--threads", str(threads), "--disk", str(budget["pick_gb"]),
                "--dir", "/srv/opentallas-scratch", "--pick"]
    if not auto:
        pick_cmd += ["--hosts", host]
    admission_wait = False
    while True:
        picked = subprocess.run(pick_cmd, capture_output=True, text=True)
        if picked.returncode != 75:
            break
        # The read-only picker cannot start or reserve anything. A CPU load
        # hold is capacity waiting, not a hardware/source gate failure; retain
        # this exact archive and retry before uploading to any chosen host.
        if not admission_wait:
            g.add("INFO", "admission_wait", "fleet load hold; preserving the exact source archive and waiting for an eligible host")
        admission_wait = True
        time.sleep(60)
    if picked.returncode or not picked.stdout.strip():
        g.add("FAIL", "remote", "fleet admission could not choose a host: " + picked.stderr[-500:], "read ot-run --status")
        return
    host = picked.stdout.strip()
    g.add("INFO", "remote", f"ot-run selected {host} for {mem} GB memory; disk pick {budget['pick_gb']} GiB, "
          f"runtime {budget['runtime_gb']} GiB includes {budget['reserve_gb']} GiB work reserve plus snapshot staging")
    binding = SB.snapshot(data, ROOT, start_commit, DAEMON_TREE, daemon_commit, SHIP_HELPERS)
    binding["disk_admission"] = budget
    binding["route_overlay_plan"] = route_plan
    binding["consumed"] = gate_consumed(data, kd, spec, ref, binding["files"])
    binding["captured"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    g.source_binding = binding
    commit = binding["commit"] or "snapshot-sha256:" + binding["manifest_sha256"]
    sh = REMOTE_SH.format(R=R, COMMIT=commit, CAP=(cap if cap > 0 else "unlimited"), KIT=kd.relative_to(ROOT), IMG="openroad/orfs:latest",
                          RC=",".join(GATE_REFUSE), BRP=("--balanced-reset-profile $R/src/{}/reset_landing.json".format(kd.relative_to(ROOT)) if (spec.get('reset_landing') or {}).get('first_copies') else ""), TOP=spec["top"], CTS=1 if cts else 0, PGM=PF.ROUTE_PIN_GROUP_MAX,
                          TRIAL=1, GRTX=trial_grt_make_args(spec), CLKS=",".join(RT.declared_clock_ports(spec)),
                          CLK=spec["clock_port"], ARCHIVE_SHA256=binding["archive_sha256"], STEP_CAP=GATE_STEP_CAP_S)   # ck_insertion (9f48f5ed8): --clock = clock name or its source port; the default 'ck' failed every kit whose port is 'clk'
    tbx = textbook_reset_args(spec) + reset_landing_args(spec)
    if tbx:
        tb = f"--refuse-checks {','.join(GATE_REFUSE)} | sed 's/^/GATE_TB /'"
        sh = sh.replace(tb, tb.replace(" | sed", tbx + " | sed", 1), 1)
    sh = gate_route_clock_hooks(sh, spec)
    sh = gate_route_hold_context(sh, spec, str(kd.relative_to(ROOT)))
    binding["route_hold_context"] = RT.route_hold_context(spec, str(kd.relative_to(ROOT)))
    import hashlib
    binding["remote_script_sha256"] = hashlib.sha256(sh.encode()).hexdigest()
    binding["tool_image_requested"] = "openroad/orfs:latest"
    binding["remote_host"] = host
    binding["remote_run"] = R
    local_snapshot = Path(os.environ.get("TMPDIR", "/tmp")) / f"ref_gate_{spec['name']}_{ts}.source_snapshot.json"
    local_snapshot.write_text(json.dumps(binding, indent=1) + "\n")
    g.add("INFO", "source_binding", f"immutable shipping manifest {local_snapshot}")
    script = f"/tmp/ref_gate_{spec['name']}_{ts}.sh"
    t0 = time.time()

    def ship(h):
        binding["remote_host"] = h
        local_snapshot.write_text(json.dumps(binding, indent=1) + "\n")
        up = subprocess.run(["ssh", h, f"cat > {script}"], input=sh.encode(), capture_output=True)
        if not up.returncode:
            up = subprocess.run(["ssh", h, f"mkdir -p {Path(R).parent} && cat > {R}.tgz"], input=data, capture_output=True)
        if not up.returncode:
            up = subprocess.run(["ssh", h, f"cat > {R}.source_snapshot.json"],
                                input=(json.dumps(binding, indent=1) + "\n").encode(), capture_output=True)
        return up
    up = ship(host)
    if up.returncode:
        g.add("FAIL", "remote", f"cannot ship to {host}: {up.stderr[-200:]!r}", "pick another host")
        return
    # Exactly one ot-heavy reservation, inside ot-run; never nest guards.
    # Recheck after upload, reserving enough for extraction as well as outputs.
    # AFTER-UPLOAD RACE (ROOT 2026-10-15): the archive sits on the picked host only, so a host that filled up (or went
    # load-held) between pick and launch kept the gate waiting there while other hosts were free.  Each launch now waits
    # at most RELAUNCH_WAIT_S; on NOT RUN (75) the read-only pick runs again and, when it names another host, the SAME
    # bytes (archive, script, binding) are shipped there and the stale upload is removed.  Same host: wait again.
    while True:
        p = subprocess.run(["ot-run", "--mem", str(mem), "--threads", str(threads), "--disk", str(budget["runtime_gb"]),
                            "--hosts", host, "--max-wait", str(RELAUNCH_WAIT_S), "--dir", str(Path(R).parent), "--",
                            "bash", script], stdin=subprocess.DEVNULL, capture_output=True)
        if p.returncode != 75 or b"NOT RUN" not in p.stderr:
            break
        again = subprocess.run(pick_cmd, capture_output=True, text=True)
        nxt = again.stdout.strip() if again.returncode == 0 else ""
        if not nxt or nxt == host:
            continue
        if ship(nxt).returncode:
            continue
        subprocess.run(["ssh", host, f"rm -f {script} {R}.tgz {R}.source_snapshot.json"], capture_output=True)
        g.add("INFO", "remote", f"{host} did not admit the gate within {RELAUNCH_WAIT_S} s; same archive re-shipped to {nxt}")
        host = nxt
    out = p.stdout.decode(errors="replace")
    logp = Path(os.environ.get("TMPDIR", "/tmp")) / f"ref_gate_{spec['name']}_{ts}.log"   # never into the kit (dirty tree)
    logp.write_text(out + "\n--- stderr\n" + p.stderr.decode(errors="replace")[-4000:])
    g.remote_host = host
    g.add("INFO", "remote", f"remote log {logp}; host dir {host}:{R}")
    # A dropped SSH session can leave the admitted container running. Its
    # partial stdout must never become a terminal CTS/clock qualification.
    # Preserve the source snapshot and handle; collect this original job.
    terminal = re.search(r"^GATE_SCRIPT_RC=(\d+)$", out, re.M)
    completed = (terminal is not None and int(terminal[1]) == p.returncode
                 and re.search(r"^GATE_DONE$", out, re.M)
                 and b"NOT COMPLETED" not in p.stderr)
    if not completed:
        g.add("FAIL", "remote_incomplete",
              f"remote gate has no verified terminal completion (ot-run exit {p.returncode}); "
              f"original job may still run at {host}:{R}; script {script}; log {logp}",
              "inspect the original live handle and collect its terminal output; do not submit a duplicate")
        g.clock = {"cts": bool(cts), "verdict": "REFUSE", "status": "REMOTE_INCOMPLETE",
                   "text": "transport or script ended without verified GATE_DONE; no clock qualification"}
        return
    analyse_remote(g, kd, spec, out, cts, binding, cap, host, round(time.time() - t0), local_snapshot)
    if p.returncode:
        g.add("FAIL", "remote_script", f"remote script completed with exit {p.returncode}",
              "read the original terminal log and fix the reported failure")
    gate_layout(g, kd, spec, out)


FILL_WARN, FILL_FAIL = 0.50, 0.35       # OWNER RULE 20:45 PT 10-15 (parent / cluster kits)


def is_parent_kit(spec: dict) -> bool:
    """a parent / cluster kit: kind cluster, hardened children, or >= 4 hard macros"""
    return spec.get("kind") == "cluster" or bool(spec.get("children")) or len(spec.get("macros") or []) >= 4


def trial_grt_make_args(spec: dict) -> str:
    """extra ORFS make variables of the gate's trial GRT (ROOT-0630, HANDOFF 0gi): a single tile skips the post-GRT
    incremental repair (a congestion screen; overflow > 0 still FAILs); a parent / cluster kit runs the full trial"""
    return "" if is_parent_kit(spec) else "SKIP_INCREMENTAL_REPAIR=1 "


def pin_demand(d: dict) -> list:
    """per face: pins, occupied span of the face (first..last pin), edge length -- pin-bound evidence"""
    X0, Y0, X1, Y1 = d["die"]
    faces = {"S": [], "N": [], "W": [], "E": []}
    for name, layer, a, b, c, e in d.get("pins", []):
        cx, cy = (a + c) / 2, (b + e) / 2
        dist = {"S": cy - Y0, "N": Y1 - cy, "W": cx - X0, "E": X1 - cx}
        f = min(dist, key=dist.get)
        faces[f].append(cx if f in "SN" else cy)
    out = []
    for f, v in faces.items():
        edge = (X1 - X0) if f in "SN" else (Y1 - Y0)
        span = (max(v) - min(v)) if len(v) > 1 else 0.0
        out.append({"face": f, "pins": len(v), "span_um": round(span, 1), "edge_um": round(edge, 1),
                    "occupancy": round(span / edge, 3) if edge else 0.0})
    return out


def gate_layout(g: Gate, kd: Path, spec: dict, out: str):
    """LAYOUT IMAGES + FILL + TRIAL ROUTE (OWNER RULE 20:45 PT 2026-10-15): render the gate's layout dumps to PNG in
    <kit>/gate_layout/ (floorplan, post-place density, GRT congestion), judge fill of parent / cluster kits and the
    trial global route's overflow.  Element owners LOOK at the PNGs (AGENT_PREAMBLE 'LOOK AT THE LAYOUT')."""
    import base64
    import zlib
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import layout_png as LP
    dumps = {}
    for tag, b64 in re.findall(r"^GATE_LAYOUT_B64 (\S+) (\S+)$", out, re.M):
        try:
            dumps[tag] = json.loads(zlib.decompress(base64.b64decode(b64)))
        except Exception as ex:  # noqa: BLE001
            g.add("WARN", "layout_images", f"layout dump {tag} unreadable: {type(ex).__name__}")
    od = kd / "gate_layout"
    imgs = {}
    title = spec.get("name", kd.name)
    if "floorplan" in dumps:
        imgs["floorplan"], _ = LP.render_floorplan(dumps["floorplan"], od / "floorplan.png", f"{title} floorplan (gate)")
    pl = dumps.get("placed")
    if pl:
        imgs["density"] = LP.render_grid(pl, "density", od / "density.png", f"{title} post-place density (gate)",
                                         "std-cell area / bin area: blue 0, green 0.5, red 1.0+ ; grey = macros")
    m = re.search(r"^GATE_CONG_B64 (\S+)$", out, re.M)
    rpt = None
    if m:
        try:
            rpt = zlib.decompress(base64.b64decode(m.group(1))).decode(errors="replace")
        except Exception as ex:  # noqa: BLE001
            g.add("WARN", "layout_images", f"congestion report unreadable: {type(ex).__name__}")
    if rpt is not None and pl:
        try:
            pl = dict(pl, congestion=LP.congestion_grid(pl, rpt))
            imgs["congestion"] = LP.render_grid(pl, "congestion", od / "congestion.png", f"{title} GRT congestion (gate trial)",
                                                f"{pl['congestion']['markers']} congested gcells (red = most)")
        except Exception as ex:  # noqa: BLE001
            g.add("WARN", "layout_images", f"congestion report unreadable: {type(ex).__name__}")
    if imgs:
        g.add("INFO", "layout_images", "LOOK at these before submitting: " + "; ".join(f"{k} {p}" for k, p in imgs.items() if p))
        g.layout_images = {k: p for k, p in imgs.items() if p}
    elif dumps == {} and "GATE_DONE" in out:
        g.add("WARN", "layout_images", "the gate produced no layout dump (layout_dump.tcl); see the remote layout_*.log")
    parent = is_parent_kit(spec)
    fpd = dumps.get("floorplan")
    if parent and fpd:
        st = fpd.get("stats", {})
        fill = float(st.get("fill") or 0.0)
        pd = pin_demand(fpd)
        dem = ", ".join(f"{x['face']} {x['pins']} pins over {x['span_um']}/{x['edge_um']} um ({x['occupancy']:.0%})" for x in pd)
        reason = str((spec.get("fill_reason") or {}).get("pin_bound", "")).strip()
        msg = (f"fill {fill:.0%} = (hard macros {st.get('block_area')} + synthesized std cells {st.get('std_area')}) / "
               f"outline {st.get('die_area')} um2; pin demand per face: {dem}")
        if fill < FILL_FAIL and not reason:
            g.add("FAIL", "fill", msg + f" (< {FILL_FAIL:.0%})", "shrink the outline / regroup the macros, or record "
                  "\"fill_reason\": {\"pin_bound\": \"<why the perimeter, not the area, sets the outline>\"} if the pin "
                  "demand above shows the edges are full")
        elif fill < FILL_WARN:
            g.add("WARN", "fill", msg + (f" (pin-bound: {reason})" if reason else f" (< {FILL_WARN:.0%})"))
        else:
            g.add("INFO", "fill", msg)
    if "GATE_GRT_RC=" in out:
        # TRIAL ROUTE for EVERY kit (ROOT-0330-GRT 10-18; parent / cluster kits since 10-15): overflow > 0 FAILs with the
        # hotspot (worst gcell / layer / bbox from the congestion report) and the congestion PNG
        rows = re.findall(r"^GATE_GRT_LAYER (\S+) +(\d+) +(\d+) +([\d.]+)%\s+(\d+) */ *(\d+) */ *(\d+)", out, re.M)
        tot = [r for r in rows if r[0] == "Total"]
        # 5_1_grt.log prints the table after the first route AND after the incremental re-route: judge the LAST one
        ends = [i for i, r in enumerate(rows) if r[0] == "Total"]
        lay = [r for r in rows[(ends[-2] + 1 if len(ends) > 1 else 0):(ends[-1] if ends else len(rows))] if r[0] != "Total"]
        worst = max(lay, key=lambda r: float(r[3]), default=None)
        ovf = int(tot[-1][6]) if tot else None
        hot = LP.congestion_hotspots(rpt) if rpt is not None else None
        wovf = max(lay, key=lambda r: int(r[6]), default=None)
        if hot and hot.get("markers") and wovf is not None and int(wovf[6]) > 0:
            # the congestion report is 2D ("on Layer -"): the layer comes from the per-layer overflow table
            hot["worst_overflow_layer"] = [wovf[0], int(wovf[6])]
        secs = re.search(r"GATE_GRT_S=(\d+)", out)
        g.trial_route = dict(schema="opentallas.ref_tile.trial_route.v1", overflow=ovf, kind="parent" if parent else "tile",
                             skip_incremental_repair=not parent,
                             rc=re.search(r"GATE_GRT_RC=(\S+)", out).group(1), grt_s=int(secs.group(1)) if secs else None,
                             layers=[dict(layer=r[0], capacity=int(r[1]), usage=int(r[2]), pct=float(r[3]),
                                          overflow=int(r[6])) for r in lay],
                             worst_layer_usage=worst and [worst[0], float(worst[3])], hotspot=hot,
                             congestion_png=imgs.get("congestion"))
        note = (f"trial GRT: total overflow {ovf}" + (f"; worst layer {worst[0]} {worst[3]}% used" if worst else "")
                + (f"; worst-overflow layer {wovf[0]} ({wovf[6]})" if ovf and wovf is not None else "")
                + (f"; {LP.hotspot_text(hot)}" if ovf and hot is not None else
                   "; no congestion report came back" if ovf else "")
                + (f"; congestion map {imgs.get('congestion')}" if imgs.get("congestion") else "")
                + (f"; GRT {secs.group(1)} s" if secs else ""))
        if ovf is None:
            g.add("FAIL", "trial_route", "trial global route produced no congestion table (GATE_GRT_RC="
                  + re.search(r"GATE_GRT_RC=(\S+)", out).group(1) + ")", "read the remote grt.log")
        elif ovf > 0:
            g.add("FAIL", "trial_route", note, "regroup macros / widen the congested channels / move pins to their "
                  "consumers; look at congestion.png and density.png")
        else:
            g.add("INFO", "trial_route", note)


def check_actual_pin_geometry(g: Gate, out: str):
    """A missing, failed or malformed actual-dump proof can never become PASS."""
    kv = dict(re.findall(r"\b(GATE_[A-Z0-9_]+)=(\S+)", out))
    records = re.findall(r"^GATE_PIN_GEOMETRY_RESULT (.*)$", out, re.M)
    try:
        if kv.get("GATE_DUMP_RC") != "0" or len(records) != 1:
            raise ValueError("missing successful actual gate_dump / unique pin-geometry report")
        rep = json.loads(records[0])
        if not isinstance(rep, dict) or not isinstance(rep.get("metrics"), dict):
            raise ValueError("malformed actual pin-geometry report")
        if (not isinstance(rep.get("fails"), list) or
                any(not isinstance(f, dict) or not isinstance(f.get("check"), str) or
                    not isinstance(f.get("msg"), str) for f in rep["fails"])):
            raise ValueError("malformed actual pin-geometry findings")
        metrics = rep["metrics"]
        keys = ("signal_clock_pins", "pin_rectangles", "pin_track_checked", "pin_track_inaccessible",
                "pin_rectangles_outside", "missing_geometry")
        if any(type(metrics.get(k)) is not int or metrics[k] < 0 for k in keys):
            raise ValueError("invalid actual pin-geometry counters")
        if (rep.get("schema") != "opentallas.fp_pin_geometry.v1" or
                not re.fullmatch(r"[0-9a-f]{64}", rep.get("dump_sha256", "")) or
                not re.fullmatch(r"[0-9a-f]{64}", rep.get("validator_sha256", "")) or
                metrics["signal_clock_pins"] <= 0):
            raise ValueError("invalid actual pin-geometry proof")
        if rep.get("verdict") == "PASS" and not rep["fails"] and kv.get("GATE_PIN_GEOMETRY_RC") == "0":
            if metrics["pin_track_checked"] != metrics["signal_clock_pins"]:
                raise ValueError("PASS lacks actual track coverage for every signal/clock pin")
            if any(metrics[k] for k in ("pin_track_inaccessible", "pin_rectangles_outside", "missing_geometry")):
                raise ValueError("PASS contradicts actual pin-geometry metrics")
            g.add("INFO", "floorplan.pin_geometry", f"actual pin geometry PASS: {metrics}; dump SHA256 {rep['dump_sha256']}")
            return
        if rep.get("verdict") != "FAIL" or not rep["fails"] or kv.get("GATE_PIN_GEOMETRY_RC") != "3":
            raise ValueError("actual pin-geometry checker status/report disagree")
        for finding in rep["fails"]:
            g.add("FAIL", "floorplan." + finding["check"], finding["msg"],
                  "fix actual pin shapes/coordinates against the die and DEF tracks; retain the assigned native pin plan")
    except (KeyError, TypeError, ValueError) as e:
        g.add("FAIL", "floorplan.pin_geometry", str(e),
              "rerun the actual placed-IO dump and fp_margin_lint pins check; old CTS measurements alone cannot qualify geometry")


def analyse_remote(g: Gate, kd: Path, spec: dict, out: str, cts: bool, binding: dict,
                   cap: int, host: str, secs: int = 0, local_snapshot: Path | None = None):
    """One parser for live runs and fully verified frozen-run recovery."""
    fp = json.loads((kd / "floorplan.json").read_text())
    kv = dict(re.findall(r"\b(GATE_[A-Z0-9_]+)=(\S+)", out))
    errs = re.findall(r"^GATE_FLOWERR (.*)$", out, re.M)
    if binding.get("staged_remeasurement"):
        if not SB.staged_remeasurement_matches_log(binding, out.encode()):
            g.add("FAIL", "source_binding", "new staged remeasurement receipt/log mismatch", "rehash remote original source and artifacts")
            return
        binding["staged_measurement_log"] = out  # persisted exact bytes, checked again at route admission
        g.add("INFO", "source_binding", "NEW staged remeasurement: all original staged bytes, script and CTS artifacts rehashed; original archive stdout unavailable")
        # This is new measurement evidence, never historical archive verification.
        if errs or kv.get("GATE_FLOW_RC") not in (None, "0"):
            g.add("FAIL", "floorplan_run", "new measurement reports a flow failure: " + "; ".join(errs[:4]), "preserve failed evidence")
            return
        kv["GATE_FLOW_RC"] = "0"  # verified existing artifacts, no new floorplan execution
        kv["GATE_FLOW_S"] = "reused_original_floorplan"
    elif kv.get("GATE_SOURCE_ARCHIVE_SHA256") != binding["archive_sha256"]:
        g.add("FAIL", "source_binding", "remote did not verify the staged source archive", "preserve log; rerun gate")
        return
    else:
        binding["remote_archive_verified"] = True
    binding["runtime_tool_provenance"] = re.findall(r"^GATE_TOOL_.*$", out, re.M)
    if local_snapshot is not None:
        local_snapshot.write_text(json.dumps(binding, indent=1) + "\n")
    if kv.get("GATE_FLOW_RC") != "0":
        why = "; ".join(errs[:4]) or "see gate_remote.log"
        stall = any(re.search(r"tim(ed)? ?out|TimeoutExpired|exceeded", e, re.I) for e in errs) or \
            (cap > 0 and int(kv.get("GATE_FLOW_S", 0)) >= cap)
        g.add("FAIL", "synth_smoke" if stall else "floorplan_run",
              (f"ORFS synthesis did not finish within {cap} s (yosys SHARE / ABC stall class): " if stall else
               "synthesis + floorplan + PDN failed: ") + why[:600],
              "decoded constant-index slices instead of runtime part-selects; replicate instead of wide shifters"
              if stall else "read the first [ERROR] above (PDN-0217/0233/0006, PPL-0061, MPL, ...) and fix the kit/RTL")
        return
    if binding.get("staged_remeasurement"):
        g.add("INFO", "remote", f"reused verified original netlist, floorplan and CTS state on {host}; only measurement commands executed anew")
    else:
        g.add("INFO", "remote", f"synth + floorplan + PDN OK on {host} in {kv.get('GATE_FLOW_S')} s (gate total {secs} s)")
    if kv.get("GATE_IOP_RC") not in (None, "0"):
        g.add("FAIL", "io_place", "IO placement failed: " + "; ".join(errs[:3]),
              PF.FIX_TEXT if any("PPL-0093" in e for e in errs) else "fix the pin plan / pin layers")
    check_actual_pin_geometry(g, out)
    m = re.search(r"^GATE_PORTS (.*)$", out, re.M)
    if m:
        bounds = re.search(r"^GATE_PORT_RANGES (.*)$", out, re.M)
        ports = PortMap({k: tuple(v) for k, v in json.loads(m.group(1)).items()},
                        json.loads(bounds[1]) if bounds else {})
        check_pins(g, spec, ports, where="synthesized netlist")
    am = re.search(r"^GATE_AREA .*?([\d.]+)\s*$", out, re.M)
    if am:
        area = float(am.group(1))
        W, H = fp["die"][2], fp["die"][3]
        core = (W - 2 * RT.CORE_MARGIN) * (H - 2 * RT.CORE_MARGIN)
        area = synthesis_std_area(area, fp["blocks"])
        halo = float(spec["route"].get("macro_halo_um", RT.HALO_UM)) if spec.get("recipe", 1) >= 2 else RT.HALO_UM
        um = RT.util_metrics(area, fp["blocks"], core, halo)
        # high util is a closure risk (FAIL > 70%); low util only costs wire / area (closed blocks sit at 6-22%): WARN
        sev, _ok = RT.util_severity(um)
        mac = um["macro_um2"]
        g.add(sev, "util", f"synthesized std area {area:.0f} um2 + macros {mac:.0f} in core {core:.0f}: util {um['util']:.0%}"
              + (f" (std-cell density {um['density']:.1%} of placeable {um['placeable_um2']:.0f} um2; total fill "
                 f"{um['total_fill']:.1%})" if mac else ""),
              f"set \"std_area_um2\": {area:.0f} and drop 'outline' (gen sizes to util 0.52)" if sev != "INFO" else "")
    check_port_latency(g, kd, spec, out, binding.get("commit"), binding=binding)
    check_memory_ff(g, out)
    check_keep_modules(g, kd, spec, out)
    g.reset_landing = reset_landing_record(out)      # a gate without this record predates the reset_landing rule
    for line in re.findall(r"^GATE_TB (.*)$", out, re.M):
        if line.startswith("TEXTBOOK_LINT:"):
            continue
        mm = re.match(r"textbook_lint: (REFUSE|WARN\(refuse-tier\)|WARN|PASS|WAIVED) ?(\w+)?:? ?(.*)", line)
        if not mm:
            continue
        tag, chk, msg = mm.groups()
        if chk in TL.HARD_CHECKS:
            continue                    # the measured clock rule is judged below, after the CTS numbers
        if tag == "PASS" or not chk or " cells " in line[:200] and " flops " in line[:200] and ":" not in line[15:40]:
            g.add("INFO", "textbook", line[len("textbook_lint: "):][:300])
            continue
        g.add("FAIL" if tag == "REFUSE" else "WARN", f"textbook.{chk}", msg[:500], TEXTBOOK_FIX.get(chk, ""))
    for stall in re.findall(r"^GATE_STALL (.*)$", out, re.M):
        g.add("FAIL", "gate_stall", f"{stall[:200]} (step cap; repair/legalizer blow-up or GRT stall)",
              "read the remote cts.log / grt.log tail: the route would stall the same way; reduce density / fix the "
              "floorplan or the repair_design fan-out cause before routing")
    if cts and kv.get("GATE_CTS_RC") not in (None, "0"):
        g.add("FAIL", "cts_run", "placement / CTS of the kit failed: " + "; ".join(re.findall(r"^GATE_CTSERR (.*)$", out, re.M))[:500],
              "the route would fail the same way (DPL-0033 / GPL-0305 / CTS-*): fix the floorplan / density before routing")
    if cts:
        ck = re.search(r"^GATE_CK (.*)$", out, re.M)
        g.add("INFO" if ck else "WARN", "cts_calibration", (ck.group(1)[:900] if ck else
              f"CTS rc={kv.get('GATE_CTS_RC')} ck_insertion rc={kv.get('GATE_CK_RC')}"))
        pd = float(spec["route"].get("pd", 0.55))
        dens = [float(x) for x in re.findall(r"^GATE_GPLD .*?(?:-density|target density:)\s+([\d.]+)", out, re.M)]
        if dens:
            sev = "WARN" if abs(dens[0] - pd) > 0.05 else "INFO"
            g.add(sev, "density", f"effective global-placement target density {dens[0]:.3f} vs spec PD {pd:.2f}",
                  "clear PLACE_DENSITY_LB_ADDON (ref_tile does) or set route.pd to what the placer should target"
                  if sev == "WARN" else "")
        if spec["kind"] == "cluster" and spec.get("clock", "spine") == "spine" and kv.get("GATE_CTS_RC") == "0":
            done = re.search(r"^GATE_SPINE_DONE .*OT_SPINE done port (\S+)", out, re.M)
            if not done or re.sub(r"\[0\]$", "", done.group(1)) != re.sub(r"\[0\]$", "", spec["clock_port"]):
                g.add("FAIL", "clock_spine", f"no 'OT_SPINE done port {spec['clock_port']}' in the CTS log: the spine did not "
                      "build, TritonCTS ran instead (OT_SPINE_PORT not reaching the container before 225badfab)",
                      "check OT_SPINE_PORT in config.mk and the PRE_CTS hook order (spine sourced first)")
            else:
                g.add("INFO", "clock_spine", f"spine built on port {done.group(1)}")
        for line in re.findall(r"^GATE_SPINE (.*)$", out, re.M):
            g.add("INFO", "clock_spine", line[:300])
        for line in re.findall(r"^GATE_PC (.*)$", out, re.M):
            g.add("INFO", "path_classes", line)
    check_cross_clock(g, spec, out, cts)
    clock_item(g, clock_record(out, cts, spec))


CLOCK_RESULT = "gate_result.json"       # <kit>/gate_result.json: the kit's gate result (commit it with the kit)


def clock_record(out: str, cts: bool, spec: dict | None = None) -> dict:
    """the clock evidence of one remote gate run: sinks of the largest root from the synthesized netlist (textbook
    lint 'clock_roots' line) and, with --cts, the measured TT insertion (latest leaf arrival) and leaf arrival spread
    (max - min over all register clock pins, ck_insertion.py 'all')."""
    rec = {"max_root_sinks": None, "root": None, "cts": bool(cts), "tt_insertion_ps": None, "tt_spread_ps": None,
           "tt_pin_spread_ps": None, "ff_insertion_ps": None, "ff_spread_ps": None, "ff_pin_spread_ps": None,
           "declared_clock": (spec or {}).get("clock"),
           "limits": {"sinks": TL.CLK_ROOT_SINKS_MAX, "insertion_ps": TL.CLK_INSERTION_MAX_PS,
                      "spread_ps": TL.CLK_SPREAD_MAX_PS}}
    m = re.search(r"textbook_lint: INFO clock_roots max_root_sinks=(\d+) root=(\S+)", out)
    if m:
        rec["max_root_sinks"], rec["root"] = int(m.group(1)), m.group(2)
    domains = []
    for line in re.findall(r"^GATE_CK_DOMAIN (.*)$", out, re.M):
        try:
            domains.append(json.loads(line))
        except (ValueError, TypeError):
            continue
    if domains:
        rec["clock_measurements"] = domains
        # The largest root may be a secondary clock (fcc: str_clk on cks[0],
        # 17,460 sinks), so its tree must supply its own measured exception.
        root = (rec["root"] or "").removeprefix("port:")
        matched = [d for d in domains if d.get("source") == root or d.get("clock") == root]
        if cts and len(matched) == 1:
            matched[0] = with_child_flops(matched[0], spec)
            corner_spreads(rec, matched[0])
            child_pair_spreads(rec, matched[0], spec)
            if rec["tt_insertion_ps"] is not None:
                rec["measured_clock"] = matched[0].get("clock")
    else:
        for c in ("tt", "ff"):
            ck = re.search(rf"^GATE_CK .*?\b{c} insertion all ([\d.]+)\.\.([\d.]+) ps", out, re.M)
            if cts and ck:
                lo, hi = float(ck.group(1)), float(ck.group(2))
                rec[f"{c}_insertion_ps"], rec[f"{c}_spread_ps"] = hi, round(hi - lo, 1)
    level, text = TL.clock_rule_eval(rec["max_root_sinks"], rec)
    rec["verdict"] = ("REFUSE" if level == "FAIL" else "UNKNOWN" if rec["max_root_sinks"] is None else level)
    rec["text"] = text
    if (spec or {}).get("clock") == "multiple_cts_roots":
        expected = set(spec["clock_ports"])
        actual = [d.get("source") for d in domains]
        issues = []
        per_root = []
        landed_cluster = spec.get("kind") == "cluster" and bool(spec.get("children"))
        graph = parent_link_graph(spec) if landed_cluster else None
        if landed_cluster:
            if graph is None:
                issues.append("landed cluster: the parent RTL cannot be read, cross-region links not verified")
            else:
                bad, landed = cross_region_links(graph)
                issues += bad
                rec["landed_child_links"] = [dict(a=a.lstrip("*"), b=b.lstrip("*"), landing=n) for a, b, n in landed]
        if not cts:
            issues.append("multiple_cts_roots requires actual --cts measurement")
        if len(actual) != len(set(actual)) or set(actual) != expected:
            issues.append("actual per-root clock measurement coverage differs from clock_ports")
        for domain in domains:
            al = (domain.get("tt") or {}).get("all") or {}
            try:
                n = int(al["n"])
                lo, hi = float(al["min"]), float(al["max"])
                if n <= 0 or not math.isfinite(lo) or not math.isfinite(hi) or not 0 < lo <= hi:
                    raise ValueError("invalid actual clock population")
                measured = corner_spreads({}, domain)
                if landed_cluster:
                    measured.update(root_child_flops(domain, spec, graph))
                    if measured.get("raw_pin_fail"):
                        issues.append(f"{domain.get('source')}: " + "; ".join(measured["raw_pin_fail"]))
                level, why = TL.clock_rule_eval(n, measured)
                per_root.append(dict(source=domain.get("source"), sinks=n, **measured,
                                     verdict="REFUSE" if level == "FAIL" else level, text=why))
                if level == "FAIL":
                    issues.append(f"{domain.get('source')}: {why}")
            except (KeyError, TypeError, ValueError, OverflowError):
                issues.append(f"{domain.get('source')}: missing finite positive actual TT root census")
        rec["per_root"] = per_root
        if landed_cluster and per_root and not issues:
            # PL-GATE: the per-root child-flop judgement IS the cluster's clock rule (one root's raw spread is not)
            lv = [r["verdict"] for r in per_root]
            rec["verdict"] = "WARN" if "WARN" in lv else "PASS"
            rec["text"] = "per root: " + "; ".join(f"{r['source']} " + ", ".join(
                f"{c.upper()} {r.get(c + '_pin_spread_ps')} ps ({r.get(c + '_pin_spread_basis', 'pin-flop')})"
                for c in ("tt", "ff")) for r in per_root) + f" (limit {TL.CLK_SPREAD_MAX_PS:g} per root)" + "".join(
                f"; {r['source']} WARN: {r['text'].split('WARN: ', 1)[-1]}" for r in per_root if r["verdict"] == "WARN")
            for c in ("tt", "ff"):
                vals = [r[f"{c}_pin_spread_ps"] for r in per_root if r.get(f"{c}_pin_spread_ps") is not None]
                if vals:
                    rec[f"{c}_pin_spread_ps"], rec[f"{c}_pin_spread_basis"] = max(vals), "per_root"
        if issues:
            rec["verdict"], rec["text"] = "REFUSE", "; ".join(issues)
    return rec


def upgrade_clock_record(ev: dict | None) -> dict | None:
    """A pre-0dq gate clock record (no "<c>_pin_spread_ps") judged by the 0dq rule from its OWN report: the pin-flop
    (boundary register) spread of the measured root's domain, as corner_spreads records it today.  ROOT-0040 2026-10-18:
    without this an old record falls back to the all-register leaf spread, which 0dq does not judge."""
    if not isinstance(ev, dict) or any(f"{c}_pin_spread_ps" in ev for c in ("tt", "ff")):
        return ev
    doms = [d for d in ev.get("clock_measurements") or [] if isinstance(d, dict)]
    want = ev.get("measured_clock")
    root = str(ev.get("root") or "").removeprefix("port:")
    matched = [d for d in doms if want and d.get("clock") == want] or \
              [d for d in doms if d.get("source") == root or d.get("clock") == root]
    if len(matched) != 1:
        return ev
    add = {k: v for k, v in corner_spreads({}, matched[0]).items() if k.endswith("_pin_spread_ps")}
    return dict(ev, **add, pin_spread_from_gate_report=True) if add else ev


def with_child_flops(domain: dict, spec: dict | None) -> dict:
    """S81-DEC2 2026-10-18 (owner 10-17 0dq: "spread at the CHILD flops for a cluster"): for a cluster whose every
    boundary register clock pin is a hard child's clock pin (a wires-only parent), the pin-flop arrival is the child's
    clock-pin arrival PLUS that child's own boundary-register insertion (views/<child>/insertion.json <corner>.boundary
    min..max).  The raw child clock-pin spread is the parent compensation, not skew: s81lk_kp4_dec taps ddly 144 ps
    later than dsyn because ddly's own tree is 107 ps shorter.  Adds domain[c]["child_flop"] {n, min, max, pins};
    unchanged when the spec has no children, a child pin has no record, or glue registers share the boundary."""
    import fnmatch
    kids = [ch for ch in (spec or {}).get("children") or [] if isinstance(ch, dict) and ch.get("view") and ch.get("inst")]
    if (spec or {}).get("kind") != "cluster" or not kids:
        return domain
    out = dict(domain)
    for c in ("tt", "ff"):
        cr = domain.get(c) or {}
        pins = ((cr.get("macros") or {}).get("pins")) or []
        bd = cr.get("boundary") or {}
        if not pins or bd.get("n") != len(pins):
            continue                                    # glue registers on the boundary too: keep the measured record
        rows = []
        for x in pins:
            inst = str(x.get("pin", "")).rsplit("/", 1)[0]
            kid = next((ch for ch in kids if fnmatch.fnmatchcase(inst, ch["inst"].lstrip("*"))
                        or fnmatch.fnmatchcase(inst, ch["inst"])), None)
            ij = ROOT / kid["view"] / "insertion.json" if kid else None
            try:
                b = json.loads(ij.read_text())[c]["boundary"]
                lo, hi = float(x["arr"]) + float(b["min"]), float(x["arr"]) + float(b["max"])
            except (AttributeError, OSError, ValueError, KeyError, TypeError):
                rows = None
                break
            rows.append(dict(pin=x["pin"], arr=x["arr"], child_min=round(lo, 1), child_max=round(hi, 1)))
        if rows:
            out[c] = dict(cr, child_flop=dict(n=len(rows), min=min(r["child_min"] for r in rows),
                                              max=max(r["child_max"] for r in rows), pins=rows))
    return out


def _vlog_preprocess(text: str, defines) -> str:
    """comments stripped, `ifdef / `ifndef / `elsif / `else / `endif resolved against defines (other directives dropped)"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    defs = {str(d).split("=", 1)[0].lstrip("-D") for d in defines or []}
    out, stack = [], []                     # stack of [this branch live, some branch taken]
    for line in text.splitlines():
        m = re.match(r"\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w*)", line)
        live = all(x[0] for x in stack)
        if not m:
            if live and not re.match(r"\s*`", line):
                out.append(line)
            continue
        kw, name = m.groups()
        if kw in ("ifdef", "ifndef"):
            on = (name in defs) == (kw == "ifdef")
            stack.append([on, on])
        elif kw == "elsif" and stack:
            on = not stack[-1][1] and name in defs
            stack[-1] = [on, stack[-1][1] or on]
        elif kw == "else" and stack:
            stack[-1] = [not stack[-1][1], True]
        elif kw == "endif" and stack:
            stack.pop()
    return "\n".join(out)


VLOG_KEYWORDS = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "logic", "assign", "always",
                 "always_ff", "always_comb", "initial", "generate", "endgenerate", "parameter", "localparam", "if",
                 "else", "for", "begin", "end", "case", "endcase", "function", "endfunction", "genvar", "integer"}


def linked_child_pairs(spec: dict | None) -> list | None:
    """HANDOFF 0fz 2026-10-18 (owner 0dq "boundary matched to the NEIGHBOURS"): the communicating hard-child pairs of a
    wires-only parent, from its top module's RTL: two child instances are linked when one net (not a parent port)
    connects to both, i.e. one child's output feeds the other's input.  Returns sorted [(inst_a, inst_b)] by child
    spec inst pattern, or None when the RTL cannot be read or a child instance is not found (caller keeps the
    all-children spread)."""
    import fnmatch
    spec = spec or {}
    kids = [ch for ch in spec.get("children") or [] if isinstance(ch, dict) and ch.get("inst")]
    top = spec.get("top")
    if not kids or not top:
        return None
    body = None
    for src in spec.get("sources") or []:
        try:
            text = _vlog_preprocess((ROOT / src).read_text(errors="replace"), spec.get("defines"))
        except OSError:
            return None
        m = re.search(rf"\bmodule\s+{re.escape(top)}\b(.*?)\bendmodule\b", text, re.S)
        if m:
            body = m.group(1)
            break
    if body is None:
        return None
    hdr = re.match(r"\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\)\s*;", body, re.S)
    ports = set(re.findall(r"\b([A-Za-z_]\w*)\b", hdr.group(2))) - VLOG_KEYWORDS if hdr else set()
    for decl in re.findall(r"\b(?:input|output|inout)\b([^;]*);", body):
        ports |= set(re.findall(r"\b([A-Za-z_]\w*)\b", decl)) - VLOG_KEYWORDS
    nets: dict = {}
    seen = set()
    inst_re = re.compile(r"\b([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*([A-Za-z_]\w*)\s*\(((?:[^()]|\([^()]*\))*)\)\s*;", re.S)
    for mod, inst, conns in inst_re.findall(body):
        if mod in VLOG_KEYWORDS:
            continue
        kid = next((ch for ch in kids if fnmatch.fnmatchcase(inst, ch["inst"].lstrip("*"))
                    or fnmatch.fnmatchcase(inst, ch["inst"])), None)
        if kid is None:
            continue
        seen.add(kid["inst"])
        for expr in re.findall(r"\.\s*\w+\s*\(((?:[^()]|\([^()]*\))*)\)", conns):
            for n in set(re.findall(r"(?<![\w'])([A-Za-z_]\w*)\b", expr)) - ports - VLOG_KEYWORDS:
                nets.setdefault(n, set()).add(kid["inst"])
    if seen != {ch["inst"] for ch in kids}:
        return None
    return sorted({tuple(sorted((a, b))) for ks in nets.values() for a in ks for b in ks if a < b})


def child_pair_spreads(rec: dict, domain: dict, spec: dict | None) -> dict:
    """HANDOFF 0fz 2026-10-18: a wires-only parent (pin-flop spread on the "child_flop" basis) is judged per LINKED
    child pair, not across all children: for each pair (A, B) the boundary-flop arrival difference at that corner is
    max(A.max - B.min, B.max - A.min) over the two children's boundary flops (child clock-pin arrival + the child's own
    boundary insertion), and "<c>_pin_spread_ps" becomes the worst linked pair (basis "child_pair").  Per-pair numbers
    go to rec["child_pairs"].  Unchanged when there is no child_flop record or no linked pair can be derived."""
    import fnmatch
    if not any(rec.get(f"{c}_pin_spread_basis") == "child_flop" for c in ("tt", "ff")):
        return rec
    pairs = linked_child_pairs(spec)
    if not pairs:
        return rec
    kids = [ch["inst"] for ch in (spec or {}).get("children") or [] if isinstance(ch, dict) and ch.get("inst")]
    table = []
    for c in ("tt", "ff"):
        if rec.get(f"{c}_pin_spread_basis") != "child_flop":
            continue
        span: dict = {}
        for r in ((domain.get(c) or {}).get("child_flop") or {}).get("pins") or []:
            inst = str(r.get("pin", "")).rsplit("/", 1)[0]
            k = next((p for p in kids if fnmatch.fnmatchcase(inst, p.lstrip("*")) or fnmatch.fnmatchcase(inst, p)), None)
            if k is None:
                return rec
            lo, hi = span.get(k, (math.inf, -math.inf))
            span[k] = (min(lo, float(r["child_min"])), max(hi, float(r["child_max"])))
        if any(a not in span or b not in span for a, b in pairs):
            return rec
        worst = None
        for a, b in pairs:
            (alo, ahi), (blo, bhi) = span[a], span[b]
            d = round(max(ahi - blo, bhi - alo), 1)
            table.append(dict(corner=c, a=a.lstrip("*"), b=b.lstrip("*"), ps=d,
                              a_range=[round(alo, 1), round(ahi, 1)], b_range=[round(blo, 1), round(bhi, 1)]))
            worst = d if worst is None else max(worst, d)
        rec[f"{c}_child_flop_spread_ps"] = rec[f"{c}_pin_spread_ps"]
        rec[f"{c}_pin_spread_ps"], rec[f"{c}_pin_spread_basis"] = worst, "child_pair"
    rec["child_pairs"] = table
    return rec


LANDING_HALF_RE = re.compile(r"(.+)_([wr])")       # lp.py landing halves u_lpl_<n>_w (source root) / u_lpl_<n>_r (reader root)
RESET_RUN_RE = re.compile(r"u_lprc?_\w+")          # lp.py regional reset runs (1-bit plain hops; the only legal plain crossing)


def parent_link_graph(spec: dict | None) -> dict | None:
    """PL-GATE 2026-10-18 (landed parents, tools/landed_parent/lp.py): the instance / net graph of a multi-root parent's top
    module: {inst: {"root": clock port on its clock pins or None, "kid": child spec inst pattern or None}} plus
    "nets": {net class: set(inst)}.  Nets joined by an assign are one class (lp.py: <net>__l_<r> = lpl_<n>_o); parent
    ports and clock ports are not links; the bench-only MUT selects elaborate MUT = 0 (as lp.py audit).  None when the
    RTL cannot be read or a child instance is missing."""
    import fnmatch
    spec = spec or {}
    kids = [ch for ch in spec.get("children") or [] if isinstance(ch, dict) and ch.get("inst")]
    top, cks = spec.get("top"), set(spec.get("clock_ports") or [])
    if not kids or not top:
        return None
    body = None
    for src in spec.get("sources") or []:
        try:
            text = _vlog_preprocess((ROOT / src).read_text(errors="replace"), spec.get("defines"))
        except OSError:
            return None
        m = re.search(rf"\bmodule\s+{re.escape(top)}\b(.*?)\bendmodule\b", text, re.S)
        if m:
            body = re.sub(r"\(MUT == \d+\) \? ([^:;]+?) : ([^;]+?);", r"\2;", m.group(1))
            break
    if body is None:
        return None
    hdr = re.match(r"\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\)\s*;", body, re.S)
    ports = set(re.findall(r"\b([A-Za-z_]\w*)\b", hdr.group(2))) - VLOG_KEYWORDS if hdr else set()
    for decl in re.findall(r"\b(?:input|output|inout)\b([^;]*);", body):
        ports |= set(re.findall(r"\b([A-Za-z_]\w*)\b", decl)) - VLOG_KEYWORDS
    ports |= cks
    ident = re.compile(r"(?<![\w'$])([A-Za-z_]\w*)\b")
    parent: dict = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def balanced(t, i):                     # t[i] == "(": index after its matching ")"
        d = 0
        for j in range(i, len(t)):
            d += {"(": 1, ")": -1}.get(t[j], 0)
            if d == 0:
                return j + 1
        return None
    stmts = [x.strip() for x in body.split(";")]
    for st in stmts:
        m = re.match(r"assign\s+([^=]+)=(.*)$", st, re.S)
        if m:
            ids = sorted((set(ident.findall(m[1])) | set(ident.findall(m[2]))) - VLOG_KEYWORDS)
            if ids and not set(ids) & ports:        # a port assign (z = y2) is the boundary, not a link
                for a in ids[1:]:
                    parent[find(a)] = find(ids[0])
    insts, nets, seen = {}, {}, set()
    for st in stmts:
        m = re.match(r"([A-Za-z_]\w*)\s*", st)
        if not m or m[1] in VLOG_KEYWORDS:
            continue
        mod, i = m[1], m.end()
        if st[i:i + 1] == "#":
            k = st.index("(", i)
            i = balanced(st, k)
            if i is None:
                continue
        m = re.match(r"\s*([A-Za-z_]\w*)\s*(?=\()", st[i:])
        if not m:
            continue
        inst, k = m[1], i + m.end()
        e = balanced(st, k)
        if e is None or st[e:].strip():
            continue
        # top-level names: the pattern without its hierarchy '*' (else "*u0" would claim reset run u_lprc_u0)
        kid = next((ch["inst"] for ch in kids if fnmatch.fnmatchcase(inst, ch["inst"].lstrip("*"))), None)
        if kid:
            seen.add(kid)
        conns, exprs, j = st[k + 1:e - 1], [], 0
        while True:
            pm = re.compile(r"\.\s*\w+\s*\(").search(conns, j)
            if not pm:
                break
            q = balanced(conns, pm.end() - 1)
            if q is None:
                break
            exprs.append(conns[pm.end():q - 1])
            j = q
        root = sorted({x.strip() for x in exprs if x.strip() in cks})
        insts[inst] = dict(kid=kid, root=root[0] if len(root) == 1 else None, module=mod)
        for expr in exprs:
            for n in set(ident.findall(expr)) - ports - VLOG_KEYWORDS:
                nets.setdefault(find(n), set()).add(inst)
    if seen != {ch["inst"] for ch in kids}:
        return None
    return dict(insts=insts, nets=nets)


def cross_region_links(graph: dict) -> tuple:
    """(issues, landed) of a landed parent's link graph: every net class whose instances sit on DIFFERENT clock roots must
    be a landing (only the two halves u_lpl_<n>_w / u_lpl_<n>_r of one landing on it) or a regional reset run
    (u_lpr_* / u_lprc_*); anything else is an "unlanded cross-region link".  landed = [(child A, child B, landing)]:
    hard-child pairs linked through one landing (A -> <n>_w ... <n>_r -> B)."""
    insts, nets = graph["insts"], graph["nets"]
    issues, halves = [], {}
    for net, members in sorted(nets.items()):
        roots = {insts[i]["root"] for i in members}
        if len(roots) < 2:
            continue
        mm = sorted(members)
        lh = [LANDING_HALF_RE.fullmatch(i) for i in mm]
        if len(mm) == 2 and all(lh) and lh[0][1] == lh[1][1] and {x[2] for x in lh} == {"w", "r"}:
            continue
        # TW2-PSLICE2 10-19 (lp.py share_rings): ONE ring half read by several read halves (one per reader) -- every member
        # a landing half (no child, no glue), exactly one ring
        if len(mm) > 2 and all(lh) and sum(x[2] == "w" for x in lh) == 1 and not any(insts[i]["kid"] for i in mm):
            continue
        if any(RESET_RUN_RE.fullmatch(i) for i in mm) and \
                len({insts[i]["root"] for i in mm if not RESET_RUN_RE.fullmatch(i)}) <= 1:
            continue                                    # reset run hop: crosses only between reset-run stages
        issues.append(f"unlanded cross-region link {net}: " + ", ".join(f"{i} ({insts[i]['root']})" for i in mm))
    ring_of = {}                            # share_rings: read-half base -> its ring's base (net with one w + r halves)
    for net, members in nets.items():
        lh = [LANDING_HALF_RE.fullmatch(i) for i in members]
        if all(lh) and sum(x[2] == "w" for x in lh) == 1:
            wb = next(x[1] for x in lh if x[2] == "w")
            for x in lh:
                if x[2] == "r" and x[1] != wb:
                    ring_of[x[1]] = wb
    for net, members in nets.items():
        for i in members:
            m = LANDING_HALF_RE.fullmatch(i)
            if m and not insts[i]["kid"]:
                for j in members:
                    if insts[j]["kid"]:
                        halves.setdefault((m[1], m[2]), set()).add(insts[j]["kid"])
    landed = sorted({(a, b, base) for (base, side), ks in halves.items() if side == "w"
                     for a in ks for b in halves.get((base, "r"), ()) if a != b} |
                    {(a, b, rb) for rb, wb in ring_of.items() for a in halves.get((wb, "w"), ())
                     for b in halves.get((rb, "r"), ()) if a != b})
    return issues, landed


def root_child_flops(domain: dict, spec: dict | None, graph: dict | None) -> dict:
    """PL-GATE 2026-10-18 (landed-regions standard: "judge parents per linked child pair at child flops, TT and FF <= 80"):
    the pin-flop spread of ONE root of a multi-root cluster on the child-flop basis.  Nodes: every hard child on this root
    (clock-pin arrival + views/<child>/insertion.json <corner>.boundary min..max) and the root's soft (glue: landing
    halves, pads, reset runs) registers as one group (ck_insertion child_flop.soft.all).  Judged per linked pair on this
    root (child-child, child-soft from the RTL graph); without a derivable pair the whole-root span.  Returns
    {<c>_pin_spread_ps, <c>_pin_spread_basis, pairs, children} or {} when this root has no hard child (measured kept)."""
    import fnmatch
    kids = [ch for ch in (spec or {}).get("children") or [] if isinstance(ch, dict) and ch.get("view") and ch.get("inst")]
    src = domain.get("source")
    out, pairs = {}, []
    for c in ("tt", "ff"):
        cr = domain.get(c) or {}
        pins = ((cr.get("macros") or {}).get("pins")) or []
        if not pins:
            continue
        span, ok, raw_rows, eff, cot_rows = {}, True, [], {}, []
        for x in pins:
            inst, lpin = (str(x.get("pin", "")).rsplit("/", 1) + [""])[:2]
            kid = next((ch for ch in kids if fnmatch.fnmatchcase(inst, ch["inst"].lstrip("*"))
                        or fnmatch.fnmatchcase(inst, ch["inst"])), None)
            try:
                ins = json.loads((ROOT / kid["view"] / "insertion.json").read_text())
                # HF-4d 10-19: a multi-clock child is referenced per clock pin (clock_measurements[pin]); a RAW SRAM
                # clock entry (no routed boundary) takes the leaf's own pin -> SRAM wire from its closed record
                # (clock_entry_constraints.landed_raw_pins) and is judged against its co-timed CTS-root pin below
                cm = (ins.get("clock_measurements") or {}).get(lpin)
                b = ((cm or {}).get(c) or {}).get("boundary") if cm else ins[c]["boundary"]
                if b:
                    lo, hi = float(x["arr"]) + float(b["min"]), float(x["arr"]) + float(b["max"])
                    if b.get("mean") is not None:
                        eff[(inst, lpin)] = float(x["arr"]) + float(b["mean"])
                    if cm and any(not ((v or {}).get(cc) or {}).get("boundary")
                                  for v in (ins.get("clock_measurements") or {}).values() for cc in ("tt", "ff", "ss")):
                        # ROOT-INF21 10-19: a boundary pin of a multi-root child record is co-timed with its ref too
                        cot = CE.landed_record_pins(ROOT / kid["view"], ROOT)["cotimed"].get(lpin)
                        if cot:
                            cot_rows.append((inst, lpin, cot))
                else:
                    raw = CE.landed_raw_pins(ROOT / kid["view"], ROOT)[lpin]
                    rlo, rmean, rhi = raw["refs"][c]
                    lo, hi = float(x["arr"]) + rlo, float(x["arr"]) + rhi
                    raw_rows.append((inst, lpin, float(x["arr"]) + rmean, raw))
            except (TypeError, OSError, ValueError, KeyError, AttributeError):
                ok = False
                break
            plo, phi = span.get(kid["inst"], (math.inf, -math.inf))
            span[kid["inst"]] = (min(plo, lo), max(phi, hi))
        for inst, lpin, cot in cot_rows if ok else []:
            raw_rows.append((inst, lpin, eff[(inst, lpin)], cot))
        for inst, lpin, e, raw in raw_rows if ok else []:
            r = eff.get((inst, raw["ref"]))
            row = dict(root=src, corner=c, pin=f"{inst}/{lpin}", co_timed=f"{inst}/{raw['ref']}", eff=round(e, 1),
                       eff_ref=None if r is None else round(r, 1), tol=raw["tol"], record=raw["record"])
            row["skew"] = None if r is None else round(e - r, 1)
            row["verdict"] = "FAIL" if r is None or abs(e - r) > raw["tol"] else "PASS"
            out.setdefault("raw_pins", []).append(row)
            if row["verdict"] == "FAIL":
                out.setdefault("raw_pin_fail", []).append(
                    f"{c.upper()} raw child clock pin {row['pin']} " + (f"not co-measured with {row['co_timed']}" if r is None
                    else f"{row['skew']:+.1f} ps vs {row['co_timed']} (leaf sign-off tolerance {raw['tol']:g})"))
        if not ok:
            out[f"{c}_pin_spread_basis_note"] = "a hard child clock pin has no insertion.json boundary: measured kept"
            continue
        al = cr.get("all") or {}
        cf = cr.get("child_flop") or {}
        soft = (cf.get("soft") or {}).get("all") or None
        nodes = dict(span)
        if soft and soft.get("n"):
            nodes["soft"] = (float(soft["min"]), float(soft["max"]))
        whole = [v for v in nodes.values()]
        if "soft" not in nodes and al.get("n") and int(al["n"]) > len(pins):
            # soft registers measured but not separated (pre-PL-GATE ck record): ck_insertion child_flop.all (soft raw,
            # child pins + R mean) bounds the same union; else the raw all-register span (conservative)
            ref = cf.get("all") if (cf.get("all") or {}).get("n") else al
            whole.append((float(ref["min"]), float(ref["max"])))
        links = set()
        if graph is not None and (soft is not None or not (al.get("n") and int(al["n"]) > len(pins))):
            insts = graph["insts"]
            for members in graph["nets"].values():
                here = {(insts[i]["kid"] or "soft") for i in members if insts[i]["root"] == src}
                here &= set(nodes)
                links |= {tuple(sorted((a, b))) for a in here for b in here if a < b}
        lo, hi = min(v[0] for v in whole), max(v[1] for v in whole)
        if links:
            worst = None
            for a, b in sorted(links):
                (alo, ahi), (blo, bhi) = nodes[a], nodes[b]
                d = round(max(ahi - blo, bhi - alo), 1)
                pairs.append(dict(root=src, corner=c, a=a.lstrip("*"), b=b.lstrip("*"), ps=d,
                                  a_range=[round(alo, 1), round(ahi, 1)], b_range=[round(blo, 1), round(bhi, 1)]))
                worst = d if worst is None else max(worst, d)
            out[f"{c}_pin_spread_ps"], out[f"{c}_pin_spread_basis"] = worst, "root_child_pair"
        else:
            out[f"{c}_pin_spread_ps"], out[f"{c}_pin_spread_basis"] = round(hi - lo, 1), "root_child_flop"
        out[f"{c}_root_child_flop_span"] = [round(lo, 1), round(hi, 1)]
        out["children"] = sorted(k.lstrip("*") for k in span)
    if pairs:
        out["pairs"] = pairs
    return out


def corner_spreads(rec: dict, domain: dict) -> dict:
    """TT and FF insertion (latest register arrival), all-register leaf spread and pin-flop (boundary register) spread
    of one ck_insertion clock record (owner 10-17 0dq: the rule is the pin-flop spread at TT AND FF)."""
    for c in ("tt", "ff"):
        cr = domain.get(c) or {}
        al, bd = cr.get("all") or {}, cr.get("boundary") or {}
        cf = cr.get("child_flop") or {}
        if cf.get("boundary") and cf.get("all"):
            # CHILD-FLOP (SM-RP4 2026-10-18): a cluster's hard-child clock pins enter all_registers at their RAW arrival,
            # which the spine sets EARLY by the child's own insertion R; the rule judges the child FLOPS (pin + R)
            bd, al = cf["boundary"], cf["all"]
            rec[f"{c}_child_flop_refs"] = cf.get("refs")
        if al.get("min") is not None and al.get("max") is not None:
            lo, hi = float(al["min"]), float(al["max"])
            rec[f"{c}_insertion_ps"], rec[f"{c}_spread_ps"] = hi, round(hi - lo, 1)
        cf = cr.get("child_flop") or {}
        if cf.get("min") is not None and cf.get("max") is not None:   # wires-only cluster: the child pin flops
            rec[f"{c}_pin_spread_ps"] = round(float(cf["max"]) - float(cf["min"]), 1)
            rec[f"{c}_pin_spread_basis"] = "child_flop"
        elif bd.get("min") is not None and bd.get("max") is not None:
            rec[f"{c}_pin_spread_ps"] = round(float(bd["max"]) - float(bd["min"]), 1)
    return rec


def clock_item(g: Gate, rec: dict) -> None:
    """measured clock rule (owner 2026-10-13, constants in textbook_lint.py): reported for every kit."""
    g.clock = rec
    for row in rec.get("child_pairs") or []:
        g.add("INFO", "clock_child_pair", f"{row['corner'].upper()} linked children {row['a']}-{row['b']}: boundary-flop "
              f"arrival difference {row['ps']} ps ({row['a']} {row['a_range'][0]}..{row['a_range'][1]}, "
              f"{row['b']} {row['b_range'][0]}..{row['b_range'][1]}; limit {TL.CLK_SPREAD_MAX_PS:g})")
    for r in rec.get("per_root") or []:
        if any(str(r.get(f"{c}_pin_spread_basis", "")).startswith("root_child") for c in ("tt", "ff")):
            g.add("INFO", "clock_root_child_flop", f"root {r['source']} ({', '.join(r.get('children') or [])} + soft): " +
                  ", ".join(f"{c.upper()} {r.get(c + '_pin_spread_ps')} ps {r.get(c + '_pin_spread_basis')} span "
                            f"{(r.get(c + '_root_child_flop_span') or ['-', '-'])[0]}..{(r.get(c + '_root_child_flop_span') or ['-', '-'])[1]}"
                            for c in ("tt", "ff")) + f"; {r['verdict']} (limit {TL.CLK_SPREAD_MAX_PS:g})")
        for row in r.get("pairs") or []:
            g.add("INFO", "clock_child_pair", f"{row['corner'].upper()} root {row['root']} linked {row['a']}-{row['b']}: "
                  f"boundary-flop arrival difference {row['ps']} ps ({row['a']} {row['a_range'][0]}..{row['a_range'][1]}, "
                  f"{row['b']} {row['b_range'][0]}..{row['b_range'][1]}; limit {TL.CLK_SPREAD_MAX_PS:g})")
    for row in rec.get("landed_child_links") or []:
        g.add("INFO", "clock_landed_link", f"{row['a']} -> {row['b']} crosses regions through landing {row['landing']}_w/_r")
    if rec["verdict"] == "REFUSE":
        g.add("FAIL", "clock_rule", rec["text"] + ("" if rec["cts"] else " -- this gate ran without --cts")
              + (f" (declared clock '{rec['declared_clock']}' does not waive it)" if rec.get("declared_clock") else ""),
              TL.CLOCK_RULE_FIX)
    elif rec["verdict"] == "WARN":
        g.add("WARN", "clock_rule", f"root {rec['root']}: {rec['text']}",
              "guidance only (owner 10-17 0dq): match the boundary by parent compensation or a landed link")
    elif rec["verdict"] == "UNKNOWN":
        g.add("WARN", "clock_rule", "the synthesized netlist's clock sinks were not reported: " + rec["text"],
              "read the remote log (textbook lint line 'clock_roots')")
    else:
        g.add("INFO", "clock_rule", f"root {rec['root']}: {rec['text']}")


def textbook_reset_args(spec):
    """GATE-FRICTION 2026-10-18: the kit's declared reset_ports reach the textbook lint, so a declared reset (KV core_peer
    por_n, 5,344 async loads) is judged on the reset fanout limit, not the data-port one.  '' when none are declared (the
    gate script stays byte-identical)."""
    names = [str(x) for x in spec.get("reset_ports") or [] if isinstance(x, str) and re.fullmatch(r"[\w$\[\]:.]+", x)]
    return f" --set reset_ports={shlex.quote(','.join(names))}" if names else ""


def reset_landing_args(spec):
    """ROOT-RST 2026-10-19: the kit's reset_landing record -> textbook_lint args.  {"waive": "<reason>"} -> --waive
    reset_landing (the finding stays a WARN); {"max_sinks": N, "reason": "..."} -> --set rst_land_max=N.  '' otherwise
    (enable true / false: the netlist itself is judged).  SpecError-free: a malformed record is judged at the default."""
    rl = spec.get("reset_landing")
    if not isinstance(rl, dict):
        return ""
    out = ""
    if str(rl.get("waive") or "").strip():
        out += " --waive reset_landing"
    n = rl.get("max_sinks")
    if isinstance(n, int) and not isinstance(n, bool) and n > 0 and str(rl.get("reason") or "").strip():
        out += f" --set rst_land_max={n}"
    return out


def reset_landing_record(out: str) -> dict | None:
    """the gate netlist's reset_landing metrics (textbook_lint INFO line), None when the gate's lint predates the check"""
    m = re.search(r"^GATE_TB textbook_lint: INFO reset_landing (\{.*\})\s*$", out, re.M)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
    except ValueError:
        return None
    ports = [p for p in d.get("ports") or [] if isinstance(p, dict)]
    mx = d.get("max")
    waived = bool(re.search(r"^GATE_TB textbook_lint: WAIVED reset_landing:", out, re.M))
    over = [p["port"] for p in ports if isinstance(mx, (int, float)) and p.get("sinks", 0) > mx]
    return {"max_sinks": mx, "ports": ports, "over": over, "waived": waived, "ok": not over or waived}


def kit_gate_evidence(kd: Path, source_commit=None, why: list | None = None, note: list | None = None) -> dict | None:
    """The kit's gate result when it is bound to this exact source commit and to the daemon overlays the gate executed
    (SB.validate: route-only helper drift does not invalidate a gate).  why: receives the refusal reason."""
    def no(reason):
        if why is not None:
            why.append(reason)
        return None
    try:
        d = json.loads((kd / CLOCK_RESULT).read_text())
        binding = d.get("source_binding")
        if isinstance(binding, dict) and binding.get("schema") == SB.SCHEMA and "consumed" not in binding \
                and binding.get("files"):
            rec = reconstruct_consumed(binding, kd)
            if rec is not None:
                binding = {**binding, "consumed": rec}
                d["source_binding"] = binding
        tile = [kd.name, d.get("kit")]
        try:     # S81-DEC5 10-18: the kit job's recorded clock_rule_waiver also judges the relaxing-rule requirement
            w = json.loads((kd / "job.json").read_text()).get("clock_rule_waiver")
            if isinstance(w, dict) and isinstance(d.get("clock"), dict):
                d = {**d, "clock": {**d["clock"], "clock_rule_waiver": w}}
        except (OSError, ValueError, AttributeError):
            pass
        try:
            ks = json.loads((kd / "spec.json").read_text())
            tile += [ks.get("name"), ks.get("top")]
        except (OSError, ValueError):
            pass
        try:
            ok, reason = SB.validate(binding, ROOT, DAEMON_TREE, source_commit, clock=d.get("clock"),
                                     tile=[t for t in tile if t], gate=d)
        except TypeError:                                    # an older source_binding without the gate / tile scope
            try:
                ok, reason = SB.validate(binding, ROOT, DAEMON_TREE, source_commit, clock=d.get("clock"),
                                         tile=[t for t in tile if t])
            except TypeError:
                ok, reason = SB.validate(binding, ROOT, DAEMON_TREE, source_commit, clock=d.get("clock"))
        if not ok:
            return no(reason)
        if note is not None:
            note.append(reason)
        if binding.get("staged_remeasurement"):
            log = binding.get("staged_measurement_log")
            if not isinstance(log, str) or not SB.staged_remeasurement_matches_log(binding, log.encode()):
                return no("staged remeasurement persisted log missing or receipt mismatch")
        elif not binding.get("remote_archive_verified"):
            return no("remote archive verification missing")
        if not isinstance(d.get("clock"), dict):
            return no("gate result carries no clock record (gate ran without --cts?)")
        return d
    except (OSError, ValueError, KeyError, AttributeError) as ex:
        return no(f"gate result unreadable: {type(ex).__name__}: {ex}"[:300])


def kit_clock_evidence(kd: Path, source_commit=None) -> dict | None:
    rec = kit_gate_evidence(kd, source_commit)
    return rec["clock"] if rec else None


def check_clock_evidence(g: Gate, kd: Path, known_sinks: int | None = None, closed_stands: bool = False, source_commit=None) -> dict:
    """SUBMIT side of the measured clock rule.  The kit's committed gate result decides when it exists; without one the
    sink count of this block's latest synthesized design (known_sinks, from the loop's job history) does.  A kit with no
    gate result and no history passes here and is judged by the in-flow lint right after synthesis (FLOORPLAN_MARGIN,
    before placement).  closed_stands: a CLOSED tile is not re-judged."""
    why, note = [], []
    rec = kit_gate_evidence(kd, source_commit, why, note)
    ev = upgrade_clock_record(rec["clock"]) if rec else None
    if rec and note and "reported, not refused" in note[0]:
        g.add("INFO", "source_binding", note[0][:1500])
    relaxed = (rec or {}).get("source_binding", {}).get("relaxing_rule_allowlist") if rec else None
    if relaxed and not closed_stands:
        # RELAXING-RULE ALLOWLIST (ROOT-0040): the gate stands across relaxing-only rule commits; recorded in the job
        g.relaxing_rule_allowlist = relaxed
        g.add("INFO", "relaxing_rule_allowlist", (note[0] if note else "relaxing-rule allowlist used")[:1500])
    if rec and not closed_stands and not rec["source_binding"].get("route_hold_context"):
        g.add("WARN", "route_hold_context",
              "historical CTS gate does not attest production hold margin/MM context; diagnostic clock evidence only",
              "re-gate with the route hold context before claiming production placement/CTS readiness; routed signoff remains required")
    if rec and not closed_stands:
        frozen = rec["source_binding"].get("route_overlay_plan")
        if frozen is None:
            # Legacy v2 has exact six-helper evidence, not a historical full route plan.
            frozen, _ = HO.capture_plan(DAEMON_TREE, ROOT)
            frozen["gate_verified_paths"] = rec["source_binding"].get("daemon_overlays", [])
            frozen["scope"] = "legacy_gate_exact_overlays_with_current_full_route_plan"
        else:
            # Route-only helpers are not bound by the gate: when they moved since the gate, the route freezes today's
            # effective plan (whose gate-executed rows SB.validate just proved equal to the staged ones).
            current, _ = HO.capture_plan(DAEMON_TREE, ROOT)
            if relaxed:
                # the relaxed paths changed since the gate: the route must run TODAY's (relaxed) helpers, never the
                # gate-frozen pre-relaxation bytes (the old in-flow lint would still FAIL on the relaxed rule)
                current["gate_verified_paths"] = SB.gate_overlay_paths(rec["source_binding"])
                current["scope"] = "gate_executed_overlays_verified_relaxing_rule_allowlist_current"
                current["relaxing_rule_allowlist"] = relaxed.get("commits")
                frozen = current
            elif SB.route_only_drift(frozen, current, rec["source_binding"]["files"]):
                current["gate_verified_paths"] = SB.gate_overlay_paths(rec["source_binding"])
                current["scope"] = "gate_executed_overlays_verified_route_only_helpers_current"
                frozen = current
        g.route_overlay_plan = frozen
    if (kd / CLOCK_RESULT).exists() and ev is None and not closed_stands:
        g.add("FAIL", "source_binding", "gate result is legacy, unverified, or differs from the route source/daemon overlay"
              + (f" ({why[0]})" if why else ""),
              "preserve original as unqualified; regenerate the gate for this exact source")
    n = (ev or {}).get("max_root_sinks")
    if not isinstance(n, int):          # the kit's own gate result outranks history (a rebuilt tile proves itself)
        n = known_sinks if isinstance(known_sinks, int) else None
    level, text = TL.clock_rule_eval(n if isinstance(n, int) else None, ev)
    ok = level != "FAIL"
    res = {"evidence": ev, "sinks": n, "ok": ok, "level": level, "text": text, "closed_stands": bool(closed_stands)}
    g.clock = res
    if level == "WARN" and not closed_stands:
        g.add("WARN", "clock_rule", text, "guidance only (owner 10-17 0dq): the check is pin-flop spread <= 80 ps at "
              "TT and FF plus a neighbour-matched boundary")
    elif ok or closed_stands:
        g.add("INFO", "clock_rule", text + (" (CLOSED tile: stands)" if closed_stands and not ok else ""))
    else:
        src = "kit gate_result.json" if ev and ev.get("max_root_sinks") == n else "this block's latest synthesized design"
        g.add("FAIL", "clock_rule", f"{text} [{src}]", TL.CLOCK_RULE_FIX)
    return res


TEXTBOOK_FIX = {
    "clock_domain": "hardened sub-tiles with local roots and registered seams (kind cluster), <= ~15k sinks / 600 um a root",
    "high_fanout": "no reset on datapath registers; replicate enables / selects / pointer bits per region (<= ~256 loads)",
    "boundary": "register every boundary: pin flop in, flop out; never an ICG enable from a port",
    "logic_depth": "pipeline to ~700 ps a stage: trees, 2-3 rungs for wide compare / mux / arbitration",
    "wire_reach": "relay flops every <= 500 um, or move the logic next to its pins/macros",
    "util_channel": "size the outline to util 0.50-0.55 with >= 20 um macro channels",
    "reset_landing": "land every reset input at its face in 2 registered stages, then fan out at equal depth: kit "
                     "\"reset_landing\": {\"enable\": true} (ref_tile inserts rst_l0 -> rst_l1 at synthesis) or the RTL's own "
                     "rst_l0 / rst_l1 (one relay copy per region); reset release latency is a scheduled constant",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="kit dir (physical/ref_tile/<name>) or a tile spec json")
    ap.add_argument("--job", help="closure-loop job spec (default: the kit's job.json)")
    ap.add_argument("--commit", help="check source paths at this commit (default: working tree)")
    ap.add_argument("--remote", help="fleet host for the synthesis / floorplan / textbook run (auto: ot-run admission and placement)")
    ap.add_argument("--cts", action="store_true", help="with --remote: continue through CTS, report insertion + paths")
    ap.add_argument("--synth-cap", type=int, default=2700, help="synthesis time cap, s (default 2700; <=0 means unlimited)")
    ap.add_argument("--mem", type=int, default=24, help="ot-heavy GB (< 32 = small slot, no big-slot wait)")
    ap.add_argument("--disk", type=float, help="work/output disk reserve in GiB (spec gate_disk_gb, default 20); snapshot staging is added")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    g = Gate()
    job = json.loads(Path(a.job).read_text()) if a.job else None
    if job and "spec" in job and "stages" not in job:
        job = job["spec"]
    try:
        if a.target:
            t = Path(a.target)
            t = t if t.is_absolute() else (Path.cwd() / t)
            if t.is_file():
                r = RT.gen(str(t))
                kd = ROOT / r["kit"]
                print(f"GATE: kit regenerated -> {r['kit']}")
            else:
                kd = t
            if job is None and (kd / "job.json").exists():
                job = json.loads((kd / "job.json").read_text())
            spec = check_kit(g, kd, job, a.commit)
            if a.remote and g.verdict != "FAIL":
                remote(g, kd, spec, a.remote, a.synth_cap, a.mem, a.cts, a.disk)
            elif a.remote:
                g.add("INFO", "remote", "skipped: local FAIL first")
        elif job is not None:
            check_sources(g, job, (), a.commit or (job.get("source") or {}).get("commit"))
        else:
            ap.error("give a kit dir / spec, or --job")
    except RT.SpecError as ex:
        g.add("FAIL", "spec", str(ex), "fix the tile spec")
    g.print()
    if a.remote and getattr(g, "clock", None) and "kd" in locals():
        write_gate_result(g, kd, a.cts, a.remote)
    if a.json:
        destination = Path(a.json)
        canonical = kd / CLOCK_RESULT if "kd" in locals() else None
        # The canonical file carries immutable source and clock evidence. A
        # common --json <kit>/gate_result.json invocation must not immediately
        # replace that record with the short, unbound CLI report. Local-only
        # diagnostics must also leave an existing measured record intact.
        if canonical is None or destination.resolve() != canonical.resolve():
            destination.write_text(json.dumps({"verdict": g.verdict, "items": g.items}, indent=1) + "\n")
    return 1 if g.verdict == "FAIL" else 0


def write_gate_result(g: Gate, kd: Path, cts: bool, host: str):
    """Completion observes no HEAD: all provenance was frozen at shipping."""
    out = {"schema": "opentallas.ref_tile.gate_result.v2", "kit": kd.name, "verdict": g.verdict,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": getattr(g, "remote_host", host), "cts": bool(cts),
           "commit": g.source_binding.get("commit"), "source_binding": g.source_binding,
           "clock": g.clock, "items": [i for i in g.items if i["severity"] != "INFO"][:40]}
    if getattr(g, "trial_route", None):
        out["trial_route"] = g.trial_route      # a gate without this record predates the every-kit trial GRT
    if getattr(g, "port_latency", None):
        out["port_latency"] = g.port_latency
    if getattr(g, "reset_landing", None):
        out["reset_landing"] = g.reset_landing  # absent: the gate predates the reset_landing rule (ROOT-RST 10-19)
    previous = kd / CLOCK_RESULT
    if previous.exists():
        import hashlib
        old = previous.read_bytes()
        history = kd / "source_binding_history"
        history.mkdir(exist_ok=True)
        preserved = history / (hashlib.sha256(old).hexdigest() + ".json")
        try:
            original = json.loads(old)
        except ValueError:
            original = old.decode(errors="replace")
        preserved.write_text(json.dumps({"qualification_status": "unqualified_previous_source_binding",
                                         "original_result": original}, indent=1) + "\n")
        print(f"GATE: previous result preserved as unqualified evidence: {preserved}")
    previous.write_text(json.dumps(out, indent=1) + "\n")
    print(f"GATE: {kd.name}/{CLOCK_RESULT} written (exact staged source binding; commit it with the kit)")
    return out


def _materialise(repo: str, commit: str, kit: str, dst: Path) -> None:
    """extract the kit and everything its spec names (sources, views, contract) at the commit into dst"""
    def arch(paths):
        paths = [x for x in paths if subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{commit}:{x}"],
                                                    capture_output=True).returncode == 0]
        if not paths:
            return
        a = subprocess.run(["git", "-C", repo, "archive", commit, *paths], capture_output=True, timeout=120)
        subprocess.run(["tar", "-x", "-C", str(dst)], input=a.stdout, check=True)
    # canonical common_flow helpers ref_tile reads at ROOT (Q-XSLEAF 10-16: qfd_xs_leaf_w130-w1 gate went SKIP "literal pin
    # canonical placement helper is missing from the source archive"); filtered by existence at the commit, so harmless
    arch([kit, "physical/qwen_die_masters/io_ref_skew.sdc", OFLOP_TCL, RT.ASSIGNED_PIN_EXACT_TCL,
          getattr(RT, "M6_PIN_ACCESS_TCL", "physical/common_flow/m6_pin_access.tcl")])
    sp = json.loads((dst / kit / "spec.json").read_text())
    if sp.get("registered_cluster_candidate"):
        # gen_job ships the receipt and its hashed evidence; reproduce that closure during submit replay.
        candidate_job = json.loads((dst / kit / "job.json").read_text())
        arch(candidate_job.get("source", {}).get("extra_paths", []))
    # sdc_extra too: without it RT.gen raised FileNotFoundError and the whole gate went SKIP for every kit that has one
    arch(list(sp.get("sources", [])) + list(sp.get("sdc_extra", []))
         + [it["view"] for it in sp.get("macros", []) + sp.get("children", [])]
         + ([sp["contract"]["file"]] if sp.get("contract") else [])
         # job.benches_from too (flowfix 10-13): gen_job reads the shared bench template, and without it the whole gate
         # went SKIP "gate error FileNotFoundError" for every kit that has one (all s81hc_cry* / ctr* kits of 10-13)
         + ([sp["job"]["benches_from"]] if (sp.get("job") or {}).get("benches_from") else [])
         # cluster M8/M9 grant (VM6 10-14): ref_tile reads it at ROOT; without it every granted cluster (qfd_vm_rg* /
         # qfd_vm_band and their probes) was REFUSED "cluster layer grant source must be an existing repository file"
         + ([sp["cluster_layer_grant"]["source"]] if (sp.get("cluster_layer_grant") or {}).get("source") else [])
         # pin_hook_before_flops (claude s81-grpA r4, 10-14): ref_tile gen checks each hook exists at ROOT; without it
         # dsfd_vm_be_sl r5 (besl_xhold.tcl, committed at the source commit) was REFUSED "missing pin hook"
         + [x for x in sp.get("pin_hook_before_flops", []) if isinstance(x, str)]
         # pre_dpl_extra (Q-TILE45b 10-16): ref_tile gen checks each pre-DPL hook exists at ROOT exactly like the pin
         # hooks; without it qfd_tile_{nk,nl}_rp2_g4t (reconcile_sink_owners.tcl at the source commit) was REFUSED
         + [x for x in sp.get("pre_dpl_extra", []) if isinstance(x, str)]
         # boundary_tcl / pre_cts_extra (RH-DBKCPL 10-19): ref_tile gen reads each at ROOT; without them the submit check
         # of hv16_dbk_cpl (child_pocket_guard.tcl) went SKIP "gate error FileNotFoundError" -- binding never checked
         + [x for k in ("boundary_tcl", "pre_cts_extra") for x in sp.get(k, []) if isinstance(x, str)]
         # M6 pin-only grant (S-NET+FILL 10-15): ref_tile gen compares io_tcl / post_synth_tcl / orfs_vars .tcl/.sdc at
         # ROOT with the grant's source commit; without them every granted station was REFUSED "source differs"
         + [sp[k].removeprefix("/src/") for k in ("io_tcl", "post_synth_tcl") if isinstance(sp.get(k), str)]
         + [v.removeprefix("/src/") for v in (sp.get("orfs_vars") or {}).values()
            if isinstance(v, str) and v.endswith((".tcl", ".sdc"))])


def check_slot_fit(g: Gate, kd: Path, job: dict, repo: str, commit: str = "") -> dict | None:
    """SLOT FIT (owner 2026-10-13, tools/hier_contract/slot_fit.py): a tile with a slot in a die contract must fit it
    BEFORE it routes -- outline, pin faces, pin layers, layer cap and the estimated clock insertion against the LIVE
    contract (origin/main of the repo's object store, else main, the job's commit, the working tree).  A mismatch FAILs (REFUSED at submit) unless the
    spec carries "slot_change_request": "<die lead log line or contract version>": then it is a WARN and the request is
    appended to the die lead's log."""
    import slot_fit
    cs, ref = slot_fit.live_contracts(Path(repo), commit)
    res = slot_fit.check(kd, Path(repo), job, cs)
    if res["status"] == "no_slot":
        return res
    where = f"slot {res['slot']} of {res['contract']} v{res['version']} ({ref})"
    for n in res["notes"]:
        g.add("INFO", "slot_fit", f"{where}: {n}")
    if res["status"] == "fit":
        g.add("INFO", "slot_fit", f"{res['top']} fits {where}")
        return res
    msg = f"{res['top']} does not fit {where}: " + "; ".join(res["mismatches"])
    req = res.get("slot_change_request")
    if req:
        log = slot_fit.append_request(res, str(job.get("name", res["kit"])), commit)
        g.add("WARN", "slot_fit", f"{msg} -- routes on slot_change_request {str(req)[:160]!r}"
              + (f" (appended to {log.name})" if log else " (no die lead log for this die: tell the lead)"))
    else:
        g.add("FAIL", "slot_fit", msg, "build the tile to its slot, or get the slot changed by the die lead and put "
              "\"slot_change_request\": \"<die lead log line or contract version>\" in the spec (check before submit: "
              "tools/hier_contract/slot_fit.py KIT_DIR)")
    return res


CLOCK_WAIVER_MAX_PS = TL.CLOCK_WAIVER_MAX_PS


def apply_clock_rule_waiver(g: Gate, spec: dict) -> None:
    """HANDOFF 0ga 2026-10-18: the job spec's "clock_rule_waiver" turns the clock_rule FAIL into a WARN that prints the
    waiver when textbook_lint.clock_waiver_eval accepts it (per-pair excess <= 2 ps, recorded, named pair alone)."""
    w = spec.get("clock_rule_waiver")
    items = [i for i in g.items if i["check"] == "clock_rule" and i["severity"] == "FAIL"]
    if not isinstance(w, dict) or not items:
        return
    applied, note, why = TL.clock_waiver_eval((getattr(g, "clock", None) or {}).get("evidence") or {}, w)
    if not applied:
        for i in items:
            i["message"] += f" (clock_rule_waiver NOT applied: {'; '.join(why)})"
        return
    print(f"pre_route_gate: WAIVER {note}", file=sys.stderr)
    for i in items:
        i["severity"], i["message"] = "WARN", i["message"] + f" -- WAIVED: {note}"


def submit_check(spec: dict, repo: str | None = None, known_sinks: int | None = None,
                 closed_stands: bool = False, clock_mode: str = "refuse") -> dict:
    """closure-loop submit hook: the LOCAL gate on a job spec AT ITS SOURCE COMMIT (kit / pins / RTL / children /
    source-sync for "ref_tile": true; source-sync only for any other job).  {"verdict": PASS|WARN|REFUSE|SKIP, "message"}.
    Never raises."""
    global ROOT
    import tempfile
    repo = repo or str(ROOT)
    g = Gate()
    old = (ROOT, RT.ROOT, RT.GIT_ROOT)
    try:
        RT.GIT_ROOT = Path(repo)   # the materialised kit tree is not a git repo (M6 pin-grant source commit lookup)
        commit = str((spec.get("source") or {}).get("commit", ""))
        with tempfile.TemporaryDirectory() as td:
            if spec.get("ref_tile"):
                m = re.search(r"ref_route\.sh\s+(\S+)/kit\.env", spec["stages"]["route"]["cmd"])
                if not m:
                    g.add("FAIL", "job", "ref_tile job without a tools/ref_tile/ref_route.sh <kit>/kit.env route")
                else:
                    kit = m.group(1)
                    _materialise(repo, commit, kit, Path(td))
                    if not (Path(td) / kit / "kit.env").exists():
                        g.add("FAIL", "kit", f"{kit}/kit.env missing at {commit}", "commit the generated kit")
                    else:
                        ROOT = RT.ROOT = Path(td)
                        check_kit(g, Path(td) / kit, None)
                        ROOT = RT.ROOT = Path(repo)
                        if spec.get("auto_react_parent"):
                            # a loop successor (-arh / -arg / -hs) re-routes a kit whose parent already placed its pins
                            # and reached the router: the flowfix estimates never stop it
                            for i in g.items:
                                if i["check"] in ("pin_fit", "oflop") and i["severity"] == "FAIL":
                                    i["severity"] = "WARN"
                                    i["message"] += f" (loop successor of {spec['auto_react_parent']}: not refused)"
                        check_sources(g, spec, json.loads((Path(td) / kit / "floorplan.json").read_text())
                                      .get("referenced", []), commit)
                        check_slot_fit(g, Path(td) / kit, spec, repo, commit)
                        if clock_mode != "off":
                            check_clock_evidence(g, Path(td) / kit, known_sinks, closed_stands, commit)
                            apply_clock_rule_waiver(g, spec)
                            if clock_mode != "refuse":
                                for i in g.items:
                                    if i["check"] == "clock_rule" and i["severity"] == "FAIL":
                                        i["severity"] = "WARN"
            else:
                ROOT = RT.ROOT = Path(repo)
                check_sources(g, spec, (), commit)
    except Exception as ex:  # noqa: BLE001
        return {"verdict": "SKIP", "message": f"gate error {type(ex).__name__}: {str(ex)[:200]}"}
    finally:
        ROOT, RT.ROOT, RT.GIT_ROOT = old
    fails = [i for i in g.items if i["severity"] == "FAIL"]
    warns = [i for i in g.items if i["severity"] == "WARN"]
    msg = " | ".join(f"{i['check']}: {i['message']}" + (f" (fix: {i['fix']})" if i["fix"] else "")
                     for i in (fails or warns))[:1500]
    return {"verdict": "REFUSE" if fails else ("WARN" if warns else "PASS"), "message": msg or "pre-route gate PASS",
            "clock": getattr(g, "clock", None), "route_overlay_plan": getattr(g, "route_overlay_plan", None),
            "relaxing_rule_allowlist": getattr(g, "relaxing_rule_allowlist", None)}

if __name__ == "__main__":
    sys.exit(main())
