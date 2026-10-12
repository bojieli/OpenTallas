#!/usr/bin/env python3
"""Gate link_credit_rtt (unified ledger 2026-10-07): the full-rate hub successor ot_qwen_die_hub_fr over the actual
54/55-station forwarded TMR link (rtl/test/tb_qwen_link_fullrate.sv) plus its 4-link scoreboard bench
(rtl/test/tb_qwen_die_hub_fr.sv).  Verilator 5.050 is the primary simulator; Icarus re-runs the positives.
Cases: positives at CR=128 (54 and 55 hops, free-running and consumer back-pressure), a credit sweep CR=4..256 at 54
hops (CR=4 = the predecessor's window), four negatives that must end in the named native fault, and the 4-link
scoreboard positive/negative.  Writes <out>/result.json; exit 1 unless every case qualifies.
usage: qwen_link_fullrate_gate.py --out DIR [--n 4096] [--sim verilator|iverilog|both] [--only CASE ...]"""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ['rtl/physical/ot_qwen_die_hub_fr.sv', 'rtl/physical/ot_qwen_die_cdc_ch.sv', 'rtl/lib/ot_async_fifo.sv',
       'rtl/lib/ot_reset_sync.sv']
LINK = HUB + ['rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv']
TB_LINK, TB_HUB = 'rtl/test/tb_qwen_link_fullrate.sv', 'rtl/test/tb_qwen_die_hub_fr.sv'
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
NEG_CAUSE = {1: 'B cause[1] receive-buffer overflow AND A cause[3] credit counter below zero',
             2: 'A cause[3] link credit overflow', 3: 'A cause[4] ar credit overflow', 4: 'A cause[0] x3 skid overflow'}
RX = re.compile(r'EPOCH (\d+) hops=(\d+) CR=(\d+) delivered=(\d+)/(\d+) credit_rtt=(\d+)/(\d+) rate_milli=(\d+)/(\d+) '
                r'span=(\d+)/(\d+) stalls=(\d+)/(\d+) max_inflight=(\d+)/(\d+) cycles=(\d+)')
KEYS = ['epoch', 'hops', 'CR', 'delivered_a', 'delivered_b', 'credit_rtt_a', 'credit_rtt_b', 'rate_milli_a',
        'rate_milli_b', 'span_a', 'span_b', 'stalls_a', 'stalls_b', 'max_inflight_a', 'max_inflight_b', 'cycles']


def cases(n):
    c = []
    for hops in (54, 55):
        c.append(dict(case=f'pos_h{hops}_cr128', tb=TB_LINK, p=dict(HOPS=hops, N=n, CR=128), kind='pos'))
    c.append(dict(case='pos_h54_cr128_bp', tb=TB_LINK, p=dict(HOPS=54, N=n, CR=128, BP=1), kind='pos'))
    for cr in (4, 8, 16, 32, 64, 256):
        c.append(dict(case=f'sweep_h54_cr{cr}', tb=TB_LINK, p=dict(HOPS=54, N=min(n, 1024), CR=cr), kind='pos'))
    for neg in (1, 2, 3, 4):
        c.append(dict(case=f'neg{neg}_h54_cr128', tb=TB_LINK, p=dict(HOPS=54, N=n, CR=128, NEG=neg), kind='neg', neg=neg))
    c.append(dict(case='hub4_pos', tb=TB_HUB, p=dict(N=600), kind='hubpos'))
    c.append(dict(case='hub4_neg', tb=TB_HUB, p=dict(N=600, NEG=1), kind='hubneg'))
    return c


def build_run(sim, case, tmp, src):
    top = Path(case['tb']).stem
    files = [str(ROOT / case['tb'])] + [str(src / s) for s in (LINK if case['tb'] == TB_LINK else HUB)]
    d = Path(tmp) / f"{case['case']}_{sim}"
    if sim == 'verilator':
        cmd = [VERILATOR, '--binary', '--timing', '-j', '8', '-Wno-fatal', '-Wno-lint', '-Wno-style', '--top-module', top,
               '-Mdir', str(d)] + [f'-G{k}={v}' for k, v in case['p'].items()] + files
        exe = [str(d / f'V{top}')]
    else:
        d.mkdir(parents=True)
        cmd = ['iverilog', '-g2012', '-s', top, '-o', str(d / 'sim')] + [f'-P{top}.{k}={v}' for k, v in case['p'].items()] + files
        exe = ['vvp', '-n', str(d / 'sim')]
    comp = subprocess.run(cmd, capture_output=True, text=True)
    if comp.returncode:
        return None, comp.stdout + comp.stderr
    r = subprocess.run(exe, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def judge(case, rc, log):
    k = case['kind']
    if rc is None:
        return False
    if k == 'pos':
        p = case['p']
        ok = rc == 0 and f"PASS link_fullrate HOPS={p['HOPS']} CR={p['CR']} checks={4 * p['N']} epochs=2" in log
        return ok
    if k == 'neg':
        return rc != 0 and f"EXPECTED_FAULT NEG={case['neg']}" in log and 'DATA_MISMATCH' not in log
    if k == 'hubpos':
        return '\nPASS hub ar_words=2400 x3_words=2400' in '\n' + log
    if k == 'hubneg':
        return 'FAIL hub NEG=1' in log and 'fault 1' in log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--n', type=int, default=4096)
    ap.add_argument('--sim', default='both', choices=['verilator', 'iverilog', 'both'])
    ap.add_argument('--source-root', type=Path, default=ROOT)
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sims = ['verilator', 'iverilog'] if a.sim == 'both' else [a.sim]
    rows = []
    with tempfile.TemporaryDirectory(prefix='qwen-linkfr-') as tmp:
        for c in cases(a.n):
            if a.only and c['case'] not in a.only:
                continue
            for sim in sims:
                if sim == 'iverilog' and c['kind'] == 'pos' and c['case'].startswith('sweep') and a.sim == 'both':
                    continue          # the sweep is a rate measurement; Verilator carries it
                rc, log = build_run(sim, c, tmp, a.source_root)
                (a.out / f"{c['case']}.{sim}.log").write_text(log)
                row = dict(case=c['case'], sim=sim, params=c['p'], kind=c['kind'], returncode=rc,
                           qualified=judge(c, rc, log), log_sha256=hashlib.sha256(log.encode()).hexdigest(),
                           epochs=[dict(zip(KEYS, map(int, m))) for m in RX.findall(log)])
                if c['kind'] == 'neg':
                    row['expected_native_fault'] = NEG_CAUSE[c['neg']]
                    m = re.search(r'NATIVE_FAULT .*', log)
                    row['observed'] = m.group(0) if m else None
                rows.append(row)
                print(f"{row['case']:<22} {sim:<9} qualified={row['qualified']} "
                      + ' '.join(f"rate={e['rate_milli_a']/1000:.3f} rtt={e['credit_rtt_a']} stalls={e['stalls_a']} infl={e['max_inflight_a']}"
                                 for e in row['epochs'][:1]) + (f" {row.get('observed')}" if c['kind'] == 'neg' else ''), flush=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res = dict(schema='opentallas.qwen_link_fullrate.gate.v1', gate='link_credit_rtt',
               pass_all=all(r['qualified'] for r in rows), cases=rows,
               scope='Two ot_qwen_die_hub_fr endpoints (one active lane) over 54/55 actual ot_qwen_die_link_fwd_full_tmr '
                     'stations with independently phased equal-rate clocks; N words each way per drained epoch x 2 '
                     'cold epochs; exact order/value scoreboard; rate = (N-1)/(last-first delivery) in receiver cycles. '
                     'Negatives must end in the named native fault cause. The 4-link scoreboard bench drives all four '
                     'lanes with random selects and random ar back-pressure.',
               source_sha256={s: sha(a.source_root / s) for s in LINK},
               bench_sha256={TB_LINK: sha(ROOT / TB_LINK), TB_HUB: sha(ROOT / TB_HUB)},
               tool_sha256=sha(__file__), simulators=sims, n=a.n)
    (a.out / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
    print('PASS_ALL' if res['pass_all'] else 'FAIL_SOME')
    raise SystemExit(0 if res['pass_all'] else 1)


if __name__ == '__main__':
    main()
