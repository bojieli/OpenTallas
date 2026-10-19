#!/usr/bin/env python3
"""KV-GRP2 2026-10-19: structurally safe KV landing-group tiles qkd_kvs_grp_s2 / qkd_kvs_grp_h_s2 (default off).

Derived MECHANICALLY from sha-pinned sources (refuses on any drift); no shared leaf file is modified (every closed view
that lists those leaves keeps its source identity):
  base   = the DOMSPLIT MU/BOOT_AGES group tiles (qkd_kvs_tiles_hroot_ff_k_mu_ba_ds.sv: o_pc<j> = 33 core-clock bits,
           o_pc<j>_h = 95 HBM-clock bits; i_pc<j> / i_pc<j>_h split; the 10 HBM boot status levels landed in-group)
  ABI    = Stage 1 private deletion (da972c4c7: x__tok / x__tep / y__tok / y__tep removed, EST scalar; H: o_dn and
           i_ctl[270:194] removed) -> the y__tep -74.9 ps hold path no longer exists
  faces  = every input that reached logic or an output before a flop now lands on a KEPT face flop, one copy per consumer
           leaf (fanout <= 6 per pin): i_ctl (boot cfg of the five boot CDCs, landing / phase calendar words), i_up
           (gather), x__est; o_dn / o_ctl / y__est leave flops (no combinational input->output path is left)
  reset  = rst_n / hrst_n land in 2 stages per domain (async assert, synchronous release on its own clock), one kept
           final-stage copy per leaf
  storage= landing rows: ot_sram_1r1w_128x256_m1_r2c2_p192_mir (same 128x256 r2c2 array, 0.192-um contact pitch,
           5.09 contacts/um vs 9.98); landing calendar LD delay line dl[8]x11 -> 8-entry pointer ring + history bits
Behaviour: safe2(x) == base(x') exactly, where x' = i_ctl, i_up, x__est one core edge later and rst_n / hrst_n released
two edges later in their own domain (bench tb_kvs_grp_s2_eq, tools/qwen_kv_die/kvs_grp_s2_bench.sh).

Schedule (handed to the die / compiler, KV-GEN9 inbox): +1 core edge per group on the control fan word (a group at
chain depth d from its stack root, d = 0 at slot 7, sees the root word d + 1 edges later than the combinational
chain), +1 per group on the 18-b status gather, +1 on EST (boot-ready level), +1 on the boot cfg words (boot FIFOs are
elastic), reset release +2 core / +2 HBM edges.  K / V request -> response (8 edges) and the PC faces are unchanged.

    python3 tools/qwen_kv_die/kv_grp_safe2.py            # writes rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s2.sv
    python3 tools/qwen_kv_die/kv_grp_safe2.py --check    # regenerate in memory, fail on any difference
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba_ds.sv'
LANDING = 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv'
SEG = 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing_seg.sv'
LCAL = 'rtl/qwen_sys/static_kv_20261014/qkd_kv_landing_cal.sv'
OUT = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s2.sv'
REF = 'rtl/qwen_sys/static_kv_die_20261017/tb/qkd_kvs_grp_s2_ref.sv'
MACRO = 'ot_sram_1r1w_128x256_m1_r2c2_p192_mir'
MACRO_DIR = 'physical/asap7_memory_macros/' + MACRO
SHA = {
    BASE: '70b837783e28e56f0f5d6f34574b6974552715cd89a985af94e7c6a3bc7dd25e',
    LANDING: '54e52aa0e901080a940eb4911b86baa70821c69bdae7982d7e4ebbc30ed1ae41',
    SEG: '2e0c93c17c26418d1f0be1c2afe089d29a5ce332bd3807295ff128e0c8f62ce2',
    LCAL: '2712faf10864334991cfdee2970065b422d35e50921d7181ab055452f53915af',
}
KINDS = (('qkd_kvs_grp', 'qkd_kvs_grp_s2'), ('qkd_kvs_grp_h', 'qkd_kvs_grp_h_s2'))
DELETED = ('x__tok', 'x__tep', 'y__tok', 'y__tep')
# bench mutants (MUT of the tile; every one must FAIL the equivalence bench)
MUTANTS = {
    1: 'landing calendar ring tap one entry late (LD ages)',
    2: 'boot CDC 1 cfg face flop bypassed (combinational i_ctl -> FIFO)',
    3: 'EST face flop bypassed (combinational x__est -> y__est)',
    4: 'core reset lands in one stage instead of two',
    5: 'gather i_up face flop bypassed (combinational i_up -> o_ctl)',
    6: 'landing row data path: SRAM read word bit 0 inverted (p192 macro on the compared path)',
    7: 'o_dn chain face copy: bits 0 and 1 swapped',
}


def read(rel):
    t = (ROOT / rel).read_text()
    h = hashlib.sha256(t.encode()).hexdigest()
    if h != SHA[rel]:
        raise SystemExit(f'kv_grp_safe2: source identity changed: {rel} {h}')
    return t


def module(text, name):
    m = re.search(r'^module ' + re.escape(name) + r'\b.*?^endmodule\n', text, re.S | re.M)
    if not m:
        raise SystemExit(f'kv_grp_safe2: module {name} missing')
    return m.group(0)


def one(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit(f'kv_grp_safe2: {what}: expected exactly one match, found {text.count(old)}')
    return text.replace(old, new)


# ------------------------------------------------------------------------------------------------ derived leaves
def leaves():
    pc = module(read(LANDING), 'qkd_static_kv_landing_pc')
    pc = one(pc, 'module qkd_static_kv_landing_pc #(', 'module qkd_static_kv_landing_pc_s2 #(', 'pc name')
    pc = one(pc, '    ot_sram_1r1w_128x256_m1_r2c2 u_rows(', f'    {MACRO} u_rows(', 'pc macro')
    pc = ('// KV-GRP2: qkd_static_kv_landing_pc with the row array on the 0.192-um contact-pitch build of the same\n'
          '// 128x256 r2c2 array (identical ports, core, behaviour, latency).  Derived by tools/qwen_kv_die/kv_grp_safe2.py.\n'
          + pc)
    seg = module(read(SEG), 'qkd_static_kv_landing_seg')
    seg = one(seg, 'module qkd_static_kv_landing_seg #(', 'module qkd_static_kv_landing_seg_s2 #(', 'seg name')
    seg = one(seg, '      qkd_static_kv_landing_pc #(', '      qkd_static_kv_landing_pc_s2 #(', 'seg pc master')
    seg = '// KV-GRP2: qkd_static_kv_landing_seg on qkd_static_kv_landing_pc_s2.  Derived by kv_grp_safe2.py.\n' + seg
    lc = module(read(LCAL), 'qkd_kv_landing_cal')
    lc = one(lc, 'module qkd_kv_landing_cal #(', 'module qkd_kv_landing_cal_s2 #(', 'lcal name')
    old = """    reg [10:0] dl [0:7];                                // LD 0..8 (return slot output register + <= 6 relays)
    integer k;
    always @(posedge ck or negedge rn)
        if (!rn) begin r_put <= 0; l_put <= 0; for (k = 0; k < 8; k = k + 1) dl[k] <= 0; end
        else begin
            r_put <= {4{put_now}};
            dl[0] <= {put_now, sec};
            for (k = 1; k < 8; k = k + 1) dl[k] <= dl[k-1];
            l_put <= {4{(ld_c == 0) ? put_now : dl[3'(ld_c - 4'd1)][10]}};
        end
    always @(posedge ck) begin
        r_sector <= {4{sec}};
        l_sector <= {4{(ld_c == 0) ? sec : dl[3'(ld_c - 4'd1)][9:0]}};
"""
    new = """    // KV-GRP2 (SAFE 5): the LD delay line is an 8-entry pointer RING, not an 8-deep flop shift chain.  Entry wp is
    // written every edge with {put_now, sec}; the historical dl[j] (= the word j + 1 edges old) is rg[wp - 1 - j]
    // once written; hv[e] (reset 0) marks entries written since reset, so the zero fill after reset is exact.  The tap
    // keeps the 3-bit cast of the historical index (LD 9..15 alias LD 1..7 exactly as before); payload has no reset.
    reg [10:0] rg [0:7];
    reg [7:0] hv;
    reg [2:0] wp;
    wire [2:0] tap = 3'(ld_c - 4'd1);
    wire [2:0] ra = wp - 3'd1 - tap - ((MUT == 4) ? 3'd1 : 3'd0);
    wire [10:0] dlt = hv[ra] ? rg[ra] : 11'd0;
    always @(posedge ck) rg[wp] <= {put_now, sec};
    always @(posedge ck or negedge rn)
        if (!rn) begin r_put <= 0; l_put <= 0; wp <= 3'd0; hv <= 8'd0; end
        else begin
            r_put <= {4{put_now}};
            wp <= wp + 3'd1;
            hv[wp] <= 1'b1;
            l_put <= {4{(ld_c == 0) ? put_now : dlt[10]}};
        end
    always @(posedge ck) begin
        r_sector <= {4{sec}};
        l_sector <= {4{(ld_c == 0) ? sec : dlt[9:0]}};
"""
    lc = one(lc, old, new, 'lcal dl ring')
    lc = ('// KV-GRP2: qkd_kv_landing_cal with the LD delay line as a pointer ring (MUT 4 = tap one entry late).\n'
          '// Derived by tools/qwen_kv_die/kv_grp_safe2.py; every other line is the sha-pinned leaf.\n' + lc)
    return [pc, seg, lc]


RST = """// KV-GRP2: per-domain reset landing of one group tile: rst_n (core ck) and hrst_n (HBM hck) each land in two
// registered stages beside the tile's register mass (asynchronous assert, release on the second edge of its own clock),
// and the second stage is one KEPT flop per consumer leaf (NC core / NH HBM copies), so no reset port drives the leaves.
// MUT 4 (bench negative control): the core copies take rst_n through one stage.
module qkd_kvs_grp_s2_rst #(parameter integer NC = 1, parameter integer NH = 1, parameter integer MUT = 0) (
    input wire ck, input wire rst_n, input wire hck, input wire hrst_n,
    output wire [NC-1:0] rc, output wire [NH-1:0] rh
);
    (* keep *) reg c1;
    (* keep *) reg h1;
    always @(posedge ck or negedge rst_n) if (!rst_n) c1 <= 1'b0; else c1 <= 1'b1;
    always @(posedge hck or negedge hrst_n) if (!hrst_n) h1 <= 1'b0; else h1 <= 1'b1;
    genvar i;
    generate
        for (i = 0; i < NC; i = i + 1) begin : g_c
            (* keep *) reg c2;
            always @(posedge ck or negedge rst_n) if (!rst_n) c2 <= 1'b0; else c2 <= (MUT == 4) ? 1'b1 : c1;
            assign rc[i] = c2;
        end
        for (i = 0; i < NH; i = i + 1) begin : g_h
            (* keep *) reg h2;
            always @(posedge hck or negedge hrst_n) if (!hrst_n) h2 <= 1'b0; else h2 <= h1;
            assign rh[i] = h2;
        end
    endgenerate
endmodule
"""


# ------------------------------------------------------------------------------------------------ tiles
def private0(body, name):
    """Stage 1 private ABI deletion on the DS body (same rule set as kv_grp_private0.private_text)"""
    for port in DELETED:
        body, n = re.subn(r'^    (?:input|output) wire \[\d+:0\] ' + port + r',\n', '', body, flags=re.M)
        if n != 1:
            raise SystemExit(f'kv_grp_safe2: {name}: port {port}')
    for eq in ('    assign y__tok = x__tok;\n', '    assign y__tep = x__tep;\n'):
        body = one(body, eq, '', f'{name} {eq.strip()}')
    body = one(body, 'input wire [12:0] x__est,', 'input wire x__est,', f'{name} est')
    body = one(body, 'assign y__est__0_1 = x__est[0:0];', 'assign y__est__0_1 = x__est;', f'{name} est eq')
    if name.endswith('_h'):
        body = one(body, '    output wire [270:0] o_dn,\n', '', 'h o_dn')
        body = one(body, 'input wire [270:0] i_ctl,', 'input wire [193:0] i_ctl,', 'h i_ctl')
        body = one(body, '    assign o_dn = {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};\n', '', 'h o_dn eq')
    return body


def bits_of(hi, lo):
    return list(range(lo, hi + 1))


def tile(base_body, name, new):
    body = private0(base_body, name)
    body = one(body, f'module {name} (', f'module {new} #(parameter integer MUT = 0) (', f'{name} header')
    head, sep, rest = body.partition('\n);\n')
    if not sep:
        raise SystemExit(f'kv_grp_safe2: {name}: port list end')
    lines = rest.split('\n')
    # wires that alias i_ctl slices (the leaf cfg / calendar words)
    alias = {}
    for ln in lines:
        m = re.match(r'    wire \[(\d+):(\d+)\] (\w+) = i_ctl\[(\d+):(\d+)\];$', ln)
        if m:
            alias[m.group(3)] = (int(m.group(4)), int(m.group(5)))
    out_lines, face, rcopies, hcopies = [], [], [], []
    for ln in lines:
        m = re.match(r'    (\w+) (#\(.*?\) )?(u_\w+) \((.*)\);$', ln)
        if not m:
            out_lines.append(ln)
            continue
        master, par, inst, conns = m.group(1), m.group(2) or '', m.group(3), m.group(4)
        # (1) i_ctl aliases -> this leaf's own kept face copy
        used = []
        for port, net in re.findall(r'\.(\w+)\((\w+)\)', conns):
            if net in alias:
                hi, lo = alias[net]
                used += [b for b in bits_of(hi, lo) if b not in used]
        if used:
            used.sort()
            cp = f'icq_{inst[2:]}'
            face.append((cp, used, inst))
            pos = {b: i for i, b in enumerate(used)}

            def sub(mm, cp=cp, pos=pos):
                port, net = mm.group(1), mm.group(2)
                if net not in alias:
                    return mm.group(0)
                hi, lo = alias[net]
                a, b = pos[hi], pos[lo]
                if a - b != hi - lo:
                    raise SystemExit(f'kv_grp_safe2: non-contiguous face slice {inst}.{port}')
                src = f'{cp}[{a}:{b}]' if hi != lo else f'{cp}[{a}]'
                if inst == 'u_bcdc1' and port == 'cfg_data':     # MUT 2: bcdc1 cfg data bypasses its face flop
                    src = f'((MUT == 2) ? i_ctl[{hi}:{lo}] : {src})'
                return f'.{port}({src})'
            conns = re.sub(r'\.(\w+)\((\w+)\)', sub, conns)
        # (2) resets -> one kept landed copy per leaf and domain
        def rsub(mm):
            port, net = mm.group(1), mm.group(2)
            if net == 'rst_n':
                rcopies.append(inst)
                return f'.{port}(rc[{len(rcopies) - 1}])'
            if net == 'hrst_n':
                hcopies.append(inst)
                return f'.{port}(rh[{len(hcopies) - 1}])'
            return mm.group(0)
        conns = re.sub(r'\.(\w+)\((rst_n|hrst_n)\)', rsub, conns)
        # (3) derived leaves
        if master == 'qkd_static_kv_landing_seg':
            master = 'qkd_static_kv_landing_seg_s2'
            par = one(par, '.MUT(0)', '.MUT((MUT == 6) ? 2 : 0)', 'seg MUT')
        elif master == 'qkd_kv_landing_cal':
            master = 'qkd_kv_landing_cal_s2'
            par = one(par, '.MUT(0)', '.MUT((MUT == 1) ? 4 : 0)', 'lcal MUT')
        out_lines.append(f'    {master} {par}{inst} ({conns});')
    body_txt = '\n'.join(out_lines)
    # (4) outputs that were combinational from inputs leave face flops
    decl = []
    if not name.endswith('_h'):
        body_txt = one(body_txt, '    assign o_dn = {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};',
                       '    assign o_dn = {icq_o[193:183], icq_o[270:194], '
                       '(MUT == 7) ? {icq_o[182:2], icq_o[0], icq_o[1]} : icq_o[182:0]};', 'o_dn')
        face.append(('icq_o', list(range(271)), 'o_dn'))
        body_txt = one(body_txt, 'assign o_ctl = {i_up[125:0], {', 'assign o_ctl = {((MUT == 5) ? i_up[125:0] : iuq), {',
                       'o_ctl gather')
        decl.append('    (* keep *) reg [125:0] iuq;      // gather face: the upstream groups\' status words\n'
                    '    always @(posedge ck) iuq <= i_up[125:0];')
    body_txt = one(body_txt, '    assign y__est__0_1 = x__est;', '    assign y__est__0_1 = (MUT == 3) ? x__est : estq;', 'est')
    decl.append('    (* keep *) reg estq;             // EST face (boot-ready level to the four PCs)\n'
                '    always @(posedge ck) estq <= x__est;')
    for cp, used, inst in face:
        n = len(used)
        src = ', '.join(f'i_ctl[{b}]' for b in reversed(used)) if cp != 'icq_o' else 'i_ctl'
        decl.append(f'    (* keep *) reg [{n - 1}:0] {cp};   // face copy for {inst}: i_ctl bits {used[0]}..{used[-1]} ({n})\n'
                    f'    always @(posedge ck) {cp} <= {{{src}}};' if cp != 'icq_o' else
                    f'    (* keep *) reg [270:0] icq_o;   // face copy for the o_dn chain hop\n'
                    f'    always @(posedge ck) icq_o <= i_ctl;')
    rst = (f'    wire [{len(rcopies) - 1}:0] rc;\n    wire [{len(hcopies) - 1}:0] rh;\n'
           f'    // landed resets: rc[k] / rh[k] = one kept copy per leaf ({", ".join(rcopies)} | {", ".join(hcopies)})\n'
           f'    qkd_kvs_grp_s2_rst #(.NC({len(rcopies)}), .NH({len(hcopies)}), .MUT(MUT)) u_rst (.ck(ck), .rst_n(rst_n), '
           f'.hck(hck), .hrst_n(hrst_n), .rc(rc), .rh(rh));')
    # the i_ctl alias wires are now unread: drop them (every leaf reads its own face copy)
    for net in alias:
        decl_ln = re.search(r'^    wire \[\d+:\d+\] ' + net + r' = i_ctl\[\d+:\d+\];\n', body_txt, re.M)
        body_txt = body_txt.replace(decl_ln.group(0), '')
        if re.search(r'\b' + net + r'\b', body_txt):
            raise SystemExit(f'kv_grp_safe2: {name}: alias {net} still read after the face rewrite')
    hdr = (f'// KV-GRP2 safe tile {new}: {name} (DOMSPLIT MU/BOOT_AGES, Stage 1 private ABI) with registered faces,\n'
           '// landed per-domain resets, p192 landing rows and the ring LD delay.  GENERATED by tools/qwen_kv_die/kv_grp_safe2.py.\n')
    return hdr + head + sep + rst + '\n' + '\n'.join(decl) + '\n' + body_txt, dict(
        face=[dict(copy=c, bits=len(u), consumer=i) for c, u, i in face], core_resets=rcopies, hbm_resets=hcopies)


def ref_text(base):
    """bench reference: the unchanged DS bodies (renamed *_ref) on the unchanged leaves"""
    out = []
    for name, _ in KINDS:
        b = module(base, name)
        out.append(one(b, f'module {name} (', f'module {name}_ref (', name))
    return ('`timescale 1ns/1ps\n// KV-GRP2 bench reference: the sha-pinned DOMSPLIT MU/BOOT_AGES group tiles, renamed only.\n'
            '// GENERATED by tools/qwen_kv_die/kv_grp_safe2.py.\n' + '\n'.join(out))


def build():
    base = read(BASE)
    mods, rec = [], {}
    for name, new in KINDS:
        txt, r = tile(module(base, name), name, new)
        mods.append(txt)
        rec[new] = r
    text = ('`timescale 1ns/1ps\n// KV-GRP2 2026-10-19 structurally safe KV landing-group tiles (default off).  GENERATED by\n'
            '// tools/qwen_kv_die/kv_grp_safe2.py from sha-pinned sources; do not edit.  See the generator docstring.\n\n'
            + '\n'.join(mods) + '\n' + RST + '\n' + '\n'.join(leaves()))
    rec['sources'] = SHA
    rec['macro'] = MACRO_DIR
    rec['mutants'] = MUTANTS
    return text, ref_text(base), rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, ref, rec = build()
    if a.check:
        bad = [p for p, t in ((OUT, text), (REF, ref)) if (ROOT / p).read_text() != t]
        if bad:
            raise SystemExit(f'kv_grp_safe2 --check: stale {bad}')
        print('kv_grp_safe2 --check PASS')
        return
    (ROOT / OUT).write_text(text)
    (ROOT / REF).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / REF).write_text(ref)
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
