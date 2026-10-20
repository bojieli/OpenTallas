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
S81-SHLK 10-18: pos7 (OT_HOSTNATIVE_PIPE7 = FPIPE 2 / APIPE 7) must pass; hreg7 / hregv7 / rac7 must be caught.
Prints HNP_PASS / HNP_FAIL (pos, base) or HNP_NEG_DETECTED (rc 1) / HNP_NEG_MISSED (rc 0) and the ck cycles per case."""
import re
import os
import subprocess
import hashlib
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
if os.environ.get('HNP_S10B') == '1':
    # S81-SHLK s10b: segments of 16k sectors start st_left with a zero low nibble, so the first step borrows from the
    # registered hi - 1 right after the segment load (catches a refresh that overwrites the loaded value, hphold10)
    extra["raw_b16"] = case_raw_multi(np.random.default_rng(20261020), [1, 1, 0, 1, 1], [16, 32, 16, 48, 1])
# Exercise the actual failed block-address cone across ap1_gs[7] / sb boundary.
if mode in ('pos8','pos9','apbskip9','apstale9','apxskip9','pos10','apbskip10','apstale10','apxskip10','sprh10','spkind10','rac10','banktail10','rszswap10','sramcur10','dqc10','hrc10','hpref10','hphold10','cxrc10','s10cwa10','s10ciss10','s10dox10','s10dfq10'):
    extra['ikey_cross_sb'] = C.case_ikey(np.random.default_rng(20261019),256,first=32720,ndie=4,die=2,ns=4)
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
        "apstale": ["-DOT_HOSTNATIVE_PIPE", "-DOT_ING_MUT_APSTALE"],
        # S81-SHLK 10-18: dsdv_sh_lk's ingest (FPIPE 2, APIPE 7: registered host-FIFO head + realigner pointer copies)
        "pos7": ["-DOT_HOSTNATIVE_PIPE7"], "hreg7": ["-DOT_HOSTNATIVE_PIPE7", "-DOT_ING_MUT_HREG"],
        "hregv7": ["-DOT_HOSTNATIVE_PIPE7", "-DOT_ING_MUT_HREGV"], "rac7": ["-DOT_HOSTNATIVE_PIPE7", "-DOT_ING_MUT_RAC"],
        # S81-SAFE-FIX/SH 10-19: APIPE 8 (IKEY address stage split): pos8 must pass, apbskip8 / apstale8 must be caught
        "pos9": ["-DOT_HOSTNATIVE_PIPE9"], "apbskip9": ["-DOT_HOSTNATIVE_PIPE9", "-DOT_ING_MUT_APBSKIP"],
        "apstale9": ["-DOT_HOSTNATIVE_PIPE9", "-DOT_ING_MUT_APSTALE"], "apxskip9": ["-DOT_HOSTNATIVE_PIPE9", "-DOT_ING_MUT_APXSKIP"],
        # S81-SHLK s10 10-19: APIPE 10 (stream pipe + split row product): pos10 must pass, the rest must be caught
        "pos10": ["-DOT_HOSTNATIVE_PIPE10"], "apbskip10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_APBSKIP"],
        "apstale10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_APSTALE"], "apxskip10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_APXSKIP"],
        "sprh10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_SPRH"], "spkind10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_SPKIND"],
        "rac10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_RAC"],
        "banktail10": ["-DOT_HOSTNATIVE_PIPE10", "-DS81SH_BANK_MUT_TAIL"],   # run with HNP_SRAM=1 HNP_BANK64=1
        "rszswap10": ["-DOT_HOSTNATIVE_PIPE10", "-DS81SH_RSZ_MUT_SWAP"],     # run with HNP_SRAM=1 HNP_RSZ=1
        "sramcur10": ["-DOT_HOSTNATIVE_PIPE10", "-DS81SH_SRAM_MUT_CURRENT"],  # run with HNP_SRAM=1 (+ HNP_RSZ=1)
        # S81-SHLK s10b 10-19 (run with HNP_S10B=1): kept dq_rd / hr_v / empty / u_cx read copies, split st_row / st_left
        "dqc10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_DQC"], "hrc10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_HRC"],
        "hpref10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_HPREF"], "hphold10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_HPHOLD"],
        "cxrc10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_LINK_AFIFO_MUT_RCOPY"],
        # S81-SHLK s10c 10-19 (run with HNP_S10B=1 HNP_S10C=1): stage-O address add, registered issue counter
        "s10cwa10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_S10CWA"], "s10ciss10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_S10CISS"],
        # S81-SHLK s10d 10-19 (run with HNP_S10B=1 HNP_S10C=1 HNP_S10D=1): kept enable copies (ox payload, fq write)
        "s10dox10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_S81_SH_MUT_S10DOX"], "s10dfq10": ["-DOT_HOSTNATIVE_PIPE10", "-DOT_ING_MUT_S10DFQ"],
        "pos8": ["-DOT_HOSTNATIVE_PIPE8"], "apbskip8": ["-DOT_HOSTNATIVE_PIPE8", "-DOT_ING_MUT_APBSKIP"],
        "apstale8": ["-DOT_HOSTNATIVE_PIPE8", "-DOT_ING_MUT_APSTALE"]}[mode]
srcs = [R / s for s in [B.SECDED] + B.HOST_RTL + ["rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv",
                                                  "rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv"]] + [w / "tb.sv"]
# Explicit fleet-only Verilator backend. Keep legacy Icarus mode available.
if os.environ.get('HNP_VERILATOR') == '1':
    max_memw=max(c['memw'] for c in cases.values())
    max_np=max(1 << max(4,(len(c['beats'])-1).bit_length()) for c in cases.values())
    def sim_vlt(case_dir, sources, top, extra, plus=()):
        vl=os.environ.get('VL',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
        flags=[]
        for a in extra:
            if a.startswith('-P'+top+'.'):
                name,val=a.split('.',1)[1].split('=',1)
                if name=='MEMW':val=str(max_memw)
                if name=='NP':val=str(max_np)
                flags.append('-G'+name+'='+val)
            else:flags.append(a)
        if os.environ.get('HNP_SAMECLOCK') == '1':flags += ['-GHP=833','-GIP=833','-GCP=833']
        obj=w/'obj_vlt';binary=obj/('V'+top)
        if not binary.exists():
            args=[vl,'--binary','--timing','-j',os.environ.get('J','16'),'-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','-Wno-UNOPTFLAT','--top-module',top,'--Mdir',str(obj),*flags,*map(str,sources)]
            (w/'sources.sha256').write_text(''.join(hashlib.sha256(Path(f).read_bytes()).hexdigest()+'  '+str(f)+'\n' for f in sources))
            (w/'verilator.version').write_text(subprocess.check_output([vl,'--version'],text=True))
            with (w/'build_vlt.log').open('w') as out:
                out.write(repr(args)+'\n');out.flush()
                rc=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT).returncode
            if rc:raise RuntimeError('Verilator build failed: '+str(w/'build_vlt.log'))
        r=subprocess.run([str(binary),*plus],cwd=case_dir,capture_output=True,text=True)
        return r.returncode,r.stdout+r.stderr
    B.sim=sim_vlt
if os.environ.get('HNP_SRAM') == '1':
    defs += ['-DOT_S81_SH_SRAM']
    srcs += [R/'rtl/dsrom_sys/s81_dv/unit/host_sram/ot_dsdv_host_afifo_sram.sv', R/'physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v']
if os.environ.get('HNP_RSZ') == '1':         # S81-SHLK s10: right-sized 16x257 / 16x289 masters
    defs += ['-DOT_S81_SH_RSZ']
    srcs += [R/'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x257_m1/ot_sram_1r1w2c_16x257_m1.v',
             R/'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x289_m1/ot_sram_1r1w2c_16x289_m1.v']
if os.environ.get('HNP_S10B') == '1':        # S81-SHLK s10b: fanout copies + split row / left counters
    defs += ['-DOT_S81_SH_S10B']
if os.environ.get('HNP_S10C') == '1':        # S81-SHLK s10c: stage-O address add + registered issue counter
    defs += ['-DOT_S81_SH_S10C']
if os.environ.get('HNP_S10D') == '1':        # S81-SHLK s10d: kept ox payload / fq write enable copies
    defs += ['-DOT_S81_SH_S10D']
if os.environ.get('HNP_BANK64') == '1':      # S81-SHLK s10: native 32x64 banks instead of the 16x546 macro
    defs += ['-DOT_S81_SH_BANK64']
    srcs += [R/'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v']
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
# S81-SHLK s10: APIPE 10 delays the stream sectors through a pipe and the boot-end marker by 2 edges; the marker must
# still follow every sector (tb BOOTEND: marker word checked against the sectors written).  Stalled fabric (MSTALL 90).
if mode.endswith("10"):
    c = cases["raw_fenced_stall"]
    ex = [f"-Ptb_rom_host_ingest.{k}={v}" for k, v in dict(MEMW=c["memw"], ND=16, NP=1 << max(4, (len(c["beats"]) - 1).bit_length()),
                                                         HDMAX=16, KVHMAX=1, QKV_EN=0, RMW_EN=0).items()]
    rc, out = B.sim(w / "raw_fenced_stall", srcs, "tb_rom_host_ingest", defs + ex,
                    [f"+ND={len(c['descs'])}", f"+NP={len(c['beats'])}", "+MSTALL=90", "+SEED=5", "+BOOTEND=1",
                     f"+BCOUNT={sum(c['sizes'])}"])
    (w / "raw_fenced_stall_boot.log").write_text(out)
    mm = re.search(r"marks=(\d+) mark_bad=(\d+)", out)
    good = rc == 0 and bool(B.hing_ok(out)) and bool(mm) and mm.group(1) == "1" and mm.group(2) == "0"
    print(f"case raw_fenced_stall_boot {'PASS' if good else 'FAIL'} marks={mm.group(1) if mm else '?'} mark_bad={mm.group(2) if mm else '?'}")
    ok_all &= good
if mode in ("fencevis", "fencevis2"):
    print("HNP_NEG_DETECTED (visibility check)" if vis_only else "HNP_NEG_MISSED (no visibility-only catch)")
    sys.exit(1 if vis_only else 0)
if mode in ("pos", "base", "pos2", "pos7", "pos8", "pos9", "pos10"):
    print("HNP_PASS" if ok_all else "HNP_FAIL")
    sys.exit(0 if ok_all else 1)
print("HNP_NEG_DETECTED" if not ok_all else "HNP_NEG_MISSED")
sys.exit(1 if not ok_all else 0)
