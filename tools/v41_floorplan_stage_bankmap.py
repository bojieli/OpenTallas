#!/usr/bin/env python3
"""Checkpoint-header exact reservations for one candidate stage, not an adopted die."""
import argparse, hashlib, json, math, re, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def reserve(rows,cols,depth=8192):
    if rows%8 or cols%32: raise ValueError('unsupported qtile shape')
    beats=(rows//8)*(cols//32)
    depth_required=(beats+1)//2
    sets=(depth_required+depth-1)//depth
    return dict(rows=rows,cols=cols,beats=beats,bank_sets=sets,macros=sets*8,
        required_rows_per_bank=depth_required,allocated_rows_per_bank=sets*depth,
        useful_payload_bytes=rows*(cols//2+cols//32),
        macro_bytes=sets*8*depth*274//8,
        mapping='lane c bank=8+4*(beat%2)+floor(c/2), row=floor(beat/2), half=c%2; each additional depth segment needs bank-set select')

def derive(snapshot,stage=None,rank=0):
    ownpath=ROOT/'results/arch/v41_stage_owner_preflight.json'
    own=json.loads(ownpath.read_text()); heads=own['per_die_headroom_after_rounding_and_engram_spill_bytes']
    stage=min(range(len(heads)),key=lambda i:heads[i]) if stage is None else stage
    indexpath=snapshot/'model.safetensors.index.json'; idx=json.loads(indexpath.read_text())['weight_map']; headers={}; pins={}
    def meta(name):
        f=idx[name]
        if f not in headers:
            with (snapshot/f).open('rb') as h:
                n=struct.unpack('<Q',h.read(8))[0]; raw=h.read(n)
            headers[f]=json.loads(raw);pins[f]={'header_sha256':hashlib.sha256(raw).hexdigest(),'resolved_blob':(snapshot/f).resolve().name}
        return headers[f][name]
    assigns=[];dense=[]
    for layer in own['layer_owners']:
        if layer['dense_owner_stage']==stage:dense.append(layer['layer'])
        for o in layer['routed_expert_candidate_owners']:
            if o['stage']==stage:assigns.append(dict(layer=layer['layer'],expert_first=o['expert_ids'][0],expert_last=o['expert_ids'][1]))
    entries=[];bank_start=0
    for a in assigns:
        for e in range(a['expert_first'],a['expert_last']+1):
            for family in ['w1','w3','w2']:
                name=f"layers.{a['layer']}.ffn.experts.{e}.{family}"
                w=meta(name+'.weight');s=meta(name+'.scale')
                if w['dtype']!='I8' or s['dtype']!='F8_E8M0':raise ValueError(name+' format')
                nr,nc=w['shape']; cols=nc*2
                if nr%4 or s['shape']!=[nr,cols//32]:raise ValueError(name+' shape')
                # Both expert hidden projections and adopted w2 use output-row TP.
                r=reserve(nr//4,cols)
                entries.append(dict(tensor=name,checkpoint_weight_shape=w['shape'],checkpoint_scale_shape=s['shape'],
                    rank=rank,output_row_begin=rank*(nr//4),output_row_end=(rank+1)*(nr//4),
                    local_mac_association=f"ROM_MAC.stage{stage}.rank{rank}.expert_qtile0",
                    association_status='proposal: one reusable local eight-lane qtile; replication and timing budget not approved',
                    macro_first=bank_start,macro_last=bank_start+r['macros']-1,**r))
                bank_start+=r['macros']
    # Every actual non-routed tensor header at the dense-owned layers retained.
    unresolved=[]
    for layer in dense:
        for name in sorted(idx):
            if name.startswith(f'layers.{layer}.') and '.ffn.experts.' not in name:
                m=meta(name);unresolved.append(dict(tensor=name,dtype=m['dtype'],shape=m['shape'],
                    full_tensor_bytes=m['data_offsets'][1]-m['data_offsets'][0],
                    rank_slice=None,macro_binding=None))
    catpath=ROOT/'physical/asap7_memory_macros/index.json';m=json.loads(catpath.read_text())['macros']['ot_rom_8192x274_m8']
    logical=sum(x['useful_payload_bytes'] for x in entries)
    capacity=math.ceil(json.loads((ROOT/'results/arch/v41_die_placement.json').read_text())['rom_bytes_per_die'])
    return dict(schema='opentallas.v41.candidate_stage_bankmap.v1',status='rejected_as_complete_deployed_die_mapping',
        ownership_status=own['status'],stage=stage,rank=rank,stage_selection='minimum reported coarse headroom, not exact worst physical stage',
        checkpoint_revision=snapshot.name,index_sha256=sha(indexpath),checkpoint_header_pins=pins,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ownpath,catpath,ROOT/'rtl/chip/ot_chip_v41x_qtile_pair_bank.sv']},
        owner_ranges=assigns,dense_layers=dense,expert_matrices=entries,unbound_dense_tensors=unresolved,
        reservation=dict(macro_type='ot_rom_8192x274_m8',macros=bank_start,area_mm2=bank_start*m['area_um2']/1e6,
            payload_bytes=logical,physical_macro_bytes=sum(x['macro_bytes'] for x in entries),
            macro_bits_minus_payload_bits=sum(x['macro_bytes']-x['useful_payload_bytes'] for x in entries)*8,
            logical_capacity_budget_bytes=capacity,known_payload_exceeds_budget=logical>capacity,
            capacity_acceptance=False,
            port_contract='8 simultaneous 264-bit operands; current FP4 pairing supports qtile skew. No global activation/result network assigned.'),
        proposed_root_decision={'ownership':'approve whole expert ranges from candidate for first placement experiment, preserve w2 output-row split',
            'banking':'reserve separate eight-bank sets per matrix first; cross-matrix packing is a later optimization requiring replay proof',
            'compute':'one qtile is only a wiring association placeholder; root must allocate replication from scheduled latency and macro read ports',
            'alternative':'repartition whole expert IDs across adjacent stages before generation; requires expert activation forwarding and ordered result return priced in token schedule'},
        rejection_reasons=['candidate owner map is not executable whole-stage program ownership',
            'dense tensors lack approved rank slices and macro bindings','Engram spill rows are not enumerated',
            'all-stage worst physical occupancy has not been evaluated','macro ECC absent',
            'bank selection, local MAC replication and result network have no approved timing/area binding'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--stage',type=int);p.add_argument('--rank',type=int,default=0);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.rank not in range(4):p.error('rank must be0..3')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(derive(a.snapshot,a.stage,a.rank),indent=2)+'\n')
