#!/usr/bin/env python3
"""Prepare strict historical export replay for an explicit owner-selected list.

Selection JSON: [{"cell":"MASTER", "view":"physical/.../views/MASTER"}, ...].
This only stages small inputs. Run replay_bundle.py under ot-run on each emitted
host-specific remote directory; no heavy process or route is started here.
"""
import argparse, concurrent.futures, hashlib, io, json, re, shlex, subprocess, tarfile
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--selection',required=True,type=Path)
    ap.add_argument('--artifacts',required=True,type=Path)
    ap.add_argument('--remote-prefix',required=True)
    ap.add_argument('--runner',required=True,type=Path)
    args=ap.parse_args(); root=args.root; art=args.artifacts; art.mkdir(parents=True,exist_ok=True)
    def show(c,p): return subprocess.check_output(['git','-C',str(root),'show',c+':'+p])
    sha=lambda b:hashlib.sha256(b).hexdigest()
    files={};groups={};rows=[]
    for x in json.load(open(args.selection)):
        cell,view=x['cell'],x['view'];ab=json.load(open(root/view/'abstract.json'))
        job=re.search(r'/closure-loop/([^/]+)/',ab['orfs_dir']).group(1)
        j=json.load(open(Path.home()/'.local/state/closure_loop/jobs'/(job+'.json')))
        if j['status']!='CLOSED': raise ValueError('not CLOSED: '+job)
        c=j['publish']['branch_commit'];original=json.loads(show(c,view+'/abstract.json'))
        row=dict(cell=cell,view=view,job=job,host=j['host'],run=j['run'],record_commit=c,
                 source_commit=j['commit_full'],orfs_dir=ab['orfs_dir'],
                 raw_lef_expected=ab['files'][cell+'.lef'],image=original['corners']['ss']['image'],published_hashes={})
        for f in [cell+'.lef',*[cell+'_'+a+'.lib' for a in ['tt','ff','ss']],
                  'abstract.json','insertion.json','child_lint.json']:
            h=sha(show(c,view+'/'+f));row['published_hashes'][f]=h
            if sha((root/view/f).read_bytes())!=h: raise ValueError('working file differs from published record: '+view+'/'+f)
        lines=[]
        for line in show(c,view+'/export_ss.tcl').decode().splitlines():
            lines.append(line)
            if line.startswith('read_db '): break
        else: raise ValueError('no read_db in original export Tcl')
        lines+=['write_abstract_lef /out/raw.lef','exit']
        files[job+'/raw.tcl']=('\n'.join(lines)+'\n').encode()
        helpers=[entry for entry in j.get('route_overlay_plan',{}).get('files',[])
                 if entry['path']=='tools/hier_contract/abstract_pin_stub.py']
        if helpers:
            plan=j['route_overlay_plan']; verification=j.get('helper_overlay_verification',{})
            if (verification.get('status')!='verified_original' or
                verification.get('content_sha256')!=plan.get('content_sha256')):
                raise ValueError('effective helper overlay is not verified_original: '+job)
            helper=helpers[0]; data=subprocess.check_output(['git','-C',str(root),'cat-file','blob',helper['git_blob']])
            if sha(data)!=helper['sha256']: raise ValueError('effective helper Git blob SHA mismatch: '+job)
            row['effective_helper']=dict(basis='verified_original_frozen_overlay',
                git_blob=helper['git_blob'],sha256=helper['sha256'],
                origin_main=plan['origin_main'],content_sha256=plan['content_sha256'],
                verification=verification)
        else:
            data=show(j['commit_full'],'tools/hier_contract/abstract_pin_stub.py')
            row['effective_helper']=dict(basis='job_source_commit',source_commit=j['commit_full'],sha256=sha(data))
        files[job+'/helper.py']=data
        groups.setdefault(j['host'],[]).append(row); rows.append(row)
    (art/'bundle_recovery_plan.json').write_text(json.dumps(rows,indent=2)+'\n')
    def stage(item):
        host,group=item; data=io.BytesIO();remote=args.remote_prefix.rstrip('/')+'/'+host
        with tarfile.open(fileobj=data,mode='w') as tar:
            batch={'plan.json':json.dumps(group).encode(),'replay_bundle.py':args.runner.read_bytes()}
            for row in group:
                for name in ['raw.tcl','helper.py']:batch[row['job']+'/'+name]=files[row['job']+'/'+name]
            for name,b in batch.items():
                ti=tarfile.TarInfo(name);ti.size=len(b);tar.addfile(ti,io.BytesIO(b))
        p=subprocess.run(['ssh',host,'mkdir -p '+shlex.quote(remote)+' && tar -x -C '+shlex.quote(remote)],
                         input=data.getvalue(),capture_output=True)
        if p.returncode: raise RuntimeError(host+': '+p.stderr.decode())
        return dict(host=host,remote_dir=remote,jobs=len(group))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for x in ex.map(stage,groups.items()):print(json.dumps(x),flush=True)

if __name__=='__main__':main()
