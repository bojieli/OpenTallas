#!/usr/bin/env python3
"""HBM-R15 C16 plan delta on Codex pin6_bundle (C15 + XQ 362.88x276.48 + HC pair E pins).
(a) Q3 edge core re-lot 190.08 -> 216.00 x 1054.08 (content failure: 12 SRAM 171.288x77.784 = 84% of the core,
    movable std 13550 um2 in 14163 um2 free -> 95.7% util, GP overflow .9956 @38910 it). Growth at origin toward the
    95.04-um gap to body_core; macro column re-centred (x 9.396 -> 22.356), E-face pins follow the face, W unchanged,
    centre entry x 95.04 -> 108.00 (same y 527.04, macro channel). New free 41.2k um2 -> std util ~33% UNCHECKED.
(b) EP 250.56x375.84 -> 241.92x397.44 (Codex EP crossing model: TX-west/RX-east body, 336 crossing nets vs 200 old SRAM
    gap capacity, 425 at 60% in the taller outline). Non-host EP y 1114.56 -> 1088.64, host EP origin kept
    (ep_candidate_slots_shifted.json, 0 collisions). Pin table = HBM-CORES-R12 W/E split (pins.json sha 5a4807c8)
    re-spread per face in order onto the new outline (tracks .024+.048k, 8.64 end reserve). Entry = centre (120.96,198.72);
    core owner places SRAMs 2+2 around the centre channel.
No RTL/cycle change. TRIAL until epall/relax/G0/G0C pass.  usage: c16_delta.py PLANDIR EPPINS"""
import json, sys, collections, math
from pathlib import Path
d = Path(sys.argv[1]); eppins = json.loads(Path(sys.argv[2]).read_text())
plan = json.loads((d/'die_plan.json').read_text()); ent = json.loads((d/'clock_entries.json').read_text())
cmf = d/'core_macros.json'; cm = json.loads(cmf.read_text())
rep = {'q3_edge': [], 'ep': [], 'collisions': []}
def tracks(lo, hi, n):
    k0 = math.ceil((lo-.024)/.048); k1 = math.floor((hi-.024)/.048); ks = list(range(k0, k1+1))
    assert n <= len(ks), (n, len(ks))
    return [round(.024+.048*ks[min(len(ks)-1, int((i+.5)*len(ks)/n))], 3) for i in range(n)]
# ---- (a) q3 edge
QW_OLD, QW, QH = 190.08, 216.0, 1054.08
qf_new = 'cores/ot_hfd_coll_q3_edge_core__216x1054.08__r15_relot.json'
done = False
for tn, t in plan['partition_types'].items():
    for c in t.get('hard_cores', []):
        if c['module'] != 'ot_hfd_coll_q3_edge_core': continue
        if not done:
            pins = json.loads((d/c['pins_file']).read_text()); ne = 0
            for q in pins:
                if abs(q['x']-QW_OLD) < 2: q['x'] = round(q['x']+QW-QW_OLD, 3); ne += 1
            (d/qf_new).write_text(json.dumps(pins, indent=1)+'\n'); done = True
            rep['q3_edge_pins_moved_E'] = ne
        old = c['outline_um'][:]; c['outline_um'] = [QW, QH]; c['pins_file'] = qf_new
        c['note'] = c.get('note', '') + '; HBM-R15 C16 re-lot 216.00 wide (content: 12 SRAM 84%), growth at origin'
        e = ent.get(tn, {}).get(c['inst'].split('__')[0]) or ent.get(tn, {}).get(c['inst'])
        rep['q3_edge'].append(dict(type=tn, inst=c['inst'], origin=c['origin_um'], old=old, new=c['outline_um'], entry_found=bool(e)))
for tn, dd in ent.items():
    for inst, v in dd.items():
        if v.get('module') == 'ot_hfd_coll_q3_edge_core':
            x, y = 108.0, v['xy_um'][1]; v['xy_um'] = [x, y]
            v['island_um'] = [round(x-4.32, 3), round(y-4.32, 3), round(x+4.32, 3), round(y+4.32, 3)]
            v['source'] += '; HBM-R15 C16 re-lot centre x 108.00 (same macro channel y)'
q = cm['cores'].get('ot_hfd_coll_q3_edge_core') or {}
q.update(outline_um=[QW, QH], status=q.get('status', 'UNKNOWN'), r15_note='12x ot_sram_1r1w_64x512_m1_r2c2 column x22.356, 86.4 pitch from y12.96 (k3m column re-centred)')
cm['cores']['ot_hfd_coll_q3_edge_core'] = q
# ---- (b) EP
EW, EH = 241.92, 397.44
slots = {(s['type'], s['inst']): s['origin'] for s in json.loads((d/'ep_candidate_slots_shifted.json').read_text())}
groups = collections.defaultdict(list)
for i, p in enumerate(eppins):
    nm = p['bus'] if p.get('bit') is None else f"{p['bus']}[{p['bit']}]"
    groups[p['face'], p['layer']].append((p['y'] if p['face'] in 'EW' else p['x'], i, nm))
newp = []
for (f, L), ps in groups.items():
    ps.sort(); length = EH if f in 'EW' else EW
    for (pos, i, nm), v in zip(ps, tracks(8.64, length-8.64, len(ps))):
        x = .019 if f == 'W' else round(EW-.019, 3) if f == 'E' else v
        y = .019 if f == 'S' else round(EH-.019, 3) if f == 'N' else v
        newp.append(dict(name=nm, layer=L, x=x, y=y))
assert len({p['name'] for p in newp}) == len(newp) == len(eppins)
epf = 'cores/hfd_ep_static__241.92x397.44__r15_wesplit.json'
(d/epf).write_text(json.dumps(newp, indent=1)+'\n')
fc = collections.Counter(); 
for (f, L), ps in groups.items(): fc[f] += len(ps)
rep['ep_faces'] = {f: dict(pins=n, per_um=round(n/((EH if f in 'EW' else EW)-17.28), 2)) for f, n in fc.items()}
for tn, t in plan['partition_types'].items():
    for c in t.get('hard_cores', []):
        if c['module'] != 'hfd_ep_static': continue
        old = (c['origin_um'][:], c['outline_um'][:])
        c['origin_um'] = slots[(tn, c['inst'])]; c['outline_um'] = [EW, EH]; c['pins_file'] = epf
        c['note'] = c.get('note', '') + '; HBM-R15 C16 EP 241.92x397.44 crossing-capacity outline + R12 W/E split pins'
        rep['ep'].append(dict(type=tn, inst=c['inst'], old=old, origin=c['origin_um']))
for tn, dd in ent.items():
    for inst, v in dd.items():
        if v.get('module') == 'hfd_ep_static':
            x, y = 120.96, 198.72; v['xy_um'] = [x, y]
            v['island_um'] = [round(x-4.32, 3), round(y-4.32, 3), round(x+4.32, 3), round(y+4.32, 3)]
            v['source'] += '; HBM-R15 C16 EP 241.92x397.44 centre channel'
e = cm['cores'].get('hfd_ep_static') or {}
e.update(outline_um=[EW, EH], status='PLAN-TRIAL', macros=[], channels=[], r15_note='4 SRAM 2+2 around centre channel y198.72; core owner supplies placement')
cm['cores']['hfd_ep_static'] = e
# ---- collisions (bodies, same partition type)
for tn, t in plan['partition_types'].items():
    hc = t.get('hard_cores', [])
    for c in hc:
        if c['module'] not in ('hfd_ep_static', 'ot_hfd_coll_q3_edge_core'): continue
        x, y = c['origin_um']; w, h = c['outline_um']
        if x < 0 or y < 0 or x+w > t['outline_um'][0]+1e-6 or y+h > t['outline_um'][1]+1e-6: rep['collisions'].append((tn, c['inst'], 'OUTSIDE'))
        for o in hc:
            if o is c: continue
            ox, oy = o['origin_um']; ow, oh = o['outline_um']
            if x < ox+ow and ox < x+w and y < oy+oh and oy < y+h: rep['collisions'].append((tn, c['inst'], o['inst']))
(d/'die_plan.json').write_text(json.dumps(plan, indent=1)+'\n')
(d/'clock_entries.json').write_text(json.dumps(ent, indent=1)+'\n')
cmf.write_text(json.dumps(cm, indent=1)+'\n')
(d/'c16_delta_report.json').write_text(json.dumps(rep, indent=1)+'\n')
print(json.dumps({k: (v if k != 'q3_edge' and k != 'ep' else len(v)) for k, v in rep.items()}))
