#!/usr/bin/env python3
"""Extract only exact public identity wires from the current split wrapper.
Escaped hierarchical pins, renamed ports, resized/full buses and packed aliases
are excluded. Native parent width equality is checked by native_station_map.
"""
import argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source');ap.add_argument('--top',required=True);ap.add_argument('--nlink',type=int,required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
p=Path(a.source);s=p.read_text();start=list(re.finditer(r'^module\s+'+re.escape(a.top)+r'\s*\(',s,re.M))
if len(start)!=1:raise SystemExit('expected one literal current wrapper top')
top=s[start[0].start():];hdr=top.split(');',1)[0];decl={}
for m in re.finditer(r'\b(input|output|inout)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*[,\n)]',hdr):
 d,hi,lo,n=m.groups();decl[n]=(d,abs(int(hi)-int(lo))+1 if hi else 1)
raw=s[:start[0].start()];rawdecl={}
for m in re.finditer(r'^\s*(input|output|inout)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;',raw,re.M):
 d,hi,lo,n=m.groups();rawdecl[n]=(d,abs(int(hi)-int(lo))+1 if hi else 1)
inst=re.search(re.escape(a.top)+r'_x\s+u_x\s*\((.*?)\);',top,re.S)
if not inst:raise SystemExit('expected one explicit current u_x wrapper instance')
buses={};widths={};excluded=[]
for m in re.finditer(r'\.([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*)\s*\)',inst[1]):
 formal,expr=m.groups()
 if formal!=expr or formal not in decl or rawdecl.get(formal)!=decl[formal]:excluded.append(dict(formal=formal,expr=expr,why='not same public name/direction/width in raw and wrapper'));continue
 d,w=decl[formal];buses[formal]=[formal] if w==1 else [f'{formal}[{i}]' for i in range(w)];widths[formal]=w
r=dict(module=a.top,variant=dict(nlink=a.nlink),source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),convention='Exact current wrapper plain .formal(formal), equal raw/wrapper width/direction, increasing [0..W-1] bits; parent-native width must equal W.',public_identity_only=True,identity_public_widths=widths,buses=buses,excluded=excluded)
Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(a.top,'public identity ports',len(buses),'bits',sum(widths.values()))
