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

CHILD = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_children.sv'
ECC = 'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv'
CAL = 'rtl/qwen_sys/static_kv_20261014/qkd_controller_hbm_calendar.sv'
UCTL = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv'
TIM = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv'
CHAIN = 'rtl/qwen_sys/static_embedding_20261014/qkd_kv_pc_chain_station_b.sv'
ESM = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv'
RHOP = 'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_hop.sv'
RHEAD = 'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_head.sv'

# KV-PC SAFE item 3 (terminal census 1248d0585 + kv-pc-contract drivers.json: 188 FF roots > 32 loads).  Copies per
# root ~ loads / 24 (<= 32 a copy after the split, margin for mapping).  (reg, width, copies[, (port old, port new)])
CHAIN_WES = [
    ("    output reg  [287:0]  wes,", "    output wire [287:0]  wes,"),
    ("    (* keep *) reg rs_q;\n",
     "    (* keep *) reg rs_q;\n"
     "    // KV-PC SAFE: wes[0] (the es valid, 575 loads in the controller CDC intake) as 24 kept copies; wes[287:1] plain\n"
     "    reg [287:1] wes_d;\n"
     "    (* keep, ot_rst_split *) reg [23:0] wes0__qv;\n"
     "    assign wes = {wes_d, wes0__qv[0]};\n"),
    ("        if (h0 | h1) wes[287:1] <=", "        if (h0 | h1) wes_d[287:1] <="),
    ("        if (!rs_q) begin wes[0] <= 1'b0; hit_a <= 1'b0; x_a <= 1'b0; end\n"
     "        else begin wes[0] <= h0 | h1; hit_a <= h0 | h1; x_a <= x0 | x1; end",
     "        if (!rs_q) begin wes0__qv <= 24'd0; hit_a <= 1'b0; x_a <= 1'b0; end\n"
     "        else begin wes0__qv <= {24{h0 | h1}}; hit_a <= h0 | h1; x_a <= x0 | x1; end"),
    ("            always @(*) begin hit = hit_a; ctx_id = ctx_a;",
     "            reg hit__nolag;   // KV-PC SAFE clone: hit is a kept copy family (the lag-free MUT 5 is not built)\n"
     "            always @(*) begin hit__nolag = hit_a; ctx_id = ctx_a;"),
]
ESM_HQ = [
    ("    reg [287:0] hq;\n"
     "    always @(posedge ck) hq[287:1] <= hes[287:1];\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) hq[0] <= 1'b0; else hq[0] <= hes[0];",
     "    // KV-PC SAFE: hq[0] (the slice word valid, 310 loads) as 13 kept copies; hq[287:1] plain\n"
     "    reg [287:1] hq_d;\n"
     "    (* keep, ot_rst_split *) reg [12:0] hq0__qv;\n"
     "    wire [287:0] hq = {hq_d, hq0__qv[0]};\n"
     "    always @(posedge ck) hq_d[287:1] <= hes[287:1];\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) hq0__qv <= 13'd0; else hq0__qv <= {13{hes[0]}};"),
]
OBS_PO = [
    ("    (* keep *) reg [327:0] po_q;",
     "    // KV-PC SAFE: po_q[34:30] (col_bank: the observer's bank-indexed open-row reads, 641..43 loads) as 27 kept copies\n"
     "    (* keep *) reg [327:0] po_q_d;\n"
     "    (* keep, ot_rst_split = 5 *) reg [134:0] pob__qv;\n"
     "    wire [327:0] po_q = {po_q_d[327:35], pob__qv[4:0], po_q_d[29:0]};"),
    ("if(!h_rn)begin po_q<=0;sc_q<=0;esc_q<=0;end else begin po_q<=po;sc_q<=static_column;",
     "if(!h_rn)begin po_q_d<=0;pob__qv<=135'd0;sc_q<=0;esc_q<=0;end else begin po_q_d<=po;pob__qv<={27{po[34:30]}};sc_q<=static_column;"),
]
PORT_Y1 = [
    ("            for (i = 0; i < 4; i = i + 1) y1[i*8 +: 8] <= syn64(r_d[i*72 +: 72]);",
     "            y1 <= {syn64(r_d[3*72 +: 72]), syn64(r_d[2*72 +: 72]), syn64(r_d[1*72 +: 72]), syn64(r_d[0*72 +: 72])};"),
]

CLONES = [
    # (file, original module, clone name, [(old, new), ...], [kept copy families])
    (FAN, 'qkd_static_kv_pc_path_fan_nc_b', 'qkd_kvpc_s_fan_nc_b',
     [('qkd_static_kv_pc_path_emb_nc_b #(.MU(MU)) u_pce (', 'qkd_kvpc_s_emb_nc_b #(.MU(MU)) u_pce ('),
      ('    qkd_kv_pc_chain_station_b u_chain (', '    qkd_kvpc_s_chain u_chain (')]),
    (FAN, 'qkd_static_kv_pc_path_emb_nc_b', 'qkd_kvpc_s_emb_nc_b',
     [('qkd_static_kv_pc_path_nc #(.MU(MU)) u_path (', 'qkd_kvpc_s_path_nc #(.MU(MU)) u_path ('),
      ('    qkd_static_kv_pc_es_merge_b u_esm (', '    qkd_kvpc_s_esm u_esm (')]),
    (PATH, 'qkd_static_kv_pc_path_nc', 'qkd_kvpc_s_path_nc',
     [('qkd_ctrl_pc_host_static_nc #(', 'qkd_kvpc_s_ctrl #('),
      ('qkd_kv_hbm_elastic_front_mc_nc #(', 'qkd_kvpc_s_front #('),
      ('qkd_static_kv_return_slots_mc_nc #(.DEPTH(8)) u_return (', 'qkd_kvpc_s_return #(.DEPTH(8)) u_return ('),
      ('    qkd_controller_hbm_calendar #(', '    qkd_kvpc_s_calendar #(')]),
    (CTRL, 'qkd_ctrl_pc_host_static_nc', 'qkd_kvpc_s_ctrl',
     [('    qkd_ctrl_pc_sched_nc #(', '    qkd_kvpc_s_sched #('),
      ('    qkd_ctrl_pc_cdc_child #(', '    qkd_kvpc_s_cdc_child #('),
      ('    qkd_ctrl_pc_obs_child #(', '    qkd_kvpc_s_obs_child #('),
      ('    qkd_ctrl_pc_port_child_nc #(', '    qkd_kvpc_s_port_child #('),
      ('    qkd_ctrl_pc_ecc_child u_ecc (', '    qkd_kvpc_s_ecc_child u_ecc (')]),
    (CTRL, 'qkd_ctrl_pc_sched_nc', 'qkd_kvpc_s_sched',
     SCHED + [('    ot_qkd_static_ctrl_pc_emb #(', '    ot_qkd_static_ctrl_pc_emb_kvpc_s #(')],
     [('static_owner_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_cdc_child', 'qkd_kvpc_s_cdc_child',
     [('ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (', 'ot_qkd_static_emb_cdc_kvpc_s #(.ENABLE(1)) u_ecdc (')],
     [('hr_q', 1, 2), ('rs_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_obs_child', 'qkd_kvpc_s_obs_child', OBS_PO, [('hr_q', 1, 16)]),
    (CTRL, 'qkd_ctrl_pc_port_child_nc', 'qkd_kvpc_s_port_child',
     [('    ot_qfd_emb_pcport_nkw #(', '    ot_qfd_emb_pcport_nkw_kvpc_s #(')],
     [('rv_q', 1, 27), ('col_sr_q', 1, 2)]),
    (CTRL, 'ot_qfd_emb_pcport_nkw', 'ot_qfd_emb_pcport_nkw_kvpc_s',
     PORT_Y1 + [("    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;",
                 "    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;\n"
                 "    initial if (WA != 2 || RA != 6) $error(\"ot_qfd_emb_pcport_nkw_kvpc_s: kept copy widths assume WQD 4, RQD 64\");")],
     [('wr', 3, 49), ('wc1_st', 1, 24), ('v1', 1, 22), ('wc1_kv', 1, 13), ('kr', 7, 3), ('y1', 32, 4),
      ('kv_v', 1, 2, ('    output reg          kv_v,', '    output wire         kv_v,'))]),
    (CHILD, 'qkd_ctrl_pc_ecc_child', 'qkd_kvpc_s_ecc_child',
     [('    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (',
       '    ot_qfd_kv_landing_ecc_kvpc_s #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (')]),
    (ECC, 'ot_qfd_kv_landing_ecc', 'ot_qfd_kv_landing_ecc_kvpc_s', [], [('p1_v', 1, 23)]),
    (CAL, 'qkd_controller_hbm_calendar', 'qkd_kvpc_s_calendar', [], [('rn', 1, 28), ('go_q', 1, 41)]),
    (UCTL, 'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_ctrl_pc_emb_kvpc_s',
     [(' ot_qkd_static_kv_timing #(', ' ot_qkd_static_kv_timing_kvpc_s #(')],
     [('rp', 3, 15),
      ('col_bank', 5, 11, ('output reg [4:0] col_bank,col_col,', 'output wire [4:0] col_bank,output reg [4:0] col_col,')),
      ('col_col', 5, 3, ('output reg [4:0] col_col,', 'output wire [4:0] col_col,')),
      ('row_row', 19, 2, ('output reg [18:0] row_row,', 'output wire [18:0] row_row,'))]),
    (TIM, 'ot_qkd_static_kv_timing', 'ot_qkd_static_kv_timing_kvpc_s',
     [("    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;",
       "    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;\n"
       "    initial if (SQW != 2 || WQW != 2) $error(\"ot_qkd_static_kv_timing_kvpc_s: kept copy widths assume SQD 4, WQ 4\");")],
     [('sq_rp', 2, 27), ('wq_rp', 2, 9), ('wq_rp1', 2, 8), ('context_active', 1, 5), ('streaming', 1, 7),
      ('wq_n', 3, 3), ('c_s', 1, 2), ('wq_v', 4, 2)]),
    (CHAIN, 'qkd_kv_pc_chain_station_b', 'qkd_kvpc_s_chain', CHAIN_WES,
     [('rs_q', 1, 10), ('bt', 1, 12), ('ss', 1, 4), ('hit', 1, 11),
      ('emb_issue_v', 1, 4, ('    output reg           emb_issue_v,', '    output wire          emb_issue_v,'))]),
    (ESM, 'qkd_static_kv_pc_es_merge_b', 'qkd_kvpc_s_esm', ESM_HQ, [('own', 1, 11)]),
    (RHOP, 'qkd_embedding_static_return_hop', 'qkd_kvpc_s_rhop', [], [('ts_q', 1, 25)]),
    (RHEAD, 'qkd_embedding_static_return_head', 'qkd_kvpc_s_rhead', [], [('ts_q', 1, 25)]),
]


def module_text(path, name):
    t = (ROOT / path).read_text()
    m = re.search(rf'^module {re.escape(name)}\b', t, re.M)
    if not m:
        raise SystemExit(f'kv_pc_sram_gen: {name} not in {path}')
    e = re.compile(r'^endmodule\b.*$', re.M).search(t, m.end())
    return t[m.start():e.end()] + '\n'


def _expr_end(t, i):
    """index of the ';' ending the expression starting at i (paren / brace / bracket depth 0)"""
    d = 0
    while True:
        c = t[i]
        if c in '([{':
            d += 1
        elif c in ')]}':
            d -= 1
        elif c == ';' and d == 0:
            return i
        i += 1


def fam(t, new, name, W, N, port=None):
    """KV-PC SAFE item 3: register NAME (W bits) -> N kept identical copies, copy-major in NAME__qv, family attribute
    ot_rst_split (= W when W > 1: one family per bit position; physical/common_flow/ot_rst_copies spreads the loads,
    reset_relay_split / OT_RST_COPIES_WIDE).  Every full assignment 'NAME <= E;' becomes 'NAME__qv <= {N{NAME__f(E)}};'
    (NAME__f sizes E to W bits exactly as the assignment did); every read sees copy 0 through 'NAME' (a wire / the
    port).  port: (old header text, new header text) for an 'output reg' port.  Returns (text, assignments rewritten)."""
    rng = f'[{W - 1}:0] ' if W > 1 else ''
    attr = f'(* keep, ot_rst_split = {W} *)' if W > 1 else '(* keep, ot_rst_split *)'
    famdecl = (f'{attr} reg [{N * W - 1}:0] {name}__qv;   // KV-PC SAFE: {N} kept copies of {name}\n'
               f'    function {rng}{name}__f; input {rng}v; {name}__f = v; endfunction')
    if port:
        old, newh = port
        if t.count(old) != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: port declaration found {t.count(old)} times')
        t = t.replace(old, newh)
        hdr_end = t.index(');', t.index(newh)) + 2
        t = t[:hdr_end] + f'\n    {famdecl}\n    assign {name} = {name}__qv[{W - 1}:0];' + t[hdr_end:]
    else:
        decl = re.compile(r'(?:(?<=\n)|(?<=;))([ \t]*(?:\(\*[^*]*\*\)[ \t]*)?reg\b[ \t]*(\[[^\]]*\][ \t]*)?)([^;]*);')
        hits = []
        for m in decl.finditer(t):
            ids = [x.strip() for x in m.group(3).split(',')]
            if name in ids:
                hits.append((m, ids))
        if len(hits) != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: {len(hits)} reg declarations')
        m, ids = hits[0]
        rest = [x for x in ids if x != name]
        ind = re.match(r'[ \t]*', m.group(1)).group(0)
        keep = (m.group(1) + ', '.join(rest) + ';') if rest else ''
        rep = (keep + ('\n' if keep else '') + f'{ind}{famdecl}\n{ind}wire {rng}{name} = {name}__qv[{W - 1}:0];')
        t = t[:m.start()] + rep + t[m.end():]
    pat = re.compile(rf'(?<![\w.$\]\[])({re.escape(name)})(\s*)<=(?!=)')
    out, pos, n = [], 0, 0
    for m in pat.finditer(t):
        if m.start() < pos:
            continue
        j = m.start() - 1
        while j >= 0 and t[j] in ' \t\n':
            j -= 1
        w = re.search(r'(\w+)$', t[max(0, j - 12):j + 1])
        if not (t[j] in ';):' or (w and w.group(1) in ('begin', 'else', 'end'))):
            continue
        e = _expr_end(t, m.end())
        expr = t[m.end():e].strip()
        out.append(t[pos:m.start()])
        out.append(f'{name}__qv <= {{{N}{{{name}__f({expr})}}}};')
        pos = e + 1
        n += 1
    out.append(t[pos:])
    if n == 0:
        raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: no assignment rewritten')
    return ''.join(out), n


FAM_LOG = []


def clone(path, name, new, subs, fams=()):
    t = module_text(path, name)
    t = re.sub(rf'^module {re.escape(name)}\b', f'module {new}', t, count=1, flags=re.M)
    for old, rep in subs:
        n = t.count(old)
        if n != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}: substitution site found {n} times:\n{old}')
        t = t.replace(old, rep)
    fl = []
    for f in fams:
        reg, W, N = f[:3]
        t, n = fam(t, new, reg, W, N, port=f[3] if len(f) > 3 else None)
        fl.append(f'{reg}[{W}]x{N}({n})')
    FAM_LOG.append((new, fl))
    fs = f'; kept copy families {", ".join(fl)}' if fl else ''
    return f'// ---- {new}: clone of {name} ({path}) with {len(subs)} substitution(s){fs} ----\n' + t


def render():
    hdr = ['`timescale 1ns/1ps',
           '// GENERATED by tools/qwen_kv_die/kv_pc_sram_gen.py -- do not edit.  KV-PC 2026-10-19 SAFE redesign: the PC path',
           '// clone chain on the SRAM-backed storage of qkd_kvpc_sram_1019.sv.  Each module below is its original verbatim',
           '// except for the listed substitutions (instance module names; in qkd_kvpc_s_sched the tag queue and the',
           f'// replicated hr_q ({NHR}) / hgo ({NHGO}) roots).',
           '`ifndef OT_KVPC_SRAM_CLONES_1019_SV', '`define OT_KVPC_SRAM_CLONES_1019_SV', '']
    body = [clone(*c) for c in CLONES]
    return '\n'.join(hdr) + '\n'.join(body) + '`endif\n'


RL_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv'
SR_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv'


def sr_tile():
    """the OT_KV_PC_SRAM tile file = kv_static_die.pc_sram_text applied to the pc / pc_h modules of the committed _rl
    file (the die GEN with OT_KV_PC_RLAND=1 OT_KV_PC_SRAM=1 produces the same modules)"""
    import ast
    src = (ROOT / 'tools/qwen_kv_die/kv_static_die.py').read_text()
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'pc_sram_text')
    ns = {'PC_RLAND': True}
    exec(ast.get_source_segment(src, fn), ns)
    t = (ROOT / RL_TILE).read_text()
    for m in ('qkd_kvs_pc', 'qkd_kvs_pc_h'):
        a = re.search(rf'^module {m} \(', t, re.M).start()
        b = t.index('endmodule\n', a) + len('endmodule\n')
        t = t[:a] + ns['pc_sram_text'](t[a:b]) + t[b:]
    return t.replace('// KVJ-G2 2026-10-17:', '// KV-PC 2026-10-19 OT_KV_PC_SRAM=1 (pc / pc_h: kv_static_die.pc_sram_text; kv_pc_sram_gen.py).\n'
                     '// KVJ-G2 2026-10-17:', 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = {OUT: render(), SR_TILE: sr_tile()}
    if a.check:
        bad = [o for o, txt in outs.items() if not (ROOT / o).exists() or (ROOT / o).read_text() != txt]
        print('kv_pc_sram_gen: ' + ('UP TO DATE' if not bad else f'STALE {bad}'))
        return 1 if bad else 0
    for o, txt in outs.items():
        (ROOT / o).write_text(txt)
        print(f'kv_pc_sram_gen: wrote {o} ({len(txt.splitlines())} lines)')
    for new, fl in FAM_LOG:
        if fl:
            print(f'  {new}: {", ".join(fl)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
