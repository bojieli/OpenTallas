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
