"""ot-heavy-reconcile v17.4 acceptance replays (coordinator 2026-10-22 18:0x).

Fixtures evidence/admit_v174/<host>.json: the live units of ot-epyc5 / ot-gold1 / ot-epyc9 read at 17:50 with the v17.4
read_units fields (now, step peak, growth phase, declared --mem) and the class/family table; replayed at 17:44 by age
(units younger than the 6 min are dropped) with the coordinator's 17:44 MemAvailable.  A settled unit's step peak is its
current memory (its earlier phase's peak is not carried, v17.4 (a)).

Acceptance: the ep9 16:52 state is refused (and the 16:06 192 GB qfd ref_gate, now seeded at its siblings' measured
peak, is refused); gold1 at 17:44 (473 GB available) admits >= 200 GB; ep5 at 17:44 (489 GB) admits >= 300 GB.
"""
import datetime
import importlib.machinery
import importlib.util
import json
import os
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ld = importlib.machinery.SourceFileLoader("ohr174", str(HERE / "ot-heavy-reconcile"))
_sp = importlib.util.spec_from_loader("ohr174", _ld)
R = importlib.util.module_from_spec(_sp)
_ld.exec_module(R)
# OWNER 10-22 20:10 zeroed the growth reservation defaults; these tests pin the pre-20:10 values to keep the rules tested
R.DEFAULTS.update(GROWTH_CAP_AVAIL_FRAC=0.25, SETTLED_FLOOR_FRAC=0.02, PHASE_MARGIN=1.0)
FX = HERE / "evidence" / "admit_v174"
R.PEAKS = str(FX / "no-local-peaks.tsv")   # class late growth from the fixtures only, never this host
R._LATE.clear()


def load(host, at, avail, edit=None):
    d = json.loads((FX / f"{host}.json").read_text())
    cap = datetime.datetime.strptime(d["at"], "%Y-%m-%dT%H:%M:%S%z")
    then = cap.replace(hour=int(at[:2]), minute=int(at[3:]), second=0)
    dt = (cap - then).total_seconds()
    rows = [dict(r, age=r["age"] - dt) for r in d["rows"] if r["active"] and r["age"] - dt >= 0]
    if edit:
        rows = edit(rows)
    return d["total"], avail, rows, d["table"]


def capacity(total, avail, rows, table):
    b = R.books(rows, total, avail, table)
    inv = R.invariant(rows, total, avail, b, table)
    can = R.inv_cap(R.admissible(total, avail, b, R.floor_gb(total), 0.7), inv)
    die = R.inv_cap(R.die_admissible(avail, b, R.floor_gb(total), 0.7, can), inv)
    return can, die, inv


class V174Acceptance(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)
        for k in ("PHASE_MARGIN", "HARD_INVARIANT", "INV_HEADROOM_GB", "MEASURED_RESERVE", "SEED_STEM_TOKENS"):
            os.environ.pop(k, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_ep5_1744_admits_300(self):
        can, die, inv = capacity(*load("ot-epyc5", "17:44", 489.0))
        self.assertGreaterEqual(can, 300, inv)
        self.assertGreaterEqual(die, 300, inv)

    def test_gold1_1744_admits_200(self):
        can, die, inv = capacity(*load("ot-gold1", "17:44", 473.0))
        self.assertGreaterEqual(can, 200, inv)
        self.assertGreaterEqual(die, 200, inv)

    def test_ep9_1652_refused(self):
        # 16:52: 966/1007 GB in use (MemAvailable ~30 GB); S81 run_h11r verilator at 250 GB of 300 declared; the qfd
        # GRT (84 GB) and the other killed jobs still running
        def at1652(rows):
            for r in rows:
                if "h#r" in (r.get("cls") or ""):
                    r.update(now=250.0, obs=250.0)
            return rows
        total, avail, rows, table = load("ot-epyc9", "17:44", 30.0, at1652)
        can, die, inv = capacity(total, avail, rows, table)
        self.assertLess(can, 10, inv)
        self.assertLess(die, 30, inv)                  # a 30 GB die GEN is refused too
        self.assertLess(inv["free"], 0, inv)

    def test_ep9_1606_qfd_gate_seed_refused(self):
        # 16:06: MemAvailable 154 GB, the run_h11r verilator still small (60 GB, compiling, no measured peak -> its
        # declared 300 GB in the compile phase); a 192 GB ref_gate_qfd_c_* request: v17.1 charged the 10 GB family
        # seed and admitted it, v17.4 charges its siblings' measured peak and refuses it
        def at1606(rows):
            for r in rows:
                if "h#r" in (r.get("cls") or ""):
                    r.update(now=60.0, obs=60.0, phase="vl", compiling=True)
            return rows
        total, avail, rows, table = load("ot-epyc9", "17:44", 154.0, at1606)
        cls = "ref_gate_qfd_c_b#_rgx_c#_#-#.sh"
        seed = R.admit_size(192, cls, table)
        self.assertIsNotNone(seed)
        self.assertGreaterEqual(seed[0], 60, seed)
        can, die, inv = capacity(total, avail, rows, table)
        self.assertLess(can, seed[0], inv)
        os.environ["PHASE_MARGIN"] = "0"
        can_old, _, _ = capacity(total, avail, rows, table)
        self.assertGreater(can_old, can)               # the compile-phase cap is what binds


class V174Units(unittest.TestCase):
    def test_family_seed_siblings_then_family(self):
        t = {f"ref_gate_qfd_c_k{i}.sh": dict(n=1, proved=0, peak_gb=float(p)) for i, p in enumerate((80, 90, 105, 120))}
        t.update({f"ref_gate_x_y_z{i}.sh": dict(n=1, proved=0, peak_gb=float(p)) for i, p in enumerate((2, 3, 4))})
        self.assertEqual(R.family_seed("ref_gate_qfd_c_new.sh", "ref_gate_", t)[0], 120)
        self.assertEqual(R.family_seed("ref_gate_other_new.sh", "ref_gate_", t)[0], 120)    # family p90
        self.assertEqual(R.admit_size(192, "ref_gate_qfd_c_new.sh", t)[0], 120)
        self.assertIsNone(R.admit_size(64, "ref_gate_qfd_c_new.sh", t))                     # seed >= request

    def test_phase_target(self):
        t = {"b.sh": dict(n=1, proved=0, peak_gb=50.0)}
        u = lambda **k: dict(dict(cls="a.sh", now=10.0, obs=10.0, decl=160.0), **k)
        self.assertEqual(R.phase_target(u(phase=""), t), 0.0)                               # settled: no margin
        self.assertEqual(R.phase_target(u(phase="vl", compiling=True), t), 160.0)           # no class: cap
        self.assertEqual(R.phase_target(u(cls="b.sh", phase="vl", compiling=True), t), 50.0)  # class late growth
        self.assertEqual(R.phase_target(u(cls="b.sh", phase="vl", decl=40.0), t), 40.0)     # never above the cap

    def test_growth_phase(self):
        p = lambda comm, *argv: dict(comm=comm, argv=[comm, *argv])
        self.assertEqual(R.growth_phase([p("bash"), p("verilator_bin", "--binary")]), ("vl", False))
        self.assertEqual(R.growth_phase([p("make"), p("cc1plus")]), ("vl", True))
        self.assertEqual(R.growth_phase([p("openroad", "-exit", "/f/scripts/global_route.tcl")]), ("or", False))
        self.assertEqual(R.growth_phase([p("openroad", "-exit", "/f/scripts/cts.tcl")]), ("", False))
        self.assertEqual(R.growth_phase([p("vvp")]), ("", False))


if __name__ == "__main__":
    unittest.main()


class OwnerZeroGrowthDefaults(unittest.TestCase):
    """OWNER 10-22 20:10: growth reservation 0 %, hard invariant kept; a redeploy must not bring the reservation back"""

    def test_defaults_zero(self):
        _l = importlib.machinery.SourceFileLoader("ohr_defaults", str(Path(__file__).with_name("ot-heavy-reconcile")))
        M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ohr_defaults", _l))
        _l.exec_module(M)
        self.assertEqual(M.DEFAULTS["GROWTH_CAP_AVAIL_FRAC"], 0.0)
        self.assertEqual(M.DEFAULTS["SETTLED_FLOOR_FRAC"], 0.0)
        self.assertEqual(M.DEFAULTS["PHASE_MARGIN"], 0.0)
        self.assertEqual(M.DEFAULTS["HARD_INVARIANT"], 1.0)
        self.assertEqual(M.DEFAULTS["INV_HEADROOM_GB"], 64.0)
