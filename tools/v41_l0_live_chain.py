#!/usr/bin/env python3
"""Live L0 attention chain inside the V4.1 layer die (rung 6, first slice).

One Verilator process runs rtl/chip/ot_chip_v41x_die.sv at FULL_SHAPE with the
opt-in WINDOW HBM attention source (bounded tagged refill credits, single-use
QK->PV retention) and executes the ACTUAL production L0 program words
(results/rtl/hdc_v41x_fullshape_l0_program.hex) of the attention core:

    PC24 L0.scores  ME attention op q.k   (window rows from HBM through the die source)
    PC30 L0.softmax SU scale + max
    PC31 L0.softmax SU exp(s - max) + sum
    PC32 L0.pv      ME attention op p.v   (same generation's retained rows)
    PC33 L0.softmax SU sink denominator exp(sink - max) + sum
    PC34 L0.softmax SU divide, BF16

followed by the program's END word.  Nothing is replayed between them: scores,
probabilities and the PV accumulator move only through the tile's vector memory.

Inputs are synthetic but golden-consistent (seeded stored-format FP8 window
rows, BF16 q, sink float32(h/16 - 0.5)); the expected vector memory is computed
by the golden functions (hdc_golden / hdc_golden_v41 chunk8), independently of
the RTL.  The whole vector memory is compared bit for bit.

PROGRAM DEFECT (recorded, patched here): PC30 of the production program carries
imm1 = 0 for M1_AIMM (tools/hdc_replay_v41.py emits a shape-only placeholder),
so as encoded it multiplies every score by zero.  This gate substitutes
imm1 = float32(512 ** -0.5) (tools/rtl_v41_fullshape_layer_campaign.py
attn_scale) and records both words.

    python3 tools/v41_l0_live_chain.py prepare --out DIR [--pos 127] [--seed N]
    python3 tools/v41_l0_live_chain.py record --out DIR --log sim.log --config NAME [--record OUT.json]
        parses the bench report into a source-pinned case (appends; never overwrites a verdict)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_attn_campaign as A  # noqa: E402  (sets chunk8)
import rtl_hdc_v41x_vec_campaign as C  # noqa: E402
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"
PCS = (24, 30, 31, 32, 33, 34)
END_PC = 112
H, D, T = 16, 512, 128
Q_BASE, S_BASE, M_BASE, Z_BASE, DEN_BASE, ACC_BASE = 55744, 63936, 74176, 74208, 74240, 74272
S_STRIDE = 640
SINK_CROM = 12128
PITCH = 17
F = np.float32


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def program_words():
    words = [int(x, 16) for x in PROGRAM.read_text().split()]
    out, patches = [], []
    for pc in PCS:
        w = words[pc]
        d = I.decode(w, full_shape=True)
        if pc == 30:
            assert d["m1"] == I.M1_AIMM and d["red"] == I.RED_MAX and d["imm1"] == 0, d
            fields = {k: v for k, v in d.items()}
            fields["imm1"] = C.f32u(F(512) ** F(-0.5)) if hasattr(C, "f32u") else int(np.float32(512 ** -0.5).view(np.uint32))
            fixed = I.encode(full_shape=True, **fields)
            assert I.decode(fixed, full_shape=True) == fields
            patches.append(dict(pc=pc, field="imm1", production=0, gate=fields["imm1"],
                                reason="production PC30 multiplies scores by imm1=0 (hdc_replay_v41 placeholder)"))
            w = fixed
        out.append(w)
    out.append(words[END_PC])
    return out, patches


def expected(rng):
    job = A.random_job(rng, H, D, T, T, "coarse")
    assert np.all(job.fmt == 0)
    sc, _ = job.expected()                                      # [H, T] q.k, csum over D
    assert np.all(np.isfinite(sc))
    scaled = G.mul(sc, F(512 ** -0.5))
    maxima = scaled.max(axis=1)
    exps = G.exp(G.add(scaled, G.neg(maxima[:, None])))
    sums = V.csum(exps)
    sink = (np.arange(H, dtype=F) / F(16) - F(0.5)).astype(F)
    den = G.add(G.exp(G.add(sink, G.neg(maxima))), sums)
    p = G.to_bf16(exps)
    pjob = A.Job(job.q, job.fmt, job.codes, job.scales, p, "live p")
    _, acc = pjob.expected()                                    # [H, D] bf16(p).v, csum over T rows
    out = G.to_bf16(V.div(acc, den[:, None]))
    return job, dict(scores=sc, scaled=scaled, maxima=maxima, exps=exps, sums=sums, sink=sink, den=den,
                     acc=acc, out=out)


def sparse_hex(path: Path, regions: dict, width_hex: int):
    with path.open("w") as f:
        for base, words in sorted(regions.items()):
            f.write(f"@{base:x}\n")
            for w in words:
                f.write(f"{int(w):0{width_hex}x}\n")


def prepare(out: Path, pos: int, seed: int):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    job, g = expected(rng)
    prog, patches = program_words()
    (out / "prog.hex").write_text("".join(f"{w:0{I.FULL_INSTR_BITS // 4}x}\n" for w in prog))
    # vector memory: q heads hh at Q_BASE + hh*512 (xcs 4096 per group of 8, xjs 512)
    qbits = C.fbits(job.q.astype(F)).reshape(-1)
    sparse_hex(out / "vm_init.hex", {Q_BASE: qbits}, 8)
    # constant ROM low word: the per-head sink
    sparse_hex(out / "crom.hex", {SINK_CROM: [int(b) for b in C.fbits(g["sink"])]}, 16)
    # HBM window ring: rows pos-127 .. pos, slot = row mod 128, sector slot*17 + g (codes), +16 (scales)
    first = pos - (T - 1)
    ring = [0] * (128 * PITCH)
    for t in range(T):
        row = first + t
        slot = row % 128
        word = A.row_word(0, job.codes[t], job.scales[t])
        scales = 0
        for grp in range(16):
            blk = (word >> (265 * grp)) & ((1 << 265) - 1)
            assert blk >> 264 == 0
            ring[slot * PITCH + grp] = blk & ((1 << 256) - 1)
            scales |= (blk >> 256) << (8 * grp)
        ring[slot * PITCH + 16] = scales
    (out / "hbm_window.hex").write_text("".join(f"{w:064x}\n" for w in ring))
    # expected whole-VM regions (everything else stays as initialised)
    s_region = np.zeros(H * S_STRIDE, dtype=np.uint32)
    for h in range(H):
        s_region[h * S_STRIDE:h * S_STRIDE + T] = C.fbits(g["exps"][h])
    exp_regions = {Q_BASE: qbits, S_BASE: s_region, M_BASE: C.fbits(g["maxima"]), Z_BASE: C.fbits(g["sums"]),
                   DEN_BASE: C.fbits(g["den"]), ACC_BASE: C.fbits(g["out"]).reshape(-1)}
    sparse_hex(out / "expect_vm.hex", exp_regions, 8)
    # intermediate check points (the bench also records them live)
    sparse_hex(out / "expect_scores.hex", {0: C.fbits(g["scores"]).reshape(-1)}, 8)
    sparse_hex(out / "expect_acc.hex", {0: C.fbits(g["acc"]).reshape(-1)}, 8)
    meta = dict(pos=pos, first_row=first, seed=seed, heads=H, head_dim=D, rows=T,
                program_sha256=sha(PROGRAM), pcs=list(PCS), end_pc=END_PC, patches=patches,
                sink="float32(h/16 - 0.5)", vm_regions={k: int(v) for k, v in dict(
                    q=Q_BASE, scores=S_BASE, maxima=M_BASE, sums=Z_BASE, den=DEN_BASE, out=ACC_BASE).items()},
                images={p.name: sha(p) for p in sorted(out.glob("*.hex"))},
                golden_sources={str(p.relative_to(ROOT)): sha(p) for p in (
                    Path(__file__), ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py",
                    ROOT / "tools/rtl_hdc_v41x_attn_campaign.py", ROOT / "tools/hdc_isa_v41.py", PROGRAM)})
    (out / "prepare.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in ("pos", "first_row", "patches")}, indent=1))


RTL = ["rtl/chip/ot_chip_v41x_die.sv", "rtl/chip/ot_chip_v41x_tile.sv", "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec.sv",
       "rtl/chip/ot_chip_v41x_window_attn_source.sv", "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
       "rtl/chip/ot_chip_v41x_window_refill_schedule.sv", "rtl/chip/ot_chip_v41x_window_retention.sv",
       "rtl/chip/ot_chip_v41x_window_row_codec.sv", "rtl/chip/ot_chip_v41x_window_stage4.sv",
       "rtl/chip/ot_chip_v41x_window_stream.sv", "rtl/chip/ot_chip_v41x_attn_row_merge.sv",
       "rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
       "rtl/chip/ot_chip_v41x_hbm3e_phy.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
       "rtl/test/tb_v41_l0_live_chain.sv", "rtl/test/tb_v41_l0_live_chain_harness.cpp",
       "tools/v41_l0_live_chain_build.sh", "tools/v41_l0_live_chain_files.txt"]
PC_NAME = {24: "scores", 30: "max", 31: "exp_sum", 32: "pv", 33: "sink_den", 34: "divide"}


def parse(log: str) -> dict:
    kv = lambda line: {k: (int(v) if re.fullmatch(r"-?\d+", v) else v) for k, v in re.findall(r"(\w+)=(\S+)", line)}
    issues = [kv(l) for l in log.splitlines() if l.startswith("ISSUE ")]
    units = [kv(l) for l in log.splitlines() if l.startswith("UNIT ")]
    one = lambda tag: next((kv(l) for l in log.splitlines() if l.startswith(tag + " ")), None)
    bad = [l for l in log.splitlines() if l.startswith("VMBAD")]
    top = one("L0LIVE")
    verdict = "pass" if "\nPASS" in "\n" + log and top and top["vm_mismatch"] == 0 else "fail"
    # phases: an op runs from its issue to the end of the unit busy interval that contains its issue
    phases = []
    for i, iss in enumerate(issues):
        u = {1: 0, 2: 1}.get(iss["unit"], iss["unit"] - 1)
        end = next((x["end"] for x in units if x["u"] == u and x["start"] <= iss["cyc"] + 2 and x["end"] > iss["cyc"]), None)
        pc = PCS[i] if i < len(PCS) else None
        phases.append(dict(pc=pc, op=PC_NAME.get(pc), issue_cycle=iss["cyc"], done_cycle=end,
                           busy_cycles=None if end is None else end - iss["cyc"]))
    return dict(verdict=verdict, summary=top, window=one("WIN"), stalls=one("STALL"), phases=phases,
                vm_mismatch_examples=bad[:12], issues=issues, unit_intervals=units)


def record(out: Path, logp: Path, config: str, rec: Path, params: dict):
    meta = json.loads((out / "prepare.json").read_text())
    res = parse(logp.read_text())
    case = dict(config=config, parameters=params, log_sha256=sha(logp), vectors=meta, **res)
    data = json.loads(rec.read_text()) if rec.exists() else dict(
        schema="opentallas.rtl.v41_l0_live_chain.v1",
        scope=("Actual production L0 attention program words (PC24,30-34,END; PC30 imm1 patched, see "
               "program_defects) executed by the V4.1 layer die top at FULL_SHAPE in one Verilator process: HBM "
               "WINDOW source (bounded refill credits, retention) -> packed stage -> attention engine -> SU -> "
               "VM, bit-exact against the golden over the whole vector memory. Synthetic golden-consistent "
               "window/q/sink; as-built stand-ins for units the slice never issues (HE, ME weight, index, "
               "select, Engram). Not a layer, not a token, no physical timing."),
        program_defects=[dict(pc=30, field="imm1", production_value=0, required=f"float32(512**-0.5)",
                              source="tools/hdc_replay_v41.py emits imm1=0 placeholder for the softmax scale; "
                                     "results/rtl/hdc_v41x_fullshape_l0_program.hex inherits it")],
        cases=[])
    data["cases"].append(case)
    data["source_sha256"] = {r: sha(ROOT / r) for r in RTL if (ROOT / r).exists()}
    data["status"] = "pass" if data["cases"] and all(c["verdict"] == "pass" for c in data["cases"]) else "fail"
    rec.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(dict(config=config, verdict=res["verdict"], summary=res["summary"], window=res["window"],
                          stalls=res["stalls"], phases=res["phases"]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("prepare", "record"))
    ap.add_argument("--log", type=Path)
    ap.add_argument("--config", default="credits8_ii1_retain")
    ap.add_argument("--param", action="append", default=[], help="NAME=VALUE bench parameter, recorded")
    ap.add_argument("--record", type=Path, default=ROOT / "results/rtl/v41_l0_live_chain.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pos", type=int, default=127)
    ap.add_argument("--seed", type=int, default=20260929)
    a = ap.parse_args()
    if a.step == "prepare":
        prepare(a.out.resolve(), a.pos, a.seed)
    else:
        record(a.out.resolve(), a.log, a.config, a.record,
               dict(x.split("=", 1) for x in a.param))


if __name__ == "__main__":
    main()
