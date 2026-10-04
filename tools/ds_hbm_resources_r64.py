"""Regenerate exact original R56 model plus additive R63 source/diagnostics.
No payload execution, bound lowering, numerical launch or process resource cap.
"""
import argparse,ast,copy,json,sys
from pathlib import Path
import ds_hbm_dual_resources_r56 as base
from ds_hbm_connected_prepare_r37 import sha
from ds_producer_checkpoint_resume_v3 import canonical
ROOT=base.ROOT
OUT=ROOT/'results/uarch/ds_hbm_checkpoint_readiness_r64_20261003'
NEW=['tools/ds_hbm_checkpointed_prefix_r63.py','tools/ds_hbm_checkpoint_execution_r63.py',
     'tools/ds_hbm_checkpoint_boundary_r62.py','tools/ds_hbm_output_root_guard_r59.py',
     'tools/ds_hbm_dual_constructor_r64.py','tools/ds_hbm_resources_r64.py']


def source_pins():
    old=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_execution_r58_20261003/runtime_plan.json').read_bytes())['source_sha256']
    # Retain the complete old lineage; verify it, do not silently substitute.
    for p,digest in old.items():
        if sha(ROOT/p)!=digest:raise ValueError('original source/provenance changed: '+p)
    return dict(old,**{p:sha(ROOT/p) for p in NEW})


def compose(native,homes,manifest,*,output_root,pins):
    v=base.model(native,homes,manifest,output_root=output_root)
    source_bytes=sum((ROOT/p).stat().st_size for p in pins)
    graph_bytes=sum(len(canonical(x)) for x in (native,homes,manifest))
    # Full graph text is a deliberately retained overcharge for exception
    # messages. Each included source file also pays its full text. Two actual
    # durable records exist: boundary stage and terminal runner receipt.
    diagnostic_text=source_bytes+graph_bytes+len(canonical(pins))
    # JSON may escape every byte to six ASCII characters, plus field framing.
    diagnostic_file=6*diagnostic_text+len(canonical({'last_call_stage':'preflight_source_contract',
        'stage_status':'FAILED','exception_type':'AttributeError','reason':'','traceback':''}))
    # Existing constructor metadata source pins are copied in20 charged slots.
    # Keep20 copies for new source lineage too. Six checkpoint identity/contract
    # copies are inherited from R56. No original RAM/disk component is removed.
    lineage=len(canonical(pins))+sum((ROOT/p).stat().st_size for p in NEW)
    contract_extra=len(canonical({'original_runner_source_sha256':sha(ROOT/'tools/ds_hbm_checkpointed_prefix_r55.py')}))
    checkpoint_extra=6*(lineage+contract_extra)
    disk_extra=2*diagnostic_file+lineage
    # Two retained trace strings and concurrent unicode+encoded JSON output.
    # CPython unicode may use4 bytes/character; serialized bytes also coexist.
    ram_extra=20*lineage+4*(4*diagnostic_text+diagnostic_file)
    v['checkpoint']['components']['R64_source_contract_and_lineage_copies_bytes']=checkpoint_extra
    v['checkpoint']['checkpoint_new_bytes']+=checkpoint_extra
    v['checkpoint_new_bytes']+=checkpoint_extra
    v['other_new_bytes']+=disk_extra
    for key in ('cold_and_restore_new_RAM_bytes','serialization_workspace_RAM_bytes'):
        v[key]+=ram_extra
        v['RAM'][key]+=ram_extra
    v['RAM']['components']['R64_retained_diagnostics_and_source_lineage_bytes']=ram_extra
    v['RAM']['coexistence_RAM_peak_bytes']+=ram_extra
    v.update(output_root=str(Path(output_root).resolve()),source_sha256=pins,
        R64_additive_costs=dict(source_and_graph_diagnostic_text_upper_bytes=diagnostic_text,
            stage_or_terminal_file_upper_bytes=diagnostic_file,two_durable_records=True,
            lineage_serialized_bytes=lineage,checkpoint_extra_bytes=checkpoint_extra,
            other_disk_extra_bytes=disk_extra,RAM_extra_bytes=ram_extra,
            original_components_removed=0,original_sector_counts_and_guards_unchanged=True),
        scope='R63 exact source and stage diagnostics; R56 model freshly regenerated; no numerical/physical admission')
    return v


def prepare():
    pins=source_pins();n,h,m=base.journal.source_inputs();OUT.mkdir(exist_ok=True)
    products=[]
    for label,output in [('preflight','/tmp/kepler-ds-r64-dual-constructor-preflight-20261003'),
                         ('runtime','/tmp/kepler-ds-r64-PC0-10-checkpoint-runtime-20261003')]:
        model=compose(n,h,m,output_root=output,pins=pins)
        path=OUT/(label+'_model.json');path.write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
        plan=dict(schema='DS_PC0_10_ACTUAL_CHECKPOINT_LAUNCH_PLAN_R55',status='PASS_SOURCE_AND_STORAGE_REVIEW',
            helper_module='ds_producer_checkpoint_resume_v3',stop=10,checkpoint_boundary=9,
            source_sha256=pins,storage_proof={'path':str(path.relative_to(ROOT)),'sha256':sha(path)},
            numerical_GO=False,preflight_only=label=='preflight',output_root=output,
            authorization='User authorized source repricing and actual constructor preflight; numerical scope requires positive new constructor receipt and fresh complete fit',
            actual_constructor_receipt_pending=True)
        (OUT/(label+'_plan.json')).write_text(json.dumps(plan,sort_keys=True,indent=2)+'\n')
        products.append(dict(phase=label,output_root=output,required_disk_bytes=sum(model[k] for k in ('journal_new_bytes','checkpoint_new_bytes','other_new_bytes')),
            required_RAM_bytes=model['RAM']['coexistence_RAM_peak_bytes']))
    (OUT/'summary.json').write_text(json.dumps(products,indent=2)+'\n')
    print(json.dumps(products,indent=2))

if __name__=='__main__':prepare()
