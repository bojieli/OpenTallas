#!/usr/bin/env python3
"""KV-PC 2026-10-19 SAFE redesign: generate the opt-in clone chain of the PC path that uses the SRAM-backed storage of
rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_1019.sv (front, return ring, tag queue, embedding CDC FIFOs) and the
replicated scheduler reset / strap-release roots.  Every clone is the ORIGINAL module text (read from its committed
file) with its name suffixed and an explicit list of exact substitutions; each substitution must match exactly once, so
a drift of an original breaks the generator instead of silently diverging.  The originals stay unchanged.

    python3 tools/qwen_kv_die/kv_pc_sram_gen.py [--check]      (--check: exit 1 if the committed output differs)

Chain (tile u_pc):  qkd_kvpc_s_fan_nc_b -> qkd_kvpc_s_emb_nc_b -> qkd_kvpc_s_path_nc -> {qkd_kvpc_s_ctrl ->
{qkd_kvpc_s_sched, qkd_kvpc_s_cdc_child -> ot_qkd_static_emb_cdc_kvpc_s}, qkd_kvpc_s_front, qkd_kvpc_s_return}.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = 'rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_clones_1019.sv'
FAN = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv'
PATH = 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv'
CTRL = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv'
CORE = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv'
NHGO = 64      # u_ctl strap-release (hgo) copies: 1994 async-reset loads -> <= 32 each
NHR = 16       # sched hclk reset capture (hr_q) copies: 414 loads -> <= 32 each

TQ_DECL = '''    reg  [33:0] tq [0:TQD-1];'''
TQ_DECL_NEW = '''    // KV-PC SAFE: tq (64 x 34) is two native 32 x 64 banks (qkd_kvpc_s_tq): h0 = tq[tr], h1 = tq[tr + 1] (== tq[tr1])
    wire [33:0] tq_h0, tq_h1;'''
TQ_WRITE = '''        if (rd_kv) tq[tw[TQA-1:0]] <= {epoch_q,brow[col_bank], rj};
'''
TQ_INST = '''    // tr(t), presented at t-1: tr is cleared asynchronously by h_rn, which only changes on hclk edges (hr_q capture of
    // hrst); next(tr) = 0 if the scheduler is in reset at this edge or enters it at this edge, else tr + kv_v.
`ifdef OT_KVPC_MUT_TQ_NEXT
    wire [TQA-1:0] tq_a0_next = tr[TQA-1:0];                     // bench mutant: read issued at tr (no advance)
`else
    wire [TQA-1:0] tq_a0_next = (h_rn && hrst) ? (kv_v ? tr[TQA-1:0] + 1'b1 : tr[TQA-1:0]) : {TQA{1'b0}};
`endif
    qkd_kvpc_s_tq #(.TQD(TQD)) u_tq (.clk(hclk), .we(rd_kv), .wa(tw[TQA-1:0]), .wd({epoch_q,brow[col_bank], rj}),
        .a0_next(tq_a0_next), .h0(tq_h0), .h1(tq_h1));
'''

SCHED = [
    # hclk reset capture: NHR kept identical copies (split by physical/common_flow/ot_rst_copies, OT_RST_COPIES_MAX)
    ('''    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    wire h_rn = hr_q;''',
     f'''    // KV-PC SAFE: {NHR} kept identical capture copies (family ot_rst_split; ot_rst_copies.tcl spreads the loads)
    (* keep, ot_rst_split *) reg [{NHR - 1}:0] hr_qv;
    always @(posedge hclk) hr_qv <= {{{NHR}{{hrst}}}};
    wire h_rn = hr_qv[0];'''),
    ('''    reg       hgo;''',
     f'''    // KV-PC SAFE: the strap release hgo (u_ctl reset, 1994 loads) as {NHGO} kept identical copies (ot_rst_split)
    (* keep, ot_rst_split *) reg [{NHGO - 1}:0] hgo_qv;
    wire      hgo = hgo_qv[0];'''),
    ('''        if (!h_rn) begin dcnt <= 7'd0; hgo <= 1'b0; end
        else if (dcnt == dsel) hgo <= 1'b1;''',
     f'''        if (!h_rn) begin dcnt <= 7'd0; hgo_qv <= {{{NHGO}{{1'b0}}}}; end
        else if (dcnt == dsel) hgo_qv <= {{{NHGO}{{1'b1}}}};'''),
    (TQ_DECL, TQ_DECL_NEW),
    ('''    wire [33:0] t_head  = tq[tr[TQA-1:0]];''', '''    wire [33:0] t_head  = tq_h0;'''),
    (TQ_WRITE, ''),
    ('''    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= '0; tr <= '0; f_tag <= 1'b0; end''',
     TQ_INST + '''    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= '0; tr <= '0; f_tag <= 1'b0; end'''),
    ('''    wire [33:0]  h_c0    = tq[tr[TQA-1:0]];
    wire [33:0]  h_c1    = tq[tr1];''', '''    wire [33:0]  h_c0    = tq_h0;
    wire [33:0]  h_c1    = tq_h1;'''),
]

CLONES = [
    # (file, original module, clone name, [(old, new), ...])
    (FAN, 'qkd_static_kv_pc_path_fan_nc_b', 'qkd_kvpc_s_fan_nc_b',
     [('qkd_static_kv_pc_path_emb_nc_b #(.MU(MU)) u_pce (', 'qkd_kvpc_s_emb_nc_b #(.MU(MU)) u_pce (')]),
    (FAN, 'qkd_static_kv_pc_path_emb_nc_b', 'qkd_kvpc_s_emb_nc_b',
     [('qkd_static_kv_pc_path_nc #(.MU(MU)) u_path (', 'qkd_kvpc_s_path_nc #(.MU(MU)) u_path (')]),
    (PATH, 'qkd_static_kv_pc_path_nc', 'qkd_kvpc_s_path_nc',
     [('qkd_ctrl_pc_host_static_nc #(', 'qkd_kvpc_s_ctrl #('),
      ('qkd_kv_hbm_elastic_front_mc_nc #(', 'qkd_kvpc_s_front #('),
      ('qkd_static_kv_return_slots_mc_nc #(.DEPTH(8)) u_return (', 'qkd_kvpc_s_return #(.DEPTH(8)) u_return (')]),
    (CTRL, 'qkd_ctrl_pc_host_static_nc', 'qkd_kvpc_s_ctrl',
     [('    qkd_ctrl_pc_sched_nc #(', '    qkd_kvpc_s_sched #('),
      ('    qkd_ctrl_pc_cdc_child #(', '    qkd_kvpc_s_cdc_child #(')]),
    (CTRL, 'qkd_ctrl_pc_sched_nc', 'qkd_kvpc_s_sched', SCHED),
    (CORE, 'qkd_ctrl_pc_cdc_child', 'qkd_kvpc_s_cdc_child',
     [('ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (', 'ot_qkd_static_emb_cdc_kvpc_s #(.ENABLE(1)) u_ecdc (')]),
]


def module_text(path, name):
    t = (ROOT / path).read_text()
    m = re.search(rf'^module {re.escape(name)}\b', t, re.M)
    if not m:
        raise SystemExit(f'kv_pc_sram_gen: {name} not in {path}')
    e = re.compile(r'^endmodule\b.*$', re.M).search(t, m.end())
    return t[m.start():e.end()] + '\n'


def clone(path, name, new, subs):
    t = module_text(path, name)
    t = re.sub(rf'^module {re.escape(name)}\b', f'module {new}', t, count=1, flags=re.M)
    for old, rep in subs:
        n = t.count(old)
        if n != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}: substitution site found {n} times:\n{old}')
        t = t.replace(old, rep)
    return f'// ---- {new}: clone of {name} ({path}) with {len(subs)} substitution(s) ----\n' + t


def render():
    hdr = ['`timescale 1ns/1ps',
           '// GENERATED by tools/qwen_kv_die/kv_pc_sram_gen.py -- do not edit.  KV-PC 2026-10-19 SAFE redesign: the PC path',
           '// clone chain on the SRAM-backed storage of qkd_kvpc_sram_1019.sv.  Each module below is its original verbatim',
           '// except for the listed substitutions (instance module names; in qkd_kvpc_s_sched the tag queue and the',
           f'// replicated hr_q ({NHR}) / hgo ({NHGO}) roots).',
           '`ifndef OT_KVPC_SRAM_CLONES_1019_SV', '`define OT_KVPC_SRAM_CLONES_1019_SV', '']
    body = [clone(*c) for c in CLONES]
    return '\n'.join(hdr) + '\n'.join(body) + '`endif\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    txt = render()
    p = ROOT / OUT
    if a.check:
        ok = p.exists() and p.read_text() == txt
        print('kv_pc_sram_gen: ' + ('UP TO DATE' if ok else 'STALE') + f' {OUT}')
        return 0 if ok else 1
    p.write_text(txt)
    print(f'kv_pc_sram_gen: wrote {OUT} ({len(txt.splitlines())} lines)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
