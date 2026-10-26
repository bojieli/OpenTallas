"""Export a fixed no-repair configuration of an existing SRAM hard macro.

Array, area, regular-pin geometry and regular timing arcs are preserved. Repair
controls are internal zeros in the model; their external pins are absent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

REPAIR = {'rr_en', 'rr_addr', 'cr_en', 'cr_sel'}


def base(name):
    return name.split('[')[0]


def verilog(text, *, behavior):
    start=text.index('module '); end=text.index(');',start)
    header=text[start:end]
    removed=[]; kept=[]; ties=[]
    for line in header.splitlines():
        m=re.search(r'input\s+wire\s+(?:(\[\d+:\d+\])\s+)?(\w+)\s*,?\s*$',line)
        if m and m.group(2) in REPAIR:
            rng=m.group(1) or ''
            removed.append(m.group(2))
            ties.append(f"    wire {rng} {m.group(2)} = '0;")
        else: kept.append(line)
    if set(removed)!=REPAIR:raise ValueError('expected four repair control buses')
    kept[-1]=kept[-1].rstrip().removesuffix(',')
    return text[:start]+'\n'.join(kept)+text[end:end+2]+ ('\n'+'\n'.join(ties) if behavior else '')+text[end+2:]


def liberty(text):
    remove=[]
    for m in re.finditer(r'\b(?:bus|pin)\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{',text):
        if base(m.group(1)) not in REPAIR:continue
        depth=1;i=m.end()
        while depth and i<len(text):
            if text[i]=='{':depth+=1
            elif text[i]=='}':depth-=1
            i+=1
        if depth:raise ValueError('unbalanced Liberty pin')
        remove.append((m.start(),i))
    if len(remove) not in (4,32):raise ValueError(f'expected4 repair buses or32 bits, got{len(remove)}')
    for a,b in reversed(remove):text=text[:a]+text[b:]
    return text


def lef(text):
    pattern=re.compile(r'^\s*PIN\s+(\S+)\s*\n.*?^\s*END\s+\1\s*$',re.M|re.S)
    count=0
    def replace(m):
        nonlocal count
        if base(m.group(1)) in REPAIR:count+=1;return ''
        return m.group(0)
    text=pattern.sub(replace,text)
    if count!=32:raise ValueError(f'expected32 LEF repair pins, got{count}')
    return text


def export(src,dst):
    src=Path(src);parent=Path(dst);old=src.name;new=old+'_nr';final=parent/new
    if old!='ot_sram_1r1w_512x128_m4_r2c2':raise ValueError('unsupported source macro')
    if final.exists():raise ValueError('use a fresh output path')
    parent.mkdir(parents=True,exist_ok=True)
    temporary=tempfile.TemporaryDirectory(dir=parent,prefix='.fixed-repair-')
    dst=Path(temporary.name)
    for suffix in ['.v','_bb.v','.lef','_tt.lib','_ff.lib']:
        t=(src/(old+suffix)).read_text()
        if suffix.endswith('.v'):t=verilog(t,behavior=suffix=='.v')
        elif suffix=='.lef':t=lef(t)
        else:t=liberty(t)
        (dst/(new+suffix)).write_text(t.replace(old,new))
    info=json.loads((src/(old+'.json')).read_text());info['spec']['name']=new
    info['fixed_repair_disabled']={'original_master':old,'controls':sorted(REPAIR),'removed_input_bits':32,'normal_port_behavior':'unchanged vs original repair controls zero','array_area_and_regular_pin_geometry':'unchanged; spare array cells retained, no area credit'}
    info['views']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()}
    (dst/(new+'.json')).write_text(json.dumps(info,indent=2)+'\n')
    dst.rename(final)
    temporary.cleanup()
    return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('out');a=p.parse_args();print(export(a.source,a.out))
