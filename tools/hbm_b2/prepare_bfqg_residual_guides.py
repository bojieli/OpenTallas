#!/usr/bin/env python3
"""Materialize a placement-only BFQG bank6/7 residual-guide proposal from actual connectivity."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def norm(s):
    return s.replace('\\', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ['dump', 'pins', 'lef', 'model', 'out']:
        ap.add_argument('--' + n, required=True, type=Path)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('geom_rules', ROOT / 'tools/autopilot/geom_rules.py')
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    D = g.Design(a.dump); names = {norm(c[6]): i for i, c in D.cells.items()}
    ref = json.loads(a.model.read_text())
    boxes = {r['bank']: r['box_um'] for r in ref['bank_internal_guides']}
    banks, all_caps = {}, set()
    for i, c in D.cells.items():
        if c[0] != 'M':
            continue
        match = re.fullmatch(r'g_t\[(\d+)\]\.u_m', norm(c[6]))
        if not match:
            raise ValueError('unexpected macro')
        bank = int(match[1]); seen = set(); front = list(D.drives[i]); captures = set()
        while front:
            n = front.pop()
            if n in seen: continue
            seen.add(n)
            for s in D.nets[n][2]:
                if s[0] != 'i' or s[2]: continue
                if D.kind(s[1]) == 'S': captures.add(s[1])
                elif D.kind(s[1]) in {'B', 'L', 'K'}: front.extend(D.drives[s[1]])
        if len(captures) != 256 or captures & all_caps:
            raise ValueError('macro first-capture membership changed')
        all_caps |= captures
        banks[bank] = dict(macro=i, captures=captures, rp_sel=names[f'g_t[{bank}].rp_sel$_SDFF_PN0_'])
    if set(banks) != set(range(8)):
        raise ValueError('all eight native SRAMs required')
    # Full public boundary protection, including the nine native synchronous-reset captures.
    public = set()
    for p in D.pins:
        if p['name'].startswith('clk'): continue
        n = D.pin_net.get(p['k']); seen = set(); front = [] if n is None else [n]
        while front:
            n = front.pop()
            if n in seen: continue
            seen.add(n)
            refs = D.nets[n][2] if p['io'] == 'INPUT' else [D.nets[n][1]]
            for s in refs:
                if not s or s[0] != 'i' or s[2]: continue
                if D.kind(s[1]) == 'S': public.add(s[1])
                elif D.kind(s[1]) == 'B':
                    if p['io'] == 'INPUT': front.extend(D.drives[s[1]])
                    else: front.extend(nn for nn, clock in D.cell_in[s[1]] if not clock)
    public.add(names['wce_q$_SDFF_PN0_'])
    public.update(names[f'g_t[{b}].rp_ce$_SDFF_PN0_'] for b in range(8))
    groups = []; moved = {}; targets = {}; lef = a.lef.read_text()
    for bank in [6, 7]:
        bs = banks[bank]; ids = bs['captures'] | {bs['rp_sel']}; box = boxes[bank]
        if len(ids) != 257 or ids & public:
            raise ValueError('residual guide overlaps public capture')
        macro = D.cells[bs['macro']]; row_slots = defaultdict(int)
        for cid in sorted(bs['captures'], key=lambda i: norm(D.cells[i][6])):
            c = D.cells[cid]; w, h = c[4]-c[2], c[5]-c[3]
            bit_match = re.fullmatch(r'cap\['+str(bank)+r'\]\[(\d+)\]\$_DFF_P_', norm(c[6]))
            if not bit_match: raise ValueError('actual first-capture alias not expected native CQ')
            bit = int(bit_match[1]); pm = re.search(r'  PIN rd_out\['+str(bit)+r'\]\n(.*?)  END rd_out\['+str(bit)+r'\]', lef, re.S)
            rect = list(map(float, re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', pm.group(1)).groups()))
            pin_y = macro[3] + (rect[1]+rect[3])/2
            row = round((pin_y - 4.32 - h/2)/0.27)
            slot = row_slots[row]; row_slots[row] += 1
            x0 = box[0] + slot * w; y0 = 4.32 + row * 0.27
            if x0+w > box[2] or y0 < box[1] or y0+h > box[3]:
                raise ValueError('target packing outside approved box')
            targets[cid] = [x0, y0, x0+w, y0+h]
        # One free column beside the CQ rows for the existing bank selection FF.
        cid = bs['rp_sel']; c = D.cells[cid]; w,h=c[4]-c[2],c[5]-c[3]
        y0 = 4.32 + round(((box[1]+box[3])/2-4.32)/0.27)*0.27
        targets[cid] = [box[0]+5*w,y0,box[0]+6*w,y0+h]
        for cid in ids:
            c=D.cells[cid]; w,h=c[4]-c[2],c[5]-c[3]
            moved[cid]=[box[0]+w/2,box[1]+h/2,box[2]-w/2,box[3]-h/2]
        area=sum((D.cells[i][4]-D.cells[i][2])*(D.cells[i][5]-D.cells[i][3]) for i in ids)
        groups.append(dict(name=f'bfqg_residual_b{bank}', bank=bank, box_um=box, members=sorted(norm(D.cells[i][6]) for i in ids),
                           cells=257, movable_area_um2=round(area,6), fill=round(area/((box[2]-box[0])*(box[3]-box[1])),6)))
    # Exact all-source flop data/reset reach with worst-case centres anywhere in the proposed regions.
    pairs=set()
    for source,c in D.cells.items():
        if c[0]!='S': continue
        front=list(D.drives[source]);seen=set()
        while front:
            n=front.pop()
            if n in seen:continue
            seen.add(n)
            for s in D.nets[n][2]:
                if s[0]!='i' or s[2]:continue
                if D.kind(s[1])=='S':pairs.add((source,s[1]))
                elif D.kind(s[1]) in {'B','L','K'}:front.extend(D.drives[s[1]])
    def bounds(i):
        if i in moved:return moved[i]
        x,y=g.ctr(D.cells[i]);return[x,y,x,y]
    worst=[]
    for source,capture in pairs:
        aa,bb=bounds(source),bounds(capture)
        distance=max(abs(aa[0]-bb[2]),abs(aa[2]-bb[0]))+max(abs(aa[1]-bb[3]),abs(aa[3]-bb[1]))
        worst.append((distance,source,capture))
    worst.sort(reverse=True)
    if any(v>405 for v,_,_ in worst):raise ValueError('proposed guide envelopes exceed405um')
    model=dict(scope='UNADOPTED PLACEMENT-ONLY PREP; NO CAD/ROUTE/SOURCE/REGISTRATION RELEASE',
        outline_um=[259.2,220.32], groups=groups, moved_FFs=514, added_FFs=0, added_cycles=0,
        public_capture_FFs=len(public), public_capture_overlap=0, all8_bank_first_captures={str(b):256 for b in banks},
        all8_pin_faces={str(b):('W' if b<6 else 'E') for b in banks},
        flop_pair_count=len(pairs), guide_envelope_r2r_max_um=round(worst[0][0],4), guide_envelope_over405=0,
        worst_pair=[norm(D.cells[worst[0][1]][6]),norm(D.cells[worst[0][2]][6])],
        source_inputs_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in [('actual_dump',a.dump),('actual_pins',a.pins),('macro_lef',a.lef),('approved_model',a.model)]},
        target_cells=[dict(name=norm(D.cells[i][6]),box_um=box) for i,box in targets.items()],
        holds=['actual PLACE/r2r/pin/fill/empty/PG/clock', 'native GRT0', 'macro pin-access phase/OBS separate check', 'nine raw reset-registration FAILs remain'])
    (a.out/'guide_model.json').write_text(json.dumps(model,indent=1)+'\n')
    spec=' '.join('{'+row['name']+' {'+' '.join('{'+n+'}' for n in row['members'])+'} '+' '.join(map(str,row['box_um']))+'}' for row in groups)
    (a.out/'guide_spec.tcl').write_text('# Exact actual-connectivity-owned native residual FFs, no public capture members.\nset ::ot_mrg_spec [concat '+spec+']\n')
    # Render actual macro/pin context, old capture positions, and proposed face-local targets.
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(10,8));ax.add_patch(Rectangle((0,0),259.2,220.32,fill=False))
    for b,bs in banks.items():
        c=D.cells[bs['macro']];ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor='#dde2e5',edgecolor='#405060'));ax.text((c[2]+c[4])/2,(c[3]+c[5])/2,f'bank{b} '+('W pins' if b<6 else 'E pins'),ha='center',fontsize=9)
    for row in groups:
        box=row['box_um'];ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,lw=2,edgecolor='green'))
    old=[g.ctr(D.cells[i]) for i in targets];new=[((box[0]+box[2])/2,(box[1]+box[3])/2) for box in targets.values()]
    ax.scatter([x for x,y in old],[y for x,y in old],s=3,color='red',alpha=.25,label='actual old bank6/7 CQ/rp_sel');ax.scatter([x for x,y in new],[y for x,y in new],s=4,color='green',label='proposed native targets (GPL guide, not fixed placement)')
    pins=json.loads(a.pins.read_text());pins=pins.get('pins',[]) if isinstance(pins,dict) else pins
    clocks=[p for p in pins if p.get('bus','').startswith('clk')];ax.scatter([p['x'] for p in clocks],[p['y'] for p in clocks],marker='*',s=70,color='orange',label='all20 actual native clock pins unchanged')
    ax.set(xlim=(-4,263.2),ylim=(-4,224.32),aspect='equal',xlabel='um',ylabel='um',title='BFQG residual bank6/7 guide PREP from actual native connectivity\n514 existing FFs,0public FF overlap; outline/source/clocks unchanged; no new CAD')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.1),fontsize=8);fig.tight_layout();fig.savefig(a.out/'guide_model.png',dpi=150,bbox_inches='tight')
    print('BFQG_GUIDE_PREP',len(targets),'FFs','envelope_r2r',model['guide_envelope_r2r_max_um'],'NO_CAD')


if __name__=='__main__':main()
