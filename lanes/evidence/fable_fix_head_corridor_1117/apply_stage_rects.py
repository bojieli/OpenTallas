"""FABLE-FIX-HEAD-CORRIDOR: copy the hd_lep0N native stage group rects of a CANDIDATE plan (base groups legalized + relay ranks
as bit-slice columns) onto a composed TARGET plan, matched by group prefix.  Nothing else of the target changes.
usage: apply_stage_rects.py CANDIDATE_PLAN TARGET_PLAN OUT_PLAN REPORT.json"""
import json, sys, hashlib
from pathlib import Path
cp, tp, op, rp = map(Path, sys.argv[1:5])
grp = lambda p: p['partition_types']['hd_lep0N']['clock']['landing_contract']['native_stage_groups']['groups']
C = json.loads(cp.read_text()); T = json.loads(tp.read_text())
sp = lambda p: {k: v for k, v in p['partition_types']['hd_lep0N']['clock']['landing_contract']['native_stage_groups']['params'].items() if k != 'KCRED'}
assert sp(C) == sp(T), ('stage tuple differs (KCRED, the credit depth, is not geometry and is ignored)', sp(C), sp(T))
assert C['partition_types']['hd_lep0N']['outline_um'] == T['partition_types']['hd_lep0N']['outline_um']
assert json.dumps(C['partition_types']['hd_lep0N']['hard_cores'], sort_keys=True) == json.dumps(T['partition_types']['hd_lep0N']['hard_cores'], sort_keys=True), 'hard cores differ'
cr = {}
for g in grp(C): cr.setdefault((g['prefix'], g['tag']), []).append(g['rect_um'])
seen = {}; ch = []
for g in grp(T):
    k = (g['prefix'], g['tag']); i = seen.get(k, 0); seen[k] = i + 1
    new = cr[k][i]
    if list(new) != list(g['rect_um']): ch.append(dict(tag=g['tag'], old=g['rect_um'], new=new)); g['rect_um'] = list(new)
assert {k: len(v) for k, v in cr.items()} == seen, 'group lists differ'
op.write_text(json.dumps(T, indent=1) + '\n')
rp.write_text(json.dumps(dict(schema='opentallas.head_nf15f_stage_rect_patch.v1', candidate=hashlib.sha256(cp.read_bytes()).hexdigest(),
    target=hashlib.sha256(tp.read_bytes()).hexdigest(), out=hashlib.sha256(op.read_bytes()).hexdigest(), changed=ch), indent=1) + '\n')
print('STAGE_RECTS changed', len(ch), 'of', len(grp(T)), 'out', hashlib.sha256(op.read_bytes()).hexdigest()[:16])
