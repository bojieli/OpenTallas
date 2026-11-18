import json, os, tempfile, unittest
import ot_delete_guard as G
import ot_disk_autoprune as AP


class StructuredOnly(unittest.TestCase):
    def test_prose_never_protects(self):
        c = tempfile.mkdtemp(); os.makedirs(c + "/autopilot"); os.makedirs(c + "/lanes/handoff")
        json.dump({"dies": {"s81": {"src": "/srv/opentallas-scratch2/claude/kw45/src_s81_pin_live"}}}, open(c + "/autopilot/kit_wave.json", "w"))
        open(c + "/lanes/handoff/NOTE.md", "w").write("see /srv/opentallas-scratch2/claude/kw45/src_s81_pin_old and /srv/opentallas-scratch2/claude/mq-gate\n")
        open(c + "/CODEX-LOG.md", "w").write("/srv/opentallas-scratch2/claude/kw45/src_s81_pin_old2\n")
        p = G.build_protected(c)
        self.assertIn("/srv/opentallas-scratch2/claude/kw45/src_s81_pin_live", p)
        self.assertEqual({x for x in p if "old" in x or "mq-gate" in x}, set())

    def test_autoprune_text_refs_are_advisory(self):
        d = tempfile.mkdtemp(); f = d + "/t.refs"; open(f, "w").write("/srv/opentallas-scratch2/claude/kw45/src_x\n")
        self.assertEqual(AP.load_refs([f]), {"/srv/opentallas-scratch2/claude/kw45/src_x"})
        import inspect
        self.assertIn("--text-refs", inspect.getsource(AP.main))
