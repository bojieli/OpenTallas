#!/usr/bin/env python3
"""Structural ATT subgroup alternatives from literal physical inventory.

Distance is an optimistic PV source-to-bank affinity screen, not a netlist:
serializer selection, pipeline banks, clocks, query/KV and external VM paths
must be inserted and measured before any floorplan can be adopted.
"""
import argparse, hashlib, json, math, re
from pathlib import Path

QUAD='physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef'
MEM='physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef'
STAGE='physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef'

def lef(path):
    raw=Path(path).read_text(); size=tuple(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',raw).groups()));pins={}
    for p,b in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\bEND\s+\1(?:\s|$)',raw,re.S):
        shapes=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b)
        if shapes:
            x,y,X,Y=map(float,shapes[0]);pins[p]=((x+X)/2,(y+Y)/2)
    return dict(size=size,pins=pins,sha256=hashlib.sha256(raw.encode()).hexdigest(),path=str(path))

def bank(t,h,c):return (t*4+h//4)^((c&3)|((c&12)<<2))
def affinity(t):return (t//16)*4+t%4

def candidate(kind,q,m,st):
    # Physical macros retain original R0 orientations; no unsupported flips.
    qw,qh=q['size'];mw,mh=m['size'];street=43.2;gap=21.6
    blocks={}
    def put(n,x,y,w,h,role):blocks[n]=dict(x=x,y=y,w=w,h=h,role=role,orientation='R0')
    # Same128quad/128PVbanks in three substantially different groupings.
    if kind=='tile_local_rebank':
        tw=2*qw+gap+2*(mw+5.4)+street;th=2*(qh+gap)+street
        for t in range(32):
            ox=(t%8)*tw;oy=(t//8)*th
            for a in range(4):put(f'q{t}_{a}',ox+(a%2)*(qw+gap),oy+(a//2)*(qh+gap),qw,qh,'quad')
            for c in range(16):
                for hg in range(4):
                    put(f'b{(t*16+c)*4+hg}',ox+2*qw+gap+10.8+(hg%2)*(mw+5.4),oy+(hg//2)*(qh+gap)+c*(mh+5.4),mw,mh,'PVbank')
    elif kind=='tile_major':
        for t in range(32):
            ox=(t%8)*(2*qw+street+gap);oy=(t//8)*(2*qh+street+gap)
            for a in range(4):put(f'q{t}_{a}',ox+(a%2)*(qw+gap),oy+(a//2)*(qh+gap),qw,qh,'quad')
            for b in range(4):put(f'b{t*4+b}',ox+b*(mw+5.4),oy+2*qh+gap+5.4,mw,mh,'PVbank')
    elif kind=='head_major':
        for a in range(4):
            for t in range(32):put(f'q{t}_{a}',(t%8)*(qw+gap),(a*4+t//8)*(qh+street),qw,qh,'quad')
        for b in range(128):put(f'b{b}',(b%32)*(mw+gap),(16*(qh+street))+(b//32)*(mh+gap),mw,mh,'PVbank')
    else:
        # bank affinity invariant: t%4 and t//16; all16dimensionbeats stay local.
        gw=4*(qw+gap)+street+2*(mw+gap);gh=4*(qh+gap)
        for g in range(8):
            ox=(g%4)*(gw+street);oy=(g//4)*(gh+street)
            ts=[t for t in range(32) if affinity(t)==g]
            for row,t in enumerate(ts):
                for a in range(4):put(f'q{t}_{a}',ox+a*(qw+gap),oy+row*(qh+gap),qw,qh,'quad')
            bs=sorted({bank(t,h,c) for t in ts for h in range(16) for c in range(16)})
            assert len(bs)==16
            for j,b in enumerate(bs):put(f'b{b}',ox+4*(qw+gap)+street+(j%2)*(mw+gap),oy+(j//2)*(mh+gap),mw,mh,'PVbank')
    W=max(b['x']+b['w'] for b in blocks.values())+gap
    H=max(b['y']+b['h'] for b in blocks.values())+gap
    # Retain ALL known additional shared memories once; these explicit service
    # shelves do not assert the best query/KV/VM location or a complete design.
    for role,count,v,cols in [('query',64,m,16),('staging',34,st,17),('programme',1,st,1)]:
        w,h=v['size'];base=H+street
        for j in range(count):put(f'{role}{j}',gap+(j%cols)*(w+gap),base+(j//cols)*(h+gap),w,h,role)
        H=base+math.ceil(count/cols)*(h+gap);W=max(W,cols*(w+gap)+gap)
    total=0.;worst=0.;above=0;phase=[]
    bases=[0,2,8,10]
    for c in range(16):
        subtotal=0
        for t in range(32):
            for a,base in enumerate(bases):
                src=blocks[f'q{t}_{a}']
                for l in range(4):
                    h=base+4*(l//2)+l%2;dst=blocks[f'b{(t*16+c)*4+h//4 if kind=="tile_local_rebank" else bank(t,h,c)}']
                    for k in range(32):
                        sx,sy=q['pins'][f'oy[{l*32+k}]'];dx,dy=m['pins'][f'wd_in[{(h%4)*32+k}]']
                        d=abs(src['x']+sx-dst['x']-dx)+abs(src['y']+sy-dst['y']-dy)
                        subtotal+=d;worst=max(worst,d);above+=d>500
        phase.append(subtotal);total+=subtotal
    return dict(name=kind,PV_bank_count=2048 if kind=='tile_local_rebank' else 128,serializer_mapping_changed=kind=='tile_local_rebank',outline_um=[W,H],envelope_mm2=W*H/1e6,blocks=blocks,PV_affinity_screen=dict(sum_over_16beats_bit_um=total,max_source_to_bank_manhattan_um=worst,bit_beat_pairs=262144,pairs_over_500um=above,per_beat_bit_um=phase),qualified=False,complete_floorplan=False)

def rebank_audit():
    # Independent flat[head][dimension] scoreboard, not RTL qualification.
    memory={};reads=0;writes=0
    for record in range(3):
        epoch=record%2
        for c in range(16):
            seen=set()
            for t in range(32):
                for hg in range(4):
                    b=(t*16+c)*4+hg
                    assert b not in seen;seen.add(b)
                    memory[b,epoch]=tuple((record<<20)|(h<<12)|(t*16+c) for h in range(hg*4,hg*4+4));writes+=1
            assert len(seen)==128
        for h in range(16):
            for k in range(8):
                seen=set()
                for d in range(64):
                    dim=k*64+d;t,c=divmod(dim,16);b=(t*16+c)*4+h//4
                    assert b not in seen;seen.add(b)
                    assert memory[b,epoch][h%4]==(record<<20)|(h<<12)|dim;reads+=1
                assert len(seen)==64
    # Ignoring c aliases distinct dimensions: an actual architecture mutation.
    mutant_distinct=len({(t*16+0)*4+0 for t in range(4) for c in range(16)})
    assert mutant_distinct==4 and mutant_distinct<64
    return dict(records=3,word_checks=reads,macro_word_writes=writes,write_banks_per_beat=128,read_banks_per_edge=64,commit_edges_per_record=128,dimension_omission_mutant_rejected=True,native_RTL_qualification=False)

def svg(cases,path):
    scale=.052;pw,ph=650,690;out=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1300" viewBox="0 0 1320 1300">', '<rect width="100%" height="100%" fill="white"/>','<style>text {font-family:Arial,sans-serif} .small {font-size:11px} .axis {font-size:10px;fill:#555}</style>', '<text x="20" y="26" font-size="20" font-weight="bold">HBM attention: structural regrouping of actual macro inventory</text>', '<text x="20" y="48" font-size="13">All panels share physical scale. PV-only comparison; full die, outside connections and clocks remain unresolved.</text>']
    colors={'quad':'#dc9d52','PVbank':'#d04e8a','query':'#4c8ac0','staging':'#57a777','programme':'#956fc0'}
    titles={'tile_major':'A. Tile-major: current bank architecture', 'head_major':'B. Head-major: current bank architecture','bank_affinity':'C. Eight complete bank-affinity groups','tile_local_rebank':'D. Tile-local storage: larger structural alternative'}
    # Place the two meaningful alternatives alongside the tile-major comparison;
    # head-major is included as an explicit poor-PV-locality comparison.
    ordered=[cases[0],cases[2],cases[1],cases[3]]
    for i,c in enumerate(ordered):
        px=20+(i%2)*pw;py=82+(i//2)*470;x0=px+30;y0=py+94
        W,H=c['outline_um'];r=c['PV_affinity_screen'];bs=c['blocks']
        out += [f'<rect x="{px}" y="{py}" width="630" height="{455 if i<2 else 675}" rx="5" fill="#fff" stroke="#bbb"/>',f'<text x="{px+12}" y="{py+23}" font-size="16" font-weight="bold">{titles[c["name"]]}</text>',f'<text x="{px+12}" y="{py+44}" font-size="12">{c["PV_bank_count"]} PV SRAMs; envelope {c["envelope_mm2"]:.2f} mm²; {W:.0f} × {H:.0f} µm</text>',f'<text x="{px+12}" y="{py+63}" font-size="12">PV affinity {r["sum_over_16beats_bit_um"]/1e6:.1f} M bit-µm; worst {r["max_source_to_bank_manhattan_um"]:.0f} µm</text>']
        if c['name']=='tile_local_rebank':out.append(f'<text x="{px+12}" y="{py+81}" font-size="12" fill="#a52e65">+1920 real SRAMs / +2.052 mm² macro area; new RTL required</text>')
        out.append(f'<rect x="{x0}" y="{y0}" width="{W*scale}" height="{H*scale}" fill="#fafafa" stroke="#333"/>')
        for n,b in bs.items():
            x=x0+b['x']*scale;y=y0+(H-b['y']-b['h'])*scale;w=b['w']*scale;h=b['h']*scale
            out.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{colors[b["role"]]}" stroke="white" stroke-width=".35"><title>{n}: {b["role"]}, {b["w"]}×{b["h"]} µm, R0, origin {b["x"]},{b["y"]}</title></rect>')
            if b['role']=='quad':out.append(f'<text x="{x+1:.3f}" y="{y+8:.3f}" font-size="6.5">{n}</text>')
        for v in range(0,int(W)+1,2000):
            xx=x0+v*scale;yy=y0+H*scale
            out.append(f'<path d="M{xx},{yy} v5" stroke="#555"/><text x="{xx-5}" y="{yy+17}" class="axis">{v}</text>')
        for v in range(0,int(H)+1,2000):
            yy=y0+(H-v)*scale
            out.append(f'<path d="M{x0-5},{yy} h5" stroke="#555"/><text x="{x0-27}" y="{yy+3}" class="axis">{v}</text>')
        out.append(f'<text x="{x0+W*scale+4}" y="{y0+H*scale+17}" class="axis">µm</text>')
        # Same source/head/phase examples in each arrangement. These lines are
        # representative geometric affinities, not routes or additional nets.
        for j,(t,head,dim) in enumerate([(0,0,0),(0,0,4),(4,0,0),(8,0,0),(12,0,0)]):
            a=0;l=0;src=bs[f'q{t}_{a}'];dst=bs[f'b{(t*16+dim)*4+head//4 if c["name"]=="tile_local_rebank" else bank(t,head,dim)}']
            qp=lef_cached_q['pins']['oy[0]'];mp=lef_cached_m['pins']['wd_in[0]'];sx=x0+(src['x']+qp[0])*scale;sy=y0+(H-src['y']-qp[1])*scale;dx=x0+(dst['x']+mp[0])*scale;dy=y0+(H-dst['y']-mp[1])*scale
            color=['#225ec0','#cb2525','#225ec0','#225ec0','#225ec0'][j]
            out.append(f'<path d="M{sx:.2f},{sy:.2f} H{dx:.2f} V{dy:.2f}" fill="none" stroke="{color}" stroke-width="1.4" opacity=".85"><title>Representative PV affinity: tile{t}, head{head}, dimensionphase{dim}; actual source and SRAM input pin centres, not a routed path</title></path><circle cx="{sx:.2f}" cy="{sy:.2f}" r="2" fill="{color}"/><circle cx="{dx:.2f}" cy="{dy:.2f}" r="2" fill="{color}"/>')
        note_y=y0+H*scale+45;note_x=px+12
        if c['name']=='head_major':note_y=y0+60;note_x=x0+W*scale+15
        out += [f'<text x="{note_x}" y="{note_y}" class="small">NE VM RG3 query / WG1 output: homes TBD.</text>', f'<text x="{note_x}" y="{note_y+16}" class="small">KV / PHY / clocks outside; no route claim.</text>']
    out += ['<rect x="20" y="1271" width="12" height="12" fill="#dc9d52"/><text x="38" y="1282" class="small">128 quads</text>', '<rect x="135" y="1271" width="12" height="12" fill="#d04e8a"/><text x="153" y="1282" class="small">PV banks</text>','<rect x="244" y="1271" width="12" height="12" fill="#4c8ac0"/><text x="262" y="1282" class="small">64 query</text>','<rect x="349" y="1271" width="12" height="12" fill="#57a777"/><text x="367" y="1282" class="small">34 KV staging</text>','<rect x="485" y="1271" width="12" height="12" fill="#956fc0"/><text x="503" y="1282" class="small">1 programme</text>','<path d="M620,1278 h35" stroke="#225ec0" stroke-width="2"/><text x="665" y="1282" class="small">Representative PV pin affinities; not routes</text>','<path d="M1010,1278 h104" stroke="black" stroke-width="3"/><text x="1122" y="1282" class="small">2000 µm</text>','</svg>'];Path(path).write_text('\n'.join(out))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--out',required=True);a=p.parse_args();root=Path(a.root);q,m,st=[lef(root/x) for x in [QUAD,MEM,STAGE]];out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    global lef_cached_q,lef_cached_m;lef_cached_q=q;lef_cached_m=m
    cases=[candidate(k,q,m,st) for k in ['tile_major','head_major','bank_affinity','tile_local_rebank']]
    r=dict(rebank_model_audit=rebank_audit(),schema='opentallas.hbm.system_geometry.structural_candidates.v1',physical_view_inputs=[{k:v for k,v in d.items() if k!='pins'} for d in [q,m,st]],inventory=dict(quads=128,PVbanks=128,query=64,staging=34,programme=1),candidates=cases,limitations=['This is a structural floorplan precursor, not the full HBM die.','PV affinity screen uses real source oy pins and memory wd_in pins; selection mux/capture/registered pipeline are absent. It is an optimistic adjacency metric, not actual routed/netlist wirelength.','One fullH16 engine:32logicaltiles, proposed logicaltile=physicalpair; exact assignment still needs source binding.','Canonical NE VM WG1 output and RG3 query, KV multi-stack source/PHY, all SM/SU/IDX/COLL/clock children must enter the common graph before adoption.','tile_local_rebank is an explicit larger-memory successor, not canonical source; 2048 banks, epoch-only address, requires new RTL, clocks and compiler/consumer proof.','Query64/staging34/programme1 shelves retain all hardware counts but their connectivity is not optimized here.','No native/timing/cut/clock/PG/pin-access qualification; no performance estimate.'])
    (out/'candidates.json').write_text(json.dumps(r,indent=2)+'\n');svg(cases,out/'candidates.svg');print(json.dumps([{k:c[k] for k in ['name','outline_um','envelope_mm2','PV_affinity_screen']} for c in cases]))
if __name__=='__main__':main()
