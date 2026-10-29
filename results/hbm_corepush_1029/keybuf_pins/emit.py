#!/usr/bin/env python3
"""Two unsigned keybuf interface proposals; no source/clock/outline/cycle edits."""
from pathlib import Path
import json, copy, math, argparse, hashlib
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
pf=a.plan/'cores/ot_hnx_idxn_keybuf_slice__241.92x293.76__canon.json';old=json.loads(pf.read_text());W,H=241.92,293.76
fixed=[q for q in old if not q['name'].startswith(('key_in[','key_out['))]
assert len(fixed)==34 and len(old)==2232
instances=[dict(type=t,inst=h['inst'],origin_um=h['origin_um'],orient=h.get('orient','R0'),outline_um=h['outline_um']) for t,v in json.loads((a.plan/'die_plan.json').read_text())['partition_types'].items() for h in v.get('hard_cores',[]) if h['module']=='ot_hnx_idxn_keybuf_slice']
assert len(instances)==16
# Track pattern emitted by current gen_core_kit_hbm.make_tracks for M2.
m2ys=sorted({round(row*.270+off,6) for row in range(int(H/.270)+2) for off in (.009,.045,.081,.117,.153,.189,.225,.270) if 8.64<=row*.270+off<=H-8.64})
for mode in ('M4_Win_Eout','W_M4in_M2out'):
    pins=copy.deepcopy(old);groups={b:sorted([q for q in pins if q['name'].startswith(b+'[')],key=lambda q:int(q['name'].split('[')[1][:-1])) for b in ('key_in','key_out')}
    occ=[q['y'] for q in fixed if q['layer']=='M4' and q['x']<1]
    y=41.448
    for q in groups['key_in']:
        while any(abs(y-z)<.096-1e-8 for z in occ):y+=.192
        q.update(layer='M4',x=.096,y=round(y,6));y+=.192
    last=-1
    for i,q in enumerate(groups['key_out']):
        if mode=='M4_Win_Eout':q.update(layer='M4',x=round(W-.096,6),y=round(41.448+i*.192,6))
        else:
            desired=28.305+i*.216
            eligible=[v for v in m2ys if v>=last+.18-1e-8]
            yy=min(eligible,key=lambda v:(abs(v-desired),v));last=yy
            q.update(layer='M2',x=.096,y=yy)
    assert all(q==z for q,z in zip(old,pins) if q['name'] in {x['name'] for x in fixed})
    assert {q['name'] for q in pins}=={q['name'] for q in old}
    peaks={}
    for face,ly,coord in [('W','M4','y'),('E','M4','y'),('W','M2','y')]:
        vals=sorted(q[coord] for q in pins if q['layer']==ly and (q['x']<1 if face=='W' else q['x']>W-1));best=0;j=0
        for k,v in enumerate(vals):
            while vals[j]<v-10+1e-9:j+=1
            best=max(best,k-j+1)
        peaks[face+'/'+ly]=best/10
    assert all(v<=6 for v in peaks.values())
    for q in pins:
        assert 0<=q['x']<=W and 0<=q['y']<=H
        if q['layer']=='M4':assert abs((q['y']-.024)/.048-round((q['y']-.024)/.048))<1e-7
        if q['layer']=='M2':assert q['y'] in m2ys
    assert len({(q['layer'],q['x'],q['y']) for q in pins})==len(pins)
    out=a.out/mode;out.mkdir(parents=True,exist_ok=True);(out/'pins.json').write_text(json.dumps(pins,indent=1)+'\n')
    delta=[dict(name=u['name'],old=u,new=v,manhattan_shift_um=round(abs(u['x']-v['x'])+abs(u['y']-v['y']),6)) for u,v in zip(old,pins) if u!=v]
    report=dict(classification='CANDIDATE ONLY, unsigned physical interface; no source/clock/latency adoption',variant=mode,old_single_W_average_packet_pins_per_um=2198/H,old_single_W_peak_packet_pins_per_um=10.5,pins=len(pins),changed=len(delta),fixed=len(fixed),per_face_layer_10um_peaks=peaks,max_pin_shift_um=max(q['manhattan_shift_um'] for q in delta),clock_reset_straps_byte_unchanged=True,RTL_data_reset_cycles_changed=False,instances=instances,source_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256((out/'pins.json').read_bytes()).hexdigest(),before_PNR=['Actual all16role provider/capture/station impact and model pricing if actual station count changes','Current source/clock/sink placement and macro channel review','G2 lower-layer via/pin-access capacity if M2 variant chosen'],delta=delta)
    (out/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('instances','delta')}))
