#!/usr/bin/env python3
"""S81-C199 reset partition (OT_BF_RSTPART, 2026-10-19): every valid/metadata edge, busy and fault of the free-clock
column with the partitioned reset tree equals the default (gated-clock, single-synchroniser) column, cycle for cycle,
on the full independent BF numerical + wake + transaction workload; the stuck-copy negatives must FAIL on real output
comparisons.  Run as bf_txn_bench.py (same arguments) with --only baseline rstpart mut_stuck mut_tree and
--positive-define baseline=... rstpart=... --mutant mut_stuck=... --mutant mut_tree=..."""
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
work = Path(sys.argv[sys.argv.index('--work') + 1]).resolve()
try:
    txn.main()
except SystemExit as ex:
    if ex.code:
        raise
    a = (work / 'baseline' / 'candidate_edges.txt').read_bytes()
    b = (work / 'rstpart' / 'candidate_edges.txt').read_bytes()
    mismatch = next((i for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1) if x != y), None)
    assert a == b, f'per-cycle output/status mismatch at line {mismatch}; lengths {len(a)}/{len(b)}'
    muts = {}
    for m in ('mut_stuck', 'mut_tree'):
        log = (work / m / 'run.log').read_text()
        assert 'DIFF' in log or 'FAIL' in log or 'Fatal' in log, f'{m}: negative must fail real comparisons'
        muts[m] = next((s for s in log.splitlines() if 'DIFF' in s or 'FAIL' in s or 'Fatal' in s), '')[:300]
    rec = {'status': 'PASS', 'scope': 'OT_BF_RSTPART (free clock + partitioned kept reset copies) vs default column: every '
           'valid/metadata/busy/fault output cycle identical on the full BF numerical + wake + transaction workload',
           'trace_lines': len(a.splitlines()), 'trace_bytes': len(a), 'extra_data_edges': 0, 'mutants': muts}
    (work / 'rstpart_exact.json').write_text(json.dumps(rec, indent=2) + '\n')
    print('BF_RSTPART_EXACT PASS', json.dumps(rec))
