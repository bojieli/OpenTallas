#!/usr/bin/env python3
"""DRIVE-S81-SVCFIT 10-20: price an attw with fewer hard head groups (time-multiplexed heads) on the S81 token.

Measured base (svc 809c78aa5 full1m, T 640 = 512 selected + 128 window, 16 heads, D 512, 16 svc_rs slices):
  attn.scores = GO -> last fold score 289 = q.k pipeline fill 130 + 159 beat cycles (160 q.k beats a slice:
                40 rows x D / (TD 32 x NT 4) = 4 beats a row; IDX release bench T 128: 32 beats over 31 cycles, same law)
  attn.pv     = pv_sent -> pv_last 596, of which 160 P.V words over 159 cycles (pv_first 6403 .. pv_last 6562)
An attw with G hard groups (4 heads each) instead of 16 runs the same job in 16/G passes: NT = G/4 tiles (DPT = D/NT;
G 8 = NT 2, G 4 = NT 1, both existing engine parameters) or 16/G head passes (G 2).  Every q.k beat and every P.V word
is issued 16/G times, the pipeline fill / fold / landing latencies stay:  scores += 160 (16/G - 1), pv += 160 (16/G - 1).
MTP attn.scores.r0 (3 verify rows, old 315) gets the same delta (MODEL).  Grade: MODEL delta on a measured base.

Composition = the RATEFIX both_p126_t276 scenario (tools/toksim_s81_compose.py, the CAL1/CAL3 base) + one override
record per G (loaded last).  CAL3 rows: CAL3 T (fold.json s140/s148/s201 RATEFIX T_after) + the composer delta
(fixed path, and the solved path that catches attn.pv joining the critical path).

  python3 results/token_pass/svcfit_s81_1020/compose_svcfit.py   # -> results/token_pass/svcfit_s81_1020/summary.json
"""
import importlib.util, json, shutil
from pathlib import Path
H = Path(__file__).resolve().parent
ROOT = H.parents[2]
sp = importlib.util.spec_from_file_location('tc', ROOT / 'tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(sp); sp.loader.exec_module(tc)
RF = ROOT / 'results/token_pass/ratefix_s81_1019'
F = 1.2e9
TAU = 4.159
BEATS, SC, PV, SC_R0 = 160, 289, 596, 315
# CAL3 RATEFIX T (cycles) from claude/s81-cal3-1020 d7a5817e5 results/token_pass/cal2_s81_1020/fold.json
CAL3 = {'s140': dict(ar=F / 1065.9, mtp=F * TAU / 3286.0), 's148': dict(ar=F / 1058.3, mtp=F * TAU / 3268.7),
        's201': dict(ar=F / 1011.1, mtp=F * TAU / 3159.2)}


def override(G):
    d = BEATS * (16 // G - 1)
    note = (f'SVCFIT MODEL: attw with {G} hard head groups = {16 // G} passes; +{d} = {BEATS} beats x ({16 // G} - 1) on the '
            f'measured base (svc 809c78aa5 full1m); latency terms unchanged')
    return dict(cls='SVCFIT', written='2026-10-20', agent_branch='claude/s81-svcfit-1020', note=note, ops=[
        dict(op='attn.scores', dag_cls='hbm', grade='measured-newest-element-RTL', cycles=SC + d, tail_priced=0, note=note),
        dict(op='attn.pv', dag_cls='hbm', grade='measured-newest-element-RTL', cycles=PV + d, note=note),
        dict(op='attn.scores.r0', dag_cls='hbm', grade='measured-newest-element-RTL', cycles=SC_R0 + d, tail_priced=0, note=note)])


def main():
    SC_ = json.loads((RF / 'scenarios.json').read_text())['both_p126_t276']
    rows, base = [], None
    for G in (16, 8, 4, 2, 1):
        d = H / f'g{G}' / 'elements'
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        for f in sorted((ROOT / 'results/token_pass/measured_s81_1019/elements').glob('*.json')):
            shutil.copy(f, d / f.name)
        for f in SC_:
            shutil.copy(RF / 'overrides' / f, d / ('zzz_' + f))
        if G != 16:
            (d / 'zzzz_svcfit_attw.json').write_text(json.dumps(override(G), indent=1) + '\n')
        r = tc.build(d)
        shutil.rmtree(H / f'g{G}')
        w = {k: dict(fixed=r['workloads'][k]['T_cycles_fixed'], solved=r['workloads'][k]['T_cycles_solved']) for k in ('ar', 'mtp')}
        if G == 16:
            base = w
            ref = json.loads((RF / 'both_p126_t276/cycles.json').read_text())['workloads']
            for k in ('ar', 'mtp'):
                assert abs(w[k]['fixed'] - ref[k]['T_cycles_fixed']) < 0.5, (k, w[k], ref[k]['T_cycles_fixed'])
        row = dict(groups=G, passes=16 // G, scores=SC + BEATS * (16 // G - 1), pv=PV + BEATS * (16 // G - 1),
                   dT={k: dict(fixed=round(w[k]['fixed'] - base[k]['fixed'], 1), solved=round(w[k]['solved'] - base[k]['solved'], 1))
                       for k in ('ar', 'mtp')}, cal3={})
        for s, t in CAL3.items():
            row['cal3'][s] = {}
            for k in ('ar', 'mtp'):
                tau = TAU if k == 'mtp' else 1.0
                for m in ('fixed', 'solved'):
                    T1 = t[k] + row['dT'][k][m]
                    row['cal3'][s][f'{k}_{m}'] = dict(tok_s=round(F * tau / T1, 1), pct=round(100 * (t[k] / T1 - 1), 2))
        rows.append(row)
        c = row['cal3']['s140']
        print(f"G{G:2d} ({16 // G} pass) scores {row['scores']} pv {row['pv']} | dT AR {row['dT']['ar']} MTP {row['dT']['mtp']} | "
              f"s140 AR {c['ar_fixed']['tok_s']} ({c['ar_fixed']['pct']}%) solved {c['ar_solved']['tok_s']} ({c['ar_solved']['pct']}%) "
              f"MTP {c['mtp_fixed']['tok_s']} ({c['mtp_fixed']['pct']}%) solved {c['mtp_solved']['tok_s']} ({c['mtp_solved']['pct']}%)")
    (H / 'summary.json').write_text(json.dumps(dict(schema='opentallas.s81_svcfit.rate.v1', cal3_T=CAL3, rows=rows), indent=1) + '\n')


if __name__ == '__main__':
    main()
