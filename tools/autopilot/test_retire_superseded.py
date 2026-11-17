import os, tempfile, unittest
import hold_records as HR
import retire_superseded as RS


class RetireAtSwitch(unittest.TestCase):
    def test_switch_records_the_old_tree(self):
        cfg = {"dies": {"s81": {"src": "/x/old", "hold_records": [{"release": ["tree_ready:s81:/x/new"]}]}}}
        ctx = type("C", (), {"tree_fn": staticmethod(lambda d, t: True), "marker_fn": staticmethod(lambda d: {})})()
        HR.apply_tree_switches(cfg, ctx)
        self.assertEqual(cfg["dies"]["s81"]["src"], "/x/new")
        self.assertEqual(cfg["dies"]["s81"]["superseded_trees"], ["/x/old"])
        HR.apply_tree_switches(cfg, ctx)                         # idempotent
        self.assertEqual(cfg["dies"]["s81"]["superseded_trees"], ["/x/old"])

    def test_retire_only_what_guard_allows_and_no_die_names(self):
        d = tempfile.mkdtemp(); a, b, c, e = (os.path.join(d, n) for n in "abce")
        for p in (a, b, c):
            os.makedirs(p); open(os.path.join(p, "f"), "w").write("x")
        cfg = {"dies": {"s81": {"src": c, "superseded_trees": [a, b, c, e], "item_inputs": {}}}}
        log = []
        refuse = lambda t: "protected" if t == b else None
        r = RS.run(cfg, refuse, lambda t: __import__("shutil").rmtree(t), log.append, apply=True)
        res = {os.path.basename(x["tree"]): x["result"] for x in r}
        self.assertEqual(res["a"], "DELETED"); self.assertTrue(res["b"].startswith("KEEP guard"))
        self.assertTrue(res["c"].startswith("KEEP named")); self.assertEqual(res["e"], "absent")
        self.assertFalse(os.path.exists(a)); self.assertTrue(os.path.exists(b) and os.path.exists(c))
        r = RS.run({"dies": {"s81": {"src": c, "superseded_trees": [b]}}}, refuse, lambda t: 1 / 0, log.append, apply=False)
        self.assertTrue(os.path.exists(b))                       # dry run deletes nothing

    def test_dry_run_default(self):
        d = tempfile.mkdtemp(); a = os.path.join(d, "a"); os.makedirs(a)
        r = RS.run({"dies": {"s81": {"src": "/n", "superseded_trees": [a]}}}, lambda t: None, lambda t: 1 / 0, lambda r: None)
        self.assertEqual(r[0]["result"], "WOULD-DELETE"); self.assertTrue(os.path.exists(a))
