"""Conditional accepted-event model; NOT existing RTL isolation proof."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'sensitivity_192_role_repack_constants_retained.json').read_bytes();r=json.loads(raw)
coords=r['coordinate_construction'];xs=coords['x_slot_origins_um'];ys=coords['y_slot_origins_um'];px,py=coords['cell_pitch_um']
pin=subprocess.check_output(['git','rev-parse','64c6bffe0'],text=True).strip()
mp='physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
ms=subprocess.check_output(['git','show',pin+':'+mp]);assert b'if (ce_in) rd_out <= word_read(addr_in);' in ms
levels=[dict(level=i,edges=0,wire_stage_sum=0,max_edge_um=0.) for i in range(13)]
paths={}
def center(a,b,xx,yy):return ((xs[a]+xs[a+xx-1]+px)/2,(ys[b]+ys[b+yy-1]+py)/2)
def walk(x,y,nx,ny,depth,idx,path):
    if depth==13:
        paths[idx]=path;return
    parent=center(x,y,nx,ny)
    for bit in (0,1):
        if depth%2==0:xx,yy,nnx,nny=x,y+bit*ny//2,nx,ny//2
        else:xx,yy,nnx,nny=x+bit*nx//2,y,nx//2,ny
        child=center(xx,yy,nnx,nny);L=abs(parent[0]-child[0])+abs(parent[1]-child[1]);stages=max(1,math.ceil(L/504))
        levels[depth]['edges']+=1;levels[depth]['wire_stage_sum']+=stages;levels[depth]['max_edge_um']=max(levels[depth]['max_edge_um'],L)
        walk(xx,yy,nnx,nny,depth+1,idx*2+bit,path+[stages])
walk(0,0,64,128,0,0,[])
assert len(paths)==8192 and all(len(p)==13 for p in paths.values())
wire=sum(l['wire_stage_sum'] for l in levels);nodes=8191
repacked_tree_FF=339*(nodes+wire)+2*nodes
oldraw=(ROOT/'sensitivity_192_homes.json').read_bytes();old=json.loads(oldraw)
new_homes=[]
for h in old['homes']:
    count=h['actual_macros'];pathsum=[sum(paths[i]) for i in range(count)]
    new_homes.append(dict(home_id=h['home_id'],actual_macros=count,
        new_tree_wire_control_FF_bits=repacked_tree_FF,
        total_storage_FF_bits=repacked_tree_FF+count*298+4864+64,
        held_state_feedback_MUX2_bits=repacked_tree_FF+count*298+4864+64,
        response_MUX2_bits=nodes*288,request_demux_AND2_bits=2*nodes*51,
        selected_wire_path_cycles_range=[min(pathsum),max(pathsum)],
        complete_row_cycles_conditional_range=[2*(13+min(pathsum))+1+7,2*(13+max(pathsum))+1+7]))
proof_digest=hashlib.sha256();max_path=max(sum(p) for p in paths.values())
for leaf,path in paths.items():
    offset=0;req_events=[]
    for wirestages in path:
        offset+=1 # dedicated decode stage
        req_events.extend((offset+b,b) for b in range(8))
        for _ in range(wirestages):
            offset+=1;req_events.extend((offset+b,b) for b in range(8))
    macro_events=[(offset+1+b,b) for b in range(8)]
    off=offset+1;rsp_events=[]
    for wirestages in reversed(path):
        for _ in range(wirestages):
            off+=1;rsp_events.extend((off+b,b) for b in range(8))
        off+=1;rsp_events.extend((off+b,b) for b in range(8))
    assert off+7==2*(13+sum(path))+1+7
    assert len(req_events)==len(rsp_events)==8*(13+sum(path))
    assert [b for _,b in macro_events]==list(range(8))
    proof_digest.update((json.dumps([leaf,req_events,macro_events,rsp_events],separators=(',',':'))+'\n').encode())
seq=list(range(8));beat_changes=sum((a^b).bit_count() for a,b in zip(seq,seq[1:]));assert beat_changes==11
out=dict(schema='opentallas.engram.conditional-enable-mask-events.v1',
    status='CONDITIONAL_MODEL_EVENT_PROOF_NOT_ACTUAL_TREE_RTL_DATA_ISOLATION',
    repacked_source_sha256=hashlib.sha256(raw).hexdigest(),prior192_source_sha256=hashlib.sha256(oldraw).hexdigest(),
    source_macro_behavior_pin=dict(commit=pin,path=mp,sha256=hashlib.sha256(ms).hexdigest()),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    existing_source_fact='Macro behavioral rd_out updates only when ce_in=1. This proves behavioral data hold, NOT Liberty CLK suppression, output load, internal macro dynamic isolation, or new-tree implementation.',
    hypothetical_tree_rule=dict(request='A branch writes only on parent_valid & selected_child & child_ready. Unselected branch payload FF holds its previous value via explicit feedbackMUX. Do not broadcast changing word/address to all leaves.',
        response='Selected child valid+ready transfers one288b beat. Under stall, payload/selector/tag/valid remain stable; no overwrite. Inactive sibling output remains held in this proposed contract.',
        macro='Only selected macro receives ce_in for8accepted sequential addresses; all other addr pins held at previous value and ce_in=0. Selected physical macro outputs captured before any mux. All clocks remain ungated.',
        reset='Initialization of valid/lease state and reset/epoch distribution is a separate unqualified event. Runtime bounds apply only after initialization; no free global reset or payload clearing credit.',
        lease='Two root row slots; reserve a slot BEFORE read. Hold row identity/epoch until external final consumer acknowledgement returns. No tag reuse, overwrite or second samehome lookup without reserved slot. Unknown external ACK wait is not finite-latency credit.',
        source_presence='No new tree RTL/provider exists. Mask semantics are an admission prerequisite, not an existing hardware guarantee.'),
    path_geometry=dict(levels=levels,wire_stage_sum=wire,wire_path_cycles_range=[min(sum(p) for p in paths.values()),max_path],
        event_schedule_all8192paths_SHA256=proof_digest.hexdigest(),eventproof='Each path has exactly8ordered macro reads,8updates per chosen decode/mux/wire stage, no offpath accepted write. Stall inserts held cycles, not accepted data events; ACK latency remains unbound.',
        prior104cycle_row_not_transferred_to_repacked_grid=True),
    homes=new_homes,aggregate_repacked_storage_FF_bits=sum(h['total_storage_FF_bits'] for h in new_homes),
    finite_runtime_transition_bounds_per_lookup=dict(request_register_payload_and_valid_bit_transitions_upper=51+2*11+1,
        request_bound_recipe='At most51initial changes,22betweenbeats (wordlow3+beat3),onevalidclear; rowhighbits/epoch/layer/column/lease stable withinrow.',
        response_register_bit_transitions_upper=8*264+24+11+1,
        macro_output_bit_transitions_upper=8*274,
        macro_and_tag_capture_bit_transitions_upper=8*274+24+11+1,
        request_selected_path_register_copies_upper=13+max_path,response_selected_path_register_copies_upper=13+max_path,
        inactive_request_sibling_raw_input_bit_transitions_upper=13*(51+22+1),
        both_child_request_demux_raw_input_bit_transitions_upper=2*13*(51+22+1),
        selected_response_MUX_raw_input_bit_transitions_upper=13*(8*264+24+11+1),
        macro_addr_pin_transitions_upper=12+11,macro_CE_transitions_upper=2,
        one_packet_slot_write_bit_transitions_upper=8*288+128,
        root_control_upper_accepted_bit_write_events=64*10,
        guard='Raw inputs to disabled NAND/MUX branches STILL toggle and consume pin/internal power; physical gate truth/event pricing belongs to Confucius. Do not equate inactive FF D hold with zero cone energy.',
        source_weight_values_read=False,actual_token_bit_pattern_bound=False),
    workload=dict(lookups_per_token=48,active_homes_per_layer=24,macro_reads_per_lookup=8,total_macro_reads_per_token=384,
        capture_reads_per_home_at_most_one_lookup_per_layer=True,clock_activity='ALL192storage+all1500067macro clocks1.2GHz; no24home idleclock credit.'),
    prior_source_power_receipt='200e52bdf applies earlier uniform-origin192inventory. New repack changes FF/pipeline counts; source-typed repricing required, not silently reused.',
    physical_data_provider_proven=False,framing_CRC_sharedport_contract=None,
    routing_status='Existing fullwidth edge341tracks exceeds321remaining spine tracks; this event model does not solve that failure.',
    L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
target=ROOT/'repacked_192_enable_mask_contract.json';assert not target.exists();target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),FF=out['aggregate_repacked_storage_FF_bits'],path=out['path_geometry']['wire_path_cycles_range'],rowrange=new_homes[0]['complete_row_cycles_conditional_range'])))
