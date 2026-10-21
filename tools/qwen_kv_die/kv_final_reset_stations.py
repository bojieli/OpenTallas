#!/usr/bin/env python3
"""Opt-in actual reset transport and two local captures after final lane placement.

Default target is the real long PLL enable wire. Explicit additional scalar
en/rs endpoints may be selected. Every endpoint retains its original producer;
sites are recomputed from the current case, never imported from an old plan.
This generator emits an edge/calendar ledger, not a cold-boot qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

import kv_reset_site_trial as SITE

INST = re.compile(r'^(\s+)(\w+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')


def bit(net):
    net = net.strip()
    return net+'[0]' if re.fullmatch(r'\w+',net) else net


def geometry(case):
    """Actual final instance connections and all pin-rectangle centres, in um."""
    text = (case/'die.v').read_text()
    insts = {}
    for line in text.splitlines():
        m = INST.match(line)
        if m:
            insts[m[3]] = (m[2],dict(CONN.findall(m[4])))
    poses = {n:(float(x),float(y),o) for n,x,y,o in re.findall(
        r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', (case/'place.tcl').read_text())}
    sizes, pins = {}, {}
    master = pin = None
    for line in (case/'elements.lef').read_text().splitlines():
        s = line.strip().split()
        if not s:
            continue
        if s[0] == 'MACRO': master = s[1]
        elif s[0] == 'SIZE': sizes[master] = float(s[1]),float(s[3])
        elif s[0] == 'PIN': pin = s[1]
        elif s[0] == 'RECT' and pin:
            pins.setdefault((master,pin),[]).append(((float(s[1])+float(s[3]))/2,(float(s[2])+float(s[4]))/2))
        elif s[0] == 'END' and len(s)>1 and s[1] == pin: pin = None

    def points(name, port):
        mst,_ = insts[name]
        x,y,o = poses[name]
        w,h = sizes[mst]
        if o not in ('R0','MY','MX','R180'):
            raise ValueError('unsupported pin orientation '+name+':'+o)
        q = pins.get((mst,port), pins.get((mst,port+'[0]')))
        if not q: raise ValueError('missing actual pin geometry '+name+'/'+port)
        return [(x+(w-px if o in ('MY','R180') else px),y+(h-py if o in ('MX','R180') else py)) for px,py in q]
    return text,insts,points


def endpoint(case, target):
    _, insts, points = geometry(case)
    name, port = target.rsplit('/',1)
    mst, cs = insts[name]
    if not ((port == 'en' and mst.startswith(('qkd_rlysh0_','qkd_landsh0_'))) or
            (port == 'rs' and mst.startswith(('qkd_landsh_','qkd_landsh0_')))):
        raise ValueError('target must be an actual closed forwarded-lane en/rs input: '+target)
    reset = bit(cs[port])
    producers = [(n,m,c) for n,(m,c) in insts.items()
                 if m == 'qkd_rlys_1' and bit(c.get('b','')) == reset]
    if len(producers) != 1:
        raise ValueError('original reset producer is not one actual qkd_rlys_1: '+target)
    src,_,scs = producers[0]
    src_clock = scs['ck']
    dst_clock = cs['ck_s'] if port == 'en' and mst.startswith('qkd_landsh0_') else cs['ck']
    pairs = [(abs(s[0]-d[0])+abs(s[1]-d[1]),s,d) for s in points(src,'b') for d in points(name,port)]
    reach,s,d = max(pairs)
    return dict(id=src+'/b->'+target,master=mst,witness_net=cs[port],
                pts=[s,d],max_um=reach,consumer_clock=dst_clock,transport_clock=src_clock,
                producer_identity=dict(instance=src,port='b',net=reset,clock=src_clock))


def restrap(case, lanes_path, changes):
    """Price source and receiver reset edges in the existing canonical G-R0 basis."""
    doc = json.loads(lanes_path.read_text())
    text = (case/'die.v').read_text()
    lines = text.splitlines(keepends=True)
    indices = {m[3]:i for i,line in enumerate(lines) if (m:=INST.match(line))}
    priced = []
    for lane in doc['lanes']:
        stations = lane['stations']
        en = changes.get(stations[0]+'/en')
        rs = changes.get(stations[-1]+'/rs')
        if not en and not rs: continue
        if lane.get('cal_basis') != 'G-R0+h0' or lane.get('h0') != 1:
            raise ValueError('lane must carry the actual ALL-FIRST epoch before reset transport')
        delta_g = en['added_edges'] if en else 0
        delta_r0 = rs['added_edges'] if rs else 0
        reset_cal = int(lane.get('reset_cal',0))+delta_g-delta_r0
        total_cal = reset_cal+1
        old_k = lane['K']
        k = (int(lane.get('E',lane['E_planned']))+total_cal)%8 or 8
        li = indices[stations[-1]]
        cs = dict(CONN.findall(INST.match(lines[li])[4]))
        hi,lo = cs['tie_hi'],cs['tie_lo']
        for j in range(3):
            old = '.k'+str(j)+'('+cs['k'+str(j)]+')'
            lines[li] = lines[li].replace(old,'.k'+str(j)+'('+(hi if (k>>j)&1 else lo)+')')
        lane.update(K=k,reset_cal=reset_cal,cal=total_cal,
                    reset_distribution=dict(source_added_edges=delta_g,receiver_added_edges=delta_r0),
                    age_contract='KVR-FWDAGE: source-bound reset G-R0; source-to-landing-output age E+1; post stages unchanged')
        if en: lane['en'] = en['new_net']
        if rs: lane['rs'] = rs['new_net']
        priced.append(dict(landing=stations[-1],source_added_edges=delta_g,receiver_added_edges=delta_r0,
                           reset_cal=reset_cal,old_K=old_k,new_K=k,steady_data_age_delta=0))
    lanes_path.write_text(json.dumps(doc,indent=1)+'\n')
    (case/'die.v').write_text(''.join(lines))
    return priced


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--endpoints',default=os.environ.get('OT_KV_FINAL_RESET_PORTS','rly_pinfix_pll_lock_0__s0/en'))
    a = ap.parse_args()
    case = a.run/'case_kv'
    root = a.run/'final_reset_stations'
    if root.exists(): raise ValueError('refuse to overwrite an existing reset-distribution generation')
    work = root/'case'
    work.mkdir(parents=True)
    for name in ('die.v','place.tcl','elements.lef','manifest.json'):
        shutil.copy2(case/name,work/name)
    lanes = root/'fwd_lanes.json'
    shutil.copy2(a.run/'fwd_lanes.json',lanes)
    before = {n:hashlib.sha256((case/n).read_bytes()).hexdigest() for n in ('die.v','place.tcl','elements.lef','manifest.json')}
    changes = {}
    for index,target in enumerate(dict.fromkeys(x.strip() for x in a.endpoints.split(',') if x.strip())):
        row = endpoint(work,target)
        if row['max_um'] <= 405: continue
        inventory = root/f'input_{index}.json'
        inventory.write_text(json.dumps(dict(source_sha256={n:hashlib.sha256((work/n).read_bytes()).hexdigest() for n in before},long_pairs=[row])))
        report_path = root/f'stations_{index}.json'
        prefix = root/f'generated_{index}'
        rc = SITE.main(['--case',str(work),'--inventory',str(inventory),'--endpoint',target,
                        '--out',str(report_path),'--emit-source-prefix',str(prefix),
                        '--name-prefix','rly_finalrst_'+str(index)])
        if rc: raise ValueError('no legal current-geometry reset station path: '+target)
        report = json.loads(report_path.read_text())
        for n in ('die.v','place.tcl'): shutil.copy2(Path(str(prefix)+'.'+n),work/n)
        changes[target] = dict(original_producer=row['producer_identity'],
            original_max_um=row['max_um'],source_clock=row['transport_clock'],receiver_clock=row['consumer_clock'],
            added_edges=report['added_edges'],transport_edges=report['transport_edges'],capture_edges=2,
            new_net='n_rly_finalrst_'+str(index)+'_capture2[0]',
            max_actual_pin_span_um=report['max_actual_pin_span_um'],
            clock_phase_status='same-root relative cycles' if bit(row['transport_clock'])==bit(row['consumer_clock']) else 'regional phase bound required')
    pricing = restrap(work,lanes,changes)
    extra = max((c['added_edges'] for c in changes.values()),default=0)
    ledger = dict(schema='opentallas.kv_final_reset_stations.v1',enabled=True,
        source_sha256=before,endpoints=changes,lanes=pricing,
        max_added_reset_edges=extra,
        minimum_existing_required_hold=325,known_h273b_hold=273,
        requested_hold_env=int(os.environ.get('OT_KV_RST_HOLD','273')),
        conservative_required_hold=325+extra,hold_shortfall_vs_h273b=325+extra-273,
        boot_first_use_requirement='each affected first-use margin must cover its added reset release edges; absolute production source dates not supplied',
        first_use_profiles='PENDING actual source/clock/reset-basis profiles',
        qualification='STRUCTURAL_SOURCE_ONLY_NOT_COLD_BOOT_OR_RELEASE_QUALIFIED')
    manifest = json.loads((work/'manifest.json').read_text())
    station_count = sum(c['added_edges'] for c in changes.values())
    if isinstance(manifest.get('instances'),int): manifest['instances'] += station_count
    manifest['final_reset_stations'] = dict(added_cells=station_count,calendar='final_reset_stations/calendar.json')
    (work/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
    ledger['output_stage_sha256'] = {n:hashlib.sha256((work/n).read_bytes()).hexdigest()
                                    for n in ('die.v','place.tcl','manifest.json')}
    (root/'calendar.json').write_text(json.dumps(ledger,indent=2)+'\n')
    for n in ('die.v','place.tcl','manifest.json'):
        shutil.copy2(case/n,root/(n+'.original'))
        shutil.copy2(work/n,case/n)
    shutil.copy2(a.run/'fwd_lanes.json',root/'fwd_lanes.original.json')
    shutil.copy2(lanes,a.run/'fwd_lanes.json')
    print(json.dumps(dict(endpoints=len(changes),max_added_reset_edges=extra,
                         conservative_required_hold=325+extra,calendar=str(root/'calendar.json'))))


if __name__ == '__main__': main()
