#!/usr/bin/env python3
"""Search actual integer expert templates against an explicit construction budget.

The area rail is a proposed allocated construction, never a mapped minimum.
Expert-only feasibility is a necessary subproblem of complete admission.
"""
import argparse, ast, hashlib, json, math
from decimal import Decimal as D
from pathlib import Path
import w17_integer_expert_residency as residency

CFG_BITS=4*25*48
GEOMETRY=('541a1d2f18c6c7eeae1577b0cc15eb859f097da2','tools/uarch_model.py')
BF_CLOCK=('0cdd92fd35f142c8f0fa170426113a5b2a64e153','results/uarch/w10_clock_tree_site_budget_r1/receipt.json')
Q_POWER=('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
Q_CONSTRUCTION_PIN=('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
DESCRIPTOR_PIN=('59d0630e62502eca15ef1151085aaf63c92c8e4e','tools/w17_compact_descriptor_price.py')

def field_masks(q):
    """Validate the existing NP8192/128-region Q + BF8 reservation scheme."""
    npairs,regions,bf_per_region=8192,128,8
    per_region=npairs//regions
    if type(q) is not int or not regions<=q<=npairs-regions*bf_per_region:
        raise ValueError('q mask outside combined Q/BF field capacity [128,7168]')
    qm=[];bm=[]
    for r in range(regions):
        first=r*per_region
        count=q//regions+int(r<q%regions)
        bf_first=first+count
        if not (first<=bf_first and bf_first+bf_per_region<=first+per_region<=npairs):
            raise ValueError('Q/BF mask exceeds region or NP domain')
        qm.append(dict(region=r,first_pair=first,pairs=count))
        bm.append(dict(region=r,first_pair=bf_first,pairs=bf_per_region))
    if sum(m['pairs'] for m in qm)!=q or sum(m['pairs'] for m in bm)!=1024:
        raise ValueError('Q/BF mask count mismatch')
    return qm,bm

def product_geometry():
    raw=residency.blob(GEOMETRY)
    names={'FLOORPLAN','CONS_REFIT','CONS_FIELD_MM2','VMH_BLOCK','VMC_BLOCK',
        'CONS_SLIVER_MM2','CONS_GEOM','CONS_CREDIT','PRODUCT_GEOM','CONS'}
    nodes=[]
    for n in ast.parse(raw).body:
        if isinstance(n,ast.Assign):
            for t in n.targets:
                key=t.id if isinstance(t,ast.Name) else t.value.id if isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) else None
                if key in names:nodes.append(n);break
        elif isinstance(n,ast.FunctionDef) and n.name=='cons_field_usable_mm2':nodes.append(n)
    e={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned product geometry>','exec'),e)
    usable=D(str(e['cons_field_usable_mm2'](geom=e['PRODUCT_GEOM'])))
    clock=json.loads(residency.blob(BF_CLOCK));outline=clock['slot']['outline_um']
    bf=D(str(outline[0]))*D(str(outline[1]))/D(1000000)
    return dict(product=e['PRODUCT_GEOM'],usable_field_mm2=str(usable),
        die_mm2=e['FLOORPLAN']['die_mm2'],geometry=e['CONS_GEOM'][e['PRODUCT_GEOM']],
        hub=e['VMC_BLOCK'],overhead=e['CONS']['overhead'],fill=e['CONS']['fill'],
        BF1024_reserved_mm2=str(1024*bf),BF_per_pair_reserved_mm2=str(bf),
        BF_scope='Current conditional 625-row clock outline reservation only. Spatial hypothesis failed; no legal placement/SSFF fit transfer.',
        source_pins={name:dict(commit=p[0],path=p[1],sha256=residency.sha(residency.blob(p)))
            for name,p in [('geometry',GEOMETRY),('BF_clock_outline',BF_CLOCK)]})

def descriptor_cost(cap,stride):
    slot_bits=(cap-1).bit_length();stride_bits=stride.bit_length()
    regs=slot_bits+14+14+3+2
    mux_bits=(4*25-1)*48+48
    gates=(14+13)*5
    area=(D(CFG_BITS+regs)*D('.2916')+D(gates+mux_bits)*D('.2'))/D('.5')/D(1000000)
    return dict(slot_bits=slot_bits,stride_bits=stride_bits,
        shiftadd_and_prefix_cycles=stride_bits+1,
        cfg_cycles=27+stride_bits+1,placed_area_mm2_per_pair=str(area),
        scope='Proposed fixed-stride shift/add and local template read; same gate-screen coefficients as 59d. No hardware timing credit.')

def search(choices):
    # Reject every invalid choice before reading inputs or calling the allocator.
    choices=list(choices)
    masks=[field_masks(q) for q in choices]
    m=residency.inputs();rows=[];pg=product_geometry()
    area_limit=D(pg['usable_field_mm2']);reserve=D(pg['BF1024_reserved_mm2'])
    power=json.loads(residency.blob(Q_POWER))
    construction_receipt=json.loads(residency.blob(Q_CONSTRUCTION_PIN))
    q_construction=D(construction_receipt['conditional_50pct_cell_plus_macro_budget_um2'])/D(1000000)
    for q,(mask,bf_mask) in zip(choices,masks):
        row=dict(q_pairs=q,NP=8192,return_regions=128)
        try:
            templates,stride=residency.templates(m,q)
            owners,stages,cap=residency.assignments(m,templates,stride)
            dc=descriptor_cost(cap,max(stride.values()))
            construction=q_construction*q;cfg=D(dc['placed_area_mm2_per_pair'])*q
            layer_dist=[]
            for layer in range(40):
                ss=sorted({x['stage'] for x in owners if x['layer']==layer})
                layer_dist.append(dict(layer=layer,expert_stages=ss,
                    maximum_distance_from_first_owner=ss[-1]-ss[0]))
            assert cap*max(stride.values())<=8192<(cap+1)*max(stride.values())
            row.update(status='INTEGER_EXPERT_SUBPROBLEM_PASS',
                q_mask=mask,whole_triplet_capacity=cap,
                BF_mask=bf_mask,
                per_family_active_q_pairs={f:len(t['pairs']) for f,t in templates.items()},
                expert_only_physical_stages=len(stages),TP4_expert_die_count=4*len(stages),
                maximum_logical_mate_stride=max(stride.values()),
                maximum_full_stage_physical_bank_rows=cap*max(stride.values())//2,
                owner_stage_bits=(len(stages)-1).bit_length(),
                owner_entry_bits=1+(len(stages)-1).bit_length()+dc['slot_bits'],
                descriptor=dc,expert_stream_issue_cycles=sum(t['stream_issue_cycles'] for t in templates.values()),
                per_expert_cfg_plus_stream_partial_cycles=3*dc['cfg_cycles']+sum(t['stream_issue_cycles'] for t in templates.values()),
                q_allocated_construction_mm2=str(construction),
                cfg_affine_addition_mm2=str(cfg),
                construction_plus_cfg_mm2=str(construction+cfg),
                explicit_other_geometry_reserve_mm2=str(reserve),
                within_supplied_area_envelope=construction+cfg+reserve<=area_limit,
                layer_dispatch_distances=layer_dist,
                template_sha256=residency.sha(json.dumps(templates,sort_keys=True,separators=(',',':')).encode()),
                pair_stride_sha256=residency.sha(json.dumps(stride,sort_keys=True,separators=(',',':')).encode()))
            remaining=D(pg['usable_field_mm2'])-construction-cfg-D(pg['BF1024_reserved_mm2'])
            row['fixed_product_field_remainder_after_q_cfg_BF1024_mm2']=str(remaining)
            row['q_cfg_BF1024_area_screen_pass']=remaining>=0
            row['complete_geometry_fit']=False
            row['conditional_q_construction_power_W']=str(D(power['construction_total_power_W'])*q)
            row['conditional_q_power_envelope_within_die_budget']=D(row['conditional_q_construction_power_W'])<=D(power['thermal_limit_W'])
            row['power_interpretation']='Failure of this deliberately overcounted conditional envelope to certify thermal fit is not an impossibility lower bound. No stop credit or duty-factor reduction.'
            row['dispatch_sensitivity']=dict(
                proposed_bits_per_replica_source_cycle=256,replicas=4,
                aggregate_bits_per_source_cycle=1024,
                separate_TP4_die_links=True,
                request_bits_per_rank=5120*16,return_bits_per_rank=1280*16,
                request_serialization_cycles_per_hop=320,return_serialization_cycles_per_hop=80,
                selected_experts_serial=6,
                source_order_six_expert_worst_linear_dispatch_serialization_cycles=sum(6*(x['maximum_distance_from_first_owner']+1)*400 for x in layer_dist),
                dedicated_hub_to_first_expert_extra_hop=1,
                rule='Conditional single-packet store/forward dispatch, four rank links concurrently, six selected experts serialized. Packet credits retained through actual serialization, CDC and consumer completion. Aggregate TP4 bits do not multiply per-rank speed.',
                remaining_link_costs=['PHY and registered route delay','Forward and reverse CDC','Actual consumer completion','Credit storage and arbiter area','Whole-token activation/KV/index/collective hops'],
                actual_link_qualification=False)
        except (ValueError,AssertionError) as error:
            row.update(status='INTEGER_PLACEMENT_REJECTED',failure=str(error))
        rows.append(row)
    raw={name:residency.blob(pin) for name,pin in
         [('manifest',residency.MANIFEST),('packing',residency.SEG),('allocator',residency.PLACE)]}
    return dict(schema='opentallas.w17.conservative-geometry-search.v1',
        scope='Executed capacity/runtime search; expert-only candidate, not complete product admission.',
        source_pins={name:dict(commit=pin[0],path=pin[1],sha256=residency.sha(raw[name]))
            for name,pin in [('manifest',residency.MANIFEST),('packing',residency.SEG),('allocator',residency.PLACE)]},
        construction_assumption=dict(q_pair_allocated_mm2=str(q_construction),
            source_pin=dict(commit=Q_CONSTRUCTION_PIN[0],path=Q_CONSTRUCTION_PIN[1],sha256=residency.sha(residency.blob(Q_CONSTRUCTION_PIN))),
            provenance='Source-bound Confucius construction hypothesis; not a mapped-area measurement or lower bound.',
            actual_mapped_minimum=False,measured_fit_credit=False),
        descriptor_cost_source_pin=dict(commit=DESCRIPTOR_PIN[0],path=DESCRIPTOR_PIN[1],sha256=residency.sha(residency.blob(DESCRIPTOR_PIN))),
        supplied_geometry_envelope=dict(area_limit_mm2=str(area_limit),other_reserve_mm2=str(reserve),
            classification='Fixed source-bound PRODUCT_GEOM usable field and explicit BF1024 reservation. No larger-die override; remainder must cover remaining infrastructure before admission.'),
        candidates=rows,
        fixed_sourcebound_product_geometry=pg,
        conditional_sourcebound_q_power=dict(receipt=power,
            source_pin=dict(commit=Q_POWER[0],path=Q_POWER[1],sha256=residency.sha(residency.blob(Q_POWER)))),
        baseline_area_candidate=dict(q_pairs=1024,BF_pairs=1024,
            expert_only_stages=next((r['expert_only_physical_stages'] for r in rows if r['q_pairs']==1024),None),
            decision='Attempt current q1024 integer field plus explicit BF1024 and existing C_rotate hub within PRODUCT_GEOM. Remaining field must pay additional descriptor/hub/service/NoC/CDC/clock/PG reserves. Source-bound area screen is not legal slot or power feasibility.',
            full_operator_and_thermal_feasibility=False),
        mandatory_remaining=['All active nonexpert ROM formats/bank assignments and separately homed Engram immutable tables',
            'Actual q/BF construction proof, clock/PG/pin/track reserves and legal placed geometry',
            'Whole exact TP4 programme including shared sources, Engram projection gather and final head merge',
            'Per-hop bits/replica/aggregate serialization, queue credits, CDC, actual consumer completion',
            'Correct writable CKV mux and delayed backend visibility, prelease drain and bounded publication',
            'Complete operator/SU/SFU/index/attention/collective resource calendar and power envelope'],
        product_stage_count_derived=False,complete_architecture_admission=False,
        engine_RTL_build_ready=False,physical_admission=False,headline_rate=None,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--q-pairs',type=int,nargs='+',default=[2048,1536,1024,768,512])
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(search(a.q_pairs),indent=2)+'\n')
