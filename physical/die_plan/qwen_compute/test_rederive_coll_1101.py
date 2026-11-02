"""Collector children retain physical identity when wavefront output order changes."""
import unittest
from unittest.mock import patch

import rederive_coll_1101 as R


class ChildTerminals(unittest.TestCase):
    def derive(self, outs):
        tree = {"n_reset_consumers": 28, "outs": outs, "relays": []}
        old = {"n_reset_consumers": 28}
        contract = {"collector_tree": old, "pins": [],
                    "collector_children": [{"part": "child0", "node": "rst_n_t28",
                                             "xy_um": [1227.36, 2422.88]}]}
        with patch.object(R.RT, "for_type", return_value=tree):
            return R.derive(None, contract, "cbx")[2]

    def test_inserted_output_keeps_child_at_its_existing_terminal(self):
        self.assertEqual(self.derive([[1081.056, 8.608], [1227.36, 2422.88]]), ["rst_n_t29"])

    def test_missing_terminal_refuses_nearest_output(self):
        with self.assertRaisesRegex(ValueError, "0 reset outputs"):
            self.derive([[1081.056, 8.608]])

    def test_ambiguous_terminal_refuses_alias(self):
        with self.assertRaisesRegex(ValueError, "2 reset outputs"):
            self.derive([[1227.36, 2422.88], [1227.36, 2422.88]])


if __name__ == "__main__":
    unittest.main()
