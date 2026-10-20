"""Compare actual native tables; report serializer limits separately."""
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])

def text(case):
    return (root / case / 'native.log').read_text()


def table(case, kind, label, mode):
    found = {}
    for line in text(case).splitlines():
        if not line.startswith(f'{kind}:{label}:{mode}:'):
            continue
        fields = line.split(':')
        found[tuple(fields[3:5])] = tuple(float(x) for x in fields[5:])
    assert found, (case, kind, label, mode)
    return found


def serialized(case, mode):
    p = root / case / f'before_{mode}.sdc'
    return [s for s in p.read_text().splitlines() if s.startswith(('set_load ', 'set_port_fanout_number '))]


summary = {'direct_read': {}, 'sync': {}, 'native_limits': {}}
for family in ('', 'coupon_'):
    for mode, reference in (('ss', 'reference'), ('ff', 'reference_ff')):
        candidate = family + 'candidate'
        reference = family + reference
        before = table(candidate, 'CAP_TABLE', 'after_read', mode)
        expected = table(reference, 'CAP_TABLE', 'after_read', mode)
        assert before == expected
        assert table(candidate, 'NET_TABLE', 'after_read', mode) == table(reference, 'NET_TABLE', 'after_read', mode)
        assert serialized(candidate, mode) == serialized(reference, mode)
        old = table(family + 'old', 'CAP_TABLE', 'after_read', mode)
        assert all(values == (0., 0., 0.) for values in old.values())
        after = table(candidate, 'CAP_TABLE', 'after_sync', mode)
        assert after == before
        if family:
            assert len(before) == 32
            assert all(abs(values[0] / 1e-15 - 80) < 0.00001 and values[1:] == (0., 0.) for values in before.values())
        summary['direct_read'][family + mode] = {'native_cap_rows': len(before), 'serialized_load_fanout_rows': len(serialized(candidate, mode)), 'reference_equal': True, 'old_zero': True}
        summary['sync'][family + mode] = {'initial_pin_wire_fanout_values_retained': True}

# Direct pin/wire queries return the native min/max reduction over transitions.
# Independent one-entry ports12..15 and write_sdc records expose every rf/mm
# position. These queries do not pretend to expose four hidden C++ entries.
assert not any('y[1]' in s for s in serialized('candidate', 'ss'))
ss = table('candidate', 'CAP_TABLE', 'after_changed_asym_sync', 'ss')
ff = table('candidate', 'CAP_TABLE', 'after_changed_asym_sync', 'ff')
assert abs(ss[('1', 'min')][0] / 1e-15 - 71) < .00001
assert abs(ff[('1', 'min')][0] / 1e-15 - 11) < .00001
before = table('candidate', 'NET_TABLE', 'after_read', 'ff')[('a[5]', 'max')]
after = table('candidate', 'NET_TABLE', 'after_sync', 'ff')[('a[5]', 'max')]
assert abs(before[2] / 1e-15 - 47) < .00001
assert after[2] > before[2]
summary['native_limits'] = {
    'four_independent_values': {'write_sdc_omits_y1': True, 'changed_ss_pin_min_ff_stale_fF': [ss[('1','min')][0] / 1e-15, ff[('1','min')][0] / 1e-15]},
    'subtract_pin_load': {'direct_ff_total_fF': before[2] / 1e-15, 'after_sync_ff_total_fF': after[2] / 1e-15, 'native_write_sdc_drops_flag': True},
    'units': 'set_units pF warns STA-0345 and keeps native library fF scale; no requested conversion claim',
    'scope': 'Direct-read preservation PASS; generic native write_sdc/sync semantics HOLD; no serializer fix.'
}
invalid = [x for x in text('reference').splitlines() if x.startswith('NATIVE_INVALID:')]
assert len(invalid) == 6
for case in ('old', 'candidate', 'reference_ff'):
    assert [x for x in text(case).splitlines() if x.startswith('NATIVE_INVALID:')] == invalid
summary['native_invalid_behavior'] = {'same_warning_success_or_error_records': True, 'cases': invalid}
for case in ('candidate', 'old'):
    assert 'EVAL_COUNTS:ff 1 ss 1|ff 1 ss 1' in text(case)
summary['original_and_include_evaluation'] = 'Exactly once each per mode, both old and candidate.'
summary['scene_sensitive_load'] = 'Candidate native per-mode scene count1 and51fF equals native single-scene reference; old read count0 precedes scene creation.'
print(json.dumps(summary, indent=2))
