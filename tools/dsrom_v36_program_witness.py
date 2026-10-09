#!/usr/bin/env python3
"""Decode existing real compiler emissions; never label them native production."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--compiler-source',type=Path,required=True);p.add_argument('--binding-inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    isa_path=a.compiler_source/'tools/hdc_isa_v41.py'
    spec=importlib.util.spec_from_file_location('v36_pinned_isa',isa_path);I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
    prepared=json.loads((a.fixture/'prepare_stage2_deep.json').read_text())
    assert prepared['order']=='deep' and prepared['compressor_ring_records']==8
    assert prepared['isa_squash_reissue_state_equals_clean_both_stages']
    consumers=[];programs=[]
    for stage in range(2):
        f=a.fixture/f'cfg_stage2_deep/prog_stage{stage:02d}.hex';lines=f.read_text().splitlines()
        assert all(len(line)==I.INSTR_BITS//4 for line in lines)
        for pc,line in enumerate(lines):
            d=I.decode(int(line,16));fields=(['me_d_obase'] if d['unit']==I.UNIT_ME else ['a_d','b_d','c_d','d_d','o_d'] if d['unit']==I.UNIT_SU else [])
            used={field:d[field] for field in fields if d[field] in (I.DYN['SLOTW8'],I.DYN['SLOTP8'])}
            if used:consumers.append(dict(stage=stage,PC=pc,unit=d['unit'],pred=d['pred'],selectors=used,
                literal_output_base=d['me_obase'] if d['unit']==I.UNIT_ME else d['o_base']))
        programs.append(dict(stage=stage,instructions=len(lines),file=str(f),sha256=sha(f)))
    assert any(25 in c['selectors'].values() for c in consumers)
    assert any(26 in c['selectors'].values() for c in consumers)
    offsets={f:list(I.LAYOUT[f]) for c in consumers for f in c['selectors']}
    binding=json.loads(a.binding_inventory.read_text())
    payload=dict(schema='opentallas.v36.real-compiler-ring8-witness.v1',
        status='PASS_COMPILER_EMISSION_WITNESS_ONLY',programs=programs,consumers=consumers,
        ISA=dict(bits=I.INSTR_BITS,profile='reduced',dyn_slots=dict(SLOTW8=25,SLOTP8=26),selector_fields=offsets),
        compiler=dict(layout='P.Layout(model, rollback_ring=True) via ORDER=deep',
            prepare_sha256=sha(a.fixture/'prepare_stage2_deep.json'),order='deep',ring_records=8,
            source_sha256={name:sha(a.compiler_source/('tools/'+name)) for name in ['hdc_isa_v41.py','hdc_program_v41.py','mtp_exact_wavefront2.py']},
            prepare_record_tool_sha256=prepared['input_sha256']['tools/mtp_exact_wavefront2.py'],
            prepared_source_is_not_assumed_equal_to_later_gate_tool=True),
        selected_native_candidate=dict(source_sha256=binding['observed_source_sha256'],
            static_sources_file=binding['static_selection']['sources_file'],
            literal_parameters=dict(NSLOT=1,FULL_SHAPE=0,INSTR_BITS=1536),
            parameter_scope='candidate reduced ISA matches explicit core defaults; no actual compiled native hierarchy',
            current_core_initializes_DYN25_26_at_NSLOT1=False,
            candidate_consumer_requires_qualified_targeted_port=True),
        storage=dict(reduced_record_elements=64,ring_records=8,
            payload_bytes_per_compressor=2048,delta_from_two_records_bytes_per_compressor=1536,
            original_prepare_delta_bytes_per_package=prepared['rollback_storage_delta_bytes_per_package'],
            fullshape_record_stride_bound=False),
        physical_context_bound=False,actual_native_compiled_provider=False,
        production_program_or_runtime_qualification=False,new_RTL=False,new_routes=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2)+'\n')
    print('V36_EMISSION_WITNESS PASS consumers='+str(len(consumers)))
if __name__=='__main__':main()
