"""Publish one append-only queue row without modifying the shared coordination checkout/index.
The temporary index starts at the latest remote tree; a raced push is rebuilt on the new remote parent.
"""
import fcntl
import os
import subprocess
import tempfile
from pathlib import Path


def publish(coord, line, message, attempts=8):
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
            prior=git('show',base+':autopilot/queue.tsv',check=False)
            if prior.returncode:
                prior_text='# AUTOPILOT queue\n'
            else:prior_text=prior.stdout
            if any(l.startswith(('<<<<<<< ','=======','>>>>>>> ')) for l in prior_text.splitlines()):
                raise RuntimeError('remote queue has unresolved merge markers; no row published')
            if line in prior_text.splitlines():return base
            env={'GIT_INDEX_FILE':str(Path(tmp)/'index')}
            git('read-tree',base,env=env)
            text=prior_text.rstrip('\n')+'\n'+line+'\n'
            blob=git('hash-object','-w','--stdin',input=text).stdout.strip()
            git('update-index','--add','--cacheinfo','100644',blob,'autopilot/queue.tsv',env=env)
            tree=git('write-tree',env=env).stdout.strip()
            commit=git('commit-tree',tree,'-p',base,'-m',message+'\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',env=env).stdout.strip()
            pushed=git('push','-q','origin',commit+':refs/heads/coord/state',check=False)
            if pushed.returncode==0:return commit
        raise RuntimeError('coord/state push raced repeatedly; NOT SUBMITTED (shared checkout/index unchanged)')
