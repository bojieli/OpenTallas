#!/usr/bin/env python3
"""KV-PLAN2 10-17 (HANDOFF 0cx+5 decision 2): bit-trace equivalence bench of the FOLDED stack fan (OT_KV_FANFOLD=1:
fan inside the stack root, one 8-group down chain from the root, concatenating up-gather chain, chain-end group
qkd_kvs_grp_h) against the unfolded design (OT_KV_FANFOLD=0: stack-middle fan, two 4-group chains, 8 gather stars).

The fan, the group chain words and the gathers are pure wiring around ONE register (the root's qkd_kv_stack_relays), so
equivalence is a symbolic bit trace on the generated tile expressions (every bit, every stack): each bit of the root's
input word i_ctl is a symbol R<i>, each bit of a group's own gather a symbol G<group>.<i>.  Checked for all 4 stacks:
  - every packed field of every group's i_ctl word (the fields its children read) carries the same R symbols;
  - every ECTL frame's kg / cfg export carries the same R symbols;
  - the root's up word to the control tile (o_ctl) carries the same G symbols in the same order;
  - the control tile and the root's return path (o_emb) are textually identical; register count root -> group = 1 in both.
Die relay stages are not part of the tiles (planned per hop, recorded by the plan).
--mut 1 swaps two group slots of the folded down chain, --mut 2 re-orders the root's gather word: both must FAIL.
    python3 tools/qwen_kv_die/fanfold_trace_bench.py [--mut N] [--out FILE]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STACKS = ('WS', 'WN', 'ES', 'EN')

DUMP = r'''
import sys, json; sys.path.insert(0, %r)
import kv_static_die as S
t = S.all_tiles()
out = dict(rtl=S.RTL_FILE, tiles={})
for d, v in t.items():
    if d.startswith(('slg_', 'kvs_hroot_', 'kvs_fan_')) or d == 'kvs_ctl':
        out['tiles'][d] = dict(kind=v['kind'], packed=v.get('packed', []), body=v.get('body', []),
            ports={p: dict(dir=q['dir'], width=q['width'], cls=q['cls'], peer=q.get('peer'), peer_port=q.get('peer_port'),
                           expr=q.get('expr'), consumers=q.get('consumers')) for p, q in v['ports'].items()})
out['ctl_text'] = S.module_text(t['kvs_ctl'], 'qkd_kvs_ctl')
print(json.dumps(out))
'''


def dump(fold):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_HROOT='1', OT_KV_FANFOLD='1' if fold else '0')
    return json.loads(subprocess.check_output([sys.executable, '-c', DUMP % str(HERE)], env=env, cwd=ROOT))


# ---- a tiny evaluator for the generated expressions: {a, b[3:0], {N{x}}} -> list of symbols, LSB first
TOK = re.compile(r'\s*(\{|\}|,|\[|\]|:|\d+|[A-Za-z_][A-Za-z0-9_]*)')


def tokens(s):
    pos, out = 0, []
    while pos < len(s):
        m = TOK.match(s, pos)
        if not m:
            if s[pos:].strip() == '':
                break
            raise ValueError(f'cannot tokenise {s[pos:pos + 40]!r}')
        out.append(m.group(1))
        pos = m.end()
    return out


def ev(expr, env):
    tk = tokens(expr)
    i = [0]

    def peek():
        return tk[i[0]] if i[0] < len(tk) else None

    def take(x=None):
        t = tk[i[0]]
        if x is not None and t != x:
            raise ValueError(f'expected {x} got {t} in {expr[:80]}')
        i[0] += 1
        return t

    def term():
        t = peek()
        if t == '{':
            take('{')
            if peek().isdigit() and tk[i[0] + 1] == '{':
                n = int(take())
                take('{')
                parts = [term()]
                while peek() == ',':
                    take(',')
                    parts.append(term())
                take('}')
                take('}')
                one = [b for p in reversed(parts) for b in p]
                return one * n
            parts = [term()]
            while peek() == ',':
                take(',')
                parts.append(term())
            take('}')
            return [b for p in reversed(parts) for b in p]       # MSB-first concat -> LSB-first list
        name = take()
        bits = env[name]
        if peek() == '[':
            take('[')
            hi = int(take())
            lo = hi
            if peek() == ':':
                take(':')
                lo = int(take())
            take(']')
            return bits[lo:hi + 1]
        return list(bits)
    r = term()
    if i[0] != len(tk):
        raise ValueError(f'trailing tokens in {expr[:80]}')
    return r


def relays_param(body):
    m = re.search(r'qkd_kv_stack_relays #\(\.HW\((\d+)\), \.FW\((\d+)\), \.GW\((\d+)\), \.RW\((\d+)\)\)', ' '.join(body))
    return tuple(int(x) for x in m.groups())


def trace(D, st, mut=0):
    """-> dict of observed symbol lists keyed by (kind, name)"""
    T = D['tiles']
    hd = f'kvs_hroot_{st}'
    h = T[hd]
    HW, FW, GW, RW = relays_param(h['body'])
    R = [f'R{i}' for i in range(HW + FW)]
    reg = dict(w_rly__fan=R[HW:HW + FW])                    # the root's one register stage (fan word)
    obs = {}
    # down: who feeds each group's i_ctl
    words = {}                                               # (inst, port) -> symbols
    fan = T.get(f'kvs_fan_{st}')
    if fan:                                                  # unfolded: root o_fan -> fan i_ctl (wires)
        assert h['ports']['o_fan']['expr'] == 'w_rly__fan'
        fenv = dict(i_ctl=reg['w_rly__fan'])
        for p, v in fan['ports'].items():
            if v['dir'] == 'output' and re.fullmatch(r'o_ch\d+|o_kg|o_c\d+', p):
                words[(f'kvs_fan_{st}', p)] = ev(v['expr'], fenv)
        src = fan
        sname = f'kvs_fan_{st}'
    else:
        for p, v in h['ports'].items():
            if v['dir'] == 'output' and re.fullmatch(r'o_ch\d+|o_kg|o_c\d+', p):
                words[(hd, p)] = ev(v['expr'], reg)
        src, sname = h, hd
    for p, v in src['ports'].items():
        if v['dir'] == 'output' and re.fullmatch(r'o_kg|o_c\d+', p):
            for cd, cp in v['consumers'] or []:
                obs[('export', f'{cd}.{cp}')] = words[(sname, p)]
    # walk every chain
    for p, v in src['ports'].items():
        if not (v['dir'] == 'output' and p.startswith('o_ch')):
            continue
        cur, w = v['peer'], words[(sname, p)]
        chain = []
        while cur:
            chain.append(cur)
            g = T[cur]
            if mut == 1 and len(chain) == 3 and not fan:
                w = w[:183] + w[183 + 11:183 + 22] + w[183:183 + 11] + w[183 + 22:]   # swap two per-group slots
            env = dict(i_ctl=w)
            for pn, ww, bname, off in g['packed']:
                if bname == 'i_ctl':
                    obs[('field', f'{cur}.{pn}')] = w[off:off + ww]
            dn = g['ports']['o_dn']
            w, cur = ev(dn['expr'], env), dn['peer']
    # up: every group's own gather -> root o_ctl
    grps = [d for d in T if d.startswith(f'slg_{st}_')]
    own = {}
    for d in grps:
        own[d] = [f'G{d}.{i}' for i in range(GW // len(grps))]
    def own_expr(d):
        e = T[d]['ports']['o_ctl']['expr']
        if T[d]['kind'] == 'grp_h':
            m = re.fullmatch(r'\{(\d+)\{(.*)\}\}', e)
            return m.group(2), ('rep', int(m.group(1)))
        m = re.fullmatch(r'\{i_up\[(\d+):0\], (.*)\}', e)
        if m:
            return m.group(2), ('up', int(m.group(1)))
        return e, None
    owntxt = {d: own_expr(d)[0] for d in grps}
    if len(set(owntxt.values())) != 1:
        raise ValueError('group gathers are not replica-identical')
    if fan:
        fenv = {}
        for p, v in fan['ports'].items():
            if v['dir'] == 'input' and p.startswith('i_g'):
                fenv[p] = own[v['peer']]
        gin = ev(fan['ports']['o_ctl']['expr'], fenv)
    else:
        # chain: find the head (grp_h) and walk to the root
        memo = {}
        def up_word(d):
            ex, kind = own_expr(d)
            if kind[0] == 'rep':
                return own[d] * kind[1]
            prev = next(x for x in grps if T[x]['ports']['o_ctl']['peer'] == d)
            return ev(T[d]['ports']['o_ctl']['expr'].replace(ex, 'OWN'), dict(OWN=own[d], i_up=up_word(prev)))
        last = next(d for d in grps if T[d]['ports']['o_ctl']['peer'] == hd)
        gin = up_word(last)
    assert len(gin) == GW, (len(gin), GW)
    genv = dict(w_rly__g=gin)
    gexpr = h['ports']['o_ctl']['expr']
    if mut == 2 and not fan:
        parts = gexpr[1:-1].split(', ')
        parts[0], parts[1] = parts[1], parts[0]
        gexpr = '{' + ', '.join(parts) + '}'
    obs[('up', 'o_ctl')] = ev(gexpr, genv)
    obs[('ret', 'o_emb')] = [h['ports']['o_emb']['expr']]
    return obs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    old, new = dump(False), dump(True)
    bad, n = [], 0
    if old['ctl_text'] != new['ctl_text']:
        bad.append('control tile text differs')
    for st in STACKS:
        o, f = trace(old, st), trace(new, st, a.mut)
        if set(o) != set(f):
            bad.append(f'{st}: observation sets differ: {sorted(set(o) ^ set(f))[:6]}')
        for k in sorted(set(o) & set(f)):
            n += 1
            if o[k] != f[k]:
                diff = next(i for i in range(min(len(o[k]), len(f[k])) + 1) if i >= min(len(o[k]), len(f[k])) or o[k][i] != f[k][i])
                bad.append(f'{st} {k}: differs at bit {diff}')
    heads = sorted(d for d, v in new['tiles'].items() if v['kind'] == 'grp_h')
    res = dict(bench='fanfold_trace_bench', mut=a.mut, observations=n, mismatches=len(bad), first=bad[:8],
               verdict='PASS' if not bad else 'FAIL', old_rtl=old['rtl'], new_rtl=new['rtl'], chain_heads=heads,
               fan_tiles_old=sorted(d for d in old['tiles'] if d.startswith('kvs_fan_')),
               fan_tiles_new=sorted(d for d in new['tiles'] if d.startswith('kvs_fan_')))
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
