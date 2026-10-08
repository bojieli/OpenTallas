#!/usr/bin/env python3
"""SM -> SU native result edge against W13's golden: tools/hbm_accel_sm_v_gate.py with the bench
rtl/hbm_accel/contracts_20261007/tb_hbm_sm_su_composed.sv (the SM's result face goes through pin station, relay
stations, pin station and the SU result ingress; out.txt is written from the ingress drain).  Both SM variants
(ENABLE 0 = W13 ot_gpu_sm_v, 1 = the 1.2 GHz successor) must be exact against hdc_golden_v41.

    python3 tools/hbm_sm_su_composed_gate.py synth --simulator verilator --cols 1 2 --out R.json
    python3 tools/hbm_sm_su_composed_gate.py synth --simulator verilator --cols 2 --out R.json --mutant payload
      (negative: one payload bit flipped inside the ingress head -> every case must be NOT exact)
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hbm_accel_sm_v_gate as G  # noqa: E402

CT = "rtl/hbm_accel/contracts_20261007/"
EDGE = ["rtl/hbm_accel/result_relay_stage_20261007/ot_hbm_result_relay_slice.sv",
        "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
        CT + "ot_hbm_su_result_ingress.sv", CT + "ot_hbm_sm_su_result_edge.sv"]


def main():
    argv = sys.argv[1:]
    mutant = None
    if "--mutant" in argv:
        i = argv.index("--mutant")
        mutant = argv[i + 1]
        del argv[i:i + 2]
    src = [s for s in G.SRC if s != "rtl/test/tb_hbm_accel_sm_v.sv"] + EDGE + [CT + "tb_hbm_sm_su_composed.sv"]
    if mutant == "payload":
        text = (ROOT / CT / "ot_hbm_su_result_ingress.sv").read_text()
        old = "assign out_row=head[RW+DW-1:DW];assign out_data=head[DW-1:0];"
        assert text.count(old) == 1
        d = Path(tempfile.mkdtemp(prefix="smsu_mut_"))
        (d / "ot_hbm_su_result_ingress.sv").write_text(text.replace(old, "assign out_row=head[RW+DW-1:DW];assign out_data=head[DW-1:0]^{{(DW-1){1'b0}},1'b1};"))
        src = [str(d / "ot_hbm_su_result_ingress.sv") if s == CT + "ot_hbm_su_result_ingress.sv" else s for s in src]
    G.SRC = src
    G.TB = "tb_hbm_sm_su_composed"
    rc = G.main(argv)
    if mutant:
        import json
        out = Path(argv[argv.index("--out") + 1])
        rec = json.loads(out.read_text()) if out.is_file() else {}
        detected = rec.get("cases", 0) > 0 and rec.get("mismatching_cases") == rec.get("cases")
        print("SMSU_MUTANT_DETECTED" if detected else "SMSU_MUTANT_ESCAPED", rec.get("mismatching_cases"), rec.get("cases"))
        return 1 if detected else 0
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
