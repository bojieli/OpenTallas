#!/usr/bin/env python3
"""RTL campaign for the per-bank Engram gather (rtl/hdc/v41x/ot_hdc_v41x_egather.sv).

Spec (docs/ARCH_SPEC_V41.md section 6 item 8; results/arch/arch_budget_v41.json engram): 48 rows x 264 B =
12,672 B per token within a quarter of the >= 3.57 us slack, i.e. >= 13.7 B/cycle into the consuming die;
one 264-B row per column bank per token; a 256-bit beat stream, ~400 cycles per token; a normal pin count
(the as-built flat 48 x 2,112-bit port has 16,559 IO pins).

DUT (rtl/test/tb_hdc_v41x_egather.sv): 48 ot_hdc_v41x_egather_slice (one per column bank) with in-order
behavioural ROMs of any latency, a behavioural merge network carrying one 256-bit beat per cycle in
round-robin or random bank order (link latency, link stalls), and ot_hdc_v41x_egather_asm writing a
behavioural vector memory (write-port stalls).  Every 512-bit word of every token is compared.

Expected rows are the golden's:
* shipped geometry (256 codes, 8 beats per row; released primes and offsets): the hash rows of
  hdc_golden_v41.EngramTables on the shipped tables (hdc_v41_engram_shipped.shipped_tables) for the token
  streams of rtl_hdc_v41_engram_gather_campaign, the synthetic table content of
  hdc_v41_engram_shipped.row_bytes (every E4M3 code, every scale byte), decoded by the golden's expression
  (hdc_v41_engram_shipped.decode_rows);
* the reduced vehicle (32 codes, one beat per row): its real tables, real hashes of the workload's prompt and
  gold tokens and of random token streams; the expected rows are RECORDED from Model.engram_layer inside a
  forward pass (the rows it hands to the Engram wkv), and the bench's own expectation must equal them.

Writes results/rtl/hdc_v41x_egather_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import hdc_v41_engram_shipped as ES  # noqa: E402
import rtl_hdc_v41_engram_gather_campaign as GC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_egather_campaign.json"
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_egather.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_egather.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_v41_engram_shipped.py",
         ROOT / "tools/rtl_hdc_v41_engram_gather_campaign.py", Path(__file__)]
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY")
VL_FLAGS = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
            "-Wno-MULTIDRIVEN")
NL, NC = 2, 24
TROWS = 1 << 18
MAXT = 700
# name, plusargs
MODES = {
    "shipped": [
        ("back_to_back_rr_4", dict(LAT=4, NETLAT=2)),
        ("back_to_back_random_order_stressed", dict(LAT=4, JIT=40, NETLAT=6, NSTALL=10, ARB=1, WSTALL=10, CDEL=60)),
        ("isolated_ucie_hop_pair_23", dict(LAT=4, NETLAT=23, SPACED=1)),
        ("isolated_board_hop_pair_209", dict(LAT=4, NETLAT=209, SPACED=1)),
    ],
    "reduced": [
        ("back_to_back_rr_4", dict(LAT=4, NETLAT=2, TABLE=1)),
        ("back_to_back_random_order_stressed", dict(LAT=4, JIT=40, NETLAT=6, NSTALL=10, ARB=1, WSTALL=10, CDEL=60,
                                                    TABLE=1)),
    ],
}
MUTATIONS = [
    ("slice: scale not latched for beats 1..", "wire [7:0]       r_scale = (r_beat == 0) ? rd[263:256] : scl;",
     "wire [7:0]       r_scale = rd[263:256];"),
    ("slice: column base not subtracted", "wire [RW-1:0]    hres = hrow - cfg_base;", "wire [RW-1:0]    hres = hrow;"),
    ("slice: beat index off by one", "if (issue) mq[mq_wp] <= {cur_tag, cur_beat};",
     "if (issue) mq[mq_wp] <= {cur_tag, cur_beat + 1'b1};"),
    ("asm: layer and column order swapped", "ma <= ((hsl * NL + hly) * NC + hcl) * BEATS + hbt;",
     "ma <= ((hsl * NC + hcl) * NL + hly) * BEATS + hbt;"),
    ("asm: slot ignored in the address", "ma <= ((hsl * NL + hly) * NC + hcl) * BEATS + hbt;",
     "ma <= ((0 * NL + hly) * NC + hcl) * BEATS + hbt;"),
    ("asm: token ready one word early", "rdy[s] <= busy[s] && !(rel_valid && rel_tag == s) && (cnt[s] == TOTV);",
     "rdy[s] <= busy[s] && !(rel_valid && rel_tag == s) && (cnt[s] >= TOTV - 1);"),
    ("decode: subnormal tie rounds away from even", "(rem == half && q[0])", "(rem == half)"),
    ("decode: NaN sign dropped", "{s, 15'h7FC0}", "{1'b0, 15'h7FC0}"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def words_of(bf16_rows, beats):
    """BF16 rows [n, 32*beats] -> hex 512-bit words, lane 0 lowest, per row per beat."""
    out = []
    for row in bf16_rows:
        for k in range(beats):
            lanes = row[32 * k:32 * (k + 1)]
            out.append("".join(f"{int(v):04x}" for v in lanes[::-1]))
    return out


# -- shipped geometry --------------------------------------------------------------------------------------
def shipped_vectors(ntok, rng):
    t = ES.shipped_tables()
    layout = ES.check_against_released_layout(t)
    toks, counts = GC.build_vectors(t, rng)
    toks = toks[:ntok]
    bases = [int(t.offsets[li][c]) for li in range(NL) for c in range(NC)]
    reqs, exp = [], []
    for _, _, rr in toks:
        for li in range(NL):
            codes, scales = [], []
            for c, row in enumerate(rr[li]):
                assert bases[li * NC + c] <= row < bases[li * NC + c] + int(t.primes[li].reshape(-1)[c])
                reqs.append(row)
                cd, s = ES.row_bytes(li, row)
                codes.append(cd)
                scales.append(s)
            exp.extend(words_of(ES.decode_rows(codes, scales), ES.BEATS))
    return {"bases": bases, "reqs": reqs, "exp": exp, "ntok": len(toks), "table": None, "beats": ES.BEATS,
            "streams": counts, "released_layout": layout}


# -- the reduced vehicle -------------------------------------------------------------------------------------
def reduced_vectors(ntok_random, rng):
    """Real tables and hashes; the expected rows recorded from Model.engram_layer in a forward pass."""
    model = G.Model()
    eng = model.engram
    prompt, gold = G.prompt_and_expected()
    # recorded: run the golden over the workload's tokens and capture the rows engram_layer builds
    rec = []
    orig_layer, orig_lq = G.Model.engram_layer, G.linear_q
    state = {"on": False}

    def lq(w, x):
        if state["on"]:
            rec.append(np.asarray(x, dtype=np.float32).copy())
            state["on"] = False
        return orig_lq(w, x)

    def layer(self, h, L, history):
        state["on"] = True
        return orig_layer(self, h, L, history)

    G.Model.engram_layer, G.linear_q = layer, lq
    try:
        st = model.new_state()
        model.forward_positions(list(prompt) + list(gold[:4]), 0, st)
    finally:
        G.Model.engram_layer, G.linear_q = orig_layer, orig_lq
    hist_all = list(prompt) + list(gold[:4])
    streams = [("reduced_workload_prompt_and_gold", hist_all)]
    V = int(model.c["vocab_size"])
    k = 0
    while sum(len(s) for _, s in streams) < len(hist_all) + ntok_random:
        n = int(rng.integers(1, 40))
        streams.append((f"random_{k}", [int(i) for i in rng.integers(0, V, n)]))
        k += 1
    bases = [int(eng.offsets[li][c]) for li in range(NL) for c in range(NC)]
    tab = {}
    reqs, exp, rows_checked = [], [], 0
    for name, ids in streams:
        for p in range(len(ids)):
            hist = ids[:p + 1]
            for li, L in enumerate(eng.layer_ids):
                rid = eng.hashes(hist, li)
                codes, sc = model.emb_codes[L]
                rows = G.to_bf16((G.E4M3[codes[rid]] * np.exp2(sc[rid])[:, None]).astype(G.F))
                if name.startswith("reduced_workload"):
                    got = rec[li * len(hist_all) + p].reshape(rows.shape)   # layer-major pass
                    assert np.array_equal(G.bits(got), G.bits(rows)), (p, li)
                    rows_checked += rows.shape[0]
                for c, r in enumerate(rid):
                    reqs.append(int(r))
                    tab[(li, int(r))] = (codes[r], int(sc[r]) + 127)
                exp.extend(words_of((G.bits(rows) >> 16).astype(np.int64), 1))
    assert len(rec) == 2 * len(hist_all), (len(rec), len(hist_all))
    ntok = sum(len(s) for _, s in streams)
    return {"bases": bases, "reqs": reqs, "exp": exp, "ntok": ntok, "beats": 1,
            "table": tab, "table_rows": [int(model.emb_codes[L][0].shape[0]) for L in eng.layer_ids],
            "streams": {"reduced_workload_prompt_and_gold": len(hist_all), "random": ntok - len(hist_all)},
            "golden_rows_recorded_and_equal": rows_checked}


def write_vectors(d: Path, v):
    d.mkdir(parents=True, exist_ok=True)
    (d / "eg_meta.mem").write_text(f"{v['ntok']:08x}\n{0:08x}\n")
    (d / "eg_base.mem").write_text("".join(f"{b:08x}\n" for b in v["bases"]))
    (d / "eg_req.mem").write_text("".join(f"{r:08x}\n" for r in v["reqs"]))
    (d / "eg_exp.mem").write_text("\n".join(v["exp"]) + "\n")
    if v["table"] is not None:
        # every addressed row at l * TROWS + row; the rest zero (never read by a correct slice)
        lines = {}
        for (li, r), (codes, sbyte) in v["table"].items():
            assert r < TROWS
            word = (sbyte << 256) | int.from_bytes(bytes(int(c) for c in codes), "little")
            lines[li * TROWS + r] = word
        out = []
        for i in sorted(lines):
            out.append(f"@{i:x}\n{lines[i]:066x}\n")
        (d / "eg_tab.mem").write_text("".join(out))


def build(obj: Path, beats, sources, maxt, trows):
    subprocess.run(["verilator", *VL_FLAGS, "--top-module", "tb_hdc_v41x_egather", "-Mdir", str(obj),
                    f"-GBEATS={beats}", f"-GMAXT={maxt}", f"-GTROWS={trows}",
                    "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_egather", "-CFLAGS", "-O1", "-j", "8",
                    *map(str, sources), str(TB), str(HARNESS)], check=True, capture_output=True, text=True)
    return obj / "Vtb_hdc_v41x_egather"


RE_EG = re.compile(r"EG tokens=(\d+) words=(\d+) errors=(\d+) faults=(\d+) rom_over=(\d+) cycles=(\d+) "
                   r"beats=(\d+) lat_min=(\d+) lat_max=(\d+) lat_sum=(\d+) gap_min=(\d+) gap_max=(\d+)")


def simulate(exe, d, args, seed=5):
    p = subprocess.run([str(exe), f"+SEED={seed}", f"+verilator+seed+{seed}", "+verilator+rand+reset+2",
                        *(f"+{k}={v}" for k, v in args.items())], cwd=d,
                       capture_output=True, text=True, timeout=7200)
    m = RE_EG.search(p.stdout)
    if not m:
        return {"pass": False, "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-1500:]}
    tok, words, err, flt, over, cyc, beats, lmin, lmax, lsum, gmin, gmax = map(int, m.groups())
    return {"pass": err == 0 and flt == 0 and over == 0, "tokens": tok, "words_compared": words,
            "word_mismatches": err, "faults": flt, "rom_queue_overflows": over, "cycles": cyc,
            "beats_moved": beats, "latency_cycles": {"min": lmin, "max": lmax, "mean": round(lsum / max(1, tok), 1)},
            "token_interval_cycles": {"min": gmin, "max": gmax,
                                      "mean": round(cyc / max(1, tok - 1), 1) if tok > 1 else None},
            "first_mismatches": [ln for ln in p.stdout.splitlines() if ln.startswith("MISMATCH")][:3]}


def pins():
    """Signal IO pins of the two blocks at the shipped parameters (from the port declarations)."""
    TW, LW, CW, BTW, RW, AW = 1, 1, 5, 3, 32, 24
    TAGW = TW + LW + CW + BTW + 8
    slice_ = {"clk_rst": 2, "straps": RW + LW + CW, "request": 2 + RW + TW, "rom": 1 + (AW + BTW) + 1 + 264,
              "beats": 2 + 256 + TAGW}
    VAW = math.ceil(math.log2(2 * NL * NC * 8))
    asm = {"clk_rst": 2, "slots": 2 + TW, "beats": 2 + 256 + TAGW, "write_port": 2 + VAW + 512,
           "completion": 2 + 1 + TW + 1}
    return {"slice": {**slice_, "total": sum(slice_.values())}, "asm": {**asm, "total": sum(asm.values())},
            "as_built_flat_port_io_pins": 16559}


def run(quick=False, scratch=None, ntok=MAXT - 100) -> dict:
    rng = np.random.default_rng(20260926)
    base = Path(scratch) if scratch else Path(tempfile.mkdtemp(prefix="egather_"))
    vec = {"shipped": shipped_vectors(60 if quick else ntok, rng),
           "reduced": reduced_vectors(40 if quick else 400, rng)}
    lint = {t: subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", t, str(RTL)],
                              capture_output=True, text=True)
            for t in ("ot_hdc_v41x_egather_slice", "ot_hdc_v41x_egather_asm")}
    runs, muts = {}, []
    for cfg, v in vec.items():
        d = base / cfg
        write_vectors(d, v)
        exe = build(d / "obj", v["beats"], [RTL], MAXT, TROWS if v["table"] is not None else 1)
        runs[cfg] = {}
        for name, args in (MODES[cfg][:1] if quick else MODES[cfg]):
            r = simulate(exe, d, args)
            r["plusargs"] = args
            runs[cfg][name] = r
            print(cfg, name, "pass" if r.get("pass") else "FAIL",
                  {k: r.get(k) for k in ("tokens", "word_mismatches", "latency_cycles", "token_interval_cycles")},
                  flush=True)
    if not quick:
        md = base / "mut"
        mv = dict(vec["shipped"])
        n = 40
        mv.update(ntok=n, reqs=mv["reqs"][:n * NL * NC], exp=mv["exp"][:n * NL * NC * ES.BEATS])
        write_vectors(md, mv)
        for i, (name, old, new) in enumerate(MUTATIONS):
            src = RTL.read_text()
            assert src.count(old) == 1, old
            mdir = base / f"mut_{i}"
            mdir.mkdir(parents=True, exist_ok=True)
            (mdir / RTL.name).write_text(src.replace(old, new))
            try:
                mexe = build(mdir / "obj", ES.BEATS, [mdir / RTL.name], MAXT, 1)
                r = simulate(mexe, md, MODES["shipped"][1][1])
                caught = not r.get("pass")
            except subprocess.CalledProcessError as e:
                caught, r = True, {"build_error": (e.stderr or "")[-300:]}
            muts.append({"mutation": name, "caught": caught, "word_mismatches": r.get("word_mismatches"),
                         "faults": r.get("faults")})
            print("mutation", name, "caught" if caught else "MISSED", flush=True)
    budget = json.loads(BUDGET.read_text())["engram"]
    sp = runs["shipped"].get("back_to_back_rr_4", {})
    iv = (sp.get("token_interval_cycles") or {}).get("mean")
    lat = (runs["shipped"].get("isolated_ucie_hop_pair_23") or sp).get("latency_cycles", {})
    spec = {
        "bytes_per_token": budget["bytes_per_token"],
        "required_bytes_per_cycle": budget["required_bytes_per_cycle"],
        "measured_bytes_per_cycle": round(budget["bytes_per_token"] / iv, 2) if iv else None,
        "measured_token_interval_cycles": iv,
        "spec_port_cycles": budget["port_cycles"],
        "bandwidth_met": bool(iv) and budget["bytes_per_token"] / iv >= budget["required_bytes_per_cycle"],
        "isolated_token_latency_cycles": lat,
        "note": "a token is 384 beats of 256-bit codes + tag (the UE8M0 scale rides in every beat's tag, so the "
                "row's 7 pad bytes are never sent); one beat per cycle is 32 B/cycle of codes, 2.4x the "
                "requirement"}
    ok = (all(r.get("pass") for c in runs.values() for r in c.values())
          and all(l.returncode == 0 for l in lint.values()) and all(m["caught"] for m in muts))
    return {
        "schema": "opentallas.hdc-v41x-egather-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "cycle-level Verilator simulation of 48 column-bank slices and the consumer-side "
                          "assembler with behavioural ROMs, a behavioural one-beat-per-cycle merge network and a "
                          "behavioural vector memory; the shipped table CONTENT is synthetic (not in this "
                          "repository), the reduced vehicle's is real; link latencies are parameters.  Clock, "
                          "area and pins: results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_egather_{slice,asm}.",
        "spec": spec,
        "io_pins": pins(),
        "vectors": {cfg: {k: v[k] for k in ("ntok", "beats", "streams") if k in v} |
                    ({"golden_rows_recorded_and_equal": v["golden_rows_recorded_and_equal"]}
                     if "golden_rows_recorded_and_equal" in v else {}) |
                    ({"released_layout": v["released_layout"]} if "released_layout" in v else {})
                    for cfg, v in vec.items()},
        "runs": runs,
        "mutations": muts,
        "verilator_lint": {"flags": list(LINT_FLAGS),
                           **{t: {"returncode": l.returncode, "messages": l.stderr.strip().splitlines()[:10]}
                              for t, l in lint.items()}},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--scratch", type=Path)
    args = ap.parse_args()
    rec = run(args.quick, args.scratch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
