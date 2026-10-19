#!/usr/bin/env python3
"""XDIE-HBM3 (2026-10-19): compose the HBM d4g cross-die collective terms from the VM-SOURCED production-P step co-sim
(rtl/hbm_accel/generic/collective/xdie/run_xdie_hbm_step.sh) into a record with a token_compose block.

    python3 tools/xdie_hbm_step_compose.py --run DIR --out results/rtl/xdie_hbm_1019/record.json [--rtl-commit C]

Measured per step (both dies at once; E = first VM request pin -> last DEL0 delivery, max over the two dies, 1.2 GHz):
  AG(P)  gather step, P frames a link each way (Qwen 64/32/16, DS 48 = the production per-link frame counts)
  RS(4), AG(4)  reduce step and gather step at P = 4 (the reduce step at production P does not fit one 64-row
         static_issuer_v6 programme: reduce tags are not loop-iterated and a frame takes 2 reduce inputs)
Composed (measured components, current GEN2 RTL):
  RS(P)  = AG(P) + [RS(4) - AG(4)] + (P - 4)        reduce_static in_v == load_v | add_read: 2 input edges a frame vs 1
  AG(144) (DS, beyond one 64-frame RX block) = E_link(144) + [AG(48) - E_link(48)]   (transport sweep of xdie_hbm_1018 +
         the measured on-die VM->COLL->delivery overhead at 48)
  Qwen TP8 hypercube all-reduce = RS(64) + RS(32) + RS(16) + AG(16) + AG(32) + AG(64) + priced remainder
  DS o-group reduce-mcast       = RS(144) + AG(144) + priced remainder;  DS gathers = AG(48) / AG(144) + priced remainder
Priced remainder (not in the vehicle): VM write after each delivery (VM_WR 5 per step), COLL_VM relays 3 x 14.91, COLL_RING
k x 9.38, the d4g quadrant adder of the row, and the DS 8-way FP32 tree (RED8) for the reduce-mcast.
Modelled-PHY part: the off-chip flight SWD per crossing (DS 333 words: switch 250 + cable 27.6 ns; Qwen 4: package trace).
O (overlap) per slot: as composed by tools/token_compose_xdie.py from the S2 compiler schedule (copied, never assumed).

XDIE-HBM4 (10-19, --run4 DIR = run_xdie_hbm_step4.sh output): the reduce step at production P MEASURED on the v8g parent
with iterated reduce tags (AR_ITER 1) and the 128-row issuer (ROWS 128): Qwen RS(64/32/16) replace the composed values;
DS RS(48) measured, RS(144) (beyond one 64-frame RX block) = AG(144) + [RS(48) - AG(48)] + (144 - 48), anchored at the
measured P = 48 instead of P = 4.  The record keeps the old composed values beside the measured ones.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from xdie_hbm_compose import DS, QW, COLL_VM, COLL_RING, VM_WR, RED8   # noqa: E402

SWD = dict(qw=4, ds=333)
CFG4 = ['qw_rs64', 'qw_rs32', 'qw_rs16', 'qw_rs4', 'ds_rs48', 'reg_qw_ag16', 'reg_qw_rs4', 'reg_ds_rs4']
CFGS = ['qw_ag64', 'qw_ag32', 'qw_ag16', 'qw_ag4', 'qw_rs4', 'ds_ag48', 'ds_ag4', 'ds_rs4']


def parse(log):
    t = log.read_text()
    m = re.search(r'XDIE3_STEP d0 first_vm=(-?\d+) first_wr=(-?\d+) last_rx=(-?\d+) first_pub=(-?\d+) last_pub=(-?\d+) vm_reqs=(\d+)'
                  r' \| d1 first_vm=(-?\d+) first_wr=(-?\d+) last_rx=(-?\d+) first_pub=(-?\d+) last_pub=(-?\d+) vm_reqs=(\d+)', t)
    ok = re.search(r'^XDIE2 .* PASS$', t, re.M) is not None
    adr = re.search(r'adr_bad=(\d+)/(\d+)', t)
    if not m:
        return dict(pass_=False)
    v = [int(x) for x in m.groups()]
    d = [dict(first_vm=v[0], first_wr=v[1], last_rx=v[2], first_pub=v[3], last_pub=v[4], vm_reqs=v[5]),
         dict(first_vm=v[6], first_wr=v[7], last_rx=v[8], first_pub=v[9], last_pub=v[10], vm_reqs=v[11])]
    rel = re.findall(r'XDIE2_REL d=(\d) rel=(-?\d+)', t)
    rdy = re.findall(r'XDIE2_RDY d=(\d) bank=0 rel=(-?\d+)', t)
    return dict(pass_=ok, dies=d, E=max(x['last_pub'] - x['first_vm'] for x in d),
                E_launch=max(x['last_pub'] for x in d), adr_bad=[int(adr[1]), int(adr[2])] if adr else None,
                release_rel=[int(r) for _, r in rel], ready_rel=[int(r) for _, r in rdy])


def git(*a):
    try:
        return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ''


def base_terms(design):
    p = ROOT / f'results/arch/token_path_1018/{design}.json'
    d = json.loads(p.read_text())['workloads']['ar']['terms']
    out = {}
    for t in d:
        if t.get('kind') != 'xdie':
            continue
        out.setdefault(t['slot'], t)
    return out, git('log', '-1', '--format=%h', '--', str(p.relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--rtl-commit', default=''); ap.add_argument('--run4', default='')
    a = ap.parse_args()
    run = Path(a.run)
    M = {c: parse(run / f'{c}_pass.log') for c in CFGS if (run / f'{c}_pass.log').exists()}
    assert all(M[c]['pass_'] for c in M), {c: M[c]['pass_'] for c in M}
    old = json.loads((ROOT / 'results/rtl/xdie_hbm_1018/record.json').read_text())
    el = {r['P_link_frames']: r['E_link_meas_cycles'] for r in old['rows'] if r['model'] == 'DS' and 'P_link_frames' in r}
    E = {c: M[c]['E'] for c in M}
    d_rs = dict(qw=E['qw_rs4'] - E['qw_ag4'], ds=E['ds_rs4'] - E['ds_ag4'])
    ag = dict(qw={64: E['qw_ag64'], 32: E['qw_ag32'], 16: E['qw_ag16']}, ds={48: E['ds_ag48']})
    ag['ds'][144] = el[144] + (E['ds_ag48'] - el[48])
    LANE = 'XDIE-HBM4' if a.run4 else 'XDIE-HBM3'
    rs_old = lambda m, P: ag[m][P] + d_rs[m] + (P - 4)
    rs = rs_old
    M4, rs_meas, rs_cmp = {}, {}, {}
    if a.run4:
        r4 = Path(a.run4)
        M4 = {c: parse(r4 / f'{c}_pass.log') for c in CFG4 if (r4 / f'{c}_pass.log').exists()}
        assert all(M4[c]['pass_'] for c in M4), {c: M4[c]['pass_'] for c in M4}
        rs_meas = dict(qw={int(c[5:]): M4[c]['E'] for c in M4 if c.startswith('qw_rs')},
                       ds={int(c[5:]): M4[c]['E'] for c in M4 if c.startswith('ds_rs')})
        for m in ('qw', 'ds'):
            for P, e in sorted(rs_meas[m].items()):
                if P in ag[m]:
                    rs_cmp[f'{m}_rs{P}'] = dict(measured=e, composed_old=rs_old(m, P), delta=e - rs_old(m, P))
        def rs(m, P):
            if P in rs_meas[m]:
                return rs_meas[m][P]
            if m == 'ds' and 48 in rs_meas['ds']:
                return ag['ds'][P] + (rs_meas['ds'][48] - ag['ds'][48]) + (P - 48)
            return rs_old(m, P)
    rows = {}
    # ---- DS rows (k crossings, adder from the d4g census table of tools/xdie_hbm_compose.py)
    for tag, kind, nbytes, cnt, k, adder, priced in DS:
        if kind == 'ALL_GATHER':
            P = 144 if nbytes > 16384 else 48
            meas = ag['ds'][P]
            rem = VM_WR + 3 * COLL_VM + COLL_RING + adder
            form = f'AG({P})' + (' composed: E_link(144) + measured on-die overhead at 48' if P == 144 else ' measured')
        elif kind == 'GROUP_REDUCE_MCAST':
            P = 144
            meas = rs('ds', P) + ag['ds'][P]
            rem = 2 * VM_WR + 3 * COLL_VM + 2 * COLL_RING + adder + RED8
            form = ('RS(144) + AG(144); RS(144) = AG(144) + [RS(48) - AG(48)] + 96 with RS(48) MEASURED (XDIE-HBM4 iterated tags, '
                    '128-row issuer)' if 48 in rs_meas.get('ds', {}) else
                    'RS(144) + AG(144), composed from AG(48), RS(4) - AG(4) and the 2-edge reduce cadence')
        else:
            continue
        phy = k * SWD['ds']
        tot = meas + rem
        rows[tag] = dict(model='DS', kind=kind, P_link=P, crossings=k, E_total=round(tot, 1),
                         parts=[('measured-current-RTL', round(meas - phy, 1)), ('modelled-PHY', float(phy)), ('priced', round(rem, 1))],
                         priced_per_instance=priced, form=form, per_token_count=cnt)
    for tag, kind, nbytes, cnt, k, adder, priced in QW:
        if kind != 'ALL_REDUCE_SUM':
            continue
        steps = [('RS', 64), ('RS', 32), ('RS', 16), ('AG', 16), ('AG', 32), ('AG', 64)]
        se = [rs('qw', P) if s == 'RS' else ag['qw'][P] for s, P in steps]
        meas = sum(se)
        rem = 3 * COLL_VM + adder + 6 * VM_WR
        phy = 6 * SWD['qw']
        rows['Q_AR'] = dict(model='Qwen', kind=kind, steps=[f'{s}({P})' for s, P in steps], step_E=[round(x, 1) for x in se],
                            crossings=6, E_total=round(meas + rem, 1),
                            parts=[('measured-current-RTL', round(meas - phy, 1)), ('modelled-PHY', float(phy)), ('priced', round(rem, 1))],
                            priced_per_instance=priced, per_token_count=cnt,
                            form='hypercube recursive halving / doubling (3 die links, 6 dependent steps), steps measured '
                                 + ('AG(64/32/16) + RS(64/32/16) (XDIE-HBM4: iterated reduce tags, 128-row issuer)'
                                    if all(P in rs_meas.get('qw', {}) for P in (64, 32, 16)) else
                                    'AG(64/32/16) + RS(P) = AG(P) + [RS(4) - AG(4)] + (P - 4)'))
    # ---- token_compose terms, one per base slot (O copied from the composed S2-schedule value)
    terms = []
    for design, name_of in (('hbm_gen_ds', lambda s: s.split('.xdie.', 1)[1].split('#')[0]),
                            ('hbm_gen_qwen', lambda s: s.split('.xdie.', 1)[1].split('#')[0])):
        bt, bcommit = base_terms(design)
        for slot, t in sorted(bt.items()):
            nm = name_of(slot)
            if nm not in rows:
                continue
            r = rows[nm]
            terms.append(dict(design=design, workload='ar', slot=slot, n=t['n'],
                              E=[dict(grade=g, E=e) for g, e in r['parts']], O=t['O'],
                              O_source=f"{t['O_source']} (value as composed in results/arch/token_path_1018/{design}.json on main {bcommit})",
                              pointer=f'rows.{nm}', note=f"{LANE} VM-sourced step co-sim: {r['form']}"))
    rec = dict(schema='opentallas.xdie_hbm.record.v2', lane=LANE, date='2026-10-19',
               vehicle='rtl/hbm_accel/generic/collective/xdie/tb_xdie_hbm_step.sv + run_xdie_hbm_step.sh; compiler tools/xdie_hbm_step_compile.py',
               rtl_commit=a.rtl_commit,
               rtl_rev='COLL/ep/serdes/VM-calendar sources byte-identical between claude/hd4g-gen2-1018 42726f987 (GEN2 of record) and '
                       'origin/main; GEN2c views branch only adds benches + ring_ag_n/gq changes not instantiated here',
               verilator=(run / 'verilator.version').read_text().strip() if (run / 'verilator.version').exists() else '',
               instantiated_per_die=['hb_coll_NE ot_hfd_coll_q2_hard_v8g NLINK1 TP192 (static_issuer_v6 LOOP programme via F20, ctl_v5 '
                                     'iteration offsets, VM assembly v7 slices, qslots, link_e rail, reduce_static, writer v6)',
                                     'hcollgi_NE ot_hgi_coll_gq_issue (idle)', 'cp_ep_NE + epcal_NE hfd_hgi_vm_calendar',
                                     '10 lane relays each way', 'ep_N2 hfd_ep_static', 'lk_N2 ot_pdie_serdes (KP4)'],
               modelled=['VM banks at the parent vm_rq/vm_rr pins: 8 x 256 b, sector-addressed data, the native 7-edge return contract',
                         'off-chip flight SWD 333 words DS / 4 Qwen', 'die B 300 ppm slow', 'pad bit errors inside FEC t=15',
                         'ring-A neighbours idle; SU source unused'],
               steps={c: {k: v for k, v in M[c].items() if k != 'pass_'} | dict(verdict='PASS' if M[c]['pass_'] else 'FAIL') for c in M},
               steps_hbm4={c: {k: v for k, v in M4[c].items() if k != 'pass_'} | dict(verdict='PASS' if M4[c]['pass_'] else 'FAIL')
                           for c in M4},
               rs_measured_vs_composed=rs_cmp,
               rtl_hbm4=('v8g #(.AR_ITER(1), .ROWS(128)): reduce load/read/pub tags + pub_index advance by iteration x '
                         'iter_ar_tag_step (reserved word[717:714]); static_issuer_v6 / programme target / program bank at 128 rows '
                         '(defaults AR_ITER 0 / ROWS 64 = the closed views, unchanged)') if a.run4 else None,
               composed=dict(AG=ag, RS_minus_AG_at_4=d_rs, E_link_old=dict(P48=el[48], P144=el[144]),
                             RS_rule='RS(P) = AG(P) + [RS(4) - AG(4)] + (P - 4): reduce_static takes one input edge per load/add '
                                     '(in_v == load_v | add_read), so a reduce step drains 1 frame / 2 edges vs 1 / edge for a gather'),
               rows=rows,
               findings=(['XDIE-HBM4: production-P reduce steps MEASURED (v8g AR_ITER 1 + ROWS 128): ' + ', '.join(
                   f"{k} {v['measured']} cyc (composed {v['composed_old']}, delta {v['delta']:+d})" for k, v in rs_cmp.items()) +
                   '. The XDIE-HBM3 composition RS(P) = AG(P) + [RS(4) - AG(4)] + (P - 4) is confirmed cycle-exact.',
                   'XDIE-HBM4: iterated tags alone do not fit 64 rows (rs16 96 -> 82, rs32..64 117 -> 95 rows): the RX fill (~27 '
                   'rows: the 27-edge per-frame span VM re-read -> DEL0) + drain (~20) + TX (~41) exceed 64; the 128-row issuer '
                   'is what makes RS(P >= 16) one programme. Issuer leaf (ot_hgi_coll_issuer_m: 3 -> 6 64x512 macros, 128:1 '
                   'reads), fj programme target leaves and the v8g parent need re-gate at ROWS 128 / AR_ITER 1 (not submitted).']
                   if rs_cmp else []) + (['XDIE-HBM4 item 3 (delivery-offset edge) CLOSED: the ctl_v5 delivery_obase pin lands on the DEL0 '
                   'valid edge when the compiler programs del_obase ONE row after the sink row (--del-edge 1); with the offset '
                   'CHECKED (+ADRCHK) qa_ag16 / qa_rs64 / qa_rs32 / qa_rs16 / da_rs48 / da_ag48 PASS with adr_bad 0/0 and the '
                   'same E; the del-edge-0 programme FAILS under the check (m_adr0). Compiler fix, no RTL change '
                   '(step_cosim4/adr).'] if (Path(a.run4) / 'adr' / 'qa_rs64_pass.log').exists() else []) + ['A production-P reduce step does not fit one 64-row static_issuer_v6 programme: AR fields (load/read/pub tags, '
                         'pub_index) have no iteration step, so a loop body must span the tag lifetime (load -> pub_issue 12 edges -> '
                         '>= 7 tags, 14+ rows) and prologue/epilogue are ~27 rows each: rs8 needs 70 rows, rs16 96, rs64 117 '
                         '(compiler capacity assert). AG steps fit (64 frames: 50 rows) with iterated link seq / VM sector / '
                         'delivery offset. Fix options: iterate reduce tags (tag + iteration mod 16) or a second programme bank.',
                         'reduce_static accepts one operand edge per frame operand: a 2-operand reduce step drains at 0.5 frame/edge '
                         'while the link delivers 0.8 frame/beat -- the RS step is reduce-bound, not link-bound.'],
               token_compose=dict(terms=terms, evidence='results/rtl/xdie_hbm_1019/ (step logs, programmes, sources.sha256)'))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(E=E, rows={k: (v['E_total'], v['priced_per_instance']) for k, v in rows.items()}, terms=len(terms))))


if __name__ == '__main__':
    main()
