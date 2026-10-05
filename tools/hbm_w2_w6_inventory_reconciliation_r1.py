#!/usr/bin/env python3
"""Bounded metadata reconciliation of selected NC6/W6 source state and costs.

No imported provider constructors, model execution, RTL elaboration or payload.
The predecessor inventory is an immutable historical snapshot, not current
implementation qualification. Component proxies are replaced exactly once.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
HOME='results/uarch/hbm_w2_w6_inventory_reconciliation_20261003/'
BASE='1f4422d75e08f35fe97e53d408d5e2140e6e72ce'
HIST=HOME+'inputs/historical-inventory-r1.json'
W6='results/uarch/hbm_W6_local_RTL_20261003/model_r1/model_r2_fanout.json'
PROPOSAL='results/uarch/hbm_W6_local_RTL_20261003/model_r1/component_proposal.json'
W2='results/uarch/w2_nc6_component_20261003/preparation.json'
CONNECTOR='results/uarch/hbm_W6_connector_model_20261003/r1/model.json'
JOIN='results/uarch/w2_r14_connector_model_20261003/model.json'
BRIDGE='results/uarch/h4_hbm_baseline_bridge_20261003/w5_w10_r4/model.json'
W6_RTL='rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv'
W2_RTL='rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv'
INPUTS=[HIST,W6,PROPOSAL,W2,CONNECTOR,JOIN,BRIDGE,W6_RTL,W2_RTL,
        'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','tools/hbm_w6_fullwidth_model.py',
        'tools/hbm_w6_local_rtl_model.py','tools/w2_nc6_component_preparation.py',
        'results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json',
        'results/uarch/hbm_rf_visibility_fence_20261002/model_connected_review.json']

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
def require(condition,message):
    if not condition:raise ValueError(message)

def integer(expression,params):
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) is int:return node.value
        if isinstance(node,ast.Name) and node.id in params:return params[node.id]
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult)):
            a,b=visit(node.left),visit(node.right)
            return a+b if isinstance(node.op,ast.Add) else a-b if isinstance(node.op,ast.Sub) else a*b
        raise ValueError('unsupported source dimension')
    return visit(ast.parse(expression,mode='eval').body)

def range_size(r,params):
    a,b=r.strip('[]').split(':')
    return abs(integer(a,params)-integer(b,params))+1

def nc6_state_census(source,params):
    # Bounded source grammar; all retained sequential names must reconcile.
    # Combinational reg/integer temporaries and output muxes are not FF state.
    declarations={'fault':1}
    body=source.split('localparam [1:0] FREE',1)[1].split('wire [SIDW-1:0] incoming_rc',1)[0]
    for width,items in re.findall(r'\breg\s*(\[[^]]+\])?\s*([^;]+);',body):
        bits=range_size(width,params) if width else 1
        for item in items.split(','):
            name=re.match(r'\s*(\w+)',item)[1]
            count=bits
            for r in re.findall(r'\[[^]]+\]',item):count*=range_size(r,params)
            require(name not in declarations,'duplicate source declaration')
            declarations[name]=count
    clocked=source.split('always @(posedge clk or negedge rst_n)',1)[1]
    names=set(re.findall(r'\b(\w+)(?:\[[^]]+\])*\s*<=',clocked))
    sections=dict(table=['state','tag','gen','direction'],counters_RR_fault=['outstanding','rr','fault'],
        request_holder=['hv','hw','hc','hs','ha','ht','hg','hd'],
        read_query=['rqv','rqbad','rqc','rqt','rqg','rqd'],
        read_delivery=['rdv','rdc','rds','rdt','rdg','rdd'],
        write_query=['wqv','wqbad','wqc','wqt','wqg'],write_selection=['sv','ss'])
    accounted={n for group in sections.values() for n in group}
    require(names==accounted,'sequential source name census mismatch')
    return dict(fields={n:declarations[n] for n in sorted(accounted)},
                section_bits={k:sum(declarations[n] for n in ns) for k,ns in sections.items()},
                raw_bits=sum(declarations[n] for n in accounted))

def replace_component(old_total,old_component,new_component):
    require(0<=old_component<=old_total and new_component>=0,'invalid replacement debit')
    return old_total-old_component+new_component

def compose(root=ROOT):
    pins=json.loads((root/HOME/'source-pins-r1.json').read_bytes())
    require(set(pins['sources'])==set(INPUTS),'source selection mismatch')
    raw={p:(root/p).read_bytes() for p in INPUTS}
    for p,b in raw.items():require(sha(b)==pins['sources'][p]['sha256'],'source drift: '+p)
    load=lambda p:json.loads(raw[p])
    hist,w6,w2,connector,join,bridge=map(load,[HIST,W6,W2,CONNECTOR,JOIN,BRIDGE])
    proposal=load(PROPOSAL)
    for p in [W6,W6_RTL,'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','tools/hbm_w6_fullwidth_model.py','tools/hbm_w6_local_rtl_model.py']:
        require(sha(raw[p])==proposal['source_sha256'][p],'selected W6 enrollment source identity')
    fields=w6['table']['raw_fields'];w6raw=sum(fields.values());protected=((w6raw+63)//64)*72
    require(w6raw==w6['table']['raw_bits_per_SM']==71,'W6 raw state')
    require(protected==w6['table']['protected_bits_per_SM']==144,'W6 protection state')
    text=raw[W6_RTL].decode()
    require('reg [143:0] protected_state;' in text and 'wire [70:0] raw=' in text,'W6 retained source state')
    require(set(re.findall(r'\b(\w+)\s*<=',text))=={'protected_state'},'W6 additional sequential state')
    require(w6['fanout']['identity_comparison_loads_per_bit']==7,'W6 selected match fanout')
    logic=protected*w6['assumed_DFF_um2']+sum(w6['gate_proxy'].values())*w6['assumed_gate_equivalent_um2']
    slot=logic*32/w6['area']['utilization']/1e6
    require(abs(slot-w6['area']['full32SM_slot_mm2'])<1e-12,'W6 gate/state area sum')
    oldw6=connector['W6_component'];oldslot=oldw6['area']['full32SM_slot_mm2']
    require(oldw6['table']['raw_bits_per_SM']==71,'historical W6 is not legacy51bit fence')
    params=dict(NC=6,MAX_OUT=16,AW=34,CTAGW=32,GENW=4,SIDW=3,PTAGW=35)
    require(all(w2['geometry'][k]==v for k,v in params.items()),'NC6 source geometry')
    census=nc6_state_census(raw[W2_RTL].decode(),params)
    s=w2['state'];require(census['raw_bits']==s['implemented_raw_bits']==4781,'NC6 raw source count')
    require(s['implemented_raw_bits']-s['base_raw_bits']==2,'NC6 capture-invalid state delta')
    selected=join['actual_W2_NC6']
    require(s['protected_bits']==selected['protected_state_bits_per_PC']==9144,'NC6 unchanged protection allocation')
    require(sum(selected['protected_state_by_section'].values())==s['protected_bits'],'NC6 protected section sum')
    cell=load('results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json')['facts']
    guard=(s['extra_guard_and_fence_logic_NAND2_budget']*cell['NAND2x1_ASAP7_75t_R']['SS']['area_um2']+
           s['extra_guard_and_fence_logic_INV_budget']*cell['INVx1_ASAP7_75t_R']['SS']['area_um2'])/1e6
    gross=2*128*(s['old_gross_body_mm2_assumed']+guard)
    require(abs(gross-s['all128PC_50pct_screen_mm2_ASSUMED'])<1e-12,'NC6 revised guard area')
    require(abs(s['old_gross_body_mm2_assumed']-selected['gross_protected_body_mm2_per_PC_ASSUMED'])<1e-12,'NC6 old component identity')
    legacy=load('results/uarch/hbm_rf_visibility_fence_20261002/model_connected_review.json')
    models={}
    ledger=bridge['resource_ledger']
    for name,hm in hist['models'].items():
        b=bridge['floorplan'][name]
        require(hm['current_bridge_composition']['context_plus_reserved_slots_mm2']==b['complete_context_plus_new_slots_mm2'],'historical bridge identity')
        require(hm['current_bridge_composition']['W6_component_mm2']==oldslot,'historical W6 debit identity')
        # Source records do not prove that this exact W6 component proxy is
        # included in the coarse complete bridge upper. Keep that conditional.
        conditional=replace_component(ledger['complete_service_area_upper_mm2_ASSUMED'],oldslot,slot)
        models[name]=dict(retained_context_plus_slot_envelope_mm2=b['complete_context_plus_new_slots_mm2'],
            RF4096_scratch64_L2256_PHY4_and_other_inventory_unchanged=True,
            W6_once_only_replacement=dict(old_component_mm2=oldslot,selected_component_mm2=slot,delta_mm2=slot-oldslot,
                copies=32,old_debit_identity_bound=True,exact_inclusion_in_bridge_upper_confirmed=False,
                conditional_bridge_logic_upper_mm2=conditional,bridge_slot_envelope_added_again=False),
            W2_once_only=dict(old_component_gross_mm2=selected['gross128PC50pct_slot_mm2_ASSUMED'],selected_gross_mm2=gross,
                guard_refinement_gross_delta_mm2=gross-selected['gross128PC50pct_slot_mm2_ASSUMED'],
                matched_F0_old_W2_debit_mm2=join['once_only']['matched_old_W2_debit'],net_increment_mm2=None,
                rule=join['once_only']['rule'],no_blind_gross_addition=True),
            exact_current_composed_area_mm2=None,whole_token_ns=None,source_production_drain_or_reset_bound=False,
            physical_admitted=False,build_GO=False)
    return dict(schema='opentallas.hbm.selected-W2-W6-reconciliation.v1',base_git=BASE,
        historical_inventory_origin=dict(commit='c8dafdfe0da8a537f9cea2d833a2a834308833a6',
            path='results/uarch/hbm_fullsize_inventory_20261003/model-r1.json',sha256=sha(raw[HIST]),current_implementation_complete=False),
        selected_source_identities={p:sha(raw[p]) for p in [W6_RTL,W2_RTL,W6,W2,'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv']},
        W6=dict(raw_fields=fields,raw_bits_per_SM=w6raw,raw_bits_32SM=32*w6raw,
            protected_bits_per_SM=protected,protected_bits_32SM=32*protected,identity_bits=55,generation_bits_charged_separately=0,
            gate_proxy=w6['gate_proxy'],logic_um2_per_SM=logic,logic_um2_32SM=32*logic,slot_mm2_32SM=slot,
            identity_match_loads_per_bit=7,clock_reset_loads_per_SM=144,clock_reset_loads_32SM=4608,
            source_state_storage='sole144bit SECDED register; raw71bits decoded; next_raw combinational',
            reset=w6['implementation_refinement']['reset'],source_allcopies_semantics=w6['implementation_refinement']['external_source_contract'],
            producer_of_alldrain_live_installed=False,physical_protection_latency=None,
            minimum_protocol_edges=w6['latency']['candidate_W6_minimum_edges'],finite_maximum_edges=None),
        W2=dict(source_census=census,raw_bits_per_PC=4781,raw_bits_128PC=4781*128,
            protected_bits_per_PC=9144,protected_bits_128PC=9144*128,
            protected_section_bits=selected['protected_state_by_section'],invalid_bits_use_existing_query_padding=True,
            capture_invalid_extra_raw_bits_128PC=256,protected_storage_implemented=False,
            guard_area_mm2_per_PC=guard,gross_slot_mm2_128PC=gross,geometry=params,
            source_reset=w2['reset'],additional_controls=w2['additional_controls'],clock=w2['clock']),
        legacy_RF_fence=dict(raw_bits_per_SM=legacy['total_state_bits'],separate_historical_contract=True,
            not_selected_W6=True,legacy_cost_subtracted_as_W6=False),
        models=models,evidence_scope='SOURCE_METADATA_AND_CONSTRUCTOR_FREE_ARITHMETIC_ONLY',
        payload_reads=0,constructors=0,RTL_elaborations=0,PnR_jobs=0,numerical_runs=0,physical_admitted=False,
        owner_joins=dict(Popper='confirm exact W6 old-proxy inclusion and matched F0 W2 debit before full composed area',
            Archimedes='selected component pin clock/reset/PG and loaded SS/FF; proxies grant no physical closure',
            Dewey='actual accepted source drain/ACK/consumer/reverse intervals; minimum edges are not finite maximum'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-inputs',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
    if a.freeze_inputs:
        pins=dict(schema='opentallas.hbm.selected-component-source-pins.v1',base_git=BASE,
                  sources={p:dict(sha256=sha((ROOT/p).read_bytes()),bytes=(ROOT/p).stat().st_size) for p in INPUTS})
        dest=ROOT/HOME/'source-pins-r1.json';b=encoded(pins)
        require(not dest.exists() or dest.read_bytes()==b,'immutable pins differ');dest.write_bytes(b)
    b=encoded(compose())
    if a.out:
        require(not a.out.exists() or a.out.read_bytes()==b,'immutable model differs');a.out.write_bytes(b)
    else:print(b.decode(),end='')
if __name__=='__main__':main()
