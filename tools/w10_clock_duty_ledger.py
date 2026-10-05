#!/usr/bin/env python3
"""Measured retained-vector clock duty and fail-closed old-wire reconciliation."""
import argparse
import ast
import csv
from decimal import Decimal as D
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PREFIX='results/quality/w10_clock_duty_r1/'
POWER_PIN='873a813ff3bb5880da17af5351ece55120228479'
MODEL_PIN='d9a0bd99b'
PHYSICAL='results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5_artifacts/'


def blob(pin,path):
    return subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def inspect_trace(raw,groups):
    rows=list(csv.DictReader(io.StringIO(raw.decode())))
    assert len(rows)>1
    period=int(rows[1]['time_ps'])-int(rows[0]['time_ps'])
    assert period==1000, 'vector bench period only; never adopt as physical clock'
    for i,r in enumerate(rows):
        assert int(r['time_ps'])==500+i*period
        for e in groups:
            wake=int(bool(not int(r['rst_post']) or int(r[e+'_go_elem_pre']) or
                int(r[e+'_go_e_pre']) or int(r[e+'_busy_pre']) or int(r[e+'_drain_pre'])))
            assert wake==int(r[e+'_wake_post']), 'registered wake recurrence mismatch'
            assert int(r[e+'_leaf_mask']) in (0,255), 'leaf divergence'
            if i:assert int(r[e+'_leaf_mask'])==255*int(r[e+'_wake_pre']), 'ideal latch phase mismatch'
    result=[]
    for e in groups:
        edges=sum(int(r[e+'_leaf_mask'])==255 for r in rows)
        enabled=[int(r[e+'_leaf_mask'])==255 for r in rows]
        def intervals(target):
            out=[];start=None
            for i,on in enumerate(enabled+[not target]):
                if on==target and start is None:start=i
                if on!=target and start is not None:out.append([start,i-start]);start=None
            return out
        reset_edges=sum(not int(r['rst_pre']) for r in rows)
        run_edges=len(rows)-reset_edges
        run_on=sum(bool(int(r['rst_pre'])) and int(r[e+'_leaf_mask'])==255 for r in rows)
        result.append(dict(element=e,root_rising_edges=len(rows),root_active_fraction='1',
            each_of_eight_leaf_rising_edges=edges,leaf_fraction_exact=f'{edges}/{len(rows)}',
            leaf_active_fraction=str(D(edges)/D(len(rows))),reset_root_edges=reset_edges,
            reset_deasserted_leaf_fraction_exact=f'{run_on}/{run_edges}',
            enabled_intervals=intervals(True),stopped_intervals=intervals(False),
            wake_register_transitions=sum(int(rows[i][e+'_wake_post'])!=int(rows[i-1][e+'_wake_post']) for i in range(1,len(rows))),
            go_elem_edges=sum(int(r[e+'_go_elem_pre']) for r in rows),
            walker_busy_edges=sum(int(r[e+'_busy_pre']) for r in rows),
            drain_only_edges=sum(bool(int(r[e+'_drain_pre'])) and not int(r[e+'_busy_pre']) and not int(r[e+'_go_e_pre']) for r in rows),
            wake_recurrence_mismatches=0,ideal_latch_protocol_mismatches=0))
    return result


def reconcile(model,report):
    tree=ast.parse(model)
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAIR_W' for t in n.targets))
    pair={k.arg:ast.literal_eval(k.value) for k in node.value.keywords}
    clock=re.search(r'^Clock[ \t]+([\d.eE+-]+)[ \t]+([\d.eE+-]+)[ \t]+([\d.eE+-]+)[ \t]+([\d.eE+-]+)',report,re.M)
    assert clock
    internal,switch,leak,total=map(D,clock.groups())
    assert total==D('.0237') and internal==D('.0129') and switch==D('.0108')
    assert pair['clock_hz']==1.087e9 and pair['idle_ungated']==.0835 and pair['idle_icg']==.00022
    return dict(historical_pair_clock_floor_W=str(D(str(pair['idle_ungated']))-D(str(pair['idle_icg']))),
        historical_pair_clock_hz=pair['clock_hz'],historical_reference='TT0.7V; source model comment, not current operatingV',
        embedded_clock_tree=dict(internal_W=str(internal),switching_W=str(switch),leakage_W=str(leak),reported_total_W=str(total)),
        embedded_flop_clock_pins_W='0.0270',embedded_macro_clock_W='0.0327',
        accounting_location='pair_power.clock included in cons_power cats.field_clock_busy and v41_die_static_parts field.clock; do not add candidate total as delta',
        off_pair_wire_location='xnet_energy wire_j prices activation broadcast/partial return; it excludes within-pair clock tree and is a distinct scope',
        wire_only_baseline_fF=None,wire_only_baseline_W=None,old_clock_buffer_pin_baseline_fF=None,
        reason='Clock Switching category combines driven wire and pin switching; no wire-only RC split, same-context voltage/duty or matching fullgoal tree inventory exists in this receipt.',
        old_wire_baseline_reconciled=False,numerical_candidate_wire_delta_fF=None,
        endpoint_and_existing_ICG_delta='0 new instances by topology, NOT zero energy delta: changed load/slew must be recharacterized',
        replacement_rule='Replace matched old clock subtree with matched candidate subtree; retain macro/flop endpoints once and recharacterize affected loads. Baseline TT pair is not a current SS fullgoal subtractable wire charge.')


def build(directory):
    capture=json.loads((directory/'capture.json').read_text())
    for name in ('exact_r2.json','golden_n4_r1.json'):
        raw=(directory/name).read_bytes()
        original='/home/ubuntu/w10-w18-recovery/baseline_wake/'+name
        assert digest(raw)==capture['qualification_sha256'][original]
        qualification=json.loads(raw)
        for path,expected in qualification['source_sha256'].items():
            if path.startswith(('rtl/','physical/')):
                assert digest(blob('b046de7f0',path))==expected, 'retained RTL source drift'
            elif path.startswith('/'):
                # The isolated golden binding is included as lightweight evidence.
                assert digest((directory/'array_wake_binding.sv').read_bytes())==expected
    coeff_raw=blob(POWER_PIN,'results/quality/w16_w10_clock_power_20261001/coefficients.json')
    coeff=json.loads(coeff_raw)
    model_raw=blob(MODEL_PIN,'tools/uarch_model.py')
    physical_raw=blob(MODEL_PIN,PHYSICAL+'6_finish.rpt')
    records=[]
    for entry in capture['records']:
        packed=(directory/(entry['case']+'.csv.gz')).read_bytes();raw=gzip.decompress(packed)
        assert digest(raw)==entry['trace_sha256']
        groups=['dut'] if entry['case']=='exact' else ['e0','e1']
        measured=inspect_trace(raw,groups)
        fullcolumn=entry['case'].startswith('bf16_')
        for m in measured:
            m['candidate_3873_buffer_ledger_applies']=fullcolumn
            m['nine_group_projection']=[]
            if fullcolumn:
                for g in coeff['groups']:
                    on=m['root_rising_edges'] if g['clock_role']=='ungated_source' else m['each_of_eight_leaf_rising_edges']
                    m['nine_group_projection'].append(dict(group=g['group'],buffers=g['buffers'],active_cycles=on,
                        root_cycles=m['root_rising_edges'],activity_exact=f'{on}/{m["root_rising_edges"]}',
                        added_buffer_input_fF_cycles=str(D(g['added_buffer_input_C_fF'])*on),
                        candidate_guarded_wire_fF_cycles=str(D(g['guarded_candidate_wire_C_fF'])*on),
                        VDD_sampled_grid_cycle_equivalent_fJ=str(D(g['VDD_internal_edge_grid_energy_coefficient_fJ'])*on),
                        old_wire_fF_cycles=None,net_wire_delta_fF_cycles=None))
                m['ICG_output_wire_candidate_fF_cycles']=str(D('200')*D('.145426')*m['each_of_eight_leaf_rising_edges'])
                m['ICG_output_wire_guarded_candidate_fF_cycles']=str(2*D(m['ICG_output_wire_candidate_fF_cycles']))
                m['ICG_wire_scope']='Separate eight*25um candidate component; no baseline subtraction or actual route/ICG-energy acceptance.'
        records.append(dict(case=entry['case'],trace_sha256=entry['trace_sha256'],measured=measured,
            scope='Retained actual RTL/vector schedule; not a fulltoken duty or product activity policy',
            physical_shape_scope='N4/NB2/MTP6/BF16/XF8 column' if fullcolumn else 'Protocol-only: Q XF4 or reduced MTP1 exact-reset fixture; no XF8 column buffer projection'))
    return dict(schema='opentallas.w10.actual-vector-clock-duty.v1',verdict='PASS_RETAINED_VECTOR_DUTY_AND_BASELINE_ACCOUNTING_SCOPE',
        source_pins={'coefficients':dict(commit=POWER_PIN,sha256=digest(coeff_raw)),
            'unified_model':dict(commit=MODEL_PIN,path='tools/uarch_model.py',sha256=digest(model_raw)),
            'historical_route_report':dict(commit=MODEL_PIN,path=PHYSICAL+'6_finish.rpt',sha256=digest(physical_raw)),
            'capture_sha256':digest((directory/'capture.json').read_bytes())},
        protocol='wake[k] reset=1; else go || go_e || walk_busy || drain!=0 on root posedge; each ICG latches wake while root low',
        simulator_scope='Exact fixture independently retains eight latch states; fullgolden simulator folds identical leaf clocks, mapped source independently proves eight distinct FF/ICG. Ideal phase only, no CTS skew or gating timing proof.',
        trace_timebase_ps=1000,trace_timebase_scope='Testbench1ns only; physical target/uncertainty unchanged',
        energy_coefficient_scope='Rise-count times sampled rise+fall grid coefficient is a conditional cycle-equivalent accounting term, not measured supply energy or a peak waveform; terminal partial cycles/edge windows require actual waveform.',
        root_duty_scope='All observed cycles root toggles; no source-stop protocol present. Product whole-token root duty remains unbound.',
        operation_family_scope='All eight gates use the same wake; a Q op does not selectively stop BF16 leaves, nor vice versa. Operand switching and clock switching are distinct.',
        records=records,baseline_reconciliation=reconcile(model_raw.decode(),physical_raw.decode()),
        remaining=dict(full_token_clock_group_trace=None,operating_voltage_V=None,actual_slew_load=None,
            spatial_phase_and_PG_fit=None,total_added_power_W=None,peak_current_A=None,IR_drop_V=None),
        physical_admission=False,adopted=False,headline_changed=False,hardware_jobs_launched=0,RTL_rebuilt=False,
        next_gate='Bind product scheduling/root-stop scope and matching old RC/tree energy; legal spatial CTS/PG/phase and actualV/slew/load before interpolated energy/PDN current. No P&R until full fit.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,default=ROOT/PREFIX);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(a.inputs),indent=2,sort_keys=True)+'\n')
