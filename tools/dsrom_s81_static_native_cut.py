#!/usr/bin/env python3
"""Select/build ONLY the frozen native source cut with immutable controls.

Opt-in: no model regeneration, new scheduling, field array or runtime execution.
The reference archive's exact cut parameters/public namespace remain authoritative.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / 'tools/runtime/dsrom'
CATALOG = 'results/rtl/dsrom_recovery_20261004/immutable_fullcatalog/manifest.json'
JOIN = 'results/rtl/dsrom_field_address_lookahead_20261005/static_provider_join.json'
TEMPLATE = 'tools/rtl_templates/dsrom_s81_static_source_cut.sv'
COMMON = ['rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
          'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_cg.sv',
          'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/v41/ot_hdc_actquant.sv',
          'rtl/common/ot_prefix.sv']
STATIC = ['rtl/v41die/ot_v41_spine_static_w17w10.sv',
          'rtl/v41die/ot_v41_fieldtop_static_w17w10.sv',
          'rtl/v41die/static_controls/ot_v41_stage37_control_rom.sv',
          'rtl/v41die/static_controls/ot_v41_stage38_control_rom.sv']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_parameters(reference):
    reference = Path(reference).resolve()
    for name in ('Vcut.h', 'Vcut__ALL.a', 'Vcut__verFiles.dat'):
        if not (reference/name).is_file():
            raise ValueError('completed actual native cut missing: '+str(reference/name))
    text = (reference/'Vcut__verFiles.dat').read_text()
    match = re.search(r'^C "(.*)"$', text, re.M)
    if not match:
        raise ValueError('actual Verilator source/parameter command missing')
    command = shlex.split(match[1])
    if '-DRT_CUT' not in command or command[command.index('--top-module')+1] != 'dsrom_source_cut' or command[command.index('--prefix')+1] != 'Vcut':
        raise ValueError('actual dsrom_source_cut/Vcut RT_CUT reference required')
    params = dict((x[2:].split('=',1)[0], int(x.split('=',1)[1])) for x in command if x.startswith('-G'))
    expected = dict(PHW=10, VAW=16, R=128, FAST=1, PP=1, BP=0)
    if any(params.get(k)!=v for k,v in expected.items()) or not {'NP','NBF'}<=params.keys():
        raise ValueError(('frozen native cut port/parameter mismatch',params))
    # NP/NBF remain the reference's cut-only labels. RT_CUT has no field array;
    # physical payload ownership is the unchanged canonical NP2417/BF519 map.
    return params, {n:sha(reference/n) for n in ('Vcut.h','Vcut__ALL.a','Vcut__verFiles.dat')}


def prepare(reference, out, *, stage, rank, variant='baseline_static'):
    if variant != 'baseline_static':
        raise ValueError('PQ fieldtop is flat-only: Epicurus must supply RT_CUT/tagged native surface before selection')
    if stage not in (37,38) or rank not in range(4):
        raise ValueError('frozen provider stage37/38 and actual rank0..3 required')
    params, reference_pins = reference_parameters(reference)
    join = json.loads((ROOT/JOIN).read_text())
    if not join['status'].startswith('FUNCTIONAL_PROVIDER_PASS'):
        raise ValueError('frozen functional provider/model not ready')
    for name,pin in join['source_sha256'].items():
        if sha(ROOT/name)!=pin:
            raise ValueError('provider freeze differs: '+name)
    catalog = json.loads((ROOT/CATALOG).read_text())
    if not catalog['complete'] or not catalog['all_occupied_stages_ready']:
        raise ValueError('current canonical field catalog incomplete')
    entry = next(x for x in catalog['stages'] if x['stage']==stage)
    if entry['status']!='ready' or (entry['PHW'],entry['SAW'])!=(10,14):
        raise ValueError('actual selected immutable image/geometry unavailable')
    image = ROOT/entry['image_path']
    # Metadata enrollment only: accepted table/body proof is NOT rerun here.
    from dsrom_s81_target_field_controls import read_stage_binding
    binding = read_stage_binding(image)
    if sha(image/entry['binding_file'])!=entry['binding_sha256'] or binding['canonical_inputs']!=catalog['canonical_inputs']:
        raise ValueError('selected canonical binding changed')
    out = Path(out).resolve(); out.mkdir(parents=True,exist_ok=False)
    wrapper = out/'dsrom_source_cut.sv'
    wrapper.write_bytes((ROOT/TEMPLATE).read_bytes())
    params.update(STATIC_CONTROLS=1,CONTROL_STAGE=stage,SAW=14)
    record = dict(schema='opentallas.dsrom.static-native-cut-selection.v1',
                  variant=variant,stage=stage,rank=rank,top='dsrom_source_cut',prefix='Vcut',
                  fieldtop='ot_v41_fieldtop_static_w17w10',parameters=params,
                  field_array_instantiated=False,shared_runtime_context_required=True,
                  wrapper=str(wrapper),wrapper_sha256=sha(wrapper),
                  reference_cut=str(Path(reference).resolve()),reference_sha256=reference_pins,
                  catalog=str(ROOT/CATALOG),catalog_sha256=sha(ROOT/CATALOG),
                  canonical_inputs=catalog['canonical_inputs'],image_path=str(image),image_repo_path=entry['image_path'],
                  binding_sha256=entry['binding_sha256'],image_sha256=entry['files_sha256'],
                  key_frame=str(image/f'spine_keys.rank{rank}.hex'),
                  source_sha256={p:sha(ROOT/p) for p in STATIC+COMMON+[TEMPLATE,
                      'tools/runtime/dsrom/s81_minimum_qe_static.cpp',
                      'tools/runtime/dsrom/s81_static_field_controls.hpp']},
                  native_source=str(SUPPORT/'s81_minimum_qe_static.cpp'),
                  cpp_defines=[f'DSROM_S81_STATIC_CONTROL_STAGE={stage}',f'DSROM_S81_STATIC_CONTROL_MODEL_STAGE={stage}'],
                  cfg_rule='existing predecessor-inclusive CFG at25*canonicalphase, key/phase/order unchanged',
                  controls_rule='emit_native_phase_controls(stage_image=image_path); local PHROM2 and exact body, canonical SBASE',
                  functional_model_source=JOIN,physical_admission_required_for_compile=False,
                  build_complete=False,hardware_adopted=False)
    (out/'selection.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def build(out, *, verilator, jobs=2):
    out=Path(out).resolve();record=json.loads((out/'selection.json').read_text())
    if socket.gethostname() != 'climbing-locust':
        raise ValueError('this selected minimum compile must run on admitted EPYC2 scratch, never localhost')
    if not 1<=jobs<=16:
        raise ValueError('owner build admission requires make workers1..16')
    if record['build_complete'] or (out/'obj').exists():
        raise ValueError('preserve existing build; no restart/duplicate')
    for name,pin in record['source_sha256'].items():
        if sha(ROOT/name)!=pin:
            raise ValueError('frozen source changed: '+name)
    if sha(record['wrapper'])!=record['wrapper_sha256']:
        raise ValueError('wrapper changed after selection')
    obj=out/'obj'
    commands=[
        [str(verilator),'--cc','-O3','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD',
         '--threads','1','--top-module','dsrom_source_cut','--prefix','Vcut','--Mdir',str(obj),
         '-DRT_CUT','-DV41_RT',*[f'-G{k}={v}' for k,v in record['parameters'].items()],
         record['wrapper'],*[str(ROOT/p) for p in STATIC+COMMON]],
        ['make','-C',str(obj),'-f','Vcut.mk',f'-j{jobs}','Vcut__ALL.a','OPT_FAST=-O2','OPT_SLOW=-O1']]
    for name,command in zip(('verilate','make'),commands):
        with (out/(name+'.log')).open('x') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        record.setdefault('commands',[]).append(dict(name=name,argv=command,returncode=result.returncode))
        (out/'selection.json').write_text(json.dumps(record,indent=2)+'\n')
        if result.returncode:
            raise RuntimeError('actual native cut '+name+' failed; preserve '+str(out))
    record.update(build_complete=True,model_directory='obj',
                  artifacts_sha256={p.name:sha(p) for p in [obj/'Vcut.h',obj/'Vcut___024root.h',obj/'Vcut__ALL.a',obj/'Vcut__verFiles.dat']})
    (out/'selection.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def enroll(selection, sources, include_dirs, archives):
    """Existing archive-only linker: accept a REAL static cut, not macro labels."""
    record=json.loads(Path(selection).read_text())
    if not record['build_complete'] or record['variant']!='baseline_static':
        raise ValueError('completed baseline-static native cut required, not a source-only plan')
    obj=(Path(selection).resolve().parent/record['model_directory']).resolve()
    for name,pin in record['artifacts_sha256'].items():
        if sha(obj/name)!=pin:
            raise ValueError('actual static cut artifact changed: '+name)
    actual=(obj/'Vcut__verFiles.dat').read_text()
    for token in ('--top-module dsrom_source_cut','--prefix Vcut','-DRT_CUT','-GSTATIC_CONTROLS=1',
                  '-GCONTROL_STAGE='+str(record['stage']),'ot_v41_fieldtop_static_w17w10.sv',
                  'ot_v41_spine_static_w17w10.sv'):
        if token not in actual:
            raise ValueError('static native model build binding absent: '+token)
    for name,pin in record['source_sha256'].items():
        if sha(ROOT/name)!=pin:
            raise ValueError('selected runtime/provider source differs: '+name)
    if record['cpp_defines']!=[f"DSROM_S81_STATIC_CONTROL_STAGE={record['stage']}",f"DSROM_S81_STATIC_CONTROL_MODEL_STAGE={record['stage']}"]:
        raise ValueError('native runtime/model control stage mismatch')
    for directory in include_dirs:
        if (Path(directory)/'Vcut.h').exists() and Path(directory).resolve()!=obj.resolve():
            raise ValueError('foreign mutable/other-stage Vcut include cannot enroll')
    if any('Vcut' in Path(a).name for a in archives):
        raise ValueError('supply only the selected Vcut via enrollment, never duplicate old cut archive')
    # Replace each original TU once, retaining the SAME source-tag namespace.
    selected=[]
    replacements={'s81_minimum_qe.cpp':SUPPORT/'s81_minimum_qe_static.cpp',
                  's81_minimum_source_tags_component.cpp':SUPPORT/'s81_minimum_qe_tags.cpp'}
    for source in sources:
        selected.append(replacements.get(Path(source).name,Path(source)))
    for name in ('s81_minimum_qe_static.cpp','s81_minimum_qe_controls.cpp','s81_minimum_qe_tags.cpp'):
        if not any(p.name==name for p in selected):selected.append(SUPPORT/name)
    if len({p.name for p in selected})!=len(selected):
        raise ValueError('duplicate runtime TU after static selection')
    return selected, [obj,*include_dirs], [obj/'Vcut__ALL.a',*archives], ['-D'+v for v in record['cpp_defines']]


def selected_image(selection, *, canonical_inputs, stage, rank):
    record=json.loads(Path(selection).read_text())
    if not record['build_complete'] or (record['stage'],record['rank'])!=(stage,rank):
        raise ValueError('actual compiled static cut stage/rank differs from emitted fragment')
    if record['canonical_inputs']!=canonical_inputs:
        raise ValueError('actual current assignment differs from compiled static provider')
    enroll(selection,[],[],[])
    return ROOT/record['image_repo_path']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable-static-controls',action='store_true')
    p.add_argument('--reference-cut',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--control-stage',type=int,choices=(37,38),required=True)
    p.add_argument('--rank',type=int,choices=range(4),required=True)
    p.add_argument('--variant',choices=('baseline_static','pq_static'),default='baseline_static')
    p.add_argument('--build',action='store_true')
    p.add_argument('--verilator',type=Path,default=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
    p.add_argument('--jobs',type=int,default=2)
    a=p.parse_args()
    if not a.enable_static_controls:p.error('static provider is opt-in; require --enable-static-controls')
    prepare(a.reference_cut,a.out,stage=a.control_stage,rank=a.rank,variant=a.variant)
    if a.build:build(a.out,verilator=a.verilator,jobs=a.jobs)
    print(a.out/'selection.json')


if __name__=='__main__':main()
