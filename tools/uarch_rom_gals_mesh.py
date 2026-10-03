#!/usr/bin/env python3
"""Additive seam/clock overlay on uarch_model; no RTL generation or physical jobs.
Replay: python3 tools/uarch_rom_gals_mesh.py --out results/uarch/rom_gals_mesh_20261003/model.json
All new timing/area/power entries are estimates, never signoff verdicts.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, json, math
from pathlib import Path
import uarch_model as U
import arch_budget_qwen3 as Q
ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'results/uarch/rom_gals_mesh_20261003/inputs'
FAST, SLOW = 1.2, .9  # cycles/ns

def read(name):
    p = INPUT / name
    return json.loads(gzip.decompress(p.read_bytes()) if name.endswith('.gz') else p.read_bytes())

def boundary(name, count, payload, identity, fanout, width_um, layers, depth=16, kind='async'):
    """Point-to-point banks: no shared mux or arbitration between golden tree children.
    The 64-bit envelope is an ASSUMED budget for epoch/op/row/sequence, not a new ABI.
    Async baseline: 2 Gray synchronizer stages + registered read, 3 dst cycles
    inclusive worst phase; sensitivity explicitly charges a fourth cycle.
    Related baseline: 2 dst cycles, from 27d86, only inside a common local root.
    """
    w = payload + identity
    aw = math.ceil(math.log2(depth))
    measured = read('cdc_physical.json')['place_and_route']['metrics']
    # Conservative sizing proxy: scaled whole routed related-FIFO core, not a closure claim.
    scale = w / 512 * depth / 4
    tracks = w + 12  # 2 ready/valid + 2*5 pointer bits for D16; clocks/reset separately local
    raw = layers * width_um / .048
    usable = raw * (1 - 2*.0439 - .05)
    return dict(name=name, replicas=count, payload_bits=payload, identity_bits=identity,
                wire_word_bits=w, payload_bytes_per_cycle=payload/8, wire_bytes_per_cycle=w/8,
                steady_payload_bytes_per_ns=payload/8*FAST, bits_per_cycle=w,
                memory_ports=dict(write_bytes_per_cycle=w/8,read_bytes_per_cycle=w/8),
                depth=depth, storage_bits=count*depth*w,
                read_mux=dict(inputs=depth, bits=w, two_to_one_muxes=count*w*(depth-1)),
                demux=dict(write_selects=count*depth), producer_fanout=fanout,
                downstream_ready_fanout=1, capacity_words_per_ns=FAST if kind=='async' else SLOW,
                latency_dst_cycles=3 if kind=='async' else 2,
                acceptance='ESTIMATE_UNQUALIFIED' if kind=='async' else 'LOCAL_RELATED_CONTRACT_ONLY',
                reserved_core_mm2=count*measured['core_area_um2']/1e6*scale,
                active_power_proxy_w=count*measured['power_total_w']*scale,
                area_power_basis='W512 D4 related routed block scaled by W/512 * D/4; async mapping/activity unmeasured',
                placement=dict(proposed_width_um=width_um,required_height_um=measured['core_area_um2']*scale/width_um,
                               bank_area_mm2=measured['core_area_um2']/1e6*scale,fit_proven=False,
                               note='Area-equivalent rectangle only; compare against live owner station/slab union before placement'),
                routing=dict(width_um=width_um, layers=layers, pitch_um=.048, raw_tracks=raw,
                             net_tracks=usable, tracks_per_bank=tracks,
                             parallel_track_floor=count*tracks,
                             util_one_bank=tracks/usable, aggregate_util_if_shared=count*tracks/usable,
                             claim='Track floor only; no via/pin/PG/clock/placement qualification'))

def dag_charge(g, ns):
    g=copy.deepcopy(g)
    before=g.solve(True)['token.return']
    for node in g.nodes.values():
        if node['kind']=='matvec':
            node['depth']+=ns*1e-9
    after=g.solve(True)['token.return']
    return dict(charged_ns_per_matvec=ns,base_us=before*1e6,delta_us=(after-before)*1e6,
                overlay_us=after*1e6,matvec_nodes=sum(n['kind']=='matvec' for n in g.nodes.values()),
                affected_critical_path_nodes=[n for n in g.path('token.return') if g.nodes[n]['kind']=='matvec'],
                claim='Unified DAG sensitivity only; not a source-qualified S58/PAR2 or full-token measurement')

def mesh(w,h,base_area,clock_power):
    rows=[]
    for pitch,cell_fraction,power_factor,skew in [(2,.005,1.25,80),(1,.01,1.5,40),(.5,.02,2,20)]:
        length=(math.ceil(w/pitch)+1)*h+(math.ceil(h/pitch)+1)*w
        wire_w=length*.2e-12*.7**2*FAST*1e9
        extra_area=base_area*cell_fraction
        rows.append(dict(pitch_mm=pitch,wire_length_mm=length,wire_cap_pf_per_mm=.2,voltage_v=.7,
                         shielded_metal_area_mm2=length*.003,wire_dynamic_w=wire_w,
                         incremental_driver_area_mm2=extra_area,
                         incremental_clock_w=clock_power*(power_factor-1)+wire_w,
                         assumed_residual_skew_ps=skew,
                         area_budget_remaining_mm2=858-base_area-extra_area,
                         crossing_latency_cycles=1, # actual registered boundary still costs a cycle
                         common_root_ratio_fifo_cycles_each_direction=2,
                         status='ASSUMPTION_NOT_SKEW_OR_SS_FF_PASS'))
    return rows

def build():
    for pin in read('pins.json'):
        assert hashlib.sha256((INPUT/pin['file']).read_bytes()).hexdigest()==pin['sha256']
    q, ds, field = read('qwen_floorplan.json'),read('ds_parent.json'),read('ds_field.json.gz')
    cdc=read('cdc.json')
    assert cdc['latency']['fast_to_slow']['max_dst_cycles']=='2'
    assert cdc['latency']['slow_to_fast']['max_dst_cycles']=='2'
    assert ds['candidate']=='DS4096-TP4-S58-PAR2-NP2048'
    assert len(field)==2048 and len({x['source_root'] for x in field})==64
    roots=[]
    for root in range(64):
        boxes=[x['bbox_DBU'] for x in field if x['source_root']==root]
        bbox=[min(b[0] for b in boxes)/1000,min(b[1] for b in boxes)/1000,
              max(b[2] for b in boxes)/1000,max(b[3] for b in boxes)/1000]
        roots.append(dict(root=root,pairs=len(boxes),bbox_um=bbox))
    # Parent DBU = 1000/um, cf. original field end 6315840/1000 = 6315.84 um.
    qseams=[boundary('midline_column_command',64,508,64,12,52.704,2),
            boundary('spine_block_result',96,512,64,1,524.88,2),
            boundary('spine_stack_link',8,512,32,1,174.096,2)]
    dsseams=[boundary('root_activation',64,1632,49,32,86.4,2),
             boundary('root_return',64,69,64,1,33000/64,2)]
    # Keep ROM/config captures and each complete reduction root in a local clock domain.
    # This is preferable to arbitrarily bisecting a root's golden tree at die midline.
    qall=36*sum(kind in ('mv','attn') for _,kind,_ in Q.LAYER_STAGES)+1
    qb=U.qwen_product_ss()
    qbase_ns=qb['cycles']/FAST
    _,g=U._v41_graph(U.PRESETS['proposal'],1)
    variants=[]
    for name,hops,lat,ratio in [('registered_mesh',1,1,False),('gals_seams_d16',2,3,False),
                               ('gals_seams_d16_slow_sync',2,4,False),
                               ('gals_local_ratio_2_2',2,3,True)]:
        roundtrip_ns=2*hops*lat/FAST
        if ratio: roundtrip_ns+=2/SLOW+2/FAST
        qdelta=qall*roundtrip_ns
        geometry_debt_ns=432/FAST
        variants.append(dict(name=name,hops_per_direction=hops,cycles_per_hop=lat,
                             roundtrip_ns=roundtrip_ns,
                             qwen=dict(engine_invocations=qall,baseline_cycles=qb['cycles'],
                                       baseline_us=qbase_ns/1000,added_us=qdelta/1000,
                                       geometry_link_stage_debt_us=geometry_debt_ns/1000,
                                       total_added_with_geometry_debt_us=(qdelta+geometry_debt_ns)/1000,
                                       overlay_us=(qbase_ns+qdelta+geometry_debt_ns)/1000,
                                       rate_loss_fraction=(qdelta+geometry_debt_ns)/(qbase_ns+qdelta+geometry_debt_ns),
                                       formula='36*(4 weight + 2 attention) + head = 217 serialized engine invocations'),
                             ds_dag=dag_charge(g,roundtrip_ns-(2/SLOW+2/FAST) if ratio else roundtrip_ns)))
    # Related-domain saving alone is <1% (27d86); do not adopt it as a standalone lever.
    ratios=dict(fast_to_slow_cycles=2,slow_to_fast_cycles=2,
                fast_to_slow_ns=2/SLOW,slow_to_fast_ns=2/FAST,
                scope_note='Optional Qwen ratio row prices transport only, not full SU retiming to 0.9GHz; no split-clock token headline.',
                repeated_roundtrip_vs_old_4_5_saving_ns=2/SLOW+3/FAST,
                ds_rate_gain_in_source=cdc['token_price']['v41_case_b_gain_successor_vs_charged'],
                signoff_scope='W64 both directions; W512 fast->slow only, local related clocks; all other widths/context pending',
                prohibit='Never instantiate ratio FIFO across independent regional PLLs or arbitrary regional skew')
    # Area 823 is the user-provided current candidate envelope; dimensions remain source-pinned.
    # Do not infer a new shape from the area discrepancy or count existing CTS twice.
    par2=next(x for x in read('ds_par2.json')['candidates'] if x['id']=='C1_PP58_TP4_PAR2rows')
    qarea=823.0; dsarea=max(ds['area']['combined_noncontainment_policy_screen_mm2'],par2['physical']['per_die_screen_mm2'])
    for variant in variants:
        delta=variant['ds_dag']['matvec_nodes']*variant['ds_dag']['charged_ns_per_matvec']/1000
        variant['ds_retained_par2']={str(ctx):dict(baseline_us=row['path_T_us'],
            conservative_serial_added_us=delta,overlay_us=row['path_T_us']+delta,
            overlay_ar_tokens_s=1e6/(row['path_T_us']+delta),
            rate_loss_fraction=delta/(row['path_T_us']+delta),
            claim='Model sensitivity: all 407 DAG matvec crossings charged serially; original PAR2 links/hops retained; actual source exposed-call trace required')
            for ctx,row in par2['results'].items()}
    result=dict(schema='opentallas.rom.gals_mesh.model.v1',base_commit='79b3c5f84',
                status='MODEL_ONLY_IMPLEMENTATION_HANDOFF_NO_ADOPTION',input_pins=read('pins.json'),
                generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_rtl=False,pnr=False,
                inference=False,owner='Goodall 01a0fac5',reticle_mm2=858,
                related_cdc=ratios,
                geometry=dict(qwen=dict(die_um=[q['die']['w'],q['die']['h']],source_bbox_mm2=q['die']['mm2'],
                                        candidate_envelope_mm2=qarea,envelope_basis='owner request ~823, not reconciled physical union',
                                        midline_y_um=q['geometry']['mid'],spine_x_um=q['geometry']['x_spine'],
                                        spine_width_um=q['geometry']['spine_w'],columns=64,rows=24),
                              ds=dict(candidate=ds['candidate'],die_um=[33000,26000],PAR2_retained=True,
                                      area_policy_mm2=dsarea,parent_area_policy_mm2=ds['area']['combined_noncontainment_policy_screen_mm2'],fit_proven=False,roots=roots,
                                      coordinate_basis='DBU/1000, source field rectangles, no moved units')),
                seam_boundaries=dict(qwen=qseams,ds=dsseams),variants=variants,
                retained_ds_par2=dict(total_dies=par2['physical']['total_dies'],layer_dies=464,stages=58,PAR2=True,baseline=par2['results']),
                clock_mesh=dict(qwen=mesh(q['die']['w']/1000,q['die']['h']/1000,qarea,51.9),
                                ds=mesh(33,26,dsarea,51.9),
                                assumptions='Driver 0.5/1/2% area; clock loading 1.25/1.5/2 times assumed gated 51.9W. DS 51.9W is explicit sensitivity proxy, not measurement. C=.2pF/mm V=.7; shields 3um total; skew 80/40/20ps unmeasured. Existing local CTS not removed.'),
                local_clock_screens=dict(qwen_source=read('qwen_clock.json')['models'],
                                         qwen_four_quadrants='At SS 1.135ps/um and 2% OCV, 10x15.6mm quadrant root-leaf ~12.8mm gives ~581ps skew, still unqualified.',
                                         root_regions='Qwen 96 existing 4x4 tree blocks and DS 64 complete roots are refinement candidates, not clock closure.',
                                         require='Local clock load/SS setup/FF hold and real ROM clk-q before admitting any island; 60/25ps unchanged'),
                selected=dict(option='GALS elastic point-to-point seams, D16 async, local ratio only where proven',
                              default_off=True,why='Reuses existing interfaces/seams and finite FIFO discipline; no die-wide analog skew claim or golden reduction reorder.',
                              local_clock_qualification=False,physical_fit=False,fulltoken_rate=False,
                              adoption_gate='Not a >1% performance improvement: required feasibility repair. Explicit owner adoption decision after exact/context gates; no standalone ratio lever adopted.'),
                exclusions=['HBM accelerator study','DS return-storage resize','Qwen27B','ROM ECC','CPU inference'],
                model_dependencies_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in [ROOT/'tools/uarch_model.py',ROOT/'tools/arch_budget_qwen3.py',ROOT/'tools/arch_budget_v41.py',ROOT/'tools/decode_critical_path.py']})
    for name,seams,area in [('qwen',qseams,qarea),('ds',dsseams,dsarea)]:
        fifo_area=sum(s['reserved_core_mm2'] for s in seams)
        clock_roots=5 if name=='qwen' else 65
        root_area=clock_roots*.02
        root_power=clock_roots*.2
        result.setdefault('gals_cost',{})[name]=dict(fifos=sum(s['replicas'] for s in seams),
          incremental_fifo_area_mm2=fifo_area,active_fifo_power_proxy_w=sum(s['active_power_proxy_w'] for s in seams),
          regional_roots=clock_roots,incremental_root_reset_reserve_mm2=root_area,
          incremental_root_reset_power_w=root_power,
          total_incremental_area_mm2=fifo_area+root_area,
          total_incremental_power_proxy_w=sum(s['active_power_proxy_w'] for s in seams)+root_power,
          root_reserve_basis='ASSUMED 0.02mm2/0.2W per buffered root and reset/epoch control; existing local CTS retained, no new PLL credited',
          reticle_area_remaining_mm2=858-area-fifo_area-root_area,fit_proven=False,
          local_clock_refinement_sensitivity=[dict(roots=n,area_mm2=fifo_area+n*.02,power_proxy_w=sum(s['active_power_proxy_w'] for s in seams)+n*.2) for n in ([5,97,1537] if name=='qwen' else [65,2049])],
          memory_storage_bits=sum(s['storage_bits'] for s in seams),macs_per_cycle=0,
          compute_intensity_macs_per_byte=0,communication_intensity='transport only, one ordered word/port/cycle',
          critical_caveat='Existing topology may need extra local subdivisions; root/reset reserve is an assumption; finer partitions require additional crossings and a new composed price.')
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    d=build();args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=d['status'],gals_cost=d['gals_cost'],
                         prices=[dict(name=v['name'],qwen_added_us=v['qwen']['added_us'],
                                      ds_dag_added_us=v['ds_dag']['delta_us']) for v in d['variants']]),indent=2))
if __name__=='__main__':main()
