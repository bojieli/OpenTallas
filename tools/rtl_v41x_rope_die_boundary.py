#!/usr/bin/env python3
"""Bounded die interface lint for RoPE on the packed-KV shared K path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import rtl_chip_v41x_packed_die_boundary as B  # noqa: E402

OUT=ROOT/"results/rtl/v41x_rope_die_boundary.json"
NEW=[B.CHIP/f"{n}.sv" for n in (
    "ot_chip_v41x_rope_hbm_cache", "ot_chip_v41x_rope_region_guard",
    "ot_chip_v41x_kv_rope_reqmux")]


def main()->None:
    B.SOURCES += NEW
    result=B.run()
    result["schema"]="opentallas.rtl.v41x_rope_die_boundary.v1"
    result["claim"]="Reduced/full die port elaboration with read-only RoPE cache sharing packed-KV K mux; exact tile/HBM PHY headers blackboxed, no full token or physical timing claim"
    result["sources_sha256"][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"pass":result["pass"],
                      "modes":{k:v["returncode"] for k,v in result["modes"].items()}}))
    if not result["pass"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
