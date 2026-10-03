#!/usr/bin/env python3
"""Pin-aware native fanout collector. Source FF membership, macro landing and
standard-cell footprints are bound before reset/ACK composition. No build.
"""
import collections
import copy
import gzip
import json
import math
import re
from pathlib import Path
import qwen_rom_local_release_successor as V
R=V.R;M=V.M;N=V.N;G=V.G
OUT=Path('results/uarch/qwen_rom_native_collector_clock_20261002')
PDK=Path('results/uarch/topk_finite_source_context_20261002/inputs/retained_pdk/asap7sc7p5t_28_R_1x_220121a.lef')


def abstracts():
    text=(R.ROOT/PDK).read_text();result={}
    for m in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1$',text,re.M|re.S):
        body=m[2];size=[float(v) for v in re.search(r'SIZE (\S+) BY (\S+) ;',body).groups()]
        pins={}
        for p in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',body,re.M|re.S):
            shapes=[];layer=None
            for ln in p[2].splitlines():
                if 'LAYER ' in ln:layer=ln.split()[1]
                if 'RECT ' in ln:shapes.append(dict(layer=layer,rect=[float(x) for x in ln.split()[1:5]]))
            pins[p[1]]=shapes
        result[m[1]]=dict(size_um=size,pins=pins)
    return result


class Sites:
    """Actual0.054x0.270LEF sites with alternating row rail orientation.
    Macro halos consume0.54um locally; the original10000um2 aggregate halo
    reservation remains in the slot ledger, never converted into cell credit.
    """
    def __init__(self,macros):
        self.rows=collections.defaultdict(list);self.macros=macros;self.count=0
    def put(self,pos,width,reg):
        xmin,xmax=G.BOUNDS[0][reg[0]:reg[0]+2];ymin,ymax=G.BOUNDS[1][reg[1]:reg[1]+2]
        xlo=math.ceil(xmin/.054);xhi=math.floor(xmax/.054)-math.ceil(width/.054)
        ylo=math.ceil(ymin/.270);yhi=math.floor(ymax/.270)-1
        request_x=round((pos[0]-width/2)/.054);request_y=round((pos[1]-.135)/.270)
        for radius in range(2000):
            for dy in range(-radius,radius+1):
                y=request_y+dy
                if not ylo<=y<=yhi:continue
                for dx in ({radius-abs(dy),-(radius-abs(dy))}):
                    x=request_x+dx
                    if not xlo<=x<=xhi:continue
                    left=x*.054;bottom=y*.270;right=left+width;top=bottom+.270
                    if any(left<a[2]+.54 and right>a[0]-.54 and bottom<a[3]+.54 and top>a[1]-.54 for a in self.macros):continue
                    occupied=self.rows[y];n=math.ceil(width/.054)
                    if any(x<b and x+n>a for a,b in occupied):continue
                    occupied.append((x,x+n));self.count+=1
                    return dict(origin_um=[round(left,9),round(bottom,9)],orientation='MX' if y%2 else 'R0',
                                size_um=[width,.270],region=list(reg))
        raise ValueError('no source-sized legal site near requested clock group')


def source_placement():
    old,rows,direct=N.inventory();cells=abstracts();coords=old['nominal_node_coordinates_um'];macro_rect=[];placements={};rowdict={r['instance']:r for r in rows}
    macro_names=[r for r in rows if r['group'] in ('ROM_clock','KV_clock')]
    kv=0
    for r in macro_names:
        if r['group']=='ROM_clock':
            c,bank=map(int,re.search(r'g_col\[(\d+)\].g_bank\[(\d+)\]',r['instance']).groups());x=4.32+c*227.232;y=2.16+bank*69.12
        else:x=4.32+(kv%2)*227.232;y=2.16+5*69.12;kv+=1
        name=r['cell'];spec=R.obj(Path('physical/asap7_memory_macros')/name/(name+'.json'))
        w=spec['area']['macro_width_um'];h=spec['area']['macro_height_um'];macro_rect.append([x,y,x+w,y+h])
        lef=(R.ROOT/Path('physical/asap7_memory_macros')/name/(name+'.lef')).read_text()
        block=re.search(r'PIN clk\n(.*?)END clk',lef,re.S)[1];rect=[float(v) for v in re.search(r'RECT (\S+) (\S+) (\S+) (\S+) ;',block).groups()]
        coords[r['instance']]=[x+(rect[0]+rect[2])/2,y+(rect[1]+rect[3])/2]
        placements[r['instance']]=dict(origin_um=[x,y],size_um=[w,h],orientation='R0',pin_CLK_rect_M4_um=[x+rect[0],y+rect[1],x+rect[2],y+rect[3]])
    sites=Sites(macro_rect)
    capture=R.obj(OUT/'inputs/capture-connectivity.json')
    assert capture['map_SHA256']==M.MAP_SHA and capture['distinct_direct_capture_FFs']==2560
    selected=set()
    for m in capture['macros']:
        origin=placements[m['macro']]['origin_um'];x,y=origin
        for i,name in enumerate(m['first256_direct_capture_FF_D']):
            assert rowdict[name]['cell']=='DFFHQNx1_ASAP7_75t_R'
            p=sites.put([x-3.78+(i%2)*1.08+.54,y+6.48+(i//2)*.270+.135],1.08,G.region([x-1,y+20]))
            placements[name]=p;coords[name]=[p['origin_um'][0]+.54,p['origin_um'][1]+.135];selected.add(name)
    for r in rows:
        name=r['instance']
        if name in placements or name=='context_provider':continue
        typ=r['cell'];w=cells[typ]['size_um'][0];p=sites.put(coords[name],w,G.region(coords[name]))
        placements[name]=p;coords[name]=[p['origin_um'][0]+w/2,p['origin_um'][1]+.135]
    return old,rows,direct,cells,sites,placements


class Builder(N.Builder):
    def __init__(self,old,rows,sites,placements):
        super().__init__(old,rows);self.sites=sites;self.placements=placements
    def buf(self,pos,label='native'):
        name=super().buf(pos,label);p=self.sites.put(pos,.378,G.region(pos));self.placements[name]=p
        self.g['nominal_node_coordinates_um'][name]=[p['origin_um'][0]+.189,p['origin_um'][1]+.135]
        return name
    def edge(self,a,b,p,length):
        coords=self.g['nominal_node_coordinates_um'];distance=sum(abs(x-y) for x,y in zip(coords[a],coords[b]))
        super().edge(a,b,p,max(length,distance))
    def tree(self,targets,label,minimum_levels=1):
        coords=self.g['nominal_node_coordinates_um'];targets=sorted(targets,key=lambda r:N.B.morton(coords[r[0]]));level=0
        caps=R.library('ss')[2]
        while True:
            parents=[]
            for i in range(0,len(targets),8):
                children=targets[i:i+8];pos=[sum(coords[n][d] for n,p in children)/len(children) for d in (0,1)]
                parent=self.buf(pos,label);loadpins=sum(M.pin_cap((self.g['added_primitive_cells'].get(n) or self.net['cells'][n])['type'],p,'ss') for n,p in children)
                lengths=[sum(abs(x-y) for x,y in zip(coords[parent],coords[n])) for n,p in children]
                floorwire=max(0,(2.90-loadpins)/.165790)
                extra=max(0,floorwire-sum(lengths))/len(children)
                if loadpins+.165790*sum(lengths)>40:
                    # Isolate only a physically long collector branch.
                    for (n,p),distance in zip(children,lengths):
                        branch=self.buf(coords[parent],label+'_isolate');self.edge(parent,branch,'A',16)
                        count=max(1,math.ceil(max(16,distance)/128));previous=branch
                        for k in range(1,count):
                            seg=self.buf([coords[parent][d]+(coords[n][d]-coords[parent][d])*k/count for d in (0,1)],label+'_segment')
                            self.edge(previous,seg,'A',max(16,distance)/count);previous=seg
                        self.edge(previous,n,p,max(16,distance)/count)
                else:
                    for (n,p),distance in zip(children,lengths):self.edge(parent,n,p,distance+extra)
                parents.append((parent,'A'))
            targets=parents;level+=1
            if len(parents)==1 and level>=minimum_levels:return parents[0][0],level


def construct():
    old,rows,direct,cells,sites,placements=source_placement();b=Builder(old,rows,sites,placements);coords=b.g['nominal_node_coordinates_um']
    groups=collections.defaultdict(list)
    for r in rows:
        pos=coords[r['instance']];reg=G.region(pos)
        loc=tuple(int((v-G.BOUNDS[d][reg[d]])/size) for d,(v,size) in enumerate(zip(pos,(44.712,42.525))))
        groups[reg+loc+(r['cell'],)].append(r)
    roots={};regional=collections.defaultdict(list);ledger=[]
    for key,targets in sorted(groups.items()):
        root,depth=b.tree([(r['instance'],r['pin']) for r in targets],'native_leaf',4)
        roots[root]=targets;regional[key[:2]].append((root,'A'));ledger.append(dict(root=root,region=list(key[:2]),bin=list(key[2:4]),sinks=len(targets),levels=depth))
    coarse=[]
    for reg,targets in sorted(regional.items()):
        root,depth=b.tree(targets,'native_regional',1);coarse.append((root,'A'))
    hub,depth=b.tree(coarse,'native_hub',1);entry=b.buf([178.848,393.12],'native_clock_entry')
    distance=max(16,sum(abs(x-y) for x,y in zip(coords[entry],coords[hub])));parts=math.ceil(distance/128);previous=entry
    for i in range(1,parts):
        n=b.buf([coords[entry][d]+(coords[hub][d]-coords[entry][d])*i/parts for d in (0,1)],'native_input_segment');b.edge(previous,n,'A',distance/parts);previous=n
    b.edge(previous,hub,'A',distance/parts);b.g['added_primitive_cells'][entry]['connections']['A']=['PRIMARY_CLOCK_SOURCE']
    b.g.update(root_driver=entry,source_clock_sinks=rows,local_group_ledger=ledger,local_bin_um=[44.712,42.525],regional_collector_roots=coarse,
               reset_direct_sinks=sorted(direct),metadata_reset_sinks=[r['instance'] for r in old['source_control_cells']]+[
                r['instance'] for r in json.loads(gzip.decompress((R.ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes())) if r['group']=='distributed_reset' and r['instance'] not in old['removed_old_control_FFs']])
    N.inverse_balance(b,roots)
    b.g['cell_sites']=placements;b.g['native_fanout_leaf_not_per_FF_isolation']=True
    return b,old,rows,direct


def generate():
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    if (root/'clock-checkpoint-r1.json').exists():raise ValueError('preserve native clock checkpoint')
    print('place actual2560capture FFs and source-matched native clock leaves',flush=True)
    b,old,rows,direct=construct()
    (root/'clock-allocation-r1.json.gz').write_bytes(gzip.compress(R.canon(b.g),mtime=0))
    report=dict(source_clock_sinks=102352,provider_FFs_separate=2,clock_buffers=len(b.g['added_primitive_cells']),
        placed_source_and_clock_cells=len(b.placements),macro_direct_capture_FFs=2560,
        source_map_admission=False,PnR=False,selected_map_sha256=M.MAP_SHA)
    M.write(root/'clock-checkpoint-r1.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':generate()
