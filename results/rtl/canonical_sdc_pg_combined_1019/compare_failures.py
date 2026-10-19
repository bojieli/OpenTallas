"""Compare complete pytest parameter/subtest identities and error detail cases."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys


def fingerprint(path, source_root):
    lines = Path(path).read_text().splitlines()
    cases = Counter(line for line in lines if line.startswith(('FAILED ', 'SUBFAILED')))
    errors = defaultdict(Counter)
    heading = '<before first failure heading>'
    for line in lines:
        if line.startswith('_') and line.endswith('_') and line.strip('_ '):
            heading = line.strip('_ ')
        if line.startswith('E '):
            # Normalize locations only, retaining exception types, messages,
            # parameter values and each corresponding failure section.
            value = line.replace(str(source_root).rstrip('/') + '/', '<SOURCE>/')
            value = re.sub(r'/tmp/tmp[a-zA-Z0-9_]+(?=/)', '<TMP>', value)
            value = re.sub(r'/tmp/pytest-of-ubuntu/pytest-[0-9]+/', '<PYTEST>/', value)
            errors[heading][value] += 1
    return cases, errors


def compare(base, candidate, base_root, candidate_root):
    a, ae = fingerprint(base, base_root)
    b, be = fingerprint(candidate, candidate_root)
    added = list((b-a).elements())
    removed = list((a-b).elements())
    error_differences = {}
    for heading in sorted(set(ae) | set(be)):
        if ae[heading] != be[heading]:
            error_differences[heading] = dict(candidate_only=list((be[heading]-ae[heading]).elements()),
                                            baseline_only=list((ae[heading]-be[heading]).elements()))
    return dict(status='PASS' if not added and not removed and not error_differences else 'FAIL',
        baseline_failed_cases=sum(a.values()), candidate_failed_cases=sum(b.values()),
        baseline_error_lines=sum(sum(c.values()) for c in ae.values()),
        candidate_error_lines=sum(sum(c.values()) for c in be.values()),
        added=added, removed=removed, changed_error_cases=error_differences,
        preserved_case_multiset=dict(sorted(a.items())),
        normalization='Error-detail locations only: exact source root, /tmp/tmp<random> basename, pytest run number; complete summary cases are compared verbatim.')


if __name__ == '__main__':
    result = compare(*sys.argv[1:5])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status']=='PASS' else 1)
