"""One official-cell functional gate package. Preparation only; never launch."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_selector_mappedprimitive_gate_prepare_20261002'
LIB=ROOT/'results/rtl/dsrom_selector_allowed_cut_prepare_20261002/inputs'
LIB_NAMES=['asap7sc7p5t_SEQ_RVT_TT_220101.v','asap7sc7p5t_INVBUF_RVT_TT_201020.v','asap7sc7p5t_SIMPLE_RVT_TT_201020.v']
TEMPLATE='tools/rtl_templates/bench_dsrom_selector_mappedprimitive_prepare.sv'

def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')

def expected():
    # Independent scalar specification; no library UDP/backend code reused.
    steps=[dict(index=0,payload=0,flag=1,reset=1)]
    reset=1
    for i in range(32):
        if i in (8,24):reset=0
        if i in (12,25):reset=1
        steps.append(dict(index=i+1,payload=i&1,flag=reset*((i>>1)&1),reset=reset))
    order=['S0','A1','A2'];event=2
    for i in range(32):
        if i in (8,12,24,25):event+=1;order.append('A'+str(event))
        order.append('S'+str(i+1))
    order.append('A7')
    return dict(steps=steps,marker_order=order,async_events=[dict(index=i+1,reset=x) for i,x in enumerate([0,1,0,1,0,1,0])],
                counts=dict(steps=33,async_events=7,assertions=252),
                mutants={
                    '1':dict(kind='PAYLOAD',phase='RISE',index=0,expected=0,actual=1,prefix_steps=0,prefix_async_events=0),
                    '2':dict(kind='FLAG',phase='ASYNC',index=1,expected=0,actual=1,prefix_steps=1,prefix_async_events=0),
                    '3':dict(kind='CONTROL',phase='RISE',index=2,expected=0,actual=1,prefix_steps=2,prefix_async_events=2)},
                assertions_only=True,expected_values_never_connected_to_DUT=True)

def prepare(out):
    if out.exists():raise ValueError('fresh primitive package required')
    model=json.loads((BASE/'component_model.json').read_text())
    pins=json.loads((BASE/'source_pins.json').read_text())
    for p,h in {**model['source_pins'],**pins}.items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError('component source pin changed: '+p)
    if model['compile_GO'] or model['physical_admitted']:raise ValueError('preparation does not carry GO')
    out.mkdir(parents=True);(out/'library').mkdir()
    for name in LIB_NAMES:(out/'library'/name).write_bytes((LIB/name).read_bytes())
    (out/'bench_dsrom_selector_mappedprimitive_prepare.sv').write_bytes((ROOT/TEMPLATE).read_bytes())
    (out/'inputs.mem').write_text(''.join(f'{i%4:08x}\n' for i in range(32)))
    write(out/'assertions.json',expected())
    write(out/'sourceplan.json',dict(component_model_sha256=sha((BASE/'component_model.json').read_bytes()),
        source_inventory=['bench_dsrom_selector_mappedprimitive_prepare.sv']+['library/'+n for n in LIB_NAMES],
        top='bench_dsrom_selector_mappedprimitive_prepare',profiles=[0,1,2,3],
        one_compile_runtime_MODE_selection=True,official_library_sources_byte_identical=True,
        immutable_input_only=True,expectations_assertions_only=True,minimum_functional_primitive_scope=True,
        fullshape_selector_and_transport_qualification=False,full_gate_fault_cases_retained=15,
        component_reset_and_freeclock_root_contract_explicit=True,ICG_added=False,
        backend_5_050_delayed_setuphold_outputs_supported_source_review=True,
        timing_violation_fourstate_or_metastability_credit=False,
        physical_admitted=False,integrated_parent_admitted=False,compile_GO=False))
    write(out/'artifact_manifest.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
