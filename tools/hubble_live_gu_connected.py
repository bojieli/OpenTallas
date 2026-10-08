#!/usr/bin/env python3
"""Prepare/build/run ONE changed live TC->GU->SwiGLU->W2 component gate.

Preparation is software only. Build is a separate explicitly admitted action,
after the existing progressing SwiGLU build returns. No automatic replay.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_hubble_live_gu_swiglu_w2'
PRIVATE = ['rtl/test/hbm_accel/integrated_20261005/' + n for n in (
    'ot_hubble_live_gu_capture.sv', 'ot_hubble_live_gu_source_driver.sv', TOP + '.sv')]
EXPORT = 'rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv'
EXPORT_SHA = 'aa23ad3a1a9998fd9be6969b96f4de57eec0eae88bbd4cb7c930707ecdacf6bc'
METADATA = 'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv'
METADATA_SHA = '11ca2f3f6961e88b4af76ed48da67d9535c3a2688d633c3a9cff8be5a6391cfb'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sectors(source, destination):
    raw = source.read_bytes()
    if len(raw) % 32:
        raise ValueError('whole literal 32-byte sectors required')
    destination.write_text(''.join(f'{int.from_bytes(raw[i:i+32], "little"):064x}\n'
                                  for i in range(0, len(raw), 32)))


def prepare(enrollment, original_case, out):
    manifest = json.loads((enrollment / 'enrollment.json').read_text())
    if (manifest['status'] != 'PASS_SOFTWARE_IMAGE_ENROLLMENT'
            or manifest['total_GU_rows'] != 9216 or manifest['descriptor_count'] != 768
            or manifest['conversion_pc'] != 173 or manifest['kernel_words'] != 178):
        raise ValueError('completed full released-image enrollment required')
    if sha(ROOT / EXPORT) != EXPORT_SHA or sha(ROOT / METADATA) != METADATA_SHA:
        raise ValueError('selected Gibbs actual exporter changed')
    # Original case and actual router weights/limit remain from the measured
    # SwiGLU case; retained g/u inputs are omitted from selected live-GU reads.
    if not (original_case / 'producer/source_pin.json').is_file():
        raise ValueError('original real router/limit producer fixture required')
    shutil.copytree(original_case, out)
    target = out / 'live_gu';target.mkdir()
    (target / 'weights').mkdir()
    shutil.copyfile(enrollment / 'kernel.hex', target / 'kernel.hex')
    sectors(enrollment / 'activation_codes.u32', target / 'code_sectors.hex')
    sectors(enrollment / 'activation_exponents.u32', target / 'exponent_sectors.hex')
    descriptors = []
    for index, descriptor in enumerate(manifest['descriptors']):
        if descriptor['conversion_pc'] != 173 or descriptor['conversion_source_register'] != 3 or descriptor['valid_lanes'] != 12:
            raise ValueError('actual conversion enrollment changed')
        source = enrollment / descriptor['weight_image']
        if sha(source) != descriptor['weight_sha256']:
            raise ValueError('released weight image changed')
        sectors(source, target / 'weights' / f'span{index:03}.hex')
        descriptors.extend([descriptor['expert'], int(descriptor['matrix']=='w3'),
                            descriptor['row_start'],descriptor['source_sm'],
                            descriptor['die'],descriptor['w2_op']])
    (target / 'descriptors.hex').write_text(''.join(f'{v:08x}\n' for v in descriptors))
    expected = ''.join((enrollment / f'expert{expert}_{matrix}_expected_bf16.hex').read_text()
                       for expert in (41,65) for matrix in ('w1','w3'))
    (target / 'expected_bf16.hex').write_text(expected)  # comparison only
    pin = dict(scope='released TC producer inputs; comparator-only BF16',
               enrollment_sha256=sha(enrollment / 'enrollment.json'),
               exporter_sha256=EXPORT_SHA,
               metadata_sha256=METADATA_SHA,
               prepared_sha256={str(p.relative_to(target)):sha(p)
                                for p in target.rglob('*') if p.is_file()})
    (target / 'source_pin.json').write_text(json.dumps(pin, indent=2)+'\n')
    print('PREPARED_ONE_LIVE_GU_CONNECTED_CASE rows=9216 spans=768', flush=True)


def gu_dependencies():
    tree=ast.parse((ROOT/'tools/gpu_sys/run_system.py').read_text())
    dep=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='DEP_SRC' for t in n.targets))
    # The package and coded metadata module precede the selected SM.
    return list(dict.fromkeys(['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',METADATA,
        'rtl/gpu_sys/ot_gpu_simt_lane.sv',
        'rtl/gpu_sys/ot_gpu_simt_divlane.sv','rtl/gpu_sys/ot_gpu_bd_line.sv',EXPORT]+dep))


def build(work, case, base_job, jobs):
    # The prior job must have returned. A lost observer is never a terminal.
    if not (base_job/'terminal.exit').is_file():
        raise ValueError('preserve progressing original SwiGLU job; terminal required before changed build')
    if (base_job/'terminal.exit').read_text().strip()!='0':
        raise ValueError('first original numerical failure must be handled before changed gate')
    if 'PASS_LIVE_SWIGLU_W2_CONNECTED_PUBLICATION_CPL' not in (base_job/'build/runtime.log').read_text():
        raise ValueError('actual original live-SwiGLU numerical marker required')
    if not 1<=jobs<=4:
        raise ValueError('prepared four-worker CPU fit must cover the selected build')
    old = json.loads((base_job/'build/source_pin.json').read_text())
    paths = list(dict.fromkeys(list(old)+gu_dependencies()+PRIVATE))
    if sha(ROOT/EXPORT)!=EXPORT_SHA or sha(ROOT/METADATA)!=METADATA_SHA:
        raise ValueError('selected actual exporter pin changed')
    for name,digest in old.items():
        if sha(ROOT/name)!=digest:
            raise ValueError('same measured downstream source required: '+name)
    work.mkdir(parents=True,exist_ok=False)
    (work/'obj').mkdir()
    # Generic support objects have no generated-top ABI. Let generated make
    # validate normal dependencies; all generated root/engine objects differ.
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    cxx=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]
    prior_cxx=base_job/'cxx_toolchain.log'
    cxx_compatible=(not prior_cxx.is_file() or prior_cxx.read_text().strip()==cxx)
    reused=[]
    if (base_job/'toolchain.log').read_text().strip()==version and cxx_compatible:
        for name in ('verilated.o','verilated_threads.o','verilated_timing.o'):
            source=base_job/'build/obj'/name
            if source.is_file():
                shutil.copy2(source,work/'obj'/name);reused.append(name)
                dep=source.with_suffix('.d')
                if dep.is_file():shutil.copy2(dep,work/'obj'/dep.name)
    (work/'compatible_support_objects.json').write_text(json.dumps(reused,indent=2)+'\n')
    cmd=['verilator','--binary','--timing','-O2','-Wno-fatal',
         '-GLIVE_GU=1','-GLIVE_SWIGLU=1','--top-module',TOP,
         '--Mdir',str(work/'obj'),'-j',str(jobs),'-I'+str(case),
         *[str(ROOT/name) for name in paths]]
    (work/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    (work/'source_pin.json').write_text(json.dumps({n:sha(ROOT/n) for n in paths},indent=2)+'\n')
    with (work/'compile.log').open('w') as f:
        rc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    (work/'compile.exit').write_text(str(rc)+'\n')
    if rc:raise SystemExit(rc)


def run(work, case, original_prefix):
    if (work/'runtime.log').exists():
        raise ValueError('immutable first runtime; no retry/replay')
    pin=json.loads((case/'live_gu/source_pin.json').read_text())
    for n,h in pin['prepared_sha256'].items():
        if sha(case/'live_gu'/n)!=h:raise ValueError('changed live GU image '+n)
    for i in range(2):
        if not Path(f'{original_prefix}_d0_p{i}.hex').is_file():raise ValueError('original NS2 image absent')
    producer=json.loads((case/'producer/source_pin.json').read_text())
    for n,h in producer['prepared_sha256'].items():
        if sha(case/'producer'/n)!=h:raise ValueError('changed actual router/producer boundary '+n)
    cmd=[str(work/'obj'/('V'+TOP)),f'+DIR={case}',f'+LIVE_GU_DIR={case}/live_gu',
         f'+PRODUCER_DIR={case}/producer','+SWIGLU_LIMIT='+producer['limit_bits'],
         f'+gpu_sys_mem_prefix={original_prefix}',*(case/'args.txt').read_text().split()]
    (work/'runtime_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    with (work/'runtime.log').open('w') as f:rc=subprocess.run(cmd,cwd=case,stdout=f,stderr=subprocess.STDOUT).returncode
    (work/'runtime.exit').write_text(str(rc)+'\n')
    log=(work/'runtime.log').read_text()
    if rc or 'PASS_LIVE_TC_PROTECTED_GU_SWIGLU_W2_NATIVE_CPL' not in log or 'PASS_LIVE_TC_PROTECTED_GU_CAPTURE' not in log:
        raise SystemExit(rc or 1)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('step',choices=('prepare','build','run'))
    for name in ('enrollment','case','out','work','base-job','original-prefix'):p.add_argument('--'+name,type=Path)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args()
    if a.step=='prepare':prepare(a.enrollment,a.case,a.out)
    elif a.step=='build':build(a.work,a.case,a.base_job,a.jobs)
    else:run(a.work,a.case,a.original_prefix)
