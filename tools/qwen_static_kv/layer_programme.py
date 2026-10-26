#!/usr/bin/env python3
"""Source-pinned compiler for the actual all36 layer-control root hardware.

The assembler emits boot words, not results. Production compilation requires
actual ISA/source-plan bytes and all36 measured path profiles. Component images
remain noninstallable; missing native/physical data is never defaulted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_programme import source_contract
from qwen_static_schedule.calendar import ScheduleError,pins

RTL='rtl/qwen_sys/static_kv_20261014/qkd_static_kv_layer_programme.sv'
FIELDS=('ctrl_go','kgo','vgo','attention_issue','attention_run','writer_start','link_start','expected_quiet','stage_end')
PATHS=('controller_launch','landing_calendar_launch','front_calendar_launch','k_issuer_launch',
       'attention_issue','attention_run','writer_programme_launch','link_calendar_launch')
FOOTER=0x514b564c59523336


def assemble_rows(rows,programme_digest,programme_epoch):
    if len(rows)!=36 or [r.get('stage') for r in rows]!=list(range(1,37)):
        raise ScheduleError('exactly all36 ordered stage rows required')
    if type(programme_digest)is not int or not 0<=programme_digest<2**64:
        raise ScheduleError('explicit authorized programme digest64 required')
    if type(programme_epoch)is not int or not 0<=programme_epoch<2**16:
        raise ScheduleError('explicit authorized programme epoch16 required')
    words=[];total=0;events=[]
    for row in rows:
        roots=row.get('roots',{})
        if set(roots)!=set(FIELDS) or any(type(v)is not int or not 0<=v<2**32 for v in roots.values()):
            raise ScheduleError('every actual root must be an explicit cycle32: stage '+str(row.get('stage')))
        end=roots['stage_end']
        if any(not 3<=roots[n]<end for n in FIELDS[:-1]):raise ScheduleError('root outside its implemented stage frame')
        if roots['attention_run']<roots['attention_issue']+4:raise ScheduleError('attention programme guard/load latency missing')
        if roots['expected_quiet']<=max(roots[n] for n in FIELDS[:7]):raise ScheduleError('quiet expectation precedes last control launch')
        words.extend(roots[n] for n in FIELDS)
        for n in FIELDS:events.append(dict(stage=row['stage'],kind=n,stage_cycle=roots[n],token_cycle=total+roots[n]))
        total+=end
        if total>=2**32:raise ScheduleError('all36 token cycle counter overflows')
    words += [programme_digest,programme_epoch,FOOTER]
    return dict(words=words,events=events,stage_count=36,token_core_cycles=total,
                root_pin_age_from_external_start=1,full_native_qualified=False)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_image(programme,descriptors,source_plan,profiles,programme_digest,programme_epoch,*,component_test=False):
    if profiles.get('schema')!='opentallas.qwen_kv_static.layer_roots.v1':raise ScheduleError('unsupported layer-control profile schema')
    rows=profiles.get('stages',[])
    image=assemble_rows(rows,programme_digest,programme_epoch)
    clocks={(r.get('period_fs'),r.get('phase_fs'))for r in rows}
    if len(clocks)!=1 or any(type(p)is not int or type(q)is not int or p<=0 or not 0<=q<p for p,q in clocks):
        raise ScheduleError('explicit consistent actual core period/phase required for every stage')
    module_pins={RTL:sha(ROOT/RTL),'tools/qwen_static_kv/layer_programme.py':sha(Path(__file__))}
    for row in rows:
        source_contract(programme,descriptors,source_plan,row['stage'])
        rowpins=row.get('source_sha256',{})
        pins(ROOT,rowpins)
        if any(rowpins.get(k)!=v for k,v in module_pins.items()):raise ScheduleError('actual control RTL/compiler source pins missing or stale')
        if component_test:continue
        if row.get('physical_profile_status')!='MEASURED':raise ScheduleError('actual measured control paths required')
        rp=Path(row.get('receipt_path',''))
        if rp.is_absolute() or '..' in rp.parts:raise ScheduleError('repository receipt path required')
        receipt_path=ROOT/rp
        if not receipt_path.is_file() or sha(receipt_path)!=row.get('receipt_sha256'):
            raise ScheduleError('actual source-bound path receipt missing or stale')
        receipt=json.loads(receipt_path.read_text())
        if (receipt.get('status')!='QUALIFIED' or receipt.get('scope')!='full_static_KV_control_paths' or
            receipt.get('stage')!=row['stage'] or receipt.get('roots')!=row['roots'] or
            receipt.get('period_fs')!=row['period_fs'] or receipt.get('phase_fs')!=row['phase_fs'] or
            receipt.get('programme_sha256')!=hashlib.sha256(programme).hexdigest() or receipt.get('source_sha256')!=rowpins):
            raise ScheduleError('actual programme/roots/source/path receipt mismatch')
        for name in PATHS:
            path=receipt.get('qualified_paths',{}).get(name,{})
            if path.get('status')!='QUALIFIED' or type(path.get('age_core_edges'))is not int or path['age_core_edges']<0:
                raise ScheduleError('missing implemented compiler path age: '+name)
            ep=Path(path.get('evidence_path',''))
            if ep.is_absolute() or '..' in ep.parts or not (ROOT/ep).is_file() or sha(ROOT/ep)!=path.get('evidence_sha256'):
                raise ScheduleError('actual path proof missing or changed: '+name)
            evidence=json.loads((ROOT/ep).read_text())
            if (evidence.get('source_sha256')!=rowpins or evidence.get('native_exact')is not True or
                evidence.get('mutant_failed')is not True or type(evidence.get('tt_setup_ps'))not in (int,float) or
                type(evidence.get('ff_hold_ps'))not in (int,float) or evidence['tt_setup_ps']<0 or evidence['ff_hold_ps']<0 or evidence.get('drc')!=0):
                raise ScheduleError('actual native/TT/FF/DRC path proof incomplete: '+name)
    image.update(schema='opentallas.qwen_kv_static.layer_programme.v1',installable=False,
                 status='COMPONENT_TEST_NOT_PRODUCTION_INSTALLABLE' if component_test else 'SOURCE_AND_PATH_PROFILE_BOUND_NATIVE_COMPOSITION_WITNESS_REQUIRED',
                 source_and_path_profiles_bound=not component_test,requires_native_composition_witness=True,
                 component_test=component_test,full_native_qualified=False,
                 programme_sha256=hashlib.sha256(programme).hexdigest(),descriptors_sha256=hashlib.sha256(descriptors).hexdigest(),
                 source_sha256=module_pins,source_plan_sha256=hashlib.sha256(json.dumps(source_plan,sort_keys=True).encode()).hexdigest(),profiles=profiles,
                 qualification='Boot/control path evidence only; full native die and whole programme proof remain separate.')
    return image


def main():
    ap=argparse.ArgumentParser()
    for name in ('program','descriptors','plan','profiles','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--programme-digest',type=lambda s:int(s,0),required=True);ap.add_argument('--programme-epoch',type=int,required=True)
    ap.add_argument('--component-test',action='store_true');a=ap.parse_args()
    try:
        image=compile_image(a.program.read_bytes(),a.descriptors.read_bytes(),json.loads(a.plan.read_text()),
            json.loads(a.profiles.read_text()),a.programme_digest,a.programme_epoch,component_test=a.component_test)
    except (ScheduleError,KeyError,ValueError,OSError) as e:
        print(json.dumps(dict(status='REFUSED_INVALID_OR_MISSING_ACTUAL_SOURCE_PROFILE',error=str(e),installable=False)))
        return 2
    if a.out.exists() and any(a.out.iterdir()):raise SystemExit('use a fresh output directory for source-pinned boot artifacts')
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'boot.hex').write_text(''.join(f'{v:016x}\n'for v in image['words']))
    (a.out/'image.json').write_text(json.dumps(image,indent=2)+'\n')
    return 0
if __name__=='__main__':sys.exit(main())
