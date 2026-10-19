#!/usr/bin/env python3
"""Compare every valid/metadata edge, busy and fault on default versus free-clock BF tiles."""
import json
import re
import sys
from pathlib import Path
import bf_txn_bench as txn

# Reuse the full independent numerical/wake/transaction bench. Capture actual
# candidate output edges and status, never a regenerated expected waveform.
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
    rc = ex.code
    if rc:
        raise
    baseline = work / 'baseline' / 'candidate_edges.txt'
    free = work / 'freeclk' / 'candidate_edges.txt'
    assert baseline.is_file() and free.is_file(), 'missing real output trace'
    a, b = baseline.read_bytes(), free.read_bytes()
    mismatch = next((i for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1) if x != y), None)
    assert a == b, f'actual per-cycle output/status mismatch at line {mismatch}; lengths {len(a)}/{len(b)}'
    mut = (work / 'missing_edge' / 'run.log').read_text()
    assert 'DIFF TXN' in mut, 'negative must fail actual output comparisons, not infrastructure'
    rec = {'status': 'PASS', 'scope': 'actual BF independent numerical + wake + transaction workload; every candidate valid/metadata/status edge equals default', 'trace_lines': len(a.splitlines()), 'trace_bytes': len(a), 'extra_data_edges': 0, 'missing_edge_mutant': 'actual DIFF TXN', 'physical_and_power_qualified': False}
    (work / 'freeclk_exact.json').write_text(json.dumps(rec, indent=2) + '\n')
    print('BF_TILE_FREECLK_EXACT PASS', json.dumps(rec))
