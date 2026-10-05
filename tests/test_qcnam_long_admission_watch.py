"""Watcher routing tests; no real process signals or sleeps."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import qcnam_long_admission_watch as W


@pytest.mark.parametrize('check,expected', [
    ({'released': True}, 'released'),
    ({'error': 'source changed'}, 'blocked'),
    ({'held': True, 'ready_to_release': True}, 'ready'),
    ({'held': True, 'greedy_waiter': {'state': 'S', 'exit_code': 0},
      'reasons': ['greedy waiter has not exited successfully']}, 'wait'),
    ({'held': True, 'greedy_waiter': {'state': 'Z', 'exit_code': 256},
      'reasons': ['greedy waiter has not exited successfully']}, 'blocked'),
    ({'held': True, 'reasons': ['available root disk below long admission budget']}, 'wait'),
    ({'held': True, 'reasons': ['greedy waiter identity changed']}, 'blocked'),
    ({'held': True, 'reasons': ['greedy reference is partial or truncated']}, 'blocked'),
    ({'held': None}, 'blocked'),
])
def test_only_live_greedy_or_disk_pressure_keep_waiting(check, expected):
    assert W.disposition(check) == expected
