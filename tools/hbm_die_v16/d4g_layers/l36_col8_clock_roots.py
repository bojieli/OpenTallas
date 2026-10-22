#!/usr/bin/env python3
"""Construct source-bound Col8 regional clock roots in actual reticle corridors.

The mapped clock sinks and negative-edge inverters remain literal. This step
places real root cells and constructs the existing die-clock trunk to them.
Local FF trees, residual-controller roots and propagated TT/FF are downstream.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/hbm_die_v15'))
import clock_sites
import die_clock_tree as DCT


def load(p):
    p=Path(p)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def prototype(mapped):
    m=mapped['modules']['ot_hidx_col8_sram_face_col']
    names={m['ports']['ctl']['bits'][0]:'ctl'}
    names.update({b:f'cp[{k}]' for k,b in enumerate(m['ports']['cp']['bits'])})
    inverse={}
    for n,c in m['cells'].items():
        p=c['connections']
        if c['type'].startswith('INV') and p.get('A',[None])[0] in names:
            inverse[p['Y'][0]]=dict(cell=n,master=c['type'],source_bit=p['A'][0])
    groups={n:[] for n in names.values()}
    phase=[]
    for n,c in m['cells'].items():
        for p,bits in c['connections'].items():
            if p not in ('CLK','clk','rclk','wclk'):continue
            assert len(bits)==1,(n,p)
            bit=bits[0]
            if bit in names:
                groups[names[bit]].append(dict(cell=n,port=p,master=c['type'],phase='positive'))
            else:
                assert bit in inverse,('unresolved mapped clock',n,p,bit)
                inv=inverse[bit]
                groups[names[inv['source_bit']]].append(dict(cell=n,port=p,master=c['type'],
                    phase='negative',clock_inverter=inv['cell']))
                phase.append(dict(sink=[n,p],prototype_clock=names[inv['source_bit']],**inv))
    assert len(phase)==4
    assert sum(len(x) for x in groups.values())==10029
    return groups,phase


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('geometry','baseline','root_sites','mapped','split','pins','out'):a.add_argument('--'+n,required=True,type=Path)
    a.add_argument('--trunk',action='store_true')
    p=a.parse_args();g=load(p.geometry);base=load(p.baseline);rs=load(p.root_sites);split=load(p.split)
    assert hashlib.sha256(p.baseline.read_bytes()).hexdigest()==g['input_manifest_sha256']
    assert hashlib.sha256(p.root_sites.read_bytes()).hexdigest()==g['root_keepout_sha256']
    groups,phase=prototype(load(p.mapped))
    # No opaque column envelope: obstacles are the literal accepted rectangles.
    placement={n:dict(v) for n,v in base['placement'].items()
               if n not in g['automatic_relays_requiring_regeneration'] and n!='hc_eng'}
    placement.update(g['existing_bodies_moved'])
    placement['hc_eng']=dict(g['placed_service_envelopes']['hc_eng'])
    obstacles=[(v['x'],v['y'],v['x']+v['w'],v['y']+v['h']) for v in placement.values()]
    obstacles += [(v['x_um'],v['y_um'],v['x_um']+v['width_um'],v['y_um']+v['height_um'])
                  for v in g['individual_source_rectangles'].values()]
    obstacles += [tuple(s['keepout']) for s in rs['sites']]
    roots=[];bindings=[];source_bits=collections.defaultdict(set)
    for i in split['instances']:
        if i['kind']!='hierarchical_column':continue
        key=i['placement_key'];q=key.split('.')[0]
        env=g['placed_service_envelopes'][key]
        for local in ('ctl','cp[0]','cp[1]','cp[2]','cp[3]'):
            name='col8_root_'+key.replace('.','_')+'_'+local.replace('[','').replace(']','')
            if local=='ctl':
                source=i['connections']['ctl'];x=env['x']+env['w']/2;y=env['y']+env['h']/2
            else:
                rid=int(local[3]);source=i['connections']['cp']['bits_lsb_first'][rid]
                part=g['individual_source_rectangles'][key+'/u_pair'+str(rid)]
                x=part['x_um'];y=part['y_um']+part['height_um']/2
            roots.append((name,DCT.BUF,x,y))
            source_bits[q].add(source)
            bindings.append(dict(root=name,placement_key=key,clock_source=source,
                prototype_clock=local,sink_count=len(groups[local]),
                logical_local_tree='OPEN; exact cell/pin list retained in prototype',
                phase_inverters=[v for v in phase if v['prototype_clock']==local]))
    assert len(roots)==640 and all(len(v)==136 for v in source_bits.values())
    trees={'stream':dict(buffers=roots,nets=[],model={})}
    W,H=g['die_um'];clock_sites.allocate(trees,W,H,obstacles)
    # A shared trunk is constructed with the existing regional tree recipe.
    # Its targets are the actual allocated root input cells, not hard-column
    # or quarter aliases. Actual cell-pin spans and phase are checked later.
    if p.trunk:
        sinks=[(n,'A',x,y) for n,cell,x,y in trees['stream']['buffers']]
        pll=load(p.pins)['instances']['hb_ckgen']['pll_stream'][:2]
        trunk=DCT.build(W,H,obstacles,pll,sinks,lambda n:'stream',mode='regional',
                        region_of=lambda n:n,pairs=[],near_um=405)
        trunk['buffers']+=trees['stream']['buffers']
        trunk['model']['root_cell_count']=640
        trees={'stream':trunk}
        clock_sites.allocate(trees,W,H,obstacles)
    residual=[]
    for i in split['instances']:
        if i['kind']=='hierarchical_soft_controller':
            residual.append(dict(instance=i['instance'],ports={k:v for k,v in i['connections'].items()
                if k.startswith('clk_') and k!='clk_hslice'},hard_children=i.get('hard_children',[]),
                root_construction='OPEN until current hard-bound metadata map is consumed'))
    report=dict(status='REGIONAL_ROOT_CONSTRUCTION_NOT_CLOCK_SIGNOFF',
        inputs={n:hashlib.sha256(getattr(p,n).read_bytes()).hexdigest() for n in
                ('geometry','baseline','root_sites','mapped','split','pins')},
        active_source_clock_bits_per_quarter=143,column_source_bits_per_quarter=136,
        residual_source_bits_per_quarter=7,column_regions_per_quarter=160,
        placed_root_cells=640,root_cell=DCT.BUF,root_size_um=clock_sites.SIZES[DCT.BUF],
        source_root_bindings=bindings,mapped_clock_prototype=groups,
        retained_negative_edge_inverters=phase,clock_trees=trees,residual_controllers=residual,
        trunk_source=['hb_ckgen','pll_stream'],trunk_actual_source_pin_um=load(p.pins)['instances']['hb_ckgen']['pll_stream'][:2],
        baseline_root_cases=g['baseline_roots_within_existing_bodies'],
        existing_root_keepouts=rs,old_automatic_relays_invalidated=list(g['automatic_relays_requiring_regeneration']),
        displaced_bodies=list(g['existing_bodies_moved']),
        reserved_clock_cell_area_um2=sum(clock_sites.SIZES[c][0]*clock_sites.SIZES[c][1]
            for t in trees.values() for n,c,x,y in t['buffers']),
        release_ready=False,open=['local clock buffer trees for all actual mapped FF and hard-macro clock sinks',
            'residual mapped placement and metadata literal terminal compensation',
            'propagated clock TT/FF and actual pin reach after cell-site placement',
            'all transformed reset and data delivery routes and fixed calendars',
            'ordinary existing root-within-body repair in the composed whole-die tree'])
    p.out.parent.mkdir(parents=True,exist_ok=True);p.out.write_bytes(gzip.compress(json.dumps(report,indent=1).encode(),mtime=0))
    print('COL8_ROOT_CONSTRUCTION',len(roots),'actual root cells;',sum(len(t['buffers']) for t in trees.values()),
          'clock buffers total; source clock bits143/quarter; local trees and propagated STA OPEN',flush=True)


if __name__=='__main__':main()
