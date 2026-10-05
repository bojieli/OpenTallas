#!/usr/bin/env python3
"""HA5 price-first ledger and CPU analytical replay of pinned DSpark traces.

No checkpoint load, inference, golden generation, RTL or physical launch.
All rates are analytical hypotheses, excluded from measured composition.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import subprocess
from pathlib import Path

from hbm_accel_program import compile_program, merge_audit, selector_plan

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'results/rtl/hbm_accel_ha5_20261003/inputs'


def load_spec():
    spec = importlib.util.spec_from_file_location('ha5_d2_spec', INPUTS / 'speculation.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT, mod.REC_DIR = ROOT, INPUTS
    mod.COMPOSER = INPUTS / 'w19_hbm_token_compose_71b3ffc5.py'
    return mod


def dff_area():
    tree = ast.parse((ROOT / 'tools/uarch_model.py').read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'DFF_UM2' for t in n.targets))


def selector_cost(positions, replicas):
    if not 1 <= replicas <= positions <= 6:
        raise ValueError('require 1 <= replicas <= positions <= 6')
    # ot_coll_topk_merge kmem and imem: 96 ranks x 512 x (key32 + id32).
    bits = 96 * 512 * 64
    return dict(status='ESTIMATE: register-buffer lower bound; no adoption',
                positions=positions, replicas=replicas, macs_per_cycle=0,
                compute='exact radix select; HIST 1024 candidates/cycle, FILTER 256',
                candidate_storage_bits_per_replica=bits,
                candidate_storage_bytes_total=replicas * bits // 8,
                incremental_candidate_cell_area_mm2=(replicas-1)*bits*dff_area()/1e6,
                incremental_candidate_cell_area_mm2_96_dies=96*(replicas-1)*bits*dff_area()/1e6,
                placement_lower_bound_mm2_at_util_07=(replicas-1)*bits*dff_area()/1e6/0.7,
                load_port_bytes_per_cycle_per_replica=64,
                aggregate_load_bytes_per_cycle_if_independent=64*replicas,
                input_boundary_bits_per_cycle_if_independent=512*replicas,
                histogram_port_bytes_per_cycle_per_replica=1024*4,
                filter_port_bytes_per_cycle_per_replica=256*8,
                output_port_bytes_per_cycle_per_replica=256*4,
                minimum_load_cycles_per_position=bits//512,
                serial_load_cycles_all_positions=positions*bits//512,
                independent_load_cycles=math.ceil(positions/replicas)*bits//512,
                input_demux_destinations=replicas, output_mux_sources=replicas,
                command_fanout=replicas,
                mux_area_mm2=None, demux_area_mm2=None, logic_area_mm2=None,
                clocks_power_repeaters_area_mm2=None, die_fit=None,
                routing_tracks_required=None, channel_capacity=None,
                cdc_credit_wire_cycles=None,
                reason='independent inputs required; positions are distinct, no score broadcast reuse')


def shared_measurements():
    rec = json.loads((ROOT / 'results/rtl/w19_sm_real_ops.json').read_text())
    cases = [c for c in rec['cases']['ar'] if c['tag'].startswith('expert slot 6')]
    picked = [next(c for c in cases if c['tag'] == 'expert slot 6 '+mat) for mat in ('w1','w3','w2')]
    return dict(status='measured elements ONLY; actual system hide window PENDING',
                cases=[dict(tag=c['tag'], cycles=c['rtl']['cycles_start_to_done'],
                            ns_at_nominal_1p2GHz=c['rtl']['cycles_start_to_done']/1.2,
                            lines=c['rtl']['lines'], drain=c['rtl']['drain_last_line_to_last_result'],
                            exact=c['exact']) for c in picked],
                estimated_hide_window_us=10.6, system_measured_hide_window_us=None,
                model_stream_issue_plus_drain_cycles=(40+40+67)+(48+60),
                bytes_per_cycle_ports='existing SM ports; no added data boundary',
                measured_element_total_cycles=sum(c['rtl']['cycles_start_to_done'] for c in picked),
                measured_element_total_ns_at_nominal_1p2GHz=sum(c['rtl']['cycles_start_to_done'] for c in picked)/1.2,
                additional_buffer_bytes=0, additional_replica_count=0,
                shared_ea_existing_bytes_per_position=2304*2,
                earlier_buffer_lifetime='shared ea remains live until unchanged combined gather',
                w2='still waits for combined expert_intermediate_gather',
                wire_cdc_credit_refresh_overlap_measured=False)


def compose_rows():
    mod = load_spec()
    w = mod.W19()
    union = json.loads((INPUTS / 'router_union.json').read_text())
    taus = json.loads((INPUTS / 'tau_by_gamma.json').read_text())
    draft = w.draft(union['drafter']['union_per_stage'])
    reproduction = dict(ar_us=w.run(w.prog_ctx(1048576))['total_us'],
                        verify_us=w.run(w.prog_ctx(1048576),6,w.w19_union)['total_us'])
    if abs(reproduction['ar_us']-442.14) > .01 or abs(reproduction['verify_us']-715.82) > .01:
        raise ValueError('pinned d2 replay drift: '+str(reproduction))
    rows = []
    for ctx in (1048576,200000):
        base = w.prog_ctx(ctx)
        accel = compile_program(base, shared_first=True)
        ar = w.run(base)
        candidate_ar = w.run(accel)
        for gamma in range(1,6):
            p = gamma+1
            unions = {l: union['union_by_p'][str(p)]['per_layer'][l] for l in range(40)}
            baseline = w.run(base,p,unions)
            scheduled = w.run(accel,p,unions)
            for name, tg in taus['sets'].items():
                tau = tg[str(gamma)]['tau']
                for replicas in (1,p):
                    # Upper bound ONLY: gathered candidates magically independently
                    # loaded; omit the saving from measured composition until actual
                    # ports, wires, credits and CDC are qualified.
                    nsel = sum(o['kind']=='topk_merge' and o.get('what')=='sel'
                               for layer in accel['layers'] for o in layer['ops'])
                    upper_us = nsel*(p-math.ceil(p/replicas))*w.coll['select_cycles']/w.coll['hz']*1e6
                    step = scheduled['total_us']+draft['total_us']
                    rows.append(dict(context=ctx, gamma=gamma, positions=p, replicas=replicas,
                                     tau_set=name, tau=tau, baseline_ar_us=ar['total_us'],
                                     serial_scheduled_ar_us=candidate_ar['total_us'],
                                     baseline_verify_us=baseline['total_us'],
                                     serial_scheduled_verify_us=scheduled['total_us'],
                                     draft_us=draft['total_us'], serial_step_us=round(step,2),
                                     analytical_serial_tokens_s=round(tau*1e6/step,1),
                                     selector_ideal_saving_upper_us=round(upper_us,3),
                                     analytical_ideal_tokens_s=round(tau*1e6/(step-upper_us),1),
                                     system_measured_tokens_s=None, adopted=False))
    return dict(reproduction=reproduction, draft=draft, rows=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    source = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    prog = json.loads((ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json').read_text())
    run = json.loads((ROOT/'results/rtl/w19_hbm_tp96_isa_oreduce.json').read_text())['runs']['oreduce:L0-39:head']
    paths = [p for p in INPUTS.iterdir() if p.is_file()] + [ROOT/'tools/uarch_model.py', ROOT/'tools/w19_hbm_tp96_isa.py',
             ROOT/'tools/hbm_accel_program.py', Path(__file__)]
    paths += [ROOT/p for p in load_spec().W19_INPUTS.values() if isinstance(p,str)]
    paths += [ROOT/p for p in load_spec().W19_INPUTS['sm']]
    record = dict(schema='opentallas.hbm-accel-ha5.v1', run_pid=os.getpid(),
                  host=os.uname().nodename, source_commit=source,
                  status='UNVALIDATED analytical compiler milestone; NOT ADOPTED',
                  input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  exact=dict(verdict='PENDING actual changed-program RTL layer/head gate',
                             cases=None,mismatches=None,
                             historical_original_head=run['result']['head'],
                             historical_original_context=run['result']['context']),
                  measurements=shared_measurements(),
                  selector_costs=[selector_cost(p,r) for p in range(2,7) for r in (1,p)],
                  merges=merge_audit(prog), selector_plan=selector_plan(prog,6,6),
                  gates=dict(exact='PENDING',serial_latency='PENDING',area='ESTIMATE incomplete',
                             routed_corridor='NOT RUN',timing='NOT RUN',composed_gain='PENDING'),
                  ss_wns_ns=None,ff_wns_ns=None,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                  measured_composition=dict(included_ha5_rungs=[],gain_us=0,new_rate=None),
                  analytical=compose_rows(),adopt=False,
                  peer_reuse=dict(ds20_union_commit='15a1d3749',
                                 gate='width/union replay only; full numerical engine pending',
                                 checkpoint='Kepler owns existing PC0 checkpoint; no restore/run here'))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(source_commit=source,run_pid=record['run_pid'],adopt=False,
                          reproduction=record['analytical']['reproduction'],
                          gamma_rows=len(record['analytical']['rows']))))


if __name__ == '__main__':
    main()
