#!/usr/bin/env python3
"""Opt-in measured per-tap die stub compensation; no tile or data-cycle changes.

Append a delay chain at each existing routed tap endpoint, keeping its long stub.
The original stub remains the mesh load and drives its original long wire. Match TT and FF measured tap arrivals jointly,
including the declared per-corner core insertion. Reroute and remeasure required.
"""
import argparse
import itertools
import gzip
import re
import json
from pathlib import Path
import die_clock_mesh as M


interp = M.interp
TRIM_CELLS = ["BUFx24_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx12_ASAP7_75t_R",
              "BUFx10_ASAP7_75t_R", "BUFx8_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx5_ASAP7_75t_R", "BUFx4f_ASAP7_75t_R",
              "BUFx4_ASAP7_75t_R", "BUFx3_ASAP7_75t_R", "BUFx2_ASAP7_75t_R"]   # 24.7-37.3 ps each into a BUFx24 pin (TT)

def lib_cells(corner, libdir, names=TRIM_CELLS):
    """{cell: (slews, loads, rise delay rows, rise transition rows, A rise cap)} from the INVBUF liberty."""
    f = Path(libdir) / f"asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    txt = gzip.open(f, "rt").read()
    out = {}
    for nm in names:
        i = txt.index(f"cell ({nm})")
        j = txt.find("cell (", i + 10)
        blk = txt[i:j if j > 0 else len(txt)]
        tab = {}
        for key in ("cell_rise", "rise_transition"):
            m = re.search(key + r" \(\w+\) \{\s*index_1 \(\"([^\"]+)\"\);\s*index_2 \(\"([^\"]+)\"\);\s*values \((.*?)\);",
                          blk, re.S)
            tab[key] = ([float(v) for v in m.group(1).split(",")], [float(v) for v in m.group(2).split(",")],
                        [[float(v) for v in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(3))])
        cap = float(re.search(r"pin \(A\).*?rise_capacitance : ([\d.]+)", blk, re.S).group(1))
        out[nm] = (tab, cap)
    return out

def _bilin(t, slew, load):
    sl, ld, rows = t
    return interp(sl, [interp(ld, r, load) for r in rows], slew)

def chain_delay(L, chain, slew, final_load, wire_ff=4.0):
    d = 0.0
    for k, c in enumerate(chain):
        load = (L[chain[k + 1]][1] if k + 1 < len(chain) else final_load) + wire_ff
        d += _bilin(L[c][0]["cell_rise"], slew, load) + 2.0
        slew = _bilin(L[c][0]["rise_transition"], slew, load)
    return d, slew

def taps(path):
    return {f[1]: tuple(map(float, f[2:5])) for line in path.read_text().splitlines() if (f := line.split()) and f[0] == 'T'}


def run(a):
    src, out = Path(a.dir), Path(a.out)
    if src.resolve() == out.resolve() or out.exists():
        raise ValueError('output must be a fresh directory distinct from source')
    plan = M.S.Plan(M.S.load(a.plan))
    mesh = json.loads((src/'mesh.json').read_text())
    cells = json.loads((src/'place.json').read_text())
    data = json.loads((src/'nets.json').read_text())
    early = M.DC.plan_tap_early(plan)
    arr = {c: taps(src/f'taps_{c}.txt') for c in ('TT','FF')}
    libs = {c: lib_cells(c, a.libdir) for c in ('TT','FF')}
    mesh_rc = {c: json.loads((src/f'mesh_{c}.json').read_text()) for c in ('TT','FF')}
    calibration = {c:{} for c in ('TT','FF')}
    if a.calibration:
        caldir=Path(a.calibration)
        previous=json.loads((caldir/'mesh.json').read_text())
        declared=previous.get('meta',{}).get('leaftrim',{}).get('source')
        if declared is None or Path(declared).resolve()!=src.resolve():
            raise ValueError('calibration candidate must name this exact source baseline')
        predicted={t['port']:t['leaftrim'] for t in previous['taps']}
        if set(predicted)!={t['port'] for t in mesh['taps']}:
            raise ValueError('calibration and source tap inventories differ')
        for c in ('TT','FF'):
            measured=taps(caldir/f'taps_{c}.txt')
            for t in mesh['taps']:
                port=t['port']
                calibration[c][port]=measured[port][0]-arr[c][port][0]-predicted[port][f'{c}_added_ps']

    options = [M.BUF, 'BUFx12f_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R', 'BUFx2_ASAP7_75t_R']
    chains = [[M.BUF]+list(comb)+[M.BUF] for n in range(a.max_cells-1) for comb in itertools.combinations_with_replacement(options,n)]
    # Preserve the original stub and its routed load. The new first cell replaces
    # exactly its mesh capacitance, and the final new cell drives the original.
    table = []
    for ch in chains:
        ds = {c: chain_delay(libs[c],ch,40.0,libs[c][M.BUF][1],wire_ff=4.0)[0] for c in ('TT','FF')}
        table.append((ch,ds))
    off = lambda t,c: early.get((t['part'],t['tap']),{}).get(c,t.get('early_ps',0.0))
    targets = {c:max(arr[c][t['port']][0]+off(t,c) for t in mesh['taps']) + a.reserve_ps*(1 if c=='TT' else .8) for c in ('TT','FF')}
    # A shared physical delay chain has its library TT/FF ratio. Choose the
    # global FF target from that ratio, rather than independently maximising
    # each corner (which can demand an impossible added-delay ratio).
    import statistics
    probe=[M.BUF]*4
    ratio=chain_delay(libs['FF'],probe,40.0,libs['FF'][M.BUF][1],wire_ff=4.0)[0]/chain_delay(libs['TT'],probe,40.0,libs['TT'][M.BUF][1],wire_ff=4.0)[0]
    offsets=[arr['FF'][t['port']][0]+off(t,'FF')-ratio*(arr['TT'][t['port']][0]+off(t,'TT')) for t in mesh['taps']]
    targets['FF']=ratio*targets['TT']+statistics.median(offsets)
    keeps = M.DC.KeepIndex(M.DC.keepouts(plan),die=(float(plan.W),float(plan.H)))
    # Reserve conservative BUFx24 footprints for all existing and new cells.
    occupied = {}
    def reserve(x,y):
        key=(int(x//10),int(y//10));occupied.setdefault(key,[]).append((x,y))
    for v in cells.values():reserve(v['x'],v['y'])
    def legal(q):
        if M.hitf(keeps,q):return False
        x,y=q[0]-M.BUF_W/2,q[1]-M.ROW_Y/2
        if not (0<=x<float(plan.W)-M.BUF_W and 0<=y<float(plan.H)-M.ROW_Y):return False
        ix,iy=int(x//10),int(y//10)
        return all(abs(x-xx)>=M.BUF_W+M.SITE_X or abs(y-yy)>=M.ROW_Y for bx in range(ix-1,ix+2) for by in range(iy-1,iy+2) for xx,yy in occupied.get((bx,by),[]))
    residuals=[]
    for ti,t in enumerate(mesh['taps']):
        old=t['stub']; need={c:targets[c]-arr[c][t['port']][0]-off(t,c)-calibration[c].get(t['port'],0.0) for c in ('TT','FF')}
        # Small candidate set, then evaluate each at the actual mesh input slew.
        shortlist=sorted(table,key=lambda x:max(abs(x[1][c]-need[c]) for c in ('TT','FF')))[:24]
        actual=[]
        for ch,_ in shortlist:
            ds={c:chain_delay(libs[c],ch,arr[c][t['port']][2],3.0,wire_ff=4.0)[0] for c in ('TT','FF')}
            actual.append((max(abs(ds[c]-need[c]) for c in ('TT','FF')),len(ch),ch,ds))
        err,_,ch,ds=min(actual)
        base={'x':t['xy'][0]-M.BUF_W/2,'y':t['xy'][1]-M.ROW_Y/2}; names=[]
        for k,lib in enumerate(ch):
            # Row-aligned local island; never move a cell into a hard keep-out.
            q=(base['x']+M.BUF_W/2+(k+1)*M.BUF_W*1.12,base['y']+M.ROW_Y/2+2*M.ROW_Y)
            if not legal(q):
                q=next(((base['x']+M.BUF_W/2+dx*M.BUF_W*1.12,base['y']+M.ROW_Y/2+dy*M.ROW_Y*2)
                        for r in range(1,30) for dx in range(-r,r+1) for dy in (-r,r)
                        if legal((base['x']+M.BUF_W/2+dx*M.BUF_W*1.12,base['y']+M.ROW_Y/2+dy*M.ROW_Y*2))),None)
            if q is None: raise ValueError(f'no legal leaf trim island at {t["port"]}')
            nm=f'ckm_leaftrim_{ti}_{k}'
            cells[nm]={'x':M.snap(q[0]-M.BUF_W/2,M.SITE_X),'y':M.snap(q[1]-M.ROW_Y/2,M.ROW_Y),'kind':'stub_trim','lib':lib}
            reserve(cells[nm]['x'],cells[nm]['y'])
            names.append(nm)
        original=next(n for n in data['nets'] if 'port:'+t['port'] in n['loads'])
        original['name']=f'ckm_w_leaftrim_{ti}_input'
        original['loads']=[names[0] if x=='port:'+t['port'] else x for x in original['loads']]
        for u,v in zip(names,names[1:]+['port:'+t['port']]):
            data['nets'].append({'name':f'ckm_w_leaftrim_{ti}_{u}','drv':u,'loads':[v],'level':99})
        t['leaftrim']={'cells':names,'TT_added_ps':round(ds['TT'],3),'FF_added_ps':round(ds['FF'],3),'fit_error_ps':round(err,3),'calibration_ps':{c:round(calibration[c].get(t['port'],0.0),3) for c in ('TT','FF')}}
        residuals.append(err)
    mesh['meta']['cells']=len(cells)
    mesh['meta']['leaftrim']={'source':str(src),'target_ps':targets,'max_prediction_error_ps':round(max(residuals),3),'added_cells':sum(len(t['leaftrim']['cells']) for t in mesh['taps']),'calibration':a.calibration,'qualification':'NOT RUN: requires reviewed physical reroute and TT/FF skew gate'}
    out.mkdir(parents=True)
    ren=M.write_verilog(cells,data['nets'],data['ports'],out/'ctree.v')
    for n in data['nets']:n['name']=ren.get(n['name'],n['name'])
    for name,obj in [('mesh.json',mesh),('place.json',cells),('nets.json',data)]: (out/name).write_text(json.dumps(obj)+'\n')
    print(json.dumps(mesh['meta']['leaftrim'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dir');p.add_argument('--out',required=True);p.add_argument('--plan',required=True)
    p.add_argument('--calibration',help='prior routed endpoint-trim candidate from the same baseline');p.add_argument('--libdir',required=True);p.add_argument('--reserve-ps',type=float,default=65.0);p.add_argument('--max-cells',type=int,default=14)
    run(p.parse_args())
