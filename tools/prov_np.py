#!/usr/bin/env python3
"""SIGNOFF-SPRINT-24 (moved to coord tools by SS25-TOK 11-03): write a resign PROVENANCE for a LOCAL_PASS_NEEDS_PARENT re-sign dir (COORD 11-03 18:48 ruling,
OWNER 18:49 standing rule). Uses the tag's own resign.build_record unchanged; the only difference is that a sign-off
record whose verdict is LOCAL_PASS_NEEDS_PARENT, local_verdict SIGNED and whose only reasons are io_hold_parent is
read as SIGNED. The record carries verdict_basis so the substitution is visible.
usage: prov_np.py TOOLS_DIE_PLAN --dir D --kit K --tag T [--lec L] [--build-commit C] [--note N] [--repo R]"""
import argparse, json, os, sys
ap = argparse.ArgumentParser()
ap.add_argument('tools'); ap.add_argument('--dir', required=True); ap.add_argument('--kit', required=True)
ap.add_argument('--tag', required=True); ap.add_argument('--lec'); ap.add_argument('--build-commit')
ap.add_argument('--note'); ap.add_argument('--repo', default='/home/ubuntu/OpenTallas')
a = ap.parse_args()
sys.path.insert(0, a.tools)
import resign as R
so_p = os.path.join(os.path.abspath(a.dir), 'signoff', 'signoff.json')
so = json.load(open(so_p))
v = so.get('verdict')
np = (v == 'LOCAL_PASS_NEEDS_PARENT' and so.get('local_verdict') == 'SIGNED' and
      all(str(r).startswith('io_hold_parent') for r in (so.get('reasons') or [])))
if v != 'SIGNED' and not np:
    sys.exit('REFUSED: %s verdict %s local %s reasons %s' % (so_p, v, so.get('local_verdict'), so.get('reasons')))
orig = R.load
def load(p):
    d = orig(p)
    if np and os.path.abspath(p) == so_p:
        d = dict(d, verdict='SIGNED')
    return d
R.load = load
rec = R.build_record(a.dir, a.kit, a.tag, repo=a.repo, tools=a.tools, build_commit=a.build_commit, lec=a.lec,
                     lane=os.environ.get("RESIGN_LANE", "SIGNOFF-SPRINT-25"), note=a.note)
if np:
    rec['verdict_basis'] = ('LOCAL_PASS_NEEDS_PARENT (local SIGNED, only io_hold_parent open) counts SIGNED per COORD '
                            '2026-11-03 18:48 ruling / OWNER 18:49; io_hold_parent receipt moves to die STA FF')
out = os.path.join(os.path.abspath(a.dir), 'PROVENANCE.json')
json.dump(rec, open(out, 'w'), indent=1, sort_keys=True)
print('RESIGN RECORDED %s (%s %s, LEC %s%s)' % (out, a.tag, rec['src_commit'][:12], rec['lec_verdict'],
                                               ', NEEDS_PARENT basis' if np else ''))
