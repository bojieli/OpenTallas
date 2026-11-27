import unittest
import ownership as O


class Credited(unittest.TestCase):
    def test_exact_and_prefix_rows(self):
        c = O.parse_retired("# c\nqwen_kvsys\tkv_cland_w1*\taccepted legacy\nhbm\tvsN1\n")
        it = {"item": "kv_cland_w1045_ns_ddbeb", "module": "m"}
        self.assertIn("CREDITED-UNVERSIONED (kv_cland_w1*): accepted legacy", O._credited(c, "qwen_kvsys", it))
        self.assertIsNone(O._credited(c, "qwen_kvsys", {"item": "kv_cland_w257_x", "module": "m"}))
        self.assertIsNone(O._credited(c, "qwen_compute", it))
        self.assertIsNotNone(O._credited(c, "hbm", {"item": "vsN1", "module": "m"}))

    def test_none_and_state_listed(self):
        self.assertIsNone(O._credited(None, "hbm", {"item": "x"}))
        self.assertIn("CREDITED-UNVERSIONED", O.STATES)
        self.assertIn("CREDITED-UNVERSIONED", O.NEXT)
