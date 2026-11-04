"""Publish one append-only queue row without modifying the shared coordination checkout/index.
The temporary index starts at the latest remote tree; a raced push is rebuilt on the new remote parent.
A transport error (ssh denial, dropped connection, hung remote) is retried with short backoff; a push the remote
refuses for any other reason is reported with its own message, never as a race. Publishing is idempotent (an identical
row is not added twice), so a retry after a lost push reply cannot duplicate a row.
"""
import fcntl
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

TRANSPORT_BACKOFF_S=(2,5,15)    # a fourth failure in one publish is reported; about 22 s of sleep in all
NET_TIMEOUT_S=60                # per git network call; enqueue_pass allows the whole publish 300 s
RACE_RE=re.compile(r'fetch first|non-fast-forward|cannot lock ref|failed to update ref|stale info|incorrect old value',re.I)
TRANSPORT_RE=re.compile(r'permission denied|could not read from remote|connection (reset|refused|closed|timed out)'
                        r'|timed out|early eof|hung up|broken pipe|kex_exchange|ssh_exchange|could not resolve'
                        r'|unable to access|rpc failed|network is unreachable|temporary failure|no route to host',re.I)


def publish(coord, line, message, attempts=8, path="autopilot/queue.tsv"):
    if path not in {"autopilot/queue.tsv", "autopilot/resolved.tsv", "lanes/GEOM-REVIEW.md", "autopilot/geom_templates.tsv"}:
        raise RuntimeError("not an authorized append-only coordination path")
    coord=Path(coord)
    def git(*args, input=None, env=None, check=True, timeout=None):
        e=dict(os.environ)
        for k in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE'):
            e.pop(k,None)
        if env:e.update(env)
        try:
            r=subprocess.run(['git','-C',str(coord),*args],input=input,text=True,capture_output=True,env=e,timeout=timeout)
        except subprocess.TimeoutExpired:
            r=subprocess.CompletedProcess(args,124,'',f'git {args[0]} timed out after {timeout} s')
        if check and r.returncode:raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        return r
    backoff=list(TRANSPORT_BACKOFF_S)
    def transport_wait(what,r):
        err=r.stderr.strip() or r.stdout.strip()
        if not backoff:
            raise RuntimeError(f'transport error on {what} after {len(TRANSPORT_BACKOFF_S)+1} tries: {err}')
        time.sleep(backoff.pop(0))
    with open(coord/'.autopilot-publish.lock','w') as lock, tempfile.TemporaryDirectory(prefix='ap-queue-') as tmp:
        fcntl.flock(lock,fcntl.LOCK_EX)
        races=0
        while races<attempts:
            fetched=git('fetch','-q','origin','coord/state',check=False,timeout=NET_TIMEOUT_S)
            if fetched.returncode:
                transport_wait('fetch',fetched)
                continue
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
            pushed=git('push','-q','origin',commit+':refs/heads/coord/state',check=False,timeout=NET_TIMEOUT_S)
            if pushed.returncode==0:return commit
            err=pushed.stderr+pushed.stdout
            if RACE_RE.search(err):
                races+=1
            elif TRANSPORT_RE.search(err):
                transport_wait('push',pushed)
            else:
                raise RuntimeError('coord/state push refused, not a race: '+(err.strip() or f'rc {pushed.returncode}'))
        raise RuntimeError('coord/state push raced repeatedly; NOT SUBMITTED (shared checkout/index unchanged)')
