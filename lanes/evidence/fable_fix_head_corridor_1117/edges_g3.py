"""FABLE-FIX-HEAD-CORRIDOR g3 (edges_g1.py of HEAD-PLAN-R4 with the stage map by TAG): bit edges of the COMPOSED geometry for the corridor allocator (alloc_r4, no virtual relays).
Every edge of a relayed hop is split at the real relay anchor of the g1 plan (src -> anchor rect, anchor -> dest); one relay FF
per source bit and anchor (RX head rank shared by the MLWD and RID dests).  Other rects: the g1 rect of the same group when the
model rect is a group rect, else the allocator frame (y >= 786.24 -> +60.48).  usage: edges_g1.py MODEL_PLAN G1_PLAN EDGES OUT
"""
import json, re, sys, collections, hashlib
from pathlib import Path
mp, gp, ep, op = map(Path, sys.argv[1:5])
M = json.loads(mp.read_text()); P = json.loads(gp.read_text()); E = json.loads(ep.read_text())
grp = lambda p: p['partition_types']['hd_lep0N']['clock']['landing_contract']['native_stage_groups']['groups']
# FABLE-FIX-HEAD-CORRIDOR g3: the NF15f chains are RENUMBERED (the relays took slots of the model stage indices), so a model
# stage is found in the composed plan by its TAG (stage:pin_s2 ...), never by its prefix.  edges_g1 mapped by prefix and sent
# model stage k to plan g_s[k], i.e. onto relay rects (pin_s2 -> pin_r2, pout_s0 -> pout_r0, krx1_s0 -> krx1_r0 ...).
mt = {}; pt = {}
for g in grp(M): mt.setdefault(tuple(g['rect_um']), set()).add(g['tag'])
for g in grp(P): pt.setdefault(g['tag'], set()).add(tuple(g['rect_um']))
remap = {}; unmapped = []
for r, tags in mt.items():
    cand = set()
    for tg in tags: cand |= pt.get(tg, set())
    if len(cand) == 1: remap[r] = list(list(cand)[0])
    else: unmapped.append((sorted(tags), r, sorted(cand)))
print('EDGES_G3 model rects', len(mt), 'mapped by tag', len(remap), 'unmapped', unmapped[:6], flush=True)
tag_rect = {}
for g in grp(P): tag_rect.setdefault(g['tag'], g['rect_um'])
def frame(r):
    r = tuple(r)
    if r in remap: return list(remap[r])
    return [r[0], r[1] + 60.48, r[2], r[3] + 60.48] if r[1] >= 786.24 - 1e-6 else list(r)
def clean(x): return x.replace('\\', '')
def idx(s, stem):
    m = re.search(re.escape(stem) + r'\[(\d+)\]', s); return int(m.group(1)) if m else None
def relay(kind, s, d, sbit):
    s, d = clean(s), clean(d)
    if kind == 'PIN stage': return {1: 'pin_r2', 2: 'pin_r4'}.get(idx(s, 'g_pin.g_s'))
    if kind == 'POUT stage': return {0: 'pout_r2', 1: 'pout_r4', 2: 'pout_r6'}.get(idx(s, 'g_pout.g_s'))
    if kind == 'RID to POUT0': return 'pout_r0'
    if kind == 'shared frame to TXI': return 'txi%d_r0' % idx(d, 'g_tx')
    if kind == 'TXI stage':
        i = idx(s, 'g_tx'); return 'txi%d_r2' % i if i in (1, 2) and idx(s, 'g_txi.g_s') == 0 else None
    if kind == 'TX output FF to K core input': return 'ktx%d_r0' % int(re.search(r'\.lo(\d)_d', s).group(1))
    if kind == 'K core to KRX': return 'krx%d_r0' % idx(d, 'g_kl')
    if kind == 'KRX stage': return {0: 'krx%d_r2', 1: 'krx%d_r4'}[idx(s, 'g_rxf.g_s') if 'g_rxf' in s else idx(s, 'g_rxr.g_s')] % idx(s, 'g_kl')
    if kind in ('shared RX head to MLWD', 'shared RX head to RID'):
        assert 0 <= sbit < 4 * 553; return 'rxh_l%d' % (sbit // 553)
    return None
out = []; seen = set(); split = collections.Counter(); relay_ff = collections.Counter()
for e in E['edges']:
    e = dict(e); e['source_rect_um'] = frame(e['source_rect_um']); e['dest_rect_um'] = frame(e['dest_rect_um'])
    e['source_rects_um'] = [frame(r) for r in e.get('source_rects_um', [e['source_rect_um']])]
    tg = relay(e.get('kind', ''), e['source_id'], e['dest_id'], e['source_bit'])
    if not tg:
        out.append(e); continue
    tag = 'stage:' + tg; ar = tag_rect[tag]; rid = 'RELAY:%s:%s' % (tag, e['source_id'])
    k = (rid, e['source_bit'])
    if k not in seen:
        seen.add(k); relay_ff[tag] += 1
        a = dict(e); a.update(dest_id=rid, dest_bit=e['source_bit'], dest_rect_um=ar, kind=e['kind'] + ' (to relay)'); out.append(a)
    b = dict(e); b.update(source_id=rid, source_rect_um=ar, source_rects_um=[ar], kind=e['kind'] + ' (from relay)'); out.append(b)
    split[e['kind']] += 1
rec = dict(E); rec.update(schema='opentallas.head_corridor_bit_edges.g1', plan=str(gp), plan_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
                          edges=out, notes=['HEAD-PLAN-R4 g1: relayed hops split at the real anchors', dict(split=split, relay_ff=relay_ff)])
op.write_text(json.dumps(rec) + '\n')
print('EDGES_G1', len(E['edges']), '->', len(out), 'split', dict(split), 'relay_ff', sum(relay_ff.values()), dict(relay_ff), flush=True)
