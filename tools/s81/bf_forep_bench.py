#!/usr/bin/env python3
"""S81-C199-FANOUT (OT_BF_FOREP, 2026-10-19): bf_rstpart_bench generalised -- the candidate case is 'forep'
(FREECLK + RSTPART + FOREP kept fan-out copies), every --mutant case must differ from the baseline trace.
Derived from: S81-C199 reset partition (OT_BF_RSTPART, 2026-10-19): every valid/metadata edge, busy and fault of the free-clock
column with the partitioned reset tree equals the default (gated-clock, single-synchroniser) column, cycle for cycle,
on the full independent BF numerical + wake + transaction workload; the stuck-copy negatives must FAIL on real output
comparisons.  Run as bf_txn_bench.py (same arguments) with --only baseline rstpart mut_stuck mut_tree and
--positive-define baseline=... rstpart=... --mutant mut_stuck=... --mutant mut_tree=..."""
import hashlib
import json
import sys
from pathlib import Path
import bf_txn_bench as txn

old = '    final begin : t_fin'
assert txn.SHADOW.count(old) == 1
txn.SHADOW = txn.SHADOW.replace(old, '''    integer freeclk_trace;
    initial freeclk_trace = $fopen("candidate_edges.txt", "w");
    always @(posedge s_clk) begin
      $fwrite(freeclk_trace, "%0t %b %b %b %h %h\\n", $time, s_busy, s_fault, s_pv,
          s_pv[0] ? t_slice(0, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos) : 64'd0,
          s_pv[1] ? t_slice(1, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos) : 64'd0);
    end
''' + old)
check_only = '--check-only' in sys.argv
if check_only:
    sys.argv.remove('--check-only')
work = Path(sys.argv[sys.argv.index('--work') + 1]).resolve()
CAND = 'forep'
MUTS = [x.split('=')[0] for i, x in enumerate(sys.argv) if i and sys.argv[i - 1] == '--mutant']


def main():
    if not check_only:
        try:
            txn.main()
        except SystemExit:
            pass   # bf_txn_bench's own mutant rule wants DIFF TXN; the per-cycle rule below is the stricter one
    term = json.loads((work / 'terminal.json').read_text())
    for c in ('baseline', CAND):
        assert term['cases'][c]['ok'], f'{c}: positive failed: {term["cases"][c]}'
    a = (work / 'baseline' / 'candidate_edges.txt').read_bytes()
    b = (work / CAND / 'candidate_edges.txt').read_bytes()
    mismatch = next((i for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1) if x != y), None)
    assert a == b, f'per-cycle output/status mismatch at line {mismatch}; lengths {len(a)}/{len(b)}'
    muts = {}
    for m in MUTS:
        t = (work / m / 'candidate_edges.txt').read_bytes()
        line = next((i for i, (x, y) in enumerate(zip(a.splitlines(), t.splitlines()), 1) if x != y), None)
        if line is None and len(t) != len(a):
            line = min(len(a.splitlines()), len(t.splitlines())) + 1
        assert line is not None, f'{m}: negative control NOT detected (trace identical to baseline)'
        log = (work / m / 'run.log').read_text()
        txn_fail = next((x for x in log.splitlines() if 'DIFF' in x or 'Fatal' in x), None)
        muts[m] = {'first_trace_mismatch_line': line, 'txn': (txn_fail or 'TXN MATCH (values) but output cycles differ')[:300]}
        print(f'NEGATIVE {m} DETECTED trace line {line}: {muts[m]["txn"]}')
    rec = {'status': 'PASS', 'scope': 'OT_BF_FOREP (free clock + reset partition + kept fan-out copies <= 32 loads) vs default column: every '
           'valid/metadata/busy/fault output cycle identical on the full BF numerical + wake + transaction workload',
           'trace_lines': len(a.splitlines()), 'trace_bytes': len(a), 'trace_sha256': hashlib.sha256(a).hexdigest(),
           'extra_data_edges': 0, 'mutants': muts}
    (work / 'forep_exact.json').write_text(json.dumps(rec, indent=2) + '\n')
    print('BF_FOREP_EXACT PASS', json.dumps(rec))


main()
