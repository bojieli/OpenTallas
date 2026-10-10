# struct-close 2026-10-09: closure-loop job maker (clone a base job spec, swap source / route substitutions / benches; the
# collect command is rewritten when the base copied {RUN}/bench/*.log, which a replaced bench set does not write).
import json,sys,copy,os,re
J=os.path.expanduser('~/.local/state/closure_loop/jobs/')
OUT='/tmp/claude-review-20261003/closure_jobs/'
def load(n): return json.load(open(J+n+'.json'))['spec']
def make(base, name, commit, branch, purpose, subs=(), env_prefix='', benches=None, hm=None, cycles=None, extra=None, dry=False):
    s=copy.deepcopy(load(base)); s['name']=name; s['owner']='Claude:struct-close'
    s['source']={'branch':branch,'commit':commit, **({k:v for k,v in s['source'].items() if k=='extra_paths'})}
    s['purpose']=purpose
    for st in ('calibrate','route'):
        if st in s['stages'] and isinstance(s['stages'][st],dict):
            if 'cmd' not in s['stages'][st]: continue
            c=s['stages'][st]['cmd']
            for a,b in subs:
                assert a in c or st!='route', (st,a); c=c.replace(a,b)
            s['stages'][st]['cmd']=env_prefix+c
    if benches is not None:
        s['stages']['bench']=benches
        col=(s['stages'].get('collect') or {}).get('cmd')
        if col and '{RUN}/bench/' in col:   # the base's bench logs lived in {RUN}/bench/; ours do not: copy whatever exists
            s['stages']['collect']['cmd']=re.sub(r"\s*&&\s*cp \{RUN\}/bench/\*\.log (\S+)", r" && (cp {RUN}/bench*/*.log {CL}/bench_*.log \1 2>/dev/null || true)", col)
    if hm is not None: s['route_hold_margin_ns']=hm
    if cycles is not None: s['cycles_added']=cycles
    for k in ('record','merge_target'): s.pop(k,None)
    s['merge_target']=None
    if extra: s.update(extra)
    p=OUT+name+'.json'
    if not dry: json.dump(s,open(p,'w'),indent=1)
    print('wrote' if not dry else 'dry',name)
    return s
