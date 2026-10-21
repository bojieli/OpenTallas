"""Classify strictly retained full-suite differences; never discard raw verdicts."""
from pathlib import Path
import hashlib
import json
import re
import sys

p = Path(sys.argv[1])
x = json.loads(p.read_text())
allowed = re.compile(r'E\s+\[INFO DPL-0500\] Runtime: [0-9]+(?:\.[0-9]+)?s')
changes = x['changed_error_cases']
only_walltime = all(all(allowed.fullmatch(line) for line in side) for case in changes.values() for side in case.values())
identity = not x['added'] and not x['removed'] and x['baseline_failed_cases'] == x['candidate_failed_cases']
counts = x['baseline_error_lines'] == x['candidate_error_lines']
result = {
 'strict_comparator_status_retained': x['status'],
 'strict_comparison_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
 'failed_identity_multiset_equal': identity,
 'error_line_counts_equal': counts,
 'only_changed_error_text_is_native_DPL_0500_elapsed_walltime': only_walltime,
 'semantic_error_detail_status': 'MATCH_EXCEPT_DPL_WALLTIME' if identity and counts and only_walltime else 'DIFFERENT',
 'exact_runtime_changes': changes,
 'qualification': 'Regression parity with existing failures; no all-green or byte-identical error-detail claim.'
}
print(json.dumps(result, indent=2))
raise SystemExit(0 if identity and counts and only_walltime else 1)
