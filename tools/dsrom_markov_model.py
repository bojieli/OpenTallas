"""Released DSpark Markov row sizing, before RTL. No physical or rate credit."""
import math

def model(k=256, vocab=129280, sk=11,pinreg=0):
    assert k >= 16 and k % 16 == 0 and not (k//16 & (k//16-1))
    assert pinreg in (0,1,2)
    capture=int(pinreg!=0)
    words=k//16
    levels=int(math.log2(words))
    latency=capture+6+(9+levels+1)*sk+3
    return dict(schema='opentallas.dsrom.markov-row.v1',default_enabled=False,adopted=False,
        shape=dict(vocab=vocab,k=k,source='released mtp.2.markov_head.{head,embed}.weight safetensors headers'),
        arithmetic='BF16 exact products; each contiguous8 summed sequentially from+0; pairwise tree; separate add(lm_head,markov)',
        MACs_per_cycle=16,compute_intensity_macs_per_weight_byte=0.5,
        ports_bytes_per_cycle=dict(weights=32,embedding=32,head_logit=4,result=4),
        boundary_bits_per_cycle=dict(weights=256,embedding=256,control=2,head_logit=32,result=32),
        replicas=dict(row_engine=1,multipliers=16,chunk_adders=16,tree_adders=1+levels,join_adders=1),
        fanout=dict(clock_loads='measure synthesis',embedding_lanes=16,token_broadcast='129280-row bounds check; identity required'),
        routing=dict(input_tracks=549,output_tracks=36,capacity=dict(slot_um=[600,600],pin_faces_um=540,maximum_pins_per_um=256/540,routing_layers=['M2','M3','M4','M5','M6'],pin_fit=True)),
        storage=dict(embed_bytes=vocab*k*2,head_bytes=vocab*k*2,head_pair_payload_bytes=8192*32,
                     embed_head_pairs=math.ceil(vocab*k*2/(8192*32))),
        area=dict(pinreg_enabled=bool(pinreg),pinreg_mode=pinreg,payload_capture="unconditional" if pinreg==2 else "accepted-only",maximum_extra_invalid_payload_Q_transitions_per_cycle=512 if pinreg==2 else 0,extra_energy_basis="up to512 payload FF/Q transitions each invalid cycle; dynamic energy awaits routed capacitance/activity; no energy credit",input_capture_bits=513*capture,input_capture_area_um2=513*capture*0.6,product_delay_bits=2*sum(range(8))*sk*32,
                  floorplan_slot_um=[600,600],core_um=[596,596],macros=0,
                  baseline_head_standardcell_um2=19061.2,baseline_head_sequential_um2=7686.36,baseline_head_sequential_cells=25862,
                  delay_flop_planning_um2_per_bit=0.6,delay_flop_basis='2x measured head sequential area/count, rounded upward; planning estimate, synthesis must confirm',
                  cell_area_planning_um2=1.5*(19061.2+0.6*(2*sum(range(8))*sk*32+513*capture)),
                  cell_area_capacity_um2=0.55*596*596,slot_fit=1.5*(19061.2+0.6*(2*sum(range(8))*sk*32+513*capture))<=0.55*596*596,
                  baseline_evidence='results/rtl/dsrom_fh_redesign_20261006/elemB_final/history/original_physical.json',
                  physical_scope='standalone streaming row; excludes ROM ports/allocation and parent'),
        latency=dict(first_beat_to_join_cycles_upper=words+latency,last_beat_to_join_cycles_upper=latency,
                     words_per_row=words,minimum_transaction_II_upper=words+latency+2,
                     five_sweeps_compute_ratio=k/5120,previous_reduced_ratio=32/4096,
                     claimed_54_6ns_budget_met=False),
        clock_budget=dict(route_ps=770,TT_signoff_ps=833.333,setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,input_max='measured TT insertion +250ps',input_min='measured FF insertion',output_max='250ps-measured TT insertion',output_min='-(measured FF insertion+50ps)',acceptance='TT setup>=0 FF hold>=0 DRC0; SS sensitivity only'),
        qualified=False,open=['ROM embed port','head row ROM allocation','full head element integration','exactness','TT/FF physical admission'])

if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
