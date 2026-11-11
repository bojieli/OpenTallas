#!/usr/bin/env python3
"""DIE-S81-85 SVCPROV-V5-1111: compose the svc provider form A event v5 (s81/svc_prov_1109_v5) onto the S81 plan of
record, as the follow-on of FEED-BAL-1111 (COORD 11-10: S81-SVCRS-3's 6 signed svc boxes cannot count until v5 is in
plan_h2_2249).  NOT EQ-gated: it is v5 itself (svc_lo +77.76 um Y and the die +77.76 um, 353 partitions moved, the
hard boxes / 31 macros / RTL defines of form A, type-internal pin cycle deltas for the svc compiler), so it is a
separate delta applied right after FEED-BAL-1111, never folded into it.

Recipe = the v5 commit 2096599e17 exactly, on main's tools (same blobs as the v5 commit except
svc_prov_event_1109.py, whose only change since v5 is the opt-in --pin-model v6; the default v5 is used):
  1. svc_prov_event_1109.py BASE V2 EVENT svc_prov_meas_1109.json --lo-pack b --rdpipe     (pin model v5)
  2. svc_prov_step3_ft_1109.py V2 OUT LEDGER                                              (svc_lo ft re-site)
  3. clock.cohort (FEED-BAL-1111 record): feed tap points moved with the die grow (svc_split_event_1109.die_grow dy
     rule: +77.76 at y >= LO_TOP_DIE, as the spine root); topology (parents) unchanged.  The measured tap windows and
     the landing-phase record are from the pre-grow clock: status says so (re-measure on this sha).

usage: delta_svc_prov_v5_1111.py BASE(FEED-BAL-1111 output) OUT_PLAN OUT_DIR
       delta_svc_prov_v5_1111.py --check BASE OUT_PLAN OUT_DIR"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import svc_split_event_1109 as V1  # noqa: E402

EVENT = "SVCPROV-V5-1111"
BASE_SHA = "66466e86ebcd7450a7db52c3b8ae807926721845a2e64583dadc4c41da5b2a7f"   # FEED-BAL-1111 output
BLOBS = {   # git blob ids (main) of the v5 recipe; fail closed on drift
    "svc_prov_event_1109.py": "f7aa006e76e7ebcb2b431f755087c4c7ab5f6b6a",
    "svc_split_event_1109.py": "4b7fd0ae0e2dd4320fddbd440822ac72c8547f72",
    "svc_prov_meas_1109.json": "1e14dc19eaa1185e62838a744f3ccd4ab60941f1",
    "svc_prov_step3_ft_1109.py": "81f3c1d21c9b4c9f6f95ff6f1e68e2c93ab7a95c",
}


def blob(p):
    b = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def run(base, out, od, write=True):
    raw = Path(base).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA, "base is not the FEED-BAL-1111 output"
    for f, want in BLOBS.items():
        assert blob(HERE / f) == want, (f, "recipe file drifted")
    od = Path(od)
    od.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        v2 = Path(td) / "v2.json"
        subprocess.run([sys.executable, "-I", str(HERE / "svc_prov_event_1109.py"), base, str(v2),
                        str(od / "svc_prov_1109_v5_event_on_feedbal.json"), str(HERE / "svc_prov_meas_1109.json"),
                        "--lo-pack", "b", "--rdpipe"], check=True)
        s3 = Path(td) / "s3.json"
        subprocess.run([sys.executable, "-I", str(HERE / "svc_prov_step3_ft_1109.py"), str(v2), str(s3),
                        str(od / "svc_prov_1109_v5_ft_ledger_on_feedbal.json")], check=True)
        P = json.loads(s3.read_text())
    co = P["clock"]["cohort"]
    G, cut = V1.G_TOTAL, V1.LO_TOP_DIE
    moved = 0
    for k, (x, y) in list(co["feed"]["tap"].items()):
        if y >= cut - 0.01:
            co["feed"]["tap"][k] = [x, round(y + G, 3)]
            moved += 1
    co["status"] = (co["status"] + f" | {EVENT}: svc provider v5 composed (die +{G} um Y at y >= {cut}); feed taps moved "
                    f"with the grow ({moved}); tap_window per_port_ps and landing_phases were measured on the PRE-grow "
                    "clock -> re-run the S81 die clock + kit windows + landing table on this sha before relaunch")
    txt = json.dumps(P) + "\n"
    if write:
        Path(out).write_text(txt)
    rep = dict(event=EVENT, base_plan_sha256=BASE_SHA, output_plan_sha256=hashlib.sha256(txt.encode()).hexdigest(),
               recipe="v5 commit 2096599e17: svc_prov_event_1109.py --lo-pack b --rdpipe (pin model v5) + step 3",
               recipe_blobs=BLOBS, feed_taps_moved=moved, grow_um=G, cut_y_um=cut)
    (od / "svc_prov_v5_1111_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return txt, rep


def main():
    if sys.argv[1] == "--check":
        txt, rep = run(*sys.argv[2:5], write=False)
        assert Path(sys.argv[3]).read_text() == txt
        print("CHECK PASS", rep["output_plan_sha256"])
        return
    txt, rep = run(*sys.argv[1:4])
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
