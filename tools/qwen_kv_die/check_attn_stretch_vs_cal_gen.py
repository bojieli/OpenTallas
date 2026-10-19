#!/usr/bin/env python3
"""KVJ-E2 (coordinator 10-17 decision 4): the attention calendar the KV static programme compiler emits for every
context T = 1..8192 against KVJ-B's N1 generator qkd_attn_cal_gen (claude/kvj-b-1017 58f9ebdbb).

    check_attn_stretch_vs_cal_gen.py --gold GEN_BENCH_DIR/gold_g1_rx2.hex --report die/report.json --out receipt.json

GOLD is the table run_cal_gen_bench.sh writes and the generator RTL matches exhaustively (CALGEN PASS: every T, every
field, tx_first, end): {T16, cal176 (R P1 P0 PV_START HUB_PUB HUB_RECIP HUB_Z HUB_LMAX Z LMAX EXP), tx_first16, end16}.
The report gives the link-fixed attention words (compiled_rx_cmd / compiled_tx_first / compiled_end, service_end).

Law checked (decision 4: the service ends on the link's fixed RESULT slot; R stretches per context):
  component profile (QK age 34, RL 19): every field but R equals the generator; R >= the generator's R;
                                        PV_START + R + 49 == service_end; generator tx_first / end <= the fixed words.
  die profile (die ages):  LMAX..HUB_PUB = generator + (QK_ISSUE_AGE - 34); P0 / P1 = generator + (RL - 19);
                           PV_START = the minimal start of those fields (attn_calendar law); R stretched as above.
The generator emits the minimal R and a per-T tx_first / end; the production N1 needs R = service_end - 49 - PV_START
and the fixed words (reported under rtl_delta).

KVJ-SMALL 10-17: the generator now has STRETCH=1 (D_QK, D_RL, SERVICE_END).  With --stretch-gold (the bench's
gold_s_<profile>.hex tables) and --bench-receipt (run_cal_gen_bench.sh receipt.json), the check also requires every
stretched row == attention_calendar(T, profile, service_end) with the fixed link words, and the bench's STRETCH runs
(mut 0) CALGEN PASS: then RTL == compiler for every T and rtl_delta is closed."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as C  # noqa: E402

AC = C.AC
CHAIN = ('LMAX', 'EXP', 'Z', 'HUB_LMAX', 'HUB_Z', 'HUB_RECIP', 'HUB_PUB')


def gold_rows(path):
    rows = {}
    for line in Path(path).read_text().split():
        v = int(line, 16)
        T = v >> 208
        cal = (v >> 32) & ((1 << 176) - 1)
        f = {n: (cal >> (16 * (10 - i))) & 0xffff for i, n in enumerate(AC.FIELDS)}
        rows[T] = dict(cal=f, tx_first=(v >> 16) & 0xffff, end=v & 0xffff)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--gold', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--ages', type=Path, default=C.ROOT / C.AGES)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--stretch-gold', type=Path, nargs='*', default=[], help='gold_s_<profile>.hex (profile from the name)')
    ap.add_argument('--bench-receipt', type=Path)
    a = ap.parse_args()
    rep = json.loads(a.report.read_text())
    att = rep['attention']
    se, tx, en, rx = att['service_end'], att['compiled_tx_first'], att['compiled_end'], att['compiled_rx_cmd']
    gold = gold_rows(a.gold)
    if sorted(gold) != list(range(1, 8193)):
        raise SystemExit('gold table must hold T = 1..8192')
    prs = dict(component=C.profile('component'), die=C.profile('die', json.loads(a.ages.read_text())))
    bad, stats = [], {}
    for name, pr in prs.items():
        st = dict(contexts=0, r_stretch_min=None, r_stretch_max=None, gen_tx_first_max=0, gen_slack_min=None)
        for T, g in gold.items():
            gf = g['cal']
            m = C.attention_calendar(T, pr)                 # minimal calendar of the profile
            s = C.attention_calendar(T, pr, se)             # the compiled (stretched) calendar
            want = dict(gf)
            for f in CHAIN:
                want[f] += pr['d_qk']
            want['P0'] += pr['d_rl']
            want['P1'] += pr['d_rl']
            if name == 'component' and m != gf:
                bad.append(dict(profile=name, T=T, why='minimal calendar differs from the generator'))
            for f in CHAIN + ('P0', 'P1'):
                if s[f] != want[f]:
                    bad.append(dict(profile=name, T=T, field=f, compiled=s[f], generator_law=want[f]))
            pv = max(want['EXP'] + AC.pv_after_exp_w16(T), want['HUB_PUB'] + AC.RZ_MARGIN - max(want['P0'], want['P1']))
            if s['PV_START'] != pv or (name == 'component' and s['PV_START'] != gf['PV_START']):
                bad.append(dict(profile=name, T=T, field='PV_START', compiled=s['PV_START'], law=pv))
            if AC.service_cycles(s) != se or s['PV_START'] + s['R'] + 49 != se or s['R'] < m['R'] or s['R'] < max(s['P0'], s['P1']):
                bad.append(dict(profile=name, T=T, why='service does not end on the fixed RESULT slot', R=s['R']))
            if g['tx_first'] > tx or g['end'] > en or g['end'] != g['tx_first'] + 34:
                bad.append(dict(profile=name, T=T, why='generator link ages exceed the fixed words', gen=[g['tx_first'], g['end']]))
            d = s['R'] - m['R']
            st['contexts'] += 1
            st['r_stretch_min'] = d if st['r_stretch_min'] is None else min(st['r_stretch_min'], d)
            st['r_stretch_max'] = d if st['r_stretch_max'] is None else max(st['r_stretch_max'], d)
            st['gen_tx_first_max'] = max(st['gen_tx_first_max'], g['tx_first'])
            sl = se - AC.service_cycles(m)
            st['gen_slack_min'] = sl if st['gen_slack_min'] is None else min(st['gen_slack_min'], sl)
        stats[name] = st
    stretch = None
    if a.stretch_gold:
        stretch = dict(tables={}, bench=None)
        for p in a.stretch_gold:
            name = p.stem.split('gold_s_')[-1]
            rows, nbad = gold_rows(p), 0
            if sorted(rows) != list(range(1, 8193)):
                raise SystemExit(f'{p}: stretch gold must hold T = 1..8192')
            for T, g in rows.items():
                if g['cal'] != C.attention_calendar(T, prs[name], se) or g['tx_first'] != tx or g['end'] != en:
                    nbad += 1
                    bad.append(dict(profile=name, T=T, why='stretch gold row differs from the compiler'))
            stretch['tables'][name] = dict(contexts=len(rows), mismatches=nbad)
        if a.bench_receipt:
            br = json.loads(a.bench_receipt.read_text())
            sr = [r for r in br['runs'] if r.get('stretch')]
            ok = [r for r in sr if r['mut'] == 0 and r['result'].startswith('CALGEN PASS')]
            caught = [r for r in sr if r['mut'] != 0 and r['result'].startswith('CALGEN FAIL')]
            stretch['bench'] = dict(verdict=br['verdict'], commit=br['commit'], dirty=br['dirty'], runs=sr)
            for name in stretch['tables']:
                if not any(r['stretch'] == name for r in ok):
                    bad.append(dict(profile=name, why='no STRETCH CALGEN PASS run for this profile'))
            if len(caught) != len([r for r in sr if r['mut'] != 0]):
                bad.append(dict(why='a STRETCH mutant was not caught'))
        else:
            bad.append(dict(why='--stretch-gold without --bench-receipt'))
    rec = dict(schema='opentallas.qwen_kv_static.attn_stretch_vs_cal_gen.v1', verdict='PASS' if not bad else 'FAIL',
               generator='rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv (claude/kvj-b-1017 58f9ebdbb), exhaustive bench '
                         'gold (CALGEN PASS) G3S2=1 RX_CMD=2',
               link_words=dict(compiled_rx_cmd=rx, compiled_tx_first=tx, compiled_end=en, service_end=se),
               checked=dict(contexts=8192, profiles=list(prs)), stats=stats, mismatches=bad[:50], mismatch_count=len(bad),
               stretch_rtl=stretch,
               rtl_delta=('CLOSED: qkd_attn_cal_gen STRETCH=1 (D_QK, D_RL, SERVICE_END) == attention_calendar(T, profile, '
                          'service_end) and the fixed link words for every T (stretch_rtl)') if stretch and stretch['bench'] else
                         'qkd_attn_cal_gen emits the minimal R (= P0) and tx_first / end per T.  For the static link it must '
                         'emit R = SERVICE_END - 49 - PV_START and the constant tx_first / end; with the die ages it also '
                         'needs LMAX..HUB_PUB + (QK_ISSUE_AGE - 34) and P0 / P1 + (RL - 19) before the PV_START max '
                         '(parameters D_QK, D_RL, SERVICE_END): owner KVJ-B successor.')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], json.dumps(stats), 'mismatches', len(bad))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
