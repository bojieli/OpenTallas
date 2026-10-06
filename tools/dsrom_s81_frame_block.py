#!/usr/bin/env python3
"""DS-ROM S81 field column frame as ONE hardened block (CLAUDE S81-RERUN, item 10, 2026-10-06).

The S81 die is a symmetric array of 128 column frames (AGENTS rule 2: floorplan, one hardened element, replicate).
The die-top paths inside a frame -- column FIFO, slot stations, q-element boundary banks, cfg sequencers and ROMs,
column relays, the ragged return tree and its root stages -- are common-clock paths on the frame's column clock root,
so they are closed by routing ONE frame with real macros (q element: routed abstract + its extracted timing model;
cfg ROM: compiler views) and the generated glue RTL at the generator's positions, with CTS, then SS / FF corner STA.

    python3 tools/dsrom_s81_frame_block.py emit --rev r9 --elem-h 198.72 --pairs 2050 [--frame N] --out DIR

DIR (inside the source tree) receives: frame.v (top dsfd_frame), bf_placeholder.sv (registered-IO placeholder for the
BF owner block), q_bb.v (q-element black box), views/<q>/ (routed LEF + ETM libs, from --q-etm-dir), place.tcl
(POST_MACRO_PLACE: macros at the generator's positions, glue fenced at its boxes), frame.sdc (forwarded x-stream
clock of the column FIFO's write side, meso phase-window budget), launch.sh (tools/run_abi3_physical.py), frame.json.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def lib_pin_dirs(lib):
    """pin -> direction of a liberty cell (bus members expanded)"""
    out = {}
    for pm in re.finditer(r'\n\s*(pin|bus)\("?([^")]+)"?\)\s*\{\s*\n(?:\s*bus_type : (\w+);\s*\n)?\s*direction : (\w+);', lib):
        kind, name, btype, d = pm.groups()
        if kind == "bus":
            t = re.search(r'type \("?%s"?\) \{(.*?)\}' % re.escape(btype), lib, re.S).group(1)
            w = int(re.search(r"bit_width : (\d+)", t).group(1))
            for i in range(w):
                out[f"{name}[{i}]"] = d
        else:
            out[name] = d
    return out


def esc(pn):
    return pn if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", pn) else "\\" + pn + " "


def build(a):
    import dsrom_s81_fulldie as S
    S.REV = a.rev
    S.set_cc_reach(a.cc_reach_um)
    if a.q_lef:
        S.Q_LEF = a.q_lef
    S.configure(a.die, "r8")
    S.slot_geometry(a.elem_h)
    if a.die != "head" and a.pairs:
        S.set_pairs(a.pairs)
    m = S.build()
    S.finalize_r8(m)
    return S, m


def pick_frame(m):
    """the field frame with the most q elements, then the most slots, then the most column relays"""
    rl = defaultdict(int)
    for it in m["insts"]:
        if it.kind == "rly":
            rl[it.region] += 1
    best = None
    for r, f in m["frames"].items():
        if f.get("bundles"):
            continue
        nq = sum(1 for _, k, _, _ in f["elems"] if k == "q")
        key = (nq, f["last_slot"], rl[f"frame_{r}"], -r)
        if best is None or key > best[0]:
            best = (key, r)
    return best[1]


def emit(a):
    S, m = build(a)
    r = a.frame if a.frame is not None else pick_frame(m)
    f = m["frames"][r]
    reg = f"frame_{r}"
    insts = [it for it in m["insts"] if it.region == reg]
    F = {it.name for it in insts}
    by = {it.name: it for it in m["insts"]}
    cf = by[f"cf{r}"]
    x0 = f["x"]
    yb = S.dn(cf.y - 4.32, S.GY)
    top = max(it.y + it.h for it in insts)
    H = S.up(max(top, f["y"] + S.SLOTS8 * S.SLOT_H8) + 2.16 - yb, S.GY)
    W = S.COL_W8
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rp = S.real_ports()
    pdir = m["pdir"]
    # ---- nets: internal, or a frame port
    ports, nets, conns = {}, [], defaultdict(list)
    rename = {"clk_stream": "ck", "rst_stream": "rst"}
    for bid, cls, bits, eps in m["buses"]:
        ins = [e for e in eps if e[0] in F]
        if not ins:
            continue
        outside = [e for e in eps if e[0] not in F]
        net = f"n_{bid}"
        if outside:
            drv_in = eps[0][0] in F
            pname = rename.get(bid) or {("input", "fclk"): "xf", ("input", "lane"): "xd", ("output", "fclk"): "rf",
                                        ("output", "lane"): "rd"}.get(("output" if drv_in else "input", cls),
                                                                      "p_" + re.sub(r"\W", "_", bid))
            assert pname not in ports, (pname, bid)
            ports[pname] = ("output" if drv_in else "input", bits, bid, cls)
            net = pname
        else:
            nets.append((net, bits))
        for inst, port in ins:
            mst = by[inst].master
            if mst in rp and port in rp[mst]:
                conns[inst].append((rp[mst][port][:bits], net))
            else:
                conns[inst].append((port, net, bits))
    # ---- q-element pins the generator does not bind (PQ element ot_v41_rom_elem_q_qxpq_w10: go_tag in, walking /
    # bank_free / sh_free out): one registered glue block per element at those pins, so every q pin is timed against a
    # die register; the outputs fold into the observed frame port pqs (no die consumer yet: owner PQ q-element)
    qn0 = S.real_lef(S.Q_LEF)["name"]
    qdirs = lib_pin_dirs((Path(a.q_etm_dir) / f"{qn0}_ss.lib").read_text())
    pqx, qins = [], [it for it in insts if it.master == qn0]
    for it in qins:
        bound = {"clk"}
        for c in conns.get(it.name, []):
            if isinstance(c[0], list):
                bound.update(c[0])
        ex = sorted(p_ for p_ in qdirs if p_ not in bound and p_ not in ("VDD", "VSS"))
        if not ex:
            continue
        ei = [p_ for p_ in ex if qdirs[p_] == "input"]
        eo = [p_ for p_ in ex if qdirs[p_] == "output"]
        k = len(pqx)
        if ei:
            nets.append((f"n_pqi{k}", len(ei)))
            conns[it.name].append((ei, f"n_pqi{k}"))
        if eo:
            nets.append((f"n_pqo{k}", len(eo)))
            conns[it.name].append((eo, f"n_pqo{k}"))
        pqx.append((it, ei, eo, k))
    if pqx:
        ports["pqs"] = ("output", len(pqx), "pqs", "obs")
    V = ["// GENERATED by tools/dsrom_s81_frame_block.py (CLAUDE S81-RERUN): one S81 field column frame",
         f"// die {a.die}, rev {a.rev}, element frame {a.elem_h} um, frame {r} ({f['half']} tier {f['tier']} col {f['col']})",
         "module dsfd_frame (" + ", ".join(sorted(ports)) + ");"]
    for p_, (d, b, _, _) in sorted(ports.items()):
        V.append(f"  {d} wire [{b - 1}:0] {p_};")
    for n_, b in nets:
        V.append(f"  wire [{b - 1}:0] {n_};")
    for it in insts:
        parts, bus_bits = [], defaultdict(dict)
        for c in conns.get(it.name, []):
            if isinstance(c[0], list):
                names, net = c
                for i, pn in enumerate(names):
                    mm = re.match(r"^(.*)\[(\d+)\]$", pn)
                    if mm:
                        bus_bits[mm.group(1)][int(mm.group(2))] = f"{net}[{i}]"
                    else:
                        parts.append(f".{esc(pn)}({net}[{i}])")
            else:
                port, net, n = c
                parts.append(f".{port}({net})")
        for base, bits_ in bus_bits.items():
            hi = max(bits_)
            cat = ", ".join(bits_.get(j, "1'b0") for j in range(hi, -1, -1))
            parts.append(f".{esc(base)}({{{cat}}})")
        V.append(f"  {it.master} {it.name} (" + ", ".join(parts) + ");")
    PX = []
    for it, ei, eo, k in pqx:
        ni, no = len(ei), len(eo)
        cn = [".ck(ck[0])"] + ([f".di(n_pqi{k})"] if ni else []) + ([f".do_i(n_pqo{k})", f".ob(pqs[{k}])"] if no else [])
        V.append(f"  dsfd_pqx_{k} px_{it.name} ({', '.join(cn)});")
        body = [f"module dsfd_pqx_{k} (input wire ck" + (f", output wire [{ni - 1}:0] di" if ni else "")
                + (f", input wire [{no - 1}:0] do_i, output wire ob" if no else "") + ");"]
        if ni:
            body += [f"    reg [{ni - 1}:0] r;",
                     (f"    always @(posedge ck) r <= {{r[{ni - 2}:0], r[{ni - 1}]}} ^ r ^ {ni}'d{(k % ((1 << ni) - 1)) + 1};"
                      if ni > 1 else "    always @(posedge ck) r <= ~r;"), "    assign di = r;"]
        if no:
            body += [f"    reg [{no - 1}:0] c; reg o;", "    always @(posedge ck) begin c <= do_i; o <= ^c; end", "    assign ob = o;"]
        body.append("endmodule")
        PX.append("\n".join(body))
    V.append("endmodule\n")
    (out / "frame.v").write_text("\n".join(V + PX) + "\n")
    # ---- BF placeholder: registered IO (the BF owner block is not built); every input reaches an output
    masters = sorted({it.master for it in insts})
    ph = ["// GENERATED (CLAUDE S81-RERUN): BF-element PLACEHOLDER with registered IO (owner block not built).",
          "// Its ports are the S81 die's BF binding; its contract here is: every input captured by a flop at the",
          "// pin, every output driven by a flop.  The real BF element must meet the same contract.", ""]
    for mst in masters:
        if mst not in ("dsfd_bf", "dsfd_bfnv"):
            continue
        pd = pdir[mst]
        ins_ = [(p_, b) for p_, (d, b) in sorted(pd.items()) if d == "input" and p_ not in ("ck", "rs")]
        outs_ = [(p_, b) for p_, (d, b) in sorted(pd.items()) if d == "output"]
        ph.append(f"module {mst} (")
        ph.append(",\n".join(f"    {d} wire [{b - 1}:0] {p_}" for p_, (d, b) in sorted(pd.items())))
        ph.append(");")
        tot = sum(b for _, b in ins_)
        ph.append(f"    reg [{tot - 1}:0] qi;")
        ph.append("    always @(posedge ck[0]) qi <= {" + ", ".join(p_ for p_, _ in ins_) + "};")
        for p_, b in outs_:
            # fold every input bit into each output bit position (XOR of b-bit slices of the captured word)
            k = math.ceil(tot / b)
            pad = k * b - tot
            ph.append(f"    wire [{k * b - 1}:0] w_{p_} = " + (f"{{{pad}'d0, qi}};" if pad else "qi;"))
            terms = " ^ ".join(f"w_{p_}[{(j + 1) * b - 1}:{j * b}]" for j in range(k))
            ph.append(f"    reg [{b - 1}:0] q_{p_}; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) q_{p_} <= {b}'d0; "
                      f"else q_{p_} <= {terms};")
            ph.append(f"    assign {p_} = q_{p_};")
        ph.append("endmodule\n")
    (out / "bf_placeholder.sv").write_text("\n".join(ph))
    # ---- q element: black box + macro view (routed LEF + ETM)
    rq = S.real_lef(S.Q_LEF)
    qn = rq["name"]
    vq = out / "views" / qn
    vq.mkdir(parents=True, exist_ok=True)
    (vq / f"{qn}.lef").write_text(S._lef_text(S.Q_LEF))
    etm = Path(a.q_etm_dir)
    for c in ("ss", "ff"):
        shutil.copy(etm / f"{qn}_{c}.lib", vq / f"{qn}_{c}.lib")
    shutil.copy(etm / f"{qn}_ss.lib", vq / f"{qn}_tt.lib")       # TT is not a sign-off corner; the SS model stands in
    lib = (etm / f"{qn}_ss.lib").read_text()
    bb = [f"(* blackbox *) module {qn} ("]
    pl = []
    for pm in re.finditer(r'\n    (pin|bus)\("([^"]+)"\)\s*\{\s*\n(?:\s*bus_type : (\w+);\s*\n)?\s*direction : (\w+);', lib):
        kind, name, btype, d = pm.groups()
        if kind == "bus":
            t = re.search(r'type \("%s"\) \{(.*?)\}' % re.escape(btype), lib, re.S).group(1)
            w = int(re.search(r"bit_width : (\d+)", t).group(1))
            pl.append(f"  {d} wire [{w - 1}:0] {name}")
        elif "[" not in name and name not in ("VDD", "VSS"):
            pl.append(f"  {d} wire {name}")
    bb.append(",\n".join(pl))
    bb.append(");\nendmodule\n")
    (out / "q_bb.v").write_text("\n".join(bb))
    # ---- placement hook: macros at the generator's positions (snap lattice), glue fenced at its boxes
    macros = [it for it in insts if it.master in (qn, S.real_lef(S.CFG_LEF)["name"])]
    soft = [it for it in insts if it not in macros]
    T = ["# GENERATED (CLAUDE S81-RERUN): POST_MACRO_PLACE hook of the S81 frame block",
         "source /src/physical/common/ot_macro_track_snap.tcl",
         "set _blk [ord::get_db_block]", "set _dbu [ot_mts::get_dbu]", "set _sg [ot_mts::site_grid]",
         "proc ot_find {nm} { global _blk; set i [$_blk findInst $nm]; if {$i eq \"NULL\"} { error \"no inst $nm\" }; return $i }",
         "proc fplace {nm x y o} { global _blk _dbu _sg; set i [ot_find $nm]; set m [$i getMaster]",
         "  lassign $_sg gx gw gy gh; set r [ot_mts::rule $m $o]",
         "  lassign [dict get $r x] Px Sx; lassign [dict get $r y] Py Sy",
         '  set px [expr {double([ot_mts::snap_axis [expr {round($x*$_dbu)}] $gx $gw $Px $Sx "$nm x"])/$_dbu}]',
         '  set py [expr {double([ot_mts::snap_axis [expr {round($y*$_dbu)}] $gy $gh $Py $Sy "$nm y"])/$_dbu}]',
         "  $i setPlacementStatus PLACED; $i setOrient $o; $i setLocation [expr {round($px*$_dbu)}] [expr {round($py*$_dbu)}]; $i setPlacementStatus FIRM }"]
    for it in macros:
        T.append(f"fplace {it.name} {it.x - x0:.3f} {it.y - yb:.3f} {it.orient}")
    T += ["set nb 0; foreach b [$_blk getBlockages] { odb::dbBlockage_destroy $b; incr nb }",
          'puts "OT_FRAME_PLACE macros=[llength [list ' + " ".join(i.name for i in macros[:1]) + ']] blockages_removed=$nb"',
          "set fence [dict create]"]
    for it in soft:
        bx = (max(0.0, it.x - x0 - 1.08), max(0.0, it.y - yb - 1.08), min(W, it.x - x0 + it.w + 1.08),
              min(H, it.y - yb + it.h + 1.08))
        T.append(f"dict set fence {it.name} {{{bx[0]:.3f} {bx[1]:.3f} {bx[2]:.3f} {bx[3]:.3f}}}")
    for it, ei, eo, k in pqx:
        ps = [rq["pins"][p_][1] for p_ in ei + eo if p_ in rq["pins"]]
        px_ = sum((r_[0] + r_[2]) / 2 for r_ in ps) / len(ps)
        py_ = sum((r_[1] + r_[3]) / 2 for r_ in ps) / len(ps)
        # pin position in frame coordinates (the element's orientation flips its pin map)
        fx = it.x - x0 + (it.w - px_ if it.orient in ("MY", "R180") else px_)
        fy = it.y - yb + (it.h - py_ if it.orient in ("MX", "R180") else py_)
        fy += -8.0 if fy < it.y - yb + it.h / 2 else 8.0
        T.append(f"dict set fence px_{it.name} {{{max(0.5, fx - 10):.3f} {max(0.5, fy - 4):.3f} {min(W - 0.5, fx + 10):.3f} {min(H - 0.5, fy + 4):.3f}}}")
    T += ["set regs [dict create]",
          "dict for {nm box} $fence {",
          "  set rg [odb::dbRegion_create $_blk fence_$nm]",
          "  lassign $box a b c d",
          "  odb::dbBox_create $rg [expr {round($a*$_dbu)}] [expr {round($b*$_dbu)}] [expr {round($c*$_dbu)}] [expr {round($d*$_dbu)}]",
          "  dict set regs $nm $rg }",
          "set nf 0; set nfree 0",
          "foreach inst [$_blk getInsts] {",
          "  if {[[$inst getMaster] isBlock]} { continue }",
          "  set n [string map {\\\\ {}} [$inst getName]]",
          "  set p [lindex [split $n ./] 0]",
          "  if {[dict exists $regs $p]} { [dict get $regs $p] addInst $inst; incr nf } else { incr nfree } }",
          'puts "OT_FRAME_FENCE fenced=$nf free=$nfree regions=[dict size $regs]"']
    (out / "place.tcl").write_text("\n".join(T) + "\n")
    # ---- SDC (appended to the driver's: ck = the column clock root at 0.833 ns, 60 / 25 ps)
    xin = [p_ for p_, v in ports.items() if v[0] == "input" and v[3] == "fclk"]
    xdat = [p_ for p_, v in ports.items() if v[0] == "input" and v[3] == "lane"]
    oclk = [p_ for p_, v in ports.items() if v[0] == "output" and v[3] == "fclk"]
    odat = [p_ for p_, v in ports.items() if v[0] == "output" and v[3] == "lane"]
    sd = ["# GENERATED (CLAUDE S81-RERUN): S81 frame block -- the column FIFO's forwarded write clock (x stream from the",
          "# trunk tap station) and the meso phase-window budget of physical/rom_clock/meso_ring_w512_d4.sdc"]
    for p_ in xin:
        sd.append(f"create_clock -name xf -period 833.333 [get_ports {{{p_}}}]")
    sd += ["set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]"]
    if xin:
        ck = "[get_clocks {ck clk core_clk}]"
        sd += ["set _ck [get_clocks -quiet {core_clk clk ck}]",
               "set_max_delay -ignore_clock_latency 356.667 -from [get_clocks xf] -to $_ck",
               "set_max_delay -ignore_clock_latency 356.667 -from $_ck -to [get_clocks xf]",
               "set_min_delay -ignore_clock_latency 0 -from [get_clocks xf] -to $_ck",
               "set_min_delay -ignore_clock_latency 0 -from $_ck -to [get_clocks xf]"]
        for p_ in xdat:
            sd.append(f"set_input_delay 166.666 -clock xf [get_ports {{{p_}[*]}}]")
    for p_ in oclk:
        sd.append(f"# {p_}: forwarded return clock (= the column clock) leaves with its data")
    if pqx:
        sd.append("# pqs: observation of the PQ element status pins (no die consumer yet), not a die path")
        sd.append("set_false_path -to [get_ports pqs*]")
    (out / "frame.sdc").write_text("\n".join(sd) + "\n")
    # ---- pin regions: x stream at the column FIFO's S-face x pins, return at its rf / rd pins, clock / reset beside
    cfx = cf.x - x0
    rec = dict(schema="opentallas.dsrom-s81-frame-block.v1", tool="tools/dsrom_s81_frame_block.py",
               die=a.die, rev=a.rev, cc_reach_um=S.CC_REACH, elem_h=a.elem_h, pairs=a.pairs, frame=r, half=f["half"], tier=f["tier"],
               col=f["col"], origin_um=[x0, yb], size_um=[round(W, 3), round(H, 3)], q_lef=S.Q_LEF,
               q_etm_dir=str(a.q_etm_dir), instances=defaultdict(int), ports={p_: v[:2] for p_, v in ports.items()},
               pin_x_um=dict(x=round(cfx + S.SSTN_X + S.SSTN_WH[0] / 2 - S.CF_X, 2), ret=round(S.COL_W8 - S.RSC_W / 2, 2)),
               relays_x=f.get("relay_x"), relays_ret=f.get("relay_ret"), bank_stages=f.get("bank_stages"))
    for it in insts:
        rec["instances"][it.kind] += 1
    (out / "frame.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    rel = out.resolve().relative_to(ROOT.resolve())
    px, pr = rec["pin_x_um"]["x"], rec["pin_x_um"]["ret"]
    rom = S.real_lef(S.CFG_LEF)["name"]
    srcs = [f"{rel}/frame.v", f"{rel}/bf_placeholder.sv", f"{rel}/q_bb.v",
            S.GLUE_RTL.replace("/r8/", f"/{S.out_rev()}/"), S.CFG7_RTL, "rtl/common/ot_meso_fifo.sv",
            "rtl/v41die/ot_v41_retn_w17w10.sv", "rtl/v41rom/ot_v41_ret.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
            "rtl/hdc/ot_hdc_delay.sv", "rtl/common/ot_fwd_link_stage.sv", "rtl/common/ot_ratio_cdc_fifo.sv",
            str(Path(S.CFG_LEF).parent / f"{rom}_bb.v")]
    L = ["#!/bin/bash", "# GENERATED by tools/dsrom_s81_frame_block.py (CLAUDE S81-RERUN): route the S81 frame block.",
         "# usage: WT=<pinned clean worktree> J=<job dir> [V=<variant tag>] [EXTRA ORFS args via ARGS] launch.sh",
         "set -e", ': "${WT:?worktree}" "${J:?job dir}"', "mkdir -p $J; cd $WT",
         'test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }',
         "exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \\",
         " --persistent-workdir $J/work --launch-receipt $J/receipt.json \\",
         " --view asap7 --top dsfd_frame " + " ".join(f"--source {x}" for x in srcs) + " \\",
         f" --macro-view {qn}={rel}/views/{qn} --macro-view {rom}={Path(S.CFG_LEF).parent} \\",
         " --clock-port ck --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 "
         "--io-delay-fraction 0.2 --stages pnr \\",
         f" --die-area 0 0 {W:.3f} {H:.3f} --core-area 0 0.27 {W:.3f} {H - 0.27:.3f} --place-density ${{PD:-0.45}} "
         "--macro-place-halo 2 2 \\",
         f' --pin-region "^(xf|xd).*=bottom:{px - 60:.2f}-{px + 60:.2f}" --pin-region "^(rf|rd).*=bottom:{pr - 40:.2f}-{pr + 20:.2f}"'
         f' --pin-region "^(ck|rst).*=bottom:{px + 80:.2f}-{px + 120:.2f}"' + (f' --pin-region "^pqs.*=top:20-{W - 20:.0f}"' if pqx else "") + ' \\',
         " --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns ${HM:-0.02} \\",
         f" --step-tcl POST_MACRO_PLACE={rel}/place.tcl --sdc-append {rel}/frame.sdc \\",
         " --orfs-var SYNTH_HDL_FRONTEND=slang --orfs-var NUM_CORES=${CORES:-24} --orfs-var SETUP_SLACK_MARGIN=${SM:-15} --hold-corners WC,BC \\",
         " --orfs-corner WC --pnr-stop-after ${STOP:-finish} --nickname-tag s81frame_${V:-a}_20261006 \\",
         ' --output $J/out ${ARGS:-} > $J/launch.log 2>&1']
    (out / "launch.sh").write_text("\n".join(L) + "\n")
    os.chmod(out / "launch.sh", 0o755)
    print(json.dumps(dict(frame=r, size=rec["size_um"], instances=rec["instances"], ports=len(ports),
                          nets=len(nets)), default=str))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit")
    p.add_argument("--die", default="layer", choices=["layer", "layer1", "head"])
    p.add_argument("--rev", default="r9")
    p.add_argument("--elem-h", type=float, default=198.72)
    p.add_argument("--pairs", type=int, default=2050)
    p.add_argument("--frame", type=int)
    p.add_argument("--q-lef", default=os.environ.get("OT_S81_Q_LEF"))
    p.add_argument("--q-etm-dir", required=True)
    p.add_argument("--cc-reach-um", type=float, help="MARGIN-FIRST common-clock hop cap (tools/dsrom_s81_fulldie.py)")
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    return emit(a)


if __name__ == "__main__":
    raise SystemExit(main())
