#!/usr/bin/env python3
"""DS-ROM recovery lever "router_act" (SU chains): the router's sqrt(softplus) on parallel lanes at the router
field's output root in the 1.2 GHz domain (rtl/hdc/v41x/ot_dsrom_su_spsqrt.sv) and `scores + bias` folded into the
front of the adopted parallel top-6 (rtl/hdc/v41x/ot_dsrom_su_bias_select.sv), measured at the 1M token.

    python3 tools/dsrom_su_routeract.py operands --out <dir>/router_operands_1m.npz --gold <dir of ctx1048576_LXX>
        # (host with the released checkpoint) raw router outputs mv(gate.weight, ffn_norm) of all 40 layers,
        # checked: add(sqrt(softplus(raw)), bias) == the golden's recorded biased router scores, bit for bit
    python3 tools/dsrom_su_routeract.py sim --operands <npz> --work <dir> --out <sim.json>
    python3 tools/dsrom_su_routeract.py lever --sim <sim.json> --screen-sp <json> --screen-bias <json> [--route <json>]
        --out results/rtl/dsrom_recovery_20261004/levers/su_routeract.json

sim (Verilator 5.050; every run must PASS):
  * ot_dsrom_su_spsqrt (LANES 24, IN 2 / OUT 2 wire stages) IMPL 0 (ot_hdc_v41x_softplus LM 5 / LA 4 under the
    1.2 GHz FILE SWAP rtl/hdc/ot_hdc_fastfp_lat_f12.sv) and IMPL 1 (ot_hdc_v41x_softplus_s PCUT 1): every layer's
    384 rows (4 dies x 96 = 4 beats a die), the golden's scores bit for bit; one die's 4 beats alone for the cycle
    record; random stress (finite inputs over the whole range, edge values) against tools/hdc_golden_v41
    sqrt(softplus(x)), back to back and with bubbles.
  * ot_dsrom_su_bias_select (W 64, NB 8, K 6, ORDER 1, LA 4): every layer's 384 unbiased scores + the gate bias, the
    selection must equal topk_lowest_index(add(scores, bias)) and the golden's recorded experts; random segments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

F = np.float32
CTX = 1048576
TP, ROWS = 4, 96
LANES = 24
FAST_HZ, SLOW_HZ = 1.2e9, 0.9e9
IN_ST, OUT_ST = 2, 2
SP_RTL = ROOT / "rtl/hdc/v41x/ot_dsrom_su_spsqrt.sv"
SP_TB = ROOT / "rtl/test/tb_dsrom_su_spsqrt.sv"
SP_H = ROOT / "rtl/test/dsrom_su_spsqrt_harness.cpp"
BS_RTL = ROOT / "rtl/hdc/v41x/ot_dsrom_su_bias_select.sv"
BS_TB = ROOT / "rtl/test/tb_dsrom_su_bias_select.sv"
BS_H = ROOT / "rtl/test/dsrom_su_bias_select_harness.cpp"
SEL = ROOT / "rtl/hdc/v41/ot_hdc_select_tree.sv"
LIB = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
    "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
    "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41x/ot_hdc_v41x_spshort.sv")]
LINE_SP = re.compile(r"SPSQRT LANES=(\d+) IMPL=(\d+) beats_in=(\d+) beats_out=(\d+) errors=(\d+) faults=(\d+) "
                     r"lat_min=(-?\d+) lat_max=(-?\d+) span0=(-?\d+) cycles=(\d+)")
LINE_BS = re.compile(r"SELTREE K=(\d+) VW=(\d+) IW=(\d+) W=(\d+) NB=(\d+) ORDER=(\d+) segments=(\d+) beats=(\d+) "
                     r"results=(\d+) errors=(\d+) lat_min=(-?\d+) lat_max=(-?\d+) lat_expect=(\d+) span0=(-?\d+) "
                     r"cycles=(\d+)")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def git_head():
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def u32(x):
    return np.asarray(x, F).view(np.uint32)


# ---------------------------------------------------------------------------------------------------------------------
def cmd_operands(a):
    import rtl_v41_fullshape_layer_campaign as LC
    gold = Path(a.gold)
    ck = LC.Checkpoint()

    def tensor(name):
        b, dt, shape = ck.raw(name)
        if dt == "F32":
            return np.frombuffer(bytes(b), dtype=np.float32).reshape(shape).copy()
        if dt == "BF16":
            return V.from_bits(np.frombuffer(bytes(b), dtype=np.uint16).astype(np.uint32) << 16).reshape(shape)
        raise SystemExit(f"{name}: {dt}")
    out, rows = {}, []
    for L in range(40):
        z = np.load(gold / f"ctx{CTX}_L{L:02d}.npz")
        js = json.loads((gold / f"ctx{CTX}_L{L:02d}.json").read_text())
        raw = V.mv(tensor(f"layers.{L}.ffn.gate.weight"), z[f"L{L}.ffn_norm"]).astype(F)
        bias = tensor(f"layers.{L}.ffn.gate.bias").astype(F)
        sc = V.sqrt(V.softplus(raw))
        ok = bool(np.array_equal(u32(V.add(sc, bias)), u32(z[f"L{L}.router"])))
        ids = sorted(int(i) for i in V.topk_lowest_index(V.add(sc, bias), 6))
        assert ok and ids == js["experts"], L
        out.update({f"raw{L}": raw, f"bias{L}": bias, f"scores{L}": sc, f"experts{L}": np.asarray(ids)})
        rows.append(dict(layer=L, npz_sha256=sha(gold / f"ctx{CTX}_L{L:02d}.npz"), biased_bit_exact=ok))
    np.savez(a.out, **out)
    Path(str(a.out) + ".json").write_text(json.dumps(dict(context=CTX, position=CTX - 1, layers=rows,
                                                          npz_sha256=sha(a.out)), indent=1) + "\n")
    print("OPERANDS", a.out, sha(a.out))
    return 0


# ---------------------------------------------------------------------------------------------------------------------
def stress_inputs(rng, n):
    """Finite binary32 inputs over the whole range, weighted to softplus's interesting region."""
    parts = [np.asarray([0.0, -0.0, 1e-45, -1e-45, 1.17549435e-38, -1.17549435e-38, 87.0, -87.0, 88.0, -88.0,
                         88.7, -88.7, 100.0, -100.0, 3.4028235e38, -3.4028235e38, 1.0, -1.0, 2.0, -2.0], F)]
    parts.append(rng.uniform(-30, 30, n // 2).astype(F))
    parts.append(rng.uniform(-100, 100, n // 8).astype(F))
    b = rng.integers(0, 1 << 32, n - n // 2 - n // 8, dtype=np.uint64).astype(np.uint32)
    e = (b >> 23) & 0xFF
    b = np.where(e == 0xFF, b & np.uint32(0xBF7FFFFF), b)          # no inf / NaN
    parts.append(b.view(F))
    x = np.concatenate(parts)
    return x[: len(x) - len(x) % LANES] if len(x) % LANES else x


def write_words(path, words):
    path.write_text("".join(f"{int(w):08x}\n" for w in np.asarray(words, np.uint32)))


def build(verilator, obj, top, srcs, params):
    exe = obj / f"V{top}"
    if not exe.exists():
        subprocess.run([verilator, "--cc", "--exe", "--build", "-j", "16", "-O2", "-Wno-fatal", "--top-module", top,
                        *[f"-G{k}={v}" for k, v in params.items()], "-Mdir", str(obj), *map(str, srcs),
                        "-CFLAGS", "-O1"], check=True, capture_output=True)
    return exe


def run_sp(exe, fin, fexp, seg, bubble=0, seed=1):
    out = subprocess.run([str(exe), f"+IN={fin}", f"+EXP={fexp}", f"+SEG={seg}", f"+BUBBLE={bubble}",
                          f"+SEED={seed}"], capture_output=True, text=True).stdout
    m = LINE_SP.search(out)
    if not m:
        return dict(**{"pass": False}, raw=out[-1500:])
    k = ("LANES", "IMPL", "beats_in", "beats_out", "errors", "faults", "lat_min", "lat_max", "span0", "cycles")
    r = {x: int(v) for x, v in zip(k, m.groups())}
    r["pass"] = "PASS" in out[m.end():]
    if not r["pass"]:
        r["raw"] = out[-1500:]
    return r


def bs_vectors(segs, fin, fexp):
    """segs: (scores, bias, labels) of <= 512 elements, 64 lanes a beat in label order."""
    import rtl_hdc_v41_select_campaign as SC
    li, le = [], []
    for sc, bias, labels in segs:
        n = len(sc)
        beats = -(-n // 64)
        for b in range(beats):
            li.append(f"B {int(b == beats - 1)}\n")
            for l in range(64):
                i = b * 64 + l
                if i < n:
                    li.append(f"{int(u32(sc[i])):x} {int(labels[i]):x} 1 {int(u32(bias[i])):x}\n")
                else:
                    li.append("0 0 0 0\n")
        biased = V.add(np.asarray(sc, F), np.asarray(bias, F)).astype(np.float64)
        exp = SC.expected(biased, labels, 6, 1)
        le.append(f"S {len(exp)}\n")
        le += [f"{i:x} {int(nf)}\n" for i, nf in exp]
    fin.write_text("".join(li))
    fexp.write_text("".join(le))
    return hashlib.sha256(fin.read_bytes() + fexp.read_bytes()).hexdigest()


def run_bs(exe, fin, fexp, bubble=0, seed=1):
    out = subprocess.run([str(exe), f"+IN={fin}", f"+EXP={fexp}", f"+BUBBLE={bubble}", f"+SEED={seed}"],
                         capture_output=True, text=True).stdout
    m = LINE_BS.search(out)
    if not m:
        return dict(**{"pass": False}, raw=out[-1500:])
    k = ("K", "VW", "IW", "W", "NB", "ORDER", "segments", "beats", "results", "errors", "lat_min", "lat_max",
         "lat_expect", "span0", "cycles")
    r = {x: int(v) for x, v in zip(k, m.groups())}
    r["pass"] = "PASS" in out[m.end():]
    if not r["pass"]:
        r["raw"] = out[-1500:]
    return r


def cmd_sim(a):
    import rtl_hdc_v41_select_campaign as SC
    ops = np.load(a.operands)
    work, out = Path(a.work), Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    verilator = str(vl) if vl.exists() else "verilator"
    impls = [int(x) for x in a.impls.split(",")]
    res = dict(schema="opentallas.dsrom-recovery.su-routeract-sim.v1", generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               source_commit=os.environ.get("SOURCE_COMMIT") or git_head(), context=CTX, position=CTX - 1,
               operands=dict(file=Path(a.operands).name, sha256=sha(a.operands)), spsqrt={}, bias_select={})
    # ---- sqrt(softplus)
    xs, ws = [], []
    for L in range(40):
        raw, sc = ops[f"raw{L}"], ops[f"scores{L}"]
        assert np.array_equal(u32(V.sqrt(V.softplus(raw))), u32(sc))
        xs.append(raw)
        ws.append(sc)
    write_words(work / "real.in", np.concatenate([u32(x) for x in xs]))
    write_words(work / "real.exp", np.concatenate([u32(w) for w in ws]))
    write_words(work / "die.in", u32(xs[20][:ROWS]))
    write_words(work / "die.exp", u32(ws[20][:ROWS]))
    rng = np.random.default_rng(20261004)
    sx = stress_inputs(rng, a.stress)
    sw = V.sqrt(V.softplus(sx))
    write_words(work / "stress.in", u32(sx))
    write_words(work / "stress.exp", u32(sw))
    for impl in impls:
        obj = work / f"obj_sp_i{impl}"
        exe = build(verilator, obj, "tb_dsrom_su_spsqrt", LIB + [SP_RTL, SP_TB, SP_H],
                    dict(LANES=LANES, IMPL=impl, IN_STAGES=IN_ST, OUT_STAGES=OUT_ST))
        seg = ROWS // LANES
        runs = dict(
            die_L20=run_sp(exe, work / "die.in", work / "die.exp", seg),
            all_layers_all_dies=run_sp(exe, work / "real.in", work / "real.exp", seg),
            all_layers_bubbles30=run_sp(exe, work / "real.in", work / "real.exp", seg, 30, 7),
            stress=run_sp(exe, work / "stress.in", work / "stress.exp", seg),
            stress_bubbles30=run_sp(exe, work / "stress.in", work / "stress.exp", seg, 30, 3))
        for k, r in runs.items():
            print("SP", impl, k, {x: r.get(x) for x in ("pass", "errors", "faults", "lat_max", "span0", "beats_in")},
                  flush=True)
        res["spsqrt"][f"impl{impl}"] = dict(
            module="ot_dsrom_su_spsqrt", params=dict(LANES=LANES, IMPL=impl, IN_STAGES=IN_ST, OUT_STAGES=OUT_ST),
            lane=("ot_hdc_v41x_softplus #(LM 5, LA 4) on the f12 units" if impl == 0 else
                  "ot_hdc_v41x_softplus_s #(PCUT 1)"),
            die_rows=ROWS, beats_a_die=seg, cycles_die=runs["die_L20"].get("span0"),
            latency=runs["die_L20"].get("lat_max"), stress_inputs=int(len(sx)),
            layers=40, rows_checked=40 * 384, runs=runs,
            status="pass" if all(r.get("pass") for r in runs.values()) else "fail")
    # ---- bias + select tree
    obj = work / "obj_bs"
    exe = build(verilator, obj, "tb_dsrom_su_bias_select", LIB + [SEL, BS_RTL, BS_TB, BS_H],
                dict(K=6, VW=32, IW=9, W=64, NB=8, ORDER=1, LA=4))
    layers, all_segs = [], []
    for L in range(40):
        sc, bias = ops[f"scores{L}"], ops[f"bias{L}"]
        ids = sorted(int(i) for i in V.topk_lowest_index(V.add(sc, bias), 6))
        assert ids == [int(i) for i in ops[f"experts{L}"]]
        seg = (sc, bias, np.arange(384))
        all_segs.append(seg)
        h = bs_vectors([seg], work / f"bs_L{L:02d}.in", work / f"bs_L{L:02d}.exp")
        r = run_bs(exe, work / f"bs_L{L:02d}.in", work / f"bs_L{L:02d}.exp")
        layers.append(dict(layer=L, experts=ids, vectors_sha256=h, first_accept_to_result_cycles=r.get("span0"),
                           latency=r.get("lat_max"), errors=r.get("errors"), **{"pass": r.get("pass")}))
    runs = {}
    bs_vectors(all_segs, work / "bs_all.in", work / "bs_all.exp")
    runs["all_layers_back_to_back"] = run_bs(exe, work / "bs_all.in", work / "bs_all.exp")
    runs["all_layers_bubbles30"] = run_bs(exe, work / "bs_all.in", work / "bs_all.exp", 30, 7)
    rs = []
    for _ in range(a.random):
        n = int(rng.integers(1, 513))
        v = SC.random_values(rng, n, 32)
        v = np.where(np.isfinite(v), v, 0.0)
        b = np.where(np.abs(v) < 1e30, rng.choice([0.0, 0.5, -0.5, 1e-3, -1e-3], n) if rng.random() < 0.5 else
                     rng.uniform(-8, 8, n), 0.0)
        rs.append((v.astype(F), b.astype(F), rng.choice(512, n, replace=False) if rng.random() < 0.5 else np.arange(n)))
    h = bs_vectors(rs, work / "bs_rnd.in", work / "bs_rnd.exp")
    runs["random"] = dict(vectors_sha256=h, **run_bs(exe, work / "bs_rnd.in", work / "bs_rnd.exp"))
    runs["random_bubbles30"] = run_bs(exe, work / "bs_rnd.in", work / "bs_rnd.exp", 30, 3)
    for k, r in runs.items():
        print("BS", k, {x: r.get(x) for x in ("pass", "errors", "lat_max", "segments")}, flush=True)
    cyc = sorted({x["first_accept_to_result_cycles"] for x in layers})
    res["bias_select"] = dict(module="ot_dsrom_su_bias_select", params=dict(K=6, VW=32, IW=9, W=64, NB=8, ORDER=1, LA=4),
                              cycles=cyc, layers=layers, runs=runs, random_segments=a.random,
                              status="pass" if all(x["pass"] for x in layers) and all(r.get("pass") for r in runs.values())
                              else "fail")
    res["simulator"] = subprocess.run([verilator, "--version"], capture_output=True, text=True).stdout.strip()
    res["source_sha256"] = {rel(p): sha(p) for p in [SP_RTL, SP_TB, SP_H, BS_RTL, BS_TB, BS_H, SEL, *LIB,
                                                      ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py",
                                                      Path(__file__)]}
    res["status"] = "pass" if all(v["status"] == "pass" for v in res["spsqrt"].values()) and \
        res["bias_select"]["status"] == "pass" else "fail"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print("SIM", res["status"])
    return 0 if res["status"] == "pass" else 1


# ---------------------------------------------------------------------------------------------------------------------
def cmd_lever(a):
    sim = json.loads(Path(a.sim).read_text())
    ssp = json.loads(Path(a.screen_sp).read_text())
    sbs = json.loads(Path(a.screen_bias).read_text())
    route = json.loads(Path(a.route).read_text()) if a.route else None
    comp = json.loads((ROOT / "results/rtl/dsrom_recovery_20261004/composition.json").read_text())
    path = {p["node"]: p["us"] for p in comp["critical_path"]}
    old_sp = path.get("L20.ffn.softplus_sqrt")
    old_bias = path.get("L20.ffn.bias")
    old_t6 = path.get("L20.ffn.top6_order")
    sp = sim["spsqrt"][f"impl{a.impl}"]
    cyc = sp["cycles_die"]
    us_sp = cyc / FAST_HZ * 1e6
    bcyc = max(sim["bias_select"]["cycles"])
    us_bs = bcyc / FAST_HZ * 1e6

    def closes(s):
        return s["ss_setup_wns_ps"] is not None and s["ff_hold_wns_ps"] is not None and \
            s["ss_setup_wns_ps"] >= 0 and s["ff_hold_wns_ps"] >= 0
    exact = sim["status"] == "pass"
    ok = closes(ssp) and closes(sbs) and (route is None or route.get("closed", False))
    rec = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever="su_routeract",
        verdict=a.verdict or ("ADOPT" if exact and ok else "REJECT"), exact=exact,
        ss_ff=dict(period_ps=833.0,
                   spsqrt_lane=dict(ss_setup_wns_ps=ssp["ss_setup_wns_ps"], ff_hold_wns_ps=ssp["ff_hold_wns_ps"],
                                    cell_area_um2=ssp.get("cell_area_um2"), worst_end=ssp.get("worst_end"),
                                    basis=ssp.get("basis"), record=a.screen_sp_record or a.screen_sp),
                   bias_select=dict(ss_setup_wns_ps=sbs["ss_setup_wns_ps"], ff_hold_wns_ps=sbs["ff_hold_wns_ps"],
                                    cell_area_um2=sbs.get("cell_area_um2"), worst_end=sbs.get("worst_end"),
                                    basis=sbs.get("basis"), record=a.screen_bias_record or a.screen_bias),
                   route=route, closes=ok),
        nodes={
            "*.ffn.softplus_sqrt": dict(
                us=round(us_sp, 5), cls="measured", kind="fused_fast",
                source=(f"ot_dsrom_su_spsqrt ({LANES} lanes of {sp['lane']}, 1.2 GHz, at the router field's output "
                        f"root: {IN_ST} in + {OUT_ST} out wire stages) {cyc} cycles first raw row in -> the die's "
                        f"96 scores out (4 beats), exact on all 40 layers x 384 rows of the 1M token + "
                        f"{sp['stress_inputs']} stress inputs ({Path(a.sim).name})")),
            "*.ffn.bias": dict(us=0.0, cls="measured", kind="fused_fast",
                               source="covered by ffn.top6_order: the add runs in front of the select tree "
                                      "(ot_dsrom_su_bias_select)"),
            "*.ffn.top6_order": dict(
                us=round(us_bs, 5), cls="measured",
                source=(f"ot_dsrom_su_bias_select (64 f12 adders LA 4 + ot_hdc_select_tree) {bcyc} cycles at 1.2 GHz "
                        f"first unbiased score beat -> 6 ids, exact on all 40 layers' golden 1M router scores + "
                        f"{sim['bias_select']['random_segments']} random segments ({Path(a.sim).name})")),
        },
        measurement=dict(
            old=dict(softplus_sqrt_us=old_sp, bias_us=old_bias, top6_order_us=old_t6,
                     record="results/rtl/dsrom_recovery_20261004/composition.json (wired SU 0.9 GHz + measured CDC)"),
            new=dict(softplus_sqrt_cycles=cyc, softplus_sqrt_us=round(us_sp, 5), lane_latency=sp["latency"],
                     bias_select_cycles=bcyc, top6_order_us=round(us_bs, 5)),
            saving_us_per_layer=round((old_sp + old_bias + old_t6) - (us_sp + us_bs), 5),
            floor=a.floor and json.loads(a.floor)),
        default="opt-in: applied only in the recovery baseline; the stream unit's side pipe and ot_hdc_select_tree "
                "are unchanged")
    if a.note:
        rec["note"] = a.note
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("operands")
    s.add_argument("--gold", required=True)
    s.add_argument("--out", required=True)
    s = sp.add_parser("sim")
    s.add_argument("--operands", required=True)
    s.add_argument("--work", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--impls", default="0,1")
    s.add_argument("--stress", type=int, default=200000)
    s.add_argument("--random", type=int, default=4000)
    s = sp.add_parser("lever")
    for k in ("--sim", "--screen-sp", "--screen-bias", "--out"):
        s.add_argument(k, required=True)
    for k in ("--route", "--sim-record", "--screen-sp-record", "--screen-bias-record", "--verdict", "--note", "--floor"):
        s.add_argument(k)
    s.add_argument("--impl", type=int, default=0)
    a = ap.parse_args(argv)
    return dict(operands=cmd_operands, sim=cmd_sim, lever=cmd_lever)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
