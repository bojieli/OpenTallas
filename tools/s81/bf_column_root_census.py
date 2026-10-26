#!/usr/bin/env python3
"""Measure a proposed ten-root partition on the exact historical mapped column.

Mapped gate counts/area, data-cone cuts and old routed sink spans are measured.
This does not predict CTS insertion or qualify the new source. No guessed die
footprint is emitted. Shared combinational cones stay in the boundary group.
"""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path


def group(n):
    p='g_bf.g_fqt.u_bf.'
    m=re.search(r'g_bf\.g_fqt\.u_bf\.g_l\[(\d+)\]',n)
    if m:return 4+int(m[1])//4
    if n.startswith(p+'g_lv[0].'):return 8
    if n.startswith(p+'g_lv['):return 9
    if n.startswith(('g_l3.u_l0.','g_ch3.u_c0.','g_pa2.','u_pp.','u_pt.')):return 1
    if n.startswith(('g_l3.u_l1.','g_ch3.u_c1.')):return 2
    if n.startswith('g_tr5.') or re.match(r'^(perr|pnseg|ppos|prow|pseg|pv|pval)(\[|\$)',n):return 3
    return 0


def normalize(s):return s.strip().replace('\\','')
def nets(s):return [normalize(n) for n in s.strip('{} ').split(',') if "'" not in n]


def libraries(paths):
    d={}
    for path in paths:
        text=Path(path).read_text()
        for m in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1\s*$',text,re.M|re.S):
            size=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',m[2]);assert size,m[1]
            ports={}
            for p in re.finditer(r'\bPIN (\S+)\s+(.*?)\bEND \1\b',m[2],re.S):
                dr=re.search(r'DIRECTION (INPUT|OUTPUT)',p[2])
                if dr:ports[p[1].split('[')[0]]=dr[1]
            d[m[1]]={'area':float(size[1])*float(size[2]),'ports':ports}
    return d


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--netlist-zstd',type=Path,required=True);ap.add_argument('--def-zstd',type=Path,required=True);ap.add_argument('--lef',action='append',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    lib=libraries(a.lef);text=subprocess.check_output(['zstdcat',str(a.netlist_zstd)],text=True)
    cells=[];drivers={};seq=[]
    for b in text.split(';'):
        m=re.match(r'\s*(\w+)\s+(\\?\S+)\s+\((.*)\)\s*$',b,re.S)
        if not m or m[1] not in lib or m[1].startswith(('FILLER','DECAP','TAPCELL')):continue
        typ,name=m[1],normalize(m[2]);ports={p:nets(n) for p,n in re.findall(r'\.(\w+)\(([^)]*)\)',m[3])}
        inputs=[];outputs=[]
        for p,nn in ports.items():
            (outputs if lib[typ]['ports'].get(p)=='OUTPUT' else inputs).extend(nn)
        sequential=typ.startswith(('DFF','SDFF','DLATCH'));idx=len(cells)
        cells.append((typ,name,ports,inputs,outputs,sequential))
        for n in outputs:drivers[n]=idx
        if sequential:seq.append(idx)
    assert len(seq)==53493,len(seq)
    # Backward clock-cone walk: clock tree cells do not define functional cut area.
    clocks=set();todo=[n for i in seq for n in cells[i][2].get('CLK',cells[i][2].get('GATE',[]))]
    seen=set()
    while todo:
        n=todo.pop()
        if n in seen:continue
        seen.add(n);i=drivers.get(n)
        if i is None or cells[i][5]:continue
        clocks.add(i);typ,_,ports,ins,_,_=cells[i]
        todo.extend(ports.get('CLK',ins) if typ.startswith('ICG') else ins)
    # A cell's target mask is the set of first sequential destinations reached.
    masks=[0]*len(cells);queue=collections.deque()
    for i in seq:
        g=group(cells[i][1]);masks[i]=1<<g
        for n in cells[i][2].get('D',[]):queue.append((n,1<<g))
    while queue:
        n,mask=queue.popleft();i=drivers.get(n)
        if i is None or i in clocks or cells[i][5] or masks[i]&mask==mask:continue
        masks[i]|=mask
        for nn in cells[i][3]:queue.append((nn,mask))
    assign=[(mask.bit_length()-1 if mask and mask&(mask-1)==0 else 0) for mask in masks]
    rows={i:dict(sinks=0,cells=0,area_um2=0.0,old_sink_bounds_um=None) for i in range(10)}
    for i,c in enumerate(cells):
        if i in clocks:continue
        g=assign[i];rows[g]['cells']+=1;rows[g]['area_um2']+=lib[c[0]]['area'];rows[g]['sinks']+=int(c[5])
    edges=collections.defaultdict(set)
    for i,c in enumerate(cells):
        if i in clocks:continue
        dst=assign[i]
        for port,nn in c[2].items():
            if port=='CLK' or lib[c[0]]['ports'].get(port)=='OUTPUT':continue
            for n in nn:
                j=drivers.get(n);src=assign[j] if j is not None else 0
                if j in clocks:continue
                if src!=dst:edges[src,dst].add(n)
    coords={};proc=subprocess.Popen(['zstdcat',str(a.def_zstd)],stdout=subprocess.PIPE,text=True)
    on=False
    for line in proc.stdout:
        if line.startswith('COMPONENTS '):on=True;continue
        if line.startswith('END COMPONENTS'):break
        if not on:continue
        m=re.match(r'\s*- (\S+) (DFF\S*|SDFF\S*|DLATCH\S*) .*?\+ (?:PLACED|FIXED) \( (\d+) (\d+) \)',line)
        if m:coords[normalize(m[1])]=(int(m[3])/1000,int(m[4])/1000)
    proc.stdout.close();proc.terminate();proc.wait()
    assert len(coords)==53493,len(coords)
    for i in seq:
        p=coords[cells[i][1]];r=rows[assign[i]];b=r['old_sink_bounds_um']
        r['old_sink_bounds_um']=[min(p[0],b[0]),min(p[1],b[1]),max(p[0],b[2]),max(p[1],b[3])] if b else [*p,*p]
    for r in rows.values():
        r['area_um2']=round(r['area_um2'],3);b=r['old_sink_bounds_um'];r['old_span_um']=[round(b[2]-b[0],3),round(b[3]-b[1],3)] if b else None
    out={'scope':'Historical actual mapped-netlist partition measurement; new ten-root source not synthesized or physically qualified. Clock buffer area excluded; new local roots/hold/seam cost pending.',
         'mapped_netlist_sha256_zstd':hashlib.sha256(a.netlist_zstd.read_bytes()).hexdigest(),'routed_def_sha256_zstd':hashlib.sha256(a.def_zstd.read_bytes()).hexdigest(),
         'sequential_cells':len(seq),'clock_cells_excluded':len(clocks),'groups':rows,
         'data_cut_edges':[dict(source=s,destination=d,bits=len(nn)) for (s,d),nn in sorted(edges.items())],
         'open':'Size actual local leaves from measured area/cuts and real macro geometry; legal clock pin homes and native CTS/STA remain required.'}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rows,indent=1))


if __name__=='__main__':main()
