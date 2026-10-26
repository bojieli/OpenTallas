import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import dvm_head_onward as H
from qwen_static_schedule.calendar import ScheduleError


def receipt(extra=23, bad=None):
    cols = []
    for c in range(48):
        side = 'W' if c < 24 else 'E'
        hops = 23 - c if c < 24 else c - 24
        rec = dict(column=c, side=side, hops_from_root=hops, arrival_edges_onward1=hops, arrival_edges_onward2=2 * hops,
                   equalise_edges_onward1=23 - hops, equalise_edges_onward2=2 * (23 - hops))
        cols.append(rec)
    if bad is not None:
        cols[bad]['equalise_edges_onward2'] += 1
    return dict(schema=H.SCHEMA, schedule=dict(head_row_edges_onward1=23, head_row_edges_onward2=46,
                                               extra_edges_per_ME_op=extra, per_column=cols))


def write(root, d):
    f = Path(root) / H.RECEIPT
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d))


class HeadOnward(unittest.TestCase):
    def test_contract(self):
        with tempfile.TemporaryDirectory() as t:
            write(t, receipt())
            c2, c1 = H.load(t, 2), H.load(t, 1)
            self.assertEqual((c2['word_shift'], c1['word_shift']), (23, 0))
            self.assertEqual({H.column_offset(c2, k) for k in range(48)}, {46})
            self.assertEqual({H.column_offset(c1, k) for k in range(48)}, {23})

    def test_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ScheduleError):
                H.load(t, 2)
            write(t, receipt(bad=5))
            with self.assertRaises(ScheduleError):
                H.load(t, 2)
            write(t, receipt(extra=22))
            with self.assertRaises(ScheduleError):
                H.load(t, 2)


if __name__ == '__main__':
    unittest.main()
