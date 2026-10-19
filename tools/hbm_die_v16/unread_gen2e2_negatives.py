#!/usr/bin/env python3
"""LH-UNREAD 10-19: strict negative proofs for the GEN2e2 unread manifest candidate, on the REAL die.

Every case runs the real tools/die_port_bind.py (manifest API) and must FAIL or REFUSE:
  P0  positive replay: reviewed manifest -> unread 5254 exactly (65066 admitted), all structural classes 0.
  N1  stale die: d517 die.v (47f3575f) with the GEN2e2 manifest -> REFUSED (die identity).
  N2  real fault consumer dropped: hleaf_NE.t_fault reads calendar_NE__tgt_fault instead of calendar_NE__fault;
      review + proposal re-stamped to the mutant die -> bind FAILS with 5255 (the dropped fault bit is NOT admitted).
  N3  real payload consumer dropped: hidxr_NE_rr2__o[0] (relay payload) no longer read; re-stamped -> FAILS 5255.
  N4  expanded range onto a consumed payload bit (hidxr_NE_rr2 o [295,303]); re-stamped proposal -> REFUSED occupied.
  N5  selected source drift (one byte appended to hfd_hgi_vm_calendar_f20.sv in a scratch copy) -> REFUSED.
  N6  wrong digest (manifest sha of the d517 ROOT admission) -> REFUSED.
Usage: unread_gen2e2_negatives.py WT ARTDIR   (ARTDIR holds b0/{die.v,common_args.txt,contract_pre_relay.json})
"""
import copy, hashlib, json, os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

WT, ART = sys.argv[1], sys.argv[2]
B0 = ART + '/b0'
R = WT + '/results/arch/hbm_unread_gen2e2_1019'
REV, MAN = R + '/review_gen2e2_candidate.json', R + '/manifest_proposal_gen2e2.json'
OLD_DIE = '/home/ubuntu/artifacts/hdie-d4/d4g_gen2e/strict_l17_score_die.v'
H = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
COMMON = open(B0 + '/common_args.txt').read().split()
DIE_IDX = COMMON.index(B0 + '/die.v')


def bind(root, die, extra, out):
    args = list(COMMON); args[DIE_IDX] = die
    p = subprocess.run(['python3', 'tools/die_port_bind.py'] + args + extra + ['--out', out + '.json'],
                       cwd=root, capture_output=True, text=True)
    open(out + '.log', 'w').write(p.stdout + p.stderr)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ''


def adm(review, manifest, sha, contract=B0 + '/contract_pre_relay.json'):
    return ['--unread-review', review, '--unread-contract', contract, '--unread-manifest', manifest,
            '--unread-manifest-sha256', sha]


def restamp(case, die, edit_review=None):
    """Mutant die + review re-stamped to it + fresh proposal (models a hash refresh on a regenerated die)."""
    d = ART + '/neg/' + case; os.makedirs(d, exist_ok=True)
    rv = json.load(open(REV)); rv = copy.deepcopy(rv)
    rv['inputs']['die_v'] = {'path': die, 'sha256': H(die)}
    if edit_review: edit_review(rv)
    json.dump(rv, open(d + '/review.json', 'w'), indent=1)
    code, last = bind(WT, die, ['--unread-review', d + '/review.json', '--unread-contract', B0 + '/contract_pre_relay.json',
                               '--unread-proposal-out', d + '/proposal.json'], d + '/propose')
    if code != 0 or not os.path.exists(d + '/proposal.json'):
        return d, None, last
    return d, H(d + '/proposal.json'), last


def mutate_die(case, old, new):
    d = ART + '/neg/' + case; os.makedirs(d, exist_ok=True)
    t = open(B0 + '/die.v').read(); assert t.count(old) == 1, (case, t.count(old))
    open(d + '/die.v', 'w').write(t.replace(old, new)); return d + '/die.v'


def case_p0():
    c, last = bind(WT, B0 + '/die.v', adm(REV, MAN, H(MAN)), ART + '/neg/P0')
    return 'P0', ('PASS' if 'unread_net_bits=5254 ' in last and 'undriven_net_bits=0' in last else 'BAD'), last


def case_n1():
    c, last = bind(WT, OLD_DIE, adm(REV, MAN, H(MAN)), ART + '/neg/N1')
    return 'N1', ('PASS' if c != 0 and 'REFUSED' in open(ART + '/neg/N1.log').read() else 'BAD'), last


def case_drop(case, old, new):
    die = mutate_die(case, old, new)
    d, sha, last = restamp(case, die)
    if not sha: return case, 'BAD(propose refused: %s)' % last, last
    c, last = bind(WT, die, adm(d + '/review.json', d + '/proposal.json', sha), d + '/admit')
    return case, ('PASS' if c != 0 and 'unread_net_bits=5255 ' in last else 'BAD'), last


def case_n4():
    def widen(rv):
        for e in rv['approved_entries']:
            if e['instance'] == 'hidxr_NE_rr2' and e['port'] == 'o':
                e['unread_ranges'] = [[295, 303]]; e['bit_count'] = 9
        rv['approved_bits'] += 1
    d, sha, last = restamp('N4', B0 + '/die.v', widen)
    if not sha:
        return 'N4', ('PASS' if 'REFUSED' in open(d + '/propose.log').read() else 'BAD'), last
    c, last = bind(WT, B0 + '/die.v', adm(d + '/review.json', d + '/proposal.json', sha), d + '/admit')
    return 'N4', ('PASS' if c != 0 and 'occupied' in open(d + '/admit.log').read() else 'BAD'), last


def case_n5():
    """Runs ALONE after the parallel cases: one byte appended to a selected source in this worktree, restored in finally."""
    f = WT + '/rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_f20.sv'
    orig = open(f, 'rb').read()
    try:
        open(f, 'ab').write(b'\n')
        c, last = bind(WT, B0 + '/die.v', adm(REV, MAN, H(MAN)), ART + '/neg/N5')
    finally:
        open(f, 'wb').write(orig)
    assert H(f) == hashlib.sha256(orig).hexdigest()
    log = open(ART + '/neg/N5.log').read()
    return 'N5', ('PASS' if c != 0 and 'REFUSED' in log and 'source' in log and 'outside source root' not in log else 'BAD'), last


def case_n6():
    c, last = bind(WT, B0 + '/die.v', adm(REV, MAN, '2beccb8e65b7a62733fd9265ce4a0397192de0315202ba1a912c257f8ec5ddf2'), ART + '/neg/N6')
    return 'N6', ('PASS' if c != 0 and 'REFUSED' in open(ART + '/neg/N6.log').read() else 'BAD'), last


os.makedirs(ART + '/neg', exist_ok=True)
jobs = [case_p0, case_n1, case_n4, case_n6,
        lambda: case_drop('N2', 'calendar_NE__fault[0], calendar_NE__tgt_fault[0], cp_svg_NW7',
                          'calendar_NE__tgt_fault[0], calendar_NE__tgt_fault[0], cp_svg_NW7'),
        lambda: case_drop('N3', 'hidxr_NE_rr2__o[295:0]', '{hidxr_NE_rr2__o[295:1], hidxr_NE_rr2__o[1]}')]
with ThreadPoolExecutor(7) as ex:
    res = list(ex.map(lambda f: f(), jobs))
res.append(case_n5())
ok = all(r[1] == 'PASS' for r in res)
out = dict(schema='opentallas.hbm_unread_gen2e2_negatives.v1', manifest_sha256=H(MAN), review_sha256=H(REV),
           die_sha256=H(B0 + '/die.v'), verdict='PASS' if ok else 'FAIL',
           cases=[dict(case=c, result=v, bind_last_line=l[:400]) for c, v, l in res])
json.dump(out, open(R + '/negatives.json', 'w'), indent=1)
for c, v, l in res: print(c, v, l[:200])
print('NEGATIVES', out['verdict'])
sys.exit(0 if ok else 1)
