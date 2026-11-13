#!/usr/bin/env python3
"""Apply the explicit SerDes form to a captured bound wrapper, before kit synthesis.

bind captures old parameter defaults (RST_TREE=0), so changing the macro default
alone does not activate the requested reset tree. This one-instance edit keeps
all other captured parameters intact and emits the actual parameter receipt.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def apply(text, reset_tree=1):
    pattern = re.compile(r"(\bot_pdie_serdes_col\s*#\s*\()(?P<params>[^;]*?)(\)\s+u_core\s*\()", re.S)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected one ot_pdie_serdes_col u_core instance, found {len(matches)}")
    m = matches[0]
    args = m.group("params")
    p = re.compile(r"(\.RST_TREE\s*\(\s*)([0-9]+)(\s*\))")
    hits = list(p.finditer(args))
    if len(hits) != 1:
        raise ValueError("captured wrapper must declare RST_TREE exactly once")
    old = int(hits[0].group(2))
    if old not in (0, reset_tree):
        raise ValueError(f"RST_TREE={old} is a distinct explicit form, refusing to overwrite")
    new_args = p.sub(lambda x: x.group(1) + str(reset_tree) + x.group(3), args)
    out = text[:m.start("params")] + new_args + text[m.end("params"):]
    return out, {"RST_TREE": {"captured": old, "actual": reset_tree}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wrapper", type=Path)
    ap.add_argument("--reset-tree", type=int, choices=(1, 3), default=1)
    ap.add_argument("--receipt", type=Path, required=True)
    a = ap.parse_args()
    before = a.wrapper.read_text()
    after, params = apply(before, a.reset_tree)
    receipt = {"schema": "opentallas.serdes_form_params.v1", "module": "ot_pdie_serdes_col", "instance": "u_core",
               "wrapper": str(a.wrapper), "sha256_before": hashlib.sha256(before.encode()).hexdigest(),
               "sha256_after": hashlib.sha256(after.encode()).hexdigest(), "parameters": params,
               "reset_release_edges_added": 1 if a.reset_tree == 1 else 2,
               "status": "PRIVATE_DO_NOT_COUNT", "note": "steady cycles must use the matching exact form benchmark"}
    if after != before:
        a.wrapper.write_text(after)
    a.receipt.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
