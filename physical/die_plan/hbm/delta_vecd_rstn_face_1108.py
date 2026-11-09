#!/usr/bin/env python3
"""HBM plan event VECD-RSTN-FACE-1108 (COORD 19:1x condition on the vecd4ae count row, DIE-HBM-93).

gen_core_kit_hbm class M5-EW-PIN places an M5 plan point a few um inside an E/W face on that face at the same y.  Four
hnx_vms_bank_q0_faces__vecd4ae pin tables (fr15, plain + o_MX + o_MY + o_R0) list rst_n at x 266.712, 3.288 um inside
the E face; every kit and signed view has it on the face.  This event writes the face position (x 270.0, the
gen_core_kit_hbm row form) into those tables so the plan and the views agree.  y, layer, every other pin and
die_plan.json are unchanged; the bind reads no pin table, so it stays valid.

    delta_vecd_rstn_face_1108.py PLAN_DIR OUT_DIR    (OUT_DIR = new hard-linked copy; changed files replaced, not edited)
"""
import gzip
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

EVENT = "VECD-RSTN-FACE-1108"
MODULE = "hnx_vms_bank_q0_faces__vecd4ae"
OLD = '{"name": "rst_n", "layer": "M5", "x": 266.712, "y": 313.181'
NEW = '{"name": "rst_n", "layer": "M5", "x": 270.0, "y": 313.181'


def fsha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(plan_dir, out_dir):
    plan_dir, out_dir = Path(plan_dir).resolve(), Path(out_dir).resolve()
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists")
    plan = json.loads((plan_dir / "die_plan.json").read_text())
    files = sorted({c["pins_file"] for t in plan["partition_types"].values() for c in t.get("hard_cores") or []
                    if c.get("module") == MODULE and c.get("pins_file")})
    targets = [f for f in files if OLD in (plan_dir / f).read_text()]
    if len(targets) != 4:
        raise SystemExit(f"expected 4 pin tables with rst_n at x 266.712, found {len(targets)}: {targets}")
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    sums = dict(reversed(line.split("  ", 1)) for line in (plan_dir / "SHA256SUMS").read_text().splitlines())
    rows = []
    for f in targets:
        text = (plan_dir / f).read_text()
        if text.count(OLD) != 1:
            raise SystemExit(f"{f}: rst_n row count {text.count(OLD)}")
        new = text.replace(OLD, NEW)
        before = json.loads(text)
        after = json.loads(new)
        diff = [(a, b) for a, b in zip(before, after) if a != b]
        if len(before) != len(after) or len(diff) != 1 or diff[0][0]["name"] != "rst_n":
            raise SystemExit(f"{f}: more than the rst_n row changed")
        for suffix in ("", ".gz"):
            (out_dir / (f + suffix)).unlink()
        (out_dir / f).write_text(new)
        with gzip.GzipFile(str(out_dir / (f + ".gz")), "wb", mtime=0) as gz:
            gz.write(new.encode())
        for name in (f, f + ".gz"):
            if name in sums:
                sums[name] = fsha(out_dir / name)
        rows.append(dict(pins_file=f, sha_in=fsha(plan_dir / f), sha_out=fsha(out_dir / f)))
    receipt = dict(event=EVENT, module=MODULE, pin="rst_n", x_in=266.712, x_out=270.0, y=313.181, tables=rows,
                   die_plan_sha256=fsha(out_dir / "die_plan.json"))
    name = "vecd_rstn_face_1108_event.json"
    (out_dir / name).write_text(json.dumps(receipt, indent=1) + "\n")
    sums[name] = fsha(out_dir / name)
    (out_dir / "SHA256SUMS").unlink()
    (out_dir / "SHA256SUMS").write_text("".join(f"{sha}  {n}\n" for n, sha in sorted(sums.items())))
    return receipt


if __name__ == "__main__":
    r = run(sys.argv[1], sys.argv[2])
    print(EVENT, len(r["tables"]), "tables, die_plan", r["die_plan_sha256"][:16])
