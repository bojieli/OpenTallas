#!/usr/bin/env python3
"""HBM-MU-QUAD-3 delta (F5): u_svg_Q0 k_{addr,len,rdy,tag,v} (the u_vmks_Q0 key-share link) re-pinned top-down to the
face toward u_vmks_Q0 in each hub type (NW: N face on M5, NE: E face on M4), on every 4th free plan track centred on the
partner's projection; one table per hub type (the shared Q0 table served both).  Usage: svg_face.py TOOLS PLAN_DIR"""
import json, sys, pathlib, hashlib, re
sys.path.insert(0, sys.argv[1]); import schema as S
pd = pathlib.Path(sys.argv[2]); P = json.load(open(pd / 'die_plan.json')); L = S.Plan(P).layers
rep = json.load(open(pd / 'delta_report.json')); out = []
PORTS = re.compile(r'^k_(addr|len|rdy|tag|v)(\[\d+\])?$')
for tn, face in (('q_hub_nw', 'N'), ('q_hub_ne', 'E')):
    hs = {h['inst']: h for h in P['partition_types'][tn]['hard_cores']}
    h = hs['u_svg_Q0']; pr = hs['u_vmks_Q0']; W, H = h['outline_um']
    assert h.get('orient', 'R0') in (None, 'R0')
    pins = json.load(open(pd / h['pins_file']))
    px = pr['origin_um'][0] + pr['outline_um'][0] / 2 - h['origin_um'][0]
    py = pr['origin_um'][1] + pr['outline_um'][1] / 2 - h['origin_um'][1]
    ly = L['M5' if face == 'N' else 'M4']; pitch, off = ly['pitch_um'], ly['offset_um']
    lim = W if face == 'N' else H
    used = {round(q['x'] if face == 'N' else q['y'], 4) for q in pins if q['layer'] == ly['name'] and
            (abs(q['y'] - H) < 0.1 if face == 'N' else abs(q['x'] - W) < 0.1)}
    mv = [q for q in pins if PORTS.match(q['name'])]
    c = min(max(px if face == 'N' else py, 0), lim); k0 = round((c - off) / pitch)
    sites = []; d = 0
    while len(sites) < len(mv):
        for k in ((k0,) if d == 0 else (k0 + 4 * d, k0 - 4 * d)):  # every 4th track: <= 5.2 pins/um (face_pins_per_um 6)
            v = round(off + k * pitch, 4)
            if 2 * pitch <= v <= lim - 2 * pitch and v not in used and len(sites) < len(mv):
                sites.append(v)
        d += 1
    sites.sort()
    for q, v in zip(mv, sites):
        q['layer'] = ly['name']
        if face == 'N': q['x'], q['y'] = v, round(H - 0.019, 4)
        else: q['x'], q['y'] = round(W - 0.019, 4), v
    nf = h['pins_file'].replace('.json', f'__{tn[-2:]}.json')
    (pd / nf).write_text(json.dumps(pins)); h['pins_file'] = nf
    out.append(dict(type=tn, face=face, pins=len(mv), span_um=[sites[0], sites[-1]], pins_file=nf))
rep['F5_svg_face'] = out
s = json.dumps(P, indent=1) + '\n'
(pd / 'die_plan.json').write_text(s); (pd / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(pd / 'delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], out=out)))
