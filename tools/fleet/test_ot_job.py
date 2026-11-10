"""ISOLATE-1: sealed jobs (ot-job + ot-job-docker + ot-run --job) and the content-addressed store (ot_store.py).

The positive control is test_undeclared_path_fails: a job that reads a host path it did not declare must FAIL, and
the same job with the path declared must pass.  The bwrap tests need a writable /srv/opentallas-scratch* base
(OT_JOB_TEST_BASE) so that hiding /srv is really exercised; they skip where bwrap cannot run.
"""
import base64
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_store as S  # noqa: E402
import signed_store as SS  # noqa: E402


def load(name, fn):
    loader = importlib.machinery.SourceFileLoader(name, str(HERE / fn))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


SHIM = load("ot_job_docker", "ot-job-docker")
JOB = load("ot_job", "ot-job")


def bwrap_ok():
    try:
        return subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _test_base():
    for b in (os.environ.get("OT_JOB_TEST_BASE"), "/srv/opentallas-scratch2/claude/isolate-1/tests"):
        if b and os.path.isdir(os.path.dirname(b)) and os.access(os.path.dirname(b), os.W_OK):
            os.makedirs(b, exist_ok=True)
            return b
    return None


class Tmp(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="otjob-")
        self.addCleanup(self._rm, self.t)
        self.store = os.path.join(self.t, "store")

    @staticmethod
    def _rm(p):
        for dp, dns, _ in os.walk(p):
            for d in dns:
                try:
                    os.chmod(os.path.join(dp, d), 0o755)
                except OSError:
                    pass
        shutil.rmtree(p, ignore_errors=True)

    def mk(self, rel, text="x", root=None):
        p = os.path.join(root or self.t, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
        return p


class SeedMtime(Tmp):
    OLD_V, OLD_SDC = 1_700_000_000, 1_600_000_000

    def kit(self):
        K = os.path.join(self.t, "K")
        os.makedirs(K + "/run/results")
        with open(K + "/run/results/1_2_yosys.v", "w") as fh:
            fh.write("netlist")
        with open(K + "/vclk_ff.sdc", "w") as fh:
            fh.write("sdc")
        os.utime(K + "/run/results/1_2_yosys.v", (self.OLD_V, self.OLD_V))
        os.utime(K + "/vclk_ff.sdc", (self.OLD_SDC, self.OLD_SDC))
        return K

    def staged(self, item):
        J = os.path.join(self.t, "J")
        os.makedirs(J + "/.ot-job")
        os.makedirs(J + "/work")
        JOB.stage_all({"work": {"seed": [item]}}, self.store, J, [])
        return J + "/work"

    def check(self, w):
        self.assertEqual(os.stat(w + "/run/results/1_2_yosys.v").st_mtime, self.OLD_V)
        self.assertEqual(os.stat(w + "/vclk_ff.sdc").st_mtime, self.OLD_SDC)
        self.assertLess(os.stat(w + "/vclk_ff.sdc").st_mtime, os.stat(w + "/run/results/1_2_yosys.v").st_mtime)

    def test_local_seed_keeps_source_mtimes(self):
        self.check(self.staged({"path": self.kit()}))

    def test_fetched_seed_keeps_source_mtimes(self):
        K = self.kit()

        def fake(host, path, dest):
            os.makedirs(dest)
            out = os.path.join(dest, "K")
            shutil.copytree(K, out)
            return out
        real, JOB.tar_fetch = JOB.tar_fetch, fake
        try:
            self.check(self.staged({"path": "/no/such/K", "host": "h"}))
        finally:
            JOB.tar_fetch = real

    def test_seed_file_keeps_its_mtime(self):
        K = self.kit()
        J = os.path.join(self.t, "J")
        os.makedirs(J + "/.ot-job")
        os.makedirs(J + "/work")
        JOB.stage_all({"work": {"seed": [{"path": K + "/vclk_ff.sdc", "into": "vclk_ff.sdc"}]}}, self.store, J, [])
        self.assertEqual(os.stat(J + "/work/vclk_ff.sdc").st_mtime, self.OLD_SDC)


class ReturnMtime(Tmp):
    """RETURN-MTIME: copy_out (the return copy) keeps source mtimes, so restored checkpoints stay newer than inputs"""
    OLD_V, OLD_SDC = 1_700_000_000, 1_600_000_000

    def tree(self):
        w = os.path.join(self.t, "work")
        self.mk("run/results/3_5_place_dp.odb", "odb", w)
        self.mk("rtl/a.sv", "rtl", w)
        os.utime(w + "/run/results/3_5_place_dp.odb", (self.OLD_V, self.OLD_V))
        os.utime(w + "/rtl/a.sv", (self.OLD_SDC, self.OLD_SDC))
        return w

    def test_returned_tree_keeps_source_mtimes(self):
        w, K = self.tree(), os.path.join(self.t, "K")
        JOB.copy_out(w, K)
        self.assertEqual(os.stat(K + "/run/results/3_5_place_dp.odb").st_mtime, self.OLD_V)
        self.assertEqual(os.stat(K + "/rtl/a.sv").st_mtime, self.OLD_SDC)
        self.assertLess(os.stat(K + "/rtl/a.sv").st_mtime, os.stat(K + "/run/results/3_5_place_dp.odb").st_mtime)

    def test_identical_dst_takes_source_date_unless_hardlinked(self):
        w, K = self.tree(), os.path.join(self.t, "K")
        self.mk("rtl/a.sv", "rtl", K)
        self.mk("run/results/3_5_place_dp.odb", "odb", K)
        os.link(K + "/run/results/3_5_place_dp.odb", os.path.join(self.t, "shared.odb"))
        before = os.stat(K + "/run/results/3_5_place_dp.odb").st_mtime
        JOB.copy_out(w, K)
        self.assertEqual(os.stat(K + "/rtl/a.sv").st_mtime, self.OLD_SDC)
        self.assertEqual(os.stat(K + "/run/results/3_5_place_dp.odb").st_mtime, before)
        self.assertEqual(os.stat(os.path.join(self.t, "shared.odb")).st_nlink, 2)


class Store(Tmp):
    def test_tree_dedup_stage_ro_and_copy(self):
        self.mk("a/x.txt", "same")
        self.mk("a/sub/y.txt", "y")
        os.symlink("sub/y.txt", os.path.join(self.t, "a/ly"))
        self.mk("b/x.txt", "same")
        ta = S.put_tree(self.store, os.path.join(self.t, "a"))
        S.put_tree(self.store, os.path.join(self.t, "b"))
        objs = [f for _, _, fs in os.walk(os.path.join(self.store, "objects")) for f in fs]
        self.assertEqual(len(objs), 4)                     # same, y, tree a, tree b: "same" stored once
        ro = os.path.join(self.t, "ro")
        S.stage(self.store, ta, ro)
        self.assertEqual(open(os.path.join(ro, "ly")).read(), "y")
        self.assertGreater(os.stat(os.path.join(ro, "x.txt")).st_nlink, 1)       # hardlink: no disk cost
        self.assertFalse(os.access(os.path.join(ro, "x.txt"), os.W_OK))
        with self.assertRaises(OSError):
            open(os.path.join(ro, "new"), "w")                                   # dirs read-only too
        cp = os.path.join(self.t, "cp")
        S.stage(self.store, ta, cp, copy=True)
        with open(os.path.join(cp, "x.txt"), "w") as fh:
            fh.write("changed")
        self.assertEqual(S.verify(self.store, ta), [])                          # a work copy never touches the store

    def test_escaping_symlink_refused(self):
        self.mk("a/x", "1")
        os.symlink("/srv/elsewhere/kit", os.path.join(self.t, "a/abs"))
        with self.assertRaises(S.StoreError):
            S.put_tree(self.store, os.path.join(self.t, "a"))
        os.unlink(os.path.join(self.t, "a/abs"))
        os.symlink("../../out", os.path.join(self.t, "a/up"))
        with self.assertRaises(S.StoreError):
            S.put_tree(self.store, os.path.join(self.t, "a"))

    def test_verify_finds_corruption(self):
        sha = S.put_file(self.store, self.mk("f", "abc"))
        p = S.obj_path(self.store, sha)
        os.chmod(p, 0o644)
        with open(p, "w") as fh:
            fh.write("abd")
        self.assertEqual(S.verify(self.store, sha), [f"corrupt {sha}"])

    def test_publish_record_is_a_signed_store_entry(self):
        self.mk("out/6_final.odb", "db")
        rec = S.publish(self.store, os.path.join(self.t, "out"), "route", {"job": "J", "host": "h", "rc": 0})
        got = SS.read_manifest(store=self.store)
        self.assertEqual([e["id"] for e in got], [rec["id"]])
        self.assertEqual(got[0]["producer"]["job"], "J")
        self.assertEqual(SS.entry_files(dict(got[0], archive="store"))[0][:3], ["6_final.odb", 2, S.sha_file(os.path.join(self.t, "out/6_final.odb"))])

    def test_gc_by_reference_only(self):
        old = time.time() - 3 * 86400
        keep_ref = S.put_file(self.store, self.mk("r", "ref"))
        counted = S.put_file(self.store, self.mk("c", "counted"))
        young = S.put_file(self.store, self.mk("y", "young"))
        dead = S.put_file(self.store, self.mk("d", "dead"))
        for s in (keep_ref, counted, dead):
            os.utime(S.obj_path(self.store, s), (old, old))
        S.ref(self.store, "job-t1", [keep_ref])
        cs = os.path.join(self.t, "counted")
        SS.write_entry({"id": "c" * 64, "files": [["v.v", 7, counted]], "archive": "/a"}, store=cs)
        r = S.gc(self.store, counted_store=cs)
        self.assertEqual(r["delete"], [dead])
        self.assertTrue(S.have(self.store, dead))                               # dry by default
        S.gc(self.store, counted_store=cs, apply=True)
        self.assertEqual([S.have(self.store, x) for x in (keep_ref, counted, young, dead)], [True, True, True, False])
        S.unref(self.store, "job-t1")
        self.assertIn(keep_ref, S.gc(self.store, counted_store=cs)["delete"])   # job ended: its inputs may go

    def test_fetch_rehashes(self):
        other = os.path.join(self.t, "other")
        sha = S.put_tree(other, os.path.dirname(self.mk("k/a", "A")))

        def runner(argv, stdout=None, stderr=None, **kw):
            path = argv[-1].split(" ", 1)[1].strip("'")
            with open(path.replace(self.store, other), "rb") as fh:
                stdout.write(fh.read())
            return subprocess.CompletedProcess(argv, 0)
        S.fetch(self.store, sha, "h", runner=runner)
        self.assertEqual(S.verify(self.store, sha), [])

        def liar(argv, stdout=None, stderr=None, **kw):
            stdout.write(b"not it")
            return subprocess.CompletedProcess(argv, 0)
        with self.assertRaises(S.StoreError):
            S.fetch(os.path.join(self.t, "s3"), sha, "h", runner=liar)


class Shim(Tmp):
    def setUp(self):
        super().setUp()
        self.J = os.path.join(self.t, "J")
        self.inp = self.mk("J/in/0/f", "in")
        os.makedirs(os.path.join(self.J, "work/sub"))
        self.m = {"job": self.J, "maps": [{"at": "/srv/x/kit_in", "real": self.J + "/in/0", "ro": True},
                                           {"at": self.J + "/work", "real": self.J + "/work", "ro": False},
                                           {"at": self.J, "real": self.J, "ro": False}], "allow_ro": []}
        self.maps = sorted(self.m["maps"], key=lambda x: -len(x["at"]))

    def chk(self, *argv):
        return SHIM.check(list(argv), self.m, self.maps)

    def test_declared_input_rewritten_read_only(self):
        a = self.chk("run", "--rm", "-v", "/srv/x/kit_in/sub:/c", "img", "cat", "-v", "/etc/passwd")
        self.assertEqual(a[3], self.J + "/in/0/sub:/c:ro")
        self.assertEqual(a[-2:], ["-v", "/etc/passwd"])                          # the container command is untouched

    def test_work_stays_writable(self):
        a = self.chk("run", "-v", self.J + "/work:/work", "--name", "n", "img")
        self.assertEqual(a[2], os.path.realpath(self.J + "/work") + ":/work")

    def test_undeclared_refused(self):
        for argv in (("run", "-v", "/srv/opentallas-scratch3/claude/other/kit:/work", "img"),
                     ("container", "run", "--volume=/home/ubuntu/coord:/c", "img"),
                     ("run", "--mount", "type=bind,source=/srv/y,target=/y", "img"),
                     ("run", "-v", "named_vol:/x", "img"),
                     ("run", "--privileged", "img"),
                     ("run", "--volumes-from", "c1", "img"),
                     ("-H", "tcp://x", "run", "img"),
                     ("build", "/srv/z"),
                     ("cp", "/srv/other/file", "c1:/x")):
            with self.assertRaises(SHIM.Refused, msg=argv):
                self.chk(*argv)

    def test_symlink_out_of_work_refused(self):
        os.symlink("/srv/opentallas-scratch3/claude/other", os.path.join(self.J, "work/esc"))
        with self.assertRaises(SHIM.Refused):
            self.chk("run", "-v", self.J + "/work/esc:/e", "img")

    def test_mount_bind_forced_readonly(self):
        a = self.chk("create", "--mount", "type=bind,src=/srv/x/kit_in,dst=/k", "img")
        self.assertEqual(a[2], f"type=bind,src={self.J}/in/0,dst=/k,readonly")

    def test_cp_into_read_only_input_refused(self):
        with self.assertRaises(SHIM.Refused):
            self.chk("cp", "c1:/out", "/srv/x/kit_in/f")
        a = self.chk("cp", "c1:/out", self.J + "/work/out")
        self.assertEqual(a[2], os.path.realpath(self.J + "/work") + "/out")

    def test_other_subcommands_pass(self):
        self.assertEqual(self.chk("ps", "-q"), ["ps", "-q"])
        self.assertEqual(self.chk("rm", "-f", "n"), ["rm", "-f", "n"])


class OtRun(Tmp):
    def test_job_wrap(self):
        m = load("ot_run_job", "ot-run")
        sp = self.mk("spec.json", json.dumps({"schema": "opentallas.ot_job.v1", "name": "p"}))
        argv = m.job_wrap(["bash", "run_kit.sh", "place"], sp)
        self.assertEqual(argv[1:3], ["run", "--spec-b64"])
        self.assertEqual(json.loads(base64.b64decode(argv[3]))["name"], "p")
        self.assertEqual(argv[4:], ["--", "bash", "run_kit.sh", "place"])
        bad = self.mk("bad.json", json.dumps({"schema": "x"}))
        with self.assertRaises(SystemExit):
            m.job_wrap(["true"], bad)


class Sealer(Tmp):
    """ot-run-sealed: only the wave's place call under a pilot dir is sealed; everything else passes unchanged"""

    def setUp(self):
        super().setUp()
        self.w = load("ot_run_sealed", "ot-run-sealed")
        self.K = "/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/qwen_kvsys/kit-wave/qwen_kvsys/e/items/kv3_phy/attempt_8/gen/kv3_phy"
        self.R = os.path.dirname(self.K) + "/run_kit.sh"
        self.conf = {"enabled": True, "host": "epyc7", "dirs": ["/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/qwen_kvsys/"],
                     "backend": "/b/ot-run", "sealed_backend": "/s/ot-run", "spec_dir": self.t}
        self.cmd = ["--", "bash", "-c", f"bash {self.R} {self.K} place 48 16"]

    def test_sync_and_async_place_sealed(self):
        for pre in (["--mem", "48", "--threads", "16", "--dir", self.K, "--hosts", "epyc4,epyc7", "--crit"],
                    ["--mem", "48", "--threads", "16", "--dir", self.K, "--stage", self.K, "--stage", self.R]):
            argv, why = self.w.decide(pre + self.cmd, self.conf, check=lambda h, r, k: (True, ["/srv/opentallas-scratch2/claude/die-kv-9/signed/kv_leaf"]))
            self.assertEqual(argv[:9], ["/s/ot-run", "--mem", "48", "--threads", "16", "--hosts", "epyc7", "--job", argv[8]], why)
            self.assertEqual(argv[-4:], self.cmd)
            spec = json.load(open(argv[8]))
            self.assertEqual(spec["work"], {"at": self.K, "seed": [{"path": self.K}]})
            self.assertEqual(spec["inputs"], [{"path": self.R}, {"path": "/srv/opentallas-scratch2/claude/die-kv-9/signed/kv_leaf"}])
            self.assertEqual(spec["return"], {"to": self.K, "paths": ["."]})

    def test_passthrough(self):
        ok = lambda h, r, k: (True, [])
        base = ["--mem", "48", "--dir", self.K]
        cases = [(dict(self.conf, enabled=False), base + self.cmd, ok),
                 (self.conf, ["--status"], ok),
                 (self.conf, base + ["--", "bash", "-c", f"bash {self.R} {self.K} route 48 16"], ok),
                 (self.conf, ["--mem", "48", "--dir", "/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/hbm/x"]
                  + ["--", "bash", "-c", "bash /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/hbm/r.sh /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/hbm/x place 4 4"], ok),
                 (self.conf, base + ["--pick"] + self.cmd, ok),
                 (self.conf, base + self.cmd, lambda h, r, k: (False, []))]
        for conf, argv, chk in cases:
            out, why = self.w.decide(argv, conf, check=chk)
            self.assertEqual(out, ["/b/ot-run"] + argv, why)


@unittest.skipUnless(bwrap_ok() and _test_base(), "needs bwrap and a writable /srv/opentallas-scratch* test base")
class Sealed(Tmp):
    """end to end: bwrap view, docker shim, publish, return, delete"""

    def setUp(self):
        super().setUp()
        self.base = tempfile.mkdtemp(prefix="t-", dir=_test_base())
        self.addCleanup(self._rm, self.base)
        self.store = os.path.join(self.base, "store")
        self.root = os.path.join(self.base, "jobs")
        os.makedirs(self.root)
        self.src = os.path.dirname(self.mk("lane_a/kit/f.txt", "declared", root=self.base))
        self.secret = self.mk("lane_b/gen/split_clean.json", "undeclared", root=self.base)
        self.ret = os.path.join(self.base, "caller")
        fake = self.mk("fake_docker", "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$OT_JOB_DIR/work/docker_argv\"\n", root=self.base)
        os.chmod(fake, 0o755)
        self.env = dict(os.environ, OT_STORE=self.store, OT_JOB_NEXT_DOCKER=fake)

    def job(self, cmd, inputs=(), publish=(), ret=None, **extra):
        spec = dict({"schema": JOB.SCHEMA, "name": "t", "root": self.root, "inputs": list(inputs),
                     "publish": list(publish)}, **extra)
        if ret:
            spec["return"] = {"to": self.ret, "paths": ret}
        sp = self.mk("spec.json", json.dumps(spec), root=self.base)
        return subprocess.run([sys.executable, "-I", str(HERE / "ot-job"), "run", "--spec", sp, "--", "sh", "-c", cmd],
                              env=self.env, capture_output=True, text=True, timeout=120)

    def jobs_left(self):
        return [x for x in os.listdir(self.root) if x != JOB.MARKER]

    def test_declared_input_read_publish_return_delete(self):
        r = self.job(f"cat {self.src}/f.txt > out.txt && mkdir -p run && echo db > run/6_final.odb",
                     inputs=[{"path": self.src}], publish=[{"name": "route", "path": "run", "required": True}],
                     ret=["out.txt"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(os.path.join(self.ret, "out.txt")).read(), "declared")
        self.assertEqual(self.jobs_left(), [], "finished job dir must be deleted")
        recs = S.records(self.store)
        self.assertEqual([e["name"] for e in recs], ["route"])
        self.assertEqual(recs[0]["producer"]["rc"], 0)
        self.assertEqual(S.verify(self.store, recs[0]["sha"]), [])
        self.assertEqual(S.refs(self.store), {}, "the live-input ref is dropped at job end")
        res = json.load(open([os.path.join(self.ret, f) for f in os.listdir(self.ret) if f.startswith(".ot-job-")][0]))
        self.assertEqual(res["published"][0]["sha"], recs[0]["sha"])

    def test_return_never_writes_through_a_hardlink(self):
        os.makedirs(self.ret)
        shared = self.mk("shared/x.txt", "shared", root=self.base)
        os.link(shared, os.path.join(self.ret, "x.txt"))             # the caller's file is a link into another tree
        r = self.job("echo mine > x.txt", ret=["x.txt"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(os.path.join(self.ret, "x.txt")).read(), "mine\n")
        self.assertEqual(open(shared).read(), "shared")

    def test_undeclared_path_fails(self):
        """POSITIVE CONTROL: reading another job's dir without declaring it fails; declared, the same read passes"""
        r = self.job(f"cat {self.secret}")
        self.assertNotEqual(r.returncode, 0, "an undeclared host path was readable inside the sealed job")
        self.assertIn("No such file", r.stderr)
        r2 = self.job(f"cat {self.secret}", inputs=[{"path": os.path.dirname(self.secret)}])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("undeclared", r2.stdout)

    def test_inputs_read_only_inside(self):
        r = self.job(f"echo x > {self.src}/f.txt", inputs=[{"path": self.src}])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(os.path.join(self.src, "f.txt")).read(), "declared")

    def test_home_and_tmp_hidden(self):
        home = os.path.expanduser("~")
        probe = next((p for p in (os.path.join(home, "coord"), os.path.join(home, ".ssh"), os.path.join(home, "OpenTallas"))
                      if os.path.exists(p)), None)
        if probe is None:
            self.skipTest("no home dir to probe")
        r = self.job(f"ls {probe}")
        self.assertNotEqual(r.returncode, 0)

    def test_docker_mount_checked(self):
        r = self.job(f"docker run --rm -v {os.path.dirname(self.secret)}:/x alpine true")
        self.assertEqual(r.returncode, SHIM.REFUSE, r.stderr)
        self.assertIn("OT-JOB ISOLATION: undeclared host path", r.stderr)
        r = self.job(f"docker run --rm -v {os.path.dirname(self.secret)}:/x alpine true; true", ret=["none"])
        res = json.load(open([os.path.join(self.ret, f) for f in os.listdir(self.ret) if f.startswith(".ot-job-")][0]))
        self.assertIn("undeclared host path", res["refusals"][0]["why"])     # the refusal survives the job dir delete
        shutil.rmtree(self.ret)
        r = self.job(f"docker run --rm -v {self.src}:/x alpine cat /x/f.txt; cp docker_argv argv.txt",
                     inputs=[{"path": self.src}], ret=["argv.txt"])
        self.assertEqual(r.returncode, 0, r.stderr)
        argv = open(os.path.join(self.ret, "argv.txt")).read().split("\n")
        mounted = argv[argv.index("-v") + 1]
        self.assertTrue(mounted.endswith("/in/0:/x:ro") and mounted.startswith(self.root), mounted)

    def test_publish_failure_keeps_job_dir(self):
        r = self.job("true", publish=[{"name": "kit", "path": "kit_out", "required": True}])
        self.assertEqual(r.returncode, JOB.PUBLISH_FAIL)
        left = self.jobs_left()
        self.assertEqual(len(left), 1)
        self.assertTrue(os.path.isfile(os.path.join(self.root, left[0], JOB.MARKER)), "AUTOCLEAN-13 marker at the job root")
        self.assertTrue(os.path.isfile(os.path.join(self.store, JOB.MARKER)))
        self.assertTrue(os.path.isfile(os.path.join(self.root, left[0], ".ot-job/result.json")))

    def test_root_owned_output_still_deleted(self):
        if subprocess.run(["docker", "image", "inspect", "alpine:latest"], capture_output=True).returncode:
            self.skipTest("needs docker + alpine")
        env = dict(self.env)
        env.pop("OT_JOB_NEXT_DOCKER", None)
        self.env = env
        r = self.job(f"docker run --rm -v $OT_JOB_DIR/work:/w alpine sh -c 'mkdir -p /w/r && touch /w/r/x && chmod 700 /w/r'")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.jobs_left(), [])

    def test_stopped_job_publishes_returns_and_deletes(self):
        """KW-FIX-44 step 5: a job STOPPED by SIGTERM (an ot-heavy unit stop) still publishes its "always" outputs,
        returns, and deletes J; rc 128+15"""
        spec = {"schema": JOB.SCHEMA, "name": "t", "root": self.root, "inputs": [],
                "publish": [{"name": "stopped-run", "path": "run", "when": "always"}],
                "return": {"to": self.ret, "paths": ["run"]}}
        sp = self.mk("spec.json", json.dumps(spec), root=self.base)
        p = subprocess.Popen([sys.executable, "-I", str(HERE / "ot-job"), "run", "--spec", sp, "--", "sh", "-c",
                              "mkdir -p run && echo partial > run/log && touch started && exec sleep 60"],
                             env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(200):
            if any(os.path.exists(os.path.join(self.root, j, "work", "started")) for j in self.jobs_left()):
                break
            time.sleep(0.05)
        p.terminate()
        _out, err = p.communicate(timeout=60)
        self.assertEqual(p.returncode, 128 + 15, err)
        self.assertEqual(self.jobs_left(), [], "a stopped job dir must be deleted too")
        self.assertEqual(open(os.path.join(self.ret, "run", "log")).read(), "partial\n")
        self.assertEqual([e["name"] for e in S.records(self.store)], ["stopped-run"])

    def test_reap_deletes_dead_jobs_only(self):
        """a J whose ot-job died (SIGKILL) is reaped; a live J, a keep=true J and a legacy J (no lock) are not"""
        spec = {"schema": JOB.SCHEMA, "name": "t", "root": self.root, "inputs": []}
        sp = self.mk("spec.json", json.dumps(spec), root=self.base)
        def start(cmd, sp=sp):
            return subprocess.Popen([sys.executable, "-I", str(HERE / "ot-job"), "run", "--spec", sp, "--", "sh", "-c", cmd],
                                    env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        def wait_for(n):
            for _ in range(200):
                if len([j for j in self.jobs_left() if os.path.exists(os.path.join(self.root, j, "work", "up"))]) >= n:
                    return
                time.sleep(0.05)
            self.fail(f"{n} jobs did not start")
        live = start("touch up; exec sleep 60")
        dead = start("touch up; exec sleep 60")
        wait_for(2)
        os.kill(dead.pid, 9)                     # ot-job SIGKILLed: its command still runs and keeps J locked
        dead.wait()
        time.sleep(0.5)
        self.assertEqual(JOB.reap([self.root], say_=lambda m: None)["reaped"], [], "J is in use while its command lives")
        dj = [j for j in self.jobs_left() if j.endswith(f"-{dead.pid}-") or f"-{dead.pid}-" in j][0]
        os.killpg(int(open(os.path.join(self.root, dj, ".ot-job", "cmd.pgid")).read()), 9)   # orphan dies: J is free
        import socket
        legacy = os.path.join(self.root, "old-legacy")             # pid of a live ot-job: kept
        gone = os.path.join(self.root, "old-gone")                  # pid gone: reaped
        for d, pid in ((legacy, live.pid), (gone, dead.pid)):
            os.makedirs(os.path.join(d, ".ot-job"))
            json.dump({"kind": "ot-job"}, open(os.path.join(d, JOB.MARKER), "w"))
            json.dump({"spec": {}, "host": socket.gethostname(), "pid": pid}, open(os.path.join(d, ".ot-job", "job.json"), "w"))
        reaped, r = [], None
        for _ in range(100):                     # the dead job's command has gone (lock released)
            r = JOB.reap([self.root], say_=lambda m: None)
            reaped += r["reaped"]
            if len(reaped) >= 2:
                break
            time.sleep(0.1)
        self.assertIn(gone, reaped)
        self.assertEqual(len(reaped), 2, reaped)
        self.assertEqual(r["live"], 1)
        self.assertEqual(r["legacy"], [legacy])
        self.assertTrue(os.path.isdir(legacy))
        live.terminate()
        live.wait(timeout=60)
        self.assertEqual(self.jobs_left(), ["old-legacy"])

    def test_shim_labels_containers_with_the_job_dir(self):
        m = {"job": "/srv/x/J", "maps": [], "allow_ro": []}
        a = SHIM.check(["run", "--rm", "alpine", "true"], m, [])
        self.assertEqual(a, ["run", "--rm", "--label", "ot-job.dir=/srv/x/J", "alpine", "true"])

    def test_bad_input_cleans_up(self):
        r = self.job("true", inputs=[{"path": os.path.join(self.base, "nope")}])
        self.assertEqual(r.returncode, JOB.SPEC_FAIL)
        self.assertEqual(self.jobs_left(), [])

    def test_input_by_sha(self):
        kind, sha = S.put(self.store, self.src)
        shutil.rmtree(self.src)                  # the producer's dir is gone; the store copy is enough
        r = self.job(f"cat {self.src}/f.txt", inputs=[{"sha": sha, "at": self.src}])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "declared")


@unittest.skipUnless(bwrap_ok() and _test_base() and shutil.which("docker")
                     and subprocess.run(["docker", "image", "inspect", "alpine:latest"], capture_output=True).returncode == 0,
                     "needs bwrap, docker and alpine:latest")
class RealDocker(Sealed):
    """the same through the real daemon: a declared input is visible in the container, an undeclared one is refused"""

    def setUp(self):
        super().setUp()
        self.env.pop("OT_JOB_NEXT_DOCKER")

    def test_docker_mount_checked(self):
        r = self.job(f"docker run --rm -v {self.src}:/x alpine cat /x/f.txt", inputs=[{"path": self.src}])
        self.assertEqual((r.returncode, r.stdout), (0, "declared"), r.stderr)
        r = self.job(f"docker run --rm -v {self.src}:/x alpine sh -c 'echo y > /x/f.txt'", inputs=[{"path": self.src}])
        self.assertNotEqual(r.returncode, 0, "a container wrote into a read-only input")
        r = self.job(f"docker run --rm -v {os.path.dirname(self.secret)}:/x alpine cat /x/split_clean.json")
        self.assertEqual(r.returncode, SHIM.REFUSE)
        r = self.job(f"/usr/bin/docker run --rm -v {os.path.dirname(self.secret)}:/x alpine true")
        self.assertEqual(r.returncode, SHIM.REFUSE, "calling /usr/bin/docker by path must hit the shim too")


if __name__ == "__main__":
    unittest.main()
