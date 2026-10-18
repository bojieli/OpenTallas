#!/usr/bin/env python3
"""H-NETLIST 2200 (H-DIE d4f request): HOIST the VM banks of hb_vms_SW / hb_vms_NW to die-level instances.

The d4f plan places 8 bank blocks vmb_<Q>0..7 around each hub column (vmh_<Q> = hub glue).  The die GEN places only
top-level contract instances, so the banks must be die instances.  This tool writes:
  * rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static_glue.sv (generated, do not edit):
      ot_vms_slice_static_glue       = ot_vms_slice_static with the g_bank generate (8 x ot_vms_bank_native_physical)
                                       REMOVED; the hub / ring stops / replay / status logic is the slice text
                                       unchanged.  The bank-side nets become ports: bk_xq/bk_xq2 (ring -> bank),
                                       bk_xq_done/bk_xq2_done, bk_eg (bank -> rings), bk_pq/bk_pr (hub <-> bank),
                                       bank_status (bank -> status, now an input).  The per-bank request ports of the
                                       slice (clk_bank, rslot*, wslot*, rq/rr, wq/wq_done, dq/kq, *_done) are gone:
                                       they are pure wires to the banks in the slice, so on the die they connect the
                                       clients straight to the bank instances.
      hfd_hgi_vms_static_SW_glue / _NW_glue = the quadrant wrappers over the glue slice (NW: input bk_flt[7:0], the
                                       wq2-merge leaves' sticky flags ORed into bank status bit 17, exactly as the
                                       ot_vms_bank_native_physical q2m adapter does).
  * tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json: full_die_v16 layer: remaster hb_vms_<Q> -> the glue wrapper with
    port_split re-targeting every old per-bank port bit to its bank / merge instance (cross-instance), bank instances
    vmb_<Q>b (hfd_vms_bank_native_q0, bid/sid identity straps), NW merge leaves vmm_NWb (hfd_vms_wq2_merge), the
    internal glue <-> bank <-> merge edges, bank / merge clocks (the old clk_bank[b] domain) and resets.
The composition glue + banks + merges is the same netlist as the STRAP_BANKS=1 (Q2_MERGE=1) wrapper, bit for bit
(the bench tools/hbm_die_v16/vms_hoist_equiv: lockstep of both forms).
SE/NE (_core, client slots absent) are NOT hoisted: their q1 banks would expose the absent client ports unconnected.
    gen_vms_hoist.py [--check]
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
OUT = D / 'hfd_hgi_vms_static_glue.sv'
LAYER = ROOT / 'tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json'
SRC = 'rtl/hbm_accel/generic/vm/static/'
Q = dict(SW=dict(sid=0, RG=5, WG=2, merge=False), NW=dict(sid=2, RG=5, WG=3, merge=True),
         # core-only hubs (hfd_hgi_vms_static_{SE,NE}_core, H-NETLIST 1940): hub rq/rr groups = old slice groups (0, 3),
         # wq group 0 only, no dq; banks = hfd_vms_bank_native_q1_core (q1 with the SM-side client ports absent)
         SE=dict(sid=1, RG=4, WG=2, merge=False, core=dict(rg=(0, 3), wg=(0,))),
         NE=dict(sid=3, RG=4, WG=2, merge=False, core=dict(rg=(0, 3), wg=(0,))))
REMOVED = ('clk_bank', 'rslot_v', 'wslot_v', 'rslot', 'wslot', 'rq', 'rr', 'wq', 'wq_done', 'dq', 'kq', 'dq_done', 'kq_done')


def sub(s, a, b, n=1):
    c = s.count(a)
    if c != n:
        raise SystemExit(f'gen_vms_hoist: expected {n} x {a[:80]!r}, found {c}')
    return s.replace(a, b)


def slice_glue(t):
    s = t[t.index('module ot_vms_slice_static #('):t.index('endmodule') + len('endmodule')]
    s = sub(s, 'module ot_vms_slice_static #(', 'module ot_vms_slice_static_glue #(')
    s = sub(s, "    parameter integer BMUT=0,RMUT=0,\n", "    parameter integer RMUT=0,\n")
    s = sub(s, "    parameter integer STRAP_QUADRANT=-1, // opt-in physical masters; -1 retains historical bank\n", "")
    s = sub(s, "    parameter integer Q2_MERGE=0, // NW (q2) bank = q0 master + hfd_vms_wq2_merge (ot_vms_bank_native_physical)\n", "")
    s = sub(s, "    parameter integer BANK_PIN_IN=0 // literal bank input pin flops (ot_vms_bank_native_physical PIN_IN); ring commit 5 + this\n",
            "    parameter integer BANK_PIN_IN=0 // the die-level banks carry literal input pin flops: ring-stop COMMIT_DELAY 5 + this\n")
    for line in ('    input wire [7:0] clk_bank,\n', '    input wire [7:0] rslot_v,wslot_v,\n', '    input wire [8*RB-1:0] rslot,\n',
                 '    input wire [8*WB-1:0] wslot,\n', '    input wire [RG*8*17-1:0] rq,\n', '    output wire [RG*8*257-1:0] rr,\n',
                 '    input wire [WG*8*281-1:0] wq,\n', '    output wire [WG*8-1:0] wq_done,\n', '    input wire [8*281-1:0] dq,kq,\n',
                 '    output wire [7:0] dq_done,kq_done,\n'):
        s = sub(s, line, '')
    s = sub(s, '    output wire [143:0] bank_status,\n',
            '    input wire [143:0] bank_status,          // from the 8 die-level bank instances (status -> vmstat)\n'
            '    output wire [2207:0] bk_xq,bk_xq2,       // ring stop cw / ccw -> bank b at [b*276+:276]\n'
            '    input wire [7:0] bk_xq_done,bk_xq2_done,\n'
            '    input wire [2207:0] bk_eg,               // bank b egress -> both ring stops\n'
            '    output wire [8*285-1:0] bk_pq,           // hub -> bank b\n'
            '    input wire [8*266-1:0] bk_pr,            // bank b -> hub\n')
    a = s.index('    genvar b,g;\n'); b = s.index('    end endgenerate\n', s.index('generate for(b=0;b<8;b=b+1)begin:g_bank'))
    s = s[:a] + ('    // H-NETLIST 2200: the 8 banks are die-level instances (vmb_<Q>b); their nets are the bk_* ports\n'
                 '    assign bk_xq=xq0; assign bk_xq2=xq1; assign xd0=bk_xq_done; assign xd1=bk_xq2_done;\n'
                 '    assign eg=bk_eg; assign bk_pq=pq; assign pr=bk_pr;\n') + s[b + len('    end endgenerate\n'):]
    if 'u_bank' in s or 'ot_vms_bank_' in s:
        raise SystemExit('gen_vms_hoist: bank instance left in the glue slice')
    return s + '\n'


def wrapper_glue(t, q, cfg):
    s = re.search(rf'module hfd_hgi_vms_static_{q} #.*?\nendmodule\n', t, re.S).group(0)
    s = sub(s, f'module hfd_hgi_vms_static_{q} #', f'module hfd_hgi_vms_static_{q}_glue #')
    for p in REMOVED:
        s, n = re.subn(rf'\n    (input|output) wire (\[[^\]]+\] )?{p},', '', s)
        if n != 1:
            raise SystemExit(f'gen_vms_hoist: wrapper {q} port {p}: {n}')
        s = sub(s, f'        .{p}({p}),\n', '')
    s = sub(s, '    output wire [143:0] bank_status,\n',
            '    input wire [143:0] bank_status,\n    output wire [2207:0] bk_xq,bk_xq2,\n    input wire [7:0] bk_xq_done,bk_xq2_done,\n'
            '    input wire [2207:0] bk_eg,\n    output wire [2279:0] bk_pq,\n    input wire [2127:0] bk_pr,\n'
            + ('    input wire [7:0] bk_flt,                 // wq2-merge leaves vmm_NWb sticky flt -> bank status bit 17\n' if cfg['merge'] else ''))
    s = re.sub(r'ot_vms_slice_static #\(.*?\) u_slice \(', f'ot_vms_slice_static_glue #(.NC({2 if q == "SW" else 0}),.RG({cfg["RG"]}),.WG({cfg["WG"]}),.NATIVE_SHAPE(1),.BANK_PIN_IN(1)) u_slice (', s)
    st = 'bank_status'
    if cfg['merge']:
        s = sub(s, '    ot_vms_slice_static_glue #', '    wire [143:0] bank_status_m;\n    genvar fb;\n'
                '    generate for(fb=0;fb<8;fb=fb+1)begin:g_flt\n'
                '        assign bank_status_m[fb*18+:18]={bank_status[fb*18+17]|bk_flt[fb],bank_status[fb*18+:17]};\n'
                '    end endgenerate\n    ot_vms_slice_static_glue #')
        st = 'bank_status_m'
    s = sub(s, '        .bank_status(bank_status),\n',
            f'        .bank_status({st}),\n        .bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),\n'
            '        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),\n')
    s = re.sub(r'#\(parameter integer STRAP_BANKS=0, STRAP_MUT=0(, Q2_MERGE=0)?(, BANK_PIN_IN=0)?\)', '', s)
    return s


def layer():
    inst, edges, clocks, straps, rem = [], [], [], [], {}
    def E(src, dst, bits):
        edges.append(dict(src=src, dst=dst, bits=bits, clock='stream', basis='gen_vms_hoist (slice g_bank wiring)'))
    for q, cfg in Q.items():
        hub = f'hb_vms_{q}'; RG, WG = cfg['RG'], cfg['WG']; RB, WB = 3, 3
        ps = {}
        for b in range(8):
            vb = f'vmb_{q}{b}'
            # banks carry LITERAL input pin flops in RTL (= their views; H-SM 05978a837): hub glue BANK_PIN_IN=1
            if cfg.get('core'):
                inst.append(dict(name=vb, master='hfd_vms_bank_native_q1_core_pr', source=SRC + 'physical/hfd_vms_bank_native_q1_core_pr.sv',
                                 rtl_deps=[SRC + 'physical/hfd_vms_bank_native_q1_core.sv', SRC + 'physical/hfd_vms_bank_native_q1.sv'],
                                 params={}, slot=vb, owner='H-SM/H-DIE',
                                 note=f'{hub} bank {b} hoisted (q1 core-only, literal input pin flops; view vm_native_q1core_pr4)'))
                bclk = ['clk']
            else:
                inst.append(dict(name=vb, master='hfd_vms_bank_native_q0_faces', source=SRC + 'faces_q0/hfd_vms_bank_native_q0_faces.sv',
                                 rtl_deps=[SRC + 'faces_q0/ot_vms_bank_q0_faces_core.sv', SRC + 'faces_q0/ot_vms_bank_q0_faces_body.sv'],
                                 params={}, slot=vb, owner='H-SM/H-DIE', note=f'{hub} bank {b} hoisted (q0C faces master, literal input pin flops)'))
                bclk = ['clk', 'clk_n', 'clk_s', 'clk_e', 'clk_w', 'clk_macro0', 'clk_macro1', 'clk_macro2']
            clocks += [dict(inst=vb, port=c_, domain='stream', kind='clock') for c_ in bclk]
            clocks += [dict(inst=vb, port='rst_n', domain='stream', kind='reset')]
            straps += [dict(inst=vb, port='bid', value=b, reason=f'identity: bank id {b} of {hub} (slice .bid(3\'(b)))'),
                       dict(inst=vb, port='sid', value=cfg['sid'], reason=f'identity: slice id of {hub}')]
            for p, w in (('xq', 276), ('xq2', 276)):
                E([hub, 'bk_' + p, b * w, b * w + w], [vb, p], w)
                E([vb, p + '_done'], [hub, f'bk_{p}_done', b, b + 1], 1)
            E([vb, 'eg'], [hub, 'bk_eg', b * 276, b * 276 + 276], 276)
            E([hub, 'bk_pq', b * 285, b * 285 + 285], [vb, 'pq'], 285)
            E([vb, 'pr'], [hub, 'bk_pr', b * 266, b * 266 + 266], 266)
            E([vb, 'status'], [hub, 'bank_status', b * 18, b * 18 + 18], 18)
            if cfg['merge']:
                vm = f'vmm_{q}{b}'
                inst.append(dict(name=vm, master='hfd_vms_wq2_merge', source=SRC + 'wq_merge/hfd_vms_wq2_merge.sv', params={},
                                 slot=vm, owner='H-SM', note=f'{hub} bank {b} write merge (wq1 SM writer | wq2 quantiser -> bank wq1)'))
                clocks += [dict(inst=vm, port='clk', domain='stream', kind='clock'), dict(inst=vm, port='rst_n', domain='stream', kind='reset')]
                E([vm, 'wq_m'], [vb, 'wq1'], 281); E([vb, 'wq_done1'], [vm, 'done_m'], 1)
                E([vm, 'flt'], [hub, 'bk_flt', b, b + 1], 1)
        # old per-bank hub ports -> bank / merge instance ports (port_split, cross-instance)
        ps['clk_bank'] = [[f'vmb_{q}{b}', 'clk', b, b + 1] for b in range(8)]
        ps['rslot_v'] = [[f'vmb_{q}{b}', 'rslot_v', b, b + 1] for b in range(8)]
        ps['wslot_v'] = [[f'vmb_{q}{b}', 'wslot_v', b, b + 1] for b in range(8)]
        ps['rslot'] = [[f'vmb_{q}{b}', 'rslot', b * RB, b * RB + RB] for b in range(8)]
        ps['wslot'] = [[f'vmb_{q}{b}', 'wslot', b * WB, b * WB + WB] for b in range(8)]
        rgs = cfg['core']['rg'] if cfg.get('core') else tuple(range(RG))   # kept slice groups (the edges still carry the
        # full-wrapper bit positions: the remaster runs before any A2P slot remap)
        ps['rq'] = [[f'vmb_{q}{b}', f'rq{g}', (g * 8 + b) * 17, (g * 8 + b) * 17 + 17] for k, g in enumerate(rgs) for b in range(8)]
        ps['rr'] = [[f'vmb_{q}{b}', f'rr{g}', (g * 8 + b) * 257, (g * 8 + b) * 257 + 257] for k, g in enumerate(rgs) for b in range(8)]
        wqt = (lambda g, b: (f'vmb_{q}{b}', f'wq{g}')) if not cfg['merge'] else \
              (lambda g, b: (f'vmb_{q}{b}', 'wq0') if g == 0 else (f'vmm_{q}{b}', f'wq{g}'))
        wdt = (lambda g, b: (f'vmb_{q}{b}', f'wq_done{g}')) if not cfg['merge'] else \
              (lambda g, b: (f'vmb_{q}{b}', 'wq_done0') if g == 0 else (f'vmm_{q}{b}', f'wq_done{g}'))
        wgs = cfg['core']['wg'] if cfg.get('core') else tuple(range(WG))
        ps['wq'] = [[*wqt(g, b), (g * 8 + b) * 281, (g * 8 + b) * 281 + 281] for k, g in enumerate(wgs) for b in range(8)]
        ps['wq_done'] = [[*wdt(g, b), g * 8 + b, g * 8 + b + 1] for k, g in enumerate(wgs) for b in range(8)]
        for p in (('kq',) if cfg.get('core') else ('dq', 'kq')):
            ps[p] = [[f'vmb_{q}{b}', p, b * 281, b * 281 + 281] for b in range(8)]
        for p in (('kq_done',) if cfg.get('core') else ('dq_done', 'kq_done')):
            ps[p] = [[f'vmb_{q}{b}', p, b, b + 1] for b in range(8)]
        rem[hub] = dict(master=f'hfd_hgi_vms_static_{q}_glue', source=SRC + 'hfd_hgi_vms_static_glue.sv', params={},
                        rtl_deps=[SRC + x for x in ('ot_vms_hub_static.sv', 'ot_vms_rstop_static.sv', 'ot_vms_rcl_static.sv', 'ot_vms_status_static.sv')],
                        port_split=ps)
    return dict(region='vm_hoist_d4f', author='Claude H-NETLIST 2200', basis_commit='H-DIE d4f vmb_<Q>b plan blocks',
                instances=inst, edges=edges, clocks=clocks, straps=straps, gaps=[], remaster=rem,
                drop_clocks=[[f'hb_vms_{q}', 'clk_bank'] for q in Q], notes=__doc__.split('\n\n')[0])


def main():
    t = (D / 'ot_vms_slice_static.sv').read_text(); w = (D / 'hfd_hgi_vms_static.sv').read_text()
    rtl = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_hoist.py (do not edit): VM hub glue with the 8 banks hoisted to\n'
           '// die-level instances (vmb_<Q>b; NW write merges vmm_NWb).  See the tool docstring.\n'
           + slice_glue(t) + ''.join(wrapper_glue(w, q, c) for q, c in Q.items()) + '`default_nettype wire\n')
    lay = json.dumps(layer(), indent=1) + '\n'
    if '--check' in sys.argv:
        ok = OUT.read_text() == rtl and LAYER.read_text() == lay
        print('VMS_HOIST_GEN', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(rtl); LAYER.write_text(lay); print('VMS_HOIST_GEN WROTE', OUT.relative_to(ROOT), LAYER.relative_to(ROOT))


if __name__ == '__main__':
    main()
