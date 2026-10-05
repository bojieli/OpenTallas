#!/usr/bin/env python3
"""Final closed connected PV boundary; exclusively PV accepted operands.

Refuses nonterminal captures. Checks actual EXP -> adapter BF16 P, then integer
PV versus independent chunk8 golden, OLD output and published native VM bytes.
Does not normalize by SUM: this frozen PV descriptor consumes unnormalized EXP.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from dsrom_i63_accepted_endpoint_compare import decode, iproduct, iadd, compare, sha


def run(root, out):
    terminal = root / "terminal.json"
    receipt = json.loads(terminal.read_text())
    if receipt["exit"] != 0:
        raise ValueError("connected capture not terminal PASS")
    log = (root / "runtime.log").read_text()
    boundary = re.search(r"^BOUNDARY PV cycle=(\d+)$", log, re.M)
    if not boundary or "CONNECTED_QK_I61_I62_PV" not in log:
        raise ValueError("closed PV native readback/complete-flow marker missing")
    names = {"PV_accepted_q.u32": 16384, "PV_accepted_p.u32": 20480,
             "PV_accepted_kv.u32": 339200, "PV_old_pv.u32": 32768,
             "PV.u32": 32768, "EXP.u32": 40960}
    files = {n: root / "captured" / n for n in names}
    for n, p in files.items():
        if p.stat().st_size != names[n]:
            raise ValueError(f"exact closed PV capture extent: {n}")
    before = {n: sha(p) for n, p in files.items()}
    p = np.fromfile(files["PV_accepted_p.u32"], dtype="<u2").reshape(640, 16).T.copy()
    q = np.fromfile(files["PV_accepted_q.u32"], dtype="<u2")
    kv = np.fromfile(files["PV_accepted_kv.u32"], dtype="<u4")
    old = np.fromfile(files["PV_old_pv.u32"], dtype="<u4").reshape(8, 64, 16).transpose(2, 1, 0).reshape(16, 512)
    vm = np.fromfile(files["PV.u32"], dtype="<u4").reshape(16, 512)
    exp_words = np.fromfile(files["EXP.u32"], dtype="<u4").reshape(16, 640)
    expected_p = ((exp_words.astype(np.uint64) + 0x7fff + ((exp_words >> 16) & 1)) >> 16).astype(np.uint16)
    m = np.flatnonzero(p.ravel() != expected_p.ravel())
    pcheck = {"compared": 10240, "mismatches": int(m.size), "first": None}
    if m.size:
        i = int(m[0])
        pcheck["first"] = {"head": i // 640, "row": i % 640,
                           "actual_bf16": f"{p.ravel()[i]:04x}", "expected_bf16": f"{expected_p.ravel()[i]:04x}"}
    ki, kg, faults, formats = decode(kv)
    if np.any(faults) or np.any(((p >> 7) & 255) == 255):
        raise ValueError("exceptional accepted operands need explicit fault golden")
    integer, golden = np.zeros((16, 512), dtype=np.uint32), np.zeros((16, 512), dtype=np.uint32)
    stages = {"product_mismatches": 0, "chunk8_mismatches": 0, "tree_mismatches": 0, "integer_faults": 0}
    for h in range(16):
        prod, bad = iproduct(p[h][None, :], ki.T)
        fp = p[h].astype(np.uint32) << 16
        gp = (kg.T * fp.view(np.float32)[None, :]).astype(np.float32)
        gp[gp == 0] = np.float32(0)
        stages["product_mismatches"] += int(np.count_nonzero(prod != gp.view(np.uint32)))
        stages["integer_faults"] += int(np.count_nonzero(bad))
        prod, gp = prod.reshape(512, 80, 8), gp.reshape(512, 80, 8)
        chunks, gc = np.zeros((512, 80), dtype=np.uint32), np.zeros((512, 80), dtype=np.float32)
        for j in range(8):
            chunks, bad = iadd(chunks, prod[:, :, j])
            stages["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc + gp[:, :, j]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
        stages["chunk8_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        chunks, gc = np.pad(chunks, ((0, 0), (0, 48))), np.pad(gc, ((0, 0), (0, 48)))
        while chunks.shape[1] > 1:
            chunks, bad = iadd(chunks[:, 0::2], chunks[:, 1::2])
            stages["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc[:, 0::2] + gc[:, 1::2]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
            stages["tree_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        integer[h], golden[h] = chunks[:, 0], gc[:, 0].view(np.uint32)
    checks = {"EXP_to_accepted_P_BF16": pcheck,
              "PV_Q_nonzero_words": int(np.count_nonzero(q)),
              "dequant_mismatches": int(np.count_nonzero((ki.astype(np.uint32) << 16) != kg.view(np.uint32))),
              "integer_vs_golden": compare(integer, golden), "integer_vs_OLD_PV": compare(integer, old),
              "golden_vs_OLD_PV": compare(golden, old), "golden_vs_VM": compare(golden, vm),
              "OLD_PV_vs_VM": compare(old, vm)}
    if before != {n: sha(p) for n, p in files.items()}:
        raise ValueError("closed capture changed during comparison")
    ok = not any(stages.values()) and all(v["mismatches"] == 0 if isinstance(v, dict) else v == 0 for v in checks.values())
    out.mkdir(exist_ok=False)
    golden.astype("<u4").tofile(out / "golden_PV.u32")
    integer.astype("<u4").tofile(out / "integer_PV.u32")
    record = {"scope": "One connected rank0 minimum QK/native I61/I62/PV diagnostic; final PV uses exclusively actual PV accepted operands; no original-run qualification/hardware timing",
              "source_commit": receipt["source_commit"], "capture_root": str(root),
              "PV_boundary_cycle": int(boundary[1]), "capture_sha256": before,
              "terminal_sha256": sha(terminal), "tool_sha256": sha(Path(__file__)),
              "integer_helper_sha256": sha(Path(__file__).with_name("dsrom_i63_accepted_endpoint_compare.py")),
              "fp4_rows_by_group": formats, "checks": checks, "stage_checks": stages,
              "SUM_normalization_applied": False, "original_full_run_qualified": False,
              "hardware_timing_qualified": False, "verdict": "PASS" if ok else "FAIL"}
    (out / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(run(args.capture_root, args.out))
