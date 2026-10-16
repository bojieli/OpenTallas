#!/usr/bin/env python3
"""Literal five-root clock-pin proposal; data pin geometry is held exact."""
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SEED='5fce4c7b5607c476c206908187ebf6371fbb73ba'


def main():
    old=ROOT/'physical/ref_tile_specs/s81_bf_native_1015/static_pins_c10s/pin_request.json'
    seed_bytes=subprocess.check_output(['git','show',SEED+':'+str(old.relative_to(ROOT))],cwd=ROOT)
    request=json.loads(seed_bytes);pins=request['pins'];mapping={}
    for i in range(1068):
        old_name=f'xb[{i}]'
        name=f'xb_data[{i}]' if i<1024 else f'xb_meta[{i-1024}]'
        pins[name]=pins.pop(old_name)
        mapping[old_name]=dict(new_pin=name,geometry=pins[name])
    added={}
    for name,face,layer,target,offset in [('io_n','N','M5',58.38,.012),('io_w','W','M4',99.36,.036),('io_e','E','M4',99.36,.036)]:
        axis='x' if face=='N' else 'y'
        used=[p[axis] for p in pins.values() if p['face']==face and p['layer']==layer]
        candidates=[round(offset+.048*k,6) for k in range(1,4100)]
        candidates=[v for v in candidates if 2.16<v<(114.48 if axis=='x' else 196.56) and min(abs(v-u) for u in used)>=.096-1e-6]
        assert candidates,(name,face)
        v=min(candidates,key=lambda x:abs(x-target))
        x=v if axis=='x' else (0 if face=='W' else 116.64)
        y=198.72 if face=='N' else v
        added[name]=dict(face=face,layer=layer,x=x,y=y,w='.024' if axis=='x' else '.192',h='.192' if axis=='x' else '.024',source_pin=name)
        pins[name]=added[name]
    groups=collections.defaultdict(list)
    for p in pins.values():groups[p['face'],p['layer']].append(p['x'] if p['face'] in ['N','S'] else p['y'])
    spacing={str(k):min(b-a for a,b in zip(sorted(v),sorted(v)[1:])) for k,v in groups.items() if len(v)>1}
    assert min(spacing.values())>=.096-1e-6,spacing
    manifest=ROOT/'results/rtl/s81_bf_clock_1015/c10/recovery_0253/front_roots_source.json'
    source_hash=json.loads(manifest.read_text())['outputs']['rtl/s81/ot_s81_bf_front_roots.sv']
    request.update(top='dsfd_bf_front_roots',status='PROPOSED_NEW_CLOCK_ABI_NOT_GRANTED',basis=dict(source_manifest=str(manifest.relative_to(ROOT)),source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),parent_pin_request_source_commit=SEED,parent_pin_request_sha256=hashlib.sha256(seed_bytes).hexdigest(),all_3269_original_pin_shapes_unchanged=True,renamed_xb_pins=1068,old_to_new_mapping='legacy_xb_pin_mapping.json',new_clock_pins=added,min_sameface_samelayer_center_spacing_um=spacing,physical_qualification=False,slot_change_grant='PENDING',native_capture='PENDING'))
    out=ROOT/'physical/ref_tile_specs/s81_bf_native_1015/front_five_roots';out.mkdir(exist_ok=True)
    (out/'pin_request.json').write_text(json.dumps(request,indent=2)+'\n')
    (out/'legacy_xb_pin_mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    lines=['# Exact old c10 data shapes, explicit xb_data/xb_meta ABI and three literal physical clock pins.']
    for name,p in pins.items():
        lines.append(f"place_pin -pin_name {{{name}}} -layer {p['layer']} -location {{{p['x']} {p['y']}}} -pin_size {{{p['w']} {p['h']}}} -force_to_die_boundary")
    (out/'pins.tcl').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection
    fig,axes=plt.subplots(1,2,figsize=(16,7),gridspec_kw={'width_ratios':[1.4,1]})
    ax=axes[0];cw=450.144;gap=1.188;fx=cw+gap;rx=fx+116.64+gap
    for x,w,label in [(0,cw,'Historical column outline\nE data assignment; new leaf homes OPEN'),(fx,116.64,'Five-root\nfront'),(rx,cw,'Historical column outline\nW-facing R0 view REQUIRED; no MY grant')]:
        ax.add_patch(Rectangle((x,0),w,198.72,fill=False));ax.text(x+w/2,145,label,ha='center',fontsize=9)
    seam=[]
    for n,p in pins.items():
        if n.startswith('c0['):seam.append([(cw,p['y']),(fx,p['y'])])
        if n.startswith('c1['):seam.append([(fx+116.64,p['y']),(rx,p['y'])])
    assert len(seam)==1552
    ax.add_collection(LineCollection(seam,colors='tab:blue',linewidths=.3))
    ax.set(xlim=(-10,rx+cw+10),ylim=(-15,215),xlabel='historical assembly context x (um)',ylabel='y (um)',title='Two requested 776-bit data-face relations; new parent layouts OPEN')
    ax.set_aspect('equal')
    ax=axes[1];ax.add_patch(Rectangle((0,0),116.64,198.72,fill=False))
    clocks=['ck','io_clk','io_n','io_w','io_e']
    for face,color in [('N','tab:green'),('S','tab:orange'),('W','tab:blue'),('E','tab:blue')]:
        pts=[p for n,p in pins.items() if p['face']==face and n not in clocks]
        ax.scatter([p['x'] for p in pts],[p['y'] for p in pts],s=1,color=color)
    for name in clocks:
        p=pins[name];ax.scatter([p['x']],[p['y']],s=30,color='red')
        shifts={'ck':(-48,-17),'io_clk':(6,-17),'io_n':(0,7),'io_w':(5,3),'io_e':(-29,3)}
        dx,dy=shifts[name];ax.annotate(f"{name}\n({p['x']:.3f},{p['y']:.3f})",(p['x'],p['y']),xytext=(p['x']+dx,p['y']+dy),fontsize=8)
    ax.text(58.32,154,'N: xb[1023:0] data only\nUnreset, as original source',ha='center',fontsize=9)
    ax.text(58.32,125,'ck: existing core\nand core-source lockups',ha='center',fontsize=9)
    ax.text(58.32,60,'S: programme/config/xs/status\nxb controls + IO-source-low lockups',ha='center',fontsize=9)
    ax.text(58.32,33,'Four actual local reset relays\nboot release +1 edge; payload +0',ha='center',fontsize=9)
    ax.set(xlim=(-10,126.64),ylim=(-24,218),title='Exact source-to-clock assignment proposal',xlabel='front local x (um)',ylabel='um');ax.set_aspect('equal')
    fig.suptitle(f'BF five-root front candidate: source body SHA256 {source_hash[:12]}, all3269 pin shapes retained +3 clocks\n1068 xb pins explicitly rebound to xb_data/xb_meta; native/capture and clock slot grants PENDING')
    fig.tight_layout();fig.savefig(out/'connected_pin_plan.png',dpi=150)
    print(json.dumps(dict(new_clock_pins=added,min_spacing_um=min(spacing.values()),pins=len(pins)),indent=2))


if __name__=='__main__':main()
