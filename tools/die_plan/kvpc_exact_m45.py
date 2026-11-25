#!/usr/bin/env python3
"""KV-PC-ABSTRACT: exact M4/M5 OBS for the kvpc hard-core views (qkd_kvs_pcc / qkd_kvs_pcf and the h_head_p variants).

The 11-21 pc_v3 obstruction form (OBS-SYNC-1) wrote M1-M5 as one blanket OBS rect (write_abstract_lef
-bloat_occupied_layers): 94 % (pcf) / 100 % (pcc) of the macro blocked on M4/M5, although the real M4/M5 metal is
2-7 % of the area (kv3_pc kits: GRT overflow 4,096-4,317 over the kvpc column).  Re-exports of a kvpc view now keep
M1-M3 blanket and take M4/M5 EXACT (write_abstract_lef -bloat_factor 0) from the same signed ODB, with the M4 pin-clear
cut; M6/M7 stay as in the base view (exact since OBS-SYNC-1).  See kv_pcsplit_exact_m45.json for the recipe.

  python3 -I kvpc_exact_m45.py --base signed_view.lef --detail exact_b0.lef --out new.lef [--receipt r.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A

LAYERS = "M4,M5"
PIN_CLEAR_UM = "0.048"
PIN_CLEAR_LAYERS = "M4"
# the published base carries the finalize pin stubs, the raw ODB export does not: this one splice finding is expected
EXPECTED_PROBLEM = "detailed export PIN section != base (different ODB?)"


def splice_args(base, detail, out):
    return ["splice", "--base", str(base), "--detail", str(detail), "--layers", LAYERS, "--bloat-factor", "0",
            "--pin-clear-um", PIN_CLEAR_UM, "--pin-clear-layers", PIN_CLEAR_LAYERS, "--out", str(out)]


def run(base, detail, out, receipt=None):
    """splice + check; 0 iff the output differs from base only in the M4/M5 OBS"""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(splice_args(base, detail, out))
    rec = json.loads(buf.getvalue() or "{}")
    problems = [p for p in rec.get("problems", []) if p != EXPECTED_PROBLEM]
    if receipt:
        Path(receipt).write_text(json.dumps(rec, indent=1))
    if (rc not in (0, 1)) or problems:
        return 2
    return A.main(["check", "--base", str(base), "--new", str(out), "--layers", LAYERS])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--detail", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt")
    a = ap.parse_args(argv)
    return run(a.base, a.detail, a.out, a.receipt)


if __name__ == "__main__":
    sys.exit(main())
