#!/usr/bin/env python3
"""Owner-authorized, one-shot full-sheet rebind of audited r18b index b1/b3/b5 only."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

import closure_loop as cl

AUDIT = 'ea6759434'
RECORD = 'results/rtl/hbm_index_budget_binding_20261006'
ALLOWED = tuple(f'hbm_idxq_b{i}_e8b5132fb_r18b' for i in (1, 3, 5))


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def validate(j, historical, binding, sheet):
    if j['name'] not in ALLOWED or j['status'] != 'NEEDS_BUDGET' or j.get('audited_budget_rebind'):
        raise ValueError('only the three authorized, unrebound NEEDS_BUDGET jobs are eligible')
    for key in ('spec', 'calibration', 'commit_full', 'host', 'run', 'stage_tag', 'stage_idx', 'benches'):
        if j.get(key) != historical.get(key):
            raise ValueError(f'{j["name"]}: live {key} differs from audited snapshot')
    if j['budget']['sheets_ref'] != binding['bound_sheets_ref']:
        raise ValueError('historical sheet reference changed')
    if binding['boundary_max_above_approved_target_ps'] != 0 or not binding['mean_gate_pass']:
        raise ValueError('boundary maximum/mean not eligible')
    ins = sheet['clock']['internal_insertion']
    if ins != binding['corrected_binding']['insertion']:
        raise ValueError('full-sheet insertion does not match audit')
    for corner in ('SS', 'FF'):
        if j['calibration']['env'][f'CK_{corner}_MAX'] > ins[f'target_{corner.lower()}']:
            raise ValueError(f'{corner} boundary maximum exceeds approved target')
    if cl.stage_list(j['spec'])[j['stage_idx']]['kind'] != 'calibrate':
        raise ValueError('not stopped at calibration')


REMOTE = r'''
import hashlib,json,pathlib,shutil,sys
p=json.loads(sys.argv[1]); j=p['job']; run=pathlib.Path(j['run']); c=run/'cl'
assert (c/(j['stage_tag']+'.rc')).read_text().strip()=='0', 'calibration not complete'
assert not list(c.glob('route.a*.sh')), 'route already attempted'
dest=c/'budget-rebind-ea6759434'; dest.mkdir()
paths=list(c.glob('budget*'))+[c/'calib.json',c/'calib.env',c/'job.json']
paths+=list((run/'src/physical/hbm_accel_die_views/common').glob('budget*.sdc'))
old={}
for source in paths:
 if not source.is_file(): continue
 relative=source.relative_to(run); target=dest/'historical'/relative; target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source,target); old[str(relative)]=hashlib.sha256(source.read_bytes()).hexdigest()
(dest/'historical_state.json').write_text(json.dumps(j,indent=2)+'\n')
(dest/'binding.json').write_text(json.dumps(p['binding'],indent=2)+'\n')
new={}; approved=dest/'approved';approved.mkdir()
for name,text in p['files'].items():
 if name.startswith('_'): continue
 target=approved/name;target.write_text(text);new[name]=hashlib.sha256(target.read_bytes()).hexdigest()
manifest=dict(historical=old,approved=new,audit_commit=p['audit_commit'],sheet_ref=p['files']['_ref'])
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# State remains NEEDS_BUDGET during this installation. Never overwrite a failed snapshot.
for name in new:
 tmp=c/(name+'.rebind-tmp');shutil.copyfile(approved/name,tmp);tmp.replace(c/name)
print(json.dumps(dict(directory=str(dest),manifest=manifest)))
'''


def rebind(name, root, binding, audit_commit, apply):
    historical_path=root/RECORD/'jobs'/f'{name}.json'
    historical=json.loads(historical_path.read_text())
    if sha(historical_path.read_bytes()) != binding['snapshot_sha256']:
        raise ValueError('audited job snapshot digest mismatch')
    with cl.job_lock(name):
        j=cl.load_job(name)
        corrected=binding['corrected_binding']
        bud=dict(j['spec']['budget'],sheets_ref=corrected['sheets_ref'],preserve_full_sheet=True,
                 sheet_sha256=corrected['sheet_sha256'])
        files=cl.budget_files(bud)  # full published sheet; no insertion override
        if sha(files['budget_sheet.json']) != bud['sheet_sha256']:
            raise ValueError('complete approved sheet hash mismatch')
        sheet=json.loads(files['budget_sheet.json'])
        validate(j,historical,binding,sheet)
        if not apply:
            return dict(job=name,validated=True,sheet_sha256=bud['sheet_sha256'],sheets_ref=files['_ref'])
        payload=dict(job=j,files=files,binding=binding,audit_commit=audit_commit)
        receipt=json.loads(cl.ssh(j['host'],'python3 - '+shlex.quote(json.dumps(payload)),input=REMOTE,
                                  timeout=120,check=True).stdout)
        j['audited_budget_rebind']=dict(audit_commit=audit_commit,receipt=receipt,previous_budget=j['budget'],
                                        previous_merge_target=j['spec'].get('merge_target'),
                                        signoff_scope='component only; physical die-context adoption remains parent-owned')
        j['spec']['budget']=bud
        j['spec']['merge_target']=None  # retain records without automatic adoption into the integration branch
        j['budget']=dict(master=bud['master'],sheets_ref=files['_ref'],sheet_sha256=bud['sheet_sha256'],
                         insertion=sheet['clock']['internal_insertion'],
                         entry_target_ss=sheet['clock']['entry_target_ss_ps'],
                         entry_target_ff=sheet['clock']['entry_target_ff_ps'],
                         check=dict(ok=True,accepted='full audited sheet; approved rounded boundary maxima checked',
                                    measured_ss=j['calibration']['env']['CK_SS_MEAN']))
        j['spec']['record'].append(dict(from_=receipt['directory'],to=f'{RECORD}/rebindings/{name}'))
        j['spec']['record'][-1]['from']=j['spec']['record'][-1].pop('from_')
        j.update(status='READY',stage_idx=j['stage_idx']+1,stage_key='route',attempt=j['attempt']+1,
                 reason='audited full-sheet rebind; component route pending',errors=[],wait=None)
        j.pop('wait_since',None)
        cl.save_job(j)
        cl.ledger(j,f"AUDITED REBIND: full sheet {files['_ref']} sha256 {bud['sheet_sha256']}; "
                    f"historical inputs {receipt['directory']}; route/admission pending; component only, no automatic merge")
        return dict(job=name,status=j['status'],receipt=receipt)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply',action='store_true')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='index-budget-audit-') as tmp:
        root=Path(tmp)
        audit_commit=cl.git('rev-parse',AUDIT).stdout.strip()
        archive=subprocess.check_output(['git','-C',str(cl.REPO),'archive',audit_commit,
                                         'tools/budgets/check_hbm_index_binding.py',RECORD])
        subprocess.run(['tar','-x','-C',str(root)],input=archive,check=True)
        replay=subprocess.run(['python3',str(root/'tools/budgets/check_hbm_index_binding.py')],
                              capture_output=True,text=True,check=True)
        proof=json.loads(replay.stdout)
        pinned=json.loads((root/RECORD/'binding.json').read_text())
        if proof != pinned or proof['verdict'] != 'PASS' or proof['signoff_claim']:
            raise ValueError('audited compensation proof replay differs')
        bindings={b['job']:b for b in proof['jobs']}
        records=[]
        try:
            for name in ALLOWED:
                records.append(rebind(name,root,bindings[name],audit_commit,args.apply))
        finally:
            args.out.write_text(json.dumps(dict(audit_commit=audit_commit,apply=args.apply,jobs=records),indent=2)+'\n')
        print(json.dumps(records))


if __name__=='__main__':
    main()
