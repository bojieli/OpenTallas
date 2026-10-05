#!/usr/bin/env python3
"""Prepare literal full-width four-state gate; never emit candidate RTL.

The candidate is an external, later Maxwell-priced source. Preparation is
allowed now; variant implementation and any run remain model-gated.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from qwen_rom_enabled_capture_cone import extract,TILE
ROOT=Path(__file__).resolve().parents[1]
BENCH='rtl/test/qwen_rom_capture/tb_qwen_rom_hold_capture_equivalence.sv'


def original_logic(raw):
    _,body,_=extract(raw)
    header='''module qwen_current_capture_logic #(
 parameter integer W=16,AW=24,TG=4,CODE_BANKS=5,MEM_EXTRA=1
)(input wire clk,rst_n,wrom_re,input wire [AW-1:0] wrom_addr,
 input wire [2*CODE_BANKS*266-1:0] rom_rd,
 output wire [2*W*8*TG/2-1:0] wrom_q,
 output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr);
'''
    return header.encode()+body+b'endmodule\n',body


def validate_model(record):
    if record.get('schema')!='opentallas.qwen-rom.direct-capture-control.v1':
        raise ValueError('Wrong Maxwell model schema')
    if not record['optin']['RTL_preparation_admitted'] or record['optin']['default']!=0:
        raise ValueError('Defaultoff Maxwell preparation admission absent')
    if record['selected_model_scenario']!='5banks_2columns_directcapture_16local32bitmask_chunks_perbank':
        raise ValueError('Unpriced control scenario')
    policy=record['signoff']
    if abs(policy['target_period_ps']-833.333333)>1e-6 or (policy['SS_setup_uncertainty_ps'],policy['FF_hold_uncertainty_ps'])!=(60,25):
        raise ValueError('Clock or uncertainty changed')
    inv=record['inventory']
    if (inv['ROM_macros'],inv['capture_FF_bits'],inv['after'],inv['new_mask_loads_per_leaf'])!=(10,2560,80,32):
        raise ValueError('Full cone/control dimensions differ')
    lat=record['latency']
    if lat['new_cycles']!=0 or lat['existing_MEM_EXTRA_cycles']!=1:
        raise ValueError('Current zero-added-cycle proposal not priced')
    bridge=lat['exact_same_program_55_reference']
    expected=json.loads((ROOT/'results/uarch/qwen_rom_hold_capture_proposal_20261002/Maxwell_handoff_r1.json').read_text())['same_program_55_bridge_reference']
    if bridge!=expected or bridge['selected_arithmetic_extra']!=55:
        raise ValueError('Whole same-program +55 bridge differs')
    for field in ['incremental_slot_policy_um2','positive_extra_route_clock_PG_policy_um2']:
        if record['area'].get(field,0)<=0:raise ValueError('Unpriced slot/clock/PG policy: '+field)
    if record['tile_PR_admitted'] or record['hardware_adoption']:
        raise ValueError('Source preparation cannot grant physical adoption')
    return True


def prepare(output,model_commit=None,model_path=None):
    if output.exists():raise ValueError('Refusing to overwrite readiness evidence')
    raw=(ROOT/TILE).read_bytes();cone,body=original_logic(raw)
    output.mkdir(parents=True);(output/'original_logic_cone.sv').write_bytes(cone)
    (output/'fourstate_bench.sv').write_bytes((ROOT/BENCH).read_bytes())
    reason='No committed Maxwell full-cost model supplied';model_ready=False;model_sha=None
    if bool(model_commit)!=bool(model_path):raise ValueError('Supply both committed model ref and path')
    if model_commit:
        commit=subprocess.check_output(['git','rev-parse',model_commit+'^{commit}'],cwd=ROOT,text=True).strip()
        model_raw=subprocess.check_output(['git','show',commit+':'+model_path],cwd=ROOT)
        (output/'Maxwell_model.json').write_bytes(model_raw);model_sha=hashlib.sha256(model_raw).hexdigest()
        try:
            model=json.loads(model_raw);validate_model(model)
            prefix=str(Path(model_path).parent)
            proof=json.loads(subprocess.check_output(['git','show',commit+':'+prefix+'/inputs/proof.json'],cwd=ROOT))
            macro_raw=subprocess.check_output(['git','show',commit+':'+prefix+'/inputs/ROM_macro.v'],cwd=ROOT)
            full_original=subprocess.check_output(['git','show',commit+':'+prefix+'/inputs/original_cone.v'],cwd=ROOT)
            if proof['source_sha256'][TILE]!=hashlib.sha256(raw).hexdigest() or macro_raw!=(ROOT/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v').read_bytes() or full_original!=extract(raw)[0]:
                raise ValueError('Maxwell proof/macro/cone source pins differ')
            for path,digest in model['source_sha256'].items():
                pinned=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
                if hashlib.sha256(pinned).hexdigest()!=digest:raise ValueError('Maxwell committed input hash differs')
            model_ready=True;reason='Committed Maxwell full-cone/control policy accepted for fixed source development only'
        except ValueError as e:reason=str(e)
    record=dict(schema='opentallas.qwen-rom-hold-capture-literal-gate-readiness.v1',
        status='READY_LITERAL_VARIANT_DEVELOPMENT' if model_ready else 'BLOCKED_MAXWELL_FULL_COST_MODEL',
        reason=reason,source_ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [TILE,BENCH,'tools/qwen_rom_hold_capture_gate_prepare.py']},
        verbatim_original_logic_sha256=hashlib.sha256(body).hexdigest(),
        prepared_original_cone_sha256=hashlib.sha256(cone).hexdigest(),
        full_geometry=dict(ROM_banks=5,columns=2,macro_output_bits=2660,captured_bits=2560,consumer_output_bits=512),
        model_commit=model_commit,model_path=model_path,model_sha256=model_sha,
        candidate_RTL_present=False,RTL_variant_implementation_admitted=model_ready,
        fourstate_simulation_launched=False,formal_equivalence_launched=False,PnR_allowed=False,
        future_candidate_interface='qwen_optin_capture_logic with ROM_HOLD_DIRECT_CAPTURE=0 by default, full same ports as original_logic_cone.sv; source extraction from the actual reviewed variant, not a substitute memory model.',
        future_command='iverilog -g2012 -s tb_qwen_rom_hold_capture_equivalence -o OUTPUT/bench.vvp OUTPUT/original_logic_cone.sv PRICED_LITERAL_CANDIDATE.sv OUTPUT/fourstate_bench.sv; vvp OUTPUT/bench.vvp',
        future_negative_controls=['Default accidentallyenabled: source/default-elaboration gate rejects.', 'Wrong metadata or same-edge response: comparison must reject.', 'CEidle output doesnot hold: source contract/proof must reject.'],
        scope='Literal current control/capture source with shared full-width CE-hold four-state response fixture. Tests only masked consumer/request interfaces, not raw unselected captures. Actual ROM array/weights/timing and connected engine are outside this gate.',
        current_jobs=[],second_position=False,adoption=False)
    (output/'readiness.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(record['status']);return record


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--model-commit');ap.add_argument('--model-path');a=ap.parse_args();prepare(a.output,a.model_commit,a.model_path);return 0


if __name__=='__main__':raise SystemExit(main())
