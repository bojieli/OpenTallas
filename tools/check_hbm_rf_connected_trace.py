#!/usr/bin/env python3
"""Validate actual connected RF-side trace; synthetic unit traces aren't RTL proof."""
import argparse,json,re
from pathlib import Path

def fields(line):
    return {k:int(v) if re.fullmatch(r'-?\d+',v) else v for k,v in re.findall(r'(\w+)=([^ ]+)',line)}

def check(text):
    if 'CONNECTED_RF_FENCE_PASS' not in text or 'RESET_RF_FENCE_PASS' not in text:
        raise ValueError('missing directed/reset terminal PASS markers')
    if re.search(r'\$fatal|%Error|Assertion failed|Aborting',text):raise ValueError('fatal in trace')
    cases={};summaries=[]
    for line in text.splitlines():
        kind=line.split(' ',1)[0];r=fields(line)
        if kind=='CASE':summaries.append(r)
        elif kind in ('STAMP','RF_VECTOR_WRITE','RF_VECTOR_ACK_VISIBLE','RF_VECTOR_ACK_RETIRE','SIMD_ALIAS_ACCEPT'):
            cases.setdefault(r['case'],[]).append((kind,r))
    if len(summaries)!=4:raise ValueError('expected4 connected cases plus separate reset case')
    q= summaries[0]['qwen']
    if q not in (0,1) or any(c['qwen']!=q for c in summaries):raise ValueError('mixed/native target selection')
    if [(c['rows'],c['scratch'],c['hold_cycles']) for c in summaries]!=[(16,0,0),(16,1,0),(4096,0,0),(4096,0,240)]:raise ValueError('missing native full4096/ACK hold cases')
    if not re.search(r'RESET_RF_FENCE_PASS qwen='+str(q)+r' actualmatrixproducer=1 staleepoch_rejected=1',text):raise ValueError('reset producer evidence missing')
    out=[]
    for c in summaries:
        ev=cases[c['id']];n=c['vectors'];q=c['qwen'];rows=c['rows']
        if n!=(rows*(16 if q else 8)+127)//128:raise ValueError('native vector geometry mismatch')
        stamp={}
        for kind,r in ev:
            if kind=='STAMP':stamp.setdefault(r['name'],[]).append(r['cycle'])
        def one(name):
            a=stamp.get(name,[])
            if len(a)!=1:raise ValueError('missing/nonunique stamp '+name)
            return a[0]
        writes=[r for k,r in ev if k=='RF_VECTOR_WRITE'];vis=[r for k,r in ev if k=='RF_VECTOR_ACK_VISIBLE'];ret=[r for k,r in ev if k=='RF_VECTOR_ACK_RETIRE']
        ops=[r for k,r in ev if k=='SIMD_ALIAS_ACCEPT']
        if any(len(a)!=n for a in (writes,vis,ret)) or len(ops)!=2*n:raise ValueError('write/ACK/dependent operation count')
        for i,(w,v,r) in enumerate(zip(writes,vis,ret)):
            if (w['index'],v['index'],r['index'])!=(i,i,i) or len({w['epoch'],v['epoch'],r['epoch']})!=1:raise ValueError('address/epoch provenance')
            if not w['cycle']<=v['cycle']<=r['cycle']:raise ValueError('ACK before write/visible')
        if ret[-1]['cycle']-vis[-1]['cycle']<c['hold_cycles']:raise ValueError('requested ACK backpressure not observed')
        fence=one('RF_fence_valid')
        if fence<ret[-1]['cycle'] or fence<one('producer_last_rv'):raise ValueError('premature connected fence')
        for j,o in enumerate(ops):
            expected_index=j%n;expected_pass=j//n
            if (o['pass'],o['index'],o['a'],o['b'],o['dst'])!=(expected_pass,expected_index,expected_index,expected_index,expected_index):raise ValueError('dependent in-place operand/destination mapping')
            if o['cycle']<=fence:raise ValueError('consumer accepted before fence')
        if len({w['epoch'] for w in writes})!=1:raise ValueError('operation epoch changed')
        if any(a['cycle']>=b['cycle'] for a,b in zip(ops,ops[1:])):raise ValueError('nonsequential SIMD acceptance')
        first=ops[0]['cycle'];last=ops[-1]['cycle']
        if any(first<=w['cycle']<=last for w in writes):raise ValueError('host overwrite between dependent operations')
        if len(stamp.get('SIMD_last_done',[]))!=2:raise ValueError('missing two dependent chain completions')
        if ops[n]['cycle']<=stamp['SIMD_last_done'][0]:raise ValueError('second pass before prior result completion')
        lastdone=stamp['SIMD_last_done'][-1];read=one('RF_operand_read_visible');x=one('consumer_x_last_write');start=one('consumer_start');issue=one('consumer_first_valid_issue')
        if not lastdone<=read<=x<start<=issue:raise ValueError('result/operand/xvisibility causal order')
        if c['scratch']:
            w=one('scratch_write_done');r=one('scratch_read_done')
            if not read<=w<=r<=x:raise ValueError('scratch visibility chain')
        if one('producer_first_rv')>one('producer_last_rv'):raise ValueError('producer result order')
        out.append(dict(case=c['id'],qwen=q,rows=rows,vectors=n,producer_first_to_next_issue_cycles=issue-one('producer_first_rv'),
            producer_last_to_next_issue_cycles=issue-one('producer_last_rv'),RF_last_visible_to_next_issue_cycles=issue-vis[-1]['cycle'],RF_last_retire_to_next_issue_cycles=issue-ret[-1]['cycle'],RF_fence_to_next_issue_cycles=issue-fence,actual_last_ACK_hold_cycles=ret[-1]['cycle']-vis[-1]['cycle'],
            host_write_count=n,dependent_alias_operations=2*n,scratch=bool(c['scratch'])))
    return dict(schema='opentallas.connected-RF-fence.trace-check.v1',verdict='PASS_DIRECTED_CONNECTED_TRACE_ONLY',cases=out,
                clock_period_ns=10,exhaustive_arithmetic=False,SSFF=False,physical_credit=False,full_token_credit=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    data=json.dumps(check(a.log.read_text()),indent=2,sort_keys=True)+'\n'
    if a.out:
        with a.out.open('x') as f:f.write(data)
    else:print(data,end='')
