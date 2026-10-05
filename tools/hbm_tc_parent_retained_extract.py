#!/usr/bin/env python3
"""Read-only census of retained mapped Verilog and text reports. Never opens ODB.

Can run via `ssh host python3 - DIR < this_file`; prints bounded JSON rather
than checkpoint/netlist payload. Flattened arithmetic cones are attributed by
reachability from semantic arithmetic FF D pins, stopping at FF/macros. Cells
shared between categories are counted once, in their own ownership mask.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys


def category(name):
    if '.u_comb.' in name and '.u_add.' in name:return 1
    if '.u_stack.' in name and '.u_add.' in name:return 2
    if name.startswith('g_scale[') and '.u_mul.' in name:return 4
    return 8


def digest(path):
    b=path.read_bytes()
    return dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),b


def library(text):
    result={};area=None;name=None
    for line in text.splitlines():
        m=re.match(r'attribute \\area "([\d.eE+-]+)"',line)
        if m:area=float(m[1])
        m=re.match(r'module \\(\S+)',line)
        if m:
            name=m[1]
            if area is not None:result[name]=dict(area_um2=area,outputs=[])
            area=None
        if name in result:
            m=re.match(r'  wire(?: width \d+)? output \d+ \\(\S+)',line)
            if m:result[name]['outputs'].append(m[1])
        if line=='end':name=None
    return result


def census(text,lib):
    normalize=lambda s:s.strip().replace('\\','').replace(' ','')
    widths={normalize(n):(int(a),int(b)) for a,b,n in re.findall(r'^  (?:wire|input|output) \[(\d+):(\d+)\] (\S+)\s*;',text,re.M)}
    def split(s):
        out=[];start=depth=0
        for i,c in enumerate(s):
            if c=='{':depth+=1
            elif c=='}':depth-=1
            elif c==',' and depth==0:out.append(s[start:i]);start=i+1
        return out+[s[start:]]
    def bits(s):
        s=normalize(s)
        if s.startswith('{'):
            inner=s[1:-1];m=re.fullmatch(r'(\d+)\{(.*)\}',inner)
            if m:return bits(m[2])*int(m[1])
            return [v for t in split(inner) for v in bits(t)]
        m=re.fullmatch(r"(\d+)'([bhd])([0-9a-fxz]+)",s,re.I)
        if m:return ['CONST']*int(m[1])
        m=re.fullmatch(r'(.*)\[(\d+):(\d+)\]',s)
        if m:return [m[1]+f'[{i}]' for i in range(int(m[2]),int(m[3])-1,-1)]
        if s in widths:
            a,b=widths[s];return [s+f'[{i}]' for i in range(a,b-1,-1)]
        return [s]
    aliases={};unsupported=[]
    for a,b in re.findall(r'^  assign (.*?) = (.*?);$',text,re.M):
        aa,bb=bits(a),bits(b)
        if len(aa)!=len(bb):unsupported.append([a,b]);continue
        for x,y in zip(aa,bb):aliases[x]=y
    def resolve(n):
        seen=set()
        while n in aliases and n not in seen:seen.add(n);n=aliases[n]
        return n
    cells=[];drivers={};instances=set();boundary=[];roots=[]
    for match in re.finditer(r'^  (\S+) (\S+)\s+\(\n(.*?)^  \);',text,re.M|re.S):
        master,name,body=match.groups();name=name.replace('\\','')
        if name in instances:raise ValueError('duplicate mapped instance '+name)
        instances.add(name)
        ports={p:normalize(v) for p,v in re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*$)',body,re.M|re.S)}
        outputs=lib[master]['outputs'];cid=len(cells)
        ins=[resolve(v) for p,e in ports.items() if p not in outputs for v in bits(e)]
        cells.append((master,name,ports,ins))
        for p in outputs:
            if p not in ports:continue
            for v in bits(ports[p]):
                n=resolve(v)
                if n=='CONST':continue
                if n in drivers:raise ValueError('multiple mapped drivers '+n)
                drivers[n]=cid
        if not master.endswith('_ASAP7_75t_R'):
            boundary.append(dict(instance=name,master=master,ports=ports));roots.extend(ins)
    for expr in re.findall(r'^  output (.*?);$',text,re.M):
        roots.extend(resolve(v) for v in bits(re.sub(r'^\[\d+:\d+\]\s*','',expr)))
    live=set();todo=list(roots)
    while todo:
        n=todo.pop();cid=drivers.get(n)
        if cid is None or cid in live:continue
        live.add(cid);todo.extend(cells[cid][3])
    # Always retain the declared target hard inventory. Only standard-cell
    # dead-logic pruning is compared with the actual import's metrics.
    live.update(i for i,c in enumerate(cells) if not c[0].endswith('_ASAP7_75t_R'))
    ffgroups=defaultdict(Counter);ffnames=set();aroots=defaultdict(list)
    counts=Counter(cells[i][0] for i in live)
    for i in live:
        master,name,ports,ins=cells[i]
        if master.startswith('DFF'):
            ffgroups[category(name)][master]+=1;ffnames.add(name)
            aroots[category(name)].append(resolve(ports['D']))
    ownership=[0]*len(cells)
    for mask,rr in aroots.items():
        todo=list(rr)
        while todo:
            n=todo.pop();cid=drivers.get(n)
            if cid is None or cid not in live or ownership[cid]&mask:continue
            master,name,ports,ins=cells[cid]
            if master.startswith('DFF') or not master.endswith('_ASAP7_75t_R'):continue
            ownership[cid]|=mask;todo.extend(ins)
    cones=defaultdict(Counter)
    for i in live:
        master=cells[i][0]
        if master.endswith('_ASAP7_75t_R') and not master.startswith('DFF'):cones[ownership[i]][master]+=1
    def priced(c):return dict(count=sum(c.values()),master_counts=dict(sorted(c.items())),area_um2=sum(lib[m]['area_um2']*n for m,n in c.items()))
    standard={m:n for m,n in counts.items() if m.endswith('_ASAP7_75t_R')}
    actualff=Counter()
    for c in ffgroups.values():actualff.update(c)
    return dict(instance_count=sum(counts.values()),raw_instance_count=len(cells),dead_instance_count=len(cells)-len(live),instance_names_unique=True,
        master_counts=dict(sorted(counts.items())),mapped_stdcell=priced(standard),
        unique_FF=priced(actualff),FF_names_sha256=hashlib.sha256('\n'.join(sorted(ffnames)).encode()).hexdigest(),
        FF_by_semantic_owner={str(k):priced(v) for k,v in sorted(ffgroups.items())},
        combinational_cones_by_unique_owner_mask={str(k):priced(v) for k,v in sorted(cones.items())},
        owner_mask_bits={'1':'combine arithmetic','2':'stack arithmetic','4':'row-scale arithmetic','8':'other resident FF inputs'},
        shared_cells_are_counted_once=True,unowned_mask0_retained=True,unsupported_assignments=unsupported,
        cone_method='live output/macro-input backward connectivity, including FF data/clock/reset; arithmetic upstream fanin from FF D stops at FF/hard macro; shared ownership counted once',
        cone_limit='Mask0 includes arithmetic output-only gates; mask8 may include arithmetic feed glue. Total live stdcell census must match retained import metrics before use.',
        boundary_macros=boundary)


def collect(base):
    base=Path(base);name='ot_gpu_sm_v' if base.name.startswith('sm_v') else 'ot_gpu_sm_q'
    rel=Path('asap7')/('chip_'+name)/'base';files={}
    def read(p):
        meta,b=digest(base/p);files[str(p)]=meta;return b.decode()
    canonical=read(Path('results')/rel/'1_1_yosys_canonicalize.rtlil')
    netlist=read(Path('results')/rel/'1_2_yosys.v')
    lib=library(canonical);result=census(netlist,lib)
    # Read metadata explicitly, avoiding expression evaluation order surprises.
    for f in ['config.mk','pdn.tcl','macro_placement.tcl','constraint.sdc']:
        if (base/f).exists():
            t=read(Path(f));files[f]['text']=t
    metrics={}
    for f in ['1_synth.json','2_1_floorplan.json','2_2_floorplan_macro.json','2_3_floorplan_tapcell.json','2_4_floorplan_pdn.json']:
        p=Path('logs')/rel/f
        if (base/p).exists():metrics[f]=json.loads(read(p))
    for f in ['1_synth.log','2_1_floorplan.log','2_2_floorplan_macro.log','2_3_floorplan_tapcell.log','2_4_floorplan_pdn.log']:
        p=Path('logs')/rel/f
        if (base/p).exists():
            t=read(p);files[str(p)]['text']=t
    defs=[str(p.relative_to(base)) for p in base.rglob('*.def')]
    odbs=[str(p.relative_to(base)) for p in (base/'results'/rel).glob('*.odb')]
    return dict(schema='retained-parent-mapped-census-v1',retained_directory=str(base),
        files=files,library_area_and_output_ports=lib,census=result,metrics=metrics,
        DEF_paths=defs,ODB_paths_metadata_only=odbs,ODB_payload_reads=False,
        no_jobs_or_physical_tools_run=True,source_authentication='Hash-pinned emitted mapped netlist and canonical RTLIL; historical RTL provenance must be verified separately before transferring census to current parent.')


def metadata(base):
    base=Path(base);files={};views={};sources=[]
    for p in sorted((base/'views').glob('*.lef')):
        meta,b=digest(p);s=b.decode();files[str(p)]=meta
        m=re.search(r'^MACRO\s+(\S+).*?SIZE\s+([\d.]+) BY ([\d.]+)',s,re.S|re.M)
        views[m[1]]=dict(size_um=[float(m[2]),float(m[3])],path=str(p),sha256=meta['sha256'])
    for p in base.glob('results/asap7/*/base/1_1_yosys_canonicalize.rtlil'):
        meta,b=digest(p);files[str(p)]=meta;s=b.decode()
        for m in re.finditer(r'^module (\S+)\n(.*?)^end$',s,re.M|re.S):
            prefix=s[max(0,m.start()-700):m.start()];body=m[2]
            if any(n in prefix+m[1] for n in ['ot_gpu_sm_', 'ot_gpu_fadd', 'ot_gpu_fmul','ot_gpu_stack','ot_gpu_tree','ot_hdc_fadd','ot_hdc_fmul']):
                sources.append(dict(module=m[1],attributes=prefix.split('end\n')[-1],parameters=re.findall(r'^  parameter (.*)$',body,re.M)))
    for p in base.glob('logs/asap7/*/base/1_2_yosys.log'):
        meta,b=digest(p);files[str(p)]=meta
        files[str(p)]['liberty_frontends']=[l for l in b.decode().splitlines() if 'Liberty frontend:' in l]
    return dict(files=files,retained_macro_views=views,canonical_source_attributes_and_parameters=sources,ODB_payload_reads=False)


if __name__=='__main__':
    result=metadata(sys.argv[1]) if '--metadata' in sys.argv else collect(sys.argv[1])
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
