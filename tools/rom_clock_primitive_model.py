#!/usr/bin/env python3
"""Model-first refinement of f954ad1ea option C; three-FF safe fallback.
No unsynchronised steady pointer path or phase-safe bypass is implemented.
"""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def throughput(depth=4,cycles=5000):
    wp=rp=0;ws=[0]*3;rs=[0]*3;valid=False;n=0
    for i in range(cycles):
        oldw,oldr=wp,rp
        pop=valid
        if wp-rs[-1]<depth:wp+=1
        if pop:rp+=1;n+=i>cycles//2
        if not valid or pop:valid=ws[-1]>(oldr+int(pop))
        ws=[oldw]+ws[:-1];rs=[oldr]+rs[:-1]
    return n/(cycles-cycles//2-1)

def build(measurement=None):
    decision=json.loads(subprocess.check_output(['git','show','f954ad1ea:results/uarch/rom_die_clocking_decision_20261003.json']))
    d=dict(schema='opentallas.rom.clock_primitives.model.v1',decision_commit='f954ad1ea67f77e8f1a5e86cf48856a96ca650bf',
      decision_main='d99237f667bd526b787f993f009113ba3444c080',default_off=True,adoption=False,
      clocks=dict(period_ps=2500/3,setup_uncertainty_ps=60,hold_uncertainty_ps=25,region_max_mm=5.25),
      fifo=dict(W=512,depth=4,sync_stages=3,steady_pointer_sync=True,phase_window_bypass=False,
        latency_cycles_min=4,latency_cycles_max=5,increment_vs_registered_cycles=4,
        anticipated_saturated_words_per_cycle=throughput(),data_storage_bits=4*512,
        output_register_bits=512,read_mux_2to1=3*512,pointer_bits=3,
        sync_control_and_monitor_positive_reserve_bits=160,
        logical_flops_floor=4*512+512+160,
        logical_flop_area_floor_um2=(4*512+512+160)*.2916,
        area_floor_not_placement_fit=True,macs_per_cycle=0,bytes_per_cycle=64,bits_per_cycle=512,
        credit='read pointer advances only at consumer accept; output preload does not return credit',
        finite_flow='producer must honor w_rdy or reserve all pipeline completions before launch',
        drift='sticky coarse frequency/clock-loss monitor on 3FF synchronized Gray clock counters, +/-2 edges from RUN anchor; not phase/metastability qualification',
        protection='candidate flops; mutable-state protection inherited contract must be priced by integration owner'),
      forwarded=dict(max_span_um=430.56,capture_edge='falling',generated_clock_edges=[2,3,4],
        half_cycle_setup_budget_before_cell_delay_ps=2500/6-60,
        predicted_wire_ps_at_max_span=430.56*1.135,
        status='MAX_SPAN_NOT_QUALIFIED_FOR_HALF_CYCLE; reject a failing measured span, no period relaxation'),
      priced_cycles=dict(qwen=decision['recommendation']['price_to_model']['qwen']['bound_cycles'] if isinstance(decision.get('recommendation'),dict) else 2024,
        ds=2642,scope='latency-only four-extra-cycle fallback; depth4 throughput/issue stalls require measured separate pricing'),
      price_to_model_reference=decision['recommendation']['price_to_model'],status='MODEL_FIRST_CANDIDATE')
    if measurement is not None:
        m=json.loads(Path(measurement).read_text())
        assert m['status']=='PASS_DIGITAL_ONLY' and not m['metastability_proof']
        nominal=m['steady_sparse_latency_cycles']['max']
        wander=max(r['max_cycles'] for r in m['runs'] if r['mode']=='wander')
        delta=nominal-1
        d['measurement']=dict(source_sha256=hashlib.sha256(Path(measurement).read_bytes()).hexdigest(),
            accepted_words=m['accepted_words'],nominal_latency=m['steady_sparse_latency_cycles'],
            queued_wander_max_cycles=wander,phase_sync_fallback=True,
            saturated_words_per_cycle=m['stream_words_per_cycle'],
            payload_GB_s_range=[64*1.2*m['stream_words_per_cycle'][k] for k in ['min','max']],
            nominal_added_cycles=dict(qwen=506*delta,ds=661*delta),
            conservative_wander_added_cycles=dict(qwen=506*4.5,ds=661*4.5),
            same_clock_stream_rate_preserved=False,issue_stall_token_cost_priced=False,
            verdict='CANDIDATE_ONLY_NOT_LATENCY_CENTRAL_OR_FULL_RATE_GATE',
            scope='Latency terms use f954 model probes, not a new DS stage/die selection; integrators must price source-matched stalls.')
        d['status']='MEASURED_DIGITAL_PRICED_FALLBACK_NO_ADOPTION'
    return d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--measurement',type=Path);a=ap.parse_args();d=build(a.measurement);d['tool_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
if __name__=='__main__':main()
