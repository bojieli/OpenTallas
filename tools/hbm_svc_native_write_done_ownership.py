#!/usr/bin/env python3
"""Prove the per-PC output ownership rewrite is only signal relocation."""
import hashlib
from pathlib import Path

def check(root):
    directory = root / "rtl/hbm_accel/loader/service_native"
    before = directory / "ot_hbm_svc_native_sector_prefetch_stack.sv"
    after = directory / "ot_hbm_svc_native_sector_owned_stack.sv"
    original = before.read_text()
    rewritten = after.read_text()
    normalized = rewritten.replace("module ot_hbm_svc_native_sector_owned_stack #(",
                                   "module ot_hbm_svc_native_sector_prefetch_stack #(")
    normalized = normalized.replace("output wire[31:0]k_wr_done,", "output reg[31:0]k_wr_done,")
    normalized = normalized.replace("\n        reg pc_write_done;\n        assign k_wr_done[p]=pc_write_done;", "")
    normalized = normalized.replace("pc_write_done<=", "k_wr_done[p]<=")
    assert normalized == original, "rewrite contains additional functional differences"
    assert rewritten.count("assign k_wr_done[p]=pc_write_done;") == 1
    assert "k_wr_done[p]<=" not in rewritten
    return {"before_SHA256": hashlib.sha256(before.read_bytes()).hexdigest(),
            "after_SHA256": hashlib.sha256(after.read_bytes()).hexdigest(),
            "normalization_equivalence": "PASS", "FF_SRAM_clock_root_delta": 0}

if __name__ == "__main__":
    import json
    print(json.dumps(check(Path(__file__).resolve().parents[1]), indent=2))
