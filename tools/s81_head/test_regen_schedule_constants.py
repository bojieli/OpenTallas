import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regen_schedule_constants import ca_lane_cycles, head_transport


class HeadScheduleTests(unittest.TestCase):
    def test_longest_path_and_twice_worst_gather_not_lane_sum(self):
        costs = dict(sp_x0=2, sp_b0=3, sp_x1=4, sp_b1=5,
                     chW0_h=10, chE0_h=9, chW1_h=3, chE1_h=2,
                     coll_WN_u=7, coll_WN_d=6, host_tx=100, head_lep_landing=80)
        result = head_transport(costs)
        self.assertEqual(result['spine']['cycles'], 17)
        self.assertEqual(result['spine']['slice'], 1)
        self.assertEqual(result['gather_worst']['cycles'], 7)
        self.assertEqual(result['total_cycles'], 31)
        costs['chW0_h'] += 5  # critical branch changes; the reported path follows it
        self.assertEqual(head_transport(costs)['total_cycles'], 34)

    def test_missing_spine_return_cannot_be_zero_cost(self):
        with self.assertRaisesRegex(ValueError, 'return lane missing'):
            head_transport(dict(sp_x0=2, chW0_h=3, coll_u=1))

    def test_ca_adds_each_actual_port_once_with_its_own_cost(self):
        raw = dict(ports=[dict(id='p0', src=dict(part='a'), dst=dict(part='b')),
                          dict(id='p1', src=dict(part='b'), dst=dict(part='c'))],
                   lanes=[dict(id='lane', ports=['p0', 'p1'])])
        rows = [dict(port='p0', lane='lane', src='a', dst='b', added_cycles=2),
                dict(port='p1', lane='lane', src='b', dst='c', added_cycles=3)]
        table = dict(ports=rows, added_cycles_per_crossing=99)
        self.assertEqual(ca_lane_cycles(raw, table)[0], dict(lane=5))
        bad = copy.deepcopy(table); bad['ports'].append(rows[0])
        with self.assertRaisesRegex(ValueError, 'duplicate or mismatched'):
            ca_lane_cycles(raw, bad)
        bad = copy.deepcopy(table); bad['ports'][0]['src'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'endpoints differ'):
            ca_lane_cycles(raw, bad)
        table['count_aligned'] = dict(ports=dict(p0=dict(sched_lat=4)))
        with self.assertRaisesRegex(ValueError, 'sched_lat'):
            ca_lane_cycles(raw, table)

    def test_already_landed_plan_refuses_double_charge(self):
        with self.assertRaisesRegex(ValueError, 'double charging'):
            ca_lane_cycles(dict(clock=dict(landing_network=dict(edges=[1]))), dict(ports=[]))


if __name__ == '__main__':
    unittest.main()
