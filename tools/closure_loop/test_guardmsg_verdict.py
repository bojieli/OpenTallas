"""Guard refusals have a distinct terminal verdict without losing closure evidence."""
import os
import tempfile
from unittest.mock import patch
os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="guardmsg_"))
import closure_loop as cl


def test_guard_refusal_is_first_ledger_field_and_needs_root():
    job = dict(name="job", spec=dict(smoke=True, source=dict(branch="codex/source")),
               metrics=dict(ss_ps=20, ff_ps=10, drc=0))
    refusal = "GATE_RULE_GUARD job abc123456: unclassified helper commit; ROOT classification required"
    out = dict(merge=refusal, branch_commit="a" * 40, files=3)
    with patch.object(cl, "adoption_held", return_value=False), patch.object(cl, "publish", return_value=out), \
         patch.object(cl, "finish") as finish:
        cl.do_commit(job)
    assert job["publish"] == out
    args = finish.call_args.args
    assert args[1] == "NEEDS_HUMAN"
    assert args[2] == refusal
    assert args[3].startswith(refusal + " | CLOSED")
