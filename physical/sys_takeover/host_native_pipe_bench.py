#!/usr/bin/env python3
"""sys-takeover 2026-10-09: dsfd_host_native with the opt-in pipeline (FPIPE fence head-ready register, ENG_TRIM engine
without the dead QKV path, APIPE registered stream address terms; `OT_HOSTNATIVE_PIPE sets all three).  The committed
exact HBM-image bench tb_rom_host_ingest around dsfd_host_native (physical/strip_protect/bench.py host_tb: raw + v41
window cases, host_ack_n = the fabric's actual sector writes, MSTALL 30) PLUS a visibility check: every fenced done word's
sector count must already be written to the HBM model when the done word leaves (the fence's job).
    host_native_pipe_bench.py pos|base|fence|fencevis|apstale OUT
fencevis: the fence mutant must be caught by the VISIBILITY check alone (raw_fenced_stall: hing ok, vis_err > 0).
rev c (OT_HOSTNATIVE_PIPE2: fence PIPE 2, engine APIPE 2): pos2, fencevis2, apstale2 (must catch); nseclag2 / ltstale2 are
recorded as NOT consuming on these fault-free cases: the done word never leaves on the edge of its own last write here (so
the one-edge done delay is not observed), and the registered monotonic check only fires on a protocol fault.
RAW multi-descriptor cases also check every done word's count EXACTLY (cumulative sectors up to that descriptor).
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
# coordinator 2026-10-09: several fenced completions back to back and interleaved with unfenced descriptors, so the
# visibility check (a done word leaving before its sectors are written) is what catches an early release
sys.path.insert(0, str(R / "tools"))
import numpy as np  # noqa: E402
import rtl_hdc_kv_ingest_campaign as C  # noqa: E402
import kv_ingest_ref as KR  # noqa: E402


def case_raw_multi(rng, fences, sizes, base=40):
    descs, beats, a0 = [], [], base
    exp = np.zeros((base + sum(sizes) + 64) * 32, dtype=np.uint8)
    for k, (f, n) in enumerate(zip(fences, sizes)):
        data = rng.integers(0, 256, n * 32, dtype=np.uint8)
        exp[a0 * 32:(a0 + n) * 32] = data
        bt = KR.beats_of(data.tobytes())
        descs.append(KR.desc(KR.M_RAW, fence=f, tag=(16 + k) & 255, a0=a0, n0=n, nb=len(bt)))
        beats += bt
        a0 += n
    return dict(descs=descs, beats=beats, init=np.zeros_like(exp), exp=exp, hd=16, kvh=2, meta=dict(fences=fences), sizes=list(sizes))


rngm = np.random.default_rng(20261010)
extra = {
    "raw_fenced_b2b": case_raw_multi(rngm, [1, 1, 1, 1, 1, 1, 1, 1], [1, 2, 1, 3, 1, 1, 2, 1]),
    "raw_fenced_mixed": case_raw_multi(rngm, [1, 0, 1, 1, 0, 0, 1, 0, 1, 1], [9, 4, 1, 17, 2, 6, 1, 3, 12, 1]),
    # fenced completions queue up behind a slow fabric (MSTALL 90): a later done word sits in the fence while an earlier
    # one waits for its writes, so any early release shows as a done count above the sectors written
    "raw_fenced_stall": case_raw_multi(rngm, [1, 1, 0, 1, 1, 0, 1, 1], [24, 2, 3, 24, 1, 2, 30, 1]),
}
extra["raw_fenced_stall"]["mstall"] = 90
for name, c in extra.items():
    c["nb"] = [(d >> 240) & 0xFFFF for d in c["descs"]]
    memw = C.pow2(max(c["exp"].size // 32 + 1, 1024 + 64))
    C.write_case(w / name, c, memw)
    (w / name / "nb.mem").write_text("".join(f"{x:08x}\n" for x in c["nb"]))
    c["memw"] = memw
    cases[name] = c
# visibility: a done word's count must not exceed the sectors already in the HBM model
a = "                if (t_d[63:56] == 8'h01) begin"
assert tb.count(a) == 1
tb = tb.replace(a, a + "\n                    $display(\"DONEW cnt=%0d\", t_d[31:0]);"
                       "\n                    if (t_d[31:0] > sectors) begin vis_err = vis_err + 1; "
                       "$display(\"VISIBILITY early done count=%0d written=%0d\", t_d[31:0], sectors); end")
a = "    integer dones = 0,"
assert tb.count(a) == 1
tb = tb.replace(a, "    integer vis_err = 0;\n" + a)
b = tb.index("$display(\"HING")
tb = tb[:b] + "$display(\"VIS errors=%0d\", vis_err);\n            " + tb[b:]
(w / "tb.sv").write_text(tb)
P2 = ["-DOT_HOSTNATIVE_PIPE2"]     # rev c: FPIPE 2 / APIPE 2
defs = {"pos2": P2, "fencevis2": P2 + ["-DOT_FENCE_MUT_HRSTALE"], "apstale2": P2 + ["-DOT_ING_MUT_APSTALE"],
        "nseclag2": P2 + ["-DOT_ING_MUT_NSECLAG"], "ltstale2": P2 + ["-DOT_FENCE_MUT_LTSTALE"],
        "pos": ["-DOT_HOSTNATIVE_PIPE"], "base": [], "fence": ["-DOT_HOSTNATIVE_PIPE", "-DOT_FENCE_MUT_HRSTALE"],
        "fencevis": ["-DOT_HOSTNATIVE_PIPE", "-DOT_FENCE_MUT_HRSTALE"],
        "apstale": ["-DOT_HOSTNATIVE_PIPE", "-DOT_ING_MUT_APSTALE"]}[mode]
srcs = [R / s for s in [B.SECDED] + B.HOST_RTL + ["rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv",
                                                  "rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv"]] + [w / "tb.sv"]
ok_all = True
vis_only = False         # fencevis: a case whose ONLY failure is the visibility check (protocol counts all correct)
for name, c in cases.items():
    ex = [f"-Ptb_rom_host_ingest.{k}={v}" for k, v in dict(MEMW=c["memw"], ND=16, NP=1 << max(4, (len(c["beats"]) - 1).bit_length()),
                                                         HDMAX=16, KVHMAX=1, QKV_EN=0, RMW_EN=0).items()]
    rc, out = B.sim(w / name, srcs, "tb_rom_host_ingest", defs + ex,
                    [f"+ND={len(c['descs'])}", f"+NP={len(c['beats'])}", f"+MSTALL={c.get('mstall', 30)}", "+SEED=5"])
    (w / f"{name}.log").write_text(out)
    m = re.search(r"VIS errors=(\d+)", out)
    vis = int(m.group(1)) if m else -1
    # exact done counts (RAW cases): each fenced done word carries the cumulative sectors of every descriptor up to it
    cnt_err = 0
    if all((d & 15) == 0 for d in c["descs"]):
        exp = []
        sizes = c.get("sizes")
        if sizes:
            cum = 0
            for d, n in zip(c["descs"], sizes):
                cum += n
                if (d >> 7) & 1: exp.append(cum)
            got = [int(x) for x in re.findall(r"DONEW cnt=(\d+)", out)]
            cnt_err = 0 if got == exp else 1
            if cnt_err: print(f"  done counts {got} != expected {exp}")
    good = rc == 0 and bool(B.hing_ok(out)) and vis == 0 and cnt_err == 0
    fenced = sum(1 for d in c["descs"] if (d >> 7) & 1)
    cyc = re.search(r"ck_cycles=(\d+)", out)
    print(f"case {name} {'PASS' if good else 'FAIL'} descs={len(c['descs'])} fenced={fenced} hing={'ok' if B.hing_ok(out) else 'FAIL'} "
          f"vis_err={vis} ck_cycles={cyc.group(1) if cyc else '?'}")
    ok_all &= good
    vis_only |= bool(B.hing_ok(out)) and rc == 0 and vis > 0
if mode in ("fencevis", "fencevis2"):
    print("HNP_NEG_DETECTED (visibility check)" if vis_only else "HNP_NEG_MISSED (no visibility-only catch)")
    sys.exit(1 if vis_only else 0)
if mode in ("pos", "base", "pos2"):
    print("HNP_PASS" if ok_all else "HNP_FAIL")
    sys.exit(0 if ok_all else 1)
print("HNP_NEG_DETECTED" if not ok_all else "HNP_NEG_MISSED")
sys.exit(1 if not ok_all else 0)
