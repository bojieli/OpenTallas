#!/usr/bin/env python3
"""Exact inactive-subtree pruning of retained RD64 return. No credit or READY.

Retains every node with ANY active descendant, including unilateral paths.
Deleting unilateral nodes is a separate timing/fault change, not dead pruning.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/v41rom/ot_v41_ret.sv','rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41die/ot_v41_field_w17w10.sv','tools/dsrom_return_storage_hbm.py']

def derive(pairs=2417,regions=128,seats=32,region_bounds=None):
    if pairs<regions or seats<1 or seats&(seats-1) or regions&(regions-1):raise ValueError('geometry')
    bounds=region_bounds or [r*pairs//regions for r in range(regions+1)]
    if len(bounds)!=regions+1 or bounds[0]!=0 or bounds[-1]!=pairs or any(not 0<b-a<=seats for a,b in zip(bounds,bounds[1:])):raise ValueError('source region ownership')
    leaves=[];old_to_leaf={}
    for r,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
        for p in range(lo,hi):
            oldseat=r*seats+p-lo
            for side in (0,1):
                leaf=2*p+side;old=2*oldseat+side
                leaves.append(dict(id=leaf,pair=p,side=side,region=r,old_leaf=old,old_return_pair=oldseat,source_pair_instance=f'g_p[{p}].u_p',leaf_bus_index=leaf))
                old_to_leaf[old]=leaf
    nl=2*regions*seats; levels=int(math.log2(2*seats));nodes=[];removed=[];children={i:old_to_leaf.get(i) for i in range(nl)}
    roots=[]
    for l in range(levels):
        next_children={}
        for g in range(nl>>(l+1)):
            a,b=children[2*g],children[2*g+1];old_id=nl-(nl>>l)+g
            x=dict(old_id=old_id,source_level=l,source_index=g,source_instance=f'g_lv[{l}].g_n[{g}].u_n',generated_instance=f'n{len(nodes)}',region=g//(2*seats>>(l+1)))
            if a is None and b is None:
                removed.append(x);next_children[g]=None
            else:
                i=2*pairs+len(nodes);x.update(id=i,a=a,b=b,unilateral=(a is None or b is None))
                nodes.append(x);next_children[g]=i
        children=next_children
    for r in range(regions):
        assert children[r] is not None
        roots.append(dict(region=r,input=children[r],source_instance=f'g_r[{r}].u_root',VM_port=r,generated_instance=f'root{r}',removed=False))
    return dict(schema='dsrom.s81.rd64.exact_inactive_prune.v1',pairs=pairs,regions=regions,region_bounds=bounds,
      reference_return_pair_seats=regions*seats,reference_levels=levels,
      active_leaves=leaves,nodes=nodes,removed_nodes=removed,roots=roots,
      removed_leaf_valid_inputs=sorted(set(range(nl))-set(old_to_leaf)),
      retained_unilateral_nodes=[n['id'] for n in nodes if n['unilateral']],
      RD=64,ROOTD=128,QD=128,RST=1,BYPASS=1,WAIT=2,
      no_READY=True,pair_identity='id=2*physical_pair+macro_side',
      tag_identity='{position3,row16,lo5,k3,nseg5}; unchanged legacy norm/sibling/parent',
      pruning_rule='remove ONLY nodes with no active descendants; retain unilateral active FIFO/delay/WAIT/fault paths',
      selected_compact_W1_node_count=2*pairs-regions,
      compact_W1_is_not_exact_dead_pruning=True)


def ledger(t):
    bits_node=2*t['RD']*65+t['RST']*66
    bits_root=t['ROOTD']*(65+66)
    removed=len(t['removed_nodes']);kept=len(t['nodes']);r=t['regions']
    # Reservation basis pinned in Scenario C; not a synthesis measurement.
    area_per_bit=.37908/.5/1e6
    return dict(label='SOURCE_DECLARATION_COUNTS_AND_MODEL_RESERVATION_NOT_SYNTHESIS',
      reference_nodes=removed+kept,retained_nodes=kept,removed_dead_nodes=removed,retained_unilateral_nodes=len(t['retained_unilateral_nodes']),
      retained_roots=r,removed_roots=0,removed_root_storage_bits=0,removed_empty_side_storage_credit_bits=0,
      node_credited_storage_bits=bits_node,root_storage_bits=bits_root,
      exact_removed_declared_storage_bits=removed*bits_node,
      original_storage_bits=(removed+kept)*bits_node+r*bits_root,
      retained_storage_bits=kept*bits_node+r*bits_root,
      exact_removed_FF50_reservation_mm2=removed*bits_node*area_per_bit,
      retained_FF50_reservation_mm2=(kept*bits_node+r*bits_root)*area_per_bit,
      selected_compact_model_storage_bits=t['selected_compact_W1_node_count']*bits_node+r*bits_root,
      compact_additional_debit_not_removed_by_dead_pruning_mm2=(kept-t['selected_compact_W1_node_count'])*bits_node*area_per_bit,
      area_exclusions='adder/control/alignment registers, muxes, CTS/PDN/route; no extra credit for these',
      latency_change_dead_prune_cycles=0,
      latency_condition='same pre-edge inputs and reset on retained legacy nodes; no unilateral contraction or remapping',
      new_MACs_per_cycle=0,node_ports_bytes_per_cycle={'two_write':130/8,'two_read':130/8},
      root_public_bits_per_cycle=r*69,node_boundary_signal_tracks=130+65,
      channel_fit=None,physical_SS_FF=None,whole_token_qualified=False)

def emit(t,module='ot_v41_return_rd64_pruned'):
    p=t['pairs'];r=t['regions'];nl=2*p;last=nl+len(t['nodes'])
    out=[f'''`timescale 1ns/1ps
// Generated legacy RD64 connectivity; strict inactive-subtree pruning, including all active unilateral stages.
// NO READY: every leaf-valid and root-valid is an uninterruptible pulse.
module {module}(input wire clk,rst_n,
 input wire [{nl-1}:0] lv,le, input wire [{nl*32-1}:0] lt,ld,
 output wire [{r-1}:0] rv,re, output wire [{r*16-1}:0] rrow,rbf16,
 output wire [{r*3-1}:0] rpos, output wire [{r*32-1}:0] rfp32,
 output wire fault);
 wire [{last-1}:0] v,e; wire [31:0] tag[0:{last-1}],data[0:{last-1}];
 wire [{len(t['nodes'])+r-1}:0] faults;
''']
    for i in range(nl):out.append(f'assign v[{i}]=lv[{i}];assign e[{i}]=le[{i}];assign tag[{i}]=lt[{32*i}+:32];assign data[{i}]=ld[{32*i}+:32];')
    def sig(i,name):return ('1\'b0' if name in ('v','e') else "32'd0") if i is None else f'{name}[{i}]'
    for j,n in enumerate(t['nodes']):
        i=n['id'];a=n['a'];b=n['b']
        out.append(f'''// Retained source {n['source_instance']} old_fault_index={n['old_id']}
 ot_v41_retn_w17w10 #(.RD(64),.RST(1),.BYPASS(1)) n{j}(.clk(clk),.rst_n(rst_n),
 .a_v({sig(a,'v')}),.a_t({sig(a,'tag')}),.a_d({sig(a,'data')}),.a_e({sig(a,'e')}),
 .b_v({sig(b,'v')}),.b_t({sig(b,'tag')}),.b_d({sig(b,'data')}),.b_e({sig(b,'e')}),
 .o_v(v[{i}]),.o_t(tag[{i}]),.o_d(data[{i}]),.o_e(e[{i}]),.fault(faults[{j}]),.quiet());''')
    for x in t['roots']:
        j=x['region'];i=x['input']
        out.append(f'''ot_v41_ret_root #(.D(128),.QD(128)) root{j}(.clk(clk),.rst_n(rst_n),
 .i_v(v[{i}]),.i_t(tag[{i}]),.i_d(data[{i}]),.i_e(e[{i}]),
 .r_v(rv[{j}]),.r_row(rrow[{16*j}+:16]),.r_pos(rpos[{3*j}+:3]),
 .r_fp32(rfp32[{32*j}+:32]),.r_bf16(rbf16[{16*j}+:16]),.r_e(re[{j}]),.fault(faults[{len(t['nodes'])+j}]));''')
    out.append('assign fault=|faults;\nendmodule\n')
    return '\n'.join(out)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage-map',type=Path);ap.add_argument('--inventory',type=Path);ap.add_argument('--matrix-map',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    bound=[];m=None
    if bool(a.stage_map)!=bool(a.inventory):raise ValueError('both inventory and stage-map required')
    if a.inventory:
        inv=json.loads(a.inventory.read_text());m=json.loads(a.stage_map.read_text())
        if inv['stages']!=81 or inv['pairs_per_rank_die']!=2417 or inv['BF_dual_pairs']!=519:raise ValueError('not selected S81')
        if len(m['BF_site_IDs'])!=519 or len(set(m['BF_site_IDs']))!=519 or any(not 0<=b<2417 for b in m['BF_site_IDs']):raise ValueError('BF inventory')
        t=derive(region_bounds=m['region_bounds']);bound=[a.inventory,a.stage_map]
    else:t=derive()
    if a.matrix_map:
        if not bound:raise ValueError('matrix-map requires inventory and stage-map')
        bound.append(a.matrix_map)
    t['inventory_bound']=bool(bound)
    t['BF_site_IDs']=m['BF_site_IDs'] if m else None
    t['rank_dies']=m.get('rank_dies') if m else None
    t['inventory_binding_scope']='exact geometry/BF ownership and file hashes; no payload/arithmetic/phase admission qualification'
    t['integration_hooks']={'leaf': 'lv/le/lt/ld[2*physical_pair+macro_side]; preserve actual pair fault separately',
        'node': 'nodes[].id,a,b,source_instance,generated_instance; None child is valid=0',
        'root': 'roots[].region,input,VM_port; outputs retain original root index',
        'fault': 'wrapper ORs every retained node/root fault; enclosing field must OR every actual pair fault',
        'admission_owner': 'Nash; before GO; unchanged NOREADY outputs'}
    # Price source-sized connectivity BEFORE emitting RTL.
    model=ledger(t);model['inventory_bound']=bool(bound);model['canonical_matrix_map_pinned']=bool(a.matrix_map);a.out.mkdir(parents=True,exist_ok=False)
    pins={'tools/dsrom_s81_rd64_connectivity.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    pins.update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    pins.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in bound})
    model['source_sha256']=pins
    (a.out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    (a.out/'connectivity.json').write_text(json.dumps(t,indent=2,sort_keys=True)+'\n')
    (a.out/'return.sv').write_text(emit(t))
    print(json.dumps(model,indent=2,sort_keys=True))
if __name__=='__main__':main()
