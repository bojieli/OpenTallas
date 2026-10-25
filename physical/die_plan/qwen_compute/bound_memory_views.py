"""Place real QC bound-memory views without changing RTL, ports, or cycles.

Call after materialization. All physical macro obstacles must participate in FT
station packing; this helper alone never authorizes a route.
"""
import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def attach(raw, manifest=None):
    manifest = manifest or json.loads((HERE/'bound_memory_views.json').read_text())
    report = {}
    for tn,t in raw['partition_types'].items():
        base = re.sub(r'_v\d+$', '', tn)
        source = base if base in manifest['types'] else 'sle_stm' if base=='slw_stm' else None
        if source is None:
            continue
        memories = copy.deepcopy(manifest['types'][source]['memories'])
        W,H = t['outline_um']
        for i,a in enumerate(memories):
            x,y = a['origin_um']; w,h = a['outline_um']
            if not (x>=5.4 and y>=5.4 and x+w<=W-5.4 and y+h<=H-5.4):
                raise ValueError(f'{tn}/{a["inst"]}: memory view does not fit with its halo')
            for b in memories[i+1:]:
                bx,by=b['origin_um'];bw,bh=b['outline_um']
                if not(x+w+10.8<=bx or bx+bw+10.8<=x or y+h+10.8<=by or by+bh+10.8<=y):
                    raise ValueError(f'{tn}: memory halos overlap {a["inst"]}/{b["inst"]}')
        existing={c['inst'] for c in memories}
        t['contents']=[c for c in t.get('contents',[]) if c['inst'] not in existing]+memories
        report[tn]=dict(macros=len(memories),area_um2=sum(c['outline_um'][0]*c['outline_um'][1] for c in memories),added_cycles=0)
    return report


def validate_synth_inventory(type_name, netlist, manifest=None):
    manifest=manifest or json.loads((HERE/'bound_memory_views.json').read_text())
    base=re.sub(r'_v\d+$','',type_name).split('__')[0]
    source=base if base in manifest['types'] else 'sle_stm' if base=='slw_stm' else base
    want={(c['module'],c['inst']) for c in manifest['types'][source]['memories']}
    actual=[]
    for line in Path(netlist).read_text().splitlines():
        s=line.split()
        if len(s)>=3 and s[0].startswith(('ot_sram_','ot_rom_','d2d_sram_')) and s[2]=='(':
            actual.append((s[0],s[1].lstrip('\\')))
    if set(actual)!=want or len(actual)!=len(want):
        raise ValueError(f'{type_name}: memory inventory differs: missing={want-set(actual)},extra={set(actual)-want}')
    return len(actual)
