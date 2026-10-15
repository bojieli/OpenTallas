#!/usr/bin/env python3
"""Exact LEF-pin geometry and source-Liberty TT budget screen of nine-root bank.

A visual/model screen, not routed RC/hold/PG or die qualification. Raw memory
bus arcs apply uniformly to their bits; only the analysis parser normalizes
bus headers, never the Liberty files consumed by physical implementation.
"""
import argparse, hashlib, json, re, sys, tempfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C
import pinreg_audit as P

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kit',default='physical/ref_tile/qvm_bank_entries_native');ap.add_argument('--out',required=True);a=ap.parse_args()
    fp=json.loads((ROOT/a.kit/'floorplan.json').read_text());out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True)
    blocks={b['inst']:b for b in fp['blocks']};cache={};hashes={str(Path(a.kit)/'floorplan.json'):hashlib.sha256((ROOT/a.kit/'floorplan.json').read_bytes()).hexdigest()}
    for b in blocks.values():
        if b['orient'] not in ('R0','MY'):raise ValueError('Only actual R0/MY transforms supported')
        view=ROOT/b['view'];name=b['master']
        if name in cache:continue
        lef=view/(name+'.lef');lib=view/(name+'_tt.lib');txt=lib.read_text()
        # Liberty bus timing applies to each declared member. Keep source bytes immutable.
        normalized=re.sub(r'(?m)^(\s*)bus\s*\(',r'\1pin (',txt)
        with tempfile.NamedTemporaryFile(mode='w',suffix='.lib') as f:
            f.write(normalized);f.flush();parsed=P.parse_lib(f.name)
        ins=json.loads((view/'insertion.json').read_text()) if (view/'insertion.json').exists() else None
        refs=P.clock_refs(parsed,ins,'tt');metrics=P.pin_metrics(parsed,refs)
        cache[name]=(C.parse_lef(lef.read_text()),metrics)
        hashes[str(lef.relative_to(ROOT))]=hashlib.sha256(lef.read_bytes()).hexdigest()
        hashes[str(lib.relative_to(ROOT))]=hashlib.sha256(lib.read_bytes()).hexdigest()
    def point(inst,pin):
        b=blocks[inst];m=cache[b['master']][0]
        rects=m['pins'][pin]['rects'];r=rects[0]
        px=(r[1]+r[3])/2
        if b['orient']=='MY':px=b['w']-px
        return [b['x']+px,b['y']+(r[2]+r[4])/2]
    def metric(inst,pin,key):
        b=blocks[inst];m=cache[b['master']][1];p=m.get(pin,m.get(pin.split('[')[0]))
        return p.get(key) if p else None
    paths=[]
    def add(src,sp,dst,dp,group):
        x=point(src,sp);y=point(dst,dp);d=abs(x[0]-y[0])+abs(x[1]-y[1]);o=metric(src,sp,'out');s=metric(dst,dp,'inp')
        paths.append(dict(source=src,source_pin=sp,target=dst,target_pin=dp,group=group,source_xy_um=x,target_xy_um=y,length_um=round(d,4),launch_ps=o,capture_ps=s,tt_setup_screen_margin_ps=round(683.333-o-s-.76*d,4) if o is not None and s is not None else None))
    for half in ['lo','hi']:
        for j in range(256):
            add('u_in_'+half,f'q[{j}]','u_'+half,f'wd_in[{j}]','registered input → SRAM')
            add('u_'+half,f'rd_out[{j}]','u_cap_'+half,f'd[{j}]','SRAM → registered capture')
            add('u_cap_'+half,f'q[{j}]','u_out_'+half,f'd[{j}]','capture → output')
            add('u_ctrl',f'p_wm[{j//32+(8 if half=="hi" else 0)}]','u_'+half,f'w_mask_in[{j}]','write-mask distribution')
        for j in range(8):
            add('u_ctrl',f'p_ra[{j}]','u_'+half,f'r_addr_in[{j}]','read-address distribution')
            add('u_ctrl',f'p_wl[{j}]','u_'+half,f'w_addr_in[{j}]','write-address distribution')
        add('u_ctrl','p_re','u_'+half,'r_ce_in','read-enable distribution')
        add('u_ctrl','p_we','u_'+half,'w_ce_in','write-enable distribution')
    assert len(paths)==2084
    known=[p for p in paths if p['tt_setup_screen_margin_ps'] is not None]
    summary=dict(schema='opentallas.qwen-nine-root-bank-pin-screen.v1',qualified=False,
        scope='actual2084 internal pin legs at fixed candidate placements with actual R0/MY transforms; no parent IO, clock routing, routedRC, FFhold or PG qualification',
        pins_resolved=len(paths),missing_timing_arcs=len(paths)-len(known),max_length_um=max(p['length_um'] for p in paths),over500=sum(p['length_um']>500 for p in paths),
        tt_setup_screen_min_ps=min(p['tt_setup_screen_margin_ps'] for p in known),negative_tt_screen=sum(p['tt_setup_screen_margin_ps']<0 for p in known),
        setup_budget_ps=683.333,wire_ps_per_um=.76,raw_macro_reference='actualLiberty clock pin; no invented insertion',
        physical_assumption='R0/MY rectilinear distance only; metal congestion/detours/parasitics and load/slew remain unmeasured',source_sha256=hashes,paths=paths)
    (out/'pin_screen.json').write_text(json.dumps(summary,indent=2)+'\n')
    w,h=fp['die'][2:];scale=2
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="760" viewBox="-10 -35 {w+20} {h+65}">','<rect x="-10" y="-35" width="100%" height="100%" fill="white"/>','<style>text{font-family:Arial;font-size:6px} .small{font-size:4px}</style>',f'<text x="0" y="-22">Nine-root Qwen bank candidate — actual LEF dimensions and pin endpoints</text>',f'<text x="0" y="-12" class="small">2084 internal bit legs; max {summary["max_length_um"]:.1f} µm; TT model margin {summary["tt_setup_screen_min_ps"]:.1f} ps. Parent RC/hold/PG and adoption OPEN.</text>']
    for b in blocks.values():
        y=h-b['y']-b['h'];color='#d2e9fa' if b['kind']=='macro' else '#e3eed8'
        svg.append(f'<rect x="{b["x"]}" y="{y}" width="{b["w"]}" height="{b["h"]}" fill="{color}" stroke="#333" stroke-width=".35"/>')
        label=b['inst'].replace('u_','');svg.append(f'<text x="{b["x"]+1}" y="{y+b["h"]/2}" class="small">{label}</text>')
    groups=defaultdict(list)
    for p in paths:groups[(p['source'],p['target'],p['group'])].append(p)
    colors=['#236aa0','#c56620','#7b4ba0','#888']
    for gi,((src,dst,g),pp) in enumerate(groups.items()):
        worst=max(pp,key=lambda x:x['length_um']);x,y=worst['source_xy_um'];xx,yy=worst['target_xy_um'];color=colors[gi%len(colors)]
        svg.append(f'<path d="M{x} {h-y} H{xx} V{h-yy}" fill="none" stroke="{color}" stroke-width=".5"/>')
        unique=len({p['source_pin'] for p in pp})
        label={'registered input → SRAM':'WD256b','SRAM → registered capture':'RD256b','capture → output':'256b','write-mask distribution':f'mask{unique}b/{len(pp)}loads','read-address distribution':'RA8b','write-address distribution':'WA8b','read-enable distribution':'RE1b','write-enable distribution':'WE1b'}[g]
        svg.append(f'<text x="{(x+xx)/2}" y="{h-(y+yy)/2}" class="small" fill="{color}">{label} →</text>')
    svg+=['<text x="0" y="'+str(h+15)+'" class="small">To scale. Each line is the longest actual pin pair in its labelled group; full per-bit list is in pin_screen.json.</text>','</svg>']
    (out/'candidate.svg').write_text('\n'.join(svg)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['paths','source_sha256']},indent=2))
if __name__=='__main__':main()
