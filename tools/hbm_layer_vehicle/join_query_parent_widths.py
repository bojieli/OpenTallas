"""Join explicit QUERY carrier widths into a disabled pure-connectivity parent.

Every changed net must have exactly two changed endpoints and its declaration,
with matching old/new widths at both endpoints. No casts, aliases or truncation.
"""
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import prepare_programme_local_move as move


def ports(text):
    header=text[:text.index(');')]
    return {m[4]:(int(m[2])-int(m[3])+1 if m[2] else 1)
            for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',header)}


def join(top,rows,before):
    nets=defaultdict(list)
    for row in rows:
        name=row['module'];old=ports((before/(name+'.sv')).read_text())
        patterns=list(re.finditer(r'^\s*'+re.escape(name)+r'\b',top,re.M))
        assert len(patterns)==1,('exact one selected parent instance required',name,len(patterns))
        pos=patterns[0].end()
        while top[pos].isspace():pos+=1
        if top[pos]=='#':pos=move.close_at(top,top.index('(',pos))+1
        instance=re.match(r'\s*(\w+)',top[pos:])[1]
        actual=move.expression_ports(move.call(top,instance)[2])
        for port,p in row['ports'].items():
            width=p['width']
            if old[port]!=width:
                wire=actual[port]
                assert re.fullmatch(r'\w+',wire),('named full-vector connection required',wire)
                nets[wire].append(dict(instance=instance,module=name,port=port,
                                       old_width=old[port],new_width=width))
    receipt=[]
    for net,uses in sorted(nets.items()):
        assert len(uses)==2,('complete source and destination required',net,uses)
        olds={x['old_width']for x in uses};news={x['new_width']for x in uses}
        assert len(olds)==len(news)==1,('endpoint widths differ',net,uses)
        old,new=next(iter(olds)),next(iter(news))
        pattern=r'(\bwire\s+\[)(\d+)(:0\]\s+'+re.escape(net)+r'\s*;)'
        decl=list(re.finditer(pattern,top));assert len(decl)==1 and int(decl[0][2])+1==old,(net,'old declaration differs')
        assert len(re.findall(r'\b'+re.escape(net)+r'\b',top))==3,(net,'unhandled consumer/part-select/assignment')
        top,count=re.subn(pattern,lambda m:m[1]+str(new-1)+m[3],top);assert count==1
        receipt.append(dict(net=net,old_width=old,new_width=new,endpoints=uses,
                            changed='whole shared vector declaration only; no cast/pad/truncate'))
    assert len(receipt)==12,('expected exact12 QUERY shared nets',len(receipt))
    return top,receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--top',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--before-query',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();old=a.top.read_text();new,rows=join(old,json.loads(a.manifest.read_text())['rows'],a.before_query)
    if a.out.exists():raise ValueError('preserve immutable existing output')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(new)
    a.receipt.write_text(json.dumps(dict(status='PASS_DISABLED_PARENT_WIDTH_JOIN',rows=rows,
      old_sha256=hashlib.sha256(old.encode()).hexdigest(),new_sha256=hashlib.sha256(new.encode()).hexdigest(),
      complete_query_nets=12,source_proof_transfer=False,frontend_compiled=False,
      physical_clock_reset_source_model_adoption=False),indent=2)+'\n')
    print('PASS_DISABLED_PARENT_WIDTH_JOIN',len(rows),'nets')


if __name__=='__main__':main()
