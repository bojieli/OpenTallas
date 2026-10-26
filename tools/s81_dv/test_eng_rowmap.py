#!/usr/bin/env python3
"""Checker for tools/s81_dv/eng_rowmap.py (RTL-BUILD-S81, 0dv): every wkv output row (K 4 x 5120 + V 5120) is captured
exactly once, through the RTL capture decode (tools/s81_slice/cap_model.decode), into the leaf that owns the same h
element (ot_s81dv_norm: slice g owns beats g*NVL..), at the documented row / word, without overlapping another vector
or W; W rows cover every (copy, element) once.  Run: python3 tools/s81_dv/test_eng_rowmap.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 's81_dv'))
sys.path.insert(0, str(ROOT / 'tools' / 's81_slice'))
import eng_rowmap as m          # noqa: E402
from cap_model import decode    # noqa: E402


def check(doc, mutate=None):
    errs = []
    for L, lay in doc['layers'].items():
        a0 = lay['A0']
        seen = {}                              # (slice, leaf, row, word) -> what
        hits = {}                              # (vector, e) -> count
        for s in lay['slices']:
            g = s['slice']
            for ph in s['capture_phases']:
                v, cfg = ph['vector'], dict(ph['cfg'])
                if mutate:
                    mutate(g, v, cfg)
                assert int(ph['cfg_d'], 16) == m.cfg_word(ph['cfg']['obase'], 0, 0, 1, ph['cfg']['rbase'], m.SLICE_E)
                # every wkv row that this phase admits (scan the whole row space: catches wrong rbase / rcnt)
                for e in range(m.D):
                    row = m.ROW_BASE[v] + e
                    bad, leaf, _port, addr, _d = decode(row << 13, 0, cfg)
                    if bad:
                        continue
                    hits[(v, e)] = hits.get((v, e), 0) + 1
                    own_g, own_k = e // m.SLICE_E, (e % m.SLICE_E) // m.BEAT
                    if (g, leaf) != (own_g, own_k):
                        errs.append(f'{L} {v} e{e}: lands slice {g} leaf {leaf}, h owner slice {own_g} leaf {own_k}')
                    beat = g * m.NVL + leaf
                    if not (s['h_beats'][0] <= beat <= s['h_beats'][1]) or beat != e // m.BEAT:
                        errs.append(f'{L} {v} e{e}: beat {beat} not the h beat {e // m.BEAT}')
                    row_l, word = addr >> 2, addr & 3
                    if (row_l, word) != (a0 + m.ROW_OFF[v] + (e % 64) // 4, (e % 64) % 4):
                        errs.append(f'{L} {v} e{e}: row/word {row_l}/{word} != documented')
                    if not (a0 <= row_l < a0 + m.REGION_ROWS):
                        errs.append(f'{L} {v} e{e}: row {row_l} outside the region')
                    key = (g, leaf, row_l, word)
                    if key in seen:
                        errs.append(f'{L} {v} e{e}: overlaps {seen[key]}')
                    seen[key] = (v, e)
            for w in s['w_row_writes']:
                j, k = w['copy'], w['leaf']
                for e in range(w['elements'][0], w['elements'][1] + 1):
                    row_l = w['rows'][0] + (e % 64) // 4
                    key = (g, k, row_l, (e % 64) % 4)
                    if row_l > w['rows'][1] or key in seen:
                        errs.append(f'{L} W{j} e{e}: row {row_l} overlap/out of range')
                    seen[key] = (f'W{j}', e)
                    hits[(f'W{j}', e)] = hits.get((f'W{j}', e), 0) + 1
        for v in m.VECS + [f'W{j}' for j in range(m.HC)]:
            for e in range(m.D):
                if hits.get((v, e), 0) != 1:
                    errs.append(f'{L} {v} e{e}: captured {hits.get((v, e), 0)} times')
                    break
        regions = sorted((x['A0'], x['A0'] + m.REGION_ROWS) for x in doc['layers'].values())
        for (a, b), (c, _) in zip(regions, regions[1:]):
            if c < b:
                errs.append(f'layer regions overlap {a}-{b} / {c}')
    return errs


def main():
    doc = m.build()
    errs = check(doc)
    print(f'BASE: {len(errs)} errors')
    for e in errs[:10]:
        print(' ', e)
    # negative controls: the checker must see a wrong rbase, a short rcnt and a wrong obase
    muts = {
        'rbase_off_by_one_beat': lambda g, v, c: c.update(rbase=c['rbase'] + 64) if g == 3 and v == 'K2' else None,
        'rcnt_short': lambda g, v, c: c.update(rcnt=256) if g == 7 and v == 'V' else None,
        'obase_overlap': lambda g, v, c: c.update(obase=c['obase'] - 64) if g == 0 and v == 'K1' else None,
    }
    bad_mut = 0
    for name, f in muts.items():
        n = len(check(doc, f))
        print(f'MUTANT {name}: {"REJECTED" if n else "NOT DETECTED"} ({n} errors)')
        bad_mut += n == 0
    ok = not errs and not bad_mut
    print('PASS eng_rowmap' if ok else 'FAIL eng_rowmap')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
