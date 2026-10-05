#!/usr/bin/env python3
"""RTL campaign for the V4.1 hyper-connection projection engine (rtl/hdc/v41x/ot_hdc_v41x_hcp.sv).

Spec (docs/ARCH_SPEC_V41.md section 6 item 7; results/arch/arch_budget_v41.json required_spec.hc_macs):
2,048 FP32 MAC lanes; the 24-output projection over K = 20,480 terms within ~1,000 cycles of the residual,
and the same for the 6 positions of an MTP verify pass (24 x 20,480 x 6 / 2,048 = 1,440 cycles of lane work).

Every expected value is the golden's own: tools/hdc_golden_v41.Model.hc_mixes under R-ARITH "chunk8",
run (a) inside the reduced vehicle's forward pass (real residuals and real hc_attn/hc_ffn fn of several
layers, 6 consecutive positions layer-major as a verify pass does), and (b) on shipped-size random operands
(K = 20,480, fn [24, 20,480]) through the same method with a stand-in `self`.  The golden's matvec_c and
rsqrt are wrapped to record the raw csum and r it computed, so the expected mix is literally
mul(raw, r) from the golden's own call.

Benches (Verilator, rtl/test/tb_hdc_v41x_hcp.sv): the SPEC configuration W = 256 (2,048 lanes) and the
ROUTED tile W = 8 (64 lanes).  Each runs every case back to back, checks every result bit for bit and in
order, and reports per-case latency (command accept -> each position's last result).  A stalled-consumer
run checks flow control.  Mutations of the engine must be caught.  Writes
results/rtl/hdc_v41x_hcp_campaign.json.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

F = np.float32
OUT = ROOT / "results/rtl/hdc_v41x_hcp_campaign.json"
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_hcp.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_hcp.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
SOURCES = [RTL, ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/v41/ot_hdc_fdiv.sv",
           ROOT / "rtl/hdc/ot_hdc_delay.sv", ROOT / "rtl/hdc/ot_hdc_sfu.sv"]
DPI_SV = ROOT / "rtl/test/sim_hdc_v41x_fastfp_dpi.sv"
DPI_CPP = ROOT / "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py", Path(__file__)]
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
              "-Wno-TIMESCALEMOD")
VL_FLAGS = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
            "-Wno-TIMESCALEMOD")
ML = 2
SHIPPED_K = 4 * 5120
SHIPPED_EPS = 1e-6
SPEC = {"lanes": 2048, "latency_one_position_cycles": 1000, "mtp_positions": 6,
        "mtp_lane_work_cycles": 24 * SHIPPED_K * 6 // 2048}
# (W, TL, FP units): the spec engine (host-float stand-ins for the FP units: see DPI_SV), the routed tile
# with the real units, and the tile again with the stand-ins (must match the real units result for result)
CONFIGS = {"spec_w256": (256, 4, "dpi"), "mtp_m2_w512": (512, 3, "dpi"), "tile_w8": (8, 9, "rtl"),
           "tile_w8_dpi": (8, 9, "dpi")}
# The sublayer body the projection must fit (tools/arch_budget_v41.py, results/arch/arch_budget_v41.json
# mtp.speculation.200000): per hc op, rom_m1 verify busy 1,440 cycles of which 720 are ON the critical path
# (verify_path_us / 80 ops), so the body the side branch overlaps is 1,440 - 720 = 720 cycles; at m = 6 the
# path share is 0.  The budget's MTP design point is m = 2 (docs/ARCH_SPEC_V41.md section 7): 2 x 2,048 lanes.
HC_OPS_PER_TOKEN = 80
MUTATIONS = [
    ("tail passes a stored sibling through instead of adding it", "a(bitl ? slot : 32'd0)", "a(32'd0)"),
    ("last run stored instead of moved up", "wire go    = ev_v[gv] && (bitl || lastr);",
     "wire go    = ev_v[gv] && bitl;"),
    ("first-term flag one cycle late", ".a(fst[2][gg] ? 32'd0 : sum)", ".a(fst[3][gg] ? 32'd0 : sum)"),
    ("last run keeps every lane", "d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;",
     "d0[F_NV +: NVW] <= WNV;"),
    ("sum of squares weight is the ROM word", "(oss ? xw : ow[32*gl +: 32])", "ow[32*gl +: 32]"),
    ("Newton step uses +1.5 minus without the sign flip", "ab <= {~my[31], my[30:0]};", "ab <= my;"),
    ("run tree takes the right half twice", ".a(yl), .b(yr), .y(y), .err(e),", ".a(yr), .b(yr), .y(y), .err(e),"),
    ("CONTROL: tree operands swapped (addition commutes)", ".a(yl), .b(yr), .y(y), .err(e),",
     ".a(yr), .b(yl), .y(y), .err(e),"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bits(a) -> np.ndarray:
    return np.asarray(a, dtype=F).view(np.uint32)


# -- the golden, recorded ------------------------------------------------------------------------------
@contextlib.contextmanager
def recording():
    """Wrap the golden's matvec_c and rsqrt (as hc_mixes calls them) to record the raw csum and r."""
    rec = {}
    mv0, rs0 = G.matvec_c, G.rsqrt

    def mv(w, x, split, **kwargs):
        out = mv0(w, x, split, **kwargs)
        rec["raw"] = out
        return out

    def rs(v):
        out = rs0(v)
        rec["r"] = out
        return out

    G.matvec_c, G.rsqrt = mv, rs
    try:
        yield rec
    finally:
        G.matvec_c, G.rsqrt = mv0, rs0


class _Stand:
    """The attributes Model.hc_mixes reads, for shipped-size operands (no shipped checkpoint here)."""

    def __init__(self, fn, eps, hc=4):
        self.hc, self.eps, self.hc_eps, self.sinkhorn_iters = hc, F(eps), F(1e-6), 3
        self._w = {"fn": np.asarray(fn, dtype=F), "scale": np.ones(3, dtype=F), "base": np.zeros(fn.shape[0], F)}

    def lw(self, L, name):
        return self._w[name.rsplit("_", 1)[1]]


def golden_mixes(fn, x, eps):
    """(raw, r, mixes) of Model.hc_mixes on one position; x is [4, dim] BF16-valued."""
    assert G.ARITH == "chunk8"
    n = fn.shape[0]
    fp = np.zeros((max(n, 24), fn.shape[1]), dtype=F)       # hc_mixes slices 24 rows; extra rows are inert
    fp[:n] = fn
    with recording() as rec:
        G.Model.hc_mixes(_Stand(fp, eps, x.shape[0]), x, 0, "attn")
    return rec["raw"][:n], rec["r"], G.mul(rec["raw"][:n], rec["r"])


def real_cases(n_pairs=4, npos=6, seed=7):
    """Reduced vehicle: 6 consecutive positions of the prompt in one layer-major pass; per (layer, sublayer)
    the golden's fn and the 6 residuals, with the mixes the golden itself computed."""
    G.set_arith("chunk8")
    model = G.Model()
    prompt, _ = G.prompt_and_expected()
    caps = []
    orig = G.Model.hc_mixes

    def wrap(self, x, L, which):
        with recording() as rec:
            out = orig(self, x, L, which)
        caps.append({"L": L, "which": which, "x": x.copy(), "raw": rec["raw"], "r": rec["r"]})
        return out

    G.Model.hc_mixes = wrap
    try:
        state = model.new_state()
        model.forward_positions(prompt[:npos], 0, state)
    finally:
        G.Model.hc_mixes = orig
    rng = np.random.default_rng(seed)
    keys = sorted({(c["L"], c["which"]) for c in caps})
    pick = [keys[i] for i in sorted(rng.choice(len(keys), size=n_pairs, replace=False))]
    cases = []
    for L, which in pick:
        cs = [c for c in caps if c["L"] == L and c["which"] == which]
        assert len(cs) == npos
        fn = model.lw(L, f"hc_{which}_fn")
        xs = np.stack([c["x"].reshape(-1) for c in cs])
        mixes = np.stack([G.mul(c["raw"], c["r"]) for c in cs])
        # the stand-in reproduces the golden's own call (the shipped-size cases rely on it)
        for c, m in zip(cs, mixes):
            _, _, m2 = golden_mixes(fn, c["x"], model.eps)
            assert np.array_equal(bits(m2), bits(m)), (L, which)
        cases.append({"name": f"reduced L{L} hc_{which} x{npos}", "fn": fn, "x": xs, "scale": 1,
                      "eps": float(model.eps), "exp": mixes})
    # one single-position case
    c0 = caps[len(caps) // 2]
    fn = model.lw(c0["L"], f"hc_{c0['which']}_fn")
    cases.append({"name": f"reduced L{c0['L']} hc_{c0['which']} x1", "fn": fn, "x": c0["x"].reshape(1, -1),
                  "scale": 1, "eps": float(model.eps), "exp": G.mul(c0["raw"], c0["r"])[None, :]})
    stats = {"fn_std": float(np.std(np.concatenate([model.lw(L, f"hc_{w}_fn").reshape(-1) for L, w in keys]))),
             "x_std": float(np.std(np.concatenate([c["x"].reshape(-1) for c in caps])))}
    return cases, stats


def synth_case(name, rng, K, nout, npos, scale, kind, stats=None, eps=SHIPPED_EPS):
    """Shipped-size (or edge-size) random operands; expected from the golden's own method."""
    if kind == "typical":
        fn = (rng.standard_normal((nout, K)) * stats["fn_std"]).astype(F)
        x = G.to_bf16((rng.standard_normal((npos, K)) * stats["x_std"]).astype(F))
    elif kind == "wide":            # magnitudes over 2^-24 .. 2^24, mixed signs: heavy cancellation
        fn = (rng.choice([-1, 1], (nout, K)) * np.exp2(rng.uniform(-24, 24, (nout, K)))).astype(F)
        x = G.to_bf16((rng.choice([-1, 1], (npos, K)) * np.exp2(rng.uniform(-24, 24, (npos, K)))).astype(F))
    elif kind == "subnormal":       # products below 2^-126: gradual underflow in every lane
        fn = (rng.standard_normal((nout, K)) * 2.0 ** -70).astype(F)
        x = G.to_bf16((rng.standard_normal((npos, K)) * 2.0 ** -60).astype(F))
    else:
        raise ValueError(kind)
    xb = np.asarray(x, dtype=F)
    if scale:
        exp = np.stack([golden_mixes(fn, xb[p].reshape(4, -1) if K % 4 == 0 else xb[p][None, :], eps)[2]
                        for p in range(npos)])
    else:
        exp = np.stack([G.matvec_c(fn, xb[p], G.HC_SPLIT) for p in range(npos)])
    return {"name": name, "fn": fn, "x": xb, "scale": scale, "eps": eps, "exp": exp}


def order_sensitivity(case):
    """How many expected results the bench would see change if the engine summed in a different order
    (plain sequential, or chunk-8 sums added sequentially): the bench's power to see an order error."""
    fn, x = case["fn"], case["x"]
    xb = G.to_bf16(x)
    diff_seq = diff_chunkseq = n = 0
    for p in range(x.shape[0]):
        prod = G.mul(fn, xb[p][None, :])
        good = G.csum(prod)
        seq = np.zeros(fn.shape[0], F)
        for k in range(prod.shape[1]):
            seq = G.add(seq, prod[:, k])
        ch = G.csum(prod.reshape(fn.shape[0], -1, 8), axis=-1) if prod.shape[1] % 8 == 0 else None
        cs = np.zeros(fn.shape[0], F)
        if ch is not None:
            for k in range(ch.shape[1]):
                cs = G.add(cs, ch[:, k])
        diff_seq += int(np.sum(bits(seq) != bits(good)))
        diff_chunkseq += int(np.sum(bits(cs) != bits(good))) if ch is not None else 0
        n += fn.shape[0]
    return {"results": n, "differ_from_sequential": diff_seq, "differ_from_sequential_chunk_sums": diff_chunkseq}


# -- memory images ----------------------------------------------------------------------------------------
def images(cases, W):
    """Weight / x bank images in the engine's layout, commands and expected results."""
    wparts, xparts, cmds, exps = [], [], [], []
    wd = xd = 0
    for c in cases:
        fn, x = c["fn"], c["x"]
        nout, K = fn.shape
        npos = x.shape[0]
        assert K % 8 == 0
        nchunk = K // 8
        R = -(-nchunk // W)
        # padding past K holds junk (finite, nonzero): the engine must mask the last run's idle lanes
        junk = np.random.default_rng(K + nout + npos)
        fp = junk.uniform(1, 2, (nout, R * W * 8)).astype(F)
        fp[:, :K] = fn
        xp = G.to_bf16(junk.uniform(1, 2, (npos, R * W * 8)).astype(F))
        xp[:, :K] = x
        wparts.append(bits(fp).reshape(nout, R, W, 8).transpose(3, 0, 1, 2).reshape(8, nout * R, W))
        xparts.append((bits(xp) >> 16).astype(np.uint16).reshape(npos, R, W, 8).transpose(3, 0, 1, 2)
                      .reshape(8, npos * R, W))
        cmds.append([npos, nout, nchunk, c["scale"], int(bits(F(K))), int(bits(F(c["eps"]))), wd, xd])
        wd += nout * R
        xd += npos * R
        for p in range(npos):
            for o in range(nout):
                exps.append((p << 40) | (o << 32) | int(bits(c["exp"][p, o])))
    assert wd < (1 << 16) and xd < (1 << 16), (wd, xd)
    return np.concatenate(wparts, axis=1), np.concatenate(xparts, axis=1), cmds, exps


def write_vectors(d: Path, cases, W):
    wm, xm, cmds, exps = images(cases, W)
    d.mkdir(parents=True, exist_ok=True)
    (d / "hcp_meta.mem").write_text("\n".join(f"{v:08x}" for v in (len(cmds), wm.shape[1], xm.shape[1],
                                                                    len(exps))) + "\n")
    (d / "hcp_cmd.mem").write_text("\n".join(f"{v:08x}" for c in cmds for v in c) + "\n")
    np.savetxt(d / "hcp_w.mem", wm.reshape(-1), fmt="%08x")
    np.savetxt(d / "hcp_x.mem", xm.reshape(-1), fmt="%04x")
    (d / "hcp_exp.mem").write_text("\n".join(f"{v:012x}" for v in exps) + "\n")
    return {"weight_words": int(wm.shape[1]), "x_words": int(xm.shape[1]), "results": len(exps)}


# -- Verilator ---------------------------------------------------------------------------------------------
def fp_sources(sources, fp):
    """The engine's sources with the FP units from the RTL or from the simulation stand-ins."""
    if fp == "rtl":
        return list(sources)
    return [p for p in sources if p.name != "ot_hdc_fastfp.sv"] + [DPI_SV, DPI_CPP]


def build(obj: Path, W, TL, sources, vec, jobs=8):
    maxw = 1 << max(10, math.ceil(math.log2(8 * W * vec["weight_words"])))
    maxx = 1 << max(10, math.ceil(math.log2(8 * W * vec["x_words"])))
    cmd = ["verilator", *VL_FLAGS, "--top-module", "tb_hdc_v41x_hcp", "-Mdir", str(obj),
           f"-GW={W}", f"-GTL={TL}", f"-GML={ML}", f"-GMAXW={maxw}", f"-GMAXX={maxx}",
           "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_hcp", "-CFLAGS", "-O1", "--output-split", "20000",
           "--x-assign", "unique", "--x-initial", "unique", "-j", str(jobs),
           *map(str, sources), str(TB), str(HARNESS)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return obj / "Vtb_hdc_v41x_hcp"


RE_CASE = re.compile(r"CASE (\d+) npos=(\d+) nout=(\d+) nchunk=(\d+) scale=(\d+) errors=(\d+) first=(\d+) "
                     r"last=(\d+) pos_last=([\d,]*)")
RE_SUM = re.compile(r"HCP W=(\d+) lanes=(\d+) cases=(\d+) results=(\d+) errors=(\d+) faults=(\d+) order=(\d+) "
                    r"cycles=(\d+)")


def simulate(exe: Path, d: Path, stall=0, seed=1):
    p = subprocess.run([str(exe), f"+STALL={stall}", f"+SEED={seed}", f"+verilator+seed+{seed}",
                        "+verilator+rand+reset+2"], cwd=d, capture_output=True, text=True, timeout=36000)
    m = RE_SUM.search(p.stdout)
    cases = [{"case": int(a), "npos": int(b), "nout": int(c), "nchunk": int(e), "scale": int(f), "errors": int(g),
              "first_result_cycles": int(h), "last_result_cycles": int(i),
              "position_last_cycles": [int(v) for v in j.strip(",").split(",") if v]}
             for a, b, c, e, f, g, h, i, j in RE_CASE.findall(p.stdout)]
    if not m:
        return {"pass": False, "stdout_tail": p.stdout[-2000:], "stderr_tail": p.stderr[-2000:], "cases": cases}
    W, lanes, nc, res, err, flt, order, cyc = map(int, m.groups())
    mism = [ln for ln in p.stdout.splitlines() if ln.startswith("MISMATCH")][:5]
    return {"pass": err == 0 and flt == 0 and order == 0 and len(cases) == nc, "lanes": lanes, "cases_run": nc,
            "results_compared": res, "mismatches": err, "faults": flt, "order_errors": order,
            "total_cycles": cyc, "cases": cases, "first_mismatches": mism}


def expected_cycles(npos, nout, nchunk, W, scale):
    """Issue-bound task count: one 8W-term task per cycle."""
    R = -(-nchunk // W)
    return npos * (nout + (1 if scale else 0)) * R


def mutate(src: Path, dst: Path, old, new):
    s = src.read_text()
    assert s.count(old) == 1, old
    dst.write_text(s.replace(old, new))


def run(quick=False, configs=None, scratch=None) -> dict:
    G.set_arith("chunk8")
    rng = np.random.default_rng(20260926)
    real, stats = real_cases()
    K = SHIPPED_K
    shipped = [synth_case("shipped typical x1", rng, K, 24, 1, 1, "typical", stats),
               synth_case("shipped typical x6 (MTP verify)", rng, K, 24, 6, 1, "typical", stats),
               synth_case("shipped wide-range raw x2", rng, K, 24, 2, 0, "wide"),
               synth_case("shipped subnormal raw x1", rng, K, 24, 1, 0, "subnormal")]
    edges = [synth_case("K=8 nout=1 x1", rng, 8, 1, 1, 1, "typical", stats),
             synth_case("K=24 nout=5 x3", rng, 24, 5, 3, 1, "typical", stats),
             synth_case("K=8(W+1) wide raw x1 (last run of one chunk)", rng, 8 * 257, 3, 1, 0, "wide"),
             synth_case("K=8(8+1) wide raw x2", rng, 8 * 9, 24, 2, 0, "wide")]
    cases = real + shipped + edges
    if quick:
        cases = real[:1] + edges
    sens = {c["name"]: order_sensitivity(c) for c in cases}
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_v41x_hcp", "-GW=8",
                           "-GTL=9", *map(str, SOURCES)], capture_output=True, text=True)
    configs = configs or (["tile_w8"] if quick else list(CONFIGS))
    benches, muts = {}, []
    base = Path(scratch) if scratch else Path(tempfile.mkdtemp(prefix="hcp_"))
    for cname in configs:
        W, TL, fp = CONFIGS[cname]
        d = base / cname
        vec = write_vectors(d, cases, W)
        exe = build(d / "obj", W, TL, fp_sources(SOURCES, fp), vec, jobs=16 if W > 64 else 4)
        res = simulate(exe, d)
        stalled = simulate(exe, d, stall=40, seed=3) if not quick else None
        for c, cc in zip(res.get("cases", []), cases):
            c["name"] = cc["name"]
            c["issue_bound_cycles"] = expected_cycles(c["npos"], c["nout"], c["nchunk"], W, c["scale"])
            c["depth_cycles"] = c["last_result_cycles"] - c["issue_bound_cycles"]
        benches[cname] = {"W": W, "TL": TL, "lanes": 8 * W, "fp_units": fp, "memory_latency": ML, "vectors": vec,
                          "run": res, "stalled_consumer_40pct": stalled}
        print(cname, "pass" if res.get("pass") else "FAIL", res.get("mismatches"), res.get("total_cycles"),
              flush=True)
        if cname == "tile_w8" and not quick:
            mcases = real[:2] + edges
            md = base / "mut"
            mvec = write_vectors(md, mcases, W)
            for name, old, new in MUTATIONS:
                control = name.startswith("CONTROL")
                mdir = base / f"mut_{len(muts)}"
                mdir.mkdir(parents=True, exist_ok=True)
                msrc = mdir / RTL.name
                mutate(RTL, msrc, old, new)
                try:
                    mexe = build(mdir / "obj", W, TL, fp_sources([msrc, *SOURCES[1:]], "dpi"), mvec, jobs=4)
                    r = simulate(mexe, md)
                    caught = not r.get("pass")
                except subprocess.CalledProcessError as e:
                    caught, r = True, {"build_error": (e.stderr or "")[-500:]}
                muts.append({"mutation": name, "control": control, "caught": caught,
                             "mismatches": r.get("mismatches"), "faults": r.get("faults")})
                print("mutation", name, "caught" if caught else "MISSED", flush=True)
    spec_rec = spec_check(benches)
    stand_in = None
    if "tile_w8" in benches and "tile_w8_dpi" in benches:
        a, b = benches["tile_w8"]["run"], benches["tile_w8_dpi"]["run"]
        same = [(x["errors"], x["last_result_cycles"], x["position_last_cycles"]) ==
                (y["errors"], y["last_result_cycles"], y["position_last_cycles"])
                for x, y in zip(a.get("cases", []), b.get("cases", []))]
        stand_in = {"cases": len(same), "identical_results_and_cycles": all(same) and len(same) > 0,
                    "note": "the tile with the real ot_hdc_fastfp units and with the host-float stand-ins, same "
                            "vectors: both bit-exact against the golden, every per-position cycle equal"}
        benches["tile_w8_dpi"]["matches_rtl_units"] = stand_in
    ok = (lint.returncode == 0 and all(b["run"].get("pass") for b in benches.values())
          and all((b["stalled_consumer_40pct"] or {"pass": True}).get("pass") for b in benches.values())
          and all(m["caught"] != m["control"] for m in muts)
          and (stand_in is None or stand_in["identical_results_and_cycles"]))
    return {
        "schema": "opentallas.hdc-v41x-hcp-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "cycle-level Verilator simulation of ot_hdc_v41x_hcp with behavioural weight/x banks "
                          "(fixed read latency) against tools/hdc_golden_v41.Model.hc_mixes under R-ARITH chunk8; "
                          "the shipped-size fn is random (no shipped checkpoint in this repository), the reduced "
                          "vehicle's fn and residuals are real.  Clock and area: results/physical_abi3/asap7/hdc/"
                          "v41x/ot_hdc_v41x_hcp*/physical.json.",
        "arith": "chunk8",
        "spec": SPEC,
        "spec_check": spec_rec,
        "cases": [{"name": c["name"], "K": int(c["fn"].shape[1]), "nout": int(c["fn"].shape[0]),
                   "npos": int(c["x"].shape[0]), "scale": c["scale"]} for c in cases],
        "reduced_operand_stats": stats,
        "order_sensitivity": sens,
        "benches": benches,
        "mutations": muts,
        "verilator_lint": {"flags": list(LINT_FLAGS), "returncode": lint.returncode,
                           "messages": lint.stderr.strip().splitlines()[:10]},
        "fp_stand_in": stand_in,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*SOURCES, DPI_SV, DPI_CPP, TB, HARNESS, *TOOLS)},
    }


def body_cycles():
    """The sublayer body an hc op overlaps under a 6-position verify pass, from the committed budget."""
    bud = json.loads(BUDGET.read_text())
    clock = bud["clock_hz"]
    m1 = bud["mtp"]["speculation"]["200000"]["rom_m1"]["classes"]["hc_projection"]
    busy = m1["verify_busy_us"] / HC_OPS_PER_TOKEN * 1e-6 * clock
    path = m1["verify_path_us"] / HC_OPS_PER_TOKEN * 1e-6 * clock
    return {"verify_busy_cycles_m1": round(busy, 1), "verify_on_path_cycles_m1": round(path, 1),
            "body_cycles": round(busy - path, 1), "clock_hz": clock,
            "source": "results/arch/arch_budget_v41.json mtp.speculation.200000.rom_m1.classes.hc_projection "
                      "(per op: / 80 hc ops per token)"}


def spec_check(benches):
    b = benches.get("spec_w256")
    if not b or not b["run"].get("cases"):
        return None
    body = body_cycles()
    cs = {c["name"]: c for c in b["run"]["cases"] if "name" in c}
    one = cs.get("shipped typical x1")
    six = cs.get("shipped typical x6 (MTP verify)")
    out = {"lanes": {"spec": SPEC["lanes"], "measured": b["lanes"], "met": b["lanes"] >= SPEC["lanes"]},
           "sublayer_body": body}
    if one:
        out["one_position_latency_cycles"] = {
            "spec": SPEC["latency_one_position_cycles"], "measured": one["last_result_cycles"],
            "met": one["last_result_cycles"] <= SPEC["latency_one_position_cycles"],
            "issue_bound": one["issue_bound_cycles"], "depth": one["depth_cycles"]}
    if six:
        lane_cycles = 24 * SHIPPED_K * 6 // (8 * b["W"])
        out["six_positions_2048_lanes"] = {
            "spec_lane_work": SPEC["mtp_lane_work_cycles"], "measured": six["last_result_cycles"],
            "position_last_cycles": six["position_last_cycles"], "fn_lane_cycles": lane_cycles,
            "sum_of_squares_task_cycles": six["issue_bound_cycles"] - lane_cycles, "depth": six["depth_cycles"],
            "lane_utilisation_during_issue": 1.0,
            "fits_body": six["last_result_cycles"] <= body["body_cycles"],
            "note": "2,048 lanes do 1,440 cycles of lane work for 6 positions: twice the body, which is why the "
                    "budget itself puts hc_projection on the critical path at m = 1 (rom_m1 verify_path_us > 0)"}
    b2 = benches.get("mtp_m2_w512")
    if b2 and b2["run"].get("cases"):
        c2 = {c["name"]: c for c in b2["run"]["cases"] if "name" in c}.get("shipped typical x6 (MTP verify)")
        if c2:
            out["six_positions_m2_4096_lanes"] = {
                "lanes": b2["lanes"], "measured": c2["last_result_cycles"], "issue_bound": c2["issue_bound_cycles"],
                "depth": c2["depth_cycles"], "position_last_cycles": c2["position_last_cycles"],
                "body_cycles": body["body_cycles"], "fits_body": c2["last_result_cycles"] <= body["body_cycles"],
                "note": "the MTP design point m = 2 as 8 x 512 lanes (weights read at twice the rate; an m-way "
                        "multiplier sharing one weight read has the same lane count and cycle count)"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--config", action="append", choices=list(CONFIGS))
    ap.add_argument("--scratch", type=Path)
    args = ap.parse_args()
    rec = run(args.quick, args.config, args.scratch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
