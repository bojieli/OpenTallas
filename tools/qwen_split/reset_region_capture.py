"""Final regional reset ownership, after all clock-region splitting.

Rehome only an existing final capture whose complete terminal fanout names one
actual receiving region. Multiple target roots require physically allocated split
captures; this helper records them and never invents sites, clocks or an endpoint
waiver. Foreign rep/d inputs are candidates only: reset/calendar qualification is
kept on HOLD until source-bound release intervals and boot anchors are supplied.
"""
import hashlib
import re
from collections import defaultdict
from pathlib import Path

REP = ('qfd_rst_rep', 'qfd_rst_rep_p8')
RTL = 'rtl/qwen_sys/reset_tree_20261013/ot_qwen_rst_rep.sv'


def finalize(model, per, source_root=None):
    by = {i.name: i for i in model['insts']}
    clocks = defaultdict(dict)
    # m buses still contain pre-refile regional trunks: only final per is valid.
    for bid, cls, bits, eps in model['buses']:
        if cls == 'clock_trunk' and not re.fullmatch(r'clk_r\d+', bid):
            for i, p in eps[1:]:
                clocks[i][p.lstrip('*')] = bid
    for k, eps in per.items():
        for i, p in eps:
            clocks[i][p.lstrip('*')] = f'clk_r{k}'
    related = {}
    for key in ('dv_cluster_clocks', 'native_static_io_bind'):
        spec = model.get(key) or {}
        if spec.get('master'):
            related[spec['master']] = spec.get('related_pins') or {}

    def receiver(i, p):
        p = p.lstrip('*')
        refs = related.get(by[i].master, {}).get(p)
        if refs:
            return {clocks[i].get(cp) for cp in refs}
        if by[i].kind == 'relay':
            # en is captured on source ck_s (one-frame ring) or ck (hop0).
            # rs releases the reader on ck. Do not use a forwarded write clock.
            order = ('ck_s', 'ck') if p == 'en' else ('ck',)
            for cp in order:
                if cp in clocks[i]:
                    return {clocks[i][cp]}
        return set(clocks[i].values()) or {None}

    terminal = defaultdict(list)
    inputs = {}
    for bid, cls, bits, eps in model['buses']:
        if cls in ('clock_trunk', 'clock', 'constant') or bits != 1 or not eps:
            continue
        si, sp = eps[0]
        for di, dp in eps[1:]:
            if by[di].master in REP and dp.lstrip('*') == 'd':
                inputs[di] = (bid, si, sp)
            if by[si].master in REP and re.fullmatch(r'q\d*', sp.lstrip('*')) and by[di].master not in REP:
                terminal[si].append(dict(net=bid, src_port=sp, dst=di, dst_port=dp,
                                         roots=sorted(receiver(di, dp), key=str)))
    moved, split, unresolved = [], [], []
    for rep, loads in sorted(terminal.items()):
        roots = {r for load in loads for r in load['roots']}
        if None in roots or not roots:
            unresolved.append(dict(rep=rep, reason='unknown receiving clock', loads=loads)); continue
        if len(roots) != 1:
            split.append(dict(rep=rep, receiving_roots=sorted(roots), loads=loads)); continue
        dst = next(iter(roots))
        if not re.fullmatch(r'clk_r\d+', dst):
            unresolved.append(dict(rep=rep, reason='nonregional receiving clock; explicit foreign-domain plan required', loads=loads)); continue
        locations = [(k, p) for k, eps in per.items() for i, p in eps if i == rep]
        if len(locations) != 1:
            unresolved.append(dict(rep=rep, reason='capture has no unique final regional clock', loads=loads)); continue
        k0, cp = locations[0]; k1 = int(dst[5:])
        if k0 != k1:
            per[k0].remove((rep, cp)); per.setdefault(k1, []).append((rep, cp))
            moved.append(dict(rep=rep, from_clock=f'clk_r{k0}', clock=dst, loads=loads))
        clocks[rep][cp] = dst
    for k in [k for k, eps in per.items() if not eps]:
        del per[k]
    candidates = []
    for rep, (net, si, sp) in sorted(inputs.items()):
        rd = set(clocks[rep].values())
        rs = set(clocks[si].values())
        if rd and rs and rd == rs:
            continue
        candidates.append(dict(pin=rep+'/d', master=by[rep].master, net=net,
                               source=si+'/'+sp, source_clocks=sorted(rs), clocks=sorted(rd),
                               latency_edges=10 if by[rep].master.endswith('_p8') else 2,
                               qualification='HOLD: receiving-clock source proof and boot/calendar interval evidence required'))
    # Reuse the source proof already performed by _reset_tree; no new gate.
    proof = dict(path=RTL, sha256=None,
                 structural_pass=bool((model.get('reset_sync', {}).get('rep_check') or [False])[0]))
    if source_root is not None:
        path = Path(source_root) / RTL
        proof['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = dict(schema='opentallas.qwen.final-reset-capture-plan.v1', moved=moved,
                  split_required=split, unresolved=unresolved, sync_candidates=candidates,
                  source_proof=proof, calendar='HOLD: no release bounds invented',
                  qualified=False)
    model['final_reset_capture_plan'] = result
    return result
