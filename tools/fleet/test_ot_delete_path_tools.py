import importlib.machinery, importlib.util, os, sys, tempfile, unittest, io, contextlib
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import block_raw_rm as B
loader = importlib.machinery.SourceFileLoader("ot_delete_cli", os.path.join(H, "ot-delete"))
spec = importlib.util.spec_from_loader("ot_delete_cli", loader); D = importlib.util.module_from_spec(spec); loader.exec_module(D)


class FakeGuard:
    def __init__(self, refuse): self.r = refuse
    def refuse(self, t, protected=None): return self.r.get(os.path.basename(t))
    def load_list(self, p): return set(), None


def run(args, guard, rm):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = D.main(args, guard=guard, rmtree=rm)
    return rc, out.getvalue()


class Cap(unittest.TestCase):
    def test_hook_blocks_raw_rm_on_scratch(self):
        for c in ("rm -rf /srv/opentallas-scratch2/claude/kw45/src_x", "cd /; rm -r -f /srv/opentallas-scratch3/claude/a", "sudo rm -fr /srv/opentallas-scratch/x",
                  "ssh e8 'rm -rf /srv/opentallas-scratch2/claude/x'", "find /srv/opentallas-scratch2/claude/x -type f -delete",
                  "python3 -c 'import shutil; shutil.rmtree(\"/srv/opentallas-scratch2/x\")'", "ls && rm --recursive --force /srv/opentallas-scratch2/q"):
            self.assertTrue(B.blocked(c), c)

    def test_hook_allows_everything_else(self):
        for c in ("ot-delete /srv/opentallas-scratch2/claude/kw45/src_x", "rm -f /tmp/x", "rm -rf /tmp/build", "rm /srv/opentallas-scratch2/claude/a/file.log",
                  "ls /srv/opentallas-scratch2", "git rm -r tools/x", "du -sh /srv/opentallas-scratch2/claude"):
            self.assertFalse(B.blocked(c), c)

    def test_guard_refusal_is_a_skip_not_an_error(self):
        d = tempfile.mkdtemp(); a = os.path.join(d, "keep"); b = os.path.join(d, "go"); os.mkdir(a); os.mkdir(b)
        gone = []
        rc, out = run([a, b], FakeGuard({"keep": "protected (kit_wave.json)"}), lambda t: gone.append(t))
        self.assertEqual(rc, 0); self.assertEqual(gone, [b])
        self.assertIn("SKIP %s: protected" % a, out); self.assertIn("DELETED %s" % b, out)

    def test_dry_and_missing_and_failure(self):
        d = tempfile.mkdtemp(); a = os.path.join(d, "t"); os.mkdir(a); gone = []
        rc, out = run(["--dry", a, os.path.join(d, "nope")], FakeGuard({}), lambda t: gone.append(t))
        self.assertEqual((rc, gone), (0, [])); self.assertIn("WOULD-DELETE", out); self.assertIn("does not exist", out)
        def boom(t): raise OSError("busy")
        rc, out = run([a], FakeGuard({}), boom)
        self.assertEqual(rc, 1); self.assertIn("FAILED", out)

    def test_single_regular_file_same_guard(self):
        """FLOW-OPS-1000: a lane's stray file in a shared dir goes through the guard + manifest, then unlink; a refused one stays"""
        d = tempfile.mkdtemp(); f = os.path.join(d, "stray.json"); k = os.path.join(d, "keep.json")
        for p in (f, k):
            open(p, "w").write("{}")
        rc, out = run([f, k], FakeGuard({"keep.json": "protected (kit_wave.json)"}), lambda t: self.fail("rmtree on a file"))
        self.assertEqual(rc, 0); self.assertFalse(os.path.exists(f)); self.assertTrue(os.path.exists(k))
        self.assertIn("DELETED %s" % f, out); self.assertIn("SKIP %s: protected" % k, out)
        fifo = os.path.join(d, "p"); os.mkfifo(fifo)
        rc, out = run([fifo], FakeGuard({}), lambda t: self.fail("fifo"))
        self.assertIn("not a directory or regular file", out); self.assertTrue(os.path.exists(fifo))

    def test_real_delete_of_readonly_tree(self):
        d = tempfile.mkdtemp(); a = os.path.join(d, "t"); os.makedirs(os.path.join(a, "sub")); open(os.path.join(a, "sub", "f"), "w").close()
        os.chmod(os.path.join(a, "sub"), 0o555)
        rc, out = run([a], FakeGuard({}), None)
        self.assertEqual(rc, 0); self.assertFalse(os.path.exists(a))

    def test_root_fallback_after_permission_failure(self):
        """CLEAN-AGGR-R3: a root-owned tree the ubuntu delete cannot remove goes through sudo rm, same guard; refused when not eligible"""
        import types
        d = tempfile.mkdtemp(); a = os.path.join(d, "t"); os.mkdir(a)
        def deny(t): raise PermissionError(13, "Permission denied", t)
        calls = []
        def root(t):
            calls.append(t); os.rmdir(t); return types.SimpleNamespace(returncode=0, stderr="")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = D.main([a], guard=FakeGuard({}), rmtree=deny, rootrm=root, root_ok=lambda t: True)
        self.assertEqual((rc, calls), (0, [a])); self.assertIn("ROOT-FALLBACK", out.getvalue()); self.assertFalse(os.path.exists(a))
        b = os.path.join(d, "u"); os.mkdir(b)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = D.main([b], guard=FakeGuard({}), rmtree=deny, rootrm=lambda t: self.fail("not eligible"), root_ok=lambda t: False)
        self.assertEqual(rc, 1); self.assertTrue(os.path.exists(b))
        with contextlib.redirect_stdout(io.StringIO()):
            rc = D.main([b], guard=FakeGuard({"u": "protected"}), rmtree=deny, rootrm=lambda t: self.fail("guarded"), root_ok=lambda t: True)
        self.assertEqual(rc, 0); self.assertTrue(os.path.exists(b))

    def test_root_fallback_eligibility(self):
        self.assertFalse(D.root_fallback_ok("/tmp/x"))
        self.assertFalse(D.root_fallback_ok("/srv/opentallas-scratch2/claude"))
