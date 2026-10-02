"""Verify immutable parent-owned D1 compile/runtime FAIL receipts, offline only."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'results/uarch/w17_D1_callback_terminal_archive_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def review(rec=REC,source_root=ROOT):
    m=json.loads((rec/'archive_manifest.json').read_text())
    if m['source_commit']!='2512aabf75df475ced8ce6ff13f0fe0e239a78e3' or m['engine_source_pin']!='4e38326d6f361bc85e660f48c59c355e2bb95274':raise ValueError('source identity')
    raw=rec/'raw'
    for name,row in m['files'].items():
        p=(raw/name).resolve()
        if not p.is_relative_to(raw.resolve()) or not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('raw archive drift '+name)
    obj=lambda n:json.loads((raw/n).read_text())
    record=obj('record.json');failure=obj('first_failure_stage.json');snapshot=obj('source_snapshot.json')
    planpath=source_root/'results/uarch/w17_D1_frozen_observer_20261002/plan.json';plan=json.loads(planpath.read_text())
    if snapshot['commit']!=m['source_commit'] or snapshot['plan_sha256']!=sha(planpath) or snapshot['files_sha256']!=plan['files_sha256']:raise ValueError('compiled source/plan snapshot')
    for p,h in snapshot['files_sha256'].items():
        if sha(source_root/p)!=h:raise ValueError('compiled source input drift '+p)
    steps=record['steps']
    if len(steps)!=1 or steps[0]['returncode']!=0 or steps[0]['log_sha256']!=sha(raw/'compile.log'):raise ValueError('actual compile receipt')
    cmd=steps[0]['command'];origin=m['files']['record.json']['original_path'].rsplit('/',1)[0]
    inputs=next(x.split('/rtl/test/',1)[0] for x in cmd if '/rtl/test/' in x and x.endswith(('.v','.sv')))
    old=inputs+'/rtl/test/w17_owner_progress_watchdog';new=inputs+'/rtl/test/w17_D1_frozen_observer'
    expected=[plan['compiler']['path']]+plan['options']+['--Mdir',origin+'/obj','-I'+old+'/pinned/rtl/hdc/v41','-CFLAGS','-I'+old]+[inputs+'/'+p for p in plan['sources']]+[old+'/owner_progress_exports.sv',new+'/source_observer.sv',new+'/tb_D1.sv',old+'/observer_dpi.cpp']
    if cmd!=expected:raise ValueError('compile command differs from frozen plan')
    if obj('compiler_receipt.json')!=plan['compiler']:raise ValueError('compiler metadata binding')
    caps=obj('caps_before_compile.json')
    if caps['memory_max']!='12884901888' or caps['swap_max']!='0' or caps['affinity']!=[0,1]:raise ValueError('resource caps')
    if record['verdict']!='FAIL_PRESERVED_NO_RETRY' or not record['no_retry'] or failure['predicate']!='stage_time_cap':raise ValueError('terminal verdict/cause')
    if failure['command']!=[origin+'/obj/Vtb_D1','+CASE=HEALTHY'] or failure['wall_seconds']<20 or obj('active_stage.json')['seconds']!=20:raise ValueError('first runtime capped command')
    if obj('first_failure.json')['error']!="RuntimeError('stage_time_cap; no retry')":raise ValueError('first failure changed')
    if (raw/'HEALTHY.log').stat().st_size!=0 or any((raw/(n+'.log')).exists() for n in ['HOLD_REQ','HOLD_RSP','OVERALL','WRITER']):raise ValueError('event/case coverage changed; requires separate review')
    for key in ['core_four_bits_executed','original_progress_inferred','PHY_qualified','fulltoken']:
        if record[key] is not False:raise ValueError('unsupported qualification '+key)
    terminal=dict(line.split('=',1) for line in (rec/'fresh_unit_terminal.txt').read_text().splitlines())
    if terminal!=m['fresh_independent_poll'] or terminal.get('MainPID')!='0':raise ValueError('unit terminal evidence')
    text=(raw/'compile.log').read_text();report=re.search(r'Walltime ([0-9.]+) s \(elab=([0-9.]+), cvt=([0-9.]+), bld=([0-9.]+)\); cpu ([0-9.]+) s on (\d+) threads; allocated ([0-9.]+) MB',text)
    if not report:raise ValueError('frontend/CXX phase report absent')
    fields=report.groups()
    return dict(verdict='VERIFIED_ACTUAL_FIXTURE_COMPILE_PASS_FIRST_RUNTIME_CAP_FAIL',source_commit=m['source_commit'],source_files_verified=len(snapshot['files_sha256']),compile_returncode=0,compile_wall_seconds=steps[0]['wall_seconds'],frontend_report=dict(wall_seconds=float(fields[0]),elaboration_seconds=float(fields[1]),conversion_seconds=float(fields[2]),build_seconds=float(fields[3]),cpu_seconds=float(fields[4]),threads=int(fields[5]),allocated_MB_internal=float(fields[6]),kernel_RSS_peak=None),runtime_case='HEALTHY',runtime_cap_seconds=20,first_failure_wall_seconds=failure['wall_seconds'],retained_HEALTHY_bytes=0,retained_callback_events=0,actual_internal_callback_counts=None,actual_runtime_phase=None,stdout_buffering_loss_not_excluded=True,unrun_cases=['HOLD_REQ','HOLD_RSP','OVERALL','WRITER'],binary_receipt=obj('binary_receipt.json'),binary_executed_by_collector=False,original_full_L0_restarted=False,callback_qualification=False,whole_token=False,core_four_bits=False,PHY_qualification=False,service_status='BOUND_MISSING',no_retry=True,output_peak_bytes=record['output_peak_bytes'],fresh_unit_terminal=terminal)
if __name__=='__main__':print(json.dumps(review(),indent=2))
