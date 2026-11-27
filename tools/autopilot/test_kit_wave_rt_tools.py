"""TOOLS-DECOUPLE-1118: kits take tools/ and physical/common_flow from the scheduler's rt/<sha12> snapshot, resolved once at launch
(spec.json tools_rt / tools_sha); the die tree keeps the design data; tools_refresh and the tool-skew refusal are off for such dies."""
import inspect
import json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW

SH = HERE / "rt_launch_tree.sh"
SHA = "0d6591bd9617a1c02e269e3c3f63ae89ebcd6a58"


def w(p, txt):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)


class SchedulerRt(unittest.TestCase):
    def test_rt_snapshot_dir_gives_full_sha(self):
        with tempfile.TemporaryDirectory() as t:
            rt = Path(t) / SHA[:12]
            rt.mkdir()
            (Path(t) / f"{SHA[:12]}.manifest.json").write_text(json.dumps({"sha": SHA, "files": {}}))
            self.assertEqual(KW.scheduler_rt(rt), (str(rt), SHA))

    def test_checkout_is_not_an_rt_snapshot(self):
        self.assertEqual(KW.scheduler_rt(Path("/x/OpenTallas")), (None, None))

    def test_fields_and_opt_out(self):
        cfg = {"dies": {"s81": {}, "qc": {"tools_from_rt": False}}}
        with mock.patch.object(KW, "scheduler_rt", return_value=("/r/rt/0d6591bd9617", SHA)):
            self.assertEqual(KW.rt_tools_fields(cfg, "s81"), {"tools_rt": "/r/rt/0d6591bd9617", "tools_sha": SHA})
            self.assertEqual(KW.rt_tools_fields(cfg, "qc"), {})
            self.assertFalse(KW.tool_skew_refuse(None, cfg, {}, "s81"))

    def test_item_pin_matches_only_its_event_source_and_effective_bind(self):
        source = "c" * 64
        d = {"event": "E1", "src_manifest_hash": "d" * 64, "kit_rtl": {"bind_out": "/x/bind"},
             "item_inputs": {"t": {"src_manifest_hash": source,
                                   "gen_tools_pin": {"event": "E1", "src_manifest_hash": source, "bind_out": "/x/bind"}}}}
        self.assertEqual(KW.item_gen_tools_manifest(d, "t"), source)
        self.assertEqual(KW.item_gen_tools_manifest(d, "other"), "")
        self.assertEqual(KW.item_gen_tools_manifest(dict(d, event="E2"), "t"), "")
        self.assertEqual(KW.item_gen_tools_manifest(dict(d, kit_rtl={"bind_out": "/x/next"}), "t"), "")
        d["item_inputs"]["t"]["kit_rtl"] = {"bind_out": "/x/override"}
        self.assertEqual(KW.item_gen_tools_manifest(d, "t"), "")
        d["item_inputs"]["t"]["gen_tools_pin"]["bind_out"] = "/x/override"
        self.assertEqual(KW.item_gen_tools_manifest(d, "t"), source)
        d["item_inputs"]["t"]["src_manifest_hash"] = "e" * 64
        self.assertEqual(KW.item_gen_tools_manifest(d, "t"), "")

    def test_item_pin_rekeys_gen_and_keeps_late_flow_on_runtime(self):
        source = "a" * 64
        d = {"event": "E1", "src_manifest_hash": source, "kit_rtl": {"bind_out": "/x/bind"},
             "item_inputs": {"t": {"gen_tools_pin": {"event": "E1", "src_manifest_hash": source, "bind_out": "/x/bind"}}}}
        cfg = {"dies": {"s81": d}}
        for rt in ("runtime-before", "runtime-after"):
            with mock.patch.object(KW, "exec_family_digests", return_value={"gen": rt, "kit": rt, "flow": rt}), \
                 mock.patch.object(KW, "stage_tools_digests", return_value={"gen": rt, "kit_rtl": rt, "route": rt}):
                pin = KW.input_parts(cfg, "s81", "t")
                sibling = KW.input_parts(cfg, "s81", "other")
                self.assertEqual(pin["stg"]["gen"], source)
                self.assertEqual(pin["stg"]["kit_rtl"], source)
                self.assertEqual(pin["stg"]["route"], rt)
                self.assertEqual(sibling["stg"]["gen"], rt)
                self.assertNotEqual(pin["noenv"], sibling["noenv"])

    def test_bind_preflight_uses_the_selected_tool_cohort(self):
        source = "c" * 64
        d = {"event": "E1", "src_manifest_hash": source, "src": "/x/src", "plan": "/x/plan",
             "kit_rtl": {"mode": "bind", "bind_out": "/x/bind"},
             "item_inputs": {"t": {"gen_tools_pin": {"event": "E1", "src_manifest_hash": source, "bind_out": "/x/bind"}}}}
        calls = {}

        def probe(host, code, args, timeout):
            if code == KW.PROBE_BIND:
                calls[args["types"][0]] = args.get("gen_tools_manifest_sha")
                return {"stale": []}
            return {"sig": "stable"}

        self.assertEqual(KW.bind_preflight(None, {"dies": {"s81": d}}, {}, "s81",
                                          [{"item": "t"}, {"item": "other"}], rpy=probe), {})
        self.assertEqual(calls, {"t": source, "other": None})

    def test_tools_fields_are_not_kit_inputs(self):
        """a new main sha alone never releases a design-fail hold (the stage tools digest of fail keys covers real tool changes)"""
        a = {"die": "s81", "item": "t", "plan": "/p", "gen_args": ["x"]}
        b = dict(a, tools_rt="/r/rt/0d6591bd9617", tools_sha=SHA)
        self.assertEqual(KW.input_hash(a), KW.input_hash(b))

    def test_launch_path_and_cmd(self):
        sp = {"src": "/s/kw45/src_s81_x/", "tools_rt": "/s/rt/0d6591bd9617"}
        self.assertEqual(KW.rt_launch_path(sp["src"], sp["tools_rt"]), "/s/kw45/rt_tools_launch/src_s81_x@0d6591bd9617")
        self.assertEqual(KW.rt_mirror_path(sp["src"], sp["tools_rt"]), "/s/kw45/rt_tools_launch/.rt/0d6591bd9617")
        c = KW.rt_tree_cmd(sp)
        self.assertTrue(c.startswith("[ -f /s/kw45/rt_tools_launch/src_s81_x@0d6591bd9617/.rt_launch_ok ] || {"))
        self.assertIn("R=/s/kw45/rt_tools_launch/.rt/0d6591bd9617", c)
        self.assertEqual(KW.rt_tree_cmd({"src": "/s/x"}), "")

    def test_run_item_runs_tools_from_tsrc(self):
        """every tool command of run_item changes into tsrc; the design roots stay on the die tree"""
        body = inspect.getsource(KW._run_item)
        cds = re.findall(r"cd \{q\(src\)\} && (\S+)", body)
        self.assertEqual(cds, ["for"], cds)            # only the legacy KITRTL farm (tree-own tools, never reached with rt tools)
        self.assertIn("--rtl-root {q(src)}", body)
        self.assertIn('--src-tree {q(src)} ', body)
        self.assertIn('if rcp and not pinned_gen:', body)
        self.assertIn('src_flag = "" if rcp and pinned_gen', body)
        self.assertIn('"rt_tools"', body)


class LaunchTree(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        b = Path(self.t.name)
        self.src, self.rt = b / "kw45/src_d", b / "rt/0d6591bd9617"
        w(self.src / "tools/die_plan/gen.py", "tree")
        w(self.src / "tools/die_plan/tree_only.py", "private")
        w(self.src / "physical/common_flow/hook.tcl", "tree")
        w(self.src / "physical/die_plan/d/plan.json", "{}")
        w(self.src / "rtl/a.v", "module a; endmodule")
        w(self.src / ".src-manifest.json", "{}")
        w(self.rt / "tools/die_plan/gen.py", "main")
        w(self.rt / "physical/common_flow/hook.tcl", "main")
        os.chmod(self.rt / "tools/die_plan", 0o555)
        self.L = KW.rt_launch_path(self.src, self.rt)

    def tearDown(self):
        os.chmod(self.rt / "tools/die_plan", 0o755)
        subprocess.run(["chmod", "-R", "u+w", self.t.name])
        self.t.cleanup()

    def run_sh(self):
        return subprocess.run(["bash", str(SH), str(self.src), str(self.rt), self.L], capture_output=True, text=True)

    def test_compose(self):
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr)
        L = Path(self.L)
        self.assertEqual((L / "tools/die_plan/gen.py").read_text(), "main")                    # rt wins
        self.assertEqual(os.stat(L / "tools/die_plan/gen.py").st_ino, os.stat(self.rt / "tools/die_plan/gen.py").st_ino)
        self.assertEqual((L / "physical/common_flow/hook.tcl").read_text(), "main")
        self.assertEqual((L / "tools/die_plan/tree_only.py").read_text(), "private")           # tree-only tool file kept
        self.assertEqual((L / ".rt_launch_filled").read_text().split(), ["tools/die_plan/tree_only.py"])
        self.assertTrue((L / "rtl").is_symlink() and (L / "physical/die_plan").is_symlink())
        self.assertEqual(os.path.realpath(L / "physical/die_plan/d/plan.json"), os.path.realpath(self.src / "physical/die_plan/d/plan.json"))
        self.assertTrue(os.access(L / "tools/die_plan", os.W_OK))
        self.assertEqual(json.loads((L / ".rt_launch_ok").read_text())["tree_only_tool_files"], 1)
        # idempotent and immutable: a second call changes nothing, even after the rt or tree moved on
        w(self.src / "tools/die_plan/new_in_tree.py", "x")
        r = self.run_sh()
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse((L / "tools/die_plan/new_in_tree.py").exists())

    def test_prefix_after_prune(self):
        """a stage after ot-tools-sync pruned rt/<sha> runs on the made tree, with no wait"""
        self.assertEqual(self.run_sh().returncode, 0)
        os.chmod(self.rt / "tools/die_plan", 0o755)
        subprocess.run(["rm", "-rf", str(self.rt)], check=True)
        c = KW.rt_tree_cmd({"src": str(self.src), "tools_rt": str(self.rt)})
        r = subprocess.run(["bash", "-c", c + f"cat {self.L}/tools/die_plan/gen.py"], capture_output=True, text=True, timeout=20)
        self.assertEqual((r.returncode, r.stdout), (0, "main"))
        (self.rt / "tools/die_plan").mkdir(parents=True)

    def test_verified_pinned_runtime_composes_without_a_mirror(self):
        import hashlib
        import shutil

        paths = (KW.RT_LOCAL_LAUNCH, "physical/common_flow/abc_kit.script")
        w(self.rt / paths[1], "flow")
        (self.rt / paths[0]).parent.mkdir(parents=True)
        shutil.copy(SH, self.rt / paths[0])
        for rel in (*paths, "tools", "physical/common_flow"):
            (self.rt / rel).chmod(0o555)
        receipt = self.rt.with_name(self.rt.name + ".manifest.json")
        files = {rel: hashlib.sha256((self.rt / rel).read_bytes()).hexdigest() for rel in paths}
        receipt.write_text(json.dumps({"sha": SHA, "files": files}))
        sp = dict(src=str(self.src), tools_rt=str(self.rt), tools_sha=SHA, private=True, kind="type",
                  place_spill=False, roam_hosts=["epyc7"], hosts=["epyc7", "intel1"],
                  place_spill_hosts=["epyc7"], work=str(Path(self.t.name) / "attempt"))

        with mock.patch.object(KW, "RT_CURRENT", str(self.rt.with_name("current"))):
            cmd = KW.rt_local_launch_cmd(sp, "epyc7")
            self.assertTrue(cmd)
            self.assertFalse(KW.rt_local_launch_cmd(dict(sp, place_spill=True), "epyc7"))
            self.assertFalse(KW.rt_local_launch_cmd(dict(sp, roam_hosts=["epyc7", "intel1"]), "epyc7"))
            self.assertFalse(KW.rt_local_launch_cmd(dict(sp, gen_pins={"files": {"x": "sha"}}), "epyc7"))
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.splitlines()[-1])["rt"], str(self.rt))
        mirror = KW.rt_mirror_path(sp["src"], sp["tools_rt"])
        self.assertFalse(Path(mirror).exists())
        command = KW.rt_tree_cmd(sp) + "true"
        seal = {"manifest_hash": "c" * 64}
        normal = KW.wave_stage_args(sp, sp["work"], command, (), event_env="", source_seal=seal)
        local_command = KW.rt_tree_cmd(sp, local_runtime=True) + "true"
        local = KW.wave_stage_args(sp, sp["work"], local_command, (), event_env="", source_seal=seal)
        self.assertNotIn(mirror, local_command)
        self.assertIn(mirror, normal)
        self.assertNotIn(mirror, local)
        self.assertIn(KW.sp_launch_path(sp), local)
        self.assertIn(str(self.rt), local)
        self.assertIn("--no-spill", local)

        receipt.write_text(json.dumps({"sha": "0" * 40, "files": files}))
        self.assertNotEqual(subprocess.run(["bash", "-c", cmd], timeout=20).returncode, 0)
        receipt.write_text(json.dumps({"sha": SHA, "files": files}))
        (self.rt / paths[1]).chmod(0o755)
        self.assertNotEqual(subprocess.run(["bash", "-c", cmd], timeout=20).returncode, 0)
        receipt.unlink()
        self.assertNotEqual(subprocess.run(["bash", "-c", cmd], timeout=20).returncode, 0)

    def test_mirror_push_and_compose(self):
        """fleet hosts carry only tools/fleet of rt: the hub-side mirror copy (local rsync here) feeds the launch tree"""
        sp = {"src": str(self.src), "tools_rt": str(self.rt)}
        rtfake = Path(self.t.name) / "rt/aaaaaaaaaaaa"            # the 'rt' the prefix looks at first does not exist on this host
        sp2 = dict(sp, tools_rt=str(rtfake))
        import shutil
        shutil.copytree(self.rt, rtfake)
        (rtfake / "tools/autopilot").mkdir(parents=True)
        shutil.copy(SH, rtfake / "tools/autopilot/rt_launch_tree.sh")
        prep, rs, fin = KW.rt_mirror_cmds(sp2, "localhost", "intel2", tag="t1")
        r = subprocess.run(["bash", "-c", prep], capture_output=True, text=True)
        self.assertIn("KW_RT_MIRROR_PREV", r.stdout)
        self.assertEqual(subprocess.run(rs(""), capture_output=True, text=True).returncode, 0)
        self.assertEqual(subprocess.run(["bash", "-c", fin], capture_output=True, text=True).returncode, 0)
        M = Path(KW.rt_mirror_path(self.src, rtfake))
        self.assertEqual((M / "tools/die_plan/gen.py").read_text(), "main")
        self.assertFalse(list(M.parent.glob("*.part*")))
        subprocess.run(["chmod", "-R", "u+w", str(rtfake)]); shutil.rmtree(rtfake)       # the host has no full rt: the mirror is used
        c = KW.rt_tree_cmd(sp2)
        L = KW.rt_launch_path(self.src, rtfake)
        r = subprocess.run(["bash", "-c", c + f"cat {L}/tools/die_plan/gen.py"], capture_output=True, text=True, timeout=30)
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, "main"), r.stderr)
        r = subprocess.run(["bash", "-c", prep], capture_output=True, text=True)
        self.assertIn("KW_RT_MIRROR_HAVE", r.stdout)

    def test_mirror_prune_keeps_young_mirrors(self):
        """RT-PRUNE-REFS-1124: beyond the 12 newest, only mirrors older than RT_MIRROR_KEEP_H go; a young one a resting kit names stays"""
        import time
        sp = {"src": str(self.src), "tools_rt": str(self.rt)}
        par = Path(KW.rt_mirror_path(self.src, "/x/aaaaaaaaaaaa")).parent
        now = time.time()
        for i in range(16):                                    # 16 mirrors, i=0 newest; two of the old ones are older than the floor
            d = par / f"{i:012x}"
            (d / "tools/autopilot").mkdir(parents=True)
            (d / "tools/autopilot/rt_launch_tree.sh").write_text("x")
            age = (KW.RT_MIRROR_KEEP_H * 3600 + 7200 + i) if i in (14, 15) else 60 + i
            os.utime(d, (now - age, now - age))
        prep, rs, fin = KW.rt_mirror_cmds(sp, "localhost", "intel2", tag="t2")
        subprocess.run(["bash", "-c", fin], capture_output=True, text=True)      # the final test -f of the missing own mirror fails; the prune has run
        left = sorted(p.name for p in par.iterdir() if p.is_dir())
        self.assertIn(f"{12:012x}", left)                      # 13th newest but young: kept (the old count-only rule removed it)
        self.assertIn(f"{13:012x}", left)
        self.assertNotIn(f"{14:012x}", left)                   # beyond 12 and old: pruned
        self.assertNotIn(f"{15:012x}", left)

    def test_mirror_prune_keeps_referenced_old_mirror(self):
        """RT-PRUNE-REFS-1124b: an OLD mirror (beyond 12 newest and 168 h) named by a non-terminal spec stays; a terminal-only one goes"""
        import time
        d0 = Path(self.t.name) / "ap"
        for nm, res in (("00000000000e", None), ("00000000000f", {"verdict": "FAIL"})):
            sd = d0 / "private_specs/L" / nm
            sd.mkdir(parents=True)
            (sd / "spec.json").write_text(json.dumps({"tools_rt": f"/x/rt/{nm}"}))
            if res:
                (sd / "result.json").write_text(json.dumps(res))
        refs = KW.rt_live_refs(roots=[str(d0)])
        self.assertEqual(refs, {"00000000000e"})
        KW.RT_REF_CACHE.update(t=time.time(), v=frozenset(refs))
        try:
            sp = {"src": str(self.src), "tools_rt": str(self.rt)}
            par = Path(KW.rt_mirror_path(self.src, "/x/aaaaaaaaaaaa")).parent
            now = time.time()
            for i in range(16):
                d = par / f"{i:012x}"
                (d / "tools/autopilot").mkdir(parents=True)
                (d / "tools/autopilot/rt_launch_tree.sh").write_text("x")
                age = KW.RT_MIRROR_KEEP_H * 3600 + 7200 + i if i >= 12 else 60 + i
                os.utime(d, (now - age, now - age))
            prep, rs, fin = KW.rt_mirror_cmds(sp, "localhost", "intel2", tag="t3")
            subprocess.run(["bash", "-c", fin], capture_output=True, text=True)
            left = {p.name for p in par.iterdir() if p.is_dir()}
            self.assertIn("00000000000e", left)
            self.assertNotIn("00000000000d", left)
            self.assertNotIn("00000000000f", left)
        finally:
            KW.RT_REF_CACHE.update(t=0.0, v=frozenset())

    def test_no_tools_anywhere_is_97_fast(self):
        c = KW.rt_tree_cmd({"src": str(self.src), "tools_rt": str(self.rt) + "x"})
        r = subprocess.run(["bash", "-c", c + "echo RAN"], capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 97)
        self.assertNotIn("RAN", r.stdout)

    def test_missing_rt_is_97(self):
        r = subprocess.run(["bash", str(SH), str(self.src), str(self.rt) + "x", self.L + "x"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 97)
        self.assertIn("rt snapshot", r.stderr)

    def test_half_made_tree_is_rebuilt(self):
        Path(self.L).mkdir(parents=True)
        w(Path(self.L) / "junk", "x")
        self.assertEqual(self.run_sh().returncode, 0)
        self.assertFalse((Path(self.L) / "junk").exists())


class DecoupleTwo(unittest.TestCase):
    """TOOLS-DECOUPLE-2 (COORD 11-19)"""

    def body(self):
        return inspect.getsource(KW._run_item)

    def test_flow_refresh_gets_the_die_tree_and_the_farm_starts_from_rt(self):
        b = self.body()
        self.assertIn("--die-src {q(src)}", b)                         # kit scripts that are die tree copies become rt's, tools_rev.json is written
        self.assertIn("cp -a {q(tsrc)}/tools/die_plan {q(kt)}/tools/die_plan", b)   # the legacy kit_rtl farm no longer starts from the die tree's die_plan
        self.assertNotIn("cp -a {q(src)}/tools", b)

    def test_stage_tool_hashes_are_the_rt_tree_not_the_die_tree(self):
        """SKIP-SAME-INPUT / fail keys: stage_tools_digest and exec_tools_digest read the scheduler's own (rt) tree; a die tree edit never moves them"""
        with tempfile.TemporaryDirectory() as t:
            rt, die = Path(t) / "rt", Path(t) / "die"
            for r in (rt, die):
                w(r / "tools/die_plan/hook.tcl", "puts same\n")
                w(r / "tools/die_plan/gen.py", "x = 1\n")
                w(r / "tools/die_plan/gen_phys.py", "y = 1\n")
                w(r / "tools/die_plan/bind.py", "z = 1\n")
            KW._EXEC_TOOLS.clear()
            KW._STAGE_TOOLS.clear()
            e0, s0 = KW.exec_tools_digest(rt), KW.stage_tools_digest(rt)
            w(die / "tools/die_plan/hook.tcl", "puts die-edit\n")      # the die tree changes: no effect on the rt digest
            KW._EXEC_TOOLS.clear()
            KW._STAGE_TOOLS.clear()
            self.assertEqual((KW.exec_tools_digest(rt), KW.stage_tools_digest(rt)), (e0, s0))
            w(rt / "tools/die_plan/hook.tcl", "puts rt-fix\n")          # the rt copy changes: the exec digest moves
            KW._EXEC_TOOLS.clear()
            self.assertNotEqual(KW.exec_tools_digest(rt), e0)
        default = re.search(r"def stage_tools_digest\(.*?\n(.*?)\n    k = ", (HERE / "kit_wave.py").read_text(), re.S).group(1)
        self.assertIn("Path(__file__).resolve().parents[2]", default)  # default root = the tools tree the scheduler runs from (rt/<sha>)


if __name__ == "__main__":
    unittest.main()
