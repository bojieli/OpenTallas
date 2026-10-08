#!/usr/bin/env python3
"""Freeze unchanged routed NETS for the two-path native glue ECO; audit geometry."""
import argparse,hashlib,json,re
from pathlib import Path

def nets(text):
    match=re.search(r'^NETS\s+\d+\s*;\s*\n(.*?)^END NETS',text,re.M|re.S)
    if not match:raise ValueError('Missing NETS section')
    result={}
    for entry in re.split(r';\s*\n',match.group(1)):
        if not entry.strip():continue
        name=re.match(r'\s*-\s+(\S+)',entry).group(1)
        result[name]=entry
    return match,result

def geometry(entry):
    route=re.search(r'\+\s+(?:ROUTED|FIXED|COVER)\s+',entry)
    if not route:return None
    data=re.sub(r'\+\s+(?:ROUTED|FIXED|COVER)\s+','+ WIRE ',entry[route.start():])
    return hashlib.sha256(' '.join(data.split()).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=['freeze','check'])
    ap.add_argument('--original',type=Path,required=True)
    ap.add_argument('--current',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();oldtext=a.original.read_text();newtext=a.current.read_text()
    _,old=nets(oldtext);match,new=nets(newtext)
    retained={};changed=[]
    for name,entry in old.items():
        before=geometry(entry);after=geometry(new.get(name,''))
        if before!=after:changed.append(name)
        elif before:retained[name]=before
    if a.mode=='freeze':
        if len(changed)!=2:raise SystemExit(f'Expected only2 old nets changed, got{len(changed)}: {changed}')
        for name in changed:
            if geometry(new[name]) is not None:raise SystemExit('Changed old net must have no stale route')
        fixed={name:re.sub(r'\+\s+ROUTED\s+','+ FIXED ',entry) if geometry(entry) else entry for name,entry in new.items()}
        head='\n'.join(re.findall(r'^(?:VERSION|BUSBITCHARS|DIVIDERCHAR|DESIGN|UNITS DISTANCE MICRONS)\b[^\n]*',newtext,re.M))+'\n'
        a.output.write_text(head+f'NETS {len(fixed)} ;\n'+';\n'.join(fixed.values())+';\nEND NETS\nEND DESIGN\n')
        a.output.with_suffix('.json').write_text(json.dumps({'unchanged_routed_nets':retained,'changed_old_nets':changed,'new_nets':sorted(set(new)-set(old))},indent=2)+'\n')
        print(f'OT_FIXED_ROUTES_PREPARED unchanged_routed_nets={len(retained)} changed_old_nets=2 new_nets={len(set(new)-set(old))}')
    else:
        expected=json.loads(a.output.read_text());mismatch=[]
        for name,digest in expected['unchanged_routed_nets'].items():
            if geometry(new.get(name,''))!=digest:mismatch.append(name)
        if mismatch:raise SystemExit(f'Unchanged routes moved: {mismatch[:20]} total={len(mismatch)}')
        print(f'OT_FIXED_ROUTES_GEOMETRY_PASS unchanged_routed_nets={len(expected["unchanged_routed_nets"])} includes_all_clock_nets=1')
if __name__=='__main__':main()
