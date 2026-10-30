"""Combine current exact registered-station ages with tested real V bodies."""
import json
from pathlib import Path
import sys

routes=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
rows={r['target']:r for r in routes['routes']}
legs={}
def age(target,source):
    r=rows[target]
    if (r['status']!='PASS_EXACT_RAW_BOUND_WORD' or r['source']!=source or
        r['source_is_glue']!=[False] or r['bits']!=276):
        raise ValueError('unqualified or stale current bound word '+target)
    legs[target]=r['age_edges'];return r['age_edges']
def delay(name,src,dst,n):
    if type(n)is not int or n<0:raise ValueError('missing exact station age')
    return (f'ot_hdc_delay #(.W(276),.D({n}),.RESET(1)) {name}'
            f'(.clk(ck),.rst_n(rst_n),.d({src}),.q({dst}));\n')
gni=age('u_gunit.u_l3.vi_s','u_s_3S.u_sl.u_xg.vo')
gno=age('u_s_3N.u_slice.u_xg.vi','u_gunit.u_l5.vo_n')
gsi=age('u_gunit.u_l5.vi_n','u_s_3N.u_slice.u_xg.vo')
gso=age('u_s_3S.u_sl.u_xg.vi','u_gunit.u_l3.vo_s')
chain=['l3','l1','l2','l0','l4','l5']
for south,north in zip(chain,chain[1:]):
    if age(f'u_gunit.u_{north}.rs_i',f'u_gunit.u_{south}.rn_o')!=0:
        raise ValueError('Gunit interleaf transport changed; retain explicit stations')
    if age(f'u_gunit.u_{south}.rn_i',f'u_gunit.u_{north}.rs_o')!=0:
        raise ValueError('Gunit reverse interleaf transport changed')
bni=age('u_bk_sel.vi_s','u_s_4S.u_lp.u_xg.vo')
bmidn=age('u_seqhost.u_seqhost.vi_s','u_bk_sel.vo_n')
bno=age('u_s_4N.u_lp.u_xg.vi','u_seqhost.u_seqhost.vo_n')
bsi=age('u_seqhost.u_seqhost.vi_n','u_s_4N.u_lp.u_xg.vo')
bmids=age('u_bk_sel.vi_n','u_seqhost.u_seqhost.vo_s')
bso=age('u_s_4S.u_lp.u_xg.vi','u_bk_sel.vo_s')
eni=age('u_eng.u_e.vi_s','u_s_6S.u_lp.u_xg.vo')
eno=age('u_s_6N.u_lp.u_xg.vi','u_eng.u_e.vo_n')
esi=age('u_eng.u_e.vi_n','u_s_6N.u_lp.u_xg.vo')
eso=age('u_s_6S.u_lp.u_xg.vi','u_eng.u_e.vo_s')
lat=[gni+12+gno,gsi+12+gso,bni+3+bmidn+2+bno,bsi+2+bmids+3+bso,eni+2+eno,esi+2+eso]
s='''`timescale 1ps/1fs
module native_bound_middle_fixture(input wire ck,rst_n,inject,own_v,
 input wire[275:0]va,vb, output wire[275:0]gno,gso,bno,bso,eno,eso,
 output wire[3:0]fault);
wire[275:0]gn[0:6],gs[0:6];
'''
s+=delay('gni','va','gn[0]',gni)+delay('gsi','vb','gs[6]',gsi)
s+='''for(genvar j=0;j<6;j=j+1)begin:g_leaf
 if(j==2)begin:g_l2
 ot_dsdv_vstop #(.V(276),.JREG(0)) u_vs(.clk(ck),.rst_n(rst_n),.tap_k(8'ha0),.sink_k(8'ha0),.bk_uid(8'd0),
 .vi_s(gn[j]),.vo_n(gn[j+1]),.vi_n(gs[j+1]),.vo_s(gs[j]),
 .in_nv(inject),.in_n(276'd3),.in_sv(inject),.in_s(276'd3),.fault(fault[0]),
 .dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
 end else begin:g_pass
 dsdv_gunit_pass #(.W(276),.N(2)) u_up(.clk(ck),.rst_n(rst_n),.d(gn[j]),.q(gn[j+1]));
 dsdv_gunit_pass #(.W(276),.N(2)) u_dn(.clk(ck),.rst_n(rst_n),.d(gs[j+1]),.q(gs[j]));
 end end
'''
s+=delay('gno_d','gn[6]','gno',gno)+delay('gso_d','gs[0]','gso',gso)
s+='wire[275:0]bni,bsi,brn,brs,bkn,bks,bs,bn,bmidn,bmids;\n'
s+=delay('bni_d','va','bni',bni)+delay('bsi_d','vb','bsi',bsi)
s+='''dsfd_dvrly_276_SN u_rs(.ck(ck),.rs(rst_n),.i(bni),.o(brn),.ck_o());
dsfd_dvrly_276_NS u_rn(.ck(ck),.rs(rst_n),.i(bmids),.o(brs),.ck_o());
ot_dsdv_vstop #(.V(276),.BK_DRAIN_SINK(1)) u_bk_vs(.clk(ck),.rst_n(rst_n),.tap_k(8'hff),.sink_k(8'hff),.bk_uid(8'd4),
 .vi_s(brn),.vo_n(bkn),.vi_n(brs),.vo_s(bks),.in_nv(1'b0),.in_n(276'd0),.in_sv(1'b0),.in_s(276'd0),
 .fault(fault[1]),.dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
dsdv_sh_vc u_sh(.ck(ck),.rst_n(rst_n),.tap_k(8'hff),.sink_k(8'hff),.vi_s(bmidn),.vo_n(bn),.vi_n(bsi),.vo_s(bs),
 .tw_i(194'd0),.cn_i(85'd0),.cs_i(85'd0),.cf_i(267'd0),.cg_i(85'd0),.dn_o(),.vf_o(fault[2]),.cw_v(),.cw_a(),.cw_d());
'''
s+=delay('bmidn_d','bkn','bmidn',bmidn)+delay('bmids_d','bs','bmids',bmids)
s+=delay('bno_d','bn','bno',bno)+delay('bso_d','bks','bso',bso)
s+='wire[275:0]evi_s,evi_n,evo_s,evo_n;\n'
s+=delay('eni_d','va','evi_s',eni)+delay('esi_d','vb','evi_n',esi)
s+='''ot_s81eng_xq_n32 u_xq(.ck(ck),.rst_n(rst_n),.o_v(own_v),.o_col(5'd0),.o_beat(3'd1),.o_d(264'd0),
 .vi_a(evi_s),.vo_a(evo_s),.vi_b(evi_n),.vo_b(evo_n),.fault(fault[3]));
'''
s+=delay('eno_d','evo_n','eno',eno)+delay('eso_d','evo_s','eso',eso)+'endmodule\n'
(out/'native_bound_middle_fixture.sv').write_text(s)
(out/'latency_params.svh').write_text('\n'.join(f'localparam integer L{i}={v};' for i,v in enumerate(lat))+'\n')
record={'scope':'CURRENT_REGISTERED_WIRE_AGES_PLUS_REAL_NATIVE_MIDDLE_V_CARVES',
 'source_asbuilt_sha256':routes['source_asbuilt_sha256'],
 'bound_top_sha256':routes['bound_top_sha256'],'bind_sinks_sha256':routes['bind_sinks_sha256'],
 'latency_edges':dict(zip(['gunit_n','gunit_s','bk_seqhost_n','bk_seqhost_s','eng_n','eng_s'],lat)),
 'wire_legs':legs,'wire_model':'Exact bound registered station ages represented by ot_hdc_delay; functional middle bodies remain real RTL',
 'conditional_scope':'Foreign XQ/XB trains, controller injections idle; own-injection collision guard tested separately',
 'full_bind_verification':'PENDING owned by S81 die lane','physical_START_qualified':False,'full_token':False}
(out/'composed_source.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record['latency_edges']))
