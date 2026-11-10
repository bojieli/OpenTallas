"""ISOLATION step 4: GATE PASS per die = the first sealed job of that die to sign off (any item), 0 refusals / gaps."""
import json
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path

M = SourceFileLoader("gate_pass", str(Path(__file__).with_name("gate_pass.py"))).load_module()
SEALED = "ot-job: SEALED /srv/j: 3 inputs\n...\not-job: published 2 artifact(s); job dir deleted /srv/j\nAP_RC=0\n"


def mk(tmp, jobs):
    st = {"jobs": {}}
    for jid, (die, status, log, t) in jobs.items():
        st["jobs"][jid] = {"die": die, "type": jid + "_t", "status": status, "kit": f"epyc2:/srv/k/{jid}", "archive": f"a/{jid}"}
        d = tmp / "jobs" / jid
        d.mkdir(parents=True)
        (d / "a1.log").write_text(log)
        os.utime(d / "a1.log", (t, t))
    return st


def test_first_sealed_signed_job_per_die(tmp_path):
    st = mk(tmp_path, {"late": ("s81", "ARCHIVED", SEALED, 200), "early": ("s81", "ARCHIVED", SEALED, 100),
                       "unsealed": ("hbm", "ARCHIVED", "routed unsealed\nAP_RC=0\n", 50),
                       "running": ("qwen_kvsys", "RUNNING", SEALED, 10),
                       "refused": ("qwen_compute", "ARCHIVED", SEALED + "OT-JOB ISOLATION: undeclared host path /srv/x\n", 10),
                       "gap": ("s81_head", "ARCHIVED", SEALED, 10)})
    g = tmp_path / "gaps.tsv"
    g.write_text("2026-11-09\ts81_head\tx\troute\t/srv/k/gap/missing\tENOENT\n")
    per = M.gate(st, str(tmp_path / "jobs"), [str(g)])
    assert set(per) == {"s81"} and per["s81"]["job"] == "early"


def test_unversioned_or_killed_never_passes(tmp_path):
    st = mk(tmp_path, {"uv": ("s81", "ARCHIVED", SEALED, 1), "killed": ("hbm", "ARCHIVED", "ot-job: SEALED /srv/j\nKilled\n", 1)})
    st["jobs"]["uv"]["prov_error"] = "no src commit"
    assert M.gate(st, str(tmp_path / "jobs"), []) == {}
