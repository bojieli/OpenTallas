"""Strict actual primitive completion / independently bound mutant DIFF."""
import re
import prepare_dsrom_selector_mappedprimitive_gate as P

STEP=re.compile(r'PRIMITIVE_STEP_PASS mode=(\d+) index=(\d+) payload=([01]) flag=([01]) reset=([01])')
ASYNC=re.compile(r'PRIMITIVE_ASYNC_PASS mode=(\d+) index=(\d+) reset=([01])')
DIFF=re.compile(r'PRIMITIVE_DIFF mode=(\d+) kind=(PAYLOAD|FLAG|CONTROL) phase=(RISE|ASYNC) index=(\d+) expected=([01]) actual=([01])')
FINAL='PRIMITIVE_PASS mode=0 steps=33 async=7 assertions=252'

def verify(log,mode,returncode=0):
    if mode not in (0,1,2,3) or returncode!=0:raise ValueError('mode or process failure')
    if any(x in log for x in ('%Error','fatal','PRIMITIVE_FAILURE','PRIMITIVE_MUTANT_NO_DIFFERENCE')):raise ValueError('primitive failure/crash is not DIFF')
    lines=[x.strip() for x in log.splitlines() if 'PRIMITIVE_' in x]
    expect=P.expected();steps=[];events=[];diff=[];terminal=[];order=[]
    for line in lines:
        if m:=STEP.fullmatch(line):
            if int(m[1])!=mode:raise ValueError('foreign step mode')
            steps.append(dict(index=int(m[2]),payload=int(m[3]),flag=int(m[4]),reset=int(m[5])))
            order.append('S'+m[2])
        elif m:=ASYNC.fullmatch(line):
            if int(m[1])!=mode:raise ValueError('foreign event mode')
            events.append(dict(index=int(m[2]),reset=int(m[3])))
            order.append('A'+m[2])
        elif m:=DIFF.fullmatch(line):
            if int(m[1])!=mode:raise ValueError('foreign DIFF mode')
            diff.append(dict(kind=m[2],phase=m[3],index=int(m[4]),expected=int(m[5]),actual=int(m[6])))
        elif line==FINAL:terminal.append(line)
        else:raise ValueError('malformed/foreign primitive marker')
    if mode==0:
        if steps!=expect['steps'] or events!=expect['async_events'] or order!=expect['marker_order'] or diff or len(terminal)!=1:raise ValueError('exact primitive counts/order/values required')
        if not lines or lines[-1]!=FINAL:raise ValueError('terminal must be last marker')
        return dict(status='PASS_PRIMITIVE_FUNCTIONAL_ONLY',steps=33,async_events=7,assertions=252)
    wanted=expect['mutants'][str(mode)]
    bound={k:v for k,v in wanted.items() if not k.startswith('prefix_')}
    if diff!=[bound] or terminal or steps!=expect['steps'][:wanted['prefix_steps']] or events!=expect['async_events'][:wanted['prefix_async_events']]:raise ValueError('exact independent mutant witness/prefix required')
    if order!=expect['marker_order'][:len(order)]:raise ValueError('mutant prefix order changed')
    if not DIFF.fullmatch(lines[-1]) or bound['expected']==bound['actual']:raise ValueError('actual terminal DIFF required')
    return dict(status='EXPECTED_PRIMITIVE_DIFF',mode=mode,**bound)
