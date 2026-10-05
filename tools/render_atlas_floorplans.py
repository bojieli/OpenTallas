#!/usr/bin/env python3
"""Render Atlas plates from recorded ROM coordinates and explicit HBM concepts.

No placement, route or sign-off verdict is inferred by this renderer.
"""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/floorplans'
Q = 'results/floorplan/qwen_o4/floorplan.json'
D = 'results/physical_abi3/asap7/chip/v41_w18/die_floorplan_ch8.64.json'
HBM = 'tools/hbm_gpu_floorplan.py'
COL = dict(weight='#e7b17c', hub='#c5b5dc', memory='#95bed9', service='#86c6b2', wire='#d5dde4')

def txt(x, y, s, size=14, color='#243447', anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(s)}</text>'

def box(x, y, w, h, fill, title='', stroke='#ffffff'):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="0.7"><title>{html.escape(title)}</title></rect>'

def plate(title, status, body, notes):
    return '\n'.join(['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800" role="img">',
        f'<title>{html.escape(title)}</title><desc>{html.escape(status + ". " + " ".join(notes))}</desc>',
        '<style>text{font-family:Arial,Helvetica,sans-serif}</style>', box(0,0,1000,800,'#f6f8fa'),
        txt(32,42,title,25), box(32,58,936,38,'#fff0d6',stroke='#e1c085'),txt(45,83,status,15),body,
        box(32,655,936,125,'#ffffff',stroke='#d5dde4'),
        *[txt(48,680+i*23,s,14) for i,s in enumerate(notes)], '</svg>'])

def rom_qwen():
    data=json.loads((ROOT/Q).read_text()); p=data['designs']['rom_die.rtl_as_instantiated']
    scale=0.0175; ox,oy=46,135
    def b(r,c): return box(ox+r['x']*scale,oy+r['y']*scale,r['w']*scale,r['h']*scale,c,r.get('name',''))
    out=[b(p['regions'][0],'#e9edf1')]
    for r in p['regions'][1:]:
        kind=r.get('kind',''); color=COL['service'] if 'service' in kind.lower() or 'phy' in kind.lower() else COL['hub']
        out.append(b(r,color))
    for a in p['geometry']['arrays']:
        for row in range(a['rows']):
            for col in range(a['cols']):
                r=dict(x=a['x0']+col*p['tile']['w']+(col//4)*60,y=a['y0']+row*p['tile']['h']+(row//8)*60,w=p['tile']['w'],h=p['tile']['h'])
                out.append(b(r,COL['weight']))
    out += [txt(675,155,'Recorded die geometry',19),txt(675,184,'31.80 × 25.63 mm'),txt(675,225,'Weight tiles',17),txt(675,250,'West and east arrays'),txt(675,285,'Central spine',17),txt(675,310,'VM · vector lanes · scales'),txt(675,335,'embedding · control'),txt(675,375,'Shoreline service / link',17),txt(675,405,'KV remains in attached HBM'),txt(675,455,'FIT CHECK: FAIL',18,'#a53225'),txt(675,482,'1,512 needed / 1,225 slots'),txt(675,525,'Current target: TP-4',17),txt(675,550,'2 packages × 2 ROM dies'),txt(675,575,'Rebase of this snapshot pending')]
    return plate('Qwen3-8B ROM — coordinate floorplan snapshot','HISTORICAL GEOMETRY • fit failed • current option-C layout not qualified',''.join(out),[
        'Drawn from qwen_o4/floorplan.json, rtl_as_instantiated profile; units and proportions are retained.',
        'Orange: weight tiles. Purple: central spine reservations. Green: shoreline service and links.',
        'This older profile is not the current four-die product and is not evidence of 1.2 GHz closure.',
        'Replace after current tile abstracts, TP-4 inventory, clock insertion and composed route are validated.'])

def rom_ds():
    d=json.loads((ROOT/D).read_text()); scale=.0175; ox,oy=46,135
    def b(r,c):return box(ox+r['x']*scale,oy+r['y']*scale,r['w']*scale,r['h']*scale,c,r.get('name',r.get('kind','')))
    out=[box(ox,oy,d['die']['w_um']*scale,d['die']['h_um']*scale,'#e9edf1')]
    for c in d['clusters']:out.append(b(c,COL['weight']))
    for r in d['service'].values():out.append(b(r,COL['service']))
    for r in d['hub']['parts'].values():out.append(b(r,COL['hub'] if r['kind']!='VM' else COL['memory']))
    out += [txt(675,155,'Recorded die geometry',19),txt(675,184,'31.80 × 25.63 mm'),txt(675,225,'Replicated ROM clusters',17),txt(675,251,'Old p5 element abstract'),txt(675,295,'Central dedicated hub',17),txt(675,321,'Attention · vector · mHC'),txt(675,347,'VM · gather · collective'),txt(675,390,'North / south HBM service',17),txt(675,416,'Persistent per-user KV'),txt(675,460,'Snapshot capacity only',17),txt(675,487,'7,102 pairs / 7,628 slots'),txt(675,532,'Current plus-hub rebase',17),txt(675,559,'and mapped elements pending')]
    return plate('DeepSeek-V4.1 ROM — coordinate floorplan snapshot','INTERIM GEOMETRY • old elements and hub reservations • current rebase pending',''.join(out),[
        'Drawn from v41_w18/die_floorplan_ch8.64.json; actual cluster and hub coordinates are retained.',
        'Orange: ROM clusters. Purple: dedicated hub. Blue: VM. Green: HBM service reservations.',
        'The snapshot slot count does not qualify current weight ownership, BF16 columns or complete timing.',
        'Replace with the current mapped-element / plus-hub assembly after contextual SS/FF and route checks.'])

def hbm(model):
    out=[box(45,125,645,500,'#e9edf1',stroke='#243447')]
    for y in (135,575):
        for x in (70,390):
            out.append(box(x,y,270,38,COL['service'],'HBM PHY, controller and service queue'))
            out.append(txt(x+135,y+24,'HBM PHY / controller / queues',13,anchor='middle'))
    for row in range(4):
        for col in range(8):
            x,y=70+col*75,219+row*70
            out += [box(x,y,67,57,COL['weight'],'SM: matrix + SIMT lanes, RF and shared memory'),txt(x+33.5,y+22,f'SM {row*8+col}',12,anchor='middle'),txt(x+33.5,y+40,'TC / RF',10,anchor='middle')]
    for x in (70,220,370,520):
        out += [box(x,185,142,23,COL['memory'],'L2 slice'),txt(x+71,201,'Banked L2 slice',11,anchor='middle')]
    out += [box(70,510,592,43,COL['hub'],'NoC and collective transport'),txt(366,536,'NoC · collectives · publication / reuse fences',14,anchor='middle')]
    out += [txt(720,155,'32 SMs • 8 × 4 concept',18),txt(720,191,'Within every SM:',17),txt(720,220,'Matrix / tensor unit'),txt(720,247,'FP32 SIMT vector lanes'),txt(720,274,'Register file + shared SRAM'),txt(720,315,'Decode dataflow',17),txt(720,344,'HBM → L2 → SM'),txt(720,371,'accumulator → epilogue'),txt(720,398,'→ collective → consumer'),txt(720,447,'Full area / route fit: OPEN',16,'#a53225'),txt(720,477,'RF and service included'),txt(720,504,'in qualification requirements')]
    q=model=='Qwen3-8B'
    notes=['Proposed GPU organisation; diagram is not to scale and is not an actual placed or routed die.',
        'Uses the 32-SM organisation in hbm_gpu_floorplan.py; no ROM-specific dedicated vector hub.',
        'Qwen: historical SM slot is smaller than the updated SM requirement; a new fit is required.' if q else 'DeepSeek: ordinary SIMT executes mHC, norms and vector work; complete RF/service fit is still open.',
        'Replace after full SM abstracts, L2/service allocation, transport and contextual SS/FF qualification.']
    return plate(model+' HBM — proposed GPU die organisation','ILLUSTRATIVE ONLY • not to scale • full SM / service / physical qualification pending',''.join(out),notes)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,svg in [('qwen-rom',rom_qwen()),('deepseek-rom',rom_ds()),('qwen-hbm',hbm('Qwen3-8B')),('deepseek-hbm',hbm('DeepSeek-V4.1'))]:
        (OUT/(name+'.svg')).write_text(svg+'\n')
    manifest={'schema':'opentallas.atlas-floorplan-illustrations.v1','qualification':'illustrations only; captions define evidence scope','sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (Q,D,HBM,'tools/qwen_o4_floorplan.py')},'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'plates':{n:hashlib.sha256((OUT/(n+'.svg')).read_bytes()).hexdigest() for n in ('qwen-rom','deepseek-rom','qwen-hbm','deepseek-hbm')}}
    (OUT/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
