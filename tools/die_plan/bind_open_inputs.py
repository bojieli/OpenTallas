#!/usr/bin/env python3
"""BIND-UNDRIVEN-IN 11-23: read-only scan of an existing bind dir for leaf input bits no driver reaches because the as-built
instance leaves the port unconnected (bind.Binder.open_input_audit, the check strict bind now runs in analyse).

    [OT_REPO_ROOT=TREE] bind_open_inputs.py --plan PLAN.json [--asbuilt MANIFEST.json] --bind-dir OUT [--json FILE]

Reads OUT/asbuilt.json(.gz) and the plan (its asbuilt section, or --asbuilt as in `bind.py bind`); writes nothing in OUT.
Set OT_REPO_ROOT to the tree the bind ran on (provenance_bind.json) so repository-relative proofs resolve there.  rc 0 = none, 1 = undriven bits."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def scan(plan_path, bind_dir, asbuilt=None):
    bind._AB_OVERRIDE["path"] = asbuilt
    raw = bind.load_plan(plan_path)
    yjs = bind.load_asbuilt_netlist(bind_dir)
    B = bind.Binder(raw, yjs, Path(plan_path).parent, bind.plan_base(plan_path, raw))
    B.map_cells()
    plan_rw = B.pc.rewired_keys() if B.pc else set()
    cnt = defaultdict(int)
    B.open_input_audit(cnt, plan_rw)
    return dict(schema="opentallas.bind_open_inputs.v1", plan=str(plan_path), bind_dir=str(bind_dir),
                undriven=B.open_inputs, unjudged=B.open_inputs_unjudged,
                n_undriven=cnt.get("open_input", 0), n_leaf=sum(1 for c in B.cpart if B.G.kind[c] == "leaf"),
                n_input_bits=sum(w or 0 for c in B.cpart if B.G.kind[c] == "leaf"
                                 for w in (B._leaf_input_widths(B.F.cells[c]) or {}).values()),
                **{k: cnt.get("open_input_" + k, 0) for k in ("dead", "bump", "tied", "derived", "source_leaf")},
                errors=[e for e in B.errors if e.startswith("UNDRIVEN_OPEN")])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--asbuilt", help="as-built manifest in its own file (provenance_bind.json manifest)")
    ap.add_argument("--bind-dir", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = scan(a.plan, a.bind_dir, a.asbuilt)
    text = json.dumps(r, indent=1) + "\n"
    if a.json:
        Path(a.json).write_text(text)
    for e in r["errors"]:
        print(e)
    print(f"leaves {r['n_leaf']} input bits examined {r['n_input_bits']}; undriven {r['n_undriven']} on {len(r['undriven'])} "
          f"pins; dead {r['dead']} bump {r['bump']} tied {r['tied']} derived {r['derived']} source_leaf {r['source_leaf']}; unjudged {len(r['unjudged'])}")
    return 1 if r["n_undriven"] else 0


if __name__ == "__main__":
    sys.exit(main())
