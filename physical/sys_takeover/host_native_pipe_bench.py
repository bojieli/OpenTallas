#!/usr/bin/env python3
"""sys-takeover 2026-10-09: dsfd_host_native with the opt-in pipeline (FPIPE fence head-ready register, ENG_TRIM engine
without the dead QKV path, APIPE registered stream address terms; `OT_HOSTNATIVE_PIPE sets all three).  The committed
exact HBM-image bench tb_rom_host_ingest around dsfd_host_native (physical/strip_protect/bench.py host_tb: raw + v41
window cases, host_ack_n = the fabric's actual sector writes, MSTALL 30) PLUS a visibility check: every fenced done word's
sector count must already be written to the HBM model when the done word leaves (the fence's job).
    host_native_pipe_bench.py pos|base|fence|apstale OUT
pos: pipeline ON, must pass; base: pipeline OFF (the original), must pass; fence / apstale: mutants OT_FENCE_MUT_HRSTALE
(release flag not cleared on a pop) / OT_ING_MUT_APSTALE (stale row address across rows), must fail.
Prints HNP_PASS / HNP_FAIL (pos, base) or HNP_NEG_DETECTED (rc 1) / HNP_NEG_MISSED (rc 0) and the ck cycles per case."""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "physical/strip_protect"))
import bench as B  # noqa: E402

mode, w = sys.argv[1], Path(sys.argv[2]).resolve()
w.mkdir(parents=True, exist_ok=True)
B.KEY = "host_native"
tb, cases = B.host_tb(w)
# visibility: a done word's count must not exceed the sectors already in the HBM model
a = "                if (t_d[63:56] == 8'h01) begin"
assert tb.count(a) == 1
tb = tb.replace(a, a + "\n                    if (t_d[31:0] > sectors) begin vis_err = vis_err + 1; "
                       "$display(\"VISIBILITY early done count=%0d written=%0d\", t_d[31:0], sectors); end")
a = "    integer dones = 0,"
assert tb.count(a) == 1
tb = tb.replace(a, "    integer vis_err = 0;\n" + a)
b = tb.index("$display(\"HING")
tb = tb[:b] + "$display(\"VIS errors=%0d\", vis_err);\n            " + tb[b:]
(w / "tb.sv").write_text(tb)
defs = {"pos": ["-DOT_HOSTNATIVE_PIPE"], "base": [], "fence": ["-DOT_HOSTNATIVE_PIPE", "-DOT_FENCE_MUT_HRSTALE"],
        "apstale": ["-DOT_HOSTNATIVE_PIPE", "-DOT_ING_MUT_APSTALE"]}[mode]
srcs = [R / s for s in [B.SECDED] + B.HOST_RTL + ["rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv",
                                                  "rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv"]] + [w / "tb.sv"]
ok_all = True
for name, c in cases.items():
    ex = [f"-Ptb_rom_host_ingest.{k}={v}" for k, v in dict(MEMW=c["memw"], ND=16, NP=1 << max(4, (len(c["beats"]) - 1).bit_length()),
                                                         HDMAX=16, KVHMAX=1, QKV_EN=0, RMW_EN=0).items()]
    rc, out = B.sim(w / name, srcs, "tb_rom_host_ingest", defs + ex,
                    [f"+ND={len(c['descs'])}", f"+NP={len(c['beats'])}", "+MSTALL=30", "+SEED=5"])
    (w / f"{name}.log").write_text(out)
    m = re.search(r"VIS errors=(\d+)", out)
    vis = int(m.group(1)) if m else -1
    good = rc == 0 and bool(B.hing_ok(out)) and vis == 0
    cyc = re.search(r"ck_cycles=(\d+)", out)
    print(f"case {name} {'PASS' if good else 'FAIL'} vis_err={vis} ck_cycles={cyc.group(1) if cyc else '?'}")
    ok_all &= good
if mode in ("pos", "base"):
    print("HNP_PASS" if ok_all else "HNP_FAIL")
    sys.exit(0 if ok_all else 1)
print("HNP_NEG_DETECTED" if not ok_all else "HNP_NEG_MISSED")
sys.exit(1 if not ok_all else 0)
