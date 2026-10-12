#!/usr/bin/env python3
"""child-lint verdict gate (do_commit): a tile whose exported view fails child_lint (c)/(f) is NOT CLOSED.

Runs on COPIES of real view LEFs (never the live loop state): ot_engc_t_win from the closed archive (15 face pins blocked
above after the pre-a804fc09b hold ECO) must be refused; the ref_tile ot_nhb_pvlg view (0/679 blocked) must pass.
ssh is replaced by a local reader over a temp {RUN}/record tree; finish/publish are stubbed."""
import shutil
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_loop as cl  # noqa: E402

BAD = Path("/home/ubuntu/closed_archive/dsfd_engram_c/el1011-engc-win-pk-5f1603a05-tc-cl/final/ot_engc_t_win.lef")
GOOD = HERE.parents[1] / "physical/ref_tile/nhb_pvlg_ref/views/ot_nhb_pvlg/ot_nhb_pvlg.lef"


def fake_ssh(host, script, timeout=120, **kw):
    import subprocess
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def job(run, block, **spec):
    return {"name": f"t-{block}", "host": "fakehost", "run": str(run), "metrics": {"ss_ps": 10.0, "ff_ps": 1.0, "drc": 0},
            "spec": dict(block=block, source={"branch": "x"}, **spec), "events": []}


def run_commit(j):
    out = {}
    cl.ssh, cl.adoption_held = fake_ssh, (lambda j: False)
    cl.finish = lambda j, st, reason, text: out.update(status=st, reason=reason)
    cl.publish = lambda j, m: {"merge": "MERGED", "files": 0}
    cl.event = lambda j, msg: j["events"].append(msg)
    cl.do_commit(j)
    return out


def main():
    tmp = Path(tempfile.mkdtemp(prefix="cl_gate_"))
    try:
        for name, src, blk in (("bad", BAD, "ot_engc_t_win"), ("good", GOOD, "ot_nhb_pvlg")):
            d = tmp / name / "record" / "views" / blk
            d.mkdir(parents=True)
            shutil.copy(src, d / f"{blk}.lef")
            (d / f"{blk}_bloat.lef").write_text("bogus")     # must be ignored
        r = run_commit(job(tmp / "bad", "ot_engc_t_win"))
        assert r["status"] == "NEEDS_HUMAN" and "CHILD-LINT" in r["reason"] and "(f)" in r["reason"], r
        j = job(tmp / "bad", "ot_engc_t_win", hier_lint={"skip": "f", "why": "test"})
        r = run_commit(j)
        assert r["status"] == "CLOSED", (r, j.get("child_lint"))
        r = run_commit(job(tmp / "bad", "ot_engc_t_win", hier_lint={"skip": "f"}))   # no reason -> not skipped
        assert r["status"] == "NEEDS_HUMAN", r
        j = job(tmp / "good", "ot_nhb_pvlg", ref_tile=True)
        r = run_commit(j)
        assert r["status"] == "CLOSED" and j["child_lint"]["fails"] == [], (r, j.get("child_lint"))
        r = run_commit(job(tmp / "none", "ot_x"))                       # no view: not a tile view job -> passes
        assert r["status"] == "CLOSED", r
        r = run_commit(job(tmp / "none", "ot_x", ref_tile=True))        # ref_tile without its view -> refused
        assert r["status"] == "NEEDS_HUMAN", r
        print("child-lint gate: 6/6 PASS")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
