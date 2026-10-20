#!/usr/bin/env python3
"""TOK-S81-GAPS/HEADB (10-18): INTERIM LM-head / MTP-draft-head measurement, NOT on a head die (gap G9: no head-die
netlist exists).  Vehicle = rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4.sv (4 x ot_dsrom_s81_head_amax_fh
ranks, TP4 x 32,320 rows, R = 128 lanes, ascending-vocab rank chain, final ARGMAX broadcast to every rank), fed from the
committed S81 layer fixtures (results/rtl/s81_layer_tput_1018/fixtures HEAD + MTP manifests; bulk on ot-epyc4/5).

Cases (one Verilator 5.050 build per FH):
  head      LG = HEAD ops/head.lm_head (129,280 FP32 logits), MK = MTP draft.markov0; op 1 (capture) must give the
            reference next token (HEAD io/next_token = 21946) with the golden logit bits.
  draft<k>  k = 0..4: LG = MTP draft.head<k>, MK = draft.markov<k>; op 2 (fused add(LG, MK) then argmax) must give
            draft.markov<k>.token and every fused lane must equal draft.markov<k>.logits bit for bit.
Mutants (must FAIL): mut_lg (head: the golden row 21946 lowered to -FLT_MAX -> a different token), fh0 (draft0 on the
FH = 0 build: the as-built head argmaxes the Markov row alone -> wrong draft token when it differs).

    python3 -I tools/s81_dv/head_tp4_interim.py --fix-head DIR --fix-mtp DIR --scratch DIR --out record.json
Exit 0 only when every base case passes and every mutant fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
SRC = ["rtl/rom/collectives/ot_rom_coll_pkg.sv", "rtl/rom/collectives/ot_rom_coll_skid.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv",
       "rtl/dsrom_sys/integration/ot_dsrom_s81_head_amax_fh.sv"]
TB = "rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4.sv"
HARNESS = "rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4_harness.cpp"
N = 4 * 32320
OPL = re.compile(r"OP (\d) fh=(\d) id=(\d+) val=([0-9a-f]+) beats=(\d+) first_beat=(\d+) last_beat=(\d+) "
                 r"dn0=(-?\d+) dn1=(-?\d+) dn2=(-?\d+) dn3=(-?\d+) final=(\d+) done=(\d+)")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def f32(p: Path) -> np.ndarray:
    a = np.fromfile(p, dtype="<f4")
    assert a.size == N, (p, a.size)
    return a


def i64(p: Path) -> np.ndarray:
    return np.fromfile(p, dtype="<i8")


def bits(a: np.ndarray) -> np.ndarray:
    return a.astype("<f4").view("<u4")


def wr_hex(p: Path, a: np.ndarray):
    p.write_text("".join(f"{int(b):08x}\n" for b in bits(a)))


def build(obj: Path, fh: int, log: Path):
    exe = obj / "Vtb_dsrom_s81_fused_head_tp4"
    if exe.exists():
        return exe, dict(reused=True)
    obj.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r = subprocess.run(["/usr/bin/time", "-v", str(VERILATOR), "--cc", "--exe", "--build", "-j", "8", "-O2",
                        "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_dsrom_s81_fused_head_tp4",
                        f"-GFH={fh}", "--Mdir", str(obj), *[str(ROOT / s) for s in SRC + [TB]], str(ROOT / HARNESS),
                        "-CFLAGS", "-O1"], capture_output=True, text=True, cwd=ROOT)
    log.write_text(r.stdout + r.stderr)
    rss = re.search(r"Maximum resident set size \(kbytes\): (\d+)", r.stderr)
    if r.returncode != 0 or not exe.exists():
        raise SystemExit(f"build FH={fh} failed rc {r.returncode}, see {log}")
    return exe, dict(reused=False, wall_s=round(time.time() - t0, 1), max_rss_kb=int(rss.group(1)) if rss else None)


def run(exe: Path, sc: Path, name: str):
    dump = sc / f"{name}.dump"
    t0 = time.time()
    r = subprocess.run([str(exe), f"+LG={sc / (name + '_lg.hex')}", f"+MK={sc / (name + '_mk.hex')}", f"+DUMP={dump}"],
                       capture_output=True, text=True)
    (sc / f"{name}.run.log").write_text(r.stdout + r.stderr)
    ops = {}
    for m in OPL.finditer(r.stdout):
        op, _, i, v, nb, fb, lb, d0, d1, d2, d3, fin, done = m.groups()
        ops[int(op)] = dict(id=int(i), bits=int(v, 16), beats=int(nb), first_beat=int(fb), last_beat=int(lb),
                            rank_dn=[int(d0), int(d1), int(d2), int(d3)], final=int(fin), done=int(done),
                            last_beat_to_rank0_result=int(d0) - int(lb), last_beat_to_final=int(fin) - int(lb),
                            first_beat_to_final=int(fin) - int(fb), first_beat_to_done=int(done) - int(fb))
    ok = r.returncode == 0 and "DONE" in r.stdout and set(ops) == {1, 2}
    return dict(returncode=r.returncode, completed=ok, ops=ops, wall_s=round(time.time() - t0, 1),
                tail=(r.stdout + r.stderr).splitlines()[-4:]), dump


def lanes(dump: Path, exp_bits: np.ndarray):
    got = {}
    if dump.exists():
        for ln in dump.read_text().split("\n"):
            if ln:
                i, v = ln.split()
                got[int(i, 16)] = int(v, 16)
    if not got:
        return dict(rows_seen=0, bit_mismatches=None, missing=N)
    ids = np.fromiter(got.keys(), dtype=np.int64)
    vals = np.fromiter(got.values(), dtype=np.uint32)
    return dict(rows_seen=len(got), bit_mismatches=int((exp_bits[ids] != vals).sum()), missing=N - len(got))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-head", type=Path, required=True)
    ap.add_argument("--fix-mtp", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    sc = a.scratch.resolve()
    sc.mkdir(parents=True, exist_ok=True)
    H, M = a.fix_head, a.fix_mtp
    inputs = {}
    lg_head = f32(H / "ops/head.lm_head.bin")
    y = int(i64(H / "io/next_token.bin")[0])
    assert int(np.argmax(lg_head)) == y, "fixture next_token != argmax(lm_head)"
    cases = {"head": dict(lg=lg_head, mk=f32(M / "ops/draft.markov0.bin"), check="op1", exp_id=y,
                          exp_bits=int(bits(lg_head[y:y + 1])[0]))}
    for k in range(5):
        lg, mk = f32(M / f"ops/draft.head{k}.bin"), f32(M / f"ops/draft.markov{k}.bin")
        fused = f32(M / f"ops/draft.markov{k}.logits.bin")
        tok = int(i64(M / f"ops/draft.markov{k}.token.bin")[0])
        np_add_eq = bool(np.array_equal(bits((lg + mk).astype(np.float32)), bits(fused)))
        cases[f"draft{k}"] = dict(lg=lg, mk=mk, check="op2", exp_id=tok, exp_bits=int(bits(fused[tok:tok + 1])[0]),
                                  fused=fused, fixture_logits_eq_f32_add=np_add_eq,
                                  argmax_fused_eq_token=int(np.argmax(fused)) == tok)
    mut = lg_head.copy()
    mut[y] = np.float32(-3.4028234663852886e38)
    cases["mut_lg"] = dict(lg=mut, mk=cases["head"]["mk"], check="op1", exp_id=y, exp_bits=cases["head"]["exp_bits"],
                           mutant=True)
    for n, c in cases.items():
        wr_hex(sc / f"{n}_lg.hex", c["lg"])
        wr_hex(sc / f"{n}_mk.hex", c["mk"])
        inputs[n] = dict(lg_hex=sha(sc / f"{n}_lg.hex"), mk_hex=sha(sc / f"{n}_mk.hex"))
    exe1, b1 = build(sc / "obj_fh1", 1, sc / "build_fh1.log")
    exe0, b0 = build(sc / "obj_fh0", 0, sc / "build_fh0.log")
    res = {}
    for n, c in cases.items():
        r, dump = run(exe1, sc, n)
        op = r["ops"].get(1 if c["check"] == "op1" else 2, {})
        r["id_ok"] = op.get("id") == c["exp_id"] and op.get("bits") == c["exp_bits"]
        if "fused" in c:
            r["fused_lanes"] = lanes(dump, bits(c["fused"]))
            r["lanes_ok"] = r["fused_lanes"]["bit_mismatches"] == 0 and r["fused_lanes"]["missing"] == 0
        r["pass"] = bool(r["completed"] and r["id_ok"] and r.get("lanes_ok", True))
        r.update({k: c[k] for k in ("check", "exp_id", "exp_bits", "fixture_logits_eq_f32_add",
                                    "argmax_fused_eq_token") if k in c})
        res[n] = r
        print(n, "PASS" if r["pass"] else "FAIL", json.dumps({k: v for k, v in r.items() if k not in ("tail",)})[:600],
              flush=True)
    # FH = 0 control mutant on draft0
    c = cases["draft0"]
    for x in ("lg", "mk"):
        (sc / f"fh0_draft0_{x}.hex").write_text((sc / f"draft0_{x}.hex").read_text())
    r, _ = run(exe0, sc, "fh0_draft0")
    op2 = r["ops"].get(2, {})
    r["id_ok"] = op2.get("id") == c["exp_id"] and op2.get("bits") == c["exp_bits"]
    r["pass"] = bool(r["completed"] and r["id_ok"])
    r["markov_only_argmax"] = int(np.argmax(c["mk"]))
    res["fh0_draft0"] = r
    print("fh0_draft0", "PASS" if r["pass"] else "FAIL", json.dumps(op2), flush=True)
    base = [n for n in res if n in ("head",) or n.startswith("draft")]
    muts = ["mut_lg", "fh0_draft0"]
    ok = all(res[n]["pass"] for n in base) and not any(res[n]["pass"] for n in muts)
    h1 = res["head"]["ops"].get(1, {})
    d2 = res["draft0"]["ops"]
    rec = dict(
        schema="opentallas.s81_dv.head_interim.v1",
        label="interim, not on a head die (gap G9: no head-die netlist; vehicle = fused_head_tp4 minimum component)",
        lane="TOK-S81-GAPS/HEADB 10-18", tool="tools/s81_dv/head_tp4_interim.py",
        fixtures=dict(head=str(H), mtp=str(M), head_manifest="results/rtl/s81_layer_tput_1018/fixtures/HEAD.sha256.json",
                      mtp_manifest="results/rtl/s81_layer_tput_1018/fixtures/MTP.sha256.json (claude/lb2-s81-mtp-1018)",
                      sha256={str(p): sha(p) for p in [H / "ops/head.lm_head.bin", H / "io/next_token.bin"] +
                              [M / f"ops/draft.{x}{k}{s}.bin" for k in range(5) for x, s in
                               (("head", ""), ("markov", ""), ("markov", ".logits"), ("markov", ".token"))]}),
        inputs_hex_sha256=inputs, build=dict(fh1=b1, fh0=b0), results=res, pass_=bool(ok),
        measured_cycles=dict(
            head_argmax_tail=dict(last_beat_to_final=h1.get("last_beat_to_final"),
                                  last_beat_to_rank0_result=h1.get("last_beat_to_rank0_result"),
                                  first_beat_to_final=h1.get("first_beat_to_final"), beats=h1.get("beats"),
                                  note="argmax over the 128-lane return stream + 4-rank chain merge + final broadcast; "
                                       "the stream itself is the bench's 1 beat/cycle feed, not the ROM field"),
            draft_fused_added=({k: d2[2][k] - d2[1][k] for k in ("last_beat_to_rank0_result", "last_beat_to_final")}
                               if 1 in d2 and 2 in d2 else None)),
        price_p4l=dict(source="results/rtl/s81_layer_tput_1018/compiler/lowering_head.json / lowering_mtp_draft.json",
                       head_hc_pre_norm=314.9, head_lm_head=8429.0, head_argmax=21.6, head_argmax_merge=374.9,
                       token_return=2194.0, head_total=11334.4, draft_head=8387.0, draft_markov=65.5),
        source_sha256={p: sha(ROOT / p) for p in SRC + [TB, HARNESS, "tools/s81_dv/head_tp4_interim.py"]},
        simulator=subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip())
    if h1:
        t = h1["last_beat_to_final"]
        rec["composed_head_cycles"] = dict(
            value=round(314.9 + 8429.0 + t + 2194.0, 1),
            terms="priced hc_pre+norm 314.9 + priced ROM-field lm_head stream 8,429.0 + MEASURED argmax/merge/broadcast "
                  f"tail {t} + priced token.return 2,194.0",
            priced_total=11334.4, priced_argmax_plus_merge=396.5, measured_tail=t)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print("HEAD_INTERIM", "PASS" if ok else "FAIL", json.dumps(rec.get("composed_head_cycles")), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
