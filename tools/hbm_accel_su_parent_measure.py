#!/usr/bin/env python3
"""Minimum changed CP/provider join: original native then finite fused HCpost.

One source/binary, same installed CDC/backend classes and input images. Reuses
the accepted original program and existing compiler fixture. No golden or
family campaign, no full cluster elaboration, no physical qualification.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import dsrom_su_norm as S


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args()
    plan=json.loads((a.fixture/'parent_fixture.json').read_text())
    if plan['original_program_sha256']!='0cfed448f54896266ce57d3a94826e4044cf47f8b09a22419fe16eb5e5a180d7':
        raise ValueError('exact archived native program required')
    for name,pin in plan['files_sha256'].items():
        if sha(a.fixture/name)!=pin:raise ValueError('source fixture changed: '+name)
    a.work.mkdir(parents=True,exist_ok=False)
    fixture=a.work/'fixture';shutil.copytree(a.fixture,fixture)
    native='rtl/hbm_accel/su/pinned_native/'
    pins={'ot_hdc_v41x_vec_lane_f12.sv':'50d0d7c6488ec8a6803ca285d20ee93897bb1fc49c039c888296e5315fe73092',
          'ot_hdc_v41x_sfu_f12.sv':'20f41640e1963cc85072f1a622120e1efd983312bf551f35f9eafe9f7ff3b6fb'}
    for name,pin in pins.items():
        if sha(S.ROOT/native/name)!=pin:raise ValueError('pinned original native source differs')
    common=[native+'ot_hdc_v41x_sfu_f12.sv' if p=='rtl/hdc/v41x/ot_hdc_v41x_sfu.sv' else p for p in S.COMMON]
    paths=common+S.FP_SRC['dpi']+[
        native+'ot_hdc_v41x_vec_lane_f12.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv','rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
        'rtl/hdc/v41x/ot_dsrom_su_norm.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/v41x/ot_dsrom_su_swiglu.sv',
        'rtl/hdc/ot_hdc_cg.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
        'rtl/hbm_accel/su/ot_hbm_accel_su_fused_stream.sv','rtl/hbm_accel/su/ot_hbm_accel_su_fused_vm.sv',
        'rtl/hbm_accel/su/ot_hbm_accel_su_parent_borrow.sv','rtl/hbm_accel/su/ot_hbm_accel_su_parent_exec.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20_su.sv',
        'rtl/link/ot_link_afifo.sv','rtl/gpu_sys/ot_gpu_cdc_fifo.sv','rtl/gpu_sys/ot_gpu_mreq_cdc.sv',
        'rtl/gpu_sys/ot_gpu_xbar.sv','rtl/gpu_sys/ot_gpu_l2_slice.sv','rtl/gpu_sys/ot_gpu_hbm_partition.sv',
        'rtl/gpu_sys/ot_gpu_memsys.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/test/tb_hbm_accel_su_parent.sv']
    paths=list(dict.fromkeys(paths));src=[S.ROOT/p for p in paths]
    obj=a.work.resolve()/'obj'
    cmd=[S.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH',
         '--top-module','tb_hbm_accel_su_parent','-Mdir',str(obj),'-j','16',
         '--unroll-count','4','-fno-dfg','-I'+str(S.ROOT/'rtl/test'),*map(str,src),'-CFLAGS','-O1']
    model_path=S.ROOT/'results/rtl/hbm_su_fused_20261005/finite_native_parent_model.json'
    model=json.loads(model_path.read_text())
    if not model['component_RTL_implementation_permitted']:raise ValueError('actual registered model required')
    record=dict(command=cmd,source_sha256={p:sha(S.ROOT/p) for p in paths},
                include_sha256={'rtl/test/tb_hdc_v41x_vec_fields.svh':sha(S.ROOT/'rtl/test/tb_hdc_v41x_vec_fields.svh')},
                fixture=plan,model_sha256=sha(model_path),model=model,
                construction_inventory=json.loads((S.ROOT/'results/uarch/hbm_su_parent_join_20261005/construction_inventory.json').read_text()),
                scope='production owner/exec + original CP and actual NC4/AW3/NS2/NPC2/defaultW2 backend minimum cut; SM arithmetic outside cut',
                SU_clock_resolved_ns=.833334,mem_clock_ns=1,
                target_clock_qualified=False,full_cluster_elaborated=False,
                CP_no_RESULT_status=2,adopted=False)
    (a.work/'source.json').write_text(json.dumps(record,indent=2)+'\n')
    with (a.work/'build.log').open('w') as log:
        r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    (a.work/'build.rc').write_text(str(r.returncode)+'\n')
    if r.returncode:return r.returncode
    exe=obj/'Vtb_hbm_accel_su_parent';rows=[]
    for name,args in [('original_native',['+MODE=0']),('finite_fused',['+MODE=1']),
                      ('foreign_prior_tag',['+MODE=0','+FOREIGN=1'])]:
        with (a.work/(name+'.log')).open('w') as log:
            r=subprocess.run([str(exe),*args],cwd=fixture,stdout=log,stderr=subprocess.STDOUT)
        (a.work/(name+'.rc')).write_text(str(r.returncode)+'\n')
        lines=(a.work/(name+'.log')).read_text().splitlines()
        ends=[s for s in lines if s.startswith('PARENT_END ')]
        metrics={k:float(v) if '.' in v else int(v) for k,v in
                 (s.split('=') for s in ends[-1].split()[1:])} if ends else None
        good=r.returncode==0 and ('PASS' in lines if metrics else any(s.startswith('PARENT_FOREIGN_PASS ') for s in lines))
        rows.append(dict(name=name,rc=r.returncode,pass_exact=good,metrics=metrics))
        if not good:break
    base=next((x['metrics'] for x in rows if x['name']=='original_native' and x['pass_exact']),None)
    fused=next((x['metrics'] for x in rows if x['name']=='finite_fused' and x['pass_exact']),None)
    exact=len(rows)==3 and all(x['pass_exact'] for x in rows)
    slower=bool(base and fused and fused['elapsed_us']>=base['elapsed_us'])
    result=dict(source=record,binary_sha256=sha(exe),terminal=True,runs=rows,pass_exact=exact,
                native_us=base['elapsed_us'] if base else None,fused_us=fused['elapsed_us'] if fused else None,
                candidate_rejected_slower_or_inexact=slower or not exact,
                component_saving_us=(base['elapsed_us']-fused['elapsed_us']) if base and fused else None,
                composed_token_gain_us=None,SS60_FF25_qualified=False,adopted=False)
    (a.work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if exact else 1


if __name__=='__main__':raise SystemExit(main())
