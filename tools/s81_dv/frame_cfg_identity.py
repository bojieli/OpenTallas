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


def emit_bound_aliases(parent_text, band_text, frame, band_instance, report, images):
    """Materialise exact bound ROM selectors from the existing electrical identity proof.

    The binder deliberately gives each split macro its original full leaf path.
    The field writer uses the canonical parent INSTANCE suffix. Both names must
    read the same bytes, established from unchanged macro pins rather than a
    numeric-name guess. Existing images with different contents are preserved
    and rejected.
    """
    if not re.fullmatch(r'[A-Za-z_]\w*', frame) or not re.fullmatch(r'u_r\d+', band_instance):
        raise ValueError('unsafe or unknown frame/band identity')
    mapping = prove(parent_text, band_text)
    audits = {}
    for row in report.get('instance_path_params', []):
        inst = row.get('inst')
        if inst in audits:
            raise ValueError('duplicate bound image selector audit: ' + str(inst))
        audits[inst] = row
    rows = []
    pending = []
    for macro, suffix in sorted(mapping.items()):
        inst = frame + '.' + band_instance + '.' + macro
        row = audits.get(inst)
        if not row or row.get('module') != 'ot_rom_4096x72_m8' or row.get('param') != 'INSTANCE':
            raise ValueError('missing actual bound ROM image selector: ' + inst)
        if json.loads(row.get('value', 'null')) != inst:
            raise ValueError('bound ROM selector differs from its proven original leaf: ' + inst)
        source = frame + suffix + '.viamap.hex'
        data = (Path(images) / source).read_bytes()
        words = data.decode().splitlines()
        if len(words) != 512 or any(not re.fullmatch('[0-9a-fA-F]{144}', w) for w in words):
            raise ValueError('invalid 512x576 configuration via-map: ' + source)
        alias = inst + '.viamap.hex'
        dest = Path(images) / alias
        if dest.exists() and dest.read_bytes() != data:
            raise ValueError('preserve conflicting bound image alias: ' + alias)
        pending.append((dest, data))
        rows.append(dict(original_cell=inst, image=source, alias=alias,
                         image_sha256=hashlib.sha256(data).hexdigest()))
    # Validate the complete band before writing any alias.
    for dest, data in pending:
        if not dest.exists():
            dest.write_bytes(data)
    return rows


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
    ap.add_argument('--bind-report',type=Path,
                    help='emit exact runtime aliases using the binder original-leaf INSTANCE selector audit')
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
    if a.bind_report:
        record['aliases'] = emit_bound_aliases(bind_elab.module_body(parent,a.parent_module),
            bind_elab.module_body(band,a.band_module),a.frame,a.band_instance,
            json.loads(a.bind_report.read_text()),a.images)
        record['bind_report_sha256'] = hashlib.sha256(a.bind_report.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(record,indent=1)+'\n')
    print('CFG_IDENTITY PASS',a.frame,len(rows))

if __name__=='__main__':main()
