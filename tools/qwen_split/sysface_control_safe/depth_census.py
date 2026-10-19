#!/usr/bin/env python3
"""QW-SYSFACE3: generic-gate logic-depth census of a flat Yosys graph (SAFE checklist item 4).

Every state/macro/output endpoint's longest combinational path in two-input generic gates ($_NOT_ costs 0,
$_MUX_ 1) from any FF Q, macro output or input port.  Generic levels are emitted 1:1 into kept native cells
(one module per KIND), so this is the pre-map depth; native mapping adds ~10% (bc2l: 25 generic -> 28 native).
--limit L exits 1 when any endpoint exceeds L (default 20)."""
import argparse,collections,json,sys
from pathlib import Path

def census(m):
    isff=lambda t:t.startswith(('$_DFF','$_SDFF','$_ALDFF','$_DLATCH'))
    drv,gates={},{}
    for n,c in m['cells'].items():
        for p,bb in c['connections'].items():
            if c['port_directions'][p]=='output':
                for b in bb:
                    if isinstance(b,int):drv[b]=n
        if c['type'].startswith('$_') and not isff(c['type']):gates[n]=c
    memo={}
    def lvl(b):
        stack=[b]
        while stack:
            x=stack[-1]
            if not isinstance(x,int) or x in memo:stack.pop();continue
            g=gates.get(drv.get(x))
            if g is None:memo[x]=(0,x);stack.pop();continue
            ins=[y for p,bb in g['connections'].items() if g['port_directions'][p]=='input' for y in bb if isinstance(y,int)]
            todo=[y for y in ins if y not in memo]
            if todo:stack.extend(todo);continue
            best=max((memo[y] for y in ins),default=(0,x),key=lambda r:r[0])
            memo[x]=(best[0]+(0 if g['type']=='$_NOT_' else 1),best[1]);stack.pop()
        return memo[b] if isinstance(b,int) else (0,None)
    names={}
    for nn,v in m['netnames'].items():
        for i,b in enumerate(v['bits']):
            if isinstance(b,int) and (b not in names or len(nn)<len(names[b])):names[b]=nn+'['+str(i)+']'
    ends=[]
    for n,c in m['cells'].items():
        if n in gates:continue
        for p,bb in c['connections'].items():
            if c['port_directions'][p]=='input' and p not in ('C','CLK','clk'):
                for b in bb:
                    l,s=lvl(b);ends.append((l,n+'.'+p,names.get(s,str(s))))
    for pn,pd in m['ports'].items():
        if pd['direction']=='output':
            for b in pd['bits']:
                l,s=lvl(b);ends.append((l,'@'+pn,names.get(s,str(s))))
    ends.sort(key=lambda r:-r[0])
    return ends

def main():
    ap=argparse.ArgumentParser();ap.add_argument('graph');ap.add_argument('--top',default='qfd_sys_face')
    ap.add_argument('--limit',type=int,default=20);ap.add_argument('--out',required=True);a=ap.parse_args()
    m=json.loads(Path(a.graph).read_text())['modules'][a.top]
    ends=census(m);hist=collections.Counter(e[0] for e in ends)
    over=[e for e in ends if e[0]>a.limit]
    r={'graph':a.graph,'top':a.top,'limit':a.limit,'endpoints':len(ends),'max_levels':ends[0][0] if ends else 0,
       'histogram':{str(k):v for k,v in sorted(hist.items(),reverse=True)},'over_limit':len(over),
       'worst':[{'levels':l,'endpoint':e,'start':s} for l,e,s in ends[:60]],
       'status':'PASS' if not over else 'FAIL'}
    Path(a.out).write_text(json.dumps(r,indent=1)+'\n')
    print('DEPTH_CENSUS',r['status'],'max',r['max_levels'],'over',len(over),'hist',list(r['histogram'].items())[:8])
    sys.exit(0 if not over else 1)
if __name__=='__main__':main()
