#!/usr/bin/env python3
"""Emit three-region S81 frame landing hardware and explicit compiler crossing manifest.

The generated reference proves transport only. The station/return programme must
be legalised separately before adoption or a frame physical gate.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
W = str(ROOT)
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/landed_parent')]
import frame_regions as FR
import lp

def emit(master, reset_forest=False):
    r, cut, H = FR.frame(master, Path(W+'/rtl/dsrom_sys/s81_dv/frame_l4'))
    # re-derive yc per inst (frame() keeps it local): patch by recomputing
    import re, gzip, statistics
    FW=FR.FW
    fn, mod, slots, nq, nbf = FW.CLASSES[master]
    text = gzip.decompress((FW.SRC / fn).read_bytes()).decode()
    _, insts = FW.parse_column(text, mod)
    cl = json.loads(gzip.decompress((FW.SRC / 'c26l_sel_clusters.json.gz').read_bytes()))
    cluster = next(c for c in cl['clusters'] if c['master'] == mod)
    names, _ = FW.local_names(cluster['children'], insts)
    box = {c['instance']: c['box_um'] for c in cluster['children']}
    pos = {names[i['name']]: box[i['name']] for i in insts if i['name'] in box}
    s = open(W+f'/rtl/dsrom_sys/s81_dv/frame_l4/{master}_l4.sv').read()
    body = s[s.index(');') + 2:]
    inst_re = re.compile(r"^    ([a-z]\w*)\s*(?:#\((?:[^()]|\([^()]*\))*\))?\s*(u_\w+)\s*\((.*?)\);\s*$", re.M | re.S)
    nets, kids = collections.defaultdict(set), {}
    for m in inst_re.finditer(body):
        mst, inst, conns = m.groups(); kids[inst]=mst
        for pin, expr in re.findall(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", conns):
            if pin in FR.CLOCK_PINS: continue
            for n in re.findall(r"\b(n\d+|(?:x|xo|ret|xk|xok|lk)\[\d+\]|rst_n)", expr): nets[n].add(inst)
    yc = {k: v[1] + v[3] / 2 for k, v in pos.items() if k in kids}
    nb = collections.defaultdict(set)
    for ks in nets.values():
        if len(ks) < 40:
            for a in ks: nb[a] |= ks - {a}
    for _ in range(6):
        for k in kids:
            if k not in yc:
                ys = [yc[o] for o in nb[k] if o in yc]
                if ys: yc[k] = statistics.mean(ys)
    cuts = json.load(open(W+'/results/arch/s81_dv_1016/frame_l4_cluster/regions.json'))['masters'][master]['plan']['cuts_um']
    def reg(y): return 'r%d' % sum(y > c for c in cuts)
    regions = collections.defaultdict(list)
    for k in kids: regions[reg(yc[k])].append(k)
    ch = ['rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv', 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv', 'rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv', 'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv', 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv', 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv', 'rtl/dsrom_sys/s81_glue/test/actual_rly1_reference.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfu.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv', 'rtl/experimental/w5_context/tb_w5_cfg_context.sv', 'rtl/v41die/ot_s81_cfg7_seq.sv', 'rtl/v41die/ot_s81_cfg7_seq_bfp.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv']
    ch = [f for f in ch if '/test/' not in f and 'experimental' not in f] + ['physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v']
    # MX and nominal h9 share the same frame graph; this source is emitted per actual master.
    out = 'rtl/dsrom_sys/s81_dv/frame_lp'
    rec = 'results/arch/s81_dv_1016/frame_l4_cluster/compiler'
    spec = dict(top=f'{master}_l4', sources=[f'rtl/dsrom_sys/s81_dv/frame_l4/{master}_l4.sv'],
                child_sources=ch, clock_ports=['clk', 'cr', 'cr_s'], preserve_clock_ports=['xk'],
                # S81-FRAME4 10-19: dsfd_bf_front_roots io_clk / io_n / io_w / io_e are clock pins the frame RTL binds
                # to clk; left off this list the LP kept them on the dead clk net and Yosys TIED THEM LOW (TIELO, gate
                # s81frame_col_h9_sr 12:04: 12 of the 20 unreached hard-child clock pins).  No tie-offs: region root.
                clock_pins=['ck', 'clk', 'cr', 'cr_s', 'xk', 'io_clk', 'io_n', 'io_w', 'io_e'],
                reset_port='rst_n', reset_net='n257', reset_pins=['rs', 'rst_n', 'rst'],
                static=['lk'], reschedule=True, D=4, E=2,
                # TW3-S81/FRAME 10-19: the default MUT-4 child (first reset kid = u_bn0, a qbank pipeline) forgets a late
                # reset in one edge, so the frame bench was blind to it (PASS).  Children are event-driven (x/go/cfg), so
                # hold a q element the plan uses past its last return word: the mutant proves the reset run reaches it.
                mut_child='u_e0', mut4_stages=400,
                out_dir=out, record_dir=rec,
                regions=[dict(name=n, insts=sorted(v)) for n, v in sorted(regions.items())])
    if reset_forest:
        # S81-FRAME4 10-19 (SAFE 3, kept copies): each region's reset run end drove EVERY landing half rq (h9 r1 3,017 /
        # r2 1,613 / r0 1,404) plus ~90-140 child reset pads from ONE flop.  The same-age kept-copy forest gives every
        # landing half and every child reset pad its own leaf, <= 32 loads per stage (3 levels above 1,024 leaves).
        spec.update(landing_chunk_bits=24, landing_reset_forest=True, landing_reset_forest_children=True)
    d = ROOT / rec
    d.mkdir(parents=True, exist_ok=True)
    sp = d / f'{master}_spec.json'
    sp.write_text(json.dumps(spec, indent=1) + '\n')
    lp.gen(lp.load(str(sp)))
    wrapper = f'''`timescale 1ns/1ps
`ifndef LK
`define LK 2
`endif
`ifndef LP_MUT
`define LP_MUT 0
`endif
module {master}_l4_lp_b #(parameter string INSTANCE = "{master}") (
 input wire clk, cr, cr_s, rst_n, input wire [1103:0] x,
 input wire [3:0] xk, output wire [1103:0] xo,
 output wire [3:0] xok, output wire [69:0] ret);
 {master}_l4_lp #(.INSTANCE(INSTANCE), .MUT(`LP_MUT)) u_f (
 .ck_r0(cr), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n),
 .x(x), .xk(xk), .lk({{4{{3'd`LK}}}}), .xo(xo), .xok(xok), .ret(ret));
endmodule
'''
    (ROOT / out / f'{master}_l4_lp_b.sv').write_text(wrapper)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--master', choices=['col_h9', 'col_h10'], required=True)
    ap.add_argument('--reset-forest', action='store_true', help='kept-copy reset forest (lp landing_reset_forest[_children])')
    a = ap.parse_args()
    emit(a.master, a.reset_forest)
