#!/usr/bin/env python3
"""DS-ROM 1M token, the HEAD stage measured at full shape on its minimum component (AR path).

Graph nodes (s81_nodes_dump.json): head.lm_head (bf16 [129280, 5120], vocabulary split 4 ways: 32,320 rows a rank,
model 12.39 us), head.argmax (local), head.argmax_merge (4-die {logit, id} gather: bytes only, the parent prices the
collective).

Vehicle (as built, simulate the minimum component):
  lm_head   ONE head return group of the S81 native BF head mapping: 16 logical macros (8 element pairs
            ot_v41_rom_elem_w10 FAST PP BP=2 NB=2 NCH=24, 32 ROM4096 macros) behind the W10 return tree
            (rtl/test/w10_validation/ot_v41_rom_array_w10_test.sv), carrying its full-shape row share: 408 rows of
            the released head.weight (8,160 of the 8,192 words of every logical macro; the S81 storage share is
            409.6 rows a group, 2,525 ROM4096 a rank = 78.9 groups).  Every row is the S81 native split: phase A
            K 0..4095 (root4096) and phase B K 4096..5119 (root1024), both against the GOLDEN final-norm x of the
            1M token (ctx1048576_head.npz xf); every root must equal the golden partial (chunk8 csum) bit for bit and
            the merged logit root4096 + ((root1024 + 0) + 0) must equal the golden logit.  The group holds the
            golden argmax row (21,946).
            Schedules (same element, same rows):  native  one row pair per phase (the S81 native producer grain);
                                                  packed  the most rows a phase the element admits (24 chain slots).
  argmax    the S81 native ordered-root terminal (rtl/test/s81_native_head_terminal/native_head_terminal.sv: three
            LAT3 FP32 adds, the lowest-id first-max comparator) on ALL 32,320 rows of rank 0 at II 1: the measured
            group's roots are the RTL's, the other rows' are golden partials; every logit and the rank's argmax are
            checked against the golden logits.

    python3 tools/dsrom_1m_head.py golden  --work DIR                 (roots of rank 0 from the checkpoint)
    python3 tools/dsrom_1m_head.py lmhead  --work DIR --sched native|packed
    python3 tools/dsrom_1m_head.py argmax  --work DIR
    python3 tools/dsrom_1m_head.py record  --work DIR --output results/rtl/dsrom_1m_allmeasured_20261004/head.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from w10_validation import rtl_v41_rom_array as gate  # noqa: E402

G, S = gate.G, gate.S
SNAP = Path(os.environ.get("DSROM_1M_SNAP", Path.home() / (
    ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277")))
REF = Path(os.environ.get("DSROM_1M_HEAD_REF", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930/ctx1048576_head.npz"))
NODES = Path(os.environ.get("DSROM_1M_NODES", "/nonexistent/s81_nodes_dump.json"))   # default: rebuild from the graph
TB_ARRAY = "rtl/test/dsrom_sys/tb_dsrom_1m_head_array.sv"
TB_TERM = "rtl/test/dsrom_sys/tb_dsrom_1m_head_terminal.sv"
TERM = ["rtl/test/s81_native_head_terminal/native_head_terminal.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
VOCAB, K, RANKS = 129280, 5120, 4
ROWS_RANK = VOCAB // RANKS                   # 32,320
RANK = 0
N, NB = 16, 2                                # one return group: 16 logical macros = 8 element pairs
GROUP_ROWS = 408                             # 8,160 of 8,192 words a logical macro (20 words a row a macro)
S81_GROUP_ROWS = 409.6                       # S81 storage: 262,144 BF16 a pair, 8 pairs a group
GOLD_TOKEN = 21946
GROUP0 = (GOLD_TOKEN // GROUP_ROWS) * GROUP_ROWS     # 21,624: the group holding the golden argmax row
SCHED = {"native": dict(A=2, B=2), "packed": dict(A=6, B=8)}
F_ELEM, F_SERIAL = 1.2e9, 0.9e9


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def setup_gate():
    """The W10 gate at the head element's configuration (BP = 2: 2 BF16 multipliers a macro, 8-cycle word hold)."""
    S.BF16_PAIR, S.BF16_WORD_CYCLES, S.BF16_SPLIT_BOOST = True, 8, 1
    S.IL_BF16, S.BF16_CAP, S.BF16_MAX_UNITS = 1, 3, 4
    S.FADD_REC = gate.FAST_LAT
    G.set_arith("chunk8")


class Ckpt(gate.Ckpt):
    """The gate's checkpoint reader with the head tensor read once (every phase slices it)."""

    def __init__(self, snap):
        super().__init__(snap)
        self._cache = {}

    def raw(self, name):
        if name not in self._cache:
            self._cache[name] = super().raw(name)
        return self._cache[name]


def golden_x():
    z = np.load(REF)
    xf = np.asarray(z["xf"], dtype=np.float32)
    assert not (xf.view(np.uint32) & 0xFFFF).any(), "xf must be BF16"
    return xf, np.asarray(z["logits"], dtype=np.float32)


def merge(a, b):
    """The golden padded tree at K = 5120 (640 chunks -> 1024): root4096 + ((root1024 + 0) + 0)."""
    z = np.zeros_like(b)
    return G.add(a, G.add(G.add(b, z), z))


# ------------------------------------------------------------------------------------------------------------
# golden partial roots of rank 0
# ------------------------------------------------------------------------------------------------------------
def cmd_golden(a):
    setup_gate()
    xf, logits = golden_x()
    ck = Ckpt(SNAP)
    r0 = RANK * ROWS_RANK
    ra, rb = [], []
    for s in range(0, ROWS_RANK, 2048):
        n = min(2048, ROWS_RANK - s)
        m = gate.Mat(ck, "head", "bf16", n, K, r0=r0 + s)
        p = G.mul(np.asarray(m.wf, dtype=G.F), xf[None, :])
        ra.append(G.csum(p[:, :4096]))
        rb.append(G.csum(p[:, 4096:]))
        full = G.csum(p)
        assert np.array_equal(G.bits(merge(ra[-1], rb[-1])), G.bits(full)), "padded-tree split"
        assert np.array_equal(G.bits(full), G.bits(logits[r0 + s:r0 + s + n])), "golden logits"
        print(f"rows {r0 + s}..{r0 + s + n}: split == csum == golden logits", flush=True)
    ra, rb = np.concatenate(ra), np.concatenate(rb)
    a.work.mkdir(parents=True, exist_ok=True)
    np.savez(a.work / "roots_rank0.npz", root4096=G.bits(ra), root1024=G.bits(rb))
    sl = logits[r0:r0 + ROWS_RANK]
    rec = dict(rank=RANK, rows=ROWS_RANK, split_equals_golden=True, logits_equal_npz=True,
               argmax_rank=int(r0 + np.argmax(sl)), argmax_bits=int(G.bits(sl[np.argmax(sl)])),
               argmax_global=int(np.argmax(logits)), checkpoint_header_sha256=ck.pins)
    (a.work / "golden.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec))


# ------------------------------------------------------------------------------------------------------------
# lm_head: one return group, many back-to-back phases
# ------------------------------------------------------------------------------------------------------------
class XRng:
    """build_phase draws x as to_bf16(standard_normal(K) * 0.5): hand it the golden x slice instead (exact)."""

    def __init__(self, x):
        self.x = np.asarray(x, dtype=np.float64) * 2.0

    def standard_normal(self, k):
        assert k == len(self.x)
        return self.x.copy()


def build_group(work: Path, sched: str):
    setup_gate()
    xf, _ = golden_x()
    ck = Ckpt(SNAP)
    NE = N // NB
    die = S.Die(NE, NE)
    acc = {}
    plan = []                                     # (part, r0, rows)
    rA, rB = SCHED[sched]["A"], SCHED[sched]["B"]
    for part, step, k0, kk in (("A", rA, 0, 4096), ("B", rB, 4096, 1024)):
        for s in range(0, GROUP_ROWS, step):
            plan.append((part, GROUP0 + s, min(step, GROUP_ROWS - s), k0, kk))
    if sched == "native":                          # row pair by row pair: A then B
        plan.sort(key=lambda p: (p[1], p[0]))
    cfg_lines, st_lines, meta, phs = [], [], [], []
    for k, (part, r0, n, k0, kk) in enumerate(plan):
        sub = work / f"ph{k}"
        sub.mkdir(parents=True, exist_ok=True)
        m = gate.Mat(ck, "head", "bf16", n, kk, r0=r0, k0=k0, phase="wo_a")
        ph = gate.build_phase([m], N, sub, XRng(xf[k0:k0 + kk]), nb=NB, die=die, acc=acc, pp=True)
        assert ph["chain_slots"] <= 24 and ph["base_nodes"] <= 32, (k, ph["chain_slots"], ph["base_nodes"])
        cfg_lines += (sub / "cfg.hex").read_text().split()
        st_lines += (sub / "stream.hex").read_text().split()
        meta.append((int(ph["bf"]) << 72) | (ph["nrows"] << 48) | (ph["nst"] << 24) | ph["ncfg"])
        phs.append(dict(part=part, r0=r0, rows=n, k0=k0, K=kk, t_pred=ph["t_pred"], ncfg=ph["ncfg"], nst=ph["nst"],
                        exp_fp32={str(r): v for (_, r), v in ph["exp_fp32"].items()},
                        segments_per_element=ph["elements"]))
    for key, words in acc.items():
        if key[0] == "pp":
            _, e, mb = key
            for bk in (0, 1):
                gate.viamap(words[bk], work / f"e{e}{'b' if mb else ''}_{bk}.viamap.hex", 4096)
    pb = {k[1]: v for k, v in acc.items() if k[0] == "pbase"}
    (work / "cfg.hex").write_text("".join(x + "\n" for x in cfg_lines))
    (work / "stream.hex").write_text("".join(x + "\n" for x in st_lines))
    (work / "meta.hex").write_text("".join(f"{m:019x}\n" for m in meta))
    (work / "plan.json").write_text(json.dumps(dict(sched=sched, phases=phs, words_per_logical_macro=pb,
                                                    checkpoint_header_sha256=ck.pins)) + "\n")
    return phs, pb, len(cfg_lines), len(st_lines)


def build_sim(work: Path) -> Path:
    out = work / "obj"
    exe = out / "Vtb_dsrom_1m_head_array"
    if exe.exists():
        return exe
    cmd = [str(gate.VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-O2",
           f"-GN={N}", f"-GXF={gate.XF_BF}", f"-GNB={NB}", "-GMTP=1", "-GEARLY=0", "-GBYPASS=0", "-GFAST=1",
           "-GPP=1", "-GBP=2", "-GFRONT_PAR=0", "--top-module", "tb_dsrom_1m_head_array", "-Mdir", str(out),
           str(ROOT / TB_ARRAY)] + [str(ROOT / p) for p in gate.RTL + gate.RTL_FAST]
    subprocess.run(cmd, check=True, cwd=work, stdout=subprocess.DEVNULL)
    return exe


def cmd_lmhead(a):
    work = a.work / f"lmhead_{a.sched}"
    work.mkdir(parents=True, exist_ok=True)
    phs, pb, ncfg, nst = build_group(work, a.sched)
    print(json.dumps(dict(phases=len(phs), cfg=ncfg, stream=nst, words=pb)), flush=True)
    if a.build_only:
        return
    exe = build_sim(work)
    r = subprocess.run([str(exe), f"+DIR={work}", f"+OT_ROM_DIR={work}", f"+PHASES={len(phs)}"],
                       capture_output=True, text=True, check=True)
    (work / "sim.log").write_text(r.stdout)
    rows, pinfo = {}, {}
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "ROW":           # ROW row fp32 bf16 err cyc pos phase abs
            rows.setdefault(int(t[7]), {})[int(t[1])] = (int(t[2], 16), int(t[8]))
        elif t and t[0] == "PHASE":       # PHASE p cfg_start go last_row idle fault hung
            pinfo[int(t[1])] = dict(cfg_start=int(t[2]), go=int(t[3]), last_row=int(t[4]), idle=int(t[5]),
                                    fault=int(t[6]), hung=int(t[7]))
        elif t and t[0] == "DONE":
            done = int(t[1]), int(t[2])
    roots = {"A": {}, "B": {}}
    bad = 0
    for k, ph in enumerate(phs):
        got = rows.get(k, {})
        for tag, v in ph["exp_fp32"].items():
            g = got.get(int(tag))
            if g is None or g[0] != v:
                bad += 1
            roots[ph["part"]][ph["r0"] + int(tag)] = (g[0] if g else None, g[1] if g else None)
        ph.update(pinfo.get(k, {}))
        ph.pop("exp_fp32")
    res = dict(sched=a.sched, phases=phs, rows_bad=bad, roots_A=len(roots["A"]), roots_B=len(roots["B"]),
               done=done, words_per_logical_macro=pb)
    np.savez(work / "rtl_roots.npz",
             rows=np.array(sorted(roots["A"])),
             root4096=np.array([roots["A"][r][0] for r in sorted(roots["A"])], dtype=np.uint64),
             root1024=np.array([roots["B"][r][0] for r in sorted(roots["A"])], dtype=np.uint64),
             cycA=np.array([roots["A"][r][1] for r in sorted(roots["A"])], dtype=np.int64),
             cycB=np.array([roots["B"][r][1] for r in sorted(roots["A"])], dtype=np.int64))
    (work / "result.json").write_text(json.dumps(res) + "\n")
    print(json.dumps(dict(sched=a.sched, rows_bad=bad, done=done, first_go=pinfo[0]["go"],
                          last_row=max(p["last_row"] for p in pinfo.values()),
                          last_idle=pinfo[len(phs) - 1]["idle"])))


# ------------------------------------------------------------------------------------------------------------
# argmax: the native terminal on all 32,320 rows of rank 0
# ------------------------------------------------------------------------------------------------------------
def cmd_argmax(a):
    g = np.load(a.work / "roots_rank0.npz")
    ra, rb = g["root4096"].astype(np.uint32).copy(), g["root1024"].astype(np.uint32).copy()
    used = {}
    for sched in ("packed", "native"):
        p = a.work / f"lmhead_{sched}" / "rtl_roots.npz"
        if p.exists():
            z = np.load(p)
            idx = z["rows"] - RANK * ROWS_RANK
            assert np.array_equal(z["root4096"].astype(np.uint32), ra[idx]), sched
            assert np.array_equal(z["root1024"].astype(np.uint32), rb[idx]), sched
            ra[idx], rb[idx] = z["root4096"].astype(np.uint32), z["root1024"].astype(np.uint32)
            used[sched] = int(len(idx))
    work = a.work / "argmax"
    work.mkdir(parents=True, exist_ok=True)
    (work / "roots.hex").write_text("".join(f"{int(x):08x}{int(y):08x}\n" for x, y in zip(ra, rb)))
    out = work / "obj"
    exe = out / "Vtb_dsrom_1m_head_terminal"
    if not exe.exists():
        subprocess.run([str(gate.VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint",
                        "-Wno-style", "-O2", "--top-module", "tb_dsrom_1m_head_terminal", "-Mdir", str(out),
                        str(ROOT / TB_TERM)] + [str(ROOT / p) for p in TERM],
                       check=True, cwd=work, stdout=subprocess.DEVNULL)
    r = subprocess.run([str(exe), f"+DIR={work}"], capture_output=True, text=True, check=True)
    (work / "sim.log").write_text(r.stdout)
    _, logits = golden_x()
    r0 = RANK * ROWS_RANK
    gl = G.bits(logits[r0:r0 + ROWS_RANK]).astype(np.uint32)
    got = {}
    info = {}
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "L":
            got[int(t[1]) - r0] = int(t[2], 16)
        elif t and t[0] == "T":
            info = dict(first_in=int(t[1]), last_in=int(t[2]), last_logit=int(t[3]), done=int(t[4]),
                        best_row=int(t[5]), best_bits=int(t[6], 16), fault=int(t[7]), token_valid=int(t[8]))
    ok = sum(got.get(i) == int(gl[i]) for i in range(ROWS_RANK))
    sl = logits[r0:r0 + ROWS_RANK]
    res = dict(rows=ROWS_RANK, logits_out=len(got), logits_exact=ok, rtl_roots_from=used,
               golden_argmax=int(r0 + np.argmax(sl)), golden_argmax_bits=int(gl[np.argmax(sl)]), **info)
    res["argmax_exact"] = (info.get("best_row") == res["golden_argmax"] and info.get("best_bits") == res[
        "golden_argmax_bits"] and info.get("token_valid") == 1 and info.get("fault") == 0)
    (work / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


# ------------------------------------------------------------------------------------------------------------
# recovery lever "head": the ROM-read-rate bundle (rtl/v41rom/ot_dsrom_head_bundle.sv), one bundle of 128 rows
# ------------------------------------------------------------------------------------------------------------
TB_BUNDLE = "rtl/test/dsrom_sys/tb_dsrom_1m_head_bundle.sv"
BUNDLE_RTL = ["rtl/v41rom/ot_dsrom_head_bundle.sv", "rtl/v41rom/ot_dsrom_head_elem.sv", "rtl/v41rom/ot_v41_fadd.sv",
              "rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_dsrom_bmul3.sv", "rtl/hdc/ot_hdc_delay.sv",
              "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v"]
BUNDLE_ROWS, SK, NW = 128, gate.FAST_LAT, 8192
BUNDLE0 = (GOLD_TOKEN // BUNDLE_ROWS) * BUNDLE_ROWS          # 21,888: the bundle holding the golden argmax row
BUNDLES_RANK = ROWS_RANK / BUNDLE_ROWS                         # 252.5 (2,525 ROM4096 a rank, as S81)


def skewed_image(L):
    """L[g, j]: lane j (BF16 bits) of logical word g (8,192 x 16).  Physical word p lane j holds logical word
    (p - SK * (j mod 8)) mod 8192 (the systolic chain skew stored in the ROM image)."""
    p = np.arange(NW)[:, None]
    j = np.arange(16)[None, :]
    return L[(p - SK * (j % 8)) % NW, np.broadcast_to(j, (NW, 16))]


def write_macro(img, work: Path, inst: str):
    for bk in (0, 1):
        words = {}
        for adr in range(NW // 2):
            v = 0
            for j in range(16):
                v |= int(img[2 * adr + bk, j]) << (16 * j)
            words[adr] = v
        gate.viamap(words, work / f"{inst}_{bk}.viamap.hex", 4096)


def cmd_bundle(a):
    setup_gate()
    work = a.work / "lmhead_bundle"
    work.mkdir(parents=True, exist_ok=True)
    xf, logits = golden_x()
    x16 = (G.bits(xf).astype(np.uint32) >> 16).astype(np.uint64)
    ck = Ckpt(SNAP)
    m = gate.Mat(ck, "head", "bf16", BUNDLE_ROWS, K, r0=BUNDLE0)
    u = np.asarray(m.u16, dtype=np.uint64)
    for q in range(4):                                         # A: rows 32q + k, K 0..4095, 256 words a row
        write_macro(skewed_image(u[32 * q:32 * q + 32, :4096].reshape(NW, 16)), work, f"ha{q}")
    perm = np.array([32 * (n % 4) + n // 4 for n in range(BUNDLE_ROWS)])     # B row order n = 4k + q
    write_macro(skewed_image(u[perm, 4096:].reshape(NW, 16)), work, "hb")

    def slices(xx, n):
        return "".join("".join(f"{int(v):04x}" for v in xx[16 * i:16 * i + 16][::-1]) + "\n" for i in range(n))
    (work / "xa.hex").write_text(slices(x16[:4096], 256))
    (work / "xb.hex").write_text(slices(x16[4096:], 64))
    out = work / "obj"
    exe = out / "Vtb_dsrom_1m_head_bundle"
    if not exe.exists():
        subprocess.run([str(gate.VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint",
                        "-Wno-style", "-O2", "--top-module", "tb_dsrom_1m_head_bundle", "-Mdir", str(out),
                        str(ROOT / TB_BUNDLE)] + [str(ROOT / p) for p in BUNDLE_RTL],
                       check=True, cwd=work, stdout=subprocess.DEVNULL)
    r = subprocess.run([str(exe), f"+DIR={work}", f"+OT_ROM_DIR={work}", f"+ROW0={BUNDLE0}"],
                       capture_output=True, text=True, check=True)
    (work / "sim.log").write_text(r.stdout)
    A, Lg, B, res = {q: [] for q in range(4)}, {q: [] for q in range(4)}, [], None
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "A":
            A[int(t[1])].append((int(t[2], 16), int(t[3])))
        elif t and t[0] == "L":
            Lg[int(t[1])].append((int(t[2], 16), int(t[3])))
        elif t and t[0] == "B":
            B.append((int(t[2], 16), int(t[3])))
        elif t and t[0] == "RES":
            res = dict(row=int(t[1]), bits=int(t[2], 16), fault=int(t[3]), cycle=int(t[4]))
    g = np.load(a.work / "roots_rank0.npz")
    i0 = BUNDLE0 - RANK * ROWS_RANK
    ga = g["root4096"][i0:i0 + BUNDLE_ROWS].astype(np.uint32)
    gb = g["root1024"][i0:i0 + BUNDLE_ROWS].astype(np.uint32)
    gbp = G.bits(G.add(G.add(G.from_bits(gb), np.float32(0)), np.float32(0))).astype(np.uint32)
    gl = G.bits(logits[BUNDLE0:BUNDLE0 + BUNDLE_ROWS]).astype(np.uint32)
    okA = sum(len(A[q]) == 32 and all(A[q][k][0] == ga[32 * q + k] for k in range(32)) for q in range(4))
    okA_rows = sum(A[q][k][0] == ga[32 * q + k] for q in range(4) for k in range(min(32, len(A[q]))))
    okB_rows = sum(B[n][0] == gbp[perm[n]] for n in range(min(BUNDLE_ROWS, len(B))))
    okL_rows = sum(Lg[q][k][0] == gl[32 * q + k] for q in range(4) for k in range(min(32, len(Lg[q]))))
    gbest = int(np.argmax(logits[BUNDLE0:BUNDLE0 + BUNDLE_ROWS])) + BUNDLE0
    exact = (okA_rows == okB_rows == okL_rows == BUNDLE_ROWS and res is not None and res["fault"] == 0
             and res["row"] == gbest == GOLD_TOKEN and res["bits"] == int(G.bits(logits[GOLD_TOKEN])))
    out = dict(rows=[BUNDLE0, BUNDLE0 + BUNDLE_ROWS], root4096_exact=int(okA_rows), padded_root1024_exact=int(okB_rows),
               logits_exact=int(okL_rows), elements_complete=int(okA), result=res, golden_bundle_argmax=gbest,
               exact=bool(exact),
               cycles=dict(first_A_root=min(A[q][0][1] for q in range(4)), last_A_root=max(A[q][-1][1] for q in range(4)),
                           last_B_root=B[-1][1], last_logit=max(Lg[q][-1][1] for q in range(4)),
                           result=res["cycle"] if res else None,
                           rom_read_span=NW + 7 * SK, issue_offset=2),
               checkpoint_header_sha256=ck.pins)
    (work / "result.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


def _route(path: Path):
    """SS setup / FF hold summary of one routed element (tools/run_abi3_physical.py record)."""
    d = json.loads(path.read_text())
    c = [x for x in d["acceptance"]["checks"] if x.get("stage") == "place_and_route"][0]
    keys = ("setup_wns_ns", "setup_violations", "hold_wns_ns", "hold_violations", "drc_errors", "max_slew_violations",
            "max_cap_violations", "max_fanout_violations", "antenna_violating_nets", "timing_met", "physically_clean")
    return dict(record=str(path.resolve().relative_to(ROOT)), status=d["status"], closed=d["status"] in ("met", "pass"),
                **{k: c.get(k) for k in keys})


def cmd_lever(a):
    """Recovery lever record (opentallas.dsrom-recovery.lever.v1) from the bundle result and the two element routes."""
    if a.output.exists():
        raise SystemExit("refuse to overwrite a verdict")
    b = json.loads(a.bundle.read_text())
    old = json.loads((ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/head.json").read_text())
    nodes = node_params()
    lm = nodes["head.lm_head"]
    cyc = b["cycles"]
    # labelled additions (not routed): the model's broadcast/VM wire stages beyond the bench's BST 2, and the rank's
    # compare-tree levels above one bundle (ceil(log2(252.5)) = 8, one registered compare a level, as measured)
    wire = lm["_uarch"]["wire"] - 2
    rank_levels = math.ceil(math.log2(BUNDLES_RANK))
    lm_cyc = cyc["last_logit"] + wire
    am_cyc = (cyc["result"] - cyc["last_logit"]) + rank_levels
    lm_us, am_us = lm_cyc / F_ELEM * 1e6, am_cyc / F_ELEM * 1e6
    routes = {k: _route(Path(p)) for k, p in (("A", a.route_a), ("B", a.route_b))}
    closed = all(r["closed"] for r in routes.values())
    exact = bool(b["exact"])
    rec = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever="head",
        verdict="ADOPT" if exact and closed else "REJECT", exact=exact,
        ss_ff=dict(clock_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                   flow="tools/run_abi3_physical.py routed (ORFS WC=SS setup, WC+BC=FF hold repair, ADDER_MAP_FILE off, "
                        "PP 2-cycle macro read physical/abi3/v41_w10_elem_pp_multicycle.sdc, 2 x ot_rom_4096x274_m8)",
                   elements=routes, closed=closed),
        nodes={"head.lm_head": dict(us=round(lm_us, 4), cls="measured", source=(
                   f"ot_dsrom_head_bundle (5 logical macros, 16 BF16 mult/macro, skewed ROM, streaming tree, join) "
                   f"go->last logit {cyc['last_logit']} cyc measured + {wire} labelled wire cyc @1.2 GHz; every bundle "
                   f"of the rank runs in lockstep (252.5 bundles = 2,525 ROM4096)")),
               "head.argmax": dict(us=round(am_us, 4), cls="measured", source=(
                   f"in-element lowest-id first-max + 2-level bundle compare tree measured "
                   f"({cyc['result'] - cyc['last_logit']} cyc after the last logit) + {rank_levels} labelled rank "
                   f"compare levels (1 cyc each, same node)"))},
        info=dict(head_stage_occupancy_us=round(lm_us, 4), head_argmax_drain_us=round(am_us, 4),
                  occupancy_basis=("measured per-position lm_head sweep: go -> last logit of one bundle (all bundles in "
                                   "lockstep) + labelled wire; the DSpark draft heads and the verify head use the SAME "
                                   "array and the same occupancy (no separate draft head die group assumed)")),
        measurement=dict(
            vehicle=("rtl/v41rom/ot_dsrom_head_bundle.sv on bench " + TB_BUNDLE + ": rows "
                     f"{BUNDLE0}..{BUNDLE0 + BUNDLE_ROWS - 1} of rank 0 (the bundle holding the golden argmax 21,946), "
                     "4 A elements (K 0..4095, 32 rows each) + 1 B element (K 4096..5119, 128 rows), golden xf, "
                     "released head.weight (skewed ROM images)"),
            bundle=b, lm_head_cycles=lm_cyc, argmax_cycles=am_cyc,
            labelled_additions=dict(wire_cycles=wire, rank_compare_levels=rank_levels,
                                    basis="model head.lm_head _uarch wire 36 minus the bench's BST 2; "
                                          "ceil(log2(252.5 bundles)) compare levels; not routed -- LABELLED"),
            old=dict(lm_head_us=old["lm_head"]["us_1p2GHz"], argmax_drain_us=round((32320 - 408 + old["argmax"]["cycles"]) / F_SERIAL * 1e6, 3),
                     head_stage_occupancy_us=old["wavefront"]["head_stage_occupancy_us_per_position"]),
            model_lm_head_us=round(lm["issue_us"] + lm["depth_us"] + lm["ctrl_us"], 3),
            storage=("same 2,525 ROM4096 a rank as S81 (A elements: 32 rows x 256 words = 8,192 words; B: 128 rows x 64 "
                     "words = 8,192): zero spare words; the ROM image is a static permutation of the released payload "
                     "(row/K placement + systolic lane skew SK*(j mod 8))"),
            unmeasured=["routed x broadcast to the rank's head dies and the cross-die compare tree (labelled cycles)",
                        "argmax_merge across ranks (parent collective, unchanged)",
                        "occupancy for k positions: one position measured; the element streams (no per-position state "
                        "beyond the tree registers), occupancy taken as the full go->last-logit latency (conservative)"]),
        simulator=f"verilator 5.050 ({gate.VERILATOR})",
        source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        source_sha256={p: sha(ROOT / p) for p in [*BUNDLE_RTL, TB_BUNDLE, "tools/dsrom_1m_head.py", "tools/hdc_golden_v41.py",
                                                  "physical/abi3/v41_w10_elem_pp_multicycle.sdc"]})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], exact=exact, closed=closed, lm_head_us=rec["nodes"]["head.lm_head"]["us"],
                          argmax_us=rec["nodes"]["head.argmax"]["us"])))


# ------------------------------------------------------------------------------------------------------------
def node_params():
    """head.* node parameters of the S81 graph (tools/dsrom_1m_measure.s58_graph), in us and 1.2 GHz cycles."""
    if NODES.exists():
        d = json.loads(NODES.read_text())
        return {k: d[k] for k in ("head.lm_head", "head.argmax", "head.argmax_merge")}
    import dsrom_1m_measure as M
    g, _, _ = M.s58_graph()
    out = {}
    for k in ("head.lm_head", "head.argmax", "head.argmax_merge"):
        nd = {x: v for x, v in g.nodes[k].items() if x not in ("_hub_edge_die",)}
        for f in ("issue", "depth", "ctrl"):
            nd[f + "_us"] = nd[f] * 1e6
            nd[f + "_cyc_1p2"] = nd[f] * 1.2e9
            nd.pop(f)
        out[k] = nd
    return out


def group_times(res):
    """Cycles of one return group from the bench's absolute stamps (1.2 GHz element clock)."""
    ph = res["phases"]
    first_cfg, first_go = ph[0]["cfg_start"], ph[0]["go"]
    last_row = max(p["last_row"] for p in ph)
    cfg = sum(p["go"] - p["cfg_start"] for p in ph)
    # phases never overlap on an element (the spine): with the configuration writes hidden (preloaded), the group is
    # busy go -> idle for every phase but the last, which ends at its last root
    hidden = sum(p["idle"] - p["go"] for p in ph[:-1]) + (ph[-1]["last_row"] - ph[-1]["go"])
    drain = [p["idle"] - p["last_row"] for p in ph]
    fill = [p["last_row"] - p["go"] - p["t_pred"] for p in ph]
    return dict(phases=len(ph), rows=GROUP_ROWS, mac_bound_cycles=sum(p["t_pred"] for p in ph),
                bench_first_cfg_to_last_root=last_row - first_cfg, bench_first_go_to_last_root=last_row - first_go,
                bench_serial_cfg_write_cycles=cfg, cfg_hidden_go_to_last_root=hidden,
                per_phase_fill_beyond_rounds=dict(min=min(fill), max=max(fill), mean=round(sum(fill) / len(fill), 2)),
                per_phase_drain_to_idle=dict(min=min(drain), max=max(drain)),
                faults=sum(p["fault"] for p in ph), hung=sum(p["hung"] for p in ph))


def cmd_record(a):
    if a.output.exists():
        raise SystemExit("refuse to overwrite a verdict")
    nodes = node_params()
    lm, am, mg = nodes["head.lm_head"], nodes["head.argmax"], nodes["head.argmax_merge"]
    cyc = 1 / F_ELEM
    model_lm_us = lm["issue_us"] + lm["depth_us"] + lm["ctrl_us"]
    gold = json.loads((a.work / "golden.json").read_text())
    sch = {}
    for sched in ("packed", "native"):
        res = json.loads((a.work / f"lmhead_{sched}" / "result.json").read_text())
        z = np.load(a.work / f"lmhead_{sched}" / "rtl_roots.npz")
        g = np.load(a.work / "roots_rank0.npz")
        idx = z["rows"] - RANK * ROWS_RANK
        ra, rb = z["root4096"].astype(np.uint32), z["root1024"].astype(np.uint32)
        okA = int((ra == g["root4096"][idx].astype(np.uint32)).sum())
        okB = int((rb == g["root1024"][idx].astype(np.uint32)).sum())
        _, logits = golden_x()
        lg = G.bits(merge(G.from_bits(ra), G.from_bits(rb))).astype(np.uint32)
        okL = int((lg == G.bits(logits[z["rows"]]).astype(np.uint32)).sum())
        t = group_times(res)
        t.update(rows_range=[int(z["rows"].min()), int(z["rows"].max()) + 1], root4096_exact=okA, root1024_exact=okB,
                 merged_logits_exact_vs_golden=okL, exact=okA == okB == okL == GROUP_ROWS and res["rows_bad"] == 0
                 and not t["faults"] and not t["hung"],
                 rows_per_phase=SCHED[sched], words_per_logical_macro=res["words_per_logical_macro"])
        sch[sched] = t
    best = min(("packed", "native"), key=lambda k: sch[k]["cfg_hidden_go_to_last_root"])
    # wire stages the bench lacks (labelled): the model's broadcast/VM wire stages beyond the bench's own BST 2 and
    # RST 1 x log2(16) return levels, plus the model's return-tree levels above one group (cross-group, to the hub)
    bench_stages = 2 + 1 * int(math.log2(N))
    wire_add = dict(model_wire_cycles=lm["_uarch"]["wire"], bench_bst_rst_cycles=bench_stages,
                    added_wire_cycles=lm["_uarch"]["wire"] - bench_stages,
                    added_cross_group_tree_levels=lm["_uarch"]["tree"],
                    total_added_cycles=lm["_uarch"]["wire"] - bench_stages + lm["_uarch"]["tree"],
                    basis="model head.lm_head _uarch wire 36 (2 x broadcast wire + VM gather/scatter) and tree 4 "
                          "(fan-in 8 over the holding macros); not routed -- LABELLED ADDITIONS, not measured")
    scale = S81_GROUP_ROWS / GROUP_ROWS
    lmh = {}
    for k, t in sch.items():
        c = t["cfg_hidden_go_to_last_root"] * scale + wire_add["total_added_cycles"]
        lmh[k] = dict(cycles_measured_408_rows=t["cfg_hidden_go_to_last_root"],
                      cycles_scaled_to_S81_share_409p6_rows=round(c - wire_add["total_added_cycles"], 1),
                      cycles_with_added_wire=round(c, 1), us_1p2GHz=round(c * cyc * 1e6, 3),
                      bench_cycles_incl_serial_cfg=t["bench_first_cfg_to_last_root"],
                      bench_us_incl_serial_cfg=round((t["bench_first_cfg_to_last_root"] * scale
                                                      + wire_add["total_added_cycles"]) * cyc * 1e6, 3))
    term = json.loads((a.work / "argmax" / "result.json").read_text())
    tail = term["done"] - term["last_in"]
    thr = term["last_in"] - term["first_in"] + 1
    rec = dict(
        schema="opentallas.dsrom-1m-allmeasured.head.v1",
        status=("MEASURED_EXACT" if all(t["exact"] for t in sch.values()) and term["argmax_exact"]
                and term["logits_exact"] == ROWS_RANK else "FAIL"),
        token=dict(context=1048576, golden="ctx1048576_head.npz (xf [5120] final-norm x, logits [129280])",
                   next_token=gold["argmax_global"], rank0_argmax=gold["argmax_rank"]),
        lm_head=dict(
            node=dict(name="head.lm_head", model_us=round(model_lm_us, 3), model_issue_cycles=lm["issue_cyc_1p2"],
                      model_depth_cycles=lm["depth_cyc_1p2"], uarch=lm["_uarch"]),
            vehicle=("ONE return group of the S81 native BF head mapping: 16 logical macros = 8 element pairs "
                     "ot_v41_rom_elem_w10 FAST=1 PP=1 BP=2 NB=2 NCH=24 (2 BF16 multipliers a macro, a 16-weight word "
                     "held 8 cycles; 32 ROM4096 behavioural macros) behind the W10 return tree "
                     "(ot_v41_rom_array_w10_test BST 2, RST 1, RD 64, root 128), bench "
                     + TB_ARRAY + ". Full-shape row share: 408 rows (8,160 of 8,192 words a logical macro; S81 "
                     "storage 409.6 rows a group, 2,525 ROM4096 a rank = 78.9 groups, all equally loaded), each row "
                     "split K 0..4095 (phase A, root4096) + K 4096..5119 (phase B, root1024) as the S81 native "
                     "head; x = golden xf. Phases run back to back on one array (a spine never overlaps two ops)."),
            rows_checked=GROUP_ROWS, schedules=sch, timing=lmh, best_schedule=best,
            cycles=lmh[best]["cycles_with_added_wire"], us_1p2GHz=lmh[best]["us_1p2GHz"],
            model_us=round(model_lm_us, 3), measured_over_model=round(lmh[best]["us_1p2GHz"] / model_lm_us, 3),
            exact=all(t["exact"] for t in sch.values()),
            why_model_differs=("the model prices lm_head at the ROM read rate (t_read 7,360: one 16-weight word a "
                               "holding macro every 2 cycles, 1,448 holding macros); the head element as built "
                               "(BP=2, root option ii) multiplies 2 BF16 weights a cycle a macro, so a rank's 2,525 "
                               "ROM4096 (1,262.5 logical macros) sustain 2,525 MAC/cycle: 165,478,400 / 2,525 = "
                               "65,536 cycles MAC-bound before any phase overhead (CONS_BF16 option_ii extra cycles "
                               "are applied to wo_a/cmp.wk/router only, never to lm_head)"),
            wire_stages_added=wire_add,
            scaling="cycles x 409.6/408 (S81 group share) -- linear in rows at the measured per-row rate; LABELLED"),
        argmax=dict(
            node=dict(name="head.argmax", model_depth_cycles=am["depth_cyc_1p2"], model_us=round(am["depth_us"], 3)),
            vehicle=("S81 native ordered-root terminal rtl/test/s81_native_head_terminal/native_head_terminal.sv "
                     "(unchanged: root4096 + ((root1024 + 0) + 0) on three ot_hdc_fp32_add_fast, first-max lowest-id "
                     "comparator, 16 logit seats, rows strictly in order) on ALL 32,320 rows of rank 0 at the highest "
                     "rate it admits; bench " + TB_TERM + "; serial-chain domain 0.9 GHz"),
            rows=ROWS_RANK, rtl_roots_from_lm_head_bench=term["rtl_roots_from"],
            other_rows_roots="golden partial csum roots (bit-identical to the RTL's wherever both exist)",
            logits_exact=term["logits_exact"], best_row=term["best_row"], golden_argmax=term["golden_argmax"],
            exact=term["argmax_exact"] and term["logits_exact"] == ROWS_RANK,
            throughput_cycles_32320_rows=thr, rows_per_cycle=round(ROWS_RANK / thr, 4),
            cycles=tail, us_0p9GHz=round(tail / F_SERIAL * 1e6, 4),
            cycles_meaning="last root pair accepted -> argmax result (done) at 0.9 GHz: the tail after the lm_head's "
                           "last root reaches the terminal, IF the roots arrive in row order at <= 1 row a cycle",
            occupancy_us_0p9GHz=round(thr / F_SERIAL * 1e6, 3),
            order_constraint=("the terminal accepts rows only in order (in_row == rank*32320 + accepted). With rows "
                              "contiguous per group (as placed here and in the S81 pair storage, 51.2 rows a pair) "
                              "group g+1's rows wait for group g's last: the terminal then drains the other groups' "
                              f"{ROWS_RANK - GROUP_ROWS:,} rows after the sweep, "
                              f"+{(ROWS_RANK - GROUP_ROWS) / F_SERIAL * 1e6:.1f} us at 0.9 GHz. Interleaving rows "
                              "across groups by phase (not built) makes them arrive in order at "
                              f"{ROWS_RANK / lmh[best]['cycles_with_added_wire']:.2f} rows a 1.2 GHz cycle, under the "
                              f"terminal's {0.9 / 1.2:.2f}, so only the tail remains.")),
        argmax_merge=dict(
            node=dict(name="head.argmax_merge", op=mg["op"], span=mg["span"], payload_bytes_model=mg["payload"],
                      model_us=round(mg["depth_us"], 4)),
            bytes_per_die=8, bytes_total_all_gather=8 * RANKS,
            as_built_s81=dict(form="carried chain rank 0 -> 1 -> 2 -> 3 then final broadcast to the 4 cores "
                                   "(dsrom_s81_native_head_connect/join models)",
                              carried_record_bits=560, links=3, final_broadcast_bits=512 + 47, fanout=4),
            measured=False, note="the parent prices the collective; bytes only"),
        root_transport=dict(bytes_per_row=8, bytes_per_rank=8 * ROWS_RANK,
                            note="S81 storage die != arithmetic rank (global_pair round-robin over 12 head dies): "
                                 "the root pairs of a rank's rows cross dies to its terminal; link latency not "
                                 "measured here"),
        wavefront=dict(
            head_lm_occupancy_us_per_position=lmh[best]["us_1p2GHz"],
            head_terminal_occupancy_us_per_position=round(thr / F_SERIAL * 1e6, 3),
            head_stage_occupancy_us_per_position=round(max(lmh[best]["us_1p2GHz"], thr / F_SERIAL * 1e6), 3),
            basis="per position (one x vector): every group is busy the whole sweep (no phase overlap) and the rank "
                  "terminal is a 1-row/cycle serial resource; NV=1 (no L2 batching): the element is MAC-bound, so k positions "
                  "cost ~k x this (not measured beyond one position)"),
        unmeasured=[
            "routed wire / cross-group return-tree stages (model numbers added, labelled)",
            "configuration writes per phase: the bench writes them serially (bench_serial_cfg_write_cycles); the "
            "headline assumes them hidden (preloaded/double-buffered), which the element does not provide as built",
            "root transport from storage dies to the rank terminal and its 1.2 -> 0.9 GHz crossing",
            "argmax_merge collective (parent)",
            "SS/FF closure of the head element at NV=1 (dsrom_l2_head_mac: SS pre-layout WNS -117.8..-171 ps)"],
        simulator=f"verilator 5.050 ({gate.VERILATOR})",
        checkpoint_revision=SNAP.name, checkpoint_header_sha256=gold["checkpoint_header_sha256"],
        golden_sha256=sha(REF),
        source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                     text=True).stdout.strip(),
        source_sha256={p: sha(ROOT / p) for p in [*gate.RTL, *gate.RTL_FAST, TB_ARRAY, TB_TERM, *TERM,
                                                  "tools/dsrom_1m_head.py", "tools/w10_validation/rtl_v41_rom_array.py",
                                                  "tools/w10_validation/v41_rom_ksplit_bankmap.py",
                                                  "tools/hdc_golden_v41.py"]})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("status",)} | dict(lm_head_us=rec["lm_head"]["us_1p2GHz"],
                                                               model_us=rec["lm_head"]["model_us"],
                                                               argmax_tail=tail, term_occ=thr)))


def stream_model():
    """Minimum missing native writer hooks; no measured drain-removal credit."""
    import uarch_model as U
    hook = U.dsrom_s81_head_result_hook(128)
    per_rank = hook['native_declared_state_bits_per_rank'] + hook['adapter_state_bits_per_rank']
    return dict(
        status='SOURCE_MODEL_ONLY_NOT_SYSTEM_MEASUREMENT', opt_in_default=False,
        source='rtl/dsrom_sys/s81_native_head/ot_dsrom_s81_head_amax.sv',
        parameters=dict(R=128, AW=30, NW=21, ranks=[1, 2, 3]),
        existing_rank0='current core native masked-writer hook; retain it',
        architectural_replicas_already_priced=hook['replicas'],
        missing_implementation_replicas=3, extra_architectural_replicas=0,
        logical_state_bits_per_rank=per_rank,
        missing_implementation_state_bits=3 * per_rank,
        missing_implementation_FF_floor_mm2=3 * per_rank * U.DFF_UM2 / 1e6,
        architectural_state_debit='existing four-rank hook charge, reconcile once; do not add three again',
        input_ports_per_rank=hook['source_return_boundary_bits'] + 128 + 47 + 21 + 30 + 1,
        input_scope='128 native valid/accept lanes, address30/data32, owner47, nout21/base30/start',
        logit_bytes_per_edge_peak=512, actual_scalar_component_bytes_per_edge_peak=4,
        tracks_per_rank=hook['routing_tracks_required'],
        readiness='actual native_ready AND busy AND NOT fault, before same VM accepting edge',
        readiness_added_FF=0, readiness_logic_per_missing_rank=dict(AND2=2, INV=1),
        compiled_rank_output_bits=2,
        VM_valid_gate='four host VM wr_v bits held off while actual leaf cannot accept; no extra data seats',
        producer_buffer_added_bits=0,
        retained_buffer='existing NativeBfHeadRoots + held_join_bits/tag until native take AND positive VM ACK',
        local_tail_cycles_lower_bound=hook['native_last_writer_to_local_slice_cycles_lower_bound'],
        retained_measured_ordered_terminal_tail_cycles=12,
        conservative_source_tail_cycles=12 + hook['native_last_writer_to_local_slice_cycles_lower_bound'],
        source_tail_scope='retain12, add native writer-to-packet lower bound; VM acceptance/ACK and global transport remain explicit',
        removable_ordered_feed_us_upper_bound=(ROWS_RANK - GROUP_ROWS) / F_SERIAL * 1e6,
        drain_removal_credit_us=0,
        drain_scope='upper opportunity only; actual all-rank producer feed/collective measurement required',
        collective='existing DsromS81NativeHeadPorts/Collective; positive link/final delays, all four real ports',
        final_retirement='real final_ready then END/ReadResult; no local packet treated as global winner',
        clock='same shared native clock/reset; physical 1.2->0.9 CDC remains separately unqualified',
        comparator_mapped_area_mm2=None, ready_route_delay_ps=None,
        floorplan_slot_fit=None, SS_FF=False, headline_gain=None)


def cmd_stream_model(a):
    print(json.dumps(stream_model(), indent=1))


def cmd_stream_build(a):
    """Three missing wrappers only; never build a core or run a head."""
    if a.jobs < 1:
        raise SystemExit('stream-build jobs must be positive')
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / p for p in (
        'rtl/rom/collectives/ot_rom_coll_pkg.sv',
        'rtl/rom/collectives/ot_rom_coll_skid.sv',
        'rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv',
        'rtl/dsrom_sys/s81_native_head/ot_dsrom_s81_head_amax.sv',
        'rtl/test/s81_native_bf_head_producer/native_stream_amax.sv')]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    receipt = dict(status='BUILDING_COMPONENTS_ONLY', model=stream_model(),
                   source_sha256=pins, commands=[], archives={}, runtime=False,
                   source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   verilator_version=subprocess.check_output([str(gate.VERILATOR), '--version'], text=True).strip(),
                   compiler_version=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0])
    for rank in (1, 2, 3):
        prefix = f'VDsromHeadStreamR{rank}'
        obj = work / f'rank{rank}'
        cmd = [str(gate.VERILATOR), '--cc', '--build', '--build-jobs', str(a.jobs),
               '--verilate-jobs', '1', '-Wno-fatal', '-Wno-TIMESCALEMOD',
               '--top-module', 'DsromHeadStream', '--prefix', prefix,
               '--Mdir', str(obj), f'-GRANK={rank}', *map(str, sources)]
        receipt['commands'].append(cmd)
        with (work / f'rank{rank}.log').open('x') as log:
            process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        if process.returncode:
            receipt.update(status='FAIL_COMPONENT_BUILD', failed_rank=rank, exit_code=process.returncode)
            (work / 'native_stream_build.json').write_text(json.dumps(receipt, indent=1) + '\n')
            raise SystemExit(process.returncode)
        archive = obj / f'{prefix}__ALL.a'
        receipt['archives'][str(archive)] = sha(archive)
    if pins != {str(p.relative_to(ROOT)): sha(p) for p in sources}:
        receipt['status'] = 'FAIL_SOURCE_POSTCHECK'
    else:
        receipt['status'] = 'PASS_THREE_COMPONENT_ARCHIVES_ONLY'
    receipt['caller_scope'] = ('BIND_ONLY helper in retained_smoke.cpp consumes actual same-edge VM acceptance; '
                               'four-port collective/real END caller still must enroll these three archives')
    (work / 'native_stream_build.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps(receipt, indent=1))
    if receipt['status'].startswith('FAIL'):
        raise SystemExit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("golden", "lmhead", "argmax", "record", "stream-model", "stream-build", "bundle", "lever"):
        p = sp.add_parser(c)
        if c not in ("stream-model", "lever"):
            p.add_argument("--work", type=Path, required=True)
        if c == "lever":
            p.add_argument("--bundle", type=Path, required=True)
            p.add_argument("--route-a", required=True)
            p.add_argument("--route-b", required=True)
        if c == "lmhead":
            p.add_argument("--sched", choices=sorted(SCHED), required=True)
            p.add_argument("--build-only", action="store_true")
        if c in ("record", "lever"):
            p.add_argument("--output", type=Path, required=True)
        if c == 'stream-build':
            p.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args(argv)
    return dict(golden=cmd_golden, lmhead=cmd_lmhead, argmax=cmd_argmax, record=cmd_record, bundle=cmd_bundle,
                lever=cmd_lever, **{'stream-model': cmd_stream_model, 'stream-build': cmd_stream_build})[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
