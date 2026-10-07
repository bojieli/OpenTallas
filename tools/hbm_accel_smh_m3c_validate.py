#!/usr/bin/env python3
"""Pinned smh request-output validation: share builds only within one parameter group.

Run in a fresh archived source tree through the host admission guard (28 compiler
workers maximum, reserve at least 192 GiB: seven elaborators measured about
18 GiB each). No process deadline or build-size cap. The rejected alternating
request candidate is reproduced at commit d3393aa88; later RTL retains the FIFO.
"""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = Path(sys.argv[1]).resolve()
    out = base / "out"
    out.mkdir(parents=True, exist_ok=True)
    groups = [
        [("ar_l20_f1", "ar_l20", 1, []), ("ar_l20_f1s", "ar_l20", 1, ["--serial"]),
         ("other_f1", "other", 1, []), ("stress_f1", "stress", 1, []),
         ("wg_f1", "wg", 1, []), ("wg_f1s", "wg", 1, ["--serial"]),
         ("stress_stalls_f1", "stress", 1, ["--req-stalls"])],
        [("p6_l20_f6", "p6_l20", 6, []), ("p6_l20_f6s", "p6_l20", 6, ["--serial"]),
         ("p6_other_f6", "p6_other", 6, []), ("p6_stress_f6", "p6_stress", 6, []),
         ("p6_wg_f6", "p6_wg", 6, []), ("p6_wg_f6s", "p6_wg", 6, ["--serial"])],
        [("ar_l20_f8", "ar_l20", 8, []), ("p6_l20_f8", "p6_l20", 8, []),
         ("stress_f8", "stress", 8, [])],
        [("mutbf_haz_haz1", "haz", 1, ["--mut-bfdly"])],
        [("neg_flip_stress", "stress", 1, ["--neg-flip", "--expect-fail"])],
        [("neg_mut_s1w_stress", "stress", 1, ["--mut-s1w", "--expect-fail"])],
        [("neg_mutbf_haz_haz0", "haz", 1, ["--haz", "0", "--mut-bfdly", "--expect-fail"])],
    ]

    def group_run(item):
        index, cases = item
        results = []
        for name, seq, active, extra in cases:
            cmd = [sys.executable, str(ROOT / "tools/dshbm_sm_pq_seq.py"), "run",
                   "--smh", "--nc", "8", "--build-jobs", "4", "--seq", seq,
                   "--active", str(active), "--workdir", str(base / "w" / str(index)),
                   "--out", str(out / (name + ".json")), *extra]
            with (out / (name + ".log")).open("w") as log:
                rc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
            (out / (name + ".rc")).write_text(str(rc) + "\n")
            results.append(dict(name=name, rc=rc, expect="fail" if "--expect-fail" in extra else "pass"))
            print(name, "rc", rc, flush=True)
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        rows = [r for group in pool.map(group_run, enumerate(groups)) for r in group]
    passed = all(r["rc"] == 0 for r in rows)
    (out / "campaign.json").write_text(json.dumps(dict(passed=passed, cases=rows), indent=2) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
