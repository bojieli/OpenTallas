#!/usr/bin/env python3
"""TOK-HBM-7 2026-10-29: IDXN multirow row pitch, priced on the compiled IDX frame with the bound reader round trip.

The IDXN calendar (rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv) launches row r of an N-row INDEX record r x pitch edges
after start and routes each instruction class from ONE stream per edge (collision = fault). The frame programme is
tools/hbm_idx_static_calendar.py, whose PIN table shifts every query/scorer/selector/link field by the reader round trip
vm_rt (donor shell 2; actual bound reader 171 SW/SE/NE, 173 NW). This tool derives the smallest legal pitch from:
  CLASS   OPR / QEM / KEY / PRE / LIN / LOUT never on one edge for two rows; SEL per selector (row mod 4)
  SCORER  the hslices hold ONE query: row r+1's first head emit >= row r's last key beat + G2MIN (23)
  DRAIN   ot_hbm_idx_query_static clears its seen bits on row_start and FAULTS if the clear meets block_v/emit_v/qv,
          and emit of an unseen head faults: row r+1's clear must land after row r's last head emit. row_start leaves
          qctl at the launch edge (= instruction -3 of that row) unless ot_hnx_idxq_qctl ROW_CLEAR_DELAY = D moves it.
  CLEAR   with D > 0 the clear must also land before row r+1's first block reaches the query core.
Price = 5 extra row boundaries x 8 INDEX records a pass (actual image a122 census) x (drain pitch - class pitch).

  idx_row_pitch_price.py OUT.json [--vm-rt 171 173] [--programme-dir DIR]
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G2MIN = 23
S = 4
LAUNCH_TO_INS0 = 3          # ot_hnx_idxn_calendar: a stream issues instruction 0 three edges after its launch
DONOR_RT = 2


def load_compiler():
    spec = importlib.util.spec_from_file_location('hbm_idx_static_calendar', ROOT / 'tools/hbm_idx_static_calendar.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def classes(word, F):
    g = lambda k: (word >> F[k][0]) & ((1 << F[k][1]) - 1)
    out = set()
    if g('weight') or g('query'):
        out.add('OPR')
    if g('head'):
        out.add('QEM')
    if g('beat'):
        out.add('KEY')
    if (word >> 6) & ((1 << 14) - 1):
        out.add('SEL')
    if g('flush'):
        out.add('LIN')
    elif g('link'):
        out.add('LOUT')
    return out


def frame(C, vm_rt, vm_period):
    C.PIN_TABLES['bound'] = dict(C.PIN_TABLES['registered'], vm_rt=vm_rt)
    prog, meta = C.compile_program('bound', vm_period=vm_period)
    occ = {}
    for n, w in enumerate(prog):
        for c in classes(w, C.FIELDS):
            occ.setdefault(c, set()).add(n)
    occ['PRE'] = {n - 1 for n in occ['KEY']}
    return prog, meta, occ


def first_block_at_q(meta, occ):
    """Instruction-equivalent edge at which the row's first operand block reaches the query core (pin-relative to QEM)."""
    q_slots = sorted(e for e in meta['vm_request_instruction_edges'])
    # the compiler aligns query-tile fields so that the q core sees the historical timeline: a query slot at historical h
    # yields its block at the q core at instruction h + shift_q + 9 (core face n+8, block_v +1), a lower bound used only
    # to check that a delayed clear stays ahead of the next row's data
    return q_slots[1] + meta['calendar_shift']['q'] + 9


def legal(occ, p, n_rows, drain_delay, meta):
    for j in range(1, n_rows):
        d = j * p
        for c in ('OPR', 'QEM', 'KEY', 'PRE', 'LIN', 'LOUT'):
            if occ.get(c, set()) & {x + d for x in occ.get(c, set())}:
                return False, f'class {c} rows r/r+{j}'
        if j % S == 0 and occ['SEL'] & {x + d for x in occ['SEL']}:
            return False, f'selector rows r/r+{j}'
    if min(occ['QEM']) + p < max(occ['KEY']) + G2MIN:
        return False, 'scorer query reuse (G2MIN)'
    if drain_delay is not None:
        clear = p - LAUNCH_TO_INS0 + drain_delay          # row r+1 clear, row-r instruction units
        if clear <= max(occ['QEM']):
            return False, 'query drain: clear before last head emit of the previous row'
        if drain_delay and clear >= p + first_block_at_q(meta, occ):
            return False, 'delayed clear after next row first block'
    return True, ''


def min_pitch(occ, n_rows, drain_delay, meta):
    for p in range(1, 4096):
        ok, _ = legal(occ, p, n_rows, drain_delay, meta)
        if ok:
            return p
    raise SystemExit('no legal pitch')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--vm-rt', type=int, nargs='+', default=[171, 173])
    ap.add_argument('--vm-period', type=int, nargs='+', default=[1, 2])
    ap.add_argument('--n-rows', type=int, default=6)
    ap.add_argument('--records', type=int, default=8, help='IDX.INDEX records a pass (a122 census: 8 N6)')
    ap.add_argument('--programme-dir', help='write calendar_instructions_rt<R>_vp<P>.hex for the RTL bench')
    a = ap.parse_args()
    C = load_compiler()
    res = dict(tool='tools/hbm_next/idx_row_pitch_price.py', g2min=G2MIN, selectors=S, n_rows=a.n_rows,
               records_per_pass=a.records, cases={})
    for vp in a.vm_period:
        _, _, docc = frame(C, DONOR_RT, vp)
        donor_p = min_pitch(docc, a.n_rows, 0, None)
        for rt in a.vm_rt:
            prog, meta, occ = frame(C, rt, vp)
            p_class = min_pitch(occ, a.n_rows, None, meta)
            p_drain0 = min_pitch(occ, a.n_rows, 0, meta)
            D = rt - DONOR_RT
            p_drainD = min_pitch(occ, a.n_rows, D, meta)
            F = len(prog)
            k = f'rt{rt}_vp{vp}'
            res['cases'][k] = dict(
                vm_rt=rt, vm_period=vp, frame=F, shift=meta['calendar_shift'],
                spans={c: [min(v), max(v)] for c, v in sorted(occ.items())},
                donor_pitch=donor_p, class_pitch=p_class, pitch_clear_at_launch=p_drain0,
                row_clear_delay=D, pitch_clear_delayed=p_drainD,
                record_edges_clear_at_launch=(a.n_rows - 1) * p_drain0 + F,
                record_edges_clear_delayed=(a.n_rows - 1) * p_drainD + F,
                pass_cost_clear_at_launch=a.records * (a.n_rows - 1) * (p_drain0 - p_class),
                pass_cost_clear_delayed=a.records * (a.n_rows - 1) * (p_drainD - p_class))
            if a.programme_dir:
                d = Path(a.programme_dir)
                d.mkdir(parents=True, exist_ok=True)
                (d / f'calendar_instructions_{k}.hex').write_text(''.join(f'{w:08x}\n' for w in prog))
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    for k, v in res['cases'].items():
        print(k, 'F', v['frame'], 'class', v['class_pitch'], 'clear@launch', v['pitch_clear_at_launch'],
              'D', v['row_clear_delay'], 'clear+D', v['pitch_clear_delayed'],
              'pass+', v['pass_cost_clear_at_launch'], '->', v['pass_cost_clear_delayed'])


if __name__ == '__main__':
    main()
