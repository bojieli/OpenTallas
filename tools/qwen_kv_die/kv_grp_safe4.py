#!/usr/bin/env python3
"""KV-GRP5 2026-10-19: s4 successor of the KV landing-group tile qkd_kvs_grp_h_s2 -> qkd_kvs_grp_h_s4 (default off).

Why (s3 gate review, lanes/KV-GRP4.md): both grp_h s3 gates showed reg->out -345 / -350 ps on rsp[527] (TT placement
RC).  rsp and krsp are two face copies of ONE row-control output register set (qkd_static_kv_rowctl rsp_*): each rsp
data flop drives rsp[32+i] AND krsp[1+i], two E-face pins ~196 um apart, so the flop sits between them and both
pins pay a long unbuffered output wire inside the 0.2 T IO budget (the grp twin met +93.8 by placement luck only).

s4 (SAFE 1 / 3, +0 cycles): the row-control output stage is built twice as KEPT exit copies, one per face group:
  u_rsp_x  -> rsp  = {data, epoch, t, v, valid}         (the rsp pins)
  u_krsp_x -> krsp = {layer, epoch, v, t, data, valid}  (the krsp pins)
Both copies take D from the same internal stage (idata / it / ivv / ie / il / iv, already registered), on the same edge
as the old single output register, so every output bit is cycle-identical to s2/s3 (bench-proven).  Each copy is the
unparameterised (* keep_hierarchy *) module qkd_kvs_rsp_exit_s4 (also in the kit's SYNTH_KEEP_MODULES), so synthesis
cannot opt_merge the two copies back into one register set; the placer puts each copy beside its own pins and the
internal stage -> copy hop gets the whole cycle.  Cost: +1062 flops per group tile (one more 1062-b register row), no
schedule change.

Derived MECHANICALLY from sha-pinned sources (refuses on drift); no shared file is modified (s3 kits keep their sources):
  qkd_kvs_grp_s2.sv (KV-GRP3 s3 generation of kv_grp_safe2.py): qkd_kvs_grp_h_s2, qkd_static_kv_landing_seg_s2
  qkd_static_kv_landing.sv: qkd_static_kv_rowctl
The s4 file holds only the new modules; a kit reads it together with qkd_kvs_grp_s2.sv (leaves pc_s2 / lcal_s2 / rst).
Mutants (bench negative controls, every one must FAIL; m1..m8 of kv_grp_safe2 still apply):
  9  krsp exit copy: data bit 0 inverted (krsp face copy on the compared path)
  10 rsp exit copy: t bit 0 inverted (rsp face copy on the compared path)

    python3 tools/qwen_kv_die/kv_grp_safe4.py            # writes rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s4.sv
    python3 tools/qwen_kv_die/kv_grp_safe4.py --check    # regenerate in memory, fail on any difference
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S2F = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s2.sv'
LANDING = 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv'
OUT = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s4.sv'
SHA = {
    S2F: '591406c831dd4b565a98725bd275fc627b1ce97f47a5cfa869943f2320d4a46b',
    LANDING: '54e52aa0e901080a940eb4911b86baa70821c69bdae7982d7e4ebbc30ed1ae41',
}
TOP = 'qkd_kvs_grp_h_s4'
KEEP = 'qkd_kvs_rsp_exit_s4'
MUTANTS = {
    9: 'krsp exit copy: data bit 0 inverted',
    10: 'rsp exit copy: t bit 0 inverted',
}


def read(rel):
    t = (ROOT / rel).read_text()
    h = hashlib.sha256(t.encode()).hexdigest()
    if h != SHA[rel]:
        raise SystemExit(f'kv_grp_safe4: source identity changed: {rel} {h}')
    return t


def module(text, name):
    m = re.search(r'^module ' + re.escape(name) + r'\b.*?^endmodule\n', text, re.S | re.M)
    if not m:
        raise SystemExit(f'kv_grp_safe4: module {name} missing')
    return m.group(0)


def one(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit(f'kv_grp_safe4: {what}: expected exactly one match, found {text.count(old)}')
    return text.replace(old, new)


EXIT = f"""// KV-GRP5: one KEPT exit copy of the row-control response stage (1062 b = krsp order {{layer, epoch, v, t, data,
// valid}}).  valid is reset (asynchronously, by the row control's landed rn) exactly as the old rsp_valid; the payload
// has no reset, as before.  keep_hierarchy (and the kit's SYNTH_KEEP_MODULES) keeps the two instances separate.
(* keep_hierarchy *)
module {KEEP} (input wire ck, input wire rn, input wire [1061:0] d, output wire [1061:0] q);
    (* keep *) reg v;
    (* keep *) reg [1060:0] p;
    always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= d[0];
    always @(posedge ck) p <= d[1061:1];
    assign q = {{p, v}};
endmodule
"""


def rowctl():
    r = module(read(LANDING), 'qkd_static_kv_rowctl')
    r = one(r, 'module qkd_static_kv_rowctl #(parameter integer VREQ=0,parameter integer DATA=1)(',
            'module qkd_static_kv_rowctl_s4 #(parameter integer VREQ=0,parameter integer DATA=1,parameter integer MUT=0)(',
            'rowctl header')
    r = one(r, '    output reg rsp_valid,output reg [1023:0] rsp_data,output reg [13:0] rsp_t,\n'
               '    output reg rsp_v,output reg [15:0] rsp_epoch,output reg [5:0] rsp_layer,output reg fault\n);',
            '    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,\n'
            '    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output reg fault,\n'
            '    output wire [1061:0] krsp_w\n);\n    wire [1023:0] xdata;', 'rowctl ports')
    r = one(r, '      always @(posedge ck)begin idata<=pc_data;rsp_data<=idata;end',
            '      always @(posedge ck)idata<=pc_data;\n      assign xdata=idata;', 'rowctl data')
    r = one(r, "      always @(*)rsp_data=1024'd0;", "      assign xdata=1024'd0;", 'rowctl nodata')
    r = one(r, '      rsp_t<=it[13:0];rsp_v<=ivv[0];rsp_epoch<=ie[15:0];rsp_layer<=il[5:0];\n', '', 'rowctl meta')
    r = one(r, 'if(!rn)begin iv<=0;ifault<=0;rsp_valid<=0;fault<=0;end', 'if(!rn)begin iv<=0;ifault<=0;fault<=0;end',
            'rowctl reset')
    r = one(r, 'iv<=pc_valid;ifault<=pc_fault;rsp_valid<=iv[0];', 'iv<=pc_valid;ifault<=pc_fault;', 'rowctl valid')
    tail = """    // KV-GRP5 s4: the old single output register set (rsp_*) is now two KEPT exit copies with the same D and edge,
    // one per E-face pin group (rsp / krsp), so no data flop drives two pins ~196 um apart.  +0 cycles.
    wire [1061:0] xd = {il[5:0], ie[15:0], ivv[0], it[13:0], xdata, iv[0]};
    wire [1061:0] ra, kb;
    QKEEP u_rsp_x (.ck(ck), .rn(rn), .d((MUT == 10) ? (xd ^ (1062'd1 << 1025)) : xd), .q(ra));
    QKEEP u_krsp_x (.ck(ck), .rn(rn), .d((MUT == 9) ? (xd ^ 1062'd2) : xd), .q(kb));
    assign {rsp_layer, rsp_epoch, rsp_v, rsp_t, rsp_data, rsp_valid} = ra;
    assign krsp_w = kb;
endmodule
""".replace('QKEEP', KEEP)
    r = one(r, 'endmodule\n', tail, 'rowctl end')
    return ('// KV-GRP5: qkd_static_kv_rowctl with the response output stage as two kept exit copies (rsp / krsp faces).\n'
            '// Derived by tools/qwen_kv_die/kv_grp_safe4.py; every other line is the sha-pinned leaf.\n' + r)


def seg(s2):
    t = module(s2, 'qkd_static_kv_landing_seg_s2')
    t = one(t, 'module qkd_static_kv_landing_seg_s2 #(\n    parameter integer MUT=0,HOP_MUT=0\n)(',
            'module qkd_static_kv_landing_seg_s4 #(\n    parameter integer MUT=0,HOP_MUT=0,KMUT=0\n)(', 'seg header')
    t = one(t, 'output wire [5:0] rsp_layer,output wire fault\n);',
            'output wire [5:0] rsp_layer,output wire fault,\n    output wire [1061:0] krsp_w\n);', 'seg ports')
    t = one(t, '    qkd_static_kv_rowctl #(.VREQ(1)) u_rowctl(', '    qkd_static_kv_rowctl_s4 #(.VREQ(1),.MUT(KMUT)) u_rowctl(',
            'seg rowctl')
    t = one(t, '.rsp_layer(rsp_layer),.fault(fault));', '.rsp_layer(rsp_layer),.fault(fault),.krsp_w(krsp_w));', 'seg conn')
    return '// KV-GRP5: qkd_static_kv_landing_seg_s2 on qkd_static_kv_rowctl_s4 (krsp exit copy out).  Derived by kv_grp_safe4.py.\n' + t


def tile(s2):
    t = module(s2, 'qkd_kvs_grp_h_s2')
    t = one(t, 'module qkd_kvs_grp_h_s2 #(parameter integer MUT = 0) (', f'module {TOP} #(parameter integer MUT = 0) (', 'tile')
    t = one(t, '    qkd_static_kv_landing_seg_s2 #(.MUT((MUT == 6) ? 2 : 0), .HOP_MUT(0)) u_slg (',
            '    wire [1061:0] w_slg__krsp_w;\n'
            '    qkd_static_kv_landing_seg_s4 #(.MUT((MUT == 6) ? 2 : 0), .HOP_MUT(0), .KMUT((MUT == 9 || MUT == 10) ? MUT : 0)) u_slg (',
            'tile seg')
    t = one(t, '.rsp_layer(w_slg__rsp_layer), .fault(w_slg__fault));',
            '.rsp_layer(w_slg__rsp_layer), .fault(w_slg__fault), .krsp_w(w_slg__krsp_w));', 'tile seg conn')
    t = one(t, '    assign krsp = {w_slg__rsp_layer, w_slg__rsp_epoch, w_slg__rsp_v, w_slg__rsp_t, w_slg__rsp_data, w_slg__rsp_valid};',
            '    assign krsp = w_slg__krsp_w;   // KV-GRP5 s4: the krsp face leaves its own kept exit copy', 'tile krsp')
    return ('// KV-GRP5 s4 tile: qkd_kvs_grp_h_s2 (s3 generation) with rsp / krsp leaving separate kept exit copies.\n' + t)


def build():
    s2 = read(S2F)
    text = ('`timescale 1ns/1ps\n// KV-GRP5 2026-10-19 s4 KV landing-group tile qkd_kvs_grp_h_s4 (default off).  GENERATED by\n'
            '// tools/qwen_kv_die/kv_grp_safe4.py from sha-pinned sources; do not edit.  Read together with qkd_kvs_grp_s2.sv.\n\n'
            + tile(s2) + '\n' + seg(s2) + '\n' + rowctl() + '\n' + EXIT)
    return text, dict(top=TOP, keep=KEEP, sources=SHA, mutants=MUTANTS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, rec = build()
    if a.check:
        if (ROOT / OUT).read_text() != text:
            raise SystemExit(f'kv_grp_safe4 --check: stale {OUT}')
        print('kv_grp_safe4 --check PASS')
        return
    (ROOT / OUT).write_text(text)
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
