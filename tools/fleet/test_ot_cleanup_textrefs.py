import json, os, pathlib, sys, tempfile, time, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ot_cleanup_textrefs as m

OLD, NEW = "/srv/opentallas-scratch2/claude/kw45/src_old_x", "/srv/opentallas-scratch2/claude/kw45/src_new_y"


class TextRefs(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp()); (self.t / "lanes/handoff").mkdir(parents=True); (self.t / "autopilot").mkdir()
        self.now = time.mktime((2026, 11, 16, 13, 0, 0, 0, 0, -1))

    def test_old_handoff_file_does_not_protect_new_one_does(self):
        old = self.t / "lanes/handoff/old.md"; old.write_text(OLD); os.utime(old, (self.now - 100 * 3600,) * 2)
        new = self.t / "lanes/handoff/new.md"; new.write_text(NEW); os.utime(new, (self.now - 10 * 3600,) * 2)
        r = m.text_refs(str(self.t), self.now)
        self.assertIn(NEW, r); self.assertNotIn(OLD, r)

    def test_queue_lines_by_timestamp_with_continuation(self):
        (self.t / "lanes/COORD-REVIEW-QUEUE.md").write_text(
            f"- 2026-11-10 08:00 PST STATE old line {OLD}\n  continuation {OLD}/a\n"
            f"- 2026-11-16 02:00 PST RESULT new {NEW}\n  continuation {NEW}/b\n- 11-15 23:10 PST x {NEW}/c\n")
        r = m.text_refs(str(self.t), self.now)
        self.assertNotIn(OLD, r); self.assertNotIn(OLD + "/a", r)
        self.assertIn(NEW, r); self.assertIn(NEW + "/b", r); self.assertIn(NEW + "/c", r)

    def test_markers_v2_releases_v1_of_same_die_and_keeps_newest_sha(self):
        d = self.t / "mk"; d.mkdir()
        def w(name, die, tree, sha, age):
            p = d / name; p.write_text(json.dumps({"die": die, "tree": tree, "tools_sha": sha})); os.utime(p, (self.now - age,) * 2)
        w("tree_switch_head.json", "head", "/srv/opentallas-scratch2/claude/kw45/src_head_pin_e594", "e594", 3 * 3600)
        w("tree_switch_s81.json", "s81", "/srv/opentallas-scratch2/claude/kw45/src_s81_pin_e4b9", "e4b9", 3 * 3600)
        w("tree_switch_s81_head.json", "s81_head", "/srv/opentallas-scratch2/claude/kw45/src_head_pin_eb1e", "eb1e", 60)
        keep, names = m.marker_keep(str(d))
        self.assertIn("/srv/opentallas-scratch2/claude/kw45/src_head_pin_eb1e", keep)
        self.assertNotIn("/srv/opentallas-scratch2/claude/kw45/src_head_pin_e594", keep)      # head v1 superseded by s81_head v2
        self.assertIn("/srv/opentallas-scratch2/claude/kw45/src_s81_pin_e4b9", keep)          # s81 has no v2 yet
        self.assertIn("_pin_eb1e", names)


if __name__ == "__main__":
    unittest.main()
