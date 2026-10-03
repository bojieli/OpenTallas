#!/usr/bin/env python3
"""Opt-in active-pair return-only RTL generator; no legacy source mutation."""
import argparse, hashlib, json
from pathlib import Path

def topology(np, regions):
    if not 1<=regions<=np: raise ValueError('1 <= regions <= active pairs')
    nodes=[]; roots=[]; spans=[]
    def tree(leaves, region):
        if len(leaves)==1:return leaves[0]
        mid=len(leaves)//2
        a=tree(leaves[:mid],region);b=tree(leaves[mid:],region)
        idx=2*np+len(nodes);nodes.append(dict(id=idx,a=a,b=b,region=region));return idx
    for r in range(regions):
        lo=r*np//regions;hi=(r+1)*np//regions
        roots.append(tree(list(range(2*lo,2*hi)),r));spans.append([lo,hi])
    assert len(nodes)==2*np-regions
    return dict(NP=np,R=regions,nodes=nodes,roots=roots,pair_spans=spans,padding_pairs=0,
                metadata_version='dsrom.active_pair_return.v1',
                leaf_index='2*compiled_pair_id+macro_side; pair regions contiguous; golden row must remain within one region')

def rtl(t,rd=4,rootd=128,rst=1):
    np=t['NP'];r=t['R'];n=2*np+len(t['nodes'])
    s=[f'''`timescale 1ns/1ps
// Opt-in generated return successor. SOURCE partials must obey lv/lready.
// Nonstallable ROM producers require the separately priced 8-row/pair buffer.
module ot_v41_return_credit_generated(
 input wire clk,rst_n, input wire [{2*np-1}:0] lv,le,
 input wire [{64*np-1}:0] lt,ld,
 output wire [{2*np-1}:0] lready,
 output wire [{r-1}:0] rv,re, output wire [{16*r-1}:0] rrow,rbf16,
 output wire [{3*r-1}:0] rpos, output wire [{32*r-1}:0] rfp32,
 output wire fault,quiet);
 wire [{n-1}:0] v,e,c,q; wire [31:0] tag[0:{n-1}],data[0:{n-1}];
 wire [{len(t['nodes'])+r-1}:0] faults;
''']
    for i in range(2*np):s.append(f'assign v[{i}]=lv[{i}]; assign e[{i}]=le[{i}]; assign tag[{i}]=lt[{32*i}+:32]; assign data[{i}]=ld[{32*i}+:32]; assign q[{i}]=!lv[{i}];')
    roots=set(t['roots'])
    for j,x in enumerate(t['nodes']):
        i,a,b=x['id'],x['a'],x['b']; depth=rootd if i in roots else rd
        s.append(f'''ot_v41_retn_credit #(.RD({rd}),.OUTD({depth}),.RST({rst})) n{j}(
 .clk(clk),.rst_n(rst_n),.a_v(v[{a}]),.a_t(tag[{a}]),.a_d(data[{a}]),.a_e(e[{a}]),
 .b_v(v[{b}]),.b_t(tag[{b}]),.b_d(data[{b}]),.b_e(e[{b}]),
 .a_ready({f'lready[{a}]' if a<2*np else ''}),.b_ready({f'lready[{b}]' if b<2*np else ''}),
 .a_credit(c[{a}]),.b_credit(c[{b}]),.o_credit(c[{i}]),
 .o_v(v[{i}]),.o_t(tag[{i}]),.o_d(data[{i}]),.o_e(e[{i}]),.fault(faults[{j}]),.quiet(q[{i}]),
 .peak_a(),.peak_b(),.credit_stalls());''')
    for j,i in enumerate(t['roots']):s.append(f'''wire rq{j};
 ot_v41_ret_credit_root #(.ROOTD({rootd})) root{j}(.clk(clk),.rst_n(rst_n),
 .i_v(v[{i}]),.i_t(tag[{i}]),.i_d(data[{i}]),.i_e(e[{i}]),.i_ready(),.i_credit(c[{i}]),
 .r_v(rv[{j}]),.r_e(re[{j}]),.r_row(rrow[{16*j}+:16]),.r_pos(rpos[{3*j}+:3]),
 .r_fp32(rfp32[{32*j}+:32]),.r_bf16(rbf16[{16*j}+:16]),.fault(faults[{len(t['nodes'])+j}]),
 .quiet(rq{j}),.peak_q(),.peak_held(),.blocked_cycles());''')
    s.append('assign fault=|faults; assign quiet=(&q) && '+ ' && '.join(f'rq{x}' for x in range(r))+';\nendmodule\n')
    return '\n'.join(s)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--active-pairs',type=int,required=True);p.add_argument('--regions',type=int,default=128)
    p.add_argument('--stage-id',type=int);p.add_argument('--rank-id',type=int);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);t=topology(a.active_pairs,a.regions);t.update(stage_id=a.stage_id,rank_id=a.rank_id,RD=4,ROOTD=128,RST=1)
    source=rtl(t);(a.out/'return.sv').write_text(source);t['rtl_sha256']=hashlib.sha256(source.encode()).hexdigest()
    t['qualification']='UNVALIDATED_RETURN_ONLY; actual element buffers/flow control, workload mapping and SS/FF are separate gates'
    (a.out/'topology.json').write_text(json.dumps(t,indent=2,sort_keys=True)+'\n')
