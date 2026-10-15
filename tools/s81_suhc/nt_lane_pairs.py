#!/usr/bin/env python3
"""Actual per-bit DL/UL seams, including the boundary between adjacent HC halves."""
import argparse, json, sys, re, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
import pinreg_audit as A
from nt_bottom_pairs import pins


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-view', required=True, type=Path)
    ap.add_argument('--diagnostic', action='store_true')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    layout_path = ROOT / 'physical/s81_die_pins/v20_hc_capture/serial_capture_layout.json'
    layout = json.loads(layout_path.read_text())
    region_h = layout['outline']['h']
    rows = {r['tile']: r for r in layout['rows']}
    entries = {}; hashes = {}
    def load(key, view, cell, row):
        lef = view / f'{cell}.lef'
        h = float(re.search(r'SIZE [\d.]+ BY ([\d.]+)', lef.read_text())[1])
        xy = pins(lef); ybase = region_h - rows[row]['y'] - h
        ins = json.loads((view / 'insertion.json').read_text()); metrics = {}
        for corner in ['tt', 'ff']:
            path = view / f'{cell}_{corner}.lib'; lib = A.parse_lib(path)
            metrics[corner] = A.pin_metrics(lib, A.clock_refs(lib, ins, corner))
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(lef)] = hashlib.sha256(lef.read_bytes()).hexdigest()
        entries[key] = dict(xy=xy, ybase=ybase, metrics=metrics, R=ins['tt']['boundary']['mean'])
    load('fx', args.source_view, 'ot_s81_hc_ctfx_nt', 'ctfx')
    load('fs', ROOT / 'physical/ref_tile/s81hc_ctfsnt_ref/views/ot_s81_hc_ctfs_nt', 'ot_s81_hc_ctfs_nt', 'ctfs')
    joins = []
    # cap -> own south relay, south relay -> next half's cap; scale flows north.
    for stream, count, cases in [
        ('dl', 275, [('fx', 0, 'fs', 0), ('fs', 0, 'fx', -region_h)]),
        ('ul', 33, [('fs', 0, 'fx', 0), ('fx', -region_h, 'fs', 0)])]:
        for a, ay, b, by in cases:
            ea, eb = entries[a], entries[b]
            for bit in range(count):
                pa, pb = f'{stream}_out[{bit}]', f'{stream}_in[{bit}]'
                row = dict(stream=stream, bit=bit, source=a, sink=b, source_half_y=ay, sink_half_y=by)
                try:
                    x0,y0=ea['xy'][pa];x1,y1=eb['xy'][pb]
                    length=abs(x0-x1)+abs(y0+ea['ybase']+ay-y1-eb['ybase']-by)
                    launch=ea['metrics']['tt'][pa]['out'];capture=eb['metrics']['tt'][pb]['inp']
                    lmin=ea['metrics']['ff'][pa]['lmin'];hold=eb['metrics']['ff'][pb]['hold']
                    if None in [launch,capture,lmin,hold]:raise ValueError('missing registered timing arc')
                    setup=833.333-60-(150 if max(ea['R'],eb['R'])>300 else 90)-launch-capture-.76*length
                    hmargin=lmin+.112*length-hold-100
                    row.update(length_um=round(length,4),launch_ps=round(launch,4),capture_ps=round(capture,4),setup_margin_ps=round(setup,4),hold_margin_ps=round(hmargin,4),status='PASS' if setup>=0 and hmargin>=0 and length<=500 else 'FAIL')
                except (KeyError,ValueError) as exc:row.update(status='MISSING',why=str(exc))
                joins.append(row)
    counts={s:sum(r['status']==s for r in joins) for s in ['PASS','FAIL','MISSING']}
    report=dict(schema='opentallas.s81.nt_lane_pairs.v1',qualification_status='UNQUALIFIED_PLACEMENT_ONLY' if args.diagnostic else 'ROUTED_PAIR_SCREEN_ONLY',scope='Four adjacent-half DL/UL seams only; far tail->collector/scalar and clock/reset delivery still separate gates.',region_height_um=region_h,hashes=hashes,counts=counts,joins=joins)
    for name in ['setup_margin_ps','hold_margin_ps']:
        valid=[r for r in joins if name in r];report['worst_'+name]=min(valid,key=lambda r:r[name]) if valid else None
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['joins','hashes']},indent=2))
    return int(bool(counts['FAIL'] or counts['MISSING']))


if __name__=='__main__':sys.exit(main())
