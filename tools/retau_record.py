#!/usr/bin/env python3
"""Re-tau a committed DS ROM composition whose inputs live only in remote scratch (owner rule 2026-10-04).

Every MTP rate in these records is tau x 1e6 / step, and the step (verify + draft + seed/commit) does not depend on
tau. So the record is re-composed at the third-party tau (tools/third_party_tau.py) from its own committed figures:
MTP_new = MTP_old x tau_new / tau_old. Only keys named MTP*_tok_s are touched, plus constants.draft.tau. A
provenance block records the superseded tau. Applies to records that cannot be re-run from committed inputs
(dsrom_1m_measure.py compose and dsrom_reindex_candidates.py compose need --work / --reader dirs on the EPYC
scratch).

Usage: python3 tools/retau_record.py RECORD.json [RECORD.json ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import third_party_tau as tpt  # noqa: E402

KEY = re.compile(r"^MTP\w*_tok_s$")


def retau(path: Path) -> int:
    d = json.loads(path.read_text())
    old = d["constants"]["draft"]["tau"]
    new = tpt.tau_ds_v41(5)
    if old == new:
        return 0
    n = 0

    def walk(o, inside=False):
        nonlocal n
        if isinstance(o, dict):
            for k, v in o.items():
                hit = inside or bool(KEY.match(k))
                if isinstance(v, (int, float)) and not isinstance(v, bool) and hit:
                    o[k] = round(v * new / old, 1)
                    n += 1
                else:
                    walk(v, hit)
        elif isinstance(o, list):
            for v in o:
                walk(v, inside)
    walk(d)
    d["constants"]["draft"]["tau"] = new
    d["tau_rescale"] = dict(tau_old=old, tau_new=new, tau_src=tpt.tau_src("deepseek_v41", 5), fields=n,
                            tool="tools/retau_record.py",
                            rule="MTP = tau x 1e6 / step; step unchanged (tau-independent); MTP_new = MTP_old x tau_new / tau_old",
                            superseded=tpt.SUPERSEDED["deepseek_v41"])
    path.write_text(json.dumps(d, indent=1) + "\n")
    return n


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, retau(Path(p)), "fields")
