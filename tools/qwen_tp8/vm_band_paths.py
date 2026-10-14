#!/usr/bin/env python3
"""All-bit closed-pin audit and combined band routing demand model.

Known lane stages use real exported LEF pins. Column d pins of the OLD view
are explicitly provisional until xcol_roots closes. Root transport may only
enter this model through a supplied actual-pin contract, never guessed stations.
The model reports unresolved requirements and cannot qualify a physical band.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
from vm_lef_pins import read
from vm_bay_cluster import VIEW
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/hier_contract'))
from pinreg_audit import parse_lib, clock_refs, pin_metrics

ROOT = Path(__file__).resolve().parents[2]


def union(intervals):
    total, end = 0., -math.inf
    for lo, hi in sorted(intervals):
        if hi > end:
            total += hi-max(lo,end)
            end = hi
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root-contract', type=Path)
    ap.add_argument('--candidate-controls',type=Path)
    ap.add_argument('--closed-column-view',type=Path)
    args = ap.parse_args()
    file = 'results/arch/qwen_tp8_1012/vm_band_composition_codex.json'
    comp = json.loads((ROOT/file).read_text())
    x0,y0=comp['origin_um'];W,H=comp['outline_um']
    children = {(c['bay'],c['slot']):c for c in comp['children'] if 'bay' in c}
    plan=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json').read_text())
    packing=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json').read_text())
    allbays={b['n']:b for b in plan['x_relay_bays']}
    # Region lane leaf placements stand unchanged in the current rg6 pilot;
    # the b6 input-core relocation affects no X lane leaf. This is an exact
    # leaf-pin lower bound, still NOT the two hardened clusters' routed seam.
    for bn,ts in packing['bay_tiles'].items():
        if allbays[bn].get('padrow'):continue
        for t in ts:
            children[bn,t['slot']]=dict(view=VIEW[t['kind']],at=[allbays[bn]['x']-x0+t['slot']*21.6,allbays[bn]['y']-y0])
    colchildren={int(c['inst'][3:]):c for c in comp['children'] if c['inst'].startswith('u_c')}
    viewpins={}; hashes={}
    for c in children.values():
        if c['view'] not in viewpins:
            f=next((ROOT/c['view']).glob('*.lef'))
            viewpins[c['view']]=read(f)[1]
            hashes[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    column_view=args.closed_column_view
    if column_view and not column_view.is_absolute():column_view=ROOT/column_view
    old=next(column_view.glob('*.lef')) if column_view else ROOT/'physical/ref_tile/qfd_vm_xcol_t/views/ot_qfd_vm_xcol_t/ot_qfd_vm_xcol_t.lef'
    oldpins=read(old)[1];hashes[str(old.relative_to(ROOT))]=hashlib.sha256(old.read_bytes()).hexdigest()
    def pin(stage,port,bit):
        c=children[stage['bay'],stage['slot']]
        p=viewpins[c['view']][f'{port}[{stage["bit0"]+stage.get("bit_permutation",list(range(8)))[bit]}]']
        return [round(x0+c['at'][0]+p['x'],4),round(y0+c['at'][1]+p['y'],4)]
    edges=[];boundary=[]
    for s in comp['segments']:
        path=s['path']; col=int(s['output'][0].split('_')[0][3:])
        port='d_hi' if s['output'][0].endswith('hi') else 'd_lo'
        for bit in range(8):
            # Boundary inputs lack assigned physical pins: record, do not certify.
            boundary.append(dict(lane=s['lane'],bit=bit,port=s['input'],peer=s['predecessor'],
                                 first_visit=s['first_visit'],destination=pin(path[0],'d',bit)))
            unordered=packing['lane_chain'][s['lane']]
            original=sorted(unordered,key=lambda q:q['visit'])
            if s['first_visit']:
                v=original[s['first_visit']-1]
                launch=dict(bay=v['bay'],visit=v['visit'],**v['tiles'][-1])
                edges.append(dict(kind='regional_boundary_lower_bound',lane=s['lane'],bit=bit,
                    A=pin(launch,'q',bit),B=pin(path[0],'d',bit),launch=launch,capture=path[0],
                    note='real leaf pins; exact regional and band boundary pins/routed seam not assigned'))
            for k in range(len(path)-1):
                edges.append(dict(kind='closed_tile_to_closed_tile',lane=s['lane'],bit=bit,
                    A=pin(path[k],'q',bit),B=pin(path[k+1],'d',bit),
                    launch=path[k],capture=path[k+1]))
            cp=oldpins[f'{port}[{s["output"][1]+bit}]'];c=colchildren[col]
            edges.append(dict(kind='closed_column_input' if column_view else 'provisional_column_input',lane=s['lane'],bit=bit,
                launch=path[-1],
                capture_column=col,capture_pin=f'{port}[{s["output"][1]+bit}]',
                A=pin(path[-1],'q',bit),B=[x0+c['at'][0]+cp['x'],y0+c['at'][1]+cp['y']]))
    root_edges=[]; root_coverage=None
    if args.root_contract:
        root=json.loads(args.root_contract.read_text())
        assert root['schema']=='opentallas.qwen.vm-band-actual-root-paths.v1'
        assert root['pin_assignment']=='die-assigned'
        root_edges=root['edges']
        root_coverage={(e['column'],e['root'],e['bit']) for e in root_edges if e['kind']=='root_source'}
        assert root_coverage=={(c,r,b) for c in range(32) for r in range(32) for b in range(4)}
        # Include every transport stage, tags and controls in the SAME demand model.
        assert {'root_source','root_transport','root_tags','root_control'} <= {e['kind'] for e in root_edges}
        edges+=root_edges
    if args.candidate_controls:
        candidate=json.loads(args.candidate_controls.read_text())
        assert candidate['qualification'] is False and candidate['status']=='CANDIDATE_SLOT_GRAPH_NOT_ASSIGNED'
        edges+=candidate['candidate_control_edges']
    for e in edges:
        e['length_um']=round(abs(e['A'][0]-e['B'][0])+abs(e['A'][1]-e['B'][1]),4)
    timing={}
    def metrics(view):
        if view not in timing:
            vd=ROOT/view;lib=next(vd.glob('*_tt.lib'));ins=json.loads((vd/'insertion.json').read_text())
            parsed=parse_lib(lib);refs=clock_refs(parsed,ins,'tt')
            timing[view]=(pin_metrics(parsed,refs),refs)
            hashes[str(lib.relative_to(ROOT))]=hashlib.sha256(lib.read_bytes()).hexdigest()
            hashes[str((vd/'insertion.json').relative_to(ROOT))]=hashlib.sha256((vd/'insertion.json').read_bytes()).hexdigest()
        return timing[view]
    missing_timing=[];pair_failures=[]
    for e in edges:
        if e['kind'] not in ('closed_tile_to_closed_tile','regional_boundary_lower_bound','closed_column_input'):continue
        la=e['launch'];lc=children[la['bay'],la['slot']]
        if e['kind']=='closed_column_input':
            cc=dict(view=str(column_view.relative_to(ROOT)));capture_pin=e['capture_pin']
        else:
            ca=e['capture'];cc=children[ca['bay'],ca['slot']];capture_pin=f'd[{ca["bit0"]+ca.get("bit_permutation",list(range(8)))[e["bit"]]}]'
        lm,lr=metrics(lc['view']);cm,cr=metrics(cc['view'])
        lp=lm[f'q[{la["bit0"]+la.get("bit_permutation",list(range(8)))[e["bit"]]}]'];cp=cm[capture_pin]
        if lp['out'] is None or cp['inp'] is None or not lp['clk'] or not cp['clk']:
            missing_timing.append(dict(lane=e['lane'],bit=e['bit']));continue
        lref=lr[lp['clk'][0]];cref=cr[cp['clk'][0]]
        # Boundary spread is inside the pair cost, in addition to die skew.
        o=lp['out']+lref['bmax']-lref['rise']
        s=cp['inp']+cref['rise']-cref['bmin']
        skew=90 if max(lref['rise'],cref['rise'])<=300 else 150
        available=833.3333333333-60-skew
        reach=min(500,(available-o-s)/.76)
        e['pair_reach_um']=round(reach,4)
        e['deep_entry_reach_um']=round(min(500,(833.3333333333-210-o-s)/.76),4)
        e['deep_entry_slack_ps']=round(833.3333333333-210-o-s-.76*e['length_um'],4)
        e['pair_slack_ps']=round(available-o-s-.76*e['length_um'],4)
        if e['length_um']>reach:pair_failures.append(e)
    bykind=collections.defaultdict(list)
    for e in edges:bykind[e['kind']].append(e)
    # Closed M5 children block lower routing layers. Cap upper layers for BOTH
    # net-specific 0.48/9.091 stripes. This conservative occupancy is 10.56%,
    # pending resolution of the grant's 5.3% versus actual net-specific geometry.
    grantfile=ROOT/'results/arch/qwen_tp8_1012/vm_cluster_layer_grant_1013.json'
    grant=json.loads(grantfile.read_text())
    assert grant['no_die_signal_through_traffic'] and grant['die_pg_layers']==['M8','M9']
    assert 'qfd_vm_band' in grant['masters'] and grant['signal_cap']=='M9'
    pg_fraction=grant['die_pg']['combined_track_fraction']
    assert abs(pg_fraction-2*grant['die_pg']['width_um']/grant['die_pg']['pitch_um'])<1e-8
    blocks=[(x0+c['at'][0],y0+c['at'][1],x0+c['at'][0]+c['outline_um'][0],
             y0+c['at'][1]+c['outline_um'][1]) for c in comp['children']]
    horizontal=[];vertical=[]
    # One explicit L route per edge; it is a demand candidate, not routed proof.
    for e in edges:
        ax,ay=e['A'];bx,by=e['B']
        horizontal.append((min(ax,bx),max(ax,bx),ay))
        vertical.append((min(ay,by),max(ay,by),bx))
    worst={};windows=[]
    for axis in ('x','y'):
        length=W if axis=='x' else H
        cross=H if axis=='x' else W
        alongorigin=x0 if axis=='x' else y0
        otherorigin=y0 if axis=='x' else x0
        segs=horizontal if axis=='x' else vertical
        layers=('M8','M6','M4') if axis=='x' else ('M9','M7','M5')
        tpu=(12.5,15.625,20.8333333333)
        maximum=dict(ratio=0)
        # Scan every 2.16um cut and 130um windows with 260um span, including
        # the short final edge window. Lower-layer capacity uses union coverage.
        for ix in range(1,int(length/2.16)):
            cp=alongorigin+ix*2.16
            crossings=sorted(s[2] for s in segs if s[0]<cp<s[1])
            for start in range(0,int(cross),130):
                lo=otherorigin+start;hi=min(lo+260,otherorigin+cross)
                demand=sum(lo<=at<hi for at in crossings)
                if not demand:continue
                cover=[]
                for b in blocks:
                    a,z=(b[0],b[2]) if axis=='x' else (b[1],b[3])
                    if a<cp<z:
                        l,h=(b[1],b[3]) if axis=='x' else (b[0],b[2])
                        if min(h,hi)>max(l,lo):cover.append((max(l,lo),min(h,hi)))
                cov=union(cover);span=hi-lo
                cap={layers[0]:.75*(1-pg_fraction)*span*tpu[0],
                     layers[1]:.75*span*tpu[1],layers[2]:.5*(span-cov)*tpu[2]}
                capacity=sum(cap.values());ratio=demand/capacity
                rec=dict(axis=axis,cut_um=round(cp,4),span_um=[lo,hi],demand_bits=demand,
                    capacity_tracks=round(capacity,2),ratio=round(ratio,6),layer_capacity=cap)
                if ratio>maximum['ratio']:maximum=rec
                if ratio>.6:windows.append(rec)
        worst[axis]=maximum
    # Geometry checks cover every placed child, not sampled bays.
    outside=[c['inst'] for c in comp['children'] if c['at'][0]<0 or c['at'][1]<0 or
             c['at'][0]+c['outline_um'][0]>W+1e-6 or c['at'][1]+c['outline_um'][1]>H+1e-6]
    channel_failures=[]
    for i,c in enumerate(comp['children']):
        for d in comp['children'][i+1:]:
            dx=max(c['at'][0],d['at'][0])-min(c['at'][0]+c['outline_um'][0],d['at'][0]+d['outline_um'][0])
            dy=max(c['at'][1],d['at'][1])-min(c['at'][1]+c['outline_um'][1],d['at'][1]+d['outline_um'][1])
            if max(dx,dy)<2.16-1e-6:channel_failures.append(dict(a=c['inst'],b=d['inst'],x_gap=dx,y_gap=dy))
    report=dict(schema='opentallas.qwen.vm-band-bit-paths.v1',status='INCOMPLETE_PHYSICAL_CONTRACT',
        qualification=False,source=file,source_sha256=hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),
        lef_sha256=hashes,children=len(comp['children']),outside_children=outside,
        geometry=dict(pair_checks=len(comp['children'])*(len(comp['children'])-1)//2,minimum_channel_um=2.16,failures=channel_failures),
        lanes=len(comp['segments']),boundary_bits=len(boundary),
        path_bits_by_kind={k:len(es) for k,es in bykind.items()},
        max_length_by_kind={k:max(e['length_um'] for e in es) for k,es in bykind.items()},
        over500=[e for e in edges if e['length_um']>500],
        pair_setup=dict(corner='tt',wire_ps_per_um=.76,clock='phi-R compensated; boundary spread included',
                        missing=len(missing_timing),failed_bits=len(pair_failures),
                        failed_by_kind=dict(collections.Counter(e['kind'] for e in pair_failures)),
                        worst_slack_ps=min((e['pair_slack_ps'] for e in edges if 'pair_slack_ps' in e),default=None),
                        failures=pair_failures,hold='not yet measured on band routed parasitics'),
        deep_entry_screen=dict(setup_reserve_ps=210,failed_by_kind=dict(collections.Counter(e['kind']for e in edges if 'deep_entry_reach_um'in e and e['length_um']>e['deep_entry_reach_um'])),classification='conservative screen until actual childclock-entry delivery classification; not waived by shallow local childR'),
        pg_occupancy=pg_fraction,pg_note='actual pairedPG occupancy from authority receipt; band PG geometry not yet built',
        layer_grant=dict(path=str(grantfile.relative_to(ROOT)),sha256=hashlib.sha256(grantfile.read_bytes()).hexdigest(),
                         actual_pg_receipt=grant['actual_pg_receipt'],core_origin_um=grant['die_pg']['core_origin_um']),
        combined_cut_model=dict(route='explicit x-then-y L, no router claim',worst=worst,over_limit=windows),
        unresolved=['boundary assigned pins and pair-specific timing reach',
                    'new column real input/output pins','4096bit gather plus tags and controls'] if not root_edges else
                    ['boundary assigned pins and pair-specific timing reach','new column real input pins'],
        root_payload_coverage=len(root_coverage) if root_coverage else 0,
        edges=edges,boundary_requests=boundary)
    out=ROOT/('results/arch/qwen_tp8_1012/vm_band_paths_closed_station_candidate_codex.json' if args.candidate_controls and column_view else 'results/arch/qwen_tp8_1012/vm_band_paths_closed_column_codex.json' if column_view else 'results/arch/qwen_tp8_1012/vm_band_paths_station_candidate_codex.json' if args.candidate_controls else 'results/arch/qwen_tp8_1012/vm_band_paths_codex.json')
    if args.candidate_controls:report['candidate_controls']=dict(path=str(args.candidate_controls),sha256=hashlib.sha256(args.candidate_controls.read_bytes()).hexdigest(),unresolved='no source entry, local equalization packing, loader/fill-fire, or root gather paths included')
    detail=dict(edges=report.pop('edges'),boundary_requests=report.pop('boundary_requests'))
    details=out.with_suffix('.details.json.gz')
    with gzip.open(details,'wt') as f:json.dump(detail,f,separators=(',',':'))
    report['all_bit_details']=dict(path=str(details.relative_to(ROOT)),sha256=hashlib.sha256(details.read_bytes()).hexdigest())
    # Failure examples are capped in the summary; all edges remain in details.
    report['over500_count']=len(report['over500']);report['over500']=report['over500'][:16]
    report['pair_setup']['failures']=report['pair_setup']['failures'][:16]
    out.write_text(json.dumps(report,indent=1)+'\n')
    print({k:report[k] for k in ('children','lanes','boundary_bits','path_bits_by_kind','max_length_by_kind','root_payload_coverage')})
    print('over500',report['over500_count'],'pair_setup',report['pair_setup']['failed_bits'],'cut',worst)


if __name__=='__main__':main()
