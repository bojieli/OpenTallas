"""MERGE-QUEUE-1 11-14: rt_tools_digest is a CONTENT digest, so two pinned version dirs rt/<sha> with byte-identical kit tools
(different absolute paths and mtimes) give the same digest (no rt_tools re-arm on every main push), and a changed kit tool does not."""
import ast, hashlib, os, pathlib, shutil, tempfile, time, unittest
from pathlib import Path

SRC = pathlib.Path(__file__).with_name("kit_wave.py").read_text()
FN = next(n for n in ast.parse(SRC).body if isinstance(n, ast.FunctionDef) and n.name == "rt_tools_digest")
CODE = ast.get_source_segment(SRC, FN)


def digest(root):
    ns = {"__file__": str(root / "tools/autopilot/kit_wave.py"), "Path": Path, "os": os, "hashlib": hashlib, "_TOOLS_DIGEST": {}}
    exec(CODE, ns)
    return ns["rt_tools_digest"]()


def tree(root, gen="X = 1\n"):
    for rel, text in (("tools/die_plan/gen_phys.py", gen), ("physical/common_flow/grt183_make.sh", "echo\n"),
                      ("tools/autopilot/kit_resume.py", "R = 1\n"), ("tools/autopilot/kit_wave.py", "W = 1\n"),
                      ("tools/autopilot/autopilot.py", "A = 1\n")):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


class Digest(unittest.TestCase):
    def test_same_content_other_dir_and_mtime_same_digest(self):
        t = Path(tempfile.mkdtemp())
        a = tree(t / "rt" / "aaaaaaaaaaaa")
        b = t / "rt" / "bbbbbbbbbbbb"
        shutil.copytree(a, b)
        later = time.time() + 3600
        for p in b.rglob("*"):
            os.utime(p, (later, later))
        self.assertEqual(digest(a), digest(b))

    def test_changed_kit_tool_changes_digest_scheduler_does_not(self):
        t = Path(tempfile.mkdtemp())
        a, b = tree(t / "a"), tree(t / "b", gen="X = 2\n")
        self.assertNotEqual(digest(a), digest(b))
        c = tree(t / "c")
        (c / "tools/autopilot/kit_wave.py").write_text("W = 2\n")      # the scheduler itself never changes a kit
        (c / "tools/autopilot/autopilot.py").write_text("A = 2\n")
        self.assertEqual(digest(a), digest(c))


if __name__ == "__main__":
    unittest.main()
