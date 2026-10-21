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


# Compose current controller, retaining PPATH, SO target/GW/GX, dynamic ST and real pv_x.
t=(D/'dsdv_svc_rs.sv').read_text();t=t[t.index('module dsdv_svc_rs_c #('):];t=t[:t.index('endmodule')+len('endmodule')]
t=t.replace('module dsdv_svc_rs_c #(','module dsdv_svc_rs_c_group72 #(').replace('parameter bit SMT = 1','parameter bit SMT = 1, parameter bit PMEM = 1').replace('input  wire              ck,','input wire ck, ck_sm, ck_att,')
t=t.replace('`include "dsdv_svc_rs_roles.svh"','`include "dsdv_svc_rs_roles_group72.svh"')
a=t.index('    dsdv_svc_att #'); b=t.index(';',a)+1
old=t[a:b]; new=old.replace('dsdv_svc_att #','dsdv_svc_attw_n1_f_lp #').replace('.MUT(MUT)', '.AMUT(MUT)').replace('.SRAM_MACRO(SRAM_MACRO)', '.SRAM_MACRO(SRAM_MACRO), .PMEM(PMEM), .ROOT(ENTRY), .TLX(6), .ROLE_EXT(1)')
new=new.replace('.clk(ck), .rst_n(rn), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(ENTRY),','.ck_c(ck), .ck_t0(ck_att), .rst(rst), .sid(sid), .role_i(role), .pvs_i(pvs),').replace('.q_v(cs[0]), .q_d(cs[512:1]), .hw_v(cs[513]), .hw_d(cs[DW-1:514]),','.cs(cs),')
t=t[:a]+new+t[b:]
a=t.index('    ot_s81_su_sms u_sms');b=t.index('    // ------------------------------------------------------------------ P path',a)
t=t[:a]+'''    wire sm_rn;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_sm_rst (.clk(ck_sm), .async_rst_n(rst), .sync_rst_n(sm_rn));
    wire [533:0] sm_ci, sm_co;
    wire [554:0] sm_ri, sm_ro;
    assign sm_ci = {tile, sm_st, sm_kind, sm_jid, r_v, r_p, r_j, r_d};
    dsdv_svc_face72 #(.W(534)) u_sm_cmd (.ck_w(ck), .ck_r(ck_sm), .rst_w(rn), .rst_r(sm_rn), .i(sm_ci), .o(sm_co));
    wire sw_v; wire [13:0] sw_a; wire [15:0] sw_m; wire [511:0] sw_d;
    wire sf_u, sf_o, sf_alive, sf_den; wire [7:0] sf_jid;
    ot_s81_su_sms u_sms (.clk(ck_sm), .rst_in(sm_rn), .cfg_g(sm_co[533:530]), .j_st(sm_co[529]), .j_kind(sm_co[528:525]), .j_jid(sm_co[524:517]),
        .r_v(sm_co[516]), .r_p(sm_co[515]), .r_j(sm_co[514:512]), .r_d(sm_co[511:0]),
        .w_v(sw_v), .w_a(sw_a), .w_m(sw_m), .w_d(sw_d), .o_fu(sf_u), .o_fo(sf_o), .o_alive(sf_alive), .o_den(sf_den), .o_rjid(sf_jid));
    assign sm_ri = {sw_v, sw_a, sw_m, sw_d, sf_jid, sf_den, sf_alive, sf_o, sf_u};
    dsdv_svc_face72 #(.W(555)) u_sm_ret (.ck_w(ck_sm), .ck_r(ck), .rst_w(sm_rn), .rst_r(rn), .i(sm_ri), .o(sm_ro));
    assign {w_v, w_a, w_m, w_d, o_rjid, o_den, o_alive, o_fo, o_fu} = sm_ro;
    assign w_st = {o_rjid, o_den, o_alive, o_fo, o_fu};

'''+t[b:]
(OUT/'dsdv_svc_rs_c_group72.sv').write_text('`timescale 1ns/1ps\n`default_nettype none\n'+t+'\n`default_nettype wire\n')

# Bit 0 of each gather/scatter lane is valid, exactly as p4l3_mu's
# sg/ss port split. The remaining families retain their existing bit order.
fields = [('dn',805), ('ud',13), ('uf',3), ('pv',514), ('g',2133), ('s',1077)]
W = sum(w for _,w in fields)
ports = [('input',48,'ck'), ('input',16,'rst'), ('input',64,'sid'),
         ('input',66,'j'), ('output',4,'jd'), ('input',1030,'q'), ('input',584,'hw'),
         ('output',18,'hc'), ('output',2,'fault'), ('output',4,'st_rg'),
         ('output',2,'pv_v'), ('output',1026,'pv_d'), ('output',96,'pv_x')]
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
    stem = 'dsdv_svc_rs_c_group72'
    L += [f'    wire [63:0] up_i_{i}, up_o_{i};']
    for f in range(4):
        L += [f'    assign up_i_{i}[{16*f}+:16] = {{uf_i_{i}[{3*f+1}+:2],ud_i_{i}[{13*f+12}],uf_i_{i}[{3*f}],ud_i_{i}[{13*f}+:12]}};',
              f'    assign {{uf_o_{i}[{3*f+1}+:2],ud_o_{i}[{13*f+12}],uf_o_{i}[{3*f}],ud_o_{i}[{13*f}+:12]}} = up_o_{i}[{16*f}+:16];']
    conns = [f'.ck(ck[{3*i}])',f'.ck_sm(ck[{3*i+1}])',f'.ck_att(ck[{3*i+2}])',
             f'.rst(rst_c[{i}])', f'.sid(sid[{4*i}+:4])']
    for p,a in [('dn_i','dn_i'),('dn_o','dn_o'),('up_i','up_i'),('up_o','up_o'),('ri','pv_i'),('ro','pv_o')]:
        conns.append(f'.{p}({a}_{i})')
    for p,a in [('gi_v','gv'),('gi_d','gd'),('go_v','gov'),('go_d','god'),
                ('si_v','sv'),('si_d','sd'),('so_v','sov'),('so_d','sod')]:
        conns.append(f'.{p}({a}_{i})')
    for p,w in [('rq',682),('rk',2),('wd',2),('rv',2),('r_data',512),('r_tag',34),('r_beat',8),('hs',2),
                ('w_v',1),('w_a',14),('w_m',16),('w_d',512),('w_st',12)]:
        conns.append(f'.{p}({p}[{i*w}+:{w}])')
    if entry:
        e = (i==11)
        for p,w in [('j',33),('jd',2),('q',515),('hw',292),('hc',9),('fault',1),('st_rg',2),('pv_v',1),('pv_d',513),('pv_x',48)]:
            conns.append(f'.{p}({p}[{int(e)*w}+:{w}])')
    else:
        conns += [".j(33'd0)", ".q(515'd0)", ".hw(292'd0)"] # ENTRY=0: existing semantic absent host endpoint
    L += [f'    {stem} #(.ENTRY({int(entry)}), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .PMEM(PMEM_MASK[{i}])) u_s{i} (',
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
record = dict(source='current PPATH/SMWIRE controller + isolated edd3f4a9e NT1 engine', placement='329d6c07a', grid=[2,8], roots=48,
              service_outline=[1728,3758.4], neighbor_gap_um=86.4,
              wide_faces=dict(gather_bits=2133,scatter_bits=1077),
              face_order=[dict(name=n,width=w) for n,w in fields], links=links, inactive_faces=inactive,
              sm_landing=dict(command_bits=534,return_bits=555,edges_each=3,roundtrip_edges=6), pv_x='actual dsdv_sm_gx from current SOT configuration and return-word producer', scope='source construction only; physical child binding/reset closure and calendar pricing of NT1 plus six SM landing edges remain obligations')
R = ROOT / 'results/arch/s81_service72_1021'; R.mkdir(parents=True,exist_ok=True)
(R/'hierarchy.json').write_text(json.dumps(record,indent=1)+'\n')
