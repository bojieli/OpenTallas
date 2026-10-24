#!/usr/bin/env python3
"""TRIAL die fabric case (lane TRIAL-HBM, 2026-10-24): flat die-level global route + STA of EVERY inter-partition
lane hop of a die plan, with the partitions as abstracts.  This is the die-scale counterpart of the G2 partition FT
probes (tools/die_plan/g2.py part_probe), stitched over all partitions at once, and the apples-to-apples successor of
the old monolithic HBM die GRT (results/physical/die_iter_1012/r25gq: 1,374,522 overflow).

Model (die frame, um):
  * every port bit gets its registers exactly where the plan puts them (g2.py part_probe semantics): a functional bus
    bit has a boundary flop 1 um inside its partition beside its pin; an ft slot bit has `stations` flops from the
    in pin along the slot route (slot regs_um, else evenly from the in pin: station 0 sits AT the in pin, so the hop
    from the previous partition crosses the face exactly at the plan pin);
  * nets: (driver register) -> (next register) for every hop of every lane: port bit nets across faces + the
    station-to-station nets inside each crossed partition.  Leaf -> boundary-flop paths are partition-internal and
    not modelled (budgeted by the kits);
  * partitions are abstracts: their own logic keeps (1 - ADJ) of M4..M7 (layer adjustment, default 0.5 as G2);
    hard cores (type hard_cores) block M4..max(M5, the core's top pin layer); content leaves not split into cores
    block M4..M5 (g2.probe_blockages); IO PHY contents (SerDes / UCIe / HBM PHY) block M4..M9 (keep-out); PHY_N-like
    hard partitions without a content outline block M4..M9 inset by PHY_MARGIN_UM from their faces;
  * die PG stripes (die.pg.grid) are M8/M9 obstructions; the clock H-tree (clock_htree.json) segments reserve
    ndr_tracks x pitch on their layer;
  * routing M4..M9 on the plan tracks; M1..M3 get coarse tracks (pitch GC_PITCH) only to set the GRT gcell to
    15 x GC_PITCH (OpenROAD derives the tile from the lowest tracks) -- 9.6 um at 0.64.

    fabric.py gen PLAN.json --out DIR [--htree clock_htree.json] [--adjust 0.5] [--mem 256] [--threads 32]
    -> DIR/fabric.def, fabric.tcl (GRT + guides + STA), map.json (instance / net metadata), run.sh (docker)
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import check  # noqa: E402
import schema as S  # noqa: E402

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
FLOP = "DFFHQNx1_ASAP7_75t_R"
INSET = 1.0
PHY_MARGIN_UM = 10.0
GC_PITCH = 0.64
DBU = 1000
IO_PHY_RE = ("serdes", "ucie", "phy")
LNUM = lambda L: int(L[1:])  # noqa: E731


def inset(pt, face, d=INSET):
    x, y = pt
    return {"E": (x - d, y), "W": (x + d, y), "N": (x, y - d), "S": (x, y + d)}[face]


def face_point(P, pid, c):
    pr = P.ports[pid]
    x0, y0, x1, y1 = P.rect(P.face_part(pid))
    f = pr["face"]
    return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[f]


def die_rect(P, part, o, s):
    a = P.to_die(part, (o[0], o[1]))
    b = P.to_die(part, (o[0] + s[0], o[1] + s[1]))
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def build(P, plan_dir):
    """cells {name: (x, y, part, kind)}, nets [(name, drv, rcv, meta)]"""
    cells, nets = {}, []
    src_idx, dst_idx = {}, {}
    for pid, pr in P.ports.items():
        src_idx[(pr["src"]["part"], pr["src"]["bus"])] = pid
        dst_idx[(pr["dst"]["part"], pr["dst"]["bus"])] = pid
    pins = {pid: P.port_pins(pid) for pid in P.ports}

    def slot_of(part, bus, suffix):
        if part == S.DIE_PART or not bus.endswith(suffix):
            return None
        return P.slot(part, bus[:-2])

    # stations per (part, slot): {bit: [names]}
    stations = {}
    for part in sorted(P.parts):
        t = P.ptype(part)
        for s in t.get("ft_slots", []):
            sn = s["name"]
            pin_ = dst_idx.get((part, sn + "_i"))
            pout = src_idx.get((part, sn + "_o"))
            fin = P.die_face(part, s.get("in_face", "W"))
            fout = P.die_face(part, s.get("out_face", "E"))
            pi = {b: inset(face_point(P, pin_, c), S.OPP[P.ports[pin_]["face"]]) for b, _, c in pins[pin_]} if pin_ else {}
            po = {b: inset(face_point(P, pout, c), P.ports[pout]["face"]) for b, _, c in pins[pout]} if pout else {}
            k = int(s.get("stations", 1))
            regs = [P.to_die(part, tuple(r)) for r in s["regs_um"]] if s.get("regs_um") else None
            d = {}
            for bit in sorted(set(pi) | set(po)):
                a = pi.get(bit) or po[bit]
                b = po.get(bit) or pi[bit]
                seg = check.zroute(a, b, fin, fout)
                L = check.plen(seg)
                names = []
                for j in range(k):
                    nm = f"{part}__st__{sn}__{bit}__{j}"
                    xy = regs[j] if regs else check.point_at(seg, L * j / k)
                    cells[nm] = (xy[0], xy[1], part, "st")
                    names.append(nm)
                    if j:
                        nets.append((f"n_{nm}", names[j - 1], nm, dict(kind="st", part=part, slot=sn)))
                d[bit] = names
            stations[(part, sn)] = d
    # port bit nets
    for pid, pr in sorted(P.ports.items()):
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        f = pr["face"]
        sp, sb = pr["src"]["part"], pr["src"]["bus"]
        dp, db = pr["dst"]["part"], pr["dst"]["bus"]
        ss = slot_of(sp, sb, "_o")
        ds = slot_of(dp, db, "_i")
        for bit, ln, c in pins[pid]:
            pt = face_point(P, pid, c)
            if ss:
                drv = stations[(sp, ss["name"])][bit][-1]
            else:
                drv = f"{sp}__bf__{sb}__{bit}"
                q = inset(pt, f)
                cells[drv] = (q[0], q[1], sp, "bf")
            if ds:
                rcv = stations[(dp, ds["name"])][bit][0]
            else:
                rcv = f"{dp}__bf__{db}__{bit}"
                q = inset(pt, S.OPP[f])
                cells[rcv] = (q[0], q[1], dp, "bf")
            nets.append((f"p_{pid}__{bit}", drv, rcv, dict(kind="port", port=pid, layer=ln)))
    return cells, nets


def blockages(P, plan_dir, htree=None):
    """[(layer, x0, y0, x1, y1, why)] in the die frame + region adjustments [(rect, part)]"""
    out = []
    layers = [f"M{i}" for i in range(4, 10)]
    core_top = {}
    for tn, t in P.types.items():
        for h in t.get("hard_cores", []):
            top = 5
            pf = h.get("pins_file")
            if pf and (plan_dir / pf).is_file():
                pl = {x["layer"] for x in json.loads((plan_dir / pf).read_text())}
                top = max([top] + [LNUM(x) for x in pl])
            core_top[(tn, h["inst"])] = top
    for part in sorted(P.parts):
        tn = P.parts[part]["type"]
        t = P.types[tn]
        cores = [h for h in t.get("hard_cores", []) if "origin_um" in h and "outline_um" in h]
        covered = set()
        for c in t.get("contents", []):
            io = any(k in c.get("module", "").lower() for k in IO_PHY_RE)
            if "origin_um" not in c or "outline_um" not in c:
                if io and t.get("hard"):
                    x0, y0, x1, y1 = P.rect(part)
                    m = PHY_MARGIN_UM
                    for L in layers:
                        out.append((L, x0 + m, y0 + m, x1 - m, y1 - m, f"keepout {part}.{c['inst']}"))
                continue
            sub = [h for h in cores if h["inst"] == c["inst"] or h["inst"].startswith(c["inst"] + "_")]
            if io:
                r = die_rect(P, part, c["origin_um"], c["outline_um"])
                for L in layers:
                    out.append((L, *r, f"keepout {part}.{c['inst']}"))
                covered.update(h["inst"] for h in sub)
                continue
            if sub:
                continue
            r = die_rect(P, part, c["origin_um"], c["outline_um"])
            for L in ("M4", "M5"):
                out.append((L, *r, f"leaf {part}.{c['inst']}"))
        for h in cores:
            if h["inst"] in covered:
                continue
            r = die_rect(P, part, h["origin_um"], h["outline_um"])
            for i in range(4, core_top.get((tn, h["inst"]), 5) + 1):
                out.append((f"M{i}", *r, f"core {part}.{h['inst']}"))
    # die PG stripes (g2.py die_probe)
    W, H = P.W, P.H
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        if not L:
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = H if L["dir"] == "V" else W
        span = W if L["dir"] == "V" else H
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                r = (a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)
                out.append((g["layer"], *r, "pg"))
            pos += g["pitch_um"]
    nres = 0
    if htree:
        ht = json.loads(Path(htree).read_text())
        nt = int(ht.get("ndr_tracks", 5))
        for s in ht["segments"]:
            x0, y0, x1, y1 = s["xy"]
            ln = s["layer"]
            hw = nt * P.layers[ln]["pitch_um"] / 2.0
            if ln == "M9":
                r = (x0 - hw, min(y0, y1), x0 + hw, max(y0, y1))
            else:
                r = (min(x0, x1), y0 - hw, max(x0, x1), y0 + hw)
            out.append((ln, *r, "htree"))
            nres += 1
    return out


def fmt(v):
    return int(round(v * DBU))


def insert_repeaters(cells, nets, pitch, master):
    """Fixed non-inverting signal buffers; no new register stages or clock sinks."""
    if pitch <= 0:
        return cells, nets
    cells = dict(cells); routed = []
    for k, (name, src, dst, meta) in enumerate(nets):
        a, b = cells[src], cells[dst]
        pts = [(a[0], a[1]), (b[0], a[1]), (b[0], b[1])]
        length = check.plen(pts)
        count = max(0, math.ceil(length / pitch) - 1)
        previous = src
        for j in range(count):
            nm = f"repeater_{k}_{j}"
            x, y = check.point_at(pts, length * (j + 1) / (count + 1))
            cells[nm] = (x, y, a[2], "buf:" + master)
            routed.append((f"{name}_seg{j}", previous, nm, dict(meta, source_net=name)))
            previous = nm
        routed.append((f"{name}_seg{count}" if count else name, previous, dst, dict(meta, source_net=name)))
    return cells, routed


def write_def(P, path, cells, nets, blks, clk_xy):
    W, H = P.W, P.H
    with open(path, "w") as f:
        f.write('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN fabric ;\n'
                f"UNITS DISTANCE MICRONS {DBU} ;\nDIEAREA ( 0 0 ) ( {fmt(W)} {fmt(H)} ) ;\n")
        # tracks: M4..M9 plan tracks; M1..M3 coarse (gcell size)
        for n in ("M9", "M8", "M7", "M6", "M5", "M4"):
            L = P.layers[n]
            o, p = L["offset_um"], L["pitch_um"]
            nx, ny = int((W - o) / p) + 1, int((H - o) / p) + 1
            f.write(f"TRACKS X {fmt(o)} DO {nx} STEP {fmt(p)} LAYER {n} ;\n")
            f.write(f"TRACKS Y {fmt(o)} DO {ny} STEP {fmt(p)} LAYER {n} ;\n")
        for n in ("M3", "M2", "M1"):
            o = GC_PITCH / 2
            nx, ny = int((W - o) / GC_PITCH) + 1, int((H - o) / GC_PITCH) + 1
            f.write(f"TRACKS X {fmt(o)} DO {nx} STEP {fmt(GC_PITCH)} LAYER {n} ;\n")
            f.write(f"TRACKS Y {fmt(o)} DO {ny} STEP {fmt(GC_PITCH)} LAYER {n} ;\n")
        # rows (site asap7sc7p5t 0.054 x 0.27) over the die: repair_design / DPL need them
        nr, ns = int(H / 0.27), int(W / 0.054)
        for r in range(nr):
            f.write(f"ROW row_{r} asap7sc7p5t 0 {fmt(r * 0.27)} {'N' if r % 2 == 0 else 'FS'} DO {ns} BY 1 STEP 54 0 ;\n")
        f.write(f"COMPONENTS {len(cells)} ;\n")
        for nm, (x, y, part, kind) in cells.items():
            x = min(max(x - 0.54, 0.0), W - 1.08)
            y = min(max(y - 0.135, 0.0), H - 0.27)
            master = kind[4:] if kind.startswith("buf:") else FLOP
            f.write(f"- {nm} {master} + PLACED ( {fmt(x)} {fmt(y)} ) N ;\n")
        f.write("END COMPONENTS\n")
        f.write(f"PINS 1 ;\n- clk + NET clk + DIRECTION INPUT + USE CLOCK\n  + LAYER M9 ( -20 0 ) ( 20 320 )\n"
                f"  + PLACED ( {fmt(clk_xy[0])} {fmt(clk_xy[1])} ) N ;\nEND PINS\n")
        f.write(f"BLOCKAGES {len(blks)} ;\n")
        for L, x0, y0, x1, y1, _ in blks:
            f.write(f"- LAYER {L} RECT ( {fmt(x0)} {fmt(y0)} ) ( {fmt(x1)} {fmt(y1)} ) ;\n")
        f.write("END BLOCKAGES\n")
        f.write(f"NETS {len(nets) + 1} ;\n")
        f.write("- clk ( PIN clk )")
        for i, nm in enumerate(cells):
            if cells[nm][3].startswith("buf:"):
                continue
            f.write(f" ( {nm} CLK )")
            if i % 8 == 7:
                f.write("\n")
        f.write(" + USE CLOCK ;\n")
        for nm, drv, rcv, _ in nets:
            dp = "Y" if cells[drv][3].startswith("buf:") else "QN"
            rp = "A" if cells[rcv][3].startswith("buf:") else "D"
            f.write(f"- {nm} ( {drv} {dp} ) ( {rcv} {rp} ) ;\n")
        f.write("END NETS\nEND DESIGN\n")


LIBS = ("asap7sc7p5t_AO_RVT_{c}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz",
        "asap7sc7p5t_OA_RVT_{c}_nldm_211120.lib.gz", "asap7sc7p5t_SIMPLE_RVT_{c}_nldm_211120.lib.gz",
        "asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib")


def tcl(P, adjust, iters, sta=True, repair=True):
    PL = "/OpenROAD-flow-scripts/flow/platforms/asap7"
    t = [f"set PL {PL}", "set t0 [clock seconds]",
         "proc T {tag} { global t0; puts \"OT_T $tag [expr {[clock seconds]-$t0}] s\" }",
         "define_corners TT FF"]
    for c in ("TT", "FF"):
        for lib in LIBS:
            t.append(f"read_liberty -corner {c} $PL/lib/NLDM/{lib.format(c=c)}")
    t += ["read_lef $PL/lef/asap7_tech_1x_201209.lef", "read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef",
          "read_def /work/fabric.def", "T read",
          "source $PL/setRC.tcl"]
    # the partitions' own logic: plan fill is 1.0 (no die channels), so one layer adjustment over the die is the same
    # as a per-partition one.  (A region adjustment RESETS a gcell's capacity to (1-adj) x nominal and so ignores
    # the core / PG obstructions under it: measured -96 % / -173 % 'reduction' on M4 / M5 -- not used.)
    for L in ("M4", "M5", "M6", "M7"):
        t.append(f"set_global_routing_layer_adjustment {L} {adjust:g}")
    t += ["set_routing_layers -signal M4-M9",
          f"global_route -congestion_iterations {iters} -allow_congestion -verbose -skip_large_fanout_nets 5000 "
          "-congestion_report_file /work/grt_congestion.rpt",
          "T grt",
          "write_guides /work/fabric.guide", "T guides",
          "if {[catch {write_db /work/fabric_grt.odb} e]} { puts \"OT_WRITE_DB_FAIL $e\" }",
          "puts OT_GRT_DONE"]
    if sta:
        per = float(P.die["period_ps"])
        t += ["create_clock -name clk -period %.3f [get_ports clk]" % per,
              "set_clock_uncertainty 60 -setup [all_clocks]", "set_clock_uncertainty 25 -hold [all_clocks]",
              "if {[file exists /work/clock_latency.tcl]} { source /work/clock_latency.tcl; puts OT_CLK_LATENCY }",
              "estimate_parasitics -global_routing", "T rc"]
        t += sta_block("grt")
    t.append("puts OT_DONE")
    return "\n".join(t) + "\n"


def repair_tcl(P, wire_layer=None):
    """second job: the same DEF, placement parasitics, repair_design (buffers / resizing for slew, cap, wire length on
    the long ft hops = the repeaters a partition must put on its M8/M9 ft routes), then STA."""
    PL = "/OpenROAD-flow-scripts/flow/platforms/asap7"
    t = [f"set PL {PL}", "set t0 [clock seconds]",
         "proc T {tag} { global t0; puts \"OT_T $tag [expr {[clock seconds]-$t0}] s\" }",
         "define_corners TT FF"]
    for c in ("TT", "FF"):
        for lib in LIBS:
            t.append(f"read_liberty -corner {c} $PL/lib/NLDM/{lib.format(c=c)}")
    per = float(P.die["period_ps"])
    t += ["read_lef $PL/lef/asap7_tech_1x_201209.lef", "read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef",
          "read_def /work/fabric.def", "T read", "source $PL/setRC.tcl"]
    if wire_layer:          # placement parasitics with that layer's RC (the plan routes ft hops on M8 / M9)
        t.append(f"set_wire_rc -signal -layer {wire_layer}")
    t += ["set_routing_layers -signal M4-M9",
          "create_clock -name clk -period %.3f [get_ports clk]" % per,
          "set_clock_uncertainty 60 -setup [all_clocks]", "set_clock_uncertainty 25 -hold [all_clocks]",
          "if {[file exists /work/clock_latency.tcl]} { source /work/clock_latency.tcl; puts OT_CLK_LATENCY }",
          "set_dont_touch [get_nets clk]",
          "estimate_parasitics -placement", "T rc"]
    t += sta_block("place")
    t += ["repair_design -verbose", "T repair", "estimate_parasitics -placement", "T rc2"]
    t += sta_block("repair")
    t += ["puts OT_DONE"]
    return "\n".join(t) + "\n"


def sta_block(tag):
    """OpenSTA 'scenes' (define_corners names them SS/TT/FF): per scene worst slack (slack_only), the worst 200k
    endpoints (-format end), 3 full paths; sign-off = setup TT, hold FF."""
    out = []
    for c, d in (("TT", "max"), ("FF", "min")):
        f = f"/work/sta_{tag}_{c}_{d}"
        out += [f"report_checks -path_delay {d} -scenes {c} -group_path_count 1 -format slack_only > {f}.wns",
                f"report_checks -path_delay {d} -scenes {c} -group_path_count 200000 -endpoint_path_count 1 "
                f"-format end > {f}.end",
                f"report_checks -path_delay {d} -scenes {c} -group_path_count 3 -format full_clock_expanded "
                f"-fields {{cap slew fanout}} -digits 1 > {f}.paths",
                f"T sta_{tag}_{c}_{d}"]
    out += [f"puts \"OT_VIOL {tag} max [sta::endpoint_violation_count max] min [sta::endpoint_violation_count min]\"",
            f"report_tns -max > /work/tns_{tag}.rpt", f"report_tns -min >> /work/tns_{tag}.rpt",
            f"report_check_types -max_slew -max_capacitance -violators > /work/drv_{tag}.rpt",
            f"report_design_area > /work/area_{tag}.rpt"]
    return out


RUN = """#!/bin/bash
# GENERATED by tools/die_trial/fabric.py: die fabric GRT + STA (docker; through ot-run on a 1 TB host)
D=$(cd $(dirname $0) && pwd)
IMAGE=${{OT_ORFS_IMAGE:-{image}}}
DK=docker; $DK ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --name trialhbm-fabric-$$ --cpus={threads} --memory={mem}g --memory-swap={mem}g -v $D:/work -w /work $IMAGE \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads {threads} -no_init -exit /work/fabric.tcl > /work/fabric.log 2>&1; echo EXIT \\$? >> /work/fabric.log; chmod -R a+rwX /work"
tail -5 $D/fabric.log
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("plan")
    g.add_argument("--out", required=True)
    g.add_argument("--htree")
    g.add_argument("--adjust", type=float, default=0.5)
    g.add_argument("--iters", type=int, default=50)
    g.add_argument("--mem", type=int, default=256)
    g.add_argument("--threads", type=int, default=32)
    g.add_argument("--no-sta", action="store_true")
    g.add_argument("--no-repair", action="store_true")
    g.add_argument("--wire-layer", help="repair job: placement RC of this layer (e.g. M8) instead of setRC's average")
    g.add_argument("--repeater-pitch", type=float, default=0, help="insert non-inverting data repeaters at this maximum Manhattan pitch (um); geometry review still required")
    g.add_argument("--repeater-master", default="BUFx12_ASAP7_75t_R")
    g.add_argument("--window", help="x0,y0,x1,y1: keep only nets with both ends inside (smoke test)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    P = S.Plan(raw)
    plan_dir = Path(a.plan).resolve().parent
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cells, nets = build(P, plan_dir)
    if a.window:
        x0, y0, x1, y1 = map(float, a.window.split(","))
        inside = lambda n: x0 <= cells[n][0] <= x1 and y0 <= cells[n][1] <= y1  # noqa: E731
        nets = [n for n in nets if inside(n[1]) and inside(n[2])]
        used = {n[1] for n in nets} | {n[2] for n in nets}
        cells = {k: v for k, v in cells.items() if k in used}
    cells, nets = insert_repeaters(cells, nets, a.repeater_pitch, a.repeater_master)
    blks = blockages(P, plan_dir, a.htree)
    root = P.clock.get("spine", {}).get("root_um") or [P.W / 2, P.H / 2]
    write_def(P, out / "fabric.def", cells, nets, blks, root)
    (out / "fabric.tcl").write_text(tcl(P, a.adjust, a.iters, not a.no_sta, not a.no_repair))
    (out / "run.sh").write_text(RUN.format(image=IMAGE, threads=a.threads, mem=a.mem))
    os.chmod(out / "run.sh", 0o755)
    (out / "repair.tcl").write_text(repair_tcl(P, a.wire_layer))
    (out / "run_repair.sh").write_text(RUN.format(image=IMAGE, threads=a.threads, mem=a.mem)
                                       .replace("fabric.tcl", "repair.tcl").replace("fabric.log", "repair.log"))
    os.chmod(out / "run_repair.sh", 0o755)
    # metadata: per net hop length (Manhattan, driver -> receiver) + kind
    hop = []
    for nm, d, r, m in nets:
        (xa, ya, pa, _), (xb, yb, pb, _) = cells[d], cells[r]
        hop.append(dict(net=nm, drv=d, rcv=r, len_um=round(abs(xa - xb) + abs(ya - yb), 1), src=pa, dst=pb, **m))
    by = defaultdict(int)
    for b in blks:
        by[b[5].split()[0]] += 1
    lens = sorted(h["len_um"] for h in hop)
    summ = dict(plan=str(Path(a.plan).resolve()), die=P.name, cells=len(cells), nets=len(nets),
                bf=sum(1 for c in cells.values() if c[3] == "bf"), st=sum(1 for c in cells.values() if c[3] == "st"),
                repeaters=sum(1 for c in cells.values() if c[3].startswith("buf:")), repeater_pitch_um=a.repeater_pitch,
                blockages=dict(by), adjust=a.adjust, htree=a.htree, window=a.window,
                hop_um=dict(max=lens[-1] if lens else 0, p50=lens[len(lens) // 2] if lens else 0,
                            p90=lens[int(0.9 * (len(lens) - 1))] if lens else 0,
                            over_500=sum(1 for x in lens if x > 500), over_850=sum(1 for x in lens if x > 850)))
    (out / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    with open(out / "nets.tsv", "w") as f:
        f.write("net\tkind\tsrc\tdst\tlen_um\tport_or_slot\n")
        for h in hop:
            f.write(f"{h['net']}\t{h['kind']}\t{h['src']}\t{h['dst']}\t{h['len_um']}\t{h.get('port', h.get('slot'))}\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
