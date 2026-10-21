#!/usr/bin/env python3
"""refinalize_view.py -- rebuild a closed child view's abstract LEF from its SAVED raw export (no re-route).

KV-ECTL5/6 2026-10-19: abstract_pin_stub.py used to close own-layer pockets right up to ONE routing pitch from a signal
pin; its fill rects are wide metal, so ASAP7 M4..M7 wide spacing (0.072 um) left such a pin with no DRC-clean access stub
in the parent (DRT-0073, qkd_ectl3_kiss_st-e4: u_a/req_t[10]).  The keep-out is now whole pitches >= the wide spacing,
child_lint (i) FAILs such a pin and `ref_tile.py gen` refuses the view.  An OLDER view is fixed by re-running the
exporter's finalize step (export_provenance.finalize: tools/hier_contract/abstract_pin_stub.py + child_lint) on the raw
LEF and raw manifest it saved under provenance/ -- pins, outline, origin and libs are unchanged (check_invariants); only
the pocket-fill OBS changes.  Never re-route a closed view for this.

    tools/ref_tile/refinalize_view.py physical/ref_tile/<kit>/views/<top>            # dry run: lint the rebuilt LEF
    tools/ref_tile/refinalize_view.py physical/ref_tile/<kit>/views/<top> --apply    # replace LEF/abstract/lint/provenance

Then `git add` the view directory by path, commit, and re-run `ref_tile.py gen` on the parent.
Exit 0 = rebuilt LEF lints PASS (and was applied with --apply), 1 = FAIL, 2 = view not rebuildable here.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
import export_provenance as EP  # noqa: E402
import child_lint  # noqa: E402

HELPER = ROOT / "tools/hier_contract/abstract_pin_stub.py"


def head_before_obs(text: str) -> str:
    """the LEF without its OBS section and the OT_OBS_CLOSED marker (pins, size, origin, PG): must be identical"""
    text = re.sub(r"(?m)^[ \t]*# OT_OBS_CLOSED .*\n", "", text)
    return re.sub(r"\n[ \t]*OBS[ \t]*\n.*?\n[ \t]*END[ \t]*\n", "\n", text, flags=re.S)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("view", help="view directory (holds <top>.lef, abstract.json, provenance/raw/<top>.lef)")
    ap.add_argument("--top", help="cell name (default: the view directory name)")
    ap.add_argument("--apply", action="store_true", help="replace the view's LEF, abstract.json, child_lint.json, provenance/")
    a = ap.parse_args(argv)
    view = Path(a.view).resolve()
    top = a.top or view.name
    prov = view / "provenance"
    raw_lef, raw_man = prov / "raw" / f"{top}.lef", prov / "view_export.abstract.json"
    if not raw_lef.exists() or not raw_man.exists():
        print(f"REFIN NO-RAW {view}: no saved raw export ({raw_lef.name} / {raw_man.name} under provenance/): this view "
              f"predates export provenance; re-export it from its closed route (ref_tile.py export), not a re-route")
        return 2
    rec = json.loads((prov / "abstract_pin_stub.json").read_text()) if (prov / "abstract_pin_stub.json").exists() else {}
    kind = rec.get("kind", "abstract_pin_stub")
    if kind != "abstract_pin_stub":
        print(f"REFIN SKIP {view}: provenance transformation is '{kind}' (not the pocket fill); nothing to rebuild here")
        return 2
    old_lef = (view / f"{top}.lef").read_text(errors="replace")
    with tempfile.TemporaryDirectory(prefix="refin_") as td:
        out = Path(td) / top
        shutil.copytree(view, out)
        shutil.rmtree(out / "provenance")
        (out / "abstract.json").write_bytes(raw_man.read_bytes())
        (out / f"{top}.lef").write_bytes(raw_lef.read_bytes())
        lint = EP.finalize(out, top, HELPER, child_lint)
        man = json.loads((out / "abstract.json").read_text())
        if lint.get("verdict") != "PASS" or not man.get("ok"):
            print(f"REFIN FAIL {view}: {lint.get('fails') or man.get('export_failure')}")
            return 1
        new_lef = (out / f"{top}.lef").read_text(errors="replace")
        same_head = head_before_obs(old_lef) == head_before_obs(new_lef)
        print(f"REFIN PASS {view}: child_lint {lint['verdict']} pin_access_violations "
              f"{lint.get('info', {}).get('pin_access_violations')}; pins/size/PG "
              f"{'identical' if same_head else 'DIFFER (check: only OBS may change)'}; LEF "
              f"{'unchanged' if old_lef == new_lef else 'OBS changed'}")
        if not same_head:
            return 1
        if a.apply:
            for f in (f"{top}.lef", "abstract.json", "child_lint.json"):
                shutil.copy2(out / f, view / f)
            shutil.rmtree(prov)
            shutil.copytree(out / "provenance", prov)
            print(f"REFIN APPLIED {view}: git add it by path, commit, re-run ref_tile.py gen on the parent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
