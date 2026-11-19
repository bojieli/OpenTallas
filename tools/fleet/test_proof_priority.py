"""PROOF-PRIO-1119: ot-run --priority proof = r712 proof kits are admitted ahead of waiting wave jobs and are the guard's last victim."""
import importlib.machinery, importlib.util, os, pathlib, tempfile
H = pathlib.Path(__file__).parent


def load(n, f):
    l = importlib.machinery.SourceFileLoader(n, str(H / f)); m = importlib.util.module_from_spec(importlib.util.spec_from_loader(n, l)); l.exec_module(m); return m


def test_ot_run_accepts_priority_proof_and_passes_it_to_ot_heavy():
    s = (H / "ot-run").read_text()
    assert '("die", "plan", "proof")' in s and 'f"OT_HEAVY_PRIO={prio} "' in s


def test_ot_heavy_writes_a_proof_marker_and_reconcile_orders_proof_like_die():
    assert 'proof.job.$$' in (H / "ot-heavy").read_text()
    r = (H / "ot-heavy-reconcile").read_text()
    assert '"OT_HEAVY_PRIO=proof" in environment.split' in r and 'in ("die", "proof")' in r
    assert "ot-protect-die --pid" in (H / "ot-heavy").read_text()          # protection (-999) stays die-only


def test_plan_pids_reads_proof_markers_by_prefix():
    O = load("oomage_proof", "ot-oom-age")
    d = tempfile.mkdtemp()
    open(f"{d}/proof.job.{os.getpid()}", "w").close(); open(f"{d}/plan.job.{os.getpid()}", "w").close(); open(f"{d}/proof.job.99999999", "w").close()
    assert O.plan_pids(d, prefix="proof.job.") == {str(os.getpid())}
    assert O.plan_pids(d) == {str(os.getpid())}
    assert not os.path.exists(f"{d}/proof.job.99999999")                      # dead launcher marker removed


def test_guard_takes_a_wave_victim_before_a_proof_one():
    s = (H / "ot-oom-age").read_text()
    assert "v = guard_victim(procs)\n                if v is None:\n                    v = guard_victim(spared)" in s


def test_proof_like_matches_env_or_the_regex_file(tmp_path):
    R = load("recon_proof", "ot-heavy-reconcile")
    f = tmp_path / "prio_proof.re"; f.write_text("# kits\nfable-fix-s81-leaf/proof/t27keep\n")
    R.PROOF_FILE = str(f)
    assert R.proof_like(["bash", "run_kit.sh", "/x/fable-fix-s81-leaf/proof/t27keep", "grt"], "/")
    assert R.proof_like(["bash", "x"], "/", ["OT_HEAVY_PRIO=proof"])
    assert not R.proof_like(["bash", "run_kit.sh", "/x/other/t1", "grt"], "/", ["OT_HEAVY_PRIO="])
