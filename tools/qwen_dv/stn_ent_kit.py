#!/usr/bin/env python3
"""QW-SLICE4 10-19 (Q.STA.SLICE.1): ref_tile kits of the station ENTRIES cluster qfd_dv_redstn2_ef_lp (lp.py landed
parent of the 8 closed region tiles qfd_dv_redstn2_region, kit qfd_dv_slice2_stnrgc, record 5fb7dcb72).

  python3 tools/qwen_dv/stn_ent_kit.py a   -> qfd_dv_slice2_stnent   (main: 108-um centre channel, 885.6 x 496.8)
  python3 tools/qwen_dv/stn_ent_kit.py b   -> qfd_dv_slice2_stnentb  (parallel fallback: 151.2-um channel, 885.6 x 540,
                                                                       landing halves FENCED beside their child)

Floorplan (every child origin on the 43.2 lattice; children 151.2 x 151.2, cap M5; the parent routes M2..M7, so M6 / M7
run over the children):
  2 x 4 array, column pitch 216 (64.8-um gaps), x0 = 43.2 + 216 c.  Region r sits in column r // 2;
  even regions = TOP row, orient MY (the fault ring runs E -> W on the top row: 6 -> 4 -> 2 -> 0, each child reads its
  ring input on its local W face = physical E), odd regions = BOTTOM row, orient MX (ring W -> E: 1 -> 3 -> 5 -> 7);
  the two vertical ring hops 0 -> 1 (W margin) and 7 -> 6 (E margin) are neighbour wires across the channel.
  Child faces: local N (rs_n / nb_d) -> parent N edge (top) / S edge (bottom) straight above / below the child pins;
  local S (bt_q in, r_d out, region 0's bt_re / bt_word / r_v / r_idx / r_last) faces the CENTRE CHANNEL and leaves on
  the parent W edge (columns 0, 1) / E edge (columns 2, 3); local W (rs_s, cfg, rst_n, ck) and local E (nb_od, fault)
  face the column gaps and leave on the N edge (top row) / S edge (bottom row) inside the gap beside the child.
  Region clocks ck_r<k>: on the N / S edge in the gap at the child's own ck-pin side (the child's ck pin is on its local
  W face at y 82.14): one entry per child.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("a", "b") else sys.exit("usage: stn_ent_kit.py a|b")
NAME = "qfd_dv_slice2_stnent" + ("" if VARIANT == "a" else "b")
VIEW = "physical/ref_tile/qfd_dv_slice2_stnrgc/views/qfd_dv_redstn2_region"
CW = 151.2
XS = [43.2 + 216.0 * c for c in range(4)]
YB = 43.2
YT = 302.4 if VARIANT == "a" else 345.6
W = 885.6
H = YT + CW + 43.2
REC = "results/arch/qw_slice4_1019/lp/qfd_dv_redstn2_ef_lp_record.json"
TOP = "qfd_dv_redstn2_ef_lp"
LP_SV = "rtl/qwen_dv/lp/qfd_dv_redstn2_ef_lp.sv"
SPEC_DIR = "tools/ref_tile/specs_qw_slice4"
DATA_IN = [("rs_s_lo", 64), ("rs_s_hi", 64), ("rs_n_lo", 64), ("rs_n_hi", 64), ("nb_d", 64), ("bt_q", 32)]
DATA_OUT = [("nb_od", 64), ("r_d", 64)]
CTRL_OUT = [("nb_oc", 2), ("bt_re", 1), ("bt_word", 9), ("r_v", 1), ("r_idx", 8), ("r_last", 1), ("fault", 1)]
CTRL_IN = [("cfg", 29), ("rs_s_c", 4), ("rs_n_c", 4), ("nb_c", 2)]
# child pin -> parent port base (region k's own ports; region 0 also carries the single control copies)
CHILD2PORT = {"rs_s_lo_p": "rs_s_lo", "rs_s_hi_p": "rs_s_hi", "rs_n_lo_p": "rs_n_lo", "rs_n_hi_p": "rs_n_hi",
              "nb_d_p": "nb_d", "bt_q_p": "bt_q", "nb_od": "nb_od", "r_d": "r_d"}
CHILD2PORT0 = {"rs_s_c_p": "rs_s_c", "rs_n_c_p": "rs_n_c", "nb_c_p": "nb_c", "nb_oc": "nb_oc", "bt_re": "bt_re",
               "bt_word": "bt_word", "r_v": "r_v", "r_idx": "r_idx", "r_last": "r_last", "fault": "fault"}
CFG_SLICES = {"cfg_v_p": (28, 28), "cfg_mode_p": (27, 26), "cfg_wsrc_p": (25, 25), "cfg_nwords_p": (24, 17),
              "cfg_sbase_p": (16, 8), "cfg_kcm1_p": (7, 0)}
PIN_SIZE = {"M3": "0.018 0.144", "M5": "0.024 0.192", "M4": "0.192 0.024", "M6": "0.192 0.032"}


def lef_pins(path):
    t = (ROOT / path).read_text()
    out = {}
    for m in re.finditer(r"^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", t, re.S | re.M):
        r = re.search(r"LAYER (\S+) ;\s*RECT\s+([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)", m.group(2))
        if r:
            out[m.group(1)] = (r.group(1), (float(r.group(2)) + float(r.group(4))) / 2, (float(r.group(3)) + float(r.group(5))) / 2)
    return out


def place(r):
    """(x0, y0, orient, top?) of region r's child"""
    top = r % 2 == 0
    return XS[r // 2], (YT if top else YB), ("MY" if top else "MX"), top


def xform(r, x, y):
    x0, y0, o, _ = place(r)
    return (x0 + CW - x, y0 + y) if o == "MY" else (x0 + x, y0 + CW - y)


def face(n, lp):
    layer, x, y = lp[n]
    if x < 0.5:
        return "W"
    if x > CW - 0.5:
        return "E"
    return "N" if y > CW - 0.5 else "S"


def parent_bits(r, n):
    """parent port bits a child pin bit maps to (None: an internal / landed net)"""
    m = re.fullmatch(r"(\w+?)(?:\[(\d+)\])?", n)
    base, b = m.group(1), int(m.group(2) or 0)
    if base in CHILD2PORT:
        return f"{CHILD2PORT[base]}_r{r}[{b}]"
    if r == 0 and base in CHILD2PORT0:
        w = dict(CTRL_OUT + CTRL_IN).get(CHILD2PORT0[base], 1)
        return f"{CHILD2PORT0[base]}[{b}]" if w > 1 else CHILD2PORT0[base]
    if r == 0 and base in CFG_SLICES:
        return f"cfg[{CFG_SLICES[base][1] + b}]"
    if r == 0 and base == "rst_n":
        return "rst_n"
    return None


def main():
    lp = lef_pins(f"{VIEW}/qfd_dv_redstn2_region.lef")
    seg = {}             # (edge, segment key) -> list of (sort key, port bit)

    def add(edge, key, sk, bit):
        seg.setdefault((edge, key), []).append((sk, bit))

    gaps = {}            # segment extents along the edge
    for r in range(8):
        x0, y0, o, top = place(r)
        c = r // 2
        ne = "N" if top else "S"
        for n in sorted(lp):
            if n == "ck":
                continue
            bit = parent_bits(r, n)
            if bit is None:
                continue
            f = face(n, lp)
            px, py = xform(r, lp[n][1], lp[n][2])
            if f == "N":                                   # straight above / below the child pin
                add(ne, ("straight", r), px, bit)
            elif f == "S":                                 # into the channel, out on the W (cols 0, 1) / E (cols 2, 3) edge
                add("W" if c < 2 else "E", ("chan", r), (-py if top else py, c if c < 2 else -c, px), bit)
            else:                                          # local W / E face -> gap / margin beside the child on N / S
                phys_e = (f == "W") == (o == "MY")         # MY flips W <-> E
                k_ = (-py if top else py)                  # pins that leave the face first sit nearest the child
                add(ne, ("side", r, "E" if phys_e else "W"), k_ if phys_e else -k_, bit)
        # the region clock: beside the ck pin's side (local W face)
        phys_e = o == "MY"
        add(ne, ("side", r, "E" if phys_e else "W"), -9999.0 if phys_e else 9999.0, f"ck_r{r}")
    # segment extents (um along the edge)
    ext = {}
    for (edge, key), items in seg.items():
        if key[0] == "straight":
            continue
        if key[0] == "chan":
            lo, hi = YB + CW + 4.32, YT - 4.32
            ext[(edge, key)] = (lo, hi)
            continue
        r, side = key[1], key[2]
        x0 = XS[r // 2]
        if side == "E":
            a, b = x0 + CW + 1.0, (x0 + 216.0 - 1.0) if r // 2 < 3 else W - 1.0
        else:
            a, b = ((x0 - 64.8 + 1.0) if r // 2 > 0 else 1.0), x0 - 1.0
        ext[(edge, key)] = (a, b)
    # split each shared gap between the two children that face it, in proportion to their pin counts
    for edge in ("N", "S"):
        for c in range(3):
            left = [k for k in ext if k[0] == edge and k[1][0] == "side" and k[1][1] // 2 == c and k[1][2] == "E"]
            right = [k for k in ext if k[0] == edge and k[1][0] == "side" and k[1][1] // 2 == c + 1 and k[1][2] == "W"]
            if left and right:
                (l,), (rr,) = left, right
                a, b = XS[c] + CW + 1.0, XS[c + 1] - 1.0
                nl, nr = len(seg[l]), len(seg[rr])
                m = a + (b - a) * nl / (nl + nr)
                ext[l], ext[rr] = (a, m - 0.5), (m + 0.5, b)
    # channel: the two rows' children on the same edge share the channel height: top row upper part, bottom row lower part
    for edge in ("W", "E"):
        ks = [k for k in ext if k[0] == edge and k[1][0] == "chan"]
        lo, hi = YB + CW + 4.32, YT - 4.32
        tot = sum(len(seg[k]) for k in ks)
        bot = sorted([k for k in ks if k[1][1] % 2 == 1], key=lambda k: abs(k[1][1] // 2 - (0 if edge == "W" else 3)))
        tp = sorted([k for k in ks if k[1][1] % 2 == 0], key=lambda k: abs(k[1][1] // 2 - (0 if edge == "W" else 3)))
        y = lo
        for k in bot:                                       # bottom row, nearest column at the bottom
            h = (hi - lo) * len(seg[k]) / tot
            ext[k] = (y, y + h - 0.3)
            y += h
        for k in reversed(tp):                              # top row, nearest column at the top
            h = (hi - lo) * len(seg[k]) / tot
            ext[k] = (y + 0.3, y + h)
            y += h
    lines = [f"# generated by tools/qwen_dv/stn_ent_kit.py ({NAME}): exact parent pins; child N-face bits straight above / below"
             " their child pins, S-face bits on the W / E edge in the centre channel, W / E-face bits on the N / S edge in the"
             " gap beside the child, region clocks beside each child's ck side"]
    placed = {}

    def pin(n, layer, x, y):
        placed[n] = (layer, round(x, 3), round(y, 3))
        lines.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{PIN_SIZE[layer]}}} -force_to_die_boundary")

    for (edge, key), items in sorted(seg.items(), key=lambda kv: str(kv[0])):
        items = sorted(items, key=lambda t: t[0] if not isinstance(t[0], tuple) else t[0])
        if key[0] == "straight":
            y = H if edge == "N" else 0.0
            for sk, bit in items:
                pin(bit, "M5", sk, y)
            continue
        a, b = ext[(edge, key)]
        n = len(items)
        for i, (sk, bit) in enumerate(items):
            v = a + (b - a) * (i + 0.5) / n
            if edge in ("N", "S"):
                pin(bit, "M3" if i % 2 == 0 else "M5", v, H if edge == "N" else 0.0)
            else:
                pin(bit, "M4" if i % 2 == 0 else "M6", 0.0 if edge == "W" else W, v)
    tcl = ROOT / f"{SPEC_DIR}/{NAME}_pins.tcl"
    tcl.parent.mkdir(parents=True, exist_ok=True)
    tcl.write_text("\n".join(lines) + "\n")
    # density check per edge segment
    dens = {}
    for (edge, key), items in seg.items():
        if key[0] == "straight":
            continue
        a, b = ext[(edge, key)]
        dens[f"{edge}:{key}"] = round(len(items) / max(b - a, 1e-3), 2)

    rec = json.loads((ROOT / REC).read_text())
    kids = [dict(view=VIEW, count=1, inst=f"u_r{r}", at=[place(r)[0], place(r)[1]], orient=place(r)[2], exact=True)
            for r in range(8)]
    dom = {}
    for r in range(8):
        ins = [f"{n}_r{r}" for n, _ in DATA_IN]
        outs = [f"{n}_r{r}" for n, _ in DATA_OUT]
        if r == 0:
            ins += [n for n, _ in CTRL_IN] + ["rst_n"]
            outs += [n for n, _ in CTRL_OUT]
        dom["core" if r == 0 else f"r{r}"] = dict(ratio=[1, 1], ports=[f"ck_r{r}"], inputs=ins, outputs=outs)
    faces = {"N": set(), "S": set(), "W": set(), "E": set()}
    for n, (layer, x, y) in placed.items():
        base = re.sub(r"\[\d+\]$", "", n)
        f = "N" if y >= H - 0.01 else "S" if y <= 0.01 else "W" if x <= 0.01 else "E"
        faces[f].add(base)
    fences = None
    if VARIANT == "b":
        fences = f"{SPEC_DIR}/{NAME}_fences.tcl"
        (ROOT / fences).write_text(fence_tcl(rec))
    W5 = "results/arch/qw_slice4_1019/bench_v5050/bench_summary.log"
    LB = "rtl/qwen_dv/lp/qfd_dv_redstn2_ef_lp_bench.sh"
    VE = "VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator VL_EXTRA=--timing SIM=verilator LP_ROOT=."
    RS = "PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH PIN=1 bash rtl/test/qwen_dv/safe_storage/run_station_regional.sh"
    benches = [
        dict(name="lp_lockstep_mut0", cmd=f"MUTS=0 {VE} bash {LB} {{RUN}}/bench/lp0", expect="pass",
             pass_regex="MUT 0: LP_LOCKSTEP PASS", threads=8, peak_ram_gb=24, needs=["verilator"]),
        dict(name="lp_mut1_bypass", cmd=f"MUTS=1 {VE} bash {LB} {{RUN}}/bench/lp1", expect="fail",
             fail_regex="MUT 1: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"], fail_witness=W5),
        dict(name="lp_mut2_read_k", cmd=f"MUTS=2 {VE} bash {LB} {{RUN}}/bench/lp2", expect="fail",
             fail_regex="MUT 2: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"], fail_witness=W5),
        dict(name="lp_mut4_late_reset", cmd=f"MUTS=4 {VE} bash {LB} {{RUN}}/bench/lp4", expect="fail",
             fail_regex="MUT 4: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"], fail_witness=W5),
        dict(name="ef_vs_monolith", cmd=f"{RS} {{RUN}}/bench/ef 0 0 +define+STN_EF", expect="pass",
             pass_regex="STATION_REGIONAL_EQ PASS PIN1", threads=8, peak_ram_gb=16, needs=["verilator"]),
        dict(name="ef_rmut1_btq_swap", cmd=f"{RS} {{RUN}}/bench/efr1 0 1 +define+STN_EF", expect="fail",
             fail_regex="REGIONAL_STATION_MISMATCH", threads=8, peak_ram_gb=16, needs=["verilator"], fail_witness=W5),
        dict(name="ef_rmut2_ring_cut", cmd=f"{RS} {{RUN}}/bench/efr2 0 2 +define+STN_EF", expect="fail",
             fail_regex="REGIONAL_FAULT_LATE|PHASE1_INJECTED_FAULT_MISSING", threads=8, peak_ram_gb=16, needs=["verilator"],
             fail_witness=W5),
    ]
    checklist = {
        "1_pins": "PASS: every parent input lands on a child pin register (PIN_IN=1, in the child's own clock) or a landing ring "
                  "(shared cfg / rs_s_c / rs_n_c / nb_c ring in r0, one read half per region); every output is a child flop Q; "
                  "rst_n -> lp reset runs (u_lpr_*) -> each child's own 2-stage face landing",
        "2_reach": "PASS: the only plain crossings are the 1-bit reset runs; ring -> read hops are E=2 multicycle landings (<= ~700 um); "
                   "fault-ring hops are neighbour landings (<= ~260 um); parent pins <= ~115 um from their child pins",
        "3_fanout": "PASS: per region one read half per landed net; reset run per region feeds <= ~8 landing halves + 1 child pin",
        "4_depth": "PASS: landing read = 4:1 registered slot select; no combinational parent path (wires-only lp parent)",
        "5_storage": "PASS: ring banks are D=4 fixed-latency landings; station storage is SRAM inside the closed children (5 each)",
        "6_floorplan": f"PASS: 8 children on the 43.2 lattice (pitch 216 x {YT - YB:.1f}), 64.8-um gaps, {YT - YB - CW:.1f}-um channel; "
                       f"outline {W} x {H:.1f} (aspect {W / H:.2f}); fill ~{8 * CW * CW / (W * H) * 100:.0f}% children + glue; "
                       f"parent pins <= {max(dens.values()):.1f}/um per segment",
        "7_clock": "PASS: 8 regional roots ck_r0..7, one per child, entry beside the child's ck pin; children are closed with their own "
                   "trees (TT/FF insertion 277.5/231.9, spread 55/54); landed crossings between every region pair; io_hold_margin 0.03",
        "8_schedule": "PASS: static; compiler record: regions 1..7 +3 edges vs region 0 (ports and children), reset release +4, fault "
                      "ring status lag <= 6 per hop (loose sticky status, never a scheduled value)",
    }
    spec = dict(
        name=NAME, top=TOP, kind="cluster", diagnostic=True,
        sources=[LP_SV, "rtl/common/landed_parent/ot_pl_land.sv"],
        params={}, clock="multiple_cts_roots", clock_port="ck_r0",
        clock_ports=[rec["regions"][r]["clock_port"] for r in rec["regions"]],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom,
        landed_record=REC,
        reset_ports=["rst_n"],
        outline=dict(w=W, h=round(H, 3), exact=True),
        children=kids, macros=[], inter=[],
        pins={f: sorted(v) for f, v in faces.items() if v},
        io_tcl=f"{SPEC_DIR}/{NAME}_pins.tcl",
        route=dict(pd=0.5, threads=16, peak_ram_gb=64, macro_halo_um=5.4, pin_h="M4 M6", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        io_flop_at_pins={"cols": 4, "allow_none": True},
        pin_regs=dict(enable=False, reason="every parent input lands on a child pin register (PIN_IN=1) or a landing ring in its "
                      "region; every output is a child flop Q; a kit flop stage would add an edge the landed record does not price"),
        reset_landing=dict(enable=False, reason="rst_n feeds the lp reset runs (u_lpr_root + u_lpr_r<k>, 1 + 3 stages on the region "
                           "roots, priced: reset release +4); each child lands its rst_n in 2 more stages on its own root"),
        safe_design_checklist=checklist,
        pin_density_per_um=dens,
        why_floorplan="2 x 4 array matching the fault-ring order (0,2,4,6 top E->W, 7,5,3,1 bottom W->E): every ring hop is a "
                      "neighbour; children face their N pins outward, S faces into the centre channel (bt_q / r_d -> W / E edge), "
                      "W / E faces into 64.8-um gaps (rs_s / cfg / nb_od -> N / S edge); one clock entry per child",
        landed=dict(record=REC, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                    reset_depth=rec["reset"]["depth"], lp_spec="tools/landed_parent/specs/qfd_dv_stn_ent.json"),
        structural_change="QW-SLICE4 10-19 Q.STA.SLICE.1: new hierarchical station cluster (replaces the flat station inside the "
                          "failed slice2_e / slice2_wh one-root cores): 8 closed region tiles, 8 region clocks, lp landings. Variant "
                          + VARIANT + (": 108-um channel, unfenced glue" if VARIANT == "a" else
                                       ": 151.2-um channel, landing halves fenced beside their child (ring beside source, read beside reader)"),
        job=dict(owner="Claude:QW-SLICE4", branch="claude/qw-slice4-1019", tag="g1" + VARIANT,
                 purpose="QW-SLICE4: slice2 station entries cluster (8 x closed qfd_dv_redstn2_region)",
                 views_to=f"physical/ref_tile/{NAME}/views", record_to=f"results/rtl/ref_tile/{NAME}",
                 extra_paths=["rtl/qwen_dv", "rtl/hdc", "rtl/common/landed_parent", "rtl/lib", "rtl/test/qwen_dv/safe_storage",
                              "tools/landed_parent", "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1",
                              "physical/ref_tile/qfd_dv_slice2_stnrgc/views", "results/arch/qw_slice4_1019"],
                 benches=benches))
    if fences:
        spec["pin_hook_before_flops"] = [fences]
    out = ROOT / f"{SPEC_DIR}/{NAME}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out.relative_to(ROOT), tcl.relative_to(ROOT), len(placed), "pins; max density", max(dens.values()), "/um;",
          f"outline {W} x {H:.1f}")


def fence_box(r):
    """variant b: a 10.8-um band along the child's local W face (cfg / rs_s / ck side), 6.48 um off the child edge"""
    x0, y0, o, top = place(r)
    if o == "MY":                     # local W = physical E side
        return (x0 + CW + 6.48, y0 + 6.48, x0 + CW + 17.28, y0 + CW - 6.48)
    return (x0 - 17.28, y0 + 6.48, x0 - 6.48, y0 + CW - 6.48)


def fence_tcl(rec):
    own = {}
    for L in rec["landings"]:
        src = [x for x in L["src_nodes"] if not x.startswith("port:")]
        own[f"u_lpl_{L['name']}_w"] = f"r{src[0][3:]}" if src else L["src_region"]
        own[f"u_lpl_{L['name']}_r"] = L["dst_region"]
    o = ["# generated by tools/qwen_dv/stn_ent_kit.py b: PRE_GLOBAL_PLACE fences of the lp.py landing halves beside their child",
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]", "array set ::lpf_g {}",
         "array set ::lpf_n {}"]
    for r in range(8):
        x0, y0, x1, y1 = fence_box(r)
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_r{r}"]')
        o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0}*$::lpf_dbu)}}] [expr {{round({y0}*$::lpf_dbu)}}] "
                 f"[expr {{round({x1}*$::lpf_dbu)}}] [expr {{round({y1}*$::lpf_dbu)}}]")
        o.append(f'set ::lpf_g(r{r}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_r{r}"]')
    o.append("array set ::lpf_own {" + " ".join(f"{k} {v}" for k, v in sorted(own.items())) + "}")
    o += ["foreach i [$::lpf_blk getInsts] {",
          "  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne \"CORE\"} continue",
          "  regsub -all {\\\\} [$i getName] {} n",
          "  if {![regexp {^(u_lpl_[0-9]+_[wr])[./]} $n -> h]} continue",
          "  if {![info exists ::lpf_own($h)]} { error \"LP_FENCE: $n has no landing owner\" }",
          "  if {[$i getGroup] ne \"NULL\"} continue",
          "  set r $::lpf_own($h)",
          "  $::lpf_g($r) addInst $i",
          "  incr ::lpf_n($r)",
          "}",
          "foreach r {r0 r1 r2 r3 r4 r5 r6 r7} {",
          "  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error \"LP_FENCE: region $r got no landing cells\" }",
          "  puts \"LP_FENCE $r cells=$::lpf_n($r)\"",
          "}"]
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    main()
