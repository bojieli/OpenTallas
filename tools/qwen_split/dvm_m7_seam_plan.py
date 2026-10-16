#!/usr/bin/env python3
"""Emit explicit DVM seam contacts for die-lead review; no route qualification.

The 1170-bit production word is unchanged. Only N/S contacts are candidates
for M7; all interior routing, clocks and PG remain <=M5. Phase variants are
selected from actual placed origins, never fixed by moving a column alone.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

TRACKS = {'M3': (36, 9, 18), 'M5': (48, 12, 24), 'M7': (64, 16, 32)}
# (leaf input, leaf output, head suffix, width). Matches actual NCH=4 RTL.
FIELDS = [('w_v','wo_v','wv',1), ('w_ep','wo_ep','wep',1),
          ('w_off','wo_off','woff',6), ('w_m','wo_m','wm',64),
          ('w_d','wo_d','wd',1024), ('w_ctl','wo_ctl','wctl',72),
          ('c_v','co_v','cv',1), ('c_ep','co_ep','cep',1)]
WIDTH_NM = 64776
EDGE_MARGIN_NM = 576
DEPTH_NM = 384


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pg_m5_intervals():
    # Same top-grid recipe as ref_tile.gen_pdn: core starts at 2.16 um,
    # then .300 offset; VDD/VSS .120 wide, .072 spacing, pitch5.4.
    return [(2160+300+5400*k+192*j, 2160+420+5400*k+192*j)
            for k in range(13) for j in range(2)
            if 2160+300+5400*k+192*j < WIDTH_NM-2160]


def available(phase, layers):
    slots = []
    for layer in layers:
        pitch, offset, width = TRACKS[layer]
        local = (offset-(phase if layer == 'M7' else 0)) % pitch
        for x in range(local, WIDTH_NM, 2*pitch):
            if x-width//2 < EDGE_MARGIN_NM or x+width//2 > WIDTH_NM-EDGE_MARGIN_NM:
                continue
            # Reserve M5 PG and M5 landing space under every M7 contact.
            # This is an analytic reservation; expanded routed vias are still mandatory.
            if layer in ('M5','M7') and any(x+48 > a and x-48 < b for a,b in pg_m5_intervals()):
                continue
            slots.append((x,layer,width))
    return sorted(slots)


def plan(phase):
    slots = available(phase, TRACKS)
    count = sum(f[3] for f in FIELDS)
    # Evenly occupy the complete available face, preserving logical bit order.
    chosen = [slots[((2*i+1)*len(slots))//(2*count)] for i in range(count)]
    assert len(set(chosen)) == count
    ports = []
    i = 0
    for inp,out,suffix,n in FIELDS:
        for bit in range(n):
            x,layer,width = chosen[i]
            names = {'leaf_S':inp, 'leaf_N':out, 'head_N':'cn_'+suffix, 'head_S':'cs_'+suffix}
            names = {k:v+(f'[{bit}]' if n>1 else '') for k,v in names.items()}
            ports.append(dict(index=i, names=names, layer=layer, x_nm=x,
                              rect_x_nm=[x-width//2,x+width//2], edge_depth_nm=DEPTH_NM))
            i += 1
    return dict(origin_x_mod64_nm=phase, seam_bits=count,
                available_slots=len(slots), cut=count/len(slots),
                baseline_M3_M5_slots=len(available(phase,('M3','M5'))),
                baseline_cut=count/len(available(phase,('M3','M5'))),
                contacts_by_layer=dict(collections.Counter(p['layer'] for p in ports)), ports=ports)


def audit(p, origins):
    errors=[]
    if len(p['ports']) != 1170 or len({x['index'] for x in p['ports']}) != 1170:
        errors.append('Missing or duplicate production word bit')
    expected=[]
    for inp,out,suffix,n in FIELDS:
        for bit in range(n):
            expected.append({k:v+(f'[{bit}]' if n>1 else '') for k,v in
                             {'leaf_S':inp,'leaf_N':out,'head_N':'cn_'+suffix,'head_S':'cs_'+suffix}.items()})
    for pin in p['ports']:
        if pin['index'] >= len(expected) or pin['names'] != expected[pin['index']]:
            errors.append('Contact name/bit does not match unchanged production seam')
        if pin['edge_depth_nm'] > DEPTH_NM or pin['edge_depth_nm'] <= 0:
            errors.append('Contact exceeds bounded edge strip')
    for origin in origins:
        for pin in p['ports']:
            pitch,offset,width=TRACKS[pin['layer']]
            if (origin+pin['x_nm']-offset)%pitch:
                errors.append(f'Track mismatch origin={origin} bit={pin["index"]}')
                break
    for layer in TRACKS:
        xs=sorted(x['x_nm'] for x in p['ports'] if x['layer']==layer)
        if any(b-a < TRACKS[layer][0]*2 for a,b in zip(xs,xs[1:])):
            errors.append('Two-track spacing violated on '+layer)
    if p['cut'] > .60:
        errors.append('Face cut exceeds .60 after analytic PG reservation')
    return errors


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--homes',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();record=json.loads(Path(a.homes).read_text());h=record['homes']; out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    columns={k:v for k,v in h.items() if v['m'] in ('qfd_xcol_e','qfd_xcol_w')}
    if len(columns)!=48:raise ValueError('Expected actual48 full columns')
    if any(v['o']!='R0' or round(v['w']*1000)!=WIDTH_NM for v in columns.values()):
        raise ValueError('Only the actual R0/64.776um column frames are covered')
    phases=collections.defaultdict(list)
    for n,v in columns.items(): phases[round(v['x']*1000)%64].append(n)
    plans={str(k):plan(k) for k in sorted(phases)}
    errors=[]
    for k,p in plans.items():errors+=audit(p,[round(columns[n]['x']*1000) for n in phases[int(k)]])
    for k,p in plans.items():
        (out/f'seam_phase{k}.json').write_text(json.dumps(p,indent=2)+'\n')
    # The deployed slot uses two phases; explicitly demonstrate why aliasing
    # either one across the other actual phase fails native track placement.
    rejected_phase_aliases={f'{a}_as_{b}':bool(audit(plans[str(a)],[next(x for x in range(0,8640,2160) if x%64==b)]))
                            for a in phases for b in phases if a!=b}
    summary=dict(schema='opentallas.qwen-dvm-m7-seam-candidate.v1', qualified=False,
       homes_fixture_sha256=digest(a.homes), source_full_homes_sha256=record.get('source_full_homes_sha256',digest(a.homes)), column_count=len(columns), width_um=WIDTH_NM/1000,
       source_rtl_sha256={p:digest(p) for p in ['rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv']},
       normal_cycle_change=0, workload_bits_per_seam=1170,
       phases={str(k):v for k,v in sorted(phases.items())},
       variants={k:{kk:vv for kk,vv in p.items() if kk!='ports'} for k,p in plans.items()},
       track_and_spacing_errors=errors, observed_wrong_phase_rejections=rejected_phase_aliases,
       interior_signal_and_pg_cap='M5', proposed_contact_cap='M7',
       grant_scope='Only the exact named M7 contacts in seam_phase*.json, N/S .384um edge strips; M6/M7 vias must be expanded and contained in corresponding source-bound landing boxes; no blanket cap/OBS/PG change',
       analytic_M5_pg_reservation_nm=pg_m5_intervals(),
       open=['die-lead expanded actual M5-to-M8 and M7-to-M8 via/PG audit at all four2.16um y phases',
             'actual M5-to-M7 signal via dimensions/clearance and routed DEF audit',
             'exact source-bound shared-flow M7 contact grant support',
             'independently hardened head/control and eight real leaves with separate native clock views',
             'head W/E full connection pin plan and <=500um neighbor leg',
             'TTsetup/FFhold/DRC0 and native220/190/80 per child; aggregate GRT/STA',
             'one-edge leaf input/output shared capture register must satisfy both opposite-face native bounds'],
       interpretation='Analytic pin capacity and track candidate only, no physical or whole-column qualification')
    (out/'candidate.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['phases','source_rtl_sha256','analytic_M5_pg_reservation_nm']},indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
