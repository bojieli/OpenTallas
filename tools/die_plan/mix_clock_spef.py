#!/usr/bin/env python3
"""Select actual routed per-net RC from uniform 4W and 8W estimates.

Both SPEFs must come from the same loaded routed design, estimated once with
M8/M9 R/4,C*1.3 and once R/8,C*1.6.  Selection preserves their via resistors;
scaling every resistor in an existing SPEF would incorrectly scale vias too.
"""
import argparse
import json
from pathlib import Path


def header(stream):
    lines=[];names={};inmap=False
    for line in stream:
        if line.startswith('*D_NET '):return lines,names,line
        lines.append(line)
        if line.startswith('*NAME_MAP'):inmap=True
        elif inmap and line.startswith('*') and line.split()[0][1:].isdigit():
            k,v=line.split(maxsplit=1);names[k]=v.strip()
    return lines,names,None


def sections(stream,first,names):
    start=first
    while start is not None:
        if not start.startswith('*D_NET '):raise ValueError('expected D_NET')
        token=start.split()[1];name=names.get(token,token);lines=[start]
        for line in stream:
            lines.append(line)
            if line.startswith('*END'):break
        else:raise ValueError(f'incomplete net {name}')
        yield name,lines
        start=None
        for line in stream:
            if line.startswith('*D_NET '):start=line;break


def wide_nets(clock,prefix='ck_'):
    cells=json.loads((clock/'place.json').read_text());data=json.loads((clock/'nets.json').read_text())
    ports={p for _,p in data['ports']};wide=set()
    for n in data['nets']:
        c=cells.get(n['drv'],{});kind=c.get('kind');level=c.get('level')
        leg=0 if n['drv'].startswith('port:') else ((level or 0)+1 if kind=='node' else (level or 0) if kind=='rep' else 99)
        if leg<=6:wide.add(n['name'] if n['name'] in ports else prefix+n['name'])
    return wide


def mix(base,widefile,wide,out):
    with open(widefile) as f:
        _,map8,first=header(f)
        selected={n:lines for n,lines in sections(f,first,map8) if n in wide}
    missing=wide-set(selected)
    if missing:raise ValueError(f'8W estimate missing assigned nets: {sorted(missing)[:8]}')
    used=set();count=0
    with open(base) as src,open(out,'w') as dest:
        h,map4,first=header(src)
        if map4!=map8:raise ValueError('uniform estimates have different NAME_MAP; regenerate from the same loaded design')
        dest.writelines(h)
        for name,lines in sections(src,first,map4):
            if name in wide:lines=selected[name];used.add(name)
            dest.writelines(lines);count+=1
    if used!=wide:raise ValueError('4W base missing selected clock nets')
    return dict(total_nets=count,nets8w=len(used),nets4w_or_unchanged=count-len(used),vias='preserved from each routed estimate')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('base4w',type=Path);ap.add_argument('wide8w',type=Path)
    ap.add_argument('--clock',type=Path,required=True);ap.add_argument('--prefix',default='ck_');ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();print(json.dumps(mix(a.base4w,a.wide8w,wide_nets(a.clock,a.prefix),a.out),indent=2))
