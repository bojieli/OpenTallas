#!/usr/bin/env python3
"""KDIE5-RTL 10-22: per-face output-register copies for the release-point native32 ctl (qkd_kvs_ctl_nc32.sv).

Why: at the relm frame (1123.176 x 172.776) the c32 members drive 967 output bits that leave on BOTH the W words
(o_hroot_WS / WN) and the E words (o_hroot_ES / EN) from ONE register (es fan root h 784, boot group / controller
addr+data 144, layer programme epoch / ctx_t / layer / kgo / vgo / ctrl_go 39): a register between pins 1119 um apart
is >= 602 um from one of them (gate textbook wire_reach: 951 stages > 500 um, nc32m / nc32f gates 2026-10-22).
Fix (0 edges, function identical): each such register gets a KEPT E-face copy with the identical D, clock and reset
(the E words read the copy, the W words + o_attn the original), so each copy sits within one reach of its own face.

Derived MECHANICALLY from sha-pinned member sources (refuses on drift); shared files untouched:
  qkd_kv_es_fan_root2_b_c32           -> qkd_kv_es_fan_root2_b_nc32           (+ output h_e)
  qkd_static_kv_boot_dispatch_c32     -> qkd_static_kv_boot_dispatch_nc32     (+ group_addr_e / group_data_e /
                                                                                 controller_addr_e / controller_data_e)
  qkd_static_kv_boot_dispatch_mu_c32  -> qkd_static_kv_boot_dispatch_mu_nc32  (passes them)
  qkd_static_kv_layer_programme_s32   -> qkd_static_kv_layer_programme_nc32   (+ ctrl_go_e kgo_e vgo_e layer_e epoch_e
                                                                                 ctx_t_e)
and the ctl body qkd_kvs_ctl_nc32.sv (c32i body verbatim) re-wired: the E words take the _e copies.

    python3 tools/qwen_kv_die/kv_ctl_nc32_face.py          # writes OUT + CTL
    python3 tools/qwen_kv_die/kv_ctl_nc32_face.py --check  # regenerate in memory, fail on any difference
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = 'rtl/qwen_sys/static_kv_die_20261017/'
MISC = D + 'qkd_kv_ctl_c32_misc.sv'
BOOT = D + 'qkd_kv_ctl_c32_boot.sv'
LPRG = 'rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_s32.sv'
C32I = D + 'qkd_kvs_tiles_hroot_ff_k_mu_ba_c32i.sv'
OUT = D + 'qkd_kv_ctl_nc32_face.sv'
CTL = D + 'qkd_kvs_ctl_nc32.sv'
PIN = {
    MISC: '300e078bb79f3cc129598f4f7801127f6e7f732354e9328541f2261a7dca5f1b',
    BOOT: '24220012d22ea7d4b1043291f7972abe5a76aa9047df2ac03abfaaa7ed210c9b',
    LPRG: '42837f7ca204a9fb511c2a1d39146920618b42a05d250385e75d1956b5e91192',
    C32I: 'd74c2f77a18abc320df95cb984a0a111921e025bd8f8d522febb74d521ac09cb',
}
CTL_BODY_SHA = '7ad3b0c2992a4c9d46988c6f1c428e77dc260db91aefd09c74ab49c9ca6f29cf'   # c32i qkd_kvs_ctl body


def read(rel):
    t = (ROOT / rel).read_text()
    h = hashlib.sha256(t.encode()).hexdigest()
    if PIN.get(rel) and PIN[rel] != h:
        raise SystemExit(f'kv_ctl_nc32_face: source identity changed: {rel} {h}')
    return t


def module(text, name):
    m = re.search(r'^module ' + re.escape(name) + r'\b.*?^endmodule\n', text, re.S | re.M)
    if not m:
        raise SystemExit(f'kv_ctl_nc32_face: module {name} missing')
    return m.group(0)


def one(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit(f'kv_ctl_nc32_face: {what}: expected exactly one match, found {text.count(old)}')
    return text.replace(old, new)


def fanr(misc):
    t = module(misc, 'qkd_kv_es_fan_root2_b_c32')
    t = one(t, 'module qkd_kv_es_fan_root2_b_c32 #(', 'module qkd_kv_es_fan_root2_b_nc32 #(', 'fanr name')
    t = one(t, '    output reg  [783:0]    h,\n',
            '    output reg  [783:0]    h,\n    (* keep *) output reg  [783:0]    h_e,   // KDIE5-RTL: E-face copy of h\n',
            'fanr h port')
    t = one(t, "        if (!rs_q) begin h <= 784'd0; fault <= 1'b0; end\n        else begin\n            h <= {use_b, hn};\n",
            "        if (!rs_q) begin h <= 784'd0; h_e <= 784'd0; fault <= 1'b0; end\n        else begin\n"
            "            h <= {use_b, hn}; h_e <= {use_b, hn};\n", 'fanr h assign')
    t = one(t, 'endmodule\n', '`ifndef SYNTHESIS\n // bench self-check: every E-face copy equals its original on every edge (a copy mutant stops the bench)\n always @(negedge ck) if (h_e !== h) $fatal(1, "qkd_kv_es_fan_root2_b_nc32: E-face copy differs from its original");\n`endif\nendmodule\n', 'fanr check')
    return t


def boot(bt):
    d = module(bt, 'qkd_static_kv_boot_dispatch_c32')
    d = one(d, 'module qkd_static_kv_boot_dispatch_c32 #(', 'module qkd_static_kv_boot_dispatch_nc32 #(', 'disp name')
    d = one(d, ' output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,\n',
            ' output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,\n'
            ' output wire[7:0]group_addr_e,output wire[63:0]group_data_e,output wire[7:0]controller_addr_e,'
            'output wire[63:0]controller_data_e,\n', 'disp ports')
    d = one(d, ' always @(posedge ck or negedge rst_n)if(!rst_n)group_q<=0;else group_q<=group_n;\n',
            ' always @(posedge ck or negedge rst_n)if(!rst_n)group_q<=0;else group_q<=group_n;\n'
            ' (* keep *) reg[71:0]group_qe;   // KDIE5-RTL: E-face copy (same D / clock / reset)\n'
            ' always @(posedge ck or negedge rst_n)if(!rst_n)group_qe<=0;else group_qe<=group_n;\n', 'group_qe')
    d = one(d, ' always @(posedge ck or negedge rst_n)if(!rst_n)ctl_q<=0;else ctl_q<=ctl_n;\n',
            ' always @(posedge ck or negedge rst_n)if(!rst_n)ctl_q<=0;else ctl_q<=ctl_n;\n'
            ' (* keep *) reg[71:0]ctl_qe;     // KDIE5-RTL: E-face copy (same D / clock / reset)\n'
            ' always @(posedge ck or negedge rst_n)if(!rst_n)ctl_qe<=0;else ctl_qe<=ctl_n;\n', 'ctl_qe')
    d = one(d, ' assign controller_addr=ctl_q[71:64];assign controller_data=ctl_q[63:0];\n',
            ' assign controller_addr=ctl_q[71:64];assign controller_data=ctl_q[63:0];\n'
            ' assign group_addr_e=group_qe[71:64];assign group_data_e=group_qe[63:0];\n'
            ' assign controller_addr_e=ctl_qe[71:64];assign controller_data_e=ctl_qe[63:0];\n', 'disp assigns')
    d = one(d, 'endmodule\n', '`ifndef SYNTHESIS\n // bench self-check: every E-face copy equals its original on every edge (a copy mutant stops the bench)\n always @(negedge ck) if (group_qe !== group_q || ctl_qe !== ctl_q) $fatal(1, "qkd_static_kv_boot_dispatch_nc32: E-face copy differs from its original");\n`endif\nendmodule\n', 'disp check')
    m = module(bt, 'qkd_static_kv_boot_dispatch_mu_c32')
    m = one(m, 'module qkd_static_kv_boot_dispatch_mu_c32 #(', 'module qkd_static_kv_boot_dispatch_mu_nc32 #(', 'mu name')
    m = one(m, ' output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,\n',
            ' output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,\n'
            ' output wire[7:0]group_addr_e,output wire[63:0]group_data_e,output wire[7:0]controller_addr_e,'
            'output wire[63:0]controller_data_e,\n', 'mu ports')
    m = one(m, ' qkd_static_kv_boot_dispatch_c32 #(', ' qkd_static_kv_boot_dispatch_nc32 #(', 'mu child')
    m = one(m, '.controller_we(controller_we),.controller_addr(controller_addr),.controller_data(controller_data),\n',
            '.controller_we(controller_we),.controller_addr(controller_addr),.controller_data(controller_data),\n'
            '  .group_addr_e(group_addr_e),.group_data_e(group_data_e),.controller_addr_e(controller_addr_e),'
            '.controller_data_e(controller_data_e),\n', 'mu child conns')
    return d + '\n' + m


def lprg(lp):
    t = module(lp, 'qkd_static_kv_layer_programme_s32')
    t = one(t, 'module qkd_static_kv_layer_programme_s32 #(', 'module qkd_static_kv_layer_programme_nc32 #(', 'lprg name')
    t = one(t, ' output wire[1:0]generation,\n',
            ' output wire[1:0]generation,\n'
            ' // KDIE5-RTL: E-face copies (kept registers, identical D / clock / reset)\n'
            ' (* keep *) output reg ctrl_go_e,(* keep *) output reg kgo_e,(* keep *) output reg vgo_e,output wire[5:0]layer_e,output wire[15:0]epoch_e,output wire[13:0]ctx_t_e,\n',
            'lprg ports')
    t = one(t, ' localparam integer RC=RCOPIES;\n',
            ' localparam integer RC=RCOPIES;\n (* keep *) reg[5:0]stage_oe;(* keep *) reg[15:0]om_e_ep;'
            '(* keep *) reg[13:0]om_e_ct;\n', 'lprg regs')
    for a, b in (('ctrl_go<=0;kgo<=0;vgo<=0;', 'ctrl_go<=0;kgo<=0;vgo<=0;ctrl_go_e<=0;kgo_e<=0;vgo_e<=0;'),):
        if t.count(a) != 2:
            raise SystemExit(f'kv_ctl_nc32_face: lprg {a}: {t.count(a)}')
        t = t.replace(a, b)
    t = one(t, 'ctrl_go<=|e_ctrl;', 'ctrl_go<=|e_ctrl;ctrl_go_e<=|e_ctrl;', 'ctrl_go set')
    t = one(t, 'kgo<=|e_k;', 'kgo<=|e_k;kgo_e<=|e_k;', 'kgo set')
    t = one(t, 'vgo<=|e_v;', 'vgo<=|e_v;vgo_e<=|e_v;', 'vgo set')
    t = one(t, 'owner<=0;stage_o<=0;', 'owner<=0;stage_o<=0;stage_oe<=0;', 'stage reset')
    m = re.search(r'stage_o<=(\(e_end\[fire_u\][^;]*);', t)
    if not m or t.count(m.group(0)) != 1:
        raise SystemExit('kv_ctl_nc32_face: stage_o update')
    t = t.replace(m.group(0), m.group(0) + f'stage_oe<={m.group(1)};')
    t = one(t, ' assign layer=stage-6\'d1;\n',
            ' assign layer=stage-6\'d1;\n assign layer_e=((MUT==2)?(stage_oe^6\'d1):stage_oe)-6\'d1;\n', 'layer_e')
    t = one(t, 'if(!rn)begin om<=0;oag<=0;otc<=0;end else begin om<=omx;oag<=oax;otc<=otx;end\n',
            'if(!rn)begin om<=0;oag<=0;otc<=0;om_e_ep<=0;om_e_ct<=0;end else begin om<=omx;oag<=oax;otc<=otx;'
            'om_e_ep<=omx[0+:16];om_e_ct<=omx[52+:14];end\n assign epoch_e=om_e_ep;assign ctx_t_e=om_e_ct;\n', 'om_e')
    t = one(t, 'endmodule\n', '`ifndef SYNTHESIS\n // bench self-check: every E-face copy equals its original on every edge (a copy mutant stops the bench)\n always @(negedge ck) if ({ctrl_go_e, kgo_e, vgo_e, stage_oe, om_e_ep, om_e_ct} !== {ctrl_go, kgo, vgo, stage_o, om[0+:16], om[52+:14]}) $fatal(1, "qkd_static_kv_layer_programme_nc32: E-face copy differs from its original");\n`endif\nendmodule\n', 'lprg check')
    return t


E_SRC = {'w_fanr__h': 'w_fanr__h_e', 'w_boot__group_data': 'w_boot__group_data_e',
         'w_boot__group_addr': 'w_boot__group_addr_e', 'w_boot__controller_data': 'w_boot__controller_data_e',
         'w_boot__controller_addr': 'w_boot__controller_addr_e', 'w_lprg__epoch': 'w_lprg__epoch_e',
         'w_lprg__ctx_t': 'w_lprg__ctx_t_e', 'w_lprg__layer': 'w_lprg__layer_e', 'w_lprg__kgo': 'w_lprg__kgo_e',
         'w_lprg__vgo': 'w_lprg__vgo_e', 'w_lprg__ctrl_go': 'w_lprg__ctrl_go_e'}
E_W = {'w_fanr__h': '[783:0]', 'w_boot__group_data': '[63:0]', 'w_boot__group_addr': '[7:0]',
       'w_boot__controller_data': '[63:0]', 'w_boot__controller_addr': '[7:0]', 'w_lprg__epoch': '[15:0]',
       'w_lprg__ctx_t': '[13:0]', 'w_lprg__layer': '[5:0]', 'w_lprg__kgo': '[0:0]', 'w_lprg__vgo': '[0:0]',
       'w_lprg__ctrl_go': '[0:0]'}


def ctl_body(c32i):
    b = re.search(r'^module qkd_kvs_ctl \(.*?^endmodule\n', c32i, re.S | re.M).group(0)
    if hashlib.sha256(b.encode()).hexdigest() != CTL_BODY_SHA:
        raise SystemExit('kv_ctl_nc32_face: c32i ctl body changed')
    decl = ''.join(f'    wire {E_W[k]} {v};\n' for k, v in E_SRC.items())
    b = one(b, '    wire [3:0] w_wprg__compiled_word_slot_c;\n', decl + '    wire [3:0] w_wprg__compiled_word_slot_c;\n', 'decl')
    b = one(b, 'qkd_static_kv_boot_dispatch_mu_c32 #(', 'qkd_static_kv_boot_dispatch_mu_nc32 #(', 'boot master')
    b = one(b, 'qkd_kv_es_fan_root2_b_c32 #(.MUT(0), .RCOPIES(32),', 'qkd_kv_es_fan_root2_b_nc32 #(.MUT(0), .RCOPIES(64),',
            'fanr master')   # h_e doubles the reset loads of the split rs_q family (784 -> 1568): 64 kept copies
    b = one(b, 'qkd_static_kv_layer_programme_s32 #(', 'qkd_static_kv_layer_programme_nc32 #(', 'lprg master')
    # extra connections (appended to each instance's port list)
    def addc(b, inst, conns):
        m = re.search(r'^(    \S+ #\(.*?\) ' + inst + r' \()(.*?)(\);\n)', b, re.M)
        if not m:
            raise SystemExit(f'kv_ctl_nc32_face: instance {inst}')
        return b[:m.end(2)] + ', ' + ', '.join(conns) + b[m.end(2):]
    b = addc(b, 'u_fanr', ['.h_e(w_fanr__h_e)'])
    b = addc(b, 'u_boot', ['.group_addr_e(w_boot__group_addr_e)', '.group_data_e(w_boot__group_data_e)',
                           '.controller_addr_e(w_boot__controller_addr_e)', '.controller_data_e(w_boot__controller_data_e)'])
    b = addc(b, 'u_lprg', ['.ctrl_go_e(w_lprg__ctrl_go_e)', '.kgo_e(w_lprg__kgo_e)', '.vgo_e(w_lprg__vgo_e)',
                           '.layer_e(w_lprg__layer_e)', '.epoch_e(w_lprg__epoch_e)', '.ctx_t_e(w_lprg__ctx_t_e)'])
    for port in ('o_hroot_ES', 'o_hroot_EN'):
        m = re.search(r'^    assign ' + port + r' = (.*?);\n', b, re.M)
        rhs = re.sub(r'\b(' + '|'.join(E_SRC) + r')\b', lambda x: E_SRC[x.group(1)], m.group(1))
        b = b[:m.start(1)] + rhs + b[m.end(1):]
    hdr = ('`timescale 1ns/1ps\n'
           '// KDIE5-RTL 10-22 (OT_KV_CTL_NC32=1, default off): the native-census successor of the RELEASE KV die control tile\n'
           '// qkd_kvs_ctl (relm point qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv; ctl body == _k_mu_ba body, sha256\n'
           '// cc153f58e9e00348699ffe78e852449db1ff7efed939156000097ef511981d38).  GENERATED by tools/qwen_kv_die/kv_ctl_nc32_face.py\n'
           f'// from the c32i body ({C32I}, KV-CTL10 c32 members + DSTG; census PASS max 32 in gate c32k; body sha256\n'
           f'// {CTL_BODY_SHA}) with the E-face register copies of {OUT} (fanr h, boot group / controller\n'
           '// words, lprg epoch / ctx_t / layer / kgo / vgo / ctrl_go): the E words read the copies.  Same 62 ports.\n'
           '// Schedule deltas vs the release ctl: u_own PIPE1 SAFE1 (leave drain guard +2 ck), u_boot SRQ 2 (boot__setup_ready\n'
           '// +2, host boot boundary), DSTG 1 (+1 boot-write edge); every token-path port edge +0 (face copies add 0 edges).\n')
    return hdr + b


def generate():
    for rel in (MISC, BOOT, LPRG, C32I):
        read(rel)
    hdr = ('`timescale 1ns/1ps\n// KDIE5-RTL 10-22: E-face register copies of the c32 ctl members (opt-in via OT_KV_CTL_NC32; shared files\n'
           '// untouched).  GENERATED by tools/qwen_kv_die/kv_ctl_nc32_face.py from sha-pinned sources; do not edit.\n\n')
    out = hdr + fanr(read(MISC)) + '\n' + boot(read(BOOT)) + '\n' + lprg(read(LPRG))
    return out, ctl_body(read(C32I))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out, ctl = generate()
    if a.check:
        bad = [p for p, t in ((OUT, out), (CTL, ctl)) if (ROOT / p).read_text() != t]
        print('kv_ctl_nc32_face: ' + ('DIFF ' + ' '.join(bad) if bad else 'current'))
        sys.exit(1 if bad else 0)
    (ROOT / OUT).write_text(out)
    (ROOT / CTL).write_text(ctl)
    print('wrote', OUT, CTL)


if __name__ == '__main__':
    main()
