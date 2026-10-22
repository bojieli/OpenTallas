#!/usr/bin/env python3
"""S81 HEAD H10 plan (STW-S81-HEAD 10-21): structural repair of the H4 die-top wiring failure.

H4 terminal (results/arch/s81_head_1021/h4_tail_terminal): GRT overflow 1,572,822, 31,574 slew violators, fclk 41/2813.
Classified cause (this script's facts.h10.diagnosis): H2 shrank the 1512 x 2592 ctl reserve to a 1036.8-um square glue,
so ALL 94 ctl links (25,579 unit + 2,728 spine bits) land on a 4.1-mm perimeter: E face 14,904 bits / 1036.8 um =
14.4 pins/um (W 9.1).  Every reported congestion gcell is at the ctl E face (x 8.5..10 mm, y 10..11 mm); the plan cut
window at the E face is 0.80 (limit 0.55).  That is a star-hub funnel, not die-wide capacity (die usage 2-4 %/layer).

H10 = H4 contents (H3 regional lep 2592^2, exact CLOSED SPR m4 R0 bodies, CLOSED M7 dsfd_mtp_seq peer) with:
  1. ctl glue outline enlarged so every ctl face is <= ~4 pins/um (MAIN 2160 x 3888: E 3.83, W 2.41 pins/um); the
     ctl reserve (band) grows with it and the die grows in y (reticle 26 x 33 mm allows it; owner 10-21 "add relays /
     enlarge floorplan").  Pins keep their fractional face order (rvcase scales the open glue kit pin plan).
  2. wider ctl band streets (ch_ctl) so the 13 lanes' 6 x 276-b core links reach the tall faces without a funnel.
  3. lane SerDes in their lane's clock region (group cl_<lane>): the 26 abutted lane <-> SerDes links stop being
     unlanded region crossings (H4 gen_safety C1 30/184) and the die-wide 'edge0' SerDes root is gone; lep SerDes
     lk_WN0..2 each get their own region (their links are stationed + landed); lk_WN3 (abutted to the lep) is clocked
     by the lep pair-B root it exchanges data with (lep tx3/rx3 ports are ck_B, hd_bind instance_clock_ports).
  python3 hd_h10_plan.py OUT_DIR [--ctl-w 2160 --ctl-h 3888 --ch-ctl 432 --ch-out 648 --variant main]
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hd_floorplan import construct      # noqa: E402
from hd_plan import build               # noqa: E402

SEQ = 151.2
SEQ_GAP = 86.4


def face_bits(p, name):
    ix = next(i for i, b in enumerate(p['blocks']) if b['name'] == name)
    out = {'N': 0, 'S': 0, 'W': 0, 'E': 0}
    for l in p['links']:
        for k, e in enumerate(l['e']):
            if e[0] == ix:
                out[l['endpoint_faces'][k]] += l['b']
    return out


def peer(p, gw, gh):
    """H2 peer step for a rectangular glue at the bottom of the (enlarged) ctl reserve; CLOSED M7 seq above it."""
    B = p['blocks']
    ci = next(i for i, b in enumerate(B) if b['name'] == 'ctl')
    c = B[ci]; old = copy.deepcopy(c)
    assert gw <= old['w'] + 1e-6 and gh + SEQ_GAP + SEQ <= old['h'] + 1e-6, (gw, gh, old)
    c.update(master='ot_s81hd_ctl_glue', w=gw, h=gh, x=round(old['x'] + (old['w'] - gw) / 2, 4), y=old['y'])
    for link in p['links']:
        for k, e in enumerate(link['e']):
            if e[0] != ci:
                continue
            face = link['endpoint_faces'][k]
            if face in ('N', 'S'):
                t = (e[2] - old['x']) / old['w']
                e[2] = round(c['x'] + t * c['w'], 4); e[3] = round(c['y'] + (c['h'] if face == 'N' else 0), 4)
            else:
                t = (e[3] - old['y']) / old['h']
                e[2] = round(c['x'] + (c['w'] if face == 'E' else 0), 4); e[3] = round(c['y'] + t * c['h'], 4)
    seq = dict(name='mtp_seq', master='dsfd_mtp_seq', kind='ctl_peer', group='clctl', x=round(c['x'] + c['w'] / 2 - SEQ / 2, 4),
               y=round(c['y'] + c['h'] + SEQ_GAP, 4), w=SEQ, h=SEQ, reg=False, orient='R0')
    si = len(B); B.append(seq)
    cy = round(c['y'] + c['h'], 4); sy = seq['y']; cx = round(c['x'] + c['w'] / 2, 4)
    for name, width, a, ap, b, bp, faces in [('seq_t', 605, ci, 'seq_t', si, 'ctl_i', ['N', 'S']),
                                              ('seq_r', 686, si, 'ctl_o', ci, 'seq_r', ['S', 'N'])]:
        e = [[a, ap, cx, cy if a == ci else sy, 'box'], [b, bp, cx, cy if b == ci else sy, 'box']]
        p['links'].append(dict(i=name, c='unit', b=width, d=1, e=e, endpoint_faces=faces, payload_b=width,
                               n='Direct registered CTL/seq peer, same clctl clock region, zero added cycles'))
    # the spine roots on the N face must not sit under the seq body: keep them where H4 had them relative to the glue centre
    p['facts']['ctl_peer'] = {'reserve': old, 'glue': c, 'sequencer': seq, 'source': 'b4f571642 unchanged CTL factored by split_ctl_peer.py',
                              'same_region': 'clctl', 'added_cycles': 0, 'peer_seed_reach_um': SEQ_GAP, 'peer_face': 'N',
                              'peer_pin_plan': 'results/arch/s81_head_1021/peer_pin_plan_m.json',
                              'physical_view': 'physical/ref_tile/s81hd_mtp_peer/views/dsfd_mtp_seq',
                              'original_closed_job': 'mtp-mtp_seq-c-c67a71fe5-tc'}
    p['facts']['instance_orientations']['mtp_seq'] = 'R0'


def regional_lep(p):
    lep = next(b for b in p['blocks'] if b['name'] == 'lep')
    lep['master'] = 'ot_s81hd_lep_regional'
    p['facts']['lep_regional'] = dict(source='4447aecf8', module='ot_s81hd_lep_regional', endpoint='ot_s81sl_lep_mu_ab_regional_r3r',
        reserve=dict(lep), clocks={'ck': 'C', 'ck_A': 'A', 'ck_B': 'B'}, parent_reset_stages=3,
        reset_roots='Independent same-age C/A/B parent forest leaves; no C root aliases A/B',
        cycle_delta={'C_to_pair': 4, 'pair_to_C': 5, 'lane_payload_valid': 2, 'reverse_credit': 2, 'credit_RTT': 4},
        closed_view=None, packing_status='OWED actual lane/core/ML packing and <=405um segment proof; no closed LEP view claimed')


def serdes_regions(p, pk, wn3_lep=True):
    lane_of = {ln['serdes']: nm for nm, ln in pk['lanes'].items()}
    moved = {}
    for b in p['blocks']:
        if b['master'] not in ('ot_pdie_serdes', 'ot_pdie_serdes_l276'):
            continue
        if b['name'] in lane_of:
            b['group'] = f"cl_{lane_of[b['name']]}"
        elif b['name'] != 'lk_WN3' or not wn3_lep:
            b['group'] = f"cl_{b['name']}"
        moved[b['name']] = b['group']
    if wn3_lep:
        p['facts']['serdes_instance_clocks'] = {'lk_WN3': {'clk': 'ck_head_lep_B'}}
    return moved


def nudge_search(q, out, steps=(21.6, -21.6, 43.2, -43.2, 64.8, -64.8, 86.4, -86.4, 108.0, -108.0)):
    """Deterministic peer-endpoint nudge (as hd_plan.NUDGE, H1): for every link whose dv_route72 station spacing leaves a
    hop > 405 um, slide its ctl / lep / lane endpoint along the face in 21.6-um steps until the route check passes."""
    import collections
    route = HERE.parent / 'dv_route72.py'
    sys.path.insert(0, str(HERE))
    import hd_plan as HP
    tmp_u, tmp_r = out / '_nudge_u.json', out / '_nudge_r.json'
    done = {}
    tried = collections.defaultdict(int)
    for it in range(60):
        tmp_u.write_text(json.dumps(q))
        subprocess.run([sys.executable, str(route), str(tmp_u), str(tmp_r)], check=True, capture_output=True)
        r = json.loads(tmp_r.read_text())
        bad = [l['i'] for l in r['links'] if max(HP.stations_hops(l)) > HP.REACH]
        fails = r['facts']['physical72']['routing_failures']
        if not bad and not fails:
            break
        by = {l['i']: l for l in q['links']}
        for lid in bad:
            l = by[lid]; k = tried[lid]
            assert k < len(steps), f'no nudge closes {lid}'
            # nudge the endpoint on the non-SerDes / non-station side with the longer face (ctl or lep first)
            names = [q['blocks'][e[0]]['name'] for e in l['e']]
            j = 0 if names[0] in ('ctl', 'lep') else 1 if names[1] in ('ctl', 'lep') else 0
            e, f, bb = l['e'][j], l['endpoint_faces'][j], q['blocks'][l['e'][j][0]]
            d = steps[k] - (steps[k - 1] if k else 0)
            if f in 'WE':
                e[3] = round(min(bb['y'] + bb['h'] - 5, max(bb['y'] + 5, e[3] + d)), 4)
            else:
                e[2] = round(min(bb['x'] + bb['w'] - 5, max(bb['x'] + 5, e[2] + d)), 4)
            tried[lid] += 1; done[lid] = steps[k]
    else:
        raise SystemExit('nudge search did not converge')
    tmp_u.unlink(); tmp_r.unlink()
    return done


def main():
    a = argparse.ArgumentParser()
    a.add_argument('out')
    a.add_argument('--variant', default='main')
    a.add_argument('--ctl-w', type=float, default=2160.0)
    a.add_argument('--ctl-h', type=float, default=3888.0)
    a.add_argument('--ch-ctl', type=float, default=432.0)
    a.add_argument('--ch-out', type=float, default=648.0)
    a.add_argument('--wn3-own', action='store_true', help='lk_WN3 in its own region (no lep-B instance clock)')
    a.add_argument('--checker', default='tools/check_macro_track_alignment.py')
    v = a.parse_args()
    out = Path(v.out); out.mkdir(parents=True, exist_ok=True)
    res_h = round(v.ctl_h + SEQ_GAP + SEQ + SEQ_GAP, 4)
    pk = construct(lep=(2592.0, 2592.0), ctl=(v.ctl_w, res_h), ch_ctl=v.ch_ctl, ch_out=v.ch_out, serdes_band=True)
    (out / 'floorplan_h10.json').write_text(json.dumps(pk, indent=1) + '\n')
    p = build(pk)
    p['links'] = [l for l in p['links']]
    for l in p['links']:          # H1 nudges were for the H1 geometry; H10 re-derives them from its own route check
        l.pop('nudge_um', None)
    peer(p, v.ctl_w, v.ctl_h)
    regional_lep(p)
    moved = serdes_regions(p, pk, wn3_lep=not v.wn3_own)
    fb = face_bits(p, 'ctl')
    g = p['facts']['ctl_peer']['glue']
    dens = {f: round(n / (g['w'] if f in 'NS' else g['h']), 2) for f, n in fb.items()}
    p['facts']['h10'] = dict(variant=v.variant, ctl_glue_um=[v.ctl_w, v.ctl_h], ctl_reserve_um=[v.ctl_w, res_h], ch_ctl=v.ch_ctl,
                             ch_out=v.ch_out, ctl_face_bits=fb, ctl_face_pins_per_um=dens, serdes_groups=moved,
                             diagnosis='H4 ctl glue 1036.8^2: E 14904 b = 14.4 pins/um, W 9384 b = 9.1; all GRT congestion gcells at the '
                                       'ctl E face; plan cut window 0.80 > 0.55; die usage 2-4 %/layer -> star-hub funnel, not capacity')
    p['facts']['physical72']['design'] = f'S81 HEAD H10{"" if v.variant == "main" else "-" + v.variant} (enlarged ctl, lane-regional SerDes)'
    pre = out / 'plan_pre_spr.json'
    pre.write_text(json.dumps(p, indent=1) + '\n')
    subprocess.run([sys.executable, str(HERE / 'hd_spr_closed_plan.py'), '--plan', str(pre), '--out', str(out), '--checker', v.checker], check=True)
    fin = out / 'plan_unrouted_h4.json'
    tgt = out / 'plan_unrouted_h10.json'
    q = json.loads(fin.read_text()); fin.unlink(); pre.unlink()
    q['facts']['physical72']['design'] = p['facts']['physical72']['design'] + '; exact CLOSED SPR m4 R0 bodies'
    q['facts']['h10']['nudges'] = nudge_search(q, out)
    tgt.write_text(json.dumps(q, indent=1) + '\n')
    print('HEAD_H10', v.variant, 'die', q['facts']['die_um'], q['facts']['die_mm2'], 'mm2', 'ctl pins/um', dens,
          'sha', hashlib.sha256(tgt.read_bytes()).hexdigest()[:12])


if __name__ == '__main__':
    main()
