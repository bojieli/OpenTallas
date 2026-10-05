#!/usr/bin/env python3
"""Source-pinned V4.1 full-shape activation-bank protocol gates.

These benches use BF16 values from the 200K layer-0 golden shard.  They check
bank addressing and read latency; they do not execute the ME/HCP arithmetic.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41x_activation_bank_campaign.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


CASES = (
    ("me_two_group", "tb_v41x_me_two_group", "ot_hdc_v41x_me_xbank",
     "v41x_me_two_group_l0_real.hex", "DATA", r"ME_TWO_GROUP_PASS load_cycles=(\d+) reads=(\d+) errors=0"),
    ("me_two_group_wide", "tb_v41x_me_two_group_wide", "ot_hdc_v41x_me_xbank",
     "v41x_me_two_group_l0_real.hex", "DATA", r"ME_TWO_GROUP_WIDE_PASS preload_cycles=(\d+) reads=(\d+) errors=0"),
    ("me_random_segments", "tb_v41x_me_xbank", "ot_hdc_v41x_me_xbank",
     "v41x_me_xbank_l0_real.hex", "ME_DATA", r"ME_XBANK_PASS kmax=(\d+) lanes=(\d+) mp=(\d+) reads=(\d+) errors=0"),
    ("he_slice", "tb_v41x_he_xslice", "ot_hdc_v41x_he_xslice",
     "v41x_he_xslice_l0_real.hex", "HE_DATA", r"HE_XSLICE_PASS depth=(\d+) lanes=(\d+) reads=(\d+)"),
    ("he_slice_wide", "tb_v41x_he_xslice_wide", "ot_hdc_v41x_he_xslice_wide",
     "v41x_he_xslice_l0_real.hex", "HE_DATA", r"HE_XSLICE_WIDE_PASS preload_cycles=(\d+) reads=(\d+) errors=0"),
)


def main() -> None:
    sources = [ROOT / "tools/rtl_v41x_activation_bank_campaign.py"]
    records = []
    with tempfile.TemporaryDirectory(prefix="v41x_activation_bank_") as tmp:
        for name, tb, dut, fixture, arg, pattern in CASES:
            rtl = ROOT / f"rtl/hdc/v41x/{dut}.sv"
            test = ROOT / f"rtl/test/{tb}.sv"
            data = ROOT / f"rtl/test/data/{fixture}"
            sources.extend((rtl, test, data))
            sim = Path(tmp) / name
            cmd = ["iverilog", "-g2012", "-s", tb, "-o", str(sim), str(rtl), str(test)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            run = subprocess.run(["vvp", str(sim), f"+{arg}={data}"], check=True,
                                 capture_output=True, text=True, timeout=300)
            match = re.search(pattern, run.stdout)
            if not match:
                raise RuntimeError(f"{name}: success marker missing: {run.stdout[-2000:]}")
            records.append({"name": name, "passed": True, "marker": match.group(),
                            "fixture_sha256": sha(data)})
    out = {
        "schema": "opentallas.v41x.activation-bank-campaign.v1",
        "scope": "standalone full-shape ME/HE activation bank protocol, not arithmetic or die throughput",
        "golden_context": 200000,
        "golden_layer": 0,
        "golden_shard_npz_sha256_at_fixture_generation": "d642ca564e20edc34f729656461fa2bd68ecf55d1b706f2043c382f157ed6de3",
        "fixture_origin": {
            "me_two_group": "first 8192 BF16 elements of golden h_in, split as two K4096 vectors",
            "me_two_group_wide": "same two real K4096 vectors, supplied as 64 BF16 elements/cycle",
            "me_random_segments": "L0.attn_norm and L0.ffn_norm, each 5120 BF16 elements",
            "he_slice": "golden h_in BF16 elements at 8*((r mod 10)*256+lane), r=0..79, lane=0..7",
            "he_slice_wide": "same real HCP slice values supplied as 128-bit whole-word writes",
        },
        "cases": records,
        "sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(sources))},
        "load_floor_cycles_per_layer": {"old_eight_K4096_G4": 8192,
                                        "corrected_two_K4096_G4": 2048,
                                        "proposed_two_K4096_G64": 128},
        "latency_contract": "one registered SRAM read; ME tile RL=2 and HCP ML=2 unchanged",
        "limitations": ["Golden residuals are fixture values, not a complete ME or HCP computation.",
                        "G64 requires a distinct 64-element VM prefetch interface and is not RTL-integrated.",
                        "HE wide slice ingress is not connected to VM or HCP adapter.",
                        "ASAP7 standard-cell routes do not establish SRAM macro area or timing."],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(records)} passed")


if __name__ == "__main__":
    main()
