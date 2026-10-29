#!/usr/bin/env python3
"""QC-A0-KITS-6 10-28: gen_core_kit_qc.py opt-in recipe key hard_children (macro-composed core, SIGNED child views).
    python3 -m pytest -q test_gen_core_kit_qc_hard_children.py"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_qc as G  # noqa: E402


def _view(root, m, status="signoff", verdict="SIGNED (signoff.py verdict SIGNED; routed LEC EQUIVALENT)",
          complete=True, size=(10.0, 20.0), drop=()):
    d = Path(root) / m
    d.mkdir(parents=True, exist_ok=True)
    files = {f"{m}.lef": f"MACRO {m}\n  SIZE {size[0]} BY {size[1]} ;\nEND {m}\n", f"{m}_tt.lib": "library(tt) {}\n",
             f"{m}_ff.lib": "library(ff) {}\n", "provenance.json": json.dumps(dict(views_status=status, verdict=verdict)),
             "gates.json": json.dumps(dict(view_complete=complete))}
    for k, v in files.items():
        if k not in drop:
            (d / k).write_text(v)
    return d


class ChildView(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.t.cleanup()

    def test_signed_view_ok(self):
        self.assertEqual(G.child_view_problems(_view(self.t.name, "leaf"), "leaf"), [])

    def test_not_signed_refused(self):
        p = G.child_view_problems(_view(self.t.name, "leaf", status="incomplete: x", verdict="NOT SIGNED",
                                        complete=False), "leaf")
        self.assertEqual(len(p), 3, p)

    def test_missing_files_named(self):
        p = G.child_view_problems(_view(self.t.name, "leaf", drop=("leaf_ff.lib", "gates.json")), "leaf")
        self.assertEqual(sorted(p), ["missing gates.json", "missing leaf_ff.lib"])

    def test_wrong_macro_name(self):
        d = _view(self.t.name, "leaf")
        (d / "leaf.lef").write_text("MACRO other\n SIZE 1 BY 1 ;\nEND other\n")
        self.assertTrue(any("no MACRO leaf" in x for x in G.child_view_problems(d, "leaf")))


class ChildPlan(unittest.TestCase):
    def test_spec_children_expand(self):
        spec = dict(children=[dict(view="a/b/leaf", inst="u.g[0].x", at=[1, 2], orient="MY"),
                              dict(view="a/b/node", inst="u.n", at=[30, 2], count=1)])
        ch = G.hard_children_list({}, spec)
        self.assertEqual([c["master"] for c in ch], ["leaf", "node"])
        self.assertEqual(ch[1]["orient"], "R0")

    def test_children_file(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "c.json").write_text(json.dumps(dict(children=[dict(inst="u.a", module="leaf", at=[5, 6])])))
            ch = G.hard_children_list(dict(children_file="c.json"), {}, repo=t)
            self.assertEqual(ch, [dict(inst="u.a", master="leaf", at=[5.0, 6.0], orient="R0")])

    def test_check_overlap_outline_view(self):
        views, sizes = {"leaf": "v"}, {"leaf": (10.0, 20.0)}
        ok = [dict(inst="a", master="leaf", at=[5, 5], orient="R0"), dict(inst="b", master="leaf", at=[15, 5], orient="MY")]
        self.assertEqual(G.hard_children_check(ok, views, sizes, (40, 40), 4.32), [])
        bad = ok + [dict(inst="c", master="leaf", at=[20, 10], orient="R90"),
                    dict(inst="d", master="node", at=[0, 0], orient="R0"),
                    dict(inst="e", master="leaf", at=[35, 30], orient="R0")]
        err = G.hard_children_check(bad, views, sizes, (40, 40), 4.32)
        self.assertTrue(any("c: orient R90" in e for e in err), err)
        self.assertTrue(any("no view for master node" in e for e in err), err)
        self.assertTrue(any("e: site" in e for e in err), err)
        self.assertTrue(any("overlap: b / c" in e for e in err), err)

    def test_inst_regex_genblk_and_brackets(self):
        r = re.compile(G.child_inst_regex("u_g.u_logic.g_ndh.u_node"))
        self.assertTrue(r.search("u_g.u_logic.genblk5.g_ndh.u_node"))
        self.assertTrue(r.search("u_g.u_logic.g_ndh.u_node"))
        self.assertFalse(r.search("u_g.u_logic.g_ndh.u_node2"))
        r = re.compile(G.child_inst_regex("u.g_sl[3].u_raw"))
        self.assertTrue(r.search(r"u.g_sl\[3\].u_raw"))
        self.assertTrue(r.search("u.g_sl[3].u_raw"))
        self.assertFalse(r.search("u.g_sl[13].u_raw"))

    def test_tcl_one_block_per_child(self):
        ch = [dict(inst="u.a[0]", master="leaf", at=[5.0, 6.0], orient="MY"),
              dict(inst="u.b", master="node", at=[50.0, 6.0], orient="R0")]
        t = G.hard_children_tcl(ch)
        self.assertEqual(t.count("setPlacementStatus FIRM"), 2)
        self.assertIn("OT_HARD_CHILDREN placed 2", t)
        self.assertIn('error "hard child u.a[0]: [llength $hit] matches"', t)


class DefaultUnchanged(unittest.TestCase):
    def test_refusal_kept_without_recipe_key(self):
        src = (HERE / "gen_core_kit_qc.py").read_text()
        self.assertIn('if spec.get("children") and not hcr:', src)
        self.assertIn("must be signed first (refused)", src)


if __name__ == "__main__":
    unittest.main()
