#!/usr/bin/env python3
"""Selected Qwen path: SYS_C actual macros and registered north-channel detour.

Consumes the actual native-bound macro proposal and actual type pins. Emits a
plan delta plus cycle receipt. This is physical-model geometry, not a route or
PG signoff: the kit must install the separate PHY PG hook and pass actual gates.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import ft_bit_sites_gen as F

PHY=[691.2,17.28,1468.8,794.88]
LEFT=656.64
RIGHT=1503.36
NORTH=829.44
GUARD=8.64    # VDDPHY guard ring W/E/N (one die-grid pitch; clear of the R4 clock taps at x 680 / 1480 and the detour stations)
S_MOAT=8.64   # S side: the domain stops 8.64 um inside the partition edge (core-VDD moat to the S neighbour)


def split_path(path):
    pts=[]
    for a,b in zip(path,path[1:]):
        n=max(1,math.ceil(F.man(a,b)/405))
        pts.extend([round(a[0]+(b[0]-a[0])*j/n,4),round(a[1]+(b[1]-a[1])*j/n,4)] for j in range(1,n+1))
    return pts


def apply(raw,pins,proposal,io):
    t=raw['partition_types']['kv3_sys_c'];W,H=t['outline_um']
    t['contents']=copy.deepcopy(proposal['macros'])
    for key in ('clock','reset'):t.setdefault(key,{})['tap_um']=[LEFT,518.4]
    ledger=[]
    for e in t.get('internal_stations',[]):
        if e.get('conn')!='bus:o_host_link_rst_n':continue
        a,b=e['from_um'],e['to_um'];before=len(e['regs_um'])
        path=[a,[LEFT,a[1]],[LEFT,NORTH],[RIGHT,NORTH],[RIGHT,b[1]],b]
        e['regs_um']=split_path(path)[:-1]
        e['note']='SYS_C actual UCIe north-channel detour; <=405um; old straight path crossed PHY body'
        ledger.append(dict(conn=e['conn'],before=before,after=len(e['regs_um']),added_cycles=len(e['regs_um'])-before))
    blocks=[(*m['origin_um'],m['origin_um'][0]+m['outline_um'][0],m['origin_um'][1]+m['outline_um'][1]) for m in t['contents']]
    for e in t.get('internal_stations',[]):
        for x,y in e['regs_um']:blocks.append((x-3,y-3,x+3,y+3))
    F.FACE_KEEP_UM=7.;sites=F.Sites(W,H,blocks)
    by={}
    for p in pins:by.setdefault(p['bus'],{})[p['bit']]=(p['x'],p['y'])
    slot=next(s for s in t['ft_slots'] if s['name']=='ft1');n=slot['width']+1
    A,B=by['ft1_i'],by['ft1_o'];order=sorted(range(n),key=lambda i:A[i][1]);rank={i:r for r,i in enumerate(order)}
    stages=[[None]*n for _ in range(11)];maxhop=maxout=0;draw=[]
    for i in order:
        r=rank[i];yn=NORTH+r*.27;xl=LEFT-28.08+r*.054;xr=RIGHT+r*.054
        pts=[((12+LEFT)/2,A[i][1]),(LEFT,A[i][1]),(xl,690),(LEFT,yn),
             (LEFT+(RIGHT-LEFT)/3,yn),(LEFT+2*(RIGHT-LEFT)/3,yn),(RIGHT,yn),
             (xr,690),(RIGHT,B[i][1]),((RIGHT+W-12)/2,B[i][1]),(W-12,B[i][1])]
        out=[]
        for j,p in enumerate(pts):
            xy=sites.take(*p,horiz=(j in (0,1,4,5,6,9,10)))
            stages[j][i]=list(xy);out.append((xy[0]+F.CELL[0]/2,xy[1]+F.CELL[1]/2))
        chain=[A[i]]+out+[B[i]];hops=[F.man(a,b) for a,b in zip(chain,chain[1:])]
        maxhop=max(maxhop,max(hops));maxout=max(maxout,hops[-1])
        if r%32==0:draw.append(dict(bit=i,path=chain))
    if maxhop>405 or maxout>20:raise ValueError(f'actual FT hop/outface fail: {maxhop}/{maxout}')
    before=slot['stations'];slot.update(stations=12,bit_sites_um=stages,bit_site_cell_um=list(F.CELL));slot.pop('regs_um',None)
    ledger.append(dict(conn='slot:ft1',bits=n,before=before,after=12,added_cycles=12-before,added_flops=(12-before)*n))
    # PHY PG domain (OWNER decision 7; same form as S81 pg_domains.py / HBM B2m): own VDDPHY+VSS over the UCIe body plus
    # a guard ring INSIDE sys_c (never over a core-VDD neighbour); on the S side the domain stops S_MOAT short of the
    # partition edge so VDDPHY M7 straps never meet the S neighbour's core-VDD M7 straps end to end.  Every station, FT
    # site and SRAM stays outside the domain (core VDD).  Kit side: gen_phys.phy_pg_pdn (PHY region grid + macro grid,
    # core grid cut, placement blockage); the abstract then exports VDDPHY M7 pins only inside this rect.
    dom_t=[round(PHY[0]-GUARD,4),round(PHY[1]-S_MOAT,4),round(PHY[2]+GUARD,4),round(PHY[3]+GUARD,4)]
    assert dom_t[0]>0 and dom_t[1]>0 and dom_t[2]<W and dom_t[3]<H,dom_t
    def inside(x,y,r=dom_t):return r[0]<=x<=r[2] and r[1]<=y<=r[3]
    bad=[('ft1',xy) for st in stages for xy in st if xy and inside(*xy)]
    bad+=[(e['conn'],xy) for e in t.get('internal_stations',[]) for xy in e['regs_um'] if inside(*xy)]
    bad+=[(m['inst'],m['origin_um']) for m in t['contents'] if m['module']!='ot_qkvd_ucie_x64_phy' and
          m['origin_um'][0]+m['outline_um'][0]>dom_t[0] and m['origin_um'][0]<dom_t[2] and
          m['origin_um'][1]+m['outline_um'][1]>dom_t[1] and m['origin_um'][1]<dom_t[3]]
    if bad:raise ValueError(f'core-VDD objects inside the PHY PG domain: {bad[:5]}')
    part=next(p for p in raw['partitions'] if p['type']=='kv3_sys_c');ox,oy=part['origin_um']
    rect=[round(PHY[0]+ox,4),round(PHY[1]+oy,4),round(PHY[2]+ox,4),round(PHY[3]+oy,4)]
    drect=[round(dom_t[0]+ox,4),round(dom_t[1]+oy,4),round(dom_t[2]+ox,4),round(dom_t[3]+oy,4)]
    pg=raw['die'].setdefault('pg',{});domains=pg.setdefault('domains',[])
    dom=dict(name='phy_sys_c_ucie',nets=['VDDPHY','VSS'],io=['io_sys_c_ucie_rom'],rect_um=drect,
             grid=[dict(layer=l,width_um=1.92,pitch_um=8.64,offset_um=4.32,nets=['VDDPHY','VSS']) for l in ['M8','M9']],
             bumps=dict(rect_um=rect,pitch_um=45.,use='power_ground',note='dedicated VDDPHY/VSS C4 rows over the UCIe macro (45-um array); academic bump assumption, not vendor escape qualification'),
             note='OWNER decision 7: separate PHY supply on the UCIe macro, guard ring inside sys_c, no core-VDD object inside; the partition kit exports truthful VDDPHY M7 pins (gen_phys.phy_pg_pdn), never relabels core VDD')
    domains[:]=[d for d in domains if d['name']!=dom['name']];domains.append(dom)
    for e in io:
        if e['name']=='io_sys_c_ucie_rom':
            e['rect_um']=rect;e['sites']=int(777.6//45)**2
            if 'dedicated VDDPHY' not in e.get('note',''):e['note']=e.get('note','')+' | actual native macro abstract footprint; dedicated VDDPHY domain phy_sys_c_ucie'
    report=dict(type='kv3_sys_c',verdict="GEOMETRY_PASS_PG_DOMAIN_PLANNED",max_ft_hop_um=maxhop,max_out_hop_um=maxout,ft_sites=len(sites.used),ledger=ledger,phy_rect_type_um=PHY,phy_rect_die_um=rect,pg_domain_type_um=dom_t,pg_domain_die_um=drect,sampled=draw,required='Install actual partitionPHYsplitPG, macro clock/reset keepouts; regenerate latency/R8/native bound RTL then G2+review')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('pins');p.add_argument('proposal');p.add_argument('io');p.add_argument('out');p.add_argument('--report',required=True);p.add_argument('--io-out',required=True);a=p.parse_args()
    raw=json.loads(Path(a.plan).read_text());io=json.loads(Path(a.io).read_text());r=apply(raw,json.loads(Path(a.pins).read_text()),json.loads(Path(a.proposal).read_text()),io)
    Path(a.out).write_text(json.dumps(raw,indent=1)+'\n');Path(a.io_out).write_text(json.dumps(io,indent=1)+'\n');Path(a.report).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='sampled'}))

if __name__=='__main__':main()
