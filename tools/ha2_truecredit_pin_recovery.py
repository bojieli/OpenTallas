#!/usr/bin/env python3
"""Privately reuse verified placement checkpoints after the PG-count failure.

Run only under host admission. Original ORFS/source directories are read-only
inputs. The private config changes only the post-IO hook. Old synthesis,
floorplan and pre-IO global placement must remain byte-identical after CTS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--part',required=True,choices=['tx','rx'])
    p.add_argument('--old-orfs',required=True,type=Path)
    p.add_argument('--old-source',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--image-id',required=True)
    p.add_argument('--threads',type=int,default=8)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',a.image_id):
        p.error('--image-id must be an immutable Docker image ID')
    if a.threads<1:p.error('--threads must be positive')
    old=a.old_orfs.resolve();old_source=a.old_source.resolve();out=a.out.resolve()
    if any(out==tree or tree in out.parents for tree in (old,old_source,ROOT)):
        p.error('--out must be outside original ORFS and source trees')
    manifest=json.loads((ROOT/'physical/ha2_truecredit_20261007/source_manifest.json').read_text())
    for name,pin in manifest['files'].items():
        if sha(ROOT/name)!=pin or sha(old_source/name)!=pin:
            raise RuntimeError('Original source changed: '+name)
    successor=json.loads((ROOT/'physical/ha2_truecredit_20261007/signal_pin_successor_manifest.json').read_text())
    for name,pin in successor['files'].items():
        if sha(ROOT/name)!=pin:raise RuntimeError('Successor source changed: '+name)
    bases=list((old/'results/asap7').glob('*/base'))
    if len(bases)!=1:raise RuntimeError('Expected one retained design')
    base=bases[0];rel=base.relative_to(old)
    required=['1_2_yosys.v','1_synth.odb','2_floorplan.odb','2_floorplan.sdc','3_1_place_gp_skip_io.odb']
    upstream={name:sha(base/name) for name in required}
    old_hook=old/'hooks'/('post_io_placement_'+a.part+'_pins.tcl')
    if sha(old_hook)!=sha(old_source/'physical/ha2_truecredit_20261007'/(a.part+'_pins.tcl')):
        raise RuntimeError('Failed hook differs from pinned predecessor')
    config=(old/'config.mk').read_text()
    want='export POST_IO_PLACEMENT_TCL = /work/hooks/post_io_placement_'+a.part+'_pins.tcl'
    replacement='export POST_IO_PLACEMENT_TCL = /src/physical/ha2_truecredit_20261007/'+a.part+'_pins_signal_only.tcl'
    if config.splitlines().count(want)!=1:raise RuntimeError('Unexpected original hook configuration')
    out.mkdir(parents=True,exist_ok=False)
    work=out/'orfs'
    shutil.copytree(old,work)  # Dereference symlinks: never write through to original checkpoints.
    (work/'config.mk').write_text(config.replace(want,replacement))
    assert (work/'config.mk').read_text().replace(replacement,want)==config
    private_base=work/rel
    for name,h in upstream.items():assert sha(private_base/name)==h
    readback=f'''read_db /work/{rel}/3_2_place_iop.odb
source /src/physical/ha2_truecredit_20261007/{a.part}_check_pins_signal_only.tcl
exit
'''
    (work/'recovery_readback.tcl').write_text(readback)
    # Do not revisit verified predecessor stages solely because a successor
    # archive/config has a new timestamp. Re-run the failed IO stage explicitly.
    completed=sorted('/work/'+str(f.relative_to(work)) for f in private_base.iterdir() if f.is_file())
    make=['make','DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work','FLOW_VARIANT=base',f'NUM_CORES={a.threads}']
    ignore=[arg for f in completed for arg in ['-o',f]]
    commands={
        'io':make+ignore+['do-3_2_place_iop'],
        'readback':['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/work/recovery_readback.tcl'],
        'cts':make+ignore+['cts'],
    }
    record=dict(part=a.part,original_orfs=str(old),original_source=str(old_source),
        predecessor_commit='04491da6ced8430c9976dc56cf828dbe4d73633d',
        original_config_sha256=sha(old/'config.mk'),private_config_sha256=sha(work/'config.mk'),
        config_change=dict(before=want,after=replacement),upstream_sha256=upstream,
        original_hook_sha256=sha(old_hook),source_manifest=manifest,successor_manifest=successor,
        image_id=a.image_id,runner_sha256=sha(Path(__file__).resolve()),
        image_provenance='Explicit current immutable ID. Original failed driver used an image alias but did not persist its digest before failure; historical alias binding is not independently proven.',
        completed_checkpoint_reuse=completed,commands=commands,
        original_artifacts_modified=False,physical_signoff=False,status='PREPARED')
    receipt=out/'recovery.json'
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    if not a.execute:
        print('RECOVERY_PREPARED: private checkpoints/config and exact commands; no tools launched')
        return 0
    probe=subprocess.run(['docker','image','inspect',a.image_id,'--format','{{.Id}}'],capture_output=True,text=True)
    if probe.returncode or probe.stdout.strip()!=a.image_id:raise RuntimeError('Immutable image unavailable')
    for stage,command in commands.items():
        shell="source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "+shlex.join(command)
        cmd=['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',
             '-w','/OpenROAD-flow-scripts/flow',a.image_id,'bash','-lc',shell]
        with (out/(stage+'.log')).open('w') as log:
            run=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        record.setdefault('exit_codes',{})[stage]=run.returncode
        record['status']='FAILED_'+stage.upper() if run.returncode else stage.upper()+'_DONE'
        receipt.write_text(json.dumps(record,indent=2)+'\n')
        if run.returncode:return run.returncode
        if stage=='readback':
            text=(out/'readback.log').read_text()
            if 'TRUECREDIT_SIGNAL_IDENTITY_PASS' not in text or 'TRUECREDIT_PIN_CHECK_PASS' not in text:
                raise RuntimeError('Pin readback PASS markers missing')
    for name,h in upstream.items():
        if sha(private_base/name)!=h or sha(base/name)!=h:
            raise RuntimeError('Verified upstream checkpoint unexpectedly changed: '+name)
    metrics=work/'logs/asap7'/rel.parts[2]/'base/4_1_cts.json'
    if not metrics.is_file():raise RuntimeError('CTS metrics missing after make')
    record.update(status='CTS_COMPLETED',upstream_checkpoints_unchanged=True,
                  cts_metrics=str(metrics),cts_metrics_sha256=sha(metrics))
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    print('RECOVERY_CTS_COMPLETED: original checkpoints retained; no signoff claim')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
