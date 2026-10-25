#!/usr/bin/env python3
"""Explicit physical projection of the approved UCIe functional line proxy.

Canonical functional emission remains unchanged. The hard physical abstract has
registered FDI pins; line_v/flit and far_v/flit represent its serialized package
service, not parallel digital bumps. Only exact declared direct proxy wiring may
be removed from a physical copy. Any additional use or ABI drift fails closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PROXY={'link_v':('output',1),'link_flit':('output',583),
       'far_v':('input',1),'far_flit':('input',583)}
FDI={'clk','rst_n','tx_up','tx_v','tx_flit','rx_v','rx_flit'}
CELL='ot_qkvd_ucie_x64_phy'


def clean(s):
    return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)


def project(text, *, instance='u_ucie_rom', prefix='bump_ucie_rom_', wrapper=False):
    names={p:prefix+p for p in PROXY}
    original=clean(text)
    for p,(direction,width) in PROXY.items():
        name=names[p]
        declarations=list(re.finditer(rf'^\s*{direction}\s+wire\s*(?:\[(\d+):0\]\s*)?{re.escape(name)}\s*,?\s*$',original,re.M))
        if len(declarations)!=1:raise ValueError(f'{name}: expected one exact {direction} declaration')
        actual=int(declarations[0].group(1))+1 if declarations[0].group(1) is not None else 1
        if actual!=width:raise ValueError(f'{name}: width {actual}, expected {width}')
        if len(re.findall(rf'\b{re.escape(name)}\b',original))!=(3 if wrapper else 2):raise ValueError(f'{name}: must have only declaration and direct hard/wrapper connection')
    target=re.escape(instance)
    pat=(rf'\bkv3_sys_c_part_bound\s+(?:#\(.*?\)\s*)?{target}\s*\((.*?)\)\s*;' if wrapper
         else rf'\b{CELL}\s+(?:#\(.*?\)\s*)?{target}\s*\((.*?)\)\s*;')
    blocks=list(re.finditer(pat,original,re.S))
    if len(blocks)!=1:raise ValueError('expected one exact target instance')
    block=blocks[0].group(1)
    pins=set(re.findall(r'\.([A-Za-z_]\w*)\s*\(',block))
    expected=set(names.values()) if wrapper else set(PROXY)
    if not wrapper and pins!=FDI|set(PROXY):raise ValueError(f'physical/functional hard ABI drift: {sorted(pins)}')
    for p,n in names.items():
        pin=n if wrapper else p
        if len(re.findall(rf'\.{re.escape(pin)}\s*\(\s*{re.escape(n)}\s*\)',block))!=1:raise ValueError(f'{pin}: not direct exact proxy connection')
    # Operate on original generated source, preserving all remaining expressions.
    out=text
    for p,n in names.items():
        out,count=re.subn(rf'^\s*(?:input|output)\s+wire\s*(?:\[\d+:0\]\s*)?{re.escape(n)}\s*,?[^\n]*\n','',out,flags=re.M)
        if count!=1:raise ValueError(f'{n}: source declaration not recognized')
        pin=n if wrapper else p
        out,count=re.subn(rf'^\s*\.{re.escape(pin)}\s*\(\s*{re.escape(n)}\s*\)\s*,?[^\n]*\n','',out,flags=re.M)
        if count!=1:raise ValueError(f'{pin}: source connection not recognized')
    out=re.sub(r',([ \t]*(?://[^\n]*)?\n[ \t]*\);)',r'\1',out)
    if any(re.search(rf'\b{re.escape(n)}\b',clean(out)) for n in names.values()):raise ValueError('dangling functional proxy')
    audit=dict(cell=CELL,instance=instance,kind='port_only_wrapper' if wrapper else 'hard_macro',removed=[dict(pin=p,port=names[p],dir=d,width=w) for p,(d,w) in PROXY.items()],physical_fdi_pins=sorted(FDI),source_sha256=hashlib.sha256(text.encode()).hexdigest(),physical_sha256=hashlib.sha256(out.encode()).hexdigest())
    return out,audit


def project_filelist(filelist, outdir, *, require_wrapper=True):
    """Produce physical copies of exact native SYS_C + optional generated wrapper."""
    filelist=Path(filelist).resolve();outdir=Path(outdir).resolve();outdir.mkdir(parents=True,exist_ok=True)
    files=[];audits=[];counts={'hard_macro':0,'port_only_wrapper':0}
    for k,line in enumerate(filelist.read_text().splitlines()):
        if not line.strip() or line.lstrip().startswith('#'):continue
        f=Path(line.strip());f=f if f.is_absolute() else filelist.parent/f
        text=f.read_text()
        if re.search(r'\bbump_ucie_rom_link_v\b',clean(text)):
            wrapper=not re.search(r'\b'+CELL+r'\s+(?:#\(.*?\)\s*)?u_ucie_rom\s*\(',clean(text),re.S)
            text,audit=project(text,wrapper=wrapper,instance='u_bound' if wrapper else 'u_ucie_rom')
            audit['source']=str(f);audits.append(audit);counts[audit['kind']]+=1
            dst=outdir/f'{k:03d}_{f.name}';dst.write_text(text);files.append(str(dst))
        else:files.append(str(f.resolve()))
    if counts['hard_macro']!=1 or counts['port_only_wrapper']!=int(require_wrapper):
        raise ValueError(f'physical filelist projection count mismatch: {counts}')
    (outdir/'physical_rtl.f').write_text('\n'.join(files)+'\n')
    return audits


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('--audit',type=Path,required=True);p.add_argument('--instance',default='u_ucie_rom');p.add_argument('--prefix',default='bump_ucie_rom_');p.add_argument('--wrapper',action='store_true');p.add_argument('--filelist',action='store_true');p.add_argument('--no-wrapper',action='store_true');a=p.parse_args()
    if a.filelist:
        audit=dict(files=project_filelist(a.source,a.out,require_wrapper=not a.no_wrapper))
        text=None
    else:
        text,audit=project(a.source.read_text(),instance=a.instance,prefix=a.prefix,wrapper=a.wrapper)
    audit['contract']=dict(functional_proxy_only=True,physical_parallel_flit_bumps=False,word_bits=583,fdi_ghz=1.2,required_gbps=699.6,tx_lanes=64,rx_lanes=64,lane_gbps=16,capacity_gbps_each_direction=1024,physical_signal_sites=144,latency_fdi_cycles=dict(best=3,typical=5,worst=9),scope='Existing generated PHY/package abstract; no licensed bump-map or internal GDS qualification')
    if text is not None:
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
    a.audit.write_text(json.dumps(audit,indent=1)+'\n')

if __name__=='__main__':main()
