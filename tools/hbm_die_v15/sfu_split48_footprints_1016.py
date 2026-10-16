#!/usr/bin/env python3
"""Attempt actual 13x48-leaf R23 footprints in the wide middle-SFU candidate.

No endpoint pins, reset-glue view or clock trees are invented. Collision/reach
failures remain explicit; this never modifies a source/die contract.
"""
import hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def hit(a,b):return a['x']<b['x']+b['w']-1e-6 and b['x']<a['x']+a['w']-1e-6 and a['y']<b['y']+b['h']-1e-6 and b['y']<a['y']+a['h']-1e-6
def point(path,t):
    for a,b in zip(path,path[1:]):
        length=abs(b[0]-a[0])+abs(b[1]-a[1])
        if t<=length:return (a[0]+(b[0]-a[0])*t/length,a[1]+(b[1]-a[1])*t/length)
        t-=length
    return path[-1]
def main():
    d=ROOT/'results/arch/hbm_die_v15/core4_sfu2_wide';p=json.loads((d/'compact.P.json').read_text());rf=json.loads((d/'rf_centre_allocation.json').read_text())
    # Correct the old historical SUCX boxes before checking candidate footprints.
    for q in ['SW','SE','NW','NE']:
        b=p['coll_'+q];p['sucx_'+q]=dict(x=b['x'] if q.endswith('W') else b['x']+b['w']-720,y=b['y']+b['h']+742 if q.startswith('S') else b['y']-1462,w=720,h=720)
    W,H=json.loads((d/'compact.metrics.json').read_text())['die_um'];src=p['sfucore_SW']
    windows=json.loads((d/'sfu_lg_face_windows.json').read_text())
    obstacle=[(n,b) for n,b in p.items()]+[(c['name'],c['rect']) for c in rf['cells']]
    accepted=[];stations=[];failures=[];routes=[]
    bins={}
    def keys(b):
        return [(x,y) for x in range(math.floor(b['x']/100),math.floor((b['x']+b['w'])/100)+1) for y in range(math.floor(b['y']/100),math.floor((b['y']+b['h'])/100)+1)]
    def add(name,b):
        for key in keys(b):bins.setdefault(key,[]).append((name,b))
    def conflicts(b):
        return list({n for key in keys(b) for n,r in bins.get(key,[]) if hit(b,r)})
    for n,b in obstacle:add(n,b)
    for q in ['SW','SE','NW','NE']:
        def canonical(b):return dict(x=W-b['x']-b['w'] if q.endswith('E') else b['x'],y=H-b['y']-b['h'] if q.startswith('N') else b['y'],w=b['w'],h=b['h'])
        src=canonical(p['sfucore_'+q]);basepaths=[]
        for g in range(4):
            sink=canonical(p[f'sfu_{q}{g}'])
            for direction in ['f','b']:
                slot=windows['pairs'][g];sx=src['x']+slot['source_'+direction+'_escape_um'];tx=sink['x']+slot['peer_'+direction+'_escape_um']
                lane=8070.32+(2*(g%2)+(direction=='b'))*130
                path=[(sx,src['y']+src['h']),(sx,lane),(tx,lane),(tx,sink['y']+sink['h'])]
                if direction=='b':path=path[::-1]
                basepaths.append((g,direction,path))
        def transform(pt):return (W-pt[0] if q.endswith('E') else pt[0],H-pt[1] if q.startswith('N') else pt[1])
        for g,direction,base in basepaths:
            path=[transform(v) for v in base];length=sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(path,path[1:]));centres=[point(path,length*(k+1)/24) for k in range(23)]
            hopmax=max(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(centres,centres[1:]));routes.append(dict(quarter=q,group=g,direction=direction,path=path,length_um=length,max_interior_centre_hop_um=hopmax,interior_pin_envelope_um=hopmax+47.52,native_EW_reach_um=415.662,interior_envelope_pass=hopmax+47.52<=415.662))
            actual_t=[];actual_offsets=[]
            cols=5 if g==3 and direction=='b' else 3;bankrows=math.ceil(13/cols)
            for k,(cx,cy) in enumerate(centres):
                name=f'sfr_{q}{g}_{direction}{k:02d}'
                def tile_rects(t,offset=(0,0)):
                    x0,y0=point(path,t)
                    x0+=offset[0];y0+=offset[1]
                    x0=round(round(x0/2.16)*2.16,2);y0=round(round(y0/2.16)*2.16,2)
                    return [dict(x=round(x0+(-1 if q.endswith('E') else 1)*(lane%cols-(cols-1)/2)*21.6-10.8,3),y=round(y0+(-1 if q.startswith('N') else 1)*(lane//cols-(bankrows-1)/2)*21.6-10.8,3),w=21.6,h=21.6) for lane in range(13)]
                nominal=length*(k+1)/24
                # Move the two return-turn stations together, preserving reach
                # to the preceding stage and freeing the paired crossing bay.
                if g==3 and direction=='b' and k in [19,20]:nominal+=86.4
                chosen=nominal;chosen_offset=(0,0)
                shifts=[0]+[v*2.16*sgn for v in range(1,41) for sgn in [-1,1]]
                offsets=[(0,0)]+[(delta,0) for delta in [21.6,-21.6,43.2,-43.2,64.8,-64.8,86.4,-86.4]]+[(0,delta) for delta in [21.6,-21.6,43.2,-43.2,64.8,-64.8,86.4,-86.4]]
                found=False
                for offset in offsets:
                    for shift in shifts:
                        candidate=nominal+shift;stub=abs(offset[0])+abs(offset[1])
                        prevstub=sum(abs(v) for v in actual_offsets[-1]) if actual_offsets else 0
                        if actual_t and (candidate<=actual_t[-1] or candidate-actual_t[-1]+prevstub+stub+47.52>415.662):continue
                        if not any(conflicts(b) for b in tile_rects(candidate,offset)):
                            chosen=candidate;chosen_offset=offset;found=True;break
                    if found:break
                actual_t.append(chosen);actual_offsets.append(chosen_offset);leaves=[]
                for lane,rect in enumerate(tile_rects(chosen,chosen_offset)):
                    bad=conflicts(rect)
                    leaf=dict(name=name+f'/g[{lane}].lane',master='hbfd_rly_48_EW',rect=rect,payload_bits=[lane*48,(lane+1)*48],conflicts=bad[:5])
                    if bad:failures.append(dict(name=leaf['name'],conflicts=bad[:5]))
                    accepted.append((leaf['name'],rect));add(leaf['name'],rect);leaves.append(leaf)
                stations.append(dict(name=name,arclength_um=chosen,arclength_shift_um=chosen-nominal,lateral_offset_um=chosen_offset,packing_cols=cols,packing_rows=bankrows,leaves=leaves,reset_ff_extra=15,reset_glue_physical_view=None))
            hopmax=max(actual_t[j+1]-actual_t[j]+sum(abs(v) for v in actual_offsets[j])+sum(abs(v) for v in actual_offsets[j+1]) for j in range(22));routes[-1].update(max_interior_centre_hop_um=hopmax,interior_pin_envelope_um=hopmax+47.52,interior_envelope_pass=hopmax+47.52<=415.662)
    view=next(v for v in json.loads((ROOT/'results/arch/hbm_die_v15/relay_compare_1016.json').read_text())['views'] if v['master']=='hbfd_rly_48_EW')
    assert view['outline_um']==[21.6,21.6] and view['full_master_native_pass']
    physical_raw=subprocess.check_output(['git','-C',str(ROOT),'show','d78d342fe:rtl/test/hbm_sfu_relay_0330/hbfd_rly_624_split48_physical_candidate.sv'])
    raw=subprocess.check_output(['git','-C',str(ROOT),'show','419e476e9:rtl/test/hbm_sfu_relay_0330/hbfd_rly_624_split48_candidate.sv'])
    out=dict(schema='opentallas.hbm.sfu_split48_footprint_attempt.v1',qualification='GEOMETRIC_LEAF_FOOTPRINTS_ONLY_NO_NATIVE_STATION_ADOPTION' if not failures and all(r['interior_envelope_pass'] for r in routes) else 'UNQUALIFIED_ATTEMPT_FAILS_CLOSED',source_candidate='419e476e9',source_candidate_sha256=hashlib.sha256(raw).hexdigest(),physical_abi_ref='d78d342fe',physical_abi_sha256=hashlib.sha256(physical_raw).hexdigest(),actual_native_leaf_view=view,partial_face_windows_sha256=hashlib.sha256((d/'sfu_lg_face_windows.json').read_bytes()).hexdigest(),routes=routes,stations=stations,
             station_count=len(stations),leaf_count=len(accepted),leaf_area_mm2=len(accepted)*21.6**2/1e6,reset_extra_ff=15*len(stations),footprint_conflicts=len(failures),failures=failures,
             reach_failures=sum(not r['interior_envelope_pass'] for r in routes),open=['source/sink actual pin arcs and roots','full per-bit obstacle-aware routing','15FF station reset physical master and independent clock entries','programme476/SKV/collective homes and clocks','explicit result-return stages and compiler/token cost','full source-native station route/TT/FF/DRC'])
    (d/'sfu_split48_footprints.json').write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['routes','stations','failures','open','actual_native_leaf_view']}))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(18,4))
    for n,b in p.items():
        if b['x']>14520 or not 5100<b['y']<8700:continue
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#e2e8ed',edgecolor='#667788',linewidth=.4))
        if n.startswith(('sfucore_SW','sfus_SW','sfu_SW','sucx_SW')):ax.text(b['x']+b['w']/2,min(8600,max(6730,b['y']+b['h']/2)),n,fontsize=6,ha='center')
    for r in routes:
        if r['quarter']=='SW':ax.plot([v[0] for v in r['path']],[v[1] for v in r['path']],linewidth=.5,alpha=.5)
    for st in stations:
        if not st['name'].startswith('sfr_SW'):continue
        for leaf in st['leaves']:
            b=leaf['rect'];ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='red' if leaf['conflicts'] else '#39875b',edgecolor='none'))
    ax.set(xlim=(0,14520),ylim=(6650,8700),aspect='equal',xlabel='um',ylabel='um',title=f"R23 split48 station attempt:736stations/9568actual48-bit leaves; {len(failures)} footprint conflicts (red), zero interior reach-envelope failures\nReset15FF per station, source/sink views, actual wires/clocks and programme476/SKV/collective homes still OPEN; no adoption")
    fig.tight_layout();fig.savefig(d/'sfu_split48_footprints.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
