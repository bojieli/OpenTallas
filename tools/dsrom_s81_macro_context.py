#!/usr/bin/env python3
"""Die-context STA vehicle for ONE hard block abstract (CLAUDE S81-RERUN, item 10; owner rule MARGIN-FIRST 2026-10-06).

Owner addendum: a block closure must survive die integration.  The PQ spine, the PQ q-element and every new block view
arrive with a routed LEF + SS / FF extracted timing models and register-to-register boundaries; before adoption they are
timed in die context.  This vehicle places the abstract (FIRM, on the macro track lattice) and, for every signal pin, a
die register at the distance the die puts its nearest station / bank (--hop-um, straight out of the pin's face), all on
one clock tree, then routes the whole thing with CTS (tools/run_abi3_physical_aligned.py) and signs off SS setup / FF
hold at 833.333 ps with 60 / 25 ps uncertainty.  Every timed path is therefore a die boundary path:
  input pin  : die register (self-feeding ring, so nothing is constant) -> wire -> block pin -> block's first flop (ETM)
  output pin : block's last flop (ETM) -> block pin -> wire -> die register (XOR-folded per bin into one observed flop)
Run it at the bank distance (--hop-um ~20: r9 q-element banks) and at the station reach (--hop-um 400: a die station
430.56 um away less pin spread) to bracket the die.

    python3 tools/dsrom_s81_macro_context.py emit --lef L --lib-dir D [--cell C] [--clock-pin clk] \
        [--hop-um 400] [--bin-um 20] --out physical/dsrom_s81_ctx/<tag>
    (WT=<pinned worktree> J=<job dir> V=<tag> <out>/launch.sh on a compute host)

--lib-dir holds <cell>_ss.lib and <cell>_ff.lib (write_timing_model of the routed block); they are copied into
<out>/views/<cell>/ with the LEF so the run is source-pinned.
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
GX, GY = 0.216, 0.270          # ASAP7 site width / row height (um)


def lef_text(p):
    p = Path(p)
    return gzip.decompress(p.read_bytes()).decode() if p.suffix == ".gz" else p.read_text()


def parse_lef(t):
    name = re.search(r"^MACRO (\S+)", t, re.M).group(1)
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t).groups())
    pins = {}
    for pm in re.finditer(r"\n  PIN (\S+)\n(.*?)\n  END \1", t, re.S):
        body = pm.group(2)
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        rm = re.search(r"LAYER (\S+) ;\s+RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", body)
        dm = re.search(r"DIRECTION (\w+)", body)
        pins[pm.group(1)] = dict(layer=rm.group(1), rect=tuple(float(v) for v in rm.groups()[1:]),
                                 dir=(dm.group(1).lower() if dm else None))
    return name, w, h, pins


def lib_dirs(lib):
    """pin -> direction from a liberty file (bus members expanded)"""
    out = {}
    for pm in re.finditer(r'\n\s*(pin|bus)\("?([^")]+)"?\)\s*\{\s*\n(?:\s*bus_type : (\w+);\s*\n)?\s*direction : (\w+);', lib):
        kind, name, btype, d = pm.groups()
        if kind == "bus":
            t = re.search(r'type \("?%s"?\) \{(.*?)\}' % re.escape(btype), lib, re.S).group(1)
            w = int(re.search(r"bit_width : (\d+)", t).group(1))
            lo = int(re.search(r"bit_from : (\d+)", t).group(1)) if "bit_from" in t else w - 1
            hi = int(re.search(r"bit_to : (\d+)", t).group(1)) if "bit_to" in t else 0
            for i in range(min(lo, hi), max(lo, hi) + 1):
                out[f"{name}[{i}]"] = d
        else:
            out[name] = d
    return out


def esc(n):
    return n if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", n) else "\\" + n + " "


def up(v, g):
    return math.ceil(v / g - 1e-9) * g


def emit(a):
    lef_rel = a.lef
    t = lef_text(ROOT / lef_rel)
    name, w, h, pins = parse_lef(t)
    cell = a.cell or name
    libd = Path(a.lib_dir)
    ss, ff = libd / f"{cell}_ss.lib", libd / f"{cell}_ff.lib"
    dirs = lib_dirs(ss.read_text())
    out = Path(a.out)
    vd = out / "views" / cell
    vd.mkdir(parents=True, exist_ok=True)
    (vd / f"{cell}.lef").write_text(t)
    shutil.copy(ss, vd / f"{cell}_ss.lib")
    shutil.copy(ff, vd / f"{cell}_ff.lib")
    shutil.copy(ss, vd / f"{cell}_tt.lib")                     # TT is not a sign-off corner: the SS model stands in
    hop, M = a.hop_um, a.hop_um + a.margin_um
    W, H = up(w + 2 * M, GX * 5), up(h + 2 * M, GY * 2)
    mx, my = up((W - w) / 2, 0.048 * 10), up((H - h) / 2, GY * 2)
    sig = [p for p in pins if p != a.clock_pin and dirs.get(p) in ("input", "output")]
    missing = [p for p in pins if p != a.clock_pin and p not in dirs]
    # face of each pin = nearest macro edge; bin along the face
    bins = defaultdict(list)
    for p in sig:
        x0, y0, x1, y1 = pins[p]["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d = dict(W=cx, E=w - cx, S=cy, N=h - cy)
        f = min(d, key=d.get)
        along = cy if f in "WE" else cx
        bins[(f, int(along // a.bin_um))].append((p, cx, cy))
    V = [f"// GENERATED by tools/dsrom_s81_macro_context.py (CLAUDE S81-RERUN): die-context STA vehicle of {cell}",
         f"// die registers {hop} um out of each pin face (bins of {a.bin_um} um); every path is a block boundary path"]
    mods, inst, nets, conn = [], [], [], []
    obs = []
    fences = {}
    for k, ((f, b), pl) in enumerate(sorted(bins.items())):
        bn = f"b{f}{b}"
        ins = [p for p, _, _ in pl if dirs[p] == "input"]
        outs = [p for p, _, _ in pl if dirs[p] == "output"]
        ni, no = len(ins), len(outs)
        ports = ["input wire ck"]
        if ni:
            ports.append(f"output wire [{ni - 1}:0] di")
        if no:
            ports.append(f"input wire [{no - 1}:0] do_i")
            ports.append("output wire ob")
        body = [f"module ctx_{bn} ({', '.join(ports)});"]
        if ni:
            # a ring of distinct flops: each one's next state depends on its neighbour, so none is constant or merged
            body += [f"    reg [{ni - 1}:0] r;",
                     f"    always @(posedge ck) r <= {{r[{ni - 2}:0], r[{ni - 1}]}} ^ r ^ {ni}'d{(k * 2654435761) % (1 << min(ni, 31))};"
                     if ni > 1 else "    always @(posedge ck) r <= ~r;",
                     "    assign di = r;"]
        if no:
            body += [f"    reg [{no - 1}:0] c; reg o;",
                     "    always @(posedge ck) begin c <= do_i; o <= ^c; end",
                     "    assign ob = o;"]
        body.append("endmodule")
        mods.append("\n".join(body))
        cn = [".ck(ck)"]
        if ni:
            nets.append(f"  wire [{ni - 1}:0] di_{bn};")
            cn.append(f".di(di_{bn})")
            for i, p in enumerate(ins):
                conn.append((p, f"di_{bn}[{i}]"))
        if no:
            nets.append(f"  wire [{no - 1}:0] do_{bn};")
            cn.append(f".do_i(do_{bn})")
            for i, p in enumerate(outs):
                conn.append((p, f"do_{bn}[{i}]"))
            cn.append(f".ob(obs[{len(obs)}])")
            obs.append(bn)
        inst.append(f"  ctx_{bn} {bn} ({', '.join(cn)});")
        # fence: the bin's span along the face, a band `hop` um out of the face
        xs = [cx for _, cx, _ in pl]
        ys = [cy for _, _, cy in pl]
        dep = max(4.0, a.bin_um / 2)
        if f in "WE":
            lo, hi = my + b * a.bin_um, my + (b + 1) * a.bin_um
            xc = mx - hop if f == "W" else mx + w + hop
            box = (xc - dep, lo, xc + dep, hi)
        else:
            lo, hi = mx + b * a.bin_um, mx + (b + 1) * a.bin_um
            yc = my - hop if f == "S" else my + h + hop
            box = (lo, yc - dep, hi, yc + dep)
        fences[bn] = tuple(round(min(max(v, 0.5), (W if i % 2 == 0 else H) - 0.5), 3) for i, v in enumerate(box))
    top = ["module ctx_top (ck, obs);", "  input wire ck;", f"  output wire [{max(len(obs), 1) - 1}:0] obs;"] + nets + inst
    mc, busc = [f".{esc(a.clock_pin)}(ck)"], defaultdict(dict)
    for p, n in conn:
        bm = re.match(r"^(.*)\[(\d+)\]$", p)
        if bm:
            busc[bm.group(1)][int(bm.group(2))] = n
        else:
            mc.append(f".{esc(p)}({n})")
    for base, bits in sorted(busc.items()):
        hi_, lo_ = max(bits), min(bits)
        mc.append(f".{esc(base)}({{" + ", ".join(bits.get(j, "1'b0") for j in range(hi_, lo_ - 1, -1)) + "})")
    top.append(f"  {cell} u_blk ({', '.join(mc)});")
    top.append("endmodule")
    (out / "ctx.v").write_text("\n".join(V + mods + top) + "\n")
    bb = [f"(* blackbox *) module {cell} ("]
    pl_ = sorted(set(re.sub(r"\[\d+\]$", "", p) for p in list(dirs) + [a.clock_pin]) - {"VDD", "VSS"})
    decl = []
    for base in pl_:
        bits = [int(m.group(1)) for p in dirs for m in [re.match(re.escape(base) + r"\[(\d+)\]$", p)] if m]
        d = dirs.get(base) or next((dirs[p] for p in dirs if p.startswith(base + "[")), "input")
        decl.append(f"  {d} wire [{max(bits)}:{min(bits)}] {base}" if bits else f"  {d} wire {base}")
    bb.append(",\n".join(decl))
    bb.append(");\nendmodule\n")
    (out / "blk_bb.v").write_text("\n".join(bb))
    T = ["# GENERATED (CLAUDE S81-RERUN): POST_MACRO_PLACE hook of the die-context vehicle",
         "source /src/physical/common/ot_macro_track_snap.tcl",
         "set _blk [ord::get_db_block]", "set _dbu [ot_mts::get_dbu]", "set _sg [ot_mts::site_grid]",
         "set i [$_blk findInst u_blk]; set m [$i getMaster]", "lassign $_sg gx gw gy gh; set r [ot_mts::rule $m R0]",
         "lassign [dict get $r x] Px Sx; lassign [dict get $r y] Py Sy",
         f'set px [ot_mts::snap_axis [expr {{round({mx}*$_dbu)}}] $gx $gw $Px $Sx "u_blk x"]',
         f'set py [ot_mts::snap_axis [expr {{round({my}*$_dbu)}}] $gy $gh $Py $Sy "u_blk y"]',
         "$i setOrient R0; $i setLocation $px $py; $i setPlacementStatus FIRM",
         "foreach b [$_blk getBlockages] { odb::dbBlockage_destroy $b }", "set fence [dict create]"]
    for bn, bx in fences.items():
        T.append(f"dict set fence {bn} {{{bx[0]} {bx[1]} {bx[2]} {bx[3]}}}")
    T += ["set regs [dict create]",
          "dict for {nm box} $fence { set rg [odb::dbRegion_create $_blk fence_$nm]; lassign $box a b c d",
          "  odb::dbBox_create $rg [expr {round($a*$_dbu)}] [expr {round($b*$_dbu)}] [expr {round($c*$_dbu)}] [expr {round($d*$_dbu)}]",
          "  dict set regs $nm $rg }",
          "set nf 0; foreach inst [$_blk getInsts] { if {[[$inst getMaster] isBlock]} { continue }",
          "  set p [lindex [split [string map {\\\\ {}} [$inst getName]] ./] 0]",
          "  if {[dict exists $regs $p]} { [dict get $regs $p] addInst $inst; incr nf } }",
          'puts "OT_CTX_PLACE fenced=$nf regions=[dict size $regs]"']
    (out / "place.tcl").write_text("\n".join(T) + "\n")
    (out / "ctx.sdc").write_text("# GENERATED (CLAUDE S81-RERUN): the observation port is not a die path\n"
                                 "set_false_path -to [get_ports obs*]\n")
    rel = out.resolve().relative_to(ROOT.resolve())
    L = ["#!/bin/bash", "# GENERATED by tools/dsrom_s81_macro_context.py (CLAUDE S81-RERUN): route the die-context vehicle.",
         "# usage: WT=<pinned clean worktree> J=<job dir> [V=<tag>] [ARGS=extra driver args] launch.sh", "set -e",
         ': "${WT:?worktree}" "${J:?job dir}"', "mkdir -p $J; cd $WT",
         'test -z "$(git status --porcelain 2>/dev/null)" || { echo "worktree not clean"; exit 2; }',
         "exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \\",
         " --persistent-workdir $J/work --launch-receipt $J/receipt.json \\",
         f" --view asap7 --top ctx_top --source {rel}/ctx.v --source {rel}/blk_bb.v \\",
         f" --macro-view {cell}={rel}/views/{cell} \\",
         " --clock-port ck --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 "
         "--io-delay-fraction 0.2 --stages pnr \\",
         f" --die-area 0 0 {W:.3f} {H:.3f} --core-area 0 0.27 {W:.3f} {H - 0.27:.3f} --place-density ${{PD:-0.3}} "
         "--macro-place-halo 2 2 \\",
         f' --pin-region "^ck$=bottom:{W / 2 - 20:.2f}-{W / 2 + 20:.2f}" --pin-region "^obs.*=top:{W * 0.1:.2f}-{W * 0.9:.2f}" \\',
         " --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns ${HM:-0.02} \\",
         f" --step-tcl POST_MACRO_PLACE={rel}/place.tcl --sdc-append {rel}/ctx.sdc \\",
         " --orfs-var REMOVE_ABC_BUFFERS=1 --orfs-var NUM_CORES=${CORES:-16} --orfs-var SETUP_SLACK_MARGIN=${SM:-15} "
         "--hold-corners WC,BC \\",
         " --orfs-corner WC --pnr-stop-after ${STOP:-finish} --nickname-tag ctx_${V:-a}_20261006 \\",
         ' --output $J/out ${ARGS:-} > $J/launch.log 2>&1']
    (out / "launch.sh").write_text("\n".join(L) + "\n")
    os.chmod(out / "launch.sh", 0o755)
    rec = dict(schema="opentallas.dsrom-s81-macro-context.v1", tool="tools/dsrom_s81_macro_context.py", cell=cell,
               lef=lef_rel, lib_dir=str(libd), hop_um=hop, bin_um=a.bin_um, die_um=[W, H], macro_at_um=[mx, my],
               macro_um=[w, h], signal_pins=len(sig), inputs=sum(dirs[p] == "input" for p in sig),
               outputs=sum(dirs[p] == "output" for p in sig), bins=len(bins), lef_pins_without_lib=missing[:50],
               lef_pins_without_lib_n=len(missing))
    (out / "ctx.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit")
    p.add_argument("--lef", required=True, help="repo-relative routed abstract (.lef or .lef.gz)")
    p.add_argument("--lib-dir", required=True)
    p.add_argument("--cell")
    p.add_argument("--clock-pin", default="clk")
    p.add_argument("--hop-um", type=float, default=400.0)
    p.add_argument("--bin-um", type=float, default=20.0)
    p.add_argument("--margin-um", type=float, default=30.0)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    return emit(a)


if __name__ == "__main__":
    raise SystemExit(main())
