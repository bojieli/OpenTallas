"""Publish one append-only queue row without modifying the shared coordination checkout/index.
The temporary index starts at the latest remote tree; a raced push is rebuilt on the new remote parent.
"""
import fcntl
import os
import subprocess
import tempfile
from pathlib import Path


def publish(coord, line, message, attempts=8, path="autopilot/queue.tsv"):
    if path not in {"autopilot/queue.tsv", "autopilot/resolved.tsv", "lanes/GEOM-REVIEW.md"}:
        raise RuntimeError("not an authorized append-only coordination path")
    coord=Path(coord)
    def git(*args, input=None, env=None, check=True):
        e=dict(os.environ)
        for k in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE'):
            e.pop(k,None)
        if env:e.update(env)
        r=subprocess.run(['git','-C',str(coord),*args],input=input,text=True,capture_output=True,env=e)
        if check and r.returncode:raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        return r
    with open(coord/'.autopilot-publish.lock','w') as lock, tempfile.TemporaryDirectory(prefix='ap-queue-') as tmp:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for _ in range(attempts):
            git('fetch','-q','origin','coord/state')
            base=git('rev-parse','origin/coord/state').stdout.strip()
            prior=git('show',base+':'+path,check=False)
            if prior.returncode:
                prior_text='# append-only coordination records: '+path+'\n'
            else:prior_text=prior.stdout
            if any(l.startswith(('<<<<<<< ','=======','>>>>>>> ')) for l in prior_text.splitlines()):
                raise RuntimeError('remote queue has unresolved merge markers; no row published')
            prior_lines=prior_text.splitlines()
            packet=line.splitlines()
            if path.endswith(".md"):
                # Markdown continuation lines belong to their request/reply packet.
                identical=any(prior_lines[i:i+len(packet)] == packet
                              for i in range(len(prior_lines)-len(packet)+1))
                additions=[] if identical else packet
            else:
                old_lines=set(prior_lines)
                additions=[row for row in packet if row not in old_lines]
            if not additions:return base
            env={'GIT_INDEX_FILE':str(Path(tmp)/'index')}
            git('read-tree',base,env=env)
            text=prior_text.rstrip('\n')+'\n'+'\n'.join(additions)+'\n'
            blob=git('hash-object','-w','--stdin',input=text).stdout.strip()
            git('update-index','--add','--cacheinfo','100644',blob,path,env=env)
            tree=git('write-tree',env=env).stdout.strip()
            commit=git('commit-tree',tree,'-p',base,'-m',message+'\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',env=env).stdout.strip()
            pushed=git('push','-q','origin',commit+':refs/heads/coord/state',check=False)
            if pushed.returncode==0:return commit
        raise RuntimeError('coord/state push raced repeatedly; NOT SUBMITTED (shared checkout/index unchanged)')
