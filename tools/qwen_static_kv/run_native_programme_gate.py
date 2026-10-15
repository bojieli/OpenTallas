#!/usr/bin/env python3
"""Minimal source-bound component gate; never emits a production physical receipt."""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_static_kv.native_programme import ROOT, PRODUCER, WRITER, compile_programme
from qwen_static_schedule.calendar import sha, ScheduleError
from qwen_static_schedule.segments import MissingPhysicalProfile


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir',type=Path,required=True,help='fresh qwen_tp8_fulltoken_plan.py output')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.source_dir
    program=(source/'layer_candidate_program.hex').read_bytes()
    descriptors=(source/'layer_candidate_segments.hex').read_bytes()
    plan=json.loads((source/'token_source_plan.json').read_text())
    paths=[PRODUCER,WRITER,'rtl/qwen_split/qfd_kvn_static_transport.sv',
           'rtl/qwen_split/qfd_native59_compute_service.sv','rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv',
           'rtl/physical/ot_qkd_kv_static_writer_native.sv','rtl/lib/ot_rst_relay.sv']
    profile=dict(period_fs=833334,phase_fs=137000,segment_start_cycle=4,
                 word_producer_age_fs=4*833334,word_stride_fs=833334,stop_cycle=16,
                 source_sha256={p:sha(ROOT/p) for p in paths},
                 component_path_ages_fs=dict(formatter_to_writer=0,expectation_to_writer=100000,reset_release=4*833334))
    image=compile_programme(program,descriptors,plan,profile,1,component_test=True)
    (a.out/'component_profile.json').write_text(json.dumps(profile,indent=2)+'\n')
    (a.out/'component_image.json').write_text(json.dumps(image,indent=2)+'\n')
    (a.out/'boot.hex').write_text(''.join(w['data_hex']+'\n' for w in image['writes']))
    negative=[]
    def refuse(name,pbytes=program,dbytes=descriptors,contract=None,stage=1,component=True):
        try:compile_programme(pbytes,dbytes,plan,profile if contract is None else contract,stage,component_test=component)
        except (ScheduleError,MissingPhysicalProfile) as e:
            negative.append(dict(name=name,refused=True,error=str(e)));return
        raise AssertionError(name+' escaped')
    refuse('missing_production_physical_receipt',component=False)
    refuse('changed_programme',pbytes=program.replace(b'0',b'1',1))
    refuse('changed_descriptor',dbytes=descriptors.replace(b'0',b'1',1))
    refuse('embedding_stage_has_no_native_writer',stage=0)
    p=copy.deepcopy(profile);del p['component_path_ages_fs']['reset_release'];refuse('missing_reset_age',contract=p)
    p=copy.deepcopy(profile);p['component_path_ages_fs']['expectation_to_writer']=833334;refuse('unimplemented_expectation_relay',contract=p)
    p=copy.deepcopy(profile);p['word_stride_fs']+=1;refuse('unaligned_formatter_word',contract=p)
    p=copy.deepcopy(profile);p['scope']='controller';refuse('unsupported_controller_front_ring',contract=p)
    p=copy.deepcopy(profile);p['stop_cycle']=12;refuse('missing_writer_drain',contract=p)
    p=copy.deepcopy(profile);p['component_path_ages_fs']['reset_release']=10*833334;refuse('word_before_reset_release',contract=p)
    sources=[ROOT/'rtl/lib/ot_rst_relay.sv',ROOT/PRODUCER,ROOT/WRITER,
             ROOT/'rtl/physical/ot_qkd_kv_static_writer_native.sv',
             ROOT/'rtl/test/qwen_static_kv/tb_qkd_kv_native_programme.sv']
    runs=[];top='tb_qkd_kv_native_programme'
    for mut,bad in [(0,0),(1,0),(2,0),(3,0),(4,0),(0,1),(0,2),(0,3)]:
        name=f'm{mut}_b{bad}'
        binary=a.out/(name+'.sim')
        cmd=['iverilog','-g2012','-s',top,f'-P{top}.MUT={mut}',f'-P{top}.BAD={bad}','-o',str(binary.resolve())]+[str(p) for p in sources]
        result=subprocess.run(cmd,capture_output=True,text=True)
        (a.out/(name+'.compile.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('compile failed: '+name)
        result=subprocess.run(['vvp',str(binary.resolve())],cwd=a.out,capture_output=True,text=True)
        (a.out/(name+'.log')).write_text(result.stdout+result.stderr)
        print(result.stdout.strip(),flush=True)
        if result.returncode or not result.stdout.startswith('PASS '):raise RuntimeError('component gate failed: '+name)
        runs.append(dict(name=name,exit=result.returncode,log=name+'.log'))
        binary.unlink()
    report=dict(model_function='tools/uarch_model.py:qwen_native_kv_programme_candidate_model',schema='opentallas.qwen-native-kv-programme-component-gate.v1',status='PASS_COMPONENT_ONLY',
                source_program_sha256=image['source_program_sha256'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources+[Path(__file__),ROOT/'tools/qwen_static_kv/native_programme.py',ROOT/'tools/uarch_model.py']},
                compiler_negative_controls=negative,rtl_runs=runs,
                production_qualified=False,physical_qualified=False,full_token_qualified=False,
                limitation='Writer candidate only. Component timeline ages are explicit test inputs; missing production physical receipts are refused. No controller/front/ring schedule, native formatter execution, routed timing or token-rate credit.')
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])

if __name__=='__main__':main()
