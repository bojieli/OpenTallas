import unittest
import ownership as O


class Alias(unittest.TestCase):
    def test_retired_lanes_map_to_current_r_lanes(self):
        for old, new in (("DIE-S81-90", "S81-DIE-R"), ("DIE-S81-89", "S81-DIE-R"), ("FAIL-S81-1", "S81-TYPES-R"), ("CORE-ROWS-1115", "S81-CORES-R"),
                         ("KV-PVHG-O", "KV-R"), ("QC-PLAN-M", "QC-PLAN-R"), ("QC-PINACCESS-O", "QC-PLAN-R")):
            self.assertEqual(O.current_lane(old), new)

    def test_unlisted_and_current_lanes_keep_their_name(self):
        for n in ("KIT-WAVE-1", "S81-DIE-R", "KV-R", "HBM-CORES", "DIE-HBM-100"):
            self.assertEqual(O.current_lane(n), n)
