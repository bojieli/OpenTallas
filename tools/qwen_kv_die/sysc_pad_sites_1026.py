#!/usr/bin/env python3
"""Allocate actual SYS_C R8 landing flop chains in the macro-free north corridor.

This is a placement trial: source/pad hops are bounded; consumer reach requires
postplace census, and no CTS/route is authorized by this allocation.
"""
import argparse,json,math,re
from pathlib import Path

def allocate(plan,pins,netlist,out,reset_tcl=None):
    raw=json.loads(Path(plan).read_text());t=raw['partition_types']['kv3_sys_c']
    pins=json.loads(Path(pins).read_text()); pp={(p['bus'],p['bit']):(p['x'],p['y']) for p in pins}
    cells=re.findall(r'^  (\w*DFF\w*)\s+\\(u_bound\.u_pd\S+)\s+\(',Path(netlist).read_text(),re.M)
    if len(cells)!=8868:raise ValueError(f'actual pad inventory changed: {len(cells)} !=8868')
    # Use the real source pin table, not compressed naming assumptions.
    busmap={re.sub(r'_+','_',p['bus']):p['bus'] for p in pins}
    occupied=set()
    def reserve(x,y):
        ix=round(x/.108); iy=round(y/.27)
        for a in range(ix-6,ix+7):
            for b in range(iy,iy+1):occupied.add((a,b))
    for ft in t.get('ft_slots',[]):
        for stage in ft.get('bit_sites_um',[]):
            for x,y in stage:reserve(x,y)
    for station in t.get('internal_stations',[]):
        for x,y in station.get('regs_um',[]):reserve(x,y)
    if reset_tcl:
        text=Path(reset_tcl).read_text()
        for x,y in re.findall(r'^rtr_place \S+ \{[^}]+\} ([0-9.]+) ([0-9.]+) ',text,re.M):
            ix,iy=round(float(x)/.108),round(float(y)/.27)
            for a in range(ix-40,ix+41):
                for b in range(iy-16,iy+17):occupied.add((a,b))
    blocked=[tuple(r) for r in t.get('clock',{}).get('die_islands_um',[])]
    for c in t['contents']:
        x,y=c['origin_um'];w,h=c['outline_um'];blocked.append((x-8.64,y-8.64,x+w+8.64,y+h+8.64))
    def snap(x,y):
        ix=round(x/.108);iy=round(y/.27)
        for r in range(150):
            for dx,dy in ((0,r),(0,-r),(16,r),(-16,r),(16,-r),(-16,-r),(160,r),(-160,r),(160,-r),(-160,-r)):
                a,b=ix+dx,iy+dy;xx,yy=a*.108,b*.27
                if not 20<xx<2140 or not 10<yy<1020:continue
                if any(l-1.2<=xx<=rr+1.2 and bb-.27<=yy<=tt+.27 for l,bb,rr,tt in blocked):continue
                if any((a+k,b) in occupied for k in range(-6,7)):continue
                reserve(xx,yy);return [round(xx,6),round(yy,6)]
        raise ValueError(f'cannot allocate {x},{y}')
    sites=[]; chains={}
    for master,name in sorted(cells):
        if master!='DFFHQNx1_ASAP7_75t_R':raise ValueError('pad master footprint changed: '+master)
        m=re.fullmatch(r'u_bound\.u_pd(\d+)_(.*)_(\d+)\.r\[(\d+)\]\$_DFF_P_',name)
        if not m:raise ValueError('unexpected pad name '+name)
        depth,bus,bit,stage=int(m[1]),busmap[m[2]],int(m[3]),int(m[4]);sx,sy=pp[bus,bit]
        if bus=='i_kvs_attn_attn__tx_payload':
            x=[1940,1720,1500,1500,1280,1060,840,720,400,180][stage]
            y=sy if stage<3 else 900+(bit-273.5)*.162
        elif bus=='i_kvs_emb_rowtx__emb_tx_payload':x=100*(stage+1);y=sy
        else:
            x=(120+stage*35) if sx==0 else (2040-stage*35);y=sy
        xy=snap(x,y)
        row=dict(inst=name,xy_um=xy,bus=bus,bit=bit,stage=stage,depth=depth)
        sites.append(row);chains.setdefault((bus,bit),[]).append(row)
    maxhop=0
    for key,rows in chains.items():
        rows.sort(key=lambda a:a['stage']);depth=rows[0]['depth']
        if [r['stage'] for r in rows]!=list(range(depth)):raise ValueError('missing pad stage '+str(key))
        path=[pp[key]]+[r['xy_um'] for r in rows]
        for a,b in zip(path,path[1:]):
            dist=abs(a[0]-b[0])+abs(a[1]-b[1]);maxhop=max(maxhop,dist)
            if dist>405:raise ValueError(f'pad hop >405: {key}: {dist}')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'sites.json').write_text(json.dumps(dict(status='PLACEMENT TRIAL ONLY; consumer reach not measured',count=len(sites),max_source_pad_hop_um=maxhop,sites=sites),indent=1)+'\n')
    tcl=['# Actual native R8 pad FF trial allocation; no latency changes.', 'uplevel #0 {','set pb [ord::get_db_block]','set pu [[ord::get_db_tech] getDbUnitsPerMicron]','set pr {}','foreach r [$pb getRows] { dict set pr [lindex [$r getOrigin] 1] [$r getOrient] }','set pc 0']
    for row in sites:
        n=re.sub(r'(?<!\\)([\[\]])',r'\\\1',row['inst']);x,y=row['xy_um'];tcl += [f'set pi [$pb findInst {{{n}}}]',f'if {{$pi eq "NULL"}} {{ error {{missing landing FF {n}}} }}',f'set px [expr {{round({x}*$pu)}}]; set py [expr {{round({y}*$pu)}}]', 'if {![dict exists $pr $py]} { error "landing FF row not legal: $py" }', '$pi setOrient [dict get $pr $py]', '$pi setOrigin $px $py', '$pi setPlacementStatus FIRM','incr pc']
    tcl += ['puts "SYS_C_NATIVE_PADS FIRM $pc"','}']
    (out/'pad_sites.tcl').write_text('\n'.join(tcl)+'\n')
    (out/'pad_release.tcl').write_text('uplevel #0 {\nset b [ord::get_db_block]\nforeach i [$b getInsts] { if {[regexp {^u_bound[.]u_pd[0-9]+_} [$i getName]] && [$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED } }\n}\n')
    print('Allocated',len(sites),'actual FF, source/pad max hop',maxhop,'consumer reach NOT RUN')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','pins','netlist','out'):p.add_argument('--'+n,required=True)
    p.add_argument("--reset-tcl")
    a=p.parse_args();allocate(a.plan,a.pins,a.netlist,a.out,a.reset_tcl)
