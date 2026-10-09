"""A revoked closure (revoked_closures.json / option-B status) does not supersede a block's failing jobs."""
import json
import tempfile
from pathlib import Path

import closure_loop as cl


def _job(name, block, status="CLOSED", metrics=None, closed="2026-10-06T22:03"):
    return dict(name=name, spec=dict(block=block), status=status, metrics=metrics or {"ss_ps": 22.6, "ff_ps": 20.4},
                events=[f"{closed}:56-07:00 CLOSED: CLOSED SS +22.64 / FF +20.36 ps DRC 0"])


def _setup(tmp):
    rv = Path(tmp) / "revoked_closures.json"
    rv.write_text(json.dumps({"hbm_x_a": {"reason": "H1"}}))
    st = Path(tmp) / "results/closure_loop/option_b_status_20261007"
    st.mkdir(parents=True)
    (st / "status.json").write_text(json.dumps({"revoked_previously_closed": {"blocks": [
        {"block": "dsfd_svcio_q", "job": "s81ph-dsfd_svcio_q-old"}]}}))
    cl.REVOKED_JSON, cl.REPO = rv, Path(tmp)


def test_revoked_sources():
    with tempfile.TemporaryDirectory() as tmp:
        _setup(tmp)
        jobs = [_job("hbm_x_a", "hfd_x"), _job("s81ph-dsfd_svcio_q-093da5918", "dsfd_svcio_q"),
                _job("ok", "hfd_ok"), _job("s81ph-dsfd_svcio_q-old", "dsfd_svcio_q", closed="2026-10-08T10:00")]
        assert cl.closed_blocks(jobs) == {"hfd_ok"}


def test_optb_block_reverified_at_tt_counts():
    with tempfile.TemporaryDirectory() as tmp:
        _setup(tmp)
        assert cl.closed_blocks([_job("tt1", "dsfd_svcio_q", metrics={"tt_ps": 1.0, "ff_ps": 2.0})]) == {"dsfd_svcio_q"}
        assert cl.closed_blocks([_job("tt2", "dsfd_svcio_q", closed="2026-10-08T21:00")]) == {"dsfd_svcio_q"}
        assert cl.closed_blocks([_job("ss", "dsfd_svcio_q")]) == set()
        assert cl.closed_blocks([_job("f", "hfd_ok", status="NEEDS_RTL")]) == set()
