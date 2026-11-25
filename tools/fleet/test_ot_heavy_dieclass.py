"""DIECLASS_1125 (OWNER 11-24 00:05 + 11-25 00:0x, lane FLEET-ADMIT): die-level work is admitted at once (no memory / load / CPU check),
runs with no MemoryMax at oom_score_adj -1000 and nice 0; type-level jobs run at nice 10 and oom_score_adj 500; a host's die slice
(DIE_SLICE_GB / DIE_SLICE_CORES) is held back from type-level jobs."""
import importlib.machinery, importlib.util, os, subprocess, unittest
from pathlib import Path
import test_ot_heavy_crit as C

HERE = Path(__file__).resolve().parent
_l = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_dieclass", str(HERE / "ot-heavy-reconcile"))
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_dieclass", _l))
_l.exec_module(R)


class _H(unittest.TestCase):
    """the ot-heavy harness of test_ot_heavy_crit, by composition (subclassing would re-run its tests)"""
    def setUp(self):
        self.h = C.Heavy("test_below_cap_runs_default_weight"); self.h.setUp(); self.d = self.h.d

    def conf(self, extra):
        (self.d / "conf").write_text("LOAD_GATE_FACTOR=0\n" + extra)


class DieClass(_H):
    def setUp(self):
        super().setUp()
        self.h.rec.write_text('#!/bin/bash\n[ "$1" = --is-die ] && { [ -n "${DIE_TEST:-}" ]; exit; }; [ "$1" = --is-plan ] && exit 1; '
                              'echo "NO 400 cls | insufficient memory: available 10 GB"\n')

    def die_run(self, load="500"):
        os.environ["DIE_TEST"] = "1"
        try:
            return self.h.run_(load, mem="400")
        finally:
            os.environ.pop("DIE_TEST", None)

    def test_die_admitted_at_once_without_memory_cap(self):
        r, a = self.die_run()
        self.assertIsNotNone(a, r.stderr)                         # memory gate said NO and load 500 >> cap: admitted anyway
        self.assertFalse(any(x.startswith("MemoryMax=") for x in a), a)
        self.assertIn("MemorySwapMax=0", a)
        self.assertNotIn("nice", a)
        self.assertIn("choom -n -1000 -p", (self.d / "args.sudo").read_text())

    def test_dieclass_off_waits(self):
        self.conf("OT_HEAVY_DIECLASS=0\n")
        r, a = self.die_run()
        self.assertIsNone(a)
        self.assertEqual(r.returncode, 75)

    def test_type_job_waits_on_memory(self):
        r, a = self.h.run_("1", mem="400")
        self.assertIsNone(a)
        self.assertIn("insufficient memory", r.stderr)


class TypeJob(_H):
    def test_type_job_nice_10_with_memory_cap(self):
        r, a = self.h.run_("1")
        self.assertIsNotNone(a, r.stderr)
        self.assertIn("MemoryMax=4G", a)
        i = a.index("--")
        self.assertEqual(a[i + 1:i + 4], ["nice", "-n", "10"])
        self.assertFalse((self.d / "args.sudo").exists())

    def test_crit_job_niced(self):
        r, a = self.h.run_("1", crit=True)   # KITNICE_1125: crit kit stages are niced now (CPUWeight 1000 stays)
        self.assertIsNotNone(a, r.stderr)
        i = a.index("--"); self.assertEqual(a[i + 1:i + 4], ["nice", "-n", "10"])

    def test_slice_cores_lower_type_load_cap(self):
        self.conf("DIE_SLICE_CORES=4\n")
        r, a = self.h.run_("9.0")                 # nproc 10 - slice 4 = 6, x 1.2 = 7: a type job waits (LOADCAP_FRESH_1125)
        self.assertIsNone(a)
        self.assertIn("= 7", r.stderr)


class KitNice(_H):
    """KITNICE_1125: kit stages run at nice 10 even with --crit / --die; die-level commands stay at nice 0"""
    def nice10(self, a):
        i = a.index("--")
        return a[i + 1:i + 4] == ["nice", "-n", "10"]

    def test_crit_kit_is_niced(self):
        r, a = self.h.run_("1", crit=True)
        self.assertIsNotNone(a, r.stderr); self.assertTrue(self.nice10(a), a)
        self.assertIn("CPUWeight=1000", a)

    def test_die_level_command_nice_0(self):
        os.environ["DIE_TEST"] = "1"
        try:
            self.h.rec.write_text('#!/bin/bash\n[ "$1" = --is-die ] && exit 0; [ "$1" = --is-plan ] && exit 1; echo "OK 4 cls | need 4, available 100 GB"\n')
            r, a = self.h.run_("500")
        finally:
            os.environ.pop("DIE_TEST", None)
        self.assertIsNotNone(a, r.stderr); self.assertNotIn("nice", a)

    def test_container_sweep_targets(self):
        cid = "a" * 64; did = "b" * 64
        cg = lambda c: f"0::/system.slice/docker-{c}.scope\n"
        procs = [(1, 0, "openroad", cg(cid)), (2, 0, "openroad", cg(did)), (3, 10, "openroad", cg(cid)), (4, 0, "bash", cg(cid)),
                 (5, 0, "openroad", "0::/user.slice/x\n"), (6, 0, "yosys", cg(cid))]
        self.assertEqual(R.kit_nice_targets(procs, lambda c: c == did), [1, 6])

    def test_crit_kit_counts_against_the_die_slice(self):    # the load cap is die-slice aware for every non-die class, crit included
        (self.d / "conf").write_text("LOAD_GATE_FACTOR=0\nLOAD_CAP_FACTOR=1.2\nDIE_SLICE_CORES=5\n")
        r, a = self.h.run_("0.1", crit=True)    # crit is never load-held (COORD 11-25): admitted; its threads are counted for the next kit
        self.assertIsNotNone(a, r.stderr)
        self.assertEqual(len(list((self.d / "state").glob("thr.oth-*"))), 1)


class DieShim(unittest.TestCase):
    def setUp(self):
        s = C.Shim("test_default_unchanged"); s.setUp(); self.sh = s.sh

    def run_env(self, *a, **env):
        e = dict(os.environ, OT_HEAVY_MEM_GB="12")
        for k in ("OT_HEAVY_CPU", "OT_HEAVY_PRIO", "OT_HEAVY_OOM_ADJ"):
            e.pop(k, None)
        e.update(env)
        return subprocess.run([str(self.sh), *a], capture_output=True, text=True, env=e).stdout.split("\n")[:-1]

    def test_die_container_uncapped_minus_1000(self):
        for prio in ("die", "plan"):
            out = self.run_env("run", "--memory", "64g", "img", "x", OT_HEAVY_PRIO=prio)
            self.assertIn("--oom-score-adj=-1000", out, prio)
            self.assertIn("--cpu-shares=17600", out, prio)
            self.assertFalse(any(x.startswith("--memory") or x == "64g" for x in out), out)

    def test_type_container_takes_job_adj(self):
        out = self.run_env("run", "img", "x", OT_HEAVY_OOM_ADJ="500")
        self.assertIn("--oom-score-adj=500", out)
        self.assertIn("--memory=12g", out)
        self.assertIn("--memory-swap=12g", out)


def test_die_level_commands_are_die_class(monkeypatch):
    monkeypatch.setattr(R, "rd", lambda p: "")
    yes = [["python3", "-I", "-B", "/x/rt/a/tools/die_plan/plan_gate_pre.py", "check", "--tree", "/t"],
           ["python3", "-I", "tools/die_plan/bind.py", "bind", "plan.json", "--out", "/o"],
           ["python3", "-I", "tools/die_plan/check.py", "plan.json", "--r8-strap-pads"],
           ["python3", "/l/kv-allfix/a5t6e10/compose3.py"], ["bash", "/l/s81/c2compose.sh"],
           ["bash", "/l/kv-allfix/a5t7i1/gate_a5t7.sh", "A5t7"], ["bash", "/l/kv-allfix/a5t7i1/run_a5t7_gate.sh"],
           ["bash", "/l/QC-CB-C1L/bindrun_l.sh", "/m"], ["bash", "/l/QC/bindR.sh"], ["python3", "tools/die_plan/bind_phases.py"]]
    no = [["python3", "-I", "tools/die_plan/bind.py", "kit-rtl", "--type", "x"], ["openroad", "-exit", "route.tcl"],
          ["bash", "/l/kv/job_a5t7pins.sh"], ["make", "-C", "/k/flow", "do-5_2_route"]]
    for a in yes:
        assert R.die_like(a, "/srv/x"), a
    for a in no:
        assert not R.die_like(a, "/srv/x/bind"), a


def test_die_slice_held_back_from_type_jobs(monkeypatch):
    monkeypatch.setattr(R, "conf", lambda k: {"DIE_SLICE_GB": 300.0, "DIE_SLICE_CORES": 32.0}.get(k, 0.0))
    assert R.die_slice_gb("") == 300.0 and R.die_slice_cores("") == 32.0
    for p in ("die", "plan"):
        assert R.die_slice_gb(p) == 0.0 and R.die_slice_cores(p) == 0.0


def test_crit_jobs_use_the_die_slice(monkeypatch):
    monkeypatch.setattr(R, "conf", lambda k: {"DIE_SLICE_GB": 300.0, "DIE_SLICE_CORES": 32.0}.get(k, 0.0))
    monkeypatch.setenv("OT_HEAVY_CPU", "crit")
    monkeypatch.delenv("OT_HEAVY_PRIO", raising=False)
    assert R.die_slice_gb() == 0.0 and R.die_slice_cores() == 0.0


def test_script_that_runs_a_die_level_tool_is_die_class(tmp_path):
    """FLEET-OPS 11-25: `bash pre_bind.sh` (runs plan_gate_pre.py / die-plan bind) ran at nice 10"""
    pre = tmp_path / "pre_run.sh"; pre.write_text("cd t; python3 -I -B tools/die_plan/plan_gate_pre.py check --tree x --plan y\n")
    bnd = tmp_path / "go.sh"; bnd.write_text("python3 -I -B tools/die_plan/bind.py bind plan.json --out o\n")
    kit = tmp_path / "kit.sh"; kit.write_text("make -C run\n")
    krt = tmp_path / "krt.sh"; krt.write_text("python3 tools/die_plan/bind.py bind kit-rtl x; tools/die_plan/plan_gate_pre.py kit-rtl\n")
    assert R.die_like(["bash", str(pre)], str(tmp_path)) and R.die_like(["bash", str(bnd)], str(tmp_path))
    assert not R.die_like(["bash", str(kit)], str(tmp_path)) and not R.die_like(["bash", str(krt)], str(tmp_path))
    assert not R.script_die_level(["python3", str(pre)]) and not R.script_die_level(["bash", str(tmp_path / "missing.sh")])
