"""GITMIRROR: host-side git mirror source sync (git_mirror.py, closure_loop.mirror_sync).

The integration tests run the real push / archive / extract path against a bare mirror in a tmpdir: the "remote"
host is a fake ssh that drops its options and host and runs the command locally."""
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as C
import git_mirror as G

HOST = "fakehost"
REAL_SSH = C.ssh


def tree_of_tar(data):
    out = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.isfile():
                out[m.name] = tf.extractfile(m).read()
    return out


def tree_of_dir(root, skip=("SOURCE_COMMIT",)):
    root = Path(root)
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and str(p.relative_to(root)) not in skip}


class MirrorBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.git("init", "-q", "-b", "fixture", str(self.repo), cwd=self.root)
        for rel, text in {"tools/run.py": "runner v1\n", "rtl/a.v": "module a; endmodule\n",
                          "physical/x/config.mk": "X=1\n", "Makefile": "all:\n", "docs/skip.md": "no\n"}.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        # a bulky blob so a full push and a delta push are clearly different
        (self.repo / "rtl/big.v").write_text("".join(f"// line {i} {i * 7919 % 104729}\n" for i in range(20000)))
        self.c1 = self.commit("c1")
        self.mirror = self.root / "hostfs/git-mirror/OpenTallas.git"
        self.mirror.parent.mkdir(parents=True)
        self.git("init", "-q", "--bare", str(self.mirror), cwd=self.root)
        (self.mirror / G.READY_MARK).write_text("")
        fake = self.root / "fake-ssh"
        fake.write_text('#!/bin/bash\n# fake ssh: drop -o options and the host, run the command locally\n'
                        'while [ "${1:-}" = -o ]; do shift 2; done\nshift\nexec bash -c "$*"\n')
        fake.chmod(0o755)
        self.fake = str(fake)
        self.cfg = {"name": HOST, "git_mirror": str(self.mirror)}
        self.bulk_calls = []

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True,
                              text=True).stdout.strip()

    def commit(self, msg):
        self.git("add", "-A")
        self.git("-c", "user.name=T", "-c", "user.email=t@e", "commit", "-qm", msg)
        self.git("update-ref", "refs/remotes/origin/fixture", "HEAD")
        return self.git("rev-parse", "HEAD")

    def job(self, commit, run="run1", **src):
        source = {"branch": "fixture", "commit": commit, **src}
        return {"name": "j", "host": HOST, "run": str(self.root / "hostfs" / run),
                "spec": {"source": source, "stages": {}}}

    @contextmanager
    def transport(self, host, *, wait_s=None, bulk=False):
        if bulk:
            self.bulk_calls.append(host)
        yield [self.fake, "-o", "BatchMode=yes", host]

    def local_ssh(self, host, script, timeout=120, check=False, input=None):
        return REAL_SSH("localhost", script, timeout=timeout, check=check, input=input)

    def sync(self, j, cfg=None):
        with patch.object(C, "REPO", self.repo), patch.object(C, "gfetch"), patch.object(C, "ship_helpers"), \
                patch.object(C, "host_cfg", return_value=cfg or self.cfg), \
                patch.object(C, "ssh", side_effect=self.local_ssh), \
                patch.object(C, "transport_command", side_effect=self.transport):
            C.sync_source(j)
        return j

    def archive(self, commit, paths=("tools", "rtl", "physical", "Makefile")):
        return subprocess.run(["git", "-C", str(self.repo), "archive", "--format=tar", commit, "--", *paths],
                              check=True, capture_output=True).stdout

    def mirror_objects(self):
        out = self.git("--git-dir", str(self.mirror), "count-objects", "-v", cwd=self.root)
        kv = dict(line.split(": ") for line in out.splitlines())
        return int(kv["count"]) + int(kv["in-pack"])


class MirrorIntegrationTest(MirrorBase):
    def test_push_archive_extract_equals_git_archive_then_delta(self):
        j = self.sync(self.job(self.c1))
        self.assertTrue(j["source_synced"])
        src = Path(j["run"]) / "src"
        self.assertEqual(tree_of_dir(src), tree_of_tar(self.archive(self.c1)))
        self.assertEqual((src / "SOURCE_COMMIT").read_text().strip(), self.c1)
        self.assertNotIn("docs/skip.md", tree_of_dir(src))
        ev = [e for e in j["events"] if "git-mirror sync" in e]
        self.assertTrue(ev and "via push" in ev[0], j["events"])
        first = int(ev[0].split("push ")[1].split(" objects")[0])
        self.assertGreaterEqual(first, 8)
        self.assertEqual(self.git("--git-dir", str(self.mirror), "rev-parse", f"refs/cl/{self.c1}", cwd=self.root),
                         self.c1)
        self.assertEqual(self.bulk_calls, [HOST])          # the push rode the bulk lease, the tar path never ran
        before = self.mirror_objects()

        (self.repo / "tools/run.py").write_text("runner v2\n")
        c2 = self.commit("c2")
        j2 = self.sync(self.job(c2, run="run2"))
        self.assertEqual(tree_of_dir(Path(j2["run"]) / "src"), tree_of_tar(self.archive(c2)))
        ev2 = [e for e in j2["events"] if "git-mirror sync" in e][0]
        delta = int(ev2.split("push ")[1].split(" objects")[0])
        self.assertLessEqual(delta, 4, ev2)              # commit + root tree + tools tree + blob
        self.assertLessEqual(self.mirror_objects() - before, 4)

    def test_resume_into_existing_src_copies_over(self):
        j = self.job(self.c1)
        src = Path(j["run"]) / "src"
        (src / "tools").mkdir(parents=True)
        (src / "tools/run.py").write_text("stale partial\n")
        (src / "flow_output.txt").write_text("keep\n")
        self.sync(j)
        self.assertEqual((src / "tools/run.py").read_text(), "runner v1\n")
        self.assertEqual((src / "flow_output.txt").read_text(), "keep\n")
        self.assertFalse(list((Path(j["run"])).glob(".src-mirror.*")))

    def test_receipt_job_verified_on_host(self):
        j = self.sync(self.job(self.c1, paths=["tools"], extra_paths=["Makefile"],
                               required_files=["tools/run.py", "Makefile"]))
        receipt = j["source_archive"]
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1, ("tools", "Makefile"))))
        self.assertTrue(any("receipt archive + required_files sha256 verified" in e for e in j["events"]))
        self.assertEqual(json.loads((Path(j["run"]) / "cl/source_archive.json").read_text()), receipt)

    def test_receipt_mismatch_falls_back_to_verified_tar(self):
        # a host-side archive that differs byte-wise (tar.umask) must not pass the receipt; the tar path ships it
        self.git("--git-dir", str(self.mirror), "config", "tar.umask", "0077", cwd=self.root)
        j = self.sync(self.job(self.c1, paths=["tools"], required_files=["tools/run.py"]))
        self.assertTrue(any("git-mirror sync failed" in e and "RECEIPT_MISMATCH" in e for e in j["events"]),
                        j["events"])
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1, ("tools",))))
        self.assertTrue(j["source_synced"])

    def test_not_ready_mirror_uses_tar_without_push(self):
        (self.mirror / G.READY_MARK).unlink()
        with patch.object(G, "push_command", side_effect=AssertionError("pushed to an unseeded mirror")):
            j = self.sync(self.job(self.c1))
        self.assertTrue(any("not ready" in e for e in j["events"]))
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1)))

    def test_push_failure_falls_back(self):
        cfg = {"name": HOST, "git_mirror": str(self.root / "hostfs/missing.git")}
        (self.root / "hostfs/missing.git").mkdir()
        (self.root / "hostfs/missing.git" / G.READY_MARK).write_text("")   # marker without a repository
        j = self.sync(self.job(self.c1), cfg)
        self.assertTrue(any("tar sync" in e for e in j["events"]), j["events"])
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1)))

    def test_half_merged_src_is_reextracted_by_fallback(self):
        real = G.extract_script

        def broken(mirror, full, paths, run, receipt=None):
            # merge part of the tree into src (corrupted), then die
            return (real(mirror, full, paths, run, receipt).replace("echo GIT_MIRROR_EXTRACTED", "")
                    + f'echo corrupt > {run}/src/tools/run.py; rm -f {run}/src/Makefile; exit 1\n')
        with patch.object(G, "extract_script", side_effect=broken):
            j = self.sync(self.job(self.c1))
        self.assertTrue(any("git-mirror sync failed" in e for e in j["events"]))
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1)))

    def test_commit_already_in_mirror_from_upstream_skips_push(self):
        cfg = dict(self.cfg, git_mirror_upstream=str(self.repo))
        with patch.object(G, "push_command", side_effect=AssertionError("push not needed")):
            j = self.sync(self.job(self.c1), cfg)
        self.assertTrue(any("via upstream" in e for e in j["events"]), j["events"])
        self.assertEqual(self.bulk_calls, [])
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1)))
        self.assertEqual(self.git("--git-dir", str(self.mirror), "rev-parse", f"refs/cl/{self.c1}", cwd=self.root),
                         self.c1)

    def test_no_mirror_configured_keeps_legacy_path(self):
        with patch.object(G, "probe_script", side_effect=AssertionError("probed")):
            j = self.sync(self.job(self.c1), {"name": HOST})
        self.assertFalse(any("git-mirror" in e for e in j.get("events", [])))
        self.assertEqual(tree_of_dir(Path(j["run"]) / "src"), tree_of_tar(self.archive(self.c1)))
        self.assertEqual(self.bulk_calls, [HOST])

    def test_housekeep_drops_old_refs_keeps_newest(self):
        olds = []
        for i in range(3):
            day = f"2020-01-0{i + 1}T00:00:00"
            env = dict(os.environ, GIT_COMMITTER_DATE=day, GIT_AUTHOR_DATE=day)
            (self.repo / "tools/run.py").write_text(f"old {i}\n")
            self.git("add", "-A")
            subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@e", "commit", "-qm", f"o{i}"],
                           cwd=self.repo, env=env, check=True)
            olds.append(self.git("rev-parse", "HEAD"))
        for c in olds:
            self.git("push", "-q", str(self.mirror), f"{c}:refs/cl/{c}")
        subprocess.run(["bash", "-c", G.housekeep_script(str(self.mirror), keep_days=14, keep_min=1)], check=True)
        refs = self.git("--git-dir", str(self.mirror), "for-each-ref", "--format=%(refname)", "refs/cl/",
                        cwd=self.root).split()
        self.assertEqual(refs, [f"refs/cl/{olds[-1]}"])
        # stamped: a second run the same day is a no-op
        self.git("push", "-q", str(self.mirror), f"{olds[0]}:refs/cl/{olds[0]}")
        subprocess.run(["bash", "-c", G.housekeep_script(str(self.mirror), keep_days=14, keep_min=1)], check=True)
        self.assertEqual(len(self.git("--git-dir", str(self.mirror), "for-each-ref", "refs/cl/",
                                      cwd=self.root).split("\n")), 2)


class MirrorUnitTest(unittest.TestCase):
    def test_config(self):
        self.assertIsNone(G.config({}))
        self.assertIsNone(G.config({"git_mirror": "relative/path"}))
        self.assertEqual(G.config({"git_mirror": "/m.git", "git_mirror_upstream": "https://u"}), ("/m.git", "https://u"))

    def test_push_command_uses_direct_bulk_connection(self):
        prefix = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ControlMaster=no", "ot-epyc3"]
        argv, env = G.push_command("/repo", "ot-epyc3", "/srv/m.git", "a" * 40, prefix)
        self.assertEqual(argv[-2:], ["ssh://ot-epyc3/srv/m.git", f"{'a' * 40}:refs/cl/{'a' * 40}"])
        self.assertIn("core.hooksPath=/dev/null", argv)
        self.assertEqual(env["GIT_SSH_COMMAND"],
                         "ssh -o BatchMode=yes -o ControlPath=none -o ControlMaster=no")
        with self.assertRaises(ValueError):
            G.push_command("/repo", "ot-epyc3", "/srv/m.git", "a" * 40, prefix[:-1])

    def test_pushed_objects(self):
        self.assertEqual(G.pushed_objects("Writing objects:  50% (1/2)\rWriting objects: 100% (2/2), done.\n"), 2)
        self.assertEqual(G.pushed_objects("Everything up-to-date"), 0)

    def test_extract_script_receipt_guards(self):
        receipt = dict(commit="b" * 40, paths=["tools"], archive_sha256="c" * 64, required_sha256={"tools/x": "d" * 64})
        s = G.extract_script("/m", "b" * 40, ["ignored"], "/run", receipt)
        self.assertIn("--literal-pathspecs", s)
        self.assertIn(" -- tools >", s)
        self.assertIn("c" * 64, s)
        self.assertIn(f"{'d' * 64}  tools/x", s)
        with self.assertRaises(ValueError):
            G.extract_script("/m", "e" * 40, ["tools"], "/run", receipt)
        with self.assertRaises(ValueError):
            G.extract_script("/m", "b" * 40, ["tools"], "/run", dict(receipt, required_sha256={}))

    def test_sequence_and_fallback_with_mocks(self):
        calls = []

        def fake_ssh(host, script, timeout=120, check=False, input=None):
            calls.append(("ssh", script.splitlines()[0][:40]))
            if "MIRROR_READY" in script:
                return subprocess.CompletedProcess([], 0, "MIRROR_READY\n", "")
            return subprocess.CompletedProcess([], 0, "GIT_MIRROR_EXTRACTED\n", "")

        @contextmanager
        def fake_transport(host, *, wait_s=None, bulk=False):
            calls.append(("lease", bulk))
            yield ["ssh", "-o", "ControlPath=none", host]

        def fake_run(argv, **kw):
            calls.append(("push", argv[-1]))
            return subprocess.CompletedProcess(argv, 0, "", "Writing objects: 100% (3/3), done.")
        j = {"name": "j", "spec": {"source": {"branch": "main"}}}
        full = "f" * 40
        with patch.object(C, "host_cfg", return_value={"git_mirror": "/m.git"}), \
                patch.object(C, "ssh", side_effect=fake_ssh), \
                patch.object(C, "transport_command", side_effect=fake_transport), \
                patch.object(C.subprocess, "run", side_effect=fake_run):
            self.assertTrue(C.mirror_sync(j, "ot-epyc3", "/run", full, ["tools"], None))
        kinds = [c[0] for c in calls]
        self.assertEqual(kinds, ["ssh", "lease", "push", "ssh", "ssh"])   # probe, bulk lease, push, extract, gc
        self.assertEqual(calls[1], ("lease", True))
        self.assertTrue(any("via push 3 objects" in e for e in j["events"]))

        def failing_run(argv, **kw):
            return subprocess.CompletedProcess(argv, 1, "", "fatal: the remote end hung up")
        j2 = {"name": "j", "spec": {"source": {"branch": "main"}}}
        with patch.object(C, "host_cfg", return_value={"git_mirror": "/m.git"}), \
                patch.object(C, "ssh", side_effect=fake_ssh), \
                patch.object(C, "transport_command", side_effect=fake_transport), \
                patch.object(C.subprocess, "run", side_effect=failing_run):
            self.assertFalse(C.mirror_sync(j2, "ot-epyc3", "/run", full, ["tools"], None))
        self.assertTrue(any("git-mirror sync failed" in e and "hung up" in e for e in j2["events"]))
        self.assertFalse(C.mirror_sync(j2, "localhost", "/run", full, ["tools"], None))


if __name__ == "__main__":
    unittest.main()
