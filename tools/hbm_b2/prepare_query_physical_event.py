#!/usr/bin/env python3
"""Prepare disabled QUERY head5 carriers and private parent captures for regional HCOL565."""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/hbm_query_native_event_0135'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--inputs',type=Path,default=BASE/'full_proposed',help='14 already-head5 wrapper bodies; unrelated composed edits are preserved')
parser.add_argument('--selected',type=Path,default=BASE/'selected',help='matching pre-QUERY bodies for source-port identity; use the same composition input before QUERY projection')
parser.add_argument('--out',type=Path,default=BASE/'coherent_event')
args=parser.parse_args()
OUT=args.out
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def ports(s):
    header=s[:s.index(');')]
    out={}
    for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',header):
        out[m[4]]=dict(direction=m[1],width=(int(m[2])-int(m[3])+1)if m[2]else 1)
    assert out
    return out
abi=[];parent=[]
for reference in sorted((BASE/'full_proposed').glob('*.sv')):
    f=args.inputs/reference.name
    old=(args.selected/f.name).read_text();s=f.read_text();oldp,newp=ports(old),ports(s)
    assert oldp.keys()==newp.keys()
    changes=[]
    for n,q in newp.items():
        ow=oldp[n]['width'];nw=q['width']
        if ow==nw:continue
        assert ow-nw==3,(f.name,n,ow,nw)
        hi,lo=(37,35)if n.startswith('L14')else(7,5)if n.startswith('xi_gc_')else(519,517)
        changes.append(dict(port=n,direction=q['direction'],old_physical_bits=ow,new_physical_bits=nw,
                            removed_old_indices=[hi,lo],retained_lower_identity=[lo-1,0],
                            upper_old_to_new=dict(old=[ow-1,hi+1],new=[nw-1,lo]),
                            epoch=dict(old=ow-1,new=nw-1),xy_policy='retain surviving old sites by semantic bit; epoch keeps its old site; no automatic repack'))
    abi.append(dict(module=f.stem,old_sha256=sha(old),carrier_proposed_sha256=sha(s),
                    old_total_bits=sum(p['width']for p in oldp.values()),new_total_bits=sum(p['width']for p in newp.values()),
                    ports=newp,changed_ports=changes))
    if f.stem in ['hbm_arch_q_b102','hbm_arch_q_b102__physical_v1']:
        added=[]
        pattern=r'ot_hbm_idx_score_hcol_h([01]) #\((.*?)\) (\w+) \((.*?)\n    \);'
        def convert(m):
            h,params,inst,body=m.groups(); conns=dict(re.findall(r'\.(\w+)\(([^\n]+)\)',body))
            q=conns['q_b'];k=conns['key'];v=conns['qv_b']
            gc=re.search(r'w_gc_(\d+)_leaf_core_u_qlate_q',q)[1]
            assert q==f'w_gc_{gc}_leaf_core_u_qlate_q[567:0]'
            assert v==f'w_gc_{gc}_leaf_core_u_qlate_q[568]'
            km=re.fullmatch(r'w_gc_'+gc+r'_leaf_core_procdff_71524_Q\[(\d+):(\d+)\]',k);assert km
            qd=f'w_gc_{gc}_leaf_procdff_71558_Q[564:0]'
            kd=f'w_gc_{gc}_leaf_procdff_71561_Q[{km[1]}:{km[2]}]'
            vr=re.search(r'always @\(posedge clk\) g_gc_'+gc+r'_leaf_core_procdff_71522_q <= ([^;]+);',s);assert vr
            vd=vr[1];name='ownface_'+inst
            added.append(f'    (* keep *) reg [564:0] {name}_q0, {name}_q1;\n    (* keep *) reg [543:0] {name}_k0, {name}_k1;\n    (* keep *) reg {name}_v0, {name}_v1;\n    always @(posedge clk) begin\n        {name}_q0 <= {qd}; {name}_q1 <= {qd};\n        {name}_k0 <= {kd}; {name}_k1 <= {kd};\n        {name}_v0 <= {vd}; {name}_v1 <= {vd};\n    end\n')
            body=body.replace('.q_b('+q+')','.q_b({'+name+'_q1, '+name+'_q0})').replace('.key('+k+')','.key({'+name+'_k1, '+name+'_k0})').replace('.qv_b('+v+')','.qv_b({'+name+'_v1, '+name+'_v0})')
            parent.append(dict(parent=f.stem,instance=inst,new_master='ot_hbm_idx_score_hcol_regional_head5_h'+h,
                HALF=int(h),clock='clk',same_edge_source_D=dict(query=qd,key=kd,valid=vd),
                qualifiers='unconditional posedgeclk, no newreset/enable; exact old71519/71524/71522 D functions',
                added_declared_private_parent_FF=2220,shared_old_producers_retained=True,
                source_D_physical_reach='UNMEASURED: actual parent placement needed',clock_pose_budget='UNSELECTED'))
            return 'ot_hbm_idx_score_hcol_regional_head5_h'+h+' #('+params+') '+inst+' ('+body+'\n    );'
        s,n=re.subn(pattern,convert,s,flags=re.S);assert n==16,(f.name,n)
        s=s.replace('endmodule','\n// Additive private face captures at the existing producer edge; disabled full event.\n'+''.join(added)+'endmodule',1)
    (OUT/f.name).write_text(s)
# Real separate physical masters: HALF0 has no cs_in/cf_in public constant pins.
wrappers=[]
for h in [0,1]:
    ports0=['input wire [1:0] clk_pair','input wire rst_col','input wire [1:0] qv_b','input wire [1129:0] q_b','input wire [1087:0] key','input wire [31:0] hid4']
    if h:ports0+=['input wire [31:0] cs_in','input wire cf_in']
    ports0+=['output wire [31:0] cs_out','output wire cf_out','output wire [1:0] prdy']
    conns=['.clk_pair(clk_pair)','.rst_col(rst_col)','.qv_b(qv_b)','.q_b(q_b)','.key(key)','.hid4(hid4)',".cs_in("+('cs_in'if h else"32'd0")+')',".cf_in("+('cf_in'if h else"1'b0")+')','.cs_out(cs_out)','.cf_out(cf_out)','.prdy(prdy)']
    wrappers.append('module ot_hbm_idx_score_hcol_regional_head5_h'+str(h)+' #(parameter integer MUT=0,DELIVERED_RESET=1)(\n '+',\n '.join(ports0)+'\n);\n ot_hidx_score_hcol_regional_head5 #(.HALF('+str(h)+'),.MUT(MUT),.DELIVERED_RESET(DELIVERED_RESET)) u_native(\n '+',\n '.join(conns)+'\n );\nendmodule\n')
(OUT/'ot_hbm_idx_hcol_regional_head5_plan.sv').write_text('`default_nettype none\n'+''.join(wrappers)+'`default_nettype wire\n')
(OUT/'ot_hbm_idx_hcol_regional_head5.sv').write_bytes((BASE/'nested_hcol_head5/ot_hbm_idx_hcol_regional_head5.sv').read_bytes())
(OUT/'source_abi_pin_manifest.json').write_text(json.dumps(dict(status='DISABLED_EXACT_SOURCE_PORT_IDENTITY_PREP_NO_XY_BIND_RELEASE',rows=abi,logical_carriers_pruned=8,logical_data_bits_removed=24,physical_XY_join='HELD until actual parent pin plans regenerated; no planning alias',native_master_abi=dict(h0=2290,h1=2323)),indent=1)+'\n')
(OUT/'parent_D_frontier.json').write_text(json.dumps(dict(status='EXACT_SOURCE_D_AVAILABLE_PHYSICAL_REACH_UNMEASURED',rows=parent,
    per_b102_definition_private_parent_FF=35520,source_definitions=2,definition_total_FF=71040,
    old_shared_Q_removal_claimed=False,cycles_added=0,clock_contract_change=False,
    scope='QUERY-touched two b102 definitions only; not all current128HCOL instances/globaldelta',
    other_inputs='hid4/cs/cf/reset own-face/constant/locality joins remain separate, not assumed qualified',
    holds=['Fullparent sourceEQ and actualnative565masters EQ/faceguard NOTRUN','Actual parent D reach/ownFF placement/clockload and2323/2290pin capacity require model+LOOK','XO physical source-to-consumer join missing from prospective cohort','No default/current clockbudget/parentactivation']),indent=1)+'\n')
(OUT/'composition_inputs.json').write_text(json.dumps(dict(inputs=str(args.inputs),selected=str(args.selected),mode='EXPLICIT_SOURCE_BODY_COMPOSITION_PREP' if args.inputs != BASE/'full_proposed' or args.selected != BASE/'selected' else 'FROZEN_QUERY_SOURCE_PREP',source_proof_transfer=False,scope='only the14 QUERY wrappers are overlaid; caller retains all other native47/programme source files'),indent=1)+'\n')
print('ABI modules',len(abi),'privateparentcalls',len(parent),'newdeclaredparentFF',sum(x['added_declared_private_parent_FF']for x in parent))
