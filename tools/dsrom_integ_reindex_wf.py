#!/usr/bin/env python3
"""DS-ROM integration checkpoint, vehicle (a): one re-index stage, every adopted flag on, verify positions issued
back to back by the wavefront package controller, at full shape on the 1M reference token's golden data.

Bench rtl/dsrom_sys/integration/tb_dsrom_integ_reindex_wf.sv: ot_rom_pkg_ctrl_wf (WAVE=1, WIN=6, NW=21, XWORDS=1)
-> ot_dsrom_reindex_chain (ot_hdc_v41x_idx_kgather_ps x 4 timed HBM3E stacks -> scorer stand-in at the idx-array
latency -> ot_hdc_v41x_sel_mdrop_top MDROP=1 -> top-512 select), one rank (die) per run.

Jobs (two verify positions of one user, both lists written before the first job starts, as the wavefront delivers
them):
  job 0  position 1,048,574  STAND-IN data: L28's golden 1M index scores on HALF the real candidate blocks (every other
         block of each stack, plus the newest block 131,071, whose position 1,048,575 is AFTER the job's position and
         is given an adversarial score: the keep mask must drop it).  Expected: topk_lowest_index on
         where(sub & pos <= 1,048,574, s28, -inf).
  job 1  position 1,048,575  REAL: L24's golden 1M index scores on the real candidate blocks (the target token).
         Expected: topk_lowest_index on the golden masked scores; the four ranks' union is checked against the golden
         layer's own selection by the cross-die final (results/rtl/dsrom_reindex_candidates_20261004, same inputs).
Configurations: slots (LSW=3: 8 position-slotted lists >= WIN) vs as built (LSW=0: one list -> job 0 reads job 1's list),
and a functional REPLAY case (one stack 2,048 blocks with ascending scores: the select overflows, pulses rep_req and
the chain re-issues the gather; one stack empty: the chain's empty last beat).

    python3 tools/dsrom_integ_reindex_wf.py prep   --scratch DIR             (golden -> lists/scores/expected)
    python3 tools/dsrom_integ_reindex_wf.py run    --scratch DIR [--jobs 8] (Verilator builds + runs)
    python3 tools/dsrom_integ_reindex_wf.py record --scratch DIR [--out results/rtl/dsrom_integration_20261004/reindex_wf.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_reindex_candidates as R  # noqa: E402

TB = ROOT / "rtl/dsrom_sys/integration/tb_dsrom_integ_reindex_wf.sv"
HARNESS = ROOT / "rtl/dsrom_sys/integration/tb_dsrom_integ_reindex_wf_harness.cpp"
SRC = ["rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv",
       "rtl/dsrom_sys/integration/ot_hdc_v41x_idx_kgather_ps.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv", "rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_sel.sv", "rtl/hdc/v41x/ot_hdc_v41x_sel_mdrop.sv",
       "rtl/dsrom_sys/integration/ot_dsrom_reindex_chain.sv", "rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv"]
REC = ROOT / "results/rtl/dsrom_integration_20261004/reindex_wf.json"
P0 = 1048574
NEWEST = 131071
K = 512
PL = R.PLACEMENTS["p2"]          # the placement of the measured worst rank (real_rank1_p2, 757 cycles)
IDX_ARRAY = dict(latency=48, query_settle=24)    # tools/dsrom_1m_measure.py IDX_ARRAY (results/rtl/w11_idx_array.json)
SRC += ["rtl/dsrom_sys/reindex_parent/"+name for name in (
    "ot_dsrom_reindex_gather.sv", "ot_dsrom_reindex_gather_parent.sv",
    "ot_dsrom_reindex_kgctl_parent.sv", "ot_dsrom_reindex_kgdata_parent.sv",
    "ot_dsrom_reindex_list_macro.sv", "ot_dsrom_reindex_request_cut.sv")]
SRC += ["rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_drain_queue.sv"]
SRC += ["physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"]


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_job(d: Path, tag: str, lists, bits_rank, exps):
    """lists: per stack local block indices; bits_rank: 262,144 uint16 (the scores the stand-in returns);
    exps: per quarter [(pos, bits, ninf)]."""
    for q, l in enumerate(lists):
        (d / f"{tag}.s{q}").write_text(f"{len(l)}\n" + "".join(f"{x:x}\n" for x in l))
        (d / f"{tag}.exp{q}").write_text(f"S {len(exps[q])}\n" + "".join(f"{p:x} {b:x} {n}\n" for p, b, n in exps[q]))
    (d / f"{tag}.scores.hex").write_text("".join(f"{int(x):04x}\n" for x in bits_rank))


def cmd_prep(a):
    import dsrom_1m_measure as M
    d = a.scratch.resolve()
    d.mkdir(parents=True, exist_ok=True)
    cand, blk = R.cand_blocks(a.gold)
    s24 = M.gold_layer(a.gold, 24)[0]["L24.index_scores"]
    s28 = M.gold_layer(a.gold, 28)[0]["L28.index_scores"]
    assert (np.isfinite(s24) == cand).all() and (np.isfinite(s28) == cand).all()
    # job 0 (stand-in): every other candidate block of each stack + the newest block
    sub_blk = np.array(sorted(set(blk[::2].tolist()) | {NEWEST}))
    sub = np.zeros_like(cand)
    for b in sub_blk:
        sub[8 * b:8 * b + 8] = True
    fin = s28[np.isfinite(s28)]
    adv = int(R.bf16_bits(np.array([float(fin.max()) * 2 + 1.0]))[0])
    man = dict(p0=P0, newest_block=NEWEST, adversarial_bits=hex(adv), ranks={})
    for r in range(R.TP):
        lo = r * R.PER_RANK
        pos = np.arange(lo, lo + R.PER_RANK)
        cuts = [q * R.PER_STACK for q in range(R.STACKS + 1)]
        # job 1: real L24
        keep1 = cand[lo:lo + R.PER_RANK]
        bits1 = np.where(keep1, R.bf16_bits(np.where(keep1, s24[lo:lo + R.PER_RANK], 0.0)), R.NINF).astype(np.int64)
        exp1, sel1 = R.expect(bits1, pos, cuts, K)
        write_job(d, f"r{r}_j1", R.rank_lists(blk, r), bits1, exp1)
        bits28 = np.where(keep1, R.bf16_bits(np.where(keep1, s28[lo:lo + R.PER_RANK], 0.0)), R.NINF).astype(np.int64)
        exp28, sel28 = R.expect(bits28, pos, cuts, K)
        write_job(d, f"r{r}_j1L28", R.rank_lists(blk, r), bits28, exp28)
        # job 0: stand-in L28 on the sub-list, causal mask at P0 (the stand-in stream still carries a score there)
        keep0 = sub[lo:lo + R.PER_RANK] & (pos <= P0)
        bits0 = np.where(keep0, R.bf16_bits(np.where(keep0, s28[lo:lo + R.PER_RANK], 0.0)), R.NINF).astype(np.int64)
        exp0, sel0 = R.expect(bits0, pos, cuts, K)
        stream0 = bits0.copy()
        late = sub[lo:lo + R.PER_RANK] & (pos > P0)
        stream0[late] = adv                                   # would be selected if not dropped
        write_job(d, f"r{r}_j0", R.rank_lists(sub_blk, r), stream0, exp0)
        man["ranks"][r] = dict(blocks_j1=[len(x) for x in R.rank_lists(blk, r)],
                               blocks_j0=[len(x) for x in R.rank_lists(sub_blk, r)],
                               late_positions_j0=int(late.sum()), selected_j1=len(sel1), selected_j0=len(sel0),
                               sel_j1_sha256=hashlib.sha256(json.dumps(sel1).encode()).hexdigest())
    # replay case (functional): rank 0 geometry; stack 0: 2,048 blocks of ascending scores (every key survives the
    # running bound -> line-memory overflow -> rep_req); stack 1 empty; stacks 2, 3: 40 random blocks each
    rng = np.random.default_rng(20261004)
    lists = [list(range(0, 4096, 2)), [], sorted(rng.choice(8192, 40, replace=False).tolist()),
             sorted(rng.choice(8192, 40, replace=False).tolist())]
    vals = np.full(R.PER_RANK, -np.inf)
    for q, l in enumerate(lists):
        for b in l:
            p = q * R.PER_STACK + 8 * b
            vals[p:p + 8] = (np.arange(p, p + 8) / 1000.0) if q == 0 else rng.standard_normal(8)
    keep = np.isfinite(vals)
    bits = np.where(keep, R.bf16_bits(np.where(keep, vals, 0.0)), R.NINF).astype(np.int64)
    expr, _ = R.expect(bits, np.arange(R.PER_RANK), [q * R.PER_STACK for q in range(5)], K)
    write_job(d, "replay_j0", lists, bits, expr)
    man["replay"] = dict(blocks=[len(x) for x in lists])
    man["golden"] = dict(cand=sha(a.gold / "ctx1048576_cand.npz"), L24=sha(a.gold / "ctx1048576_L24.npz"),
                         L28=sha(a.gold / "ctx1048576_L28.npz"))
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man["ranks"], indent=0))


def build(d: Path, lsw: int, njobs: int):
    obj = d / f"obj_lsw{lsw}_n{njobs}"
    exe = obj / "Vtb_dsrom_integ_reindex_wf"
    if not exe.exists():
        subprocess.run([R.verilator(), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNOPTFLAT", "-Wno-MULTIDRIVEN", "--top-module", "tb_dsrom_integ_reindex_wf",
                        f"-GLSW={lsw}", f"-GNJOBS={njobs}",
                        f"-GBASE={PL['BASE']}", f"-GBSTEP={PL['BSTEP']}", f"-GOSTEP={PL['OSTEP']}",
                        f"-GLAT={IDX_ARRAY['latency']}", f"-GSETTLE={IDX_ARRAY['query_settle']}",
                        "--Mdir", str(obj), *[str(ROOT / s) for s in SRC], str(TB), str(HARNESS),
                        "-CFLAGS", "-O1"], check=True, capture_output=True, cwd=ROOT)
    return exe


JOB = re.compile(r"JOB (\d+) pos=(\d+) slot=(\d+) start=(-?\d+) first_key=(-?\d+) last_key=(-?\d+) last_scored=(-?\d+) "
                 r"done=(-?\d+) busy=(-?\d+) passes=(\d+) keys=(\d+) out=(\d+) errors=(\d+)")
SUM = re.compile(r"SUMMARY (.*)")
HO = re.compile(r"HANDOFF job (\d+) start-after-prev-done=(\d+)")


def run_one(d: Path, name: str, lsw: int, jobs, rank: int, p0: int):
    exe = build(d, lsw, len(jobs))
    args = [f"+RANK={rank}", f"+P0={p0}"]
    for j, tag in enumerate(jobs):
        args += [f"+L{j}={d / tag}", f"+SC{j}={d / (tag + '.scores.hex')}", f"+EX{j}={d / tag}"]
    r = subprocess.run([str(exe), *args], capture_output=True, text=True, cwd=d)
    out = r.stdout + r.stderr
    (d / f"{name}.log").write_text(out)
    res = dict(name=name, lsw=lsw, rank=rank, jobs=list(jobs), pass_=("PASS" in out.split()) and r.returncode == 0)
    res["job"] = [dict(zip(("job", "pos", "slot", "start", "first_key", "last_key", "last_scored", "done", "busy",
                            "passes", "keys", "out", "errors"), map(int, m.groups()))) for m in JOB.finditer(out)]
    res["handoff_cycles"] = [int(m.group(2)) for m in HO.finditer(out)]
    m = SUM.search(out)
    if m:
        res["summary"] = dict(kv.split("=") for kv in m.group(1).split())
    res["first_errors"] = [ln for ln in out.splitlines() if ln.startswith("E ")][:6]
    return res


def cmd_run(a):
    d = a.scratch.resolve()
    cases = []
    for r in range(4):
        cases.append((f"slots_r{r}", 3, [f"r{r}_j0", f"r{r}_j1"], r, P0))
    cases.append(("asbuilt_r3", 0, ["r3_j0", "r3_j1"], 3, P0))
    for r in range(4):                                             # the target position alone, per layer
        cases.append((f"solo_L24_r{r}", 3, [f"r{r}_j1"], r, P0 + 1))
        cases.append((f"solo_L28_r{r}", 3, [f"r{r}_j1L28"], r, P0 + 1))
    cases.append(("replay", 3, ["replay_j0"], 0, P0 + 1))
    # builds first (one per configuration, in parallel), then the runs in parallel
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(lambda c: build(d, c[0], c[1]), sorted({(c[1], len(c[2])) for c in cases})))
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(lambda c: run_one(d, *c), cases))
    (d / "runs.json").write_text(json.dumps(res, indent=1) + "\n")
    for x in res:
        print(x["name"], x["pass_"], [(j["job"], j["done"], j["errors"], j["passes"]) for j in x["job"]],
              x["handoff_cycles"], x.get("summary", {}).get("key_errors"), x["first_errors"][:2])


def cmd_record(a):
    d = a.scratch.resolve()
    runs = {x["name"]: x for x in json.loads((d / "runs.json").read_text())}
    sep = json.loads((ROOT / "results/rtl/dsrom_reindex_candidates_20261004/gather.json").read_text())
    sel = json.loads((ROOT / "results/rtl/dsrom_reindex_candidates_20261004/select.json").read_text())
    worst_gather = sep["worst_rank"]["cycles"]
    seg = lambda L: max(sg["last"] - sg["first"] + 1 + sg["tail"]
                        for sg in sel["layers"][L]["gather"]["runs"][0]["per_segment"])
    separate = {L: worst_gather + IDX_ARRAY["query_settle"] + IDX_ARRAY["latency"] + seg(L) for L in ("L24", "L28")}
    slots = [runs[f"slots_r{r}"] for r in range(4)]
    chained = {L: {r: runs[f"solo_{L}_r{r}"]["job"][0]["done"] for r in range(4)} for L in ("L24", "L28")}
    rec = dict(
        schema="opentallas.dsrom-integration.reindex-wf.v1",
        vehicle="one re-index stage (L24 / L28) of one rank, full shape, position 1,048,575 (and 1,048,574 ahead of "
                "it), wavefront controller WAVE=1 WIN=6 -> candidate-block gather (4 timed HBM3E stacks, placement p2) "
                "-> scorer stand-in (idx-array latency 48 + settle 24, golden BF16 scores) -> mask-drop MDROP=1 -> "
                "top-512 select",
        unvalidated=["index scorer arithmetic (stand-in returns the golden score of each position after the measured "
                     "idx-array latency; the as-built scorer's exactness is its own record)",
                     "job 0 data is a stand-in (L28 scores on half the candidate blocks): no golden exists for a "
                     "second position at 1M"],
        all_pass=all(x["pass_"] for n, x in runs.items() if n != "asbuilt_r3"),
        asbuilt_single_list_fails=not runs["asbuilt_r3"]["pass_"],
        runs=runs,
        timing=dict(
            clock_hz=1.2e9,
            chained_cycles_start_to_last_out=chained,
            chained_worst={L: max(v.values()) for L, v in chained.items()},
            separate_composition_cycles=separate,
            separate_basis="tools/dsrom_1m_measure.py candidate_gather terms: idx.score = worst gather (757) + query "
                           "settle 24 + idx-array latency 48, then idx.topk_local = worst select-on-gather-order segment "
                           "(ingest + tail), serial",
            chained_over_separate={L: round(max(chained[L].values()) / separate[L], 4) for L in chained},
            wavefront_target_job_cycles={x["rank"]: x["job"][1]["done"] for x in slots},
            wavefront_handoff_cycles=[h for x in slots for h in x["handoff_cycles"]]),
        sources={p: sha(ROOT / p) for p in SRC + [str(TB.relative_to(ROOT)), str(HARNESS.relative_to(ROOT)),
                                                    "tools/dsrom_integ_reindex_wf.py"]},
        manifest=json.loads((d / "manifest.json").read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("all_pass", "asbuilt_single_list_fails", "timing")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--gold", type=Path, default=R.GOLD_DEFAULT)
    r = sub.add_parser("run")
    r.add_argument("--scratch", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=8)
    c = sub.add_parser("record")
    c.add_argument("--scratch", type=Path, required=True)
    c.add_argument("--out", type=Path, default=REC)
    a = ap.parse_args()
    dict(prep=cmd_prep, run=cmd_run, record=cmd_record)[a.cmd](a)


if __name__ == "__main__":
    main()
