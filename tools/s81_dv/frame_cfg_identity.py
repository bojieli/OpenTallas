#!/usr/bin/env python3
"""Prove split-frame configuration-ROM image identity using unchanged macro pins.

The source macro's explicit INSTANCE suffix defines its image key. A split band
must preserve its exact macro instance name and all four electrical port
expressions. This proves a namespace mapping only, not a placed-frame calendar.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_elab


def macros(text):
    rx=re.compile(r'\bot_rom_4096x72_m8\s*(?:#\((.*?)\)\s*)?(u_c\d+_\d+)\s*\((.*?)\);',re.S)
    out={}
    for params,name,body in rx.findall(text):
        if name in out:raise ValueError('duplicate macro '+name)
        ports={k:re.sub(r'\s+','',v) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',body)}
        if set(ports)!={'ce_in','clk','addr_in','rd_out'}:raise ValueError('incomplete macro pins '+name)
        key=re.search(r'\.INSTANCE\(\{INSTANCE,\s*"([^"]+)"\}\)',params)
        out[name]=dict(ports=ports,suffix=key[1] if key else None)
    return out


def prove(parent_text,band_text):
    source,band=macros(parent_text),macros(band_text)
    if not band:raise ValueError('split band has no config ROMs')
    mapped={}
    for name,b in band.items():
        s=source.get(name)
        if not s or not s['suffix']:raise ValueError('source has no explicit image suffix for '+name)
        if s['ports']!=b['ports']:raise ValueError('split macro electrical pins changed: '+name)
        if s['suffix'] in mapped.values():raise ValueError('duplicate source image suffix')
        mapped[name]=s['suffix']
    return mapped


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--parent-source',default='rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv')
    ap.add_argument('--parent-module',default='col_h10_l4_lp')
    ap.add_argument('--band-source',default='rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h10_l4_lp_plan_kit.sv')
    ap.add_argument('--band-module',default='col_h10_l4_lp_r0')
    ap.add_argument('--band-instance',default='u_r0')
    ap.add_argument('--frame',required=True)
    ap.add_argument('--images',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();parent=a.root/a.parent_source;band=a.root/a.band_source
    m=prove(bind_elab.module_body(parent,a.parent_module),bind_elab.module_body(band,a.band_module))
    rows=[]
    for macro,suffix in sorted(m.items()):
        name=a.frame+suffix+'.viamap.hex';image=a.images/name
        data=image.read_bytes();words=data.decode().splitlines()
        if len(words)!=512 or any(not re.fullmatch('[0-9a-fA-F]{144}',w) for w in words):
            raise ValueError('invalid 512x576 via-map encoding for 4096x72 ROM: '+str(image))
        rows.append(dict(original_cell=a.frame+'.'+a.band_instance+'.'+macro,
                         image=name,image_sha256=hashlib.sha256(data).hexdigest()))
    record=dict(schema='opentallas.s81.frame_cfg_image_identity.v1',verdict='PASS_NAMESPACE_IDENTITY',
        source_sha256={a.parent_source:hashlib.sha256(parent.read_bytes()).hexdigest(),
                       a.band_source:hashlib.sha256(band.read_bytes()).hexdigest()},
        frame=a.frame,band=a.band_instance,count=len(rows),mapping=rows,
        qualification='Exact source/split macro pins and explicit source image suffix; no token/calendar/physical claim')
    a.out.write_text(json.dumps(record,indent=1)+'\n')
    print('CFG_IDENTITY PASS',a.frame,len(rows))

if __name__=='__main__':main()
