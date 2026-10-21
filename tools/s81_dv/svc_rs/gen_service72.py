#!/usr/bin/env python3
"""Compose the existing service LPs and adjacent 2x8 neighbor landings.

Source generation only. Use OT_SVC_GROUP72 and existing ATTN hard-group defines.
The 20 outer faces inherit the p4l3_mu role-unused termination contract.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / 'rtl/dsrom_sys/s81_dv/svc_rs'
OUT = D / 'group72'
OUT.mkdir(parents=True, exist_ok=True)


def local_parent(entry):
    stem = 'dsdv_svc_rs_entry_lp' if entry else 'dsdv_svc_rs_lp'
    text = (D / 'lp' / f'{stem}.sv').read_text()
    text = text.replace(f'module {stem} #(', f'module {stem}_group72 #(', 1)
    text = text.replace('    input wire ck_sm\n', '    input wire ck_sm,\n    input wire ck_att\n', 1)
    # The existing narrowed attention LP keeps the original outward protocol.
    text = text.replace('dsdv_svc_rs_attw #(.MUT(AMUT)',
                        'dsdv_svc_attw_n1_f_lp #(.AMUT(AMUT), .TLX(6)')
    lines = text.splitlines()
    for n, line in enumerate(lines):
        if 'dsdv_svc_attw_n1_f_lp #' in line:
            lines[n] = line.replace('.ck(ck_c)', '.ck_c(ck_c), .ck_t0(ck_att)')
    (OUT / f'{stem}_group72.sv').write_text('\n'.join(lines) + '\n')


local_parent(False)
local_parent(True)

# Bit 0 of each gather/scatter lane is valid, exactly as p4l3_mu's
# sg/ss port split. The remaining families retain their existing bit order.
fields = [('dn',805), ('ud',13), ('uf',3), ('pv',514), ('g',2133), ('s',1077)]
W = sum(w for _,w in fields)
ports = [('input',48,'ck'), ('input',16,'rst'), ('input',64,'sid'),
         ('input',66,'j'), ('output',4,'jd'), ('input',1030,'q'), ('input',584,'hw'),
         ('output',18,'hc'), ('output',2,'fault'), ('output',4,'st_rg'),
         ('output',2,'pv_v'), ('output',1026,'pv_d')]
for dr, w, name in [('output',682,'rq'),('input',2,'rk'),('input',2,'wd'),('input',2,'rv'),
                    ('input',512,'r_data'),('input',34,'r_tag'),('input',8,'r_beat'),('input',2,'hs'),
                    ('output',1,'w_v'),('output',14,'w_a'),('output',16,'w_m'),('output',512,'w_d'),('output',12,'w_st')]:
    ports.append((dr,16*w,name))
L = ['`timescale 1ns/1ps', '`default_nettype none',
     '// Generated hierarchy; 16 x (C,SM,ATT) roots, never one group CTS root.',
     'module dsdv_svc_group72 #(parameter integer DIE_ID=0, ST=0, SRAM_MACRO=1,',
     "    parameter [15:0] PMEM_MASK=16'hffff) ("]
L += [f'    {dr} wire [{w-1}:0] {name}' + (',' if k<len(ports)-1 else '')
      for k,(dr,w,name) in enumerate(ports)]
L += [');', '    wire [15:0] rst_c;']
for i in range(16):
    L += [f'    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_{i} (.clk(ck[{3*i}]), .async_rst_n(rst[{i}]), .sync_rst_n(rst_c[{i}]));']
    for name,w in fields:
        L += [f'    wire [{4*w-1}:0] {name}_i_{i}, {name}_o_{i};']
    L += [f'    wire [3:0] gv_{i}, sv_{i}, gov_{i}, sov_{i};',
          f'    wire [8527:0] gd_{i}, god_{i}; wire [4303:0] sd_{i}, sod_{i};']
    for f in range(4):
        L += [f'    assign g_o_{i}[{2133*f}+:2133] = {{god_{i}[{2132*f}+:2132],gov_{i}[{f}]}};',
              f'    assign {{gd_{i}[{2132*f}+:2132],gv_{i}[{f}]}} = g_i_{i}[{2133*f}+:2133];',
              f'    assign s_o_{i}[{1077*f}+:1077] = {{sod_{i}[{1076*f}+:1076],sov_{i}[{f}]}};',
              f'    assign {{sd_{i}[{1076*f}+:1076],sv_{i}[{f}]}} = s_i_{i}[{1077*f}+:1077];']
    entry = i in (5,11)
    stem = 'dsdv_svc_rs_entry_lp_group72' if entry else 'dsdv_svc_rs_lp_group72'
    conns = [f'.ck_c(ck[{3*i}])',f'.ck_sm(ck[{3*i+1}])',f'.ck_att(ck[{3*i+2}])',
             f'.rst(rst_c[{i}])', f'.sid(sid[{4*i}+:4])']
    for p,a in [('dn_i','dn_i'),('dn_o','dn_o'),('up_d_i','ud_i'),('up_d_o','ud_o'),('up_f_i','uf_i'),
                ('up_f_o','uf_o'),('ri','pv_i'),('ro','pv_o')]:
        conns.append(f'.{p}({a}_{i})')
    for p,a in [('gi_v','gv'),('gi_d','gd'),('go_v','gov'),('go_d','god'),
                ('si_v','sv'),('si_d','sd'),('so_v','sov'),('so_d','sod')]:
        conns.append(f'.{p}({a}_{i})')
    for p,w in [('rq',682),('rk',2),('wd',2),('rv',2),('r_data',512),('r_tag',34),('r_beat',8),('hs',2),
                ('w_v',1),('w_a',14),('w_m',16),('w_d',512),('w_st',12)]:
        conns.append(f'.{p}({p}[{i*w}+:{w}])')
    if entry:
        e = (i==11)
        for p,w in [('j',33),('jd',2),('q',515),('hw',292),('hc',9),('fault',1),('st_rg',2),('pv_v',1),('pv_d',513)]:
            conns.append(f'.{p}({p}[{int(e)*w}+:{w}])')
    L += [f'    {stem} #(.DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .PMEM(PMEM_MASK[{i}])) u_s{i} (',
          '        ' + ', '.join(conns) + ');']

links, inactive = [], []
for i in range(16):
    row,col = i%2,i//2
    for face,(dr,dc) in enumerate(((1,0),(0,1),(-1,0),(0,-1))):
        r,c = row+dr,col+dc
        if 0<=r<2 and 0<=c<8:
            j = 2*c+r
            op = (face+2)%4
            tx = '{' + ','.join(f'{name}_o_{i}[{face*w}+:{w}]' for name,w in reversed(fields)) + '}'
            rx = '{' + ','.join(f'{name}_i_{j}[{op*w}+:{w}]' for name,w in reversed(fields)) + '}'
            L += [f'    dsdv_svc_face72 u_link_{i}_{j} (.ck_w(ck[{3*i}]), .ck_r(ck[{3*j}]),',
                  f'        .rst_w(rst_c[{i}]), .rst_r(rst_c[{j}]), .i({tx}), .o({rx}));']
            links.append(dict(source=i,destination=j,face=face,width=W,banks=(W+275)//276,added_edges=3))
        else:
            # Existing role-unused input contract, not a substitute for an active link.
            for name,w in fields:
                L += [f"    assign {name}_i_{i}[{face*w}+:{w}] = {w}'d0; // inherited semantic inactive outer face"]
            inactive.append(dict(sid=i,face=face,contract='p4l3_mu mode_unused: unlinked_bits; outputs spare_out_rules'))
L += ['endmodule', '`default_nettype wire']
(OUT / 'dsdv_svc_group72.sv').write_text('\n'.join(L)+'\n')
record = dict(source='edd3f4a9e', placement='329d6c07a', grid=[2,8], roots=48,
              service_outline=[1728,3758.4], neighbor_gap_um=86.4,
              wide_faces=dict(gather_bits=2133,scatter_bits=1077),
              face_order=[dict(name=n,width=w) for n,w in fields], links=links, inactive_faces=inactive,
              scope='source construction only; existing LP resets/child views and current service static program remain obligations')
R = ROOT / 'results/arch/s81_service72_1021'; R.mkdir(parents=True,exist_ok=True)
(R/'hierarchy.json').write_text(json.dumps(record,indent=1)+'\n')
