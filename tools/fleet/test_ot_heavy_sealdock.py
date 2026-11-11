"""SEALDOCK_1111 (KW-FIX-44, COORD 11-11): sealed jobs (ot-job + bwrap) start their container with the client copy
.ot-job/docker.real; the unit must be measured with that container (its cgroup memory.current / memory.peak), not at its
wrapper, and a unit whose container was never found keeps its peak out of the class table."""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    ld = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_sd", str(HERE / "ot-heavy-reconcile"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
    ld.exec_module(m)
    return m


R = load()
IMG = "openroad/orfs:v3.0-4122-g2d4b2bd5"
SEALED = ["/srv/x/ot-jobs/q_spu0-route/.ot-job/docker.real", "run", "--memory-swap=48g", "--oom-score-adj=0", "--rm",
          "--name", "dpkit-q_spu0-2092530", "--cpus=8", "--memory=48g", "-v", "/srv/k:/work", IMG, "bash", "-lc", "make"]


def cont(name, cmd=("bash", "-lc", "make"), binds=("/srv/k:/work",)):
    return {"Id": name + "-id", "Name": "/" + name, "Config": {"Image": IMG, "Entrypoint": None, "Cmd": list(cmd)},
            "HostConfig": {"Binds": list(binds)}}


class SealDock(unittest.TestCase):
    def setUp(self):
        R._containers = [cont("dpkit-q_spu0-2092530"), cont("dpkit-q_spu0-9999")]

    def tearDown(self):
        R._containers = None

    def test_docker_real_is_a_docker_run(self):
        self.assertTrue(R.is_docker_run(dict(comm="docker.real", argv=SEALED)))
        self.assertTrue(R.is_docker_run(dict(comm="docker", argv=["docker", "run", "--rm", IMG])))
        self.assertFalse(R.is_docker_run(dict(comm="docker", argv=["docker", "ps", "-q"])))
        self.assertFalse(R.is_docker_run(dict(comm="bash", argv=["bash", "run_kit.sh", "route"])))

    def test_container_matched_by_name(self):
        # two containers share image, command and binds: the argv match alone is ambiguous, --name decides
        self.assertEqual(R.match_container(SEALED)["Name"], "/dpkit-q_spu0-2092530")

    def test_argv_match_still_works_without_name(self):
        R._containers = [cont("other")]
        self.assertEqual(R.match_container([a for a in SEALED if not a.startswith("dpkit")
                                            and a != "--name"])["Name"], "/other")

    def test_classify_sealed_as_docker(self):
        self.assertTrue(R.classify(SEALED).startswith("docker:"))

    def test_wrapper_only_units_kept_out_of_class_table(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        R.PEAKS, R.SIZES = os.path.join(d, "peaks.tsv"), os.path.join(d, "sizes.json")
        open(R.PEAKS, "w").write("")
        st = {"a": dict(cls="run_kit.sh:route", peak=0.08, launch=48, age=4000, dock_miss=5),
              "b": dict(cls="run_kit.sh:route", peak=44.2, launch=48, age=4000, dock_miss=0)}
        t = R.rebuild_sizes(st)
        self.assertEqual(t["run_kit.sh:route"]["live"], 1)
        self.assertEqual(t["run_kit.sh:route"]["peak_gb"], 44.2)


if __name__ == "__main__":
    unittest.main()
