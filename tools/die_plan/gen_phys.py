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
import json
import math
import re
import shutil
from pathlib import Path

import schema as S
import taps as T
from schema import DIE_PART

CORE_MARGIN_UM = 4.32        # multiple of row 0.27 and site 0.054
IO_BUDGET = 0.2
PIN_LEN_UM = 0.192
LAYER_W = dict(M2=0.018, M3=0.018, M4=0.024, M5=0.024, M6=0.032, M7=0.032, M8=0.04, M9=0.04)


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
    for p in c.get("pins", []):
        if p["name"] not in edge_in:
            add(p["name"], p["layer"], *p["xy_um"])
    for port, i, ln, cx, cy, pw, ph in bump_sites:
        add(f"{port}[{i}]", ln, cx, cy)
    for name, ln, x, y in strap_pin_sites(P, tn):
        add(name, ln, x, y)
    return list(recs.values())


def port_bind_pin_records(P, tn, pins, bump_ports=None):
    """Exact top-level inventory, including physically declared landing and constant pins."""
    t = P.types[tn]
    port_pins = [dict(bus=b, bit=i) for b, i, _l, _x, _y, _f in pins]
    port_pins += [dict(bus=n, bit=None) for n, _x, _y in tap_pins(P, tn) + reset_out_pins(P, tn)]
    port_pins += [dict(bus=b["port"], bit=i) for b in (bump_ports or []) for i in range(b["width"])]
    import infra_rtl as IR
    port_pins += [dict(bus=p["name"], bit=None) for p in IR.type_ports(t)]
    port_pins += [dict(bus=p["name"], bit=None)
                  for p in t.get("clock", {}).get("landing_contract", {}).get("pins", [])]
    port_pins += [dict(zip(("bus", "bit"), _pin_bus_bit(n))) for n, _l, _x, _y in strap_pin_sites(P, tn)]
    # Forwarded input clocks may also be listed in edge_clocks: same real pin.
    return list({(p["bus"], p["bit"]): p for p in port_pins}.values())


def write_partition_freeze(P, tn, kd, recs):
    """plan_pins.json (die-plan pin centres) + freeze.json (schema partition_freeze: outline, pins_file, pins_sha256,
    pins_canon_sha256 of the die-plan pins) for kit_contract.pins_canonical; refuses the kit when io.tcl is not that
    pin set with the consumed master-plan slice applied (kit_contract.slice_expected)."""
    import hashlib
    import kit_contract as KC
    kd = Path(kd)
    w, h = P.types[tn]["outline_um"]
    body = json.dumps(dict(schema="opentallas.die_plan.partition_plan_pins.v1", die=P.name, type=tn,
                           source="gen_phys.plan_pin_records (die plan)", pins=recs), indent=1) + "\n"
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
                     f"-pin_size {{{LAYER_W.get(top, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: die spine tap")
    for name, x, y in reset_out_pins(P, tn):
        lines.append(f"place_pin -pin_name {name} -layer {top} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(top, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: reset wavefront out")
    for name, ln, x, y in strap_pin_sites(P, tn):
        lines.append(f"place_pin -pin_name {{{name}}} -layer {ln} -location {{{x:.4f} {y:.4f}}} "
                     f"-pin_size {{{LAYER_W.get(ln, 0.04):.4f} {4 * PIN_LEN_UM:.4f}}}   ;# interior: ID strap (tied at die top)")
    if t.get("clock", {}).get("landing_contract"):
        import landing_contract as LC
        lines.append(LC.io_tcl(P, tn).rstrip())
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
    """CP2 early core taps of a type (schema.core_taps; clock.core_taps 'early'), snapped: [(port, x, y)]."""
    return [(n,) + _snap_tap(P, x, y, pg_legal=not P.types[tn].get("hard")) for n, x, y, _ in S.core_taps(P, tn)]


def core_tap_rows(P, tn, corner="TT", pending=None):
    """[(port, core inst, clock pin or '*', early_ps, insertion_ps)] of the type's early core taps: a tap named
    `<inst>` takes every clock pin of that core, `<inst>.<pin>` one pin.  A merged tap on a core with no native view
    (HBM-STREETS-3, COORD 10-27 19:12 ruling 1) keeps its plan clock pins and is appended to `pending` (PENDING-VIEW)."""
    insts = [c["inst"] for c in P.types[tn].get("hard_cores", []) or []]
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
            raise ValueError(f"type {tn}: core tap {nm} names no hard_cores[] inst")
        if tp.get("merged_clock_ports"):
            import merged_core_clocks as MC
            for pin in MC.pins_or_pending(P, tn, tp, hit[0], pending):
                out.append((n, hit[0], pin, S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner)))
        else:
            out.append((n, hit[0], hit[1], S.core_tap_early_ps(P, tp, corner), S.core_tap_insertion_ps(tp, corner)))
    return out



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
    if lines and tap_window_ps(P):
        lines.append(f"# plan clock.tap_window {tap_window_ps(P):g} ps on the FF core taps (early end only)\n"
                     + core_tap_window_tcl(P, tn, "FF"))
    return "".join(lines)


def edge_clock_pins(P, tn):
    """[(port, x, y, period_mult)]: the type's PHY-edge clocks (schema clock.edge_clocks), snapped like taps."""
    return [(e["port"],) + _snap_tap(P, *e["tap_um"]) + (int(e.get("period_mult", 1)),)
            for e in P.types[tn].get("clock", {}).get("edge_clocks", [])]


# DIE-HEAD-21 (opt-in plan clock.edge_clocks[].source_latency_ps): a source-forwarded edge clock (count-aligned ring
# write clock) reaches its port at the SENDER's export arrival + wire, not at 0 while its data inputs are timed on the
# vclk insertion (DH19: 2272 ring writers -130.6 ps at source latency 0).  The measured range is a source latency on
# the edge clock: -early = min arrival (OpenSTA/PT use the early source latency for the CAPTURE clock of setup checks
# and the launch of holds), -late = max arrival (capture of holds, launch of setups), so one SDC is pessimistic for
# both checks within a corner.  The corner itself cannot share one SDC (same reason as the vclk, ruling 9.7): TT goes
# into constraint.sdc, FF into the core_taps_ff.sdc corner overlay (OT_CORE_TAP_CORNER_FILE, read by vclk_corner.tcl
# ff / postcts FF gate / sign-off FF; vclk_corner.tcl tt re-applies the constraint.sdc lines).  Absent: no line.
def edge_clock_latency(P, tn):
    """[(port, {"tt": (early, late), "ff": (early, late)}, basis)] for the type's edge clocks with source_latency_ps."""
    out = []
    for e in P.types[tn].get("clock", {}).get("edge_clocks", []):
        sl = e.get("source_latency_ps")
        if sl is None:
            continue
        if tap_window_ps(P):      # the window's port-level -early/-late lines would override the clock-level arrival
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


def tap_pins(P, tn):
    """[(port, x, y)]: every clock tap (+ early core taps) + the reset tap (+ PHY-edge clock pins)."""
    import reset_tree as RT
    if RT.wavefront(P) and not P.types[tn].get("hard"):     # OWNER DECISION 13: the wavefront reset IN site
        rs = tuple(RT.in_pin(P, tn))
    else:
        rs = tuple(tap_points(P, tn)[1])
    st = [("start_i",) + tuple(RT.start_in_pin(P, tn))] if RT.start_broadcast(P) and not P.types[tn].get("hard") else []
    return clock_pins(P, tn) + core_tap_pins(P, tn) + [("arst_n",) + rs] + st + [e[:3] for e in edge_clock_pins(P, tn)]


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
    if not dec:
        return []
    kj = Path(kit_rtl_filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        raise gen_rtl.GenError(f"type {tn}: declares bump_ports but kit-rtl {kj} is missing (bound port names unknown)")
    kr = json.loads(kj.read_text())
    rep_f = Path(kr["bind_out"]) / "bind_report.json"
    if not rep_f.is_file():
        raise gen_rtl.GenError(f"type {tn}: declares bump_ports but {rep_f} is missing")
    rep = json.loads(rep_f.read_text())
    insts = set(kr.get("instances") or [])
    bound = {}
    for b in rep.get("bump_ports", []):
        if b["partition"] not in insts:
            continue
        k = (b["pin"], b["dir"], int(b["width"]))
        if bound.setdefault(k, b["part_port"]) != b["part_port"]:
            raise gen_rtl.GenError(f"type {tn}: bump {b['pin']} bound under two port names "
                                   f"{bound[k]} / {b['part_port']} across instances")
    want = {(pin, d, w): (inst, mod) for inst, mod, pin, d, w in dec}
    if set(want) != set(bound):
        raise gen_rtl.GenError(f"type {tn}: plan bump_ports {sorted(set(want) - set(bound))[:4]} not bound / bound "
                               f"{sorted(set(bound) - set(want))[:4]} not declared ({rep_f})")
    bop = {b["port"]: (b["dir"], int(b["width"])) for b in kr.get("bound_only_pins", [])}
    out = []
    for (pin, d, w), port in sorted(bound.items(), key=lambda kv: kv[1]):
        if bop.get(port) != (d, w):
            raise gen_rtl.GenError(f"type {tn}: bump port {port} ({d} {w}) is not a bound-only pin of the kit-rtl "
                                   f"wrapper ({bop.get(port)})")
        inst, mod = want[(pin, d, w)]
        out.append(dict(port=port, inst=inst, module=mod, pin=pin, dir=d, width=w))
    return out


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
            cache[lef] = _lef_macro_pins(Path(base) / lef, mod)
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
    if not t.get("pg_island_cut"):
        return []
    import cores as C
    cuts = []
    for inst, _mod, lef, _lib, ox, oy, o in type_macros(P, tn):
        pins, (w, h) = lef_interior_pins(C.resolve(lef, root))
        for pin, r in pins:
            x0, y0, x1, y1 = _orient_rect_r(r, w, h, o)
            cuts.append((inst, pin, (round(x0 + ox - PG_CUT_MARGIN_UM, 4), round(y0 + oy - PG_CUT_SPACE_UM, 4),
                                     round(x1 + ox + PG_CUT_MARGIN_UM, 4), round(y1 + oy + PG_CUT_SPACE_UM, 4))))
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
UNC_SETUP_PS, UNC_HOLD_PS, IO_LOAD_FF = 60.0, 25.0, 2.0


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
def tap_window_ps(P):
    """the plan's declared per-tap latency window W (ps) of the kit SDC, 0.0 when absent (legacy kits unchanged)."""
    tw = P.clock.get("tap_window")
    if not tw:
        return 0.0
    w = float(tw["window_ps"])
    per = float(P.die["period_ps"]) if hasattr(P, "die") else float("inf")
    if not 0 <= w <= per / 4:
        raise ValueError(f"clock.tap_window.window_ps {w:g} outside [0, T/4]")
    if not P.clock.get("seam_hold"):
        raise ValueError("clock.tap_window needs clock.seam_hold (COORD 11:24: one declared window for intra AND seam)")
    return w


def tap_window_tcl(P, tn, value_ps=None, core=True):
    """the window's two set_clock_latency lines on the grid tap ports of type tn ('' without a window), then (core)
    the early-core-tap window lines (core_tap_window_tcl, TT).  value_ps overrides the early value (0 = the pre-CTS
    ideal stage).  core=False: grid / edge ports only (the golden SDC writes the core lines after the core taps' own
    source latency, which would otherwise overwrite them)."""
    w = tap_window_ps(P)
    if not w:
        return ""
    e = (-w if value_ps is None else -float(value_ps)) + 0.0     # never "-0.0000"
    out = ""
    for ck, ports in tap_window_ports(P, tn):
        out += (f"set_clock_latency -source -early -clock {ck} {t_lib(e):.4f} [get_ports {{{' '.join(ports)}}}]\n"
                f"set_clock_latency -source -late -clock {ck} {t_lib(0.0):.4f} [get_ports {{{' '.join(ports)}}}]\n")
    return out + (core_tap_window_tcl(P, tn, value_ps=value_ps) if core else "")


def core_tap_window_tcl(P, tn, corner="TT", value_ps=None):
    """early-core-tap window lines of type tn at corner ('' without a window or core taps): one line per core tap
    port, set_clock_latency -source -early -clock clk -(early + W) [get_ports tap], written AFTER the port's own
    -source -clock clk -early line (which sets both early and late), so late keeps the core's own early latency and
    only the early end widens by W.  value_ps overrides W (0 = the pre-CTS ideal stage: early back to the tap's own)."""
    w = tap_window_ps(P)
    if not w:
        return ""
    v = w if value_ps is None else float(value_ps)
    out, seen = "", set()
    for n, _inst, _pin, early, _ins in core_tap_rows(P, tn, corner):
        if n in seen:
            continue
        seen.add(n)
        out += f"set_clock_latency -source -early -clock clk {t_lib(-(early + v)) + 0.0:.4f} [get_ports {n}]\n"
    return out


def tap_window_ports(P, tn):
    """[(clock, [ports])] the window applies to: every real clock source port of the type (the grid taps of clk and
    each PHY-edge clock port), so every input / output path sees the same early range and the IO shift stays exact."""
    return ([("clk", [n for n, _x, _y in clock_pins(P, tn)])] +
            [(n, [n]) for n, _x, _y, _m in edge_clock_pins(P, tn)])


def tap_window_io_shift(P):
    """(input max delay shift, output min delay shift) in ps that keep the IO contract exact under the window."""
    w = tap_window_ps(P)
    return -w, w


def hold_out_min_sdc_ps(P, tn=None):
    """the output min delay WRITTEN in the kit SDC / gate / sign-off overlay: contract hold_out_min_ps + window."""
    return hold_out_min_ps(P, tn) + tap_window_io_shift(P)[1]


def hold_in_min_ps(P):
    """seam-hold padding: the kit's min input delay vs vclk (ps)."""
    return seam_hold(P)["in_min_ps"]


def hold_out_min_ps(P, tn=None):
    """Contract output-min, tightened by the type's own checked sender guarantee."""
    base = seam_hold(P)["out_min_ps"]
    guarantee = out_hold_check_ps(P, tn) if tn is not None else None
    return base if guarantee is None else min(base, (1 - UNC_SPLIT) * UNC_HOLD_PS - guarantee)


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
    return (1 - UNC_SPLIT) * UNC_HOLD_PS - hold_out_min_ps(P), "plan contract"


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
HOLD_FF_MARGIN_DEFAULT = 5.0
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


def sdc(P, tn, pins):
    """kit SDC.  Bus ports: IO_BUDGET x T each side (both ends register at the face).  ft slot ports (COORD 10-23 R3,
    hop share): the last station drives its out port over the slot's last L/k segment, so the out port keeps only the
    neighbour's face share (output delay FT_HOP_IN_SHARE x T) and the in port arrives after the upstream partition's
    last segment (input delay (1 - FT_HOP_IN_SHARE) x T) into this side's face-registered station 0."""
    per = t_lib(P.die["period_ps"])
    ib = insertion_binding(P, tn)
    lat = t_lib(ib["tt"])
    io = IO_BUDGET * per
    tw_in, _tw_out = tap_window_io_shift(P)
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
           + (f"# plan clock.tap_window (COORD 11:24): die tap-to-tap arrival window {tap_window_ps(P):g} ps on every "
              "real clock port, [-W, 0]; IO delays shifted to keep the seam contract (gen_phys.tap_window_ps)\n"
              + tap_window_tcl(P, tn, core=False) if tap_window_ps(P) else "") +
           f"set_clock_uncertainty {t_lib(UNC_SETUP_PS):.4f} -setup [all_clocks]\n"
           f"set_clock_uncertainty {t_lib(UNC_HOLD_PS):.4f} -hold [all_clocks]\n"
           f"# seam paths: uncertainty counted once per seam (COORD 16:58): {UNC_SPLIT:g} on each partition side\n"
           f"set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup {t_lib(UNC_SPLIT * UNC_SETUP_PS):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup {t_lib((1 - UNC_SPLIT) * UNC_SETUP_PS):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold {t_lib(UNC_SPLIT * UNC_HOLD_PS):.4f}\n"
           f"set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold {t_lib((1 - UNC_SPLIT) * UNC_HOLD_PS):.4f}\n"
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
    if source_ports and tap_window_ps(P):
        out += (f"# plan clock.tap_window {tap_window_ps(P):g} ps on the early core taps: early end -(early + W), "
                "late keeps the tap's own early latency\n" + core_tap_window_tcl(P, tn))
    if slots:
        sh = ft_hop_in_share(P)
        out += (f"# ft slots: hop share {sh:g} T at the face, the rest is the last station segment\n"
                f"set_input_delay -max {(1 - sh) * per + t_lib(tw_in):.4f} -clock vclk [get_ports {{{ft_in}}}]\n"
                f"set_output_delay -max {sh * per:.4f} -clock vclk [get_ports {{{ft_out}}}]\n")
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
        out += ROOT_RESET_FALSE_PATH + "\n"
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
    if P.types[tn].get("clock", {}).get("landing_contract"):
        import landing_contract as LC
        out = LC.sdc(P, tn, out)
    return out




def type_macros(P, tn):
    """content macros of a type the kit must place (COORD 10-23): hard_cores[] and contents[] that carry a hardened
    view (lef).  [(inst, module, lef, lib, x, y, orient)], type frame, origin + track offset.  A macro view without a
    placement is an error: G3 of a kit whose SRAM / ROM / cores float is meaningless."""
    t = P.types[tn]
    out = []
    for c in t.get("hard_cores", []):
        if not c.get("lef"):
            continue
        ox, oy = c.get("track_offset_um", [0.0, 0.0])
        out.append((c["inst"], c.get("module", c["inst"]), c["lef"], c.get("lib"), c["origin_um"][0] + ox,
                    c["origin_um"][1] + oy, c.get("orient", "R0")))
    cores = {c["inst"] for c in t.get("hard_cores", [])}
    for c in t.get("contents", []):
        if not c.get("lef") or c["inst"] in cores:
            continue
        if "origin_um" not in c:
            raise ValueError(f"type {tn}: macro content {c['inst']} ({c['module']}) has a lef but no origin_um")
        out.append((c["inst"], c["module"], c["lef"], c.get("lib"), c["origin_um"][0], c["origin_um"][1],
                    c.get("orient", "R0")))
    return out


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
            rt = [round(min(u[0], v[0]), 4), round(min(u[1], v[1]), 4), round(max(u[0], v[0]), 4),
                  round(max(u[1], v[1]), 4)]
            mac = []
            for c in t.get("contents", []) + t.get("hard_cores", []):
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
                mac.append(c["inst"])
            if not mac and not t.get("phy_pg_offmodel"):
                raise ValueError(f"type {tn}: PG domain {d['name']} holds no macro (a PHY domain powers its PHY macro)")
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


def macro_pg_pin_layers(lef):
    """{'VDD': {layers}, 'VSS': {layers}} of a macro LEF (PIN VDD / PIN VSS PORT geometry; missing pin -> empty)."""
    text = Path(lef).read_text(errors="replace")
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


def core_pg_grids(P, tn, macros, root=None, exclude=()):
    """pdn.tcl lines of an opt-in type (core_pg_connect): one CORE macro grid per PG pin layer over the type's placed
    macros (hard_cores + hardened contents, minus `exclude` = PHY-domain macros), add_pdn_connect pin layer -> tile
    strap layer.  [] when not opted in or the type places no macro."""
    if not P.types[tn].get("core_pg_connect"):
        return []
    import cores as C
    groups = {}
    for inst, _mod, lef, *_ in macros:
        if inst in exclude:
            continue
        groups.setdefault(core_pg_connect_layer(C.resolve(lef, root)), []).append(inst)
    t = []
    for (lo, hi), insts in sorted(groups.items(), key=lambda kv: int(kv[0][0][1:])):
        g = f"core_pg_{lo}"
        t += [f"# PG-CORECONN-1 (core_pg_connect): {len(insts)} placed macro(s) with {lo} PG pins onto the tile {hi} straps",
              f"define_pdn_grid -macro -name {{{g}}} -instances {{{_pdn_inst_patterns(insts)}}} -voltage_domains {{CORE}} -halo {{0}}",
              f"add_pdn_connect -grid {{{g}}} -layers {{{lo} {hi}}}"]
    return t


def core_pg_unconnected(pdn, macros, root=None, exclude=()):
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
        lo, hi = core_pg_connect_layer(C.resolve(lef, root))
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
    phy_layers = {m[0]: _macro_pg_layers(root / m[2]) for m in macros if m[0] in phy_insts}
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


def core_mean_contract_options(P, tn, trial=False):
    """COORD 10-28 03:35: explicit parent budgets may drive non-release probes.

    Existing plans keep their legacy path. Parent-budget early taps opt into the
    selected view's explicit TT/FF contract only in a --trial kit; they cannot
    qualify release kits. The contract reader still rejects ETM extrema as means.
    """
    if signed_mean_core_taps(P, tn):
        return dict(mean_contract=True, require_signed=True)
    ck = P.types[tn].get("clock", {}) or {}
    if ck.get("core_taps") == "internal":
        import core_clock_contract as CC
        raise CC.ContractError(f"{tn}: internal core CTS requires explicit SIGNED TT/FF mean metadata")
    taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
    budget = bool(ck.get("core_taps") == "early" and taps and P.types[tn].get("hard_cores")
                  and all("insertion_ff_ps" in tp and
                          str(tp.get("budget_owner", "")).startswith(("SIGNED", "parent_budget"))
                          for tp in taps)
                  and any(str(tp.get("budget_owner", "")).startswith("parent_budget") for tp in taps))
    if budget:
        if not trial:
            import core_clock_contract as CC
            raise CC.ContractError(f"{tn}: parent_budget mean core taps require a non-release --trial kit; release requires SIGNED")
        return dict(mean_contract=True, require_signed=False)
    return dict(mean_contract=False, require_signed=True)


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
    pending_view = []
    taps = core_tap_rows(P, tn, pending=pending_view)
    if pending_view:   # HBM-STREETS-3: PENDING-VIEW cores are reported, never PASS; retap when the signed view lands
        (kd / "merged_clock_pending_view.json").write_text(json.dumps(dict(
            type=tn, status="PENDING-VIEW", rule="COORD 10-27 19:12 HBM-STREETS-2 ruling 1", rows=pending_view),
            indent=1) + "\n")
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
                   + tap_window_tcl(P, tn) if tap_window_ps(P) else "") +
                "source /work/clock_taps.tcl\n")
    return ("# Pre-CTS ideal LOCAL tree insertion, matching the virtual neighbour clock budget.\n"
            "# Stage-only: pre_cts.tcl removes it before tree construction. Golden SDC stays unchanged.\n"
            f"set_clock_latency -clock clk {t_lib(P.clock['insertion_ps']):.4f} [get_ports {{{ports}}}]\n"
            + ("# plan clock.tap_window: ideal clocks get no CRPR, so the window is zeroed until pre_cts.tcl\n"
               + tap_window_tcl(P, tn, value_ps=0.0) if tap_window_ps(P) else ""))



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

KEEP_REGS_HOOK = ("ot_keep_regs.tcl", "ot_pin_regs.tcl", "pin_reg_split.tcl", "ot_rst_copies.tcl", "ot_rst_copies.py")


_INCLUDE = re.compile(r'^[ \t]*`include[ \t]+"([^"]+)"', re.M)


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


def write_type_kit(P, tn, out, rtl_files, util=0.5, proof=False, root=None, hold_ff_margin=None, margins=None,
                   skip_ir=False, max_wire_um=None, rc_cal=True, master_slice=None, trial=False,
                   bump_ports=None, gpl_plain=False, land_slots=None):
    """land_slots (opt-in, DIE-HEAD-21): face_guard declaration {"schema", "buses": {bus: {D, form}}} written as
    kit land_slots.json beside pins.json (clock_landings.Landings.land_slots); None: no file (byte-identical kits)."""
    t = P.types[tn]
    if gpl_plain and not t.get("ft_slots"):
        raise ValueError(f"type {tn}: --gpl-plain is for pure-FT corridor kits; the type has no ft_slots")
    import core_clock_groups as CG
    grouped = CG.network_manifest(P, tn)  # reject incomplete endpoint/network data before writing a kit
    ib = insertion_binding(P, tn)
    w, h = t["outline_um"]
    macros = type_macros(P, tn)
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
    mlef, mlib, mplace = [], [], ["# GENERATED by tools/die_plan/gen.py phys: content macros at their plan sites."]
    if macros:
        (kd / "macros").mkdir(exist_ok=True)
        base = Path(root) if root else Path(__file__).resolve().parent.parent.parent
        for inst, mod, lef, lib, x, y, o in macros:
            for src, lst in ((lef, mlef), (lib, mlib)):
                if src:
                    f = base / src         # an absolute view path (pair.py --core-views) stays as is
                    if not f.is_file():
                        raise FileNotFoundError(f"type {tn}: macro {inst} view {f} missing")
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
            mplace.append(f"place_macro -macro_name {{{inst_db}}} -location {{{x:.4f} {y:.4f}}} -orientation {o} -exact")
    srcs = []
    for f in rtl_files:
        dst = kd / "rtl" / Path(f).name
        if Path(f).resolve() != dst.resolve():
            shutil.copyfile(f, dst)
        srcs.append(f"/work/rtl/{Path(f).name}")
    stage_includes(rtl_files, kd / "rtl")
    pins = type_pins(P, tn)
    bump_sites = bump_pin_sites(P, tn, bump_ports, macros, Path(root) if root else Path(__file__).resolve().parent.parent.parent) \
        if bump_ports else []
    io_text = io_tcl(P, tn, pins)
    for port, i, ln, cx, cy, pw, ph in bump_sites:
        io_text += (f"place_pin -pin_name {{{port}[{i}]}} -layer {ln} -location {{{cx:.4f} {cy:.4f}}} "
                    f"-pin_size {{{pw:.4f} {ph:.4f}}}   ;# interior: hard-IP line side (bump) on the macro pin\n")
    (kd / "io.tcl").write_text(io_text)
    top = P.type_top_layer(tn)
    pdn = PDN
    if int(top[1:]) > int(P.layer_budget["partition_signal_max"][1:]):
        # face_layers raised this type to M8: keep its own M8 wiring off the die M8 PG bands (schema.PART_PG_BANDS),
        # so the die grid's M8 stripes run over the partition without shorts
        obs = ["", "set blk [ord::get_db_block]", "set dbu [$blk getDbUnitsPerMicron]"]
        smax = int(P.layer_budget["partition_signal_max"][1:])
        for li in range(smax + 1, int(top[1:]) + 1):
            ln = f"M{li}"
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
    phy_doms = phy_pg_domains(P, tn)
    if phy_doms:
        # PATH-KV-SYSC 10-25 PHY PG hook: separate VDDPHY region(s) of die.pg.domains inside this type
        pdn = phy_pg_pdn(P, tn, phy_doms, macros, root=root,
                         core_grids=bool(P.types[tn].get("core_pg_connect"))) + pdn[len(PDN):]
        (kd / "phy_pg.json").write_text(json.dumps([dict(name=d[0], power=d[1], ground=d[2], rect_type_um=d[3],
                                                          macros=d[4]) for d in phy_doms], indent=1) + "\n")
    elif P.types[tn].get("core_pg_connect"):
        cg = core_pg_grids(P, tn, macros, root)
        if cg:
            pdn += "\n".join(cg) + "\n"
    if P.types[tn].get("core_pg_connect"):
        bad = core_pg_unconnected(pdn, macros, root, exclude={i for d in phy_doms for i in d[4]})
        if bad:
            raise ValueError(f"type {tn}: core_pg_connect leaves macro PG pins unconnected: {bad[:4]}")
    (kd / "pdn.tcl").write_text(pdn)
    pg_cuts = pg_island_cuts(P, tn, root)
    if pg_cuts:
        (kd / "pg_island_cut.tcl").write_text(pg_island_cut_tcl(pg_cuts))
    (kd / "make_tracks.tcl").write_text(make_tracks_tcl(P))
    (kd / "constraint.sdc").write_text(sdc(P, tn, pins))
    if core_tap_rows(P, tn) or edge_clock_latency(P, tn):
        (kd / "core_taps_ff.sdc").write_text(core_tap_ff_sdc(P, tn) + edge_clock_latency_tcl(P, tn, "ff"))
    ioh = io_hold_tcl(P, tn)            # IO-HOLD option A: per-port min input delays for the hold_gate / sign-off overlays
    if ioh:
        (kd / "io_hold.tcl").write_text(ioh)
    (kd / "prects_estimate.tcl").write_text(clock_phase_tcl(P, tn))
    import reset_tree as RT
    leaf_check = ""
    if RT.pipelined(P) or RT.wavefront(P):
        leaf_check = (f"\nset rt_postplace 1\nset rt_leaf_reach_um {RT.relay_um(P):g}\n"
                      "source /work/reset_taps.tcl\nunset rt_postplace\n")
    group_hook = ""
    if grouped["groups"]:
        (kd / "core_clock_groups.json").write_text(json.dumps(grouped, indent=1) + "\n")
        (kd / "core_clock_groups_apply.tcl").write_text(CG.tcl_text(grouped))
        shutil.copyfile(Path(__file__).resolve().parents[2] / "physical/common_flow/core_clock_groups.tcl",
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
    (kd / "pre_cts.tcl").write_text(clock_phase_tcl(P, tn, before_cts=True) + leaf_check + group_hook + rsp_hook)
    # CP1-R10 / COORD 10-24: fail-closed SDC lint at kit generation (units, clocks, max+min IO delays, hold,
    # 60/25 uncertainty once per seam, no relaxed periods / exceptions); run_kit.sh re-runs it with the image liberty
    import sdc_lint
    lctx = sdc_lint.kit_context(P, tn)
    (kd / "sdc_lint.json").write_text(json.dumps(lctx, indent=1) + "\n")
    shutil.copyfile(Path(__file__).with_name("sdc_lint.py"), kd / "sdc_lint.py")
    shutil.copyfile(Path(__file__).with_name("rtl_lint.py"), kd / "rtl_lint.py")
    lerr = sdc_lint.lint((kd / "constraint.sdc").read_text(), **lctx)
    if lerr:
        raise sdc_lint.SdcLintError(f"type {tn}: constraint.sdc fails sdc_lint ({len(lerr)}): " + "; ".join(lerr[:8]))
    clat = core_latency_files(P, tn, kd, root, **core_mean_contract_options(P, tn, trial=trial))
    m = CORE_MARGIN_UM
    forest = any(Path(f).name == "ot_pl_land_reset_forest.sv" for f in srcs)
    cfg = [f"# GENERATED by tools/die_plan/gen.py phys: partition type {tn} of die_plan {P.name}. Do not edit.",
           f"export DESIGN_NICKNAME = dp_{tn}",
           f"export DESIGN_NAME = {t['module']}",
           "export PLATFORM = asap7",
           "export VERILOG_FILES = " + " ".join(srcs),
           "export VERILOG_DEFINES = " + " ".join(type_verilog_defines(t)),
           "export SDC_FILE = /work/constraint.sdc",
           f"export DIE_AREA = 0 0 {_um(w)} {_um(h)}",
           f"export CORE_AREA = {_um(m)} {_um(m)} {_um(w - m)} {_um(h - m)}",
           "export IO_CONSTRAINTS = /work/io.tcl",
           "export PDN_TCL = /work/pdn.tcl",
           *(["export POST_PDN_TCL = /work/pg_island_cut.tcl"] if pg_cuts else []),
           # override: platforms/asap7/config.mk (read AFTER the design config) sets MAKE_TRACKS with a plain
           # export, which silently replaced the plan tracks (M7 offset 0.016, not 0.032) -> every plan pin off-track
           "override export MAKE_TRACKS = /work/make_tracks.tcl",
           "export MIN_ROUTING_LAYER = M2",
           f"export MAX_ROUTING_LAYER = {top}",
           f"export PLACE_DENSITY = {util:g}",
           "export SYNTH_HIERARCHICAL = 0",
           "export SYNTH_REPEATABLE_BUILD = 1",
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
             if hold_ff_margin is not None and not macros else []),
           # pin registers FIRM at their faces through GPL, released for DPL (CP1 10-23: GPL left them ~1 mm inside)
           "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl",
           "export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl",
           # R4: one clock port per tap; every sink moves to its nearest tap's net before CTS (local trees)
           "export PRE_FLOORPLAN_TCL = /work/prects_estimate.tcl",
           "export PRE_CTS_TCL = /work/pre_cts.tcl",
           # COORD 10-23: taps sized by sink count (sink-anchored taps: the plan's clock.tap_max_sinks)
           f"export OT_TAP_MAX_SINKS = {_tap_cap(t)}",
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
           f"export OT_HOLD_IN_MIN = {t_lib(hold_in_min_ps(P)):.4f}",
           f"export OT_HOLD_OUT_MIN = {t_lib(hold_out_min_sdc_ps(P, tn)):.4f}",
           *([f"export OT_TAP_WINDOW = {t_lib(tap_window_ps(P)):.4f}"] if tap_window_ps(P) else []),
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
    if io_hold_mode(P, tn) == "plan_demand" or die_sta_hold_demand(P, tn):
        # CLOCK-KV-R21: a die_sta per-bit demand (die_sta_hold_demand) uses the same HB4 hook + buffer cap
        # HOLD-REPAIR 10-26 (12.4a a1): the FF GRT hold repair pads the declared seam demand on the input paths with
        # HB4 (hold_pad_hb4.tcl) and a raised buffer cap; hold_repair_pre.tcl sources grt_pre.tcl first
        cfg[cfg.index("export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl")] = "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl"
        cfg += [f"export OT_MAX_BUFFER_PERCENT = {HOLD_REPAIR_MAX_BUFFER_PERCENT:g}"]
        shutil.copyfile(Path(__file__).with_name("hold_repair_pre.tcl"), kd / "hold_repair_pre.tcl")
        shutil.copyfile(HOLD_PAD_HB4, kd / "hold_pad_hb4.tcl")
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
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    for f in ("face_flops.tcl", "face_flops_release.tcl", "face_keep.tcl", "face_keep_release.tcl",
              "clock_taps.tcl", "tap_balance.tcl", "reset_taps.tcl", "vclk_corner.tcl", "postcts_gate.tcl", "grt_pre.tcl",
              "grt_post.tcl", "cts_post.tcl", "leaf_affinity.tcl", "tapbal_grt.tcl", "pinreg_pad.tcl",
              "pinreg_measure.tcl", "keepout_phys.tcl", "pg_connect.tcl"):
        shutil.copyfile(Path(__file__).with_name(f), kd / f)
        if f == "reset_taps.tcl" and (RT.pipelined(P) or RT.wavefront(P)):
            hook = kd / f
            reset_prefix = f"set rt_leaf_tap {RT.leaf_tap(P, tn)}\n"
            if t.get("reset", {}).get("local_taps_um"):
                # These are terminal relay sites, not additional clock BTerms.
                reset_prefix += "set rt_consumer_taps_um {" + " ".join(
                    f"{{{i} {x:.5f} {y:.5f}}}" for i, (_, x, y) in enumerate(RT.consumer_taps(P, tn))) + "}\n"
            hook.write_text(reset_prefix + hook.read_text())
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
        (kd / "landing_exports.tcl").write_text(LC.export_tcl(P, tn))
        hook = kd / "clock_taps.tcl"
        hook.write_text(hook.read_text() + "\nsource /work/landing_exports.tcl\n")
        import landing_place as LP
        (kd / "landing_placement.tcl").write_text(LP.tcl(P, tn))
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
""")
    if rs_post:
        # after the landing placement hook: the rings are FIRM in their banks before the bank becomes a GPL blockage
        (kd / "reserved_banks.tcl").write_text(rs_post)
        (kd / "reserved_banks_release.tcl").write_text(rs_rel)
        hook = kd / "face_flops.tcl"
        hook.write_text(hook.read_text() + "\nsource /work/reserved_banks.tcl\n")
        hook = kd / "face_flops_release.tcl"
        hook.write_text("source /work/reserved_banks_release.tcl\n" + hook.read_text())
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
    ist = [Path(f).parent / "istations.tcl" for f in rtl_files[:1] if (Path(f).parent / "istations.tcl").is_file()]
    if ist:
        shutil.copyfile(ist[0], kd / "istations.tcl")
    # OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): FIRM sites of the reset entry stage + synchronous relay
    # tree.  kit_rsync writes reset_tree.tcl next to bound kit RTL; a gen_rtl kit of a pipelined plan gets it from the
    # plan (the same tree gen_rtl emitted).
    rtt = [Path(f).parent / "reset_tree.tcl" for f in rtl_files[:1] if (Path(f).parent / "reset_tree.tcl").is_file()]
    import reset_tree as RT
    if rtt:
        shutil.copyfile(rtt[0], kd / "reset_tree.tcl")
    elif RT.delivered(P):
        (kd / "reset_tree.tcl").write_text(RT.tcl_text(RT.for_type(P, tn)))
    if P.reset.get("relay_driver"):
        shutil.copyfile(Path(__file__).with_name("reset_pair_place.tcl"), kd / "reset_pair_place.tcl")
    if macros:     # S81-P8 10-23: soft relay stations on their source-sink lines (relay_mid.tcl, after face_flops)
        shutil.copyfile(Path(__file__).with_name("relay_mid.tcl"), kd / "relay_mid.tcl")
    # R3: ft station table for face_flops.tcl: slot, stations, in face (route leg order), optional regs_um sites
    ft = ["# slot stations in_face out_face [x y ...]  (GENERATED; type frame um)"]
    for s_ in t.get("ft_slots", []):
        regs = " ".join(f"{_um(x)} {_um(y)}" for x, y in s_.get("regs_um", []))
        ft.append(f"{s_['name']} {int(s_.get('stations', 1))} {s_.get('in_face', 'W')} {s_.get('out_face', 'E')} "
                  f"{regs}".rstrip())
    (kd / "ft_stations.txt").write_text("\n".join(ft) + "\n")
    from ft_bit_sites import table as ft_bit_sites_table
    (kd / "ft_bit_sites.tcl").write_text(ft_bit_sites_table(t.get("ft_slots", [])))
    ff_core_taps = {r[0]: r for r in core_tap_rows(P, tn, "FF")}
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
                          grid_taps=0 if _density(t) else len(S._grid_taps(P, tn)),
                          taps=[dict(name=n, xy=[x, y], kind="density" if _density(t) else
                                     ("grid" if i < len(S._grid_taps(P, tn)) else "sinks"))
                                for i, (n, x, y) in enumerate(S.tap_grid(P, tn))],
                          sink_taps=(T.report(P, tn)["taps"] if S.sink_tap_mode(t) else []),
                          taps_snapped=[dict(name=n, xy=[x, y]) for n, x, y in clock_pins(P, tn)],
                          core_taps=[dict(port=n, inst=i, pin=p_, early_ps=e, insertion_ps=ins,
                                          early_ff_ps=ff_core_taps[n][3], insertion_ff_ps=ff_core_taps[n][4])
                                     for n, i, p_, e, ins in clat["taps"]],
                          uncertainty_split=UNC_SPLIT),
               core_latency=clat["rows"],
               pin_reg_p90_um=P.budgets["pin_reg_p90_um"], io_budget=IO_BUDGET,
               instances=[n for n, p in P.parts.items() if p["type"] == tn])
    if ioh:
        from io_hold_qualification import plan_digest
        bud['io_hold'] = dict(mode='sender_min',plan_sha256=plan_digest(P.raw),requires_parent=True)
        if io_hold_mode(P, tn) == 'plan_demand':
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
    # CP1-R10 / COORD 10-24: boundary-register guard on the Yosys netlist (run_kit.sh, right after synth)
    shutil.copyfile(Path(__file__).with_name("face_guard.py"), kd / "face_guard.py")
    shutil.copyfile(Path(__file__).with_name("selrange_gate.py"), kd / "selrange_gate.py")
    shutil.copyfile(Path(__file__).with_name("native_bb.py"), kd / "native_bb.py")
    # FLOW-CANARY / COORD 10-25: register fanout gate right after face_guard (kv3_astk B: Yosys merged replicas -> 2048 loads)
    shutil.copyfile(Path(__file__).with_name("reg_fanout_gate.py"), kd / "reg_fanout_gate.py")
    for helper in ("port_bind_gate.py", "hold_gate.tcl"):
        shutil.copyfile(Path(__file__).with_name(helper), kd / helper)
    # LEC 10-24: RTL vs synthesised netlist equivalence (run_kit.sh, right after face_guard; NOT EQUIVALENT stops)
    shutil.copyfile(Path(__file__).with_name("lec.py"), kd / "lec.py")
    shutil.copyfile(Path(__file__).with_name("adder_map_dontuse.py"), kd / "adder_map_dontuse.py")   # ruling 4 (10-25)
    for f in ("face_keep.tcl", "face_keep_release.tcl"):   # CP1-R10 (restored: lost in main merge 0ce45ab03c)
        shutil.copyfile(Path(__file__).with_name(f), kd / f)
    # Copy the current shared hook and its conditional helpers beside each generated kit.
    cf = Path(__file__).resolve().parents[2] / "physical" / "common_flow"
    for f in KEEP_REGS_HOOK:
        shutil.copyfile(cf / f, kd / f)
    # SIGNOFF 10-24: uniform sign-off as the final kit-flow step (run_kit.sh after route): signoff.py + its helpers
    from signoff import copy_signoff_bundle
    copy_signoff_bundle(kd, extra=("kit_preflight.py",))
    # CRASH-TRIAGE 10-25: 6_report PDNSim IR is deferred out of the route container (partition_ir.py patch +
    # OT_DEFER_PARTITION_IR=1 in run_kit.sh).  10 autopilot CRASH rows (kv3_io_ft/_v1 x8, coll_ftm x2) were killed
    # at the memory cap (25/33/50 GB at --mem 24/32/48) inside analyze_power_grid AFTER 6_final.odb/.spef existed.
    # IR stays NOT_RUN for the kit; partition_ir.py sidecar KIT --mem-gb 64 runs it as its own admitted job.
    shutil.copyfile(Path(__file__).with_name("partition_ir.py"), kd / "partition_ir.py")
    (kd / "pins.json").write_text(json.dumps([dict(bus=b, bit=i, layer=l, x=x, y=y, face=f)
                                              for b, i, l, x, y, f in pins]) + "\n")
    if land_slots is not None:                  # face_guard reads it beside pins.json (count-aligned landing rings)
        (kd / "land_slots.json").write_text(json.dumps(land_slots, indent=1) + "\n")
    port_pins = port_bind_pin_records(P, tn, pins, bump_ports)
    sps = strap_pin_sites(P, tn)
    (kd / "port_bind_pins.json").write_text(json.dumps(port_pins, indent=1) + "\n")
    if sps:
        # declared ID straps of this kit for port_bind_gate / straps.py (OWNER 10-25 option B)
        (kd / "straps.json").write_text(json.dumps(dict(straps=sorted({n.split("[")[0] for n, *_ in sps})), indent=1) + "\n")
    import infra_rtl as IR
    infra = IR.type_ports(t)
    if infra:
        import ft_ports as FT
        decl = FT.declaration(t.get("infra_arcs", []), f"die plan {P.name} type {tn}: explicit native hard-core interfaces")
        if {p["name"] for p in infra} != {p["name"] for p in decl["ports"]}:
            raise ValueError("native infrastructure ports/arcs disagree")
        FT.install(kd, decl)
        (kd / "infra_ports.json").write_text(json.dumps(infra, indent=1) + "\n")
        bud["native_infrastructure"] = dict(pins=len(infra), arcs=len(decl["arcs"]), data_cycles_added=0, timing="die-timed FT interfaces; actual characterisation required")
        (kd / "budget.json").write_text(json.dumps(bud, indent=1) + "\n")
    write_partition_freeze(P, tn, kd, plan_pin_records(P, tn, pins, bump_sites))
    return kd


def type_verilog_defines(t):
    """One declared source profile for synthesis, RTL lint and the LEC gold reader."""
    values = t.get("verilog_defines", [])
    if not isinstance(values, list) or any(not isinstance(v, str) or
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in values):
        raise ValueError("type verilog_defines must be a list of bare Verilog macro names")
    return list(dict.fromkeys(["-DSYNTHESIS"] + ["-D" + v for v in values]))


RUN_KIT = r"""#!/bin/bash
# GENERATED by gen.py phys. Pre-floorplan gates fail closed. CTS is measured at
# FF before hold repair; structural failures return before global/detail route.
# Heavy: run_kit.sh KITDIR [GOAL=route] [MEM_GB=16] [CPUS=8] through ot-run.
# Kit IR (CRASH-TRIAGE 10-25): 6_report PDNSim is deferred (partition_ir.py; IR NOT_RUN in the kit, run it with
# partition_ir.py sidecar KIT --mem-gb 64 --threads 8).  OT_KIT_IR=inline restores the in-route analysis.
# LEC (10-24): lec.py proves the Yosys netlist equivalent to the kit RTL read with the OTHER HDL frontend, right after
# face_guard: NOT EQUIVALENT stops the kit before floorplan; UNPROVEN / tool error is a warning in lec/lec.json.
# Gate exit codes (classify by the FAIL_PREFLOOR / FAIL_POSTCTS marker text): 3 selrange, 4 FF structural hold gate,
# 5 LEC NOT EQUIVALENT, 6 pre-route insertion gate (FLOW 10-25), 7 reg_fanout (FLOW-CANARY 10-25: register > 64 data
# loads on the Yosys netlist = replicas merged by Yosys); other non-zero = sdc_lint / face_guard / flow step rc.
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-16}; CPUS=${4:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=dpkit-$(basename "$K")-$$
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
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_KIT_IR=${OT_KIT_IR:-defer} -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl || exit 9; \
  if [ -f /work/partition_ir.py ] && [ \"\$OT_KIT_IR\" = defer ]; then python3 -I /work/partition_ir.py patch /OpenROAD-flow-scripts/flow/scripts && export OT_DEFER_PARTITION_IR=1 || echo 'PARTITION_IR WARNING: patch refused, kit IR runs inline in 6_report'; fi; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR sdc_lint' | tee -a /work/FAIL_PREFLOOR; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/rtl_lint.py /work; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR rtl_lint (FAIL or NOT RUN)' | tee -a /work/FAIL_PREFLOOR; rc=8; fi; fi; \\\
  SRP=; if [ \$rc = 0 ]; then (python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1; echo \$? > /work/selrange.rc) & SRP=\$!; fi; \
  if [ \$rc = 0 ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR adder_map_dontuse' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist \$(ls /work/run/results/asap7/*/base/1_2_yosys.v | tail -1) --report /work/dont_use_check.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR dont_use_check' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ -n \"\$SRP\" ]; then wait \$SRP; S=\$(cat /work/selrange.rc 2>/dev/null || echo 2); tail -3 /work/selrange.log; if [ \"\$S\" != 0 ]; then echo 'FAIL_PREFLOOR selrange (FAIL or NOT RUN)' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then python3 -I /work/port_bind_gate.py \"\$N\" /work > /work/port_bind.log 2>&1; rc=\$?; tail -2 /work/port_bind.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR port_bind' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard.py \$N --pins /work/pins.json --out /work/face_guard.json; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR face_guard' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/reg_fanout_gate.py \$N --out /work/reg_fanout.json > /work/reg_fanout.log 2>&1; rc=\$?; head -12 /work/reg_fanout.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR reg_fanout (register > 64 data loads: merged replicas; or NOT RUN), see reg_fanout.json' | tee -a /work/FAIL_PREFLOOR; rc=7; fi; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; rc=\$?; \
    if [ \$rc = 0 ]; then python3 -I /work/face_guard.py /work/1_synth_odb.v --pins /work/pins.json --out /work/face_guard_odb.json; rc=\$?; fi; \
    if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR face_guard_odb' | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ] && [ -f /work/lec.py ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json)' | tee -a /work/FAIL_PREFLOOR; rc=5; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = cts ] || [ $GOAL = route ] || [ $GOAL = finish ]; }; then \
    \$M cts SKIP_CTS_REPAIR_TIMING=1; rc=\$?; \
    if [ \$rc = 0 ] && grep -q '^export OT_TAP_GRT_PRE = 1' /work/config.mk; then \$M run RUN_SCRIPT=/work/tapbal_grt.tcl RUN_LOG_NAME_STEM=4_2_tapbal_grt CORNER=TC CORNERS=tc; rc=\$?; \
      if [ \$rc != 0 ]; then echo 'FAIL_POSTCTS GRT-RC tap pre-pass (tapbal_grt.tcl)' | tee -a /work/FAIL_POSTCTS; rc=6; fi; fi; \
    if [ \$rc = 0 ]; then C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc 2>/dev/null | head -1); \
      PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\"\$C\" SDC=\"\$S\" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
        OT_VCLK_TT=\$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk) OT_VCLK_FF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
        OT_HOLD_IN_MIN=\$(sed -n 's/^export OT_HOLD_IN_MIN = //p' /work/config.mk) OT_HOLD_OUT_MIN=\$(sed -n 's/^export OT_HOLD_OUT_MIN = //p' /work/config.mk) \
        OT_TAP_WINDOW=\$(sed -n 's/^export OT_TAP_WINDOW = //p' /work/config.mk) \
        LAYER_PARASITICS_FILE=\$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) \
        openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; rc=\$?; tail -3 /work/hold_gate.log; \
      if [ \$rc != 0 ]; then echo 'FAIL_POSTCTS FF structural hold gate (or NOT RUN)' | tee -a /work/FAIL_POSTCTS; rc=4; fi; fi; fi; \
  HM=\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk | tail -1); \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ $GOAL = route ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ $GOAL = route ]; then O5=\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1); \
    for c in TT FF; do OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$O5 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; \
      grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log || echo \"OT_POSTCTS_GATE \$c no result FAIL\" | tee -a /work/postcts_gate_\$c.log; done; \
    if grep -hq 'OT_POSTCTS_GATE.*FAIL' /work/postcts_gate_TT.log /work/postcts_gate_FF.log; then \
      grep -h OT_POSTCTS_GATE /work/postcts_gate_*.log | sed 's/^/FAIL_POSTCTS pre-route insertion gate: /' >> /work/FAIL_POSTCTS; rc=6; fi; fi; \
  if [ \$rc = 0 ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/core_infra_post.v ] && [ -f /work/lec.py ]; then python3 -I /work/lec.py /work --netlist /work/core_infra_post.v --out /work/lec_post > /work/lec_post.log 2>&1; lr=\$?; tail -1 /work/lec_post.log; \
    if [ \$lr != 0 ]; then echo \"FAIL_POSTPLACE clock-gate copy LEC exit \$lr (lec_post/lec.json): copies not proved equivalent\" | tee -a /work/FAIL_POSTCTS; rc=5; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls /work/run/results/asap7/*/base/5_route.odb /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; rc=\$?; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# Route success alone is not sign-off. Preserve previous failed verdicts.
if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then
  SO="$K/signoff"; [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)_$$"
  SIGNOFF_DOCKER=${SIGNOFF_DOCKER:-docker} python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" \
    --out "$SO" --image "$IMAGE" --corners tt,ff > "$SO.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$SO.log" | head -12
fi
exit $rc
"""


def write_phys(raw, out, rtl_root=None, types=None, util=0.5, proof=False, kit_rtl=None,
               hold_ff_margin=HOLD_FF_MARGIN_DEFAULT, margins=None, skip_ir=False, max_wire_um=None, plan_path=None,
               rc_cal=True, master_slice=None, trial=False, gpl_plain=(), landing=None):
    """gpl_plain: types whose kit places on plain-wirelength GPL (pure-FT corridors, --gpl-plain)."""
    """landing (opt-in, DIE-HEAD-4b, gen phys --clock-landing): the clock_landing_plan sidecar of a composed landed plan.
    The kit wrapper is the SAME landed wrapper gen rtl --clock-landing emits (clock_landings.type_rtl: rings, ring
    reset relays, monitor), every type generated so the sidecar's type check sees all copies, and each kit carries the
    landing ring RTL its wrapper instantiates (LANDING_RTL).  Default None: byte-identical kits."""
    """margins (slew_pct, cap_pct): opt-in repair_design SLEW_MARGIN / CAP_MARGIN (None: not exported)."""
    """kit_rtl {type: filelist}: G3 kits take the bound partition RTL (bind.py kit-rtl: the bound module inside a
    port-only wrapper with the plan type's module name and exact pins) instead of the generated plan wrapper"""
    import gen_rtl
    import master_slice as MS
    if not master_slice and not trial and MS.required(raw):     # 12.7c: refuse before writing anything
        raise SystemExit(MS.REFUSE)
    # plan-relative declarations (hard-core pins_file for the reset wavefront) resolve against the plan file
    P = S.Plan(raw, plan_path)
    if master_slice:                                            # 12.7c: every slice checked before any kit is written
        for tn, t in sorted(P.types.items()):
            if not t.get("hard") and (not types or tn in types):
                MS.resolve(master_slice, tn, t["outline_um"], raw, trial, kind="partition")
    out = Path(out)
    rtl_dir = out / "_rtl"
    gtypes = types
    if kit_rtl:                # kit-rtl types take the bound RTL: no generated plan wrapper for them
        gtypes = [tn for tn in (types or P.types) if tn not in kit_rtl]
    if landing is not None:
        if kit_rtl:
            raise gen_rtl.GenError("clock landing: --kit-rtl kits take the bound RTL; landing kits use the landed wrapper")
        gtypes = None          # the landed emitter checks every copy of every type
    files = gen_rtl.write_rtl(raw, rtl_dir, rtl_root, gtypes, plan_path=plan_path, landing=landing)
    lands = None
    if landing is not None:    # DIE-HEAD-21: the same Landings write_rtl just validated -> per-type land_slots.json
        import clock_landings as CL
        lands = CL.Landings(raw, landing)
    cells = rtl_dir / "ot_dp_cells.sv"
    root = Path(rtl_root) if rtl_root else Path(__file__).resolve().parent.parent.parent
    rs = root / "rtl" / "lib" / "ot_reset_sync.sv"
    kits = []
    for tn, t in sorted(P.types.items()):
        if t.get("hard") or (types and tn not in types):
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
        bumps = kit_bump_ports(P, tn, kit_rtl[tn]) if kit_rtl and tn in kit_rtl else None
        kits.append(write_type_kit(P, tn, out, [str(f) for f in mine], util, proof, root, hold_ff_margin, margins,
                                   skip_ir, max_wire_um, rc_cal, master_slice, trial, bump_ports=bumps,
                                   gpl_plain=tn in (gpl_plain or ()),
                                   land_slots=lands.land_slots(tn) if lands is not None else None))
    (out / "run_kit.sh").write_text(RUN_KIT)
    (out / "run_kit.sh").chmod(0o755)
    return kits


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
                                       f"set_clock_uncertainty {t_lib(UNC_SETUP_PS):.4f} -setup [all_clocks]\n"
                                       f"set_clock_uncertainty {t_lib(UNC_HOLD_PS):.4f} -hold [all_clocks]\n")
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
              f"set_clock_uncertainty {t_lib(UNC_SETUP_PS):.4f} -setup [all_clocks]",
              f"set_clock_uncertainty {t_lib(UNC_HOLD_PS):.4f} -hold [all_clocks]",
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
        L += pin(name, "INPUT", "SIGNAL" if name in ("arst_n", "start_i") else "CLOCK",
                 [(top, x - tw, y - 2 * PIN_LEN_UM, x + tw, y + 2 * PIN_LEN_UM)])
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
