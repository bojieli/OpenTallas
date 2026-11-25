import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_ops as A


class T(unittest.TestCase):
    def plan(self):
        return {"partition_types": {"a": {"x": 1}, "b": {"internal_stations": [{"k": 0}]}}}

    def test_add_creates_missing_internal_stations(self):
        P = self.plan()
        r = A.apply(P, [{"op": "add", "path": "/partition_types/a/internal_stations/0", "value": {"k": 1}},
                        {"op": "add", "path": "/partition_types/a/internal_stations/1", "value": {"k": 2}}])
        self.assertEqual(r[0], 2); self.assertEqual(r[2], 0)
        self.assertEqual(P["partition_types"]["a"]["internal_stations"], [{"k": 1}, {"k": 2}])

    def test_add_existing_list_appends_and_is_idempotent(self):
        P = self.plan()
        op = {"op": "add", "path": "/partition_types/b/internal_stations/1", "value": {"k": 9}}
        A.apply(P, [op]); r = A.apply(P, [op])
        self.assertEqual(P["partition_types"]["b"]["internal_stations"], [{"k": 0}, {"k": 9}]); self.assertEqual(r[0], 1)

    def test_add_gap_is_stale(self):
        P = self.plan()
        r = A.apply(P, [{"op": "add", "path": "/partition_types/b/internal_stations/5", "value": 1}])
        self.assertEqual(r[2], 1)

    def test_replace_old_check_and_missing_key(self):
        P = self.plan()
        r = A.apply(P, [{"path": "/partition_types/a/x", "old": 1, "value": 2},
                        {"path": "/partition_types/a/x", "old": 7, "value": 3},
                        {"path": "/partition_types/zz/internal_stations/0", "old": 1, "value": 2}])
        self.assertEqual((r[0], r[2]), (1, 2)); self.assertEqual(P["partition_types"]["a"]["x"], 2)

    def test_skip_type_and_remove_absent(self):
        P = self.plan()
        r = A.apply(P, [{"op": "remove", "path": "/partition_types/a/nokey"},
                        {"op": "add", "path": "/partition_types/a/y", "value": 1}], skip="^a$")
        self.assertEqual(r[1], 2)


if __name__ == "__main__":
    unittest.main()
