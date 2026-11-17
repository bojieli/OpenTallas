import json, os, tempfile, unittest
import ot_delete_guard as G

WS = "/srv/opentallas-scratch2/claude/wave-src"


def coord(dies):
    c = tempfile.mkdtemp(); os.makedirs(c + "/autopilot"); os.makedirs(c + "/lanes/handoff")
    json.dump({"dies": dies}, open(c + "/autopilot/kit_wave.json", "w"))
    return c


class AnyKeyPaths(unittest.TestCase):
    def test_src_prev_path_protects_the_wave_src_tree_and_its_parent(self):
        c = coord({"hbm": {"src": "/srv/opentallas-scratch2/claude/kw45/src_hbm_main_d6b0b70323",
                           "src_prev_kw43fsp": WS + "/20261110hbm2/hbm"}})
        p = G.build_protected(c)
        self.assertIn(WS + "/20261110hbm2/hbm", p)
        self.assertIsNotNone(G.refuse(WS, protected=p, ptext=""))                         # the parent dir (364 GB) is refused: a protected path lies inside it
        self.assertIsNotNone(G.refuse(WS + "/20261110hbm2", protected=p, ptext=""))
        self.assertIsNotNone(G.refuse(WS + "/20261110hbm2/hbm/x", protected=p, ptext=""))
        self.assertIsNone(G.refuse(WS + "/20261111", protected=p, ptext=""))              # an unrelated sibling is not protected

    def test_nested_and_list_values_and_shallow_paths(self):
        c = coord({"s81": {"item_inputs": {"t1": {"anything": ["x " + WS + "/20261113/s81 y"]}}, "note": "see /srv/opentallas-scratch2/claude/kw45"}})
        p = G.build_protected(c)
        self.assertIn(WS + "/20261113/s81", p)
        self.assertNotIn("/srv/opentallas-scratch2/claude/kw45", p)                       # a bare lane root in prose is not a root


class RetirementQueuePaths(unittest.TestCase):
    OLD = "/srv/opentallas-scratch2/claude/kw45/src_kv_old"
    LIVE = "/srv/opentallas-scratch2/claude/kw45/src_kv_live"

    def protected(self, extra=None):
        d = {"src": self.LIVE, "superseded_trees": [self.OLD]}
        d.update(extra or {})
        c = coord({"qwen_kvsys": d})
        self.addCleanup(__import__("shutil").rmtree, c)
        return G.build_protected(c)

    def test_queue_only_is_not_protected_but_manual_and_live_proofs_still_win(self):
        p = self.protected()
        self.assertNotIn(self.OLD, p)
        self.assertIn(self.LIVE, p)
        self.assertIsNone(G.refuse(self.OLD, protected=p, ptext=""))
        self.assertIn("protected", G.refuse(self.OLD, protected=p | {self.OLD}, ptext=""))
        self.assertIn("live process", G.refuse(self.OLD, protected=p, ptext=self.OLD))

    def test_other_direct_nested_and_current_references_are_preserved(self):
        for extra in ({"src": self.OLD}, {"rollback_tree": self.OLD}, {"PROTECTEDDBS": [self.OLD]},
                      {"item_inputs": {"x": {"superseded_trees": [self.OLD]}}}):
            self.assertIn(self.OLD, self.protected(extra), extra)

    def test_unrecognized_queue_value_is_not_filtered(self):
        for value in (self.OLD, {"path": self.OLD}, [{"path": self.OLD}]):
            self.assertIn(self.OLD, self.protected({"superseded_trees": value}))
