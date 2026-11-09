"""Docker bind sources remain subject to the exact --stage admission check."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

loader=importlib.machinery.SourceFileLoader("ot_run_docker_paths",str(Path(__file__).with_name("ot-run")))
spec=importlib.util.spec_from_loader(loader.name,loader)
M=importlib.util.module_from_spec(spec);loader.exec_module(M)
ROOT="/srv/opentallas-scratch2/claude/codex-token-1713"
INPUT=ROOT+"/input_eng_be69"
OUT=ROOT+"/e5_alias_extract2"

class DockerPaths(unittest.TestCase):
    def test_bind_variants_name_only_the_host_source(self):
        for opts in (["-v",INPUT+":/work:ro"],["--volume",INPUT+":/srv/container:rw,Z"],
                     ["--volume="+INPUT+":/work"],["-v"+INPUT+":/work:ro"]):
            with self.subTest(opts=opts):
                self.assertEqual(M.command_srv_paths(["docker","run","--rm","--memory","24g",*opts,"image"]),[INPUT])
        self.assertEqual(M.command_srv_paths(["bash","-lc","docker run --rm -v "+INPUT+":/work:ro image"]),[INPUT])

    def test_no_arbitrary_colon_path_or_container_command_exemption(self):
        literal=INPUT+":/work:ro"
        for cmd in (["other-tool","-v",literal],["docker","run","image","tool","-v",literal],
                    ["docker","run","-v",INPUT+":/work:unrecognized-mode","image"]):
            with self.subTest(cmd=cmd):
                self.assertNotEqual(M.command_srv_paths(cmd),[INPUT])
        self.assertIn(ROOT+"/unstaged",M.command_srv_paths(["docker","run","-v",literal,"image",ROOT+"/unstaged"]))

    def test_exact_stage_bind_passes_path_gate_and_reaches_scan(self):
        cmd=["docker","run","-v",INPUT+":/work:ro","image"]
        with patch.object(M,"STAGE",[OUT,INPUT]),patch.object(M,"ssh_sh",return_value=SimpleNamespace(stdout="")), \
             patch.object(M,"spill_scan",side_effect=RuntimeError("reached exact stage scan")):
            result,why,permanent=M.spill_plan("localhost",OUT,cmd,24,2,False,1,{},lambda *a:None)
        self.assertIsNone(result)
        self.assertIn("reached exact stage scan",why)
        self.assertNotIn("outside",why)

    def test_unstaged_bind_source_still_refused_before_any_network(self):
        cmd=["docker","run","-v",ROOT+"/other:/work:ro","image"]
        with patch.object(M,"STAGE",[OUT,INPUT]),patch.object(M,"ssh_sh") as network:
            result,why,permanent=M.spill_plan("localhost",OUT,cmd,24,2,False,1,{},lambda *a:None)
        self.assertIsNone(result);self.assertTrue(permanent)
        self.assertIn("outside the --stage paths",why);network.assert_not_called()

if __name__=="__main__":unittest.main()


class RoSourceBinds(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.t = tempfile.TemporaryDirectory()
        self.repo = self.t.name + "/repo"
        os.makedirs(self.repo + "/.git")
        os.makedirs(self.repo + "/kits/k/gen")

    def tearDown(self):
        self.t.cleanup()

    def test_checkout_root_gets_ro(self):
        out = M.ro_source_binds(["docker", "run", "--rm", "-v", self.repo + ":/src", "img", "cmd"])
        self.assertIn(self.repo + ":/src:ro", out)

    def test_other_forms_get_ro(self):
        self.assertIn(self.repo + ":/s:ro", M.ro_source_binds(["docker", "run", "--volume", self.repo + ":/s", "i"]))
        self.assertIn("--volume=" + self.repo + ":/s:ro", M.ro_source_binds(["docker", "run", "--volume=" + self.repo + ":/s", "i"]))
        out = M.ro_source_binds(["bash", "-lc", f"docker run --rm -v {self.repo}:/s img"])
        self.assertEqual(out[:2], ["bash", "-lc"])
        self.assertIn(self.repo + ":/s:ro", out[2])

    def test_unchanged_cases(self):
        for cmd in (
            ["docker", "run", "-v", self.repo + ":/s:rw", "i"],               # explicit mode wins
            ["docker", "run", "-v", self.repo + "/kits/k/gen:/work", "i"],    # below the root stays writable
            ["docker", "run", "-v", "/nonexistent/x:/w", "i"],                # no checkout here
            ["make", "-v", self.repo + ":/s"],                                # not docker
            ["bash", "-c", f"docker run -v {self.repo}:/s i; echo x"],        # compound script
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(M.ro_source_binds(cmd), cmd)
        self.assertEqual(M.ro_source_binds(["docker", "run", "img", "-v", self.repo + ":/s"]),
                         ["docker", "run", "img", "-v", self.repo + ":/s"])   # after the image is the container's command
