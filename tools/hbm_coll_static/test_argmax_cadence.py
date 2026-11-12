"""--issue-cadence: off = byte-identical to the base compiler, on (ISS2E, 2-edge rows + pad mask) = edge-level re-check."""
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import argmax_rows as A  # noqa: E402
import parent_timing as PT  # noqa: E402
LAYOUT = json.loads(A.LAYOUT.read_text())['fields']


def compile_edges(vm_rt, P, cadence, rows=256, start_reg=False, pr=False):
    A.set_rows(rows); A.set_npt(3); A.START_O = -1 if start_reg else 0; A.set_arg_pr_source(pr)
    A.set_cadence(cadence); A.set_vm_rt(vm_rt)
    words, meta, info = A.compile_program(0, P)
    # expand the loop programme with the issuer counters (reuse unroll's walk) into the executed row stream
    pc, counters, rowsx = 0, [0] * (1 << A.PW), []
    while True:
        f = A.dec_meta(meta[pc]); rowsx.append((pc, counters[f['lid']]))
        if f['halt']:
            break
        count, lid = f['count'], f['lid']
        if count and counters[lid] < count - 1:
            counters[lid] += 1; pc = f['target']
        else:
            if count: counters[lid] = 0
            pc = f['next']
    return words, meta, info, rowsx


def get(w, k):
    f = LAYOUT[k]
    return (w >> f['lsb']) & ((1 << f['width']) - 1)


@pytest.mark.parametrize('start_reg,pr', [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize('vm_rt', [0, 3, 81])
def test_c2_edge_chain(vm_rt, start_reg, pr):
    if vm_rt % 2 == 0:
        with pytest.raises(SystemExit, match='odd fixed latency at C=2'):
            compile_edges(vm_rt, 4, 2, start_reg=start_reg, pr=pr)
        A.START_O = 0; A.set_arg_pr_source(False)
        return
    words, meta, info, rowsx = compile_edges(vm_rt, 4, 2, start_reg=start_reg, pr=pr)
    par = PT.iss2e_variant(start_reg, pr)['issue_pad_fields']
    ev = {}                                   # name -> list of (edge, row index, bitvalue) ; edge = 2*row + pad parity
    for r, (pc, it) in enumerate(rowsx):
        w = words[pc]
        if get(w, 'vm_rq') >> 16 & 1: ev.setdefault('vm_rq', []).append(2 * r + par['vm_rq'])
        cs = get(w, 'capture_slot')
        if (cs >> 5) & 0xf: ev.setdefault('capture', []).append(2 * r + par['capture_slot'])
        ar = get(w, 'ar_low') | (get(w, 'ar_high') << 31)
        for name, bit in (('start', 48), ('flush', 49), ('publish', 50)):
            if ar >> bit & 1: ev.setdefault(name, []).append(2 * r + par[name])
        if (ar >> 51) & 0xf: ev.setdefault('in', []).append(2 * r + par['in_slot'])
        ss = get(w, 'sink_slot')
        if (ss >> 11) & 0xf: ev.setdefault('sink_vm', []).append(2 * r + par['sink_vm'])
        if (ss >> 3) & 1: ev.setdefault('sink_del', []).append(2 * r + par['sink_delivery'])
        if get(w, 'capture_arg'): ev.setdefault('carg', []).append(2 * r + par['capture_arg'])
        if get(w, 'del_obase'): ev.setdefault('obase', []).append(2 * r + par['del_obase'])
    P = 4
    assert len(ev['start']) == P and len(ev['publish']) == P and len(ev['in']) == 24 * P
    assert len(ev['vm_rq']) == 24 * P and len(ev['capture']) == 24 * P
    # request -> capture 10+VM_RT, capture -> sink 1, sink -> in_slot 2, per input
    for a, b in zip(ev['vm_rq'], ev['capture']): assert b - a == 10 + vm_rt
    for a, b in zip(ev['capture'], ev['sink_vm']): assert b - a == 1
    for a, b in zip(ev['sink_vm'], ev['in']): assert b - a == 2
    for p in range(P):
        ins = ev['in'][24 * p:24 * p + 24]
        assert ins[0] - ev['start'][p] == (2 if start_reg else 1)   # start 1 edge (tp192 start_reg: 2) before the first input
        assert all(y - x == 2 for x, y in zip(ins, ins[1:]))
        assert ev['flush'][p] - ins[-1] == 1                   # flush = last input + 1 (v8)
        assert ev['publish'][p] - ev['flush'][p] == 6          # fixed amerge flush + 6
        assert ev['carg'][p] - ev['publish'][p] == 1 + pr and ev['sink_del'][p] - ev['publish'][p] == 2 + pr
        assert ev['obase'][p] - ev['publish'][p] == 3 + pr
        if p: assert ev['start'][p] + start_reg - ev['publish'][p - 1] >= 1   # unit faults if start (start_reg: registered, +1) arrives while active


def test_c1_off_is_identical_to_the_historical_compiler():
    # cadence 1 (default) manifest/rows sha vs the committed base file (git show of the base rev), several VM_RT
    base = subprocess.run(['git', '-C', str(HERE), 'show', 'HEAD:tools/hbm_coll_static/argmax_rows.py'], capture_output=True)
    if base.returncode:
        pytest.skip('no HEAD copy')
    # HEAD may already contain this change: use the explicit base rev when given
    import os
    rev = os.environ.get('ARGMAX_BASE_REV')
    if not rev:
        pytest.skip('set ARGMAX_BASE_REV=<rev before the change>')
    old = subprocess.run(['git', '-C', str(HERE), 'show', f'{rev}:tools/hbm_coll_static/argmax_rows.py'], capture_output=True, check=True)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); (d / 'tools/hbm_coll_static').mkdir(parents=True)
        (d / 'tools/hbm_coll_static/argmax_rows.py').write_bytes(old.stdout)
        (d / 'rtl').symlink_to(A.ROOT / 'rtl')
        for vm_rt, rows, P, extra in ((0, 64, 6, []), (74, 256, 8, []), (81, 256, 8, []), (0, 64, 6, ['--start-reg']), (81, 256, 8, ['--npt', '2'])):
            outs = []
            for tool in (d / 'tools/hbm_coll_static/argmax_rows.py', HERE / 'argmax_rows.py'):
                o = d / (('old' if tool.parent != HERE else 'new') + f'_{vm_rt}_{len(extra)}')
                subprocess.run([sys.executable, '-I', str(tool), str(o), '--P', str(P), '--vm-rt', str(vm_rt), '--rows', str(rows)] + extra,
                               check=True, capture_output=True, env={'PYTHONPATH': str(A.ROOT)}, cwd=str(HERE))
                outs.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(o.iterdir())})
            assert outs[0] == outs[1], (vm_rt, rows, extra)


def test_pad_mask_literal_matches_taps():
    lit = PT.pad_mask_literal(PT.iss2e_variant())
    assert lit.startswith("1536'h") and lit.endswith('3c0000021e0') and (int(lit[6:], 16) >> 705) & 0b111 == 0b111
    import iss2e_pad
    assert iss2e_pad.hold_literal(iss2e_pad.arg_hold_bits()).endswith('0')
    assert not set(iss2e_pad.arg_hold_bits()) & set(PT.iss2e_variant()['issue_pad_bits'])


def test_variant_masks_have_no_parity_conflict_with_themselves():
    base = PT.iss2e_variant(False, False)
    assert 705 in base['issue_pad_bits'] and 712 not in base['issue_pad_bits']
    sr = PT.iss2e_variant(True, False)
    assert 705 not in sr['issue_pad_bits'] and 13 in sr['issue_pad_bits']
    pr = PT.iss2e_variant(False, True)
    assert 13 not in pr['issue_pad_bits'] and 712 in pr['issue_pad_bits'] and 874 in pr['issue_pad_bits']
    both = PT.iss2e_variant(True, True)
    assert 705 not in both['issue_pad_bits'] and 712 in both['issue_pad_bits']
