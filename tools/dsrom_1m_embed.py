#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) 1M token: the 'embed' node (embedding row read + 4-copy expand) measured in
RTL, replacing the model's SU_BASE + 2 ns (tools/decode_critical_path.py) (owner measurement rule 2026-10-04).

Home (results/quality/w16_dsrom_embedding_head_home_20261001/contract.json): the BF16 table is split in four vocab
quarters, one per TP4 rank; the token's owner rank (token // 32,320) holds its row as 320 consecutive 274-bit ROM
words (16 BF16 lanes a word) inside one 4,096-word bank, reads it at one word a cycle and sends it to the four
ranks; every rank expands it into the 4-copy residual.  Measured, at the real token (16,754 at position
1,048,575; L00 h_in = 4 copies of its row, checked bit for bit):

  rom     rtl/dsrom_sys/ot_dsrom_embed_row_reader.sv on the ASAP7 ROM macro model (ot_rom_8192x274_m8, the row
          personalised through the via map), start -> last word out, every word checked (1.2 GHz).
  wire    the S81 floorplan wire stages of one field phase (field.json L0.attn.a_proj wire_stage_cycles_s81_floorplan:
          VM root -> farthest cluster and back), the address out and the row back.
  bcast   the owner -> 4 ranks transfer on the TP4 collective RTL (tb_w15b_v41_tp4 S81 config of
          tools/dsrom_1m_links.py: U_WIRE 34, X_WIRE 45, 1.2 GHz): an all_gather of 160 64-B words a rank
          (40,960 B), whose per-rank traffic equals the owner's 10,240-B row to each of 3 peers (the other ranks'
          contributions ride the other links; an upper bound on a one-source broadcast), golden-checked.
  expand  the 4-copy expand of the row into the residual on the stream unit (ot_hdc_v41x_vec N1024/M256, wired
          BCAST 22 / RET 15, 0.9 GHz), checked against L00 h_in.
  embed = rom + wire + bcast + expand (serial; the as-built reader has no cut-through into the link).

    python3 tools/dsrom_1m_embed.py golden --out DIR             # local: checkpoint row, via map, SU case
    python3 tools/dsrom_1m_embed.py rom    --out DIR --work W    # compute host
    python3 tools/dsrom_1m_embed.py bcast  --out DIR --work W [--jobs 16]
    python3 tools/dsrom_1m_embed.py expand --out DIR --work W    # stream unit, unit + wired
    python3 tools/dsrom_1m_embed.py record --out DIR [--record results/rtl/dsrom_1m_allmeasured_20261004/embed.json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F = np.float32
CTX = 1048576
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
VQ = 129280 // 4          # vocab quarter a rank
WORDS = 320               # 5,120 BF16 / 16 lanes
BANK = 4096
CLK, SLOW = 1.2e9, 0.9e9
RTL = [ROOT / "rtl/dsrom_sys/ot_dsrom_embed_row_reader.sv",
       ROOT / "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v"]
TB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_1m_embed.sv"
FIELD = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/field.json"
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/embed.json"
CASES = "su_cases_embed.pkl"
VARIANTS = {"unit": (0, 0), "wired": (6 + 16, 15)}
BCAST_WPR = WORDS * 32 // 64          # 10,240 B = 160 64-B words


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verilator():
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    return str(vl) if vl.exists() else "verilator"


def word_of(u16, w):
    """BF16 word w = h*8 + b: lane l holds element h*128 + l*8 + b (tools/rtl_v41_rom_array.py bf16_word)."""
    h, b = divmod(w, 8)
    return [int(u16[h * 128 + l * 8 + b]) for l in range(16)]


def cmd_golden(a):
    import rtl_v41_fullshape_layer_campaign as LC
    import dshbm_baseline_measure as B
    import hdc_golden as G
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    g = json.loads((GOLD / f"golden_ctx{CTX}_0-39.json").read_text())
    tok = int(g["token"])
    ck = LC.Checkpoint()
    row = np.asarray(ck.rows("embed.weight", np.array([tok])), F).reshape(-1)
    z = np.load(GOLD / f"ctx{CTX}_L00.npz")
    h = z["h_in"].astype(F)
    checks = dict(token_is_last_history=tok == int(g["history"][-1]),
                  h_in_is_4_copies=all(np.array_equal(row.view(np.uint32), h[j].view(np.uint32)) for j in range(4)),
                  row_is_bf16=bool(np.all(row.view(np.uint32) & 0xFFFF == 0)))
    owner, local = divmod(tok, VQ)
    addr = local * WORDS
    bank, off = divmod(addr, BANK)
    assert off + WORDS <= BANK, "row crosses a bank"
    u16 = (row.view(np.uint32) >> 16).astype(np.uint32)
    words = {off + w: sum(v << (16 * l) for l, v in enumerate(word_of(u16, w))) for w in range(WORDS)}
    import rtl_v41_rom_array as RA
    RA.viamap(words, out / "embed.viamap.hex")
    with open(out / "embed_exp.mem", "w") as f:
        for w in range(WORDS):
            f.write("".join(f"{v << 16:08x}" for v in reversed(word_of(u16, w))) + "\n")
    # the 4-copy expand on the stream unit: the received row (VM) -> the residual's 4 copies
    c = B.Chain("embed.expand", VC)
    c.meta = dict(layer="E", fn="embed_expand")
    R = c.vm(row)
    H = c.buf(4 * 5120)
    c.op(nout=4, nin=5120, abase=R, aso=0, asi=1, obase=H, oso=5120, osi=1)
    c.check("4-copy residual = L00 h_in", H, h.reshape(-1))
    c.meta["nodes"] = [dict(node="embed.expand", op=0, event="write")]
    cases = [dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                  checks=[(lab, ad, G.bits(w).astype(np.uint32), "golden") for lab, ad, w, _k in c.checks])]
    (out / CASES).write_bytes(pickle.dumps(dict(cases=cases, snapshots_sha256=sha(GOLD / f"ctx{CTX}_L00.npz"))))
    res = dict(status="pass" if all(checks.values()) else "fail", token=tok, owner_rank=owner, local_row=local,
               bank=bank, bank_word=off, checks=checks, row_sha256=hashlib.sha256(row.tobytes()).hexdigest(),
               shard_sha256=sha(GOLD / f"ctx{CTX}_L00.npz"), checkpoint=str(LC.HF), generated_utc=now())
    (out / "embed_golden.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))
    return 0 if res["status"] == "pass" else 1


def cmd_rom(a):
    out, work = Path(a.out), Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    gold = json.loads((out / "embed_golden.json").read_text())
    obj = work / "embed_obj"
    subprocess.run([verilator(), "--binary", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_dsrom_1m_embed",
                    "-Mdir", str(obj), *map(str, RTL), str(TB)], check=True, capture_output=True)
    r = subprocess.run([str(obj / "Vtb_dsrom_1m_embed"), f"+BASE={gold['bank_word']}"], cwd=out, capture_output=True,
                       text=True).stdout
    m = re.search(r"EMB start=(\d+) first=(\d+) last=(\d+) words=(\d+) errors=(\d+)", r)
    t0, tf, tl, n, err = map(int, m.groups())
    res = dict(start=t0, first=tf, last=tl, words=n, errors=err, cycles=tl - t0 + 1, first_word_cycles=tf - t0 + 1,
               exact=bool("PASS" in r and err == 0 and n == WORDS), clock_hz=CLK, stdout=r[-400:],
               rtl_sha256={str(p.relative_to(ROOT)): sha(p) for p in (*RTL, TB)},
               inputs_sha256={p: sha(out / p) for p in ("embed.viamap.hex", "embed_exp.mem")})
    (out / "embed_rom.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("cycles", "first_word_cycles", "exact")}))
    return 0 if res["exact"] else 1


def cmd_bcast(a):
    import dsrom_1m_links as LK
    out, work = Path(a.out), Path(a.work)
    op = ("embed.bcast", "all_gather", BCAST_WPR * LK.RANKS * LK.WORD_B)
    assert LK.words_of(op[1], op[2]) == BCAST_WPR
    LK.S81_COLL = [op]
    LK.S81_OPS = [op] * LK.NOPS
    r = LK.cmd_coll(argparse.Namespace(work=str(work), configs="s81_r0d1024", ncal=a.ncal, nmeas=a.nmeas,
                                       jobs=a.jobs))
    c = r["configs"]["s81_r0d1024"]
    res = dict(op=op, by_collective=c["by_collective"], all_runs_passed=c["all_runs_passed"],
               simulator=r["simulator"], sources=r.get("sources"), fixture=r["fixture"], wall_s=c.get("wall_s"),
               config=LK.COLL_CONFIGS["s81_r0d1024"][1])
    (out / "embed_bcast.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(c["by_collective"]))
    return 0 if c["all_runs_passed"] else 1


def cmd_expand(a):
    import dshbm_baseline_measure as B
    rc = 0
    for v, (bc, rt) in VARIANTS.items():
        rc |= B.cmd_su_run(argparse.Namespace(out=a.out, cases=CASES, bcast=bc, ret=rt, mlat=5, alat=4, n=1024,
                                              m=256, fp="dpi_beh", work=a.work))
    return rc


def cmd_record(a):
    out = Path(a.out)
    gold = json.loads((out / "embed_golden.json").read_text())
    rom = json.loads((out / "embed_rom.json").read_text())
    bc = json.loads((out / "embed_bcast.json").read_text())
    field = json.loads(FIELD.read_text())
    fn = next(x for x in field["nodes"] if x["node"] == "L0.attn.a_proj")
    wire = fn["wire_stage_cycles_s81_floorplan"] // max(1, len(fn["phases"]))
    exp = {}
    for v, (b, r) in VARIANTS.items():
        j = json.loads((out / f"su_N1024_M256_b{b}r{r}m5a4_dpi_beh_{Path(CASES).stem}.json").read_text())
        ch = j["chains"][0]
        po = ch["per_op"][0]
        exp[v] = dict(cycles=po["last_write"], exact=ch["exact"], checks=ch["checks"], status=j["status"])
    bco = bc["by_collective"]["embed.bcast"]
    parts = dict(rom=dict(cycles=rom["cycles"], clock_hz=CLK, us=rom["cycles"] / CLK * 1e6, exact=rom["exact"]),
                 wire=dict(cycles=wire, clock_hz=CLK, us=wire / CLK * 1e6,
                           source="field.json L0.attn.a_proj wire_stage_cycles_s81_floorplan (one phase): routed S81 "
                                  "geometry, VM root -> farthest cluster -> VM"),
                 bcast=dict(cycles=bco["cycles"], clock_hz=1e3 / 0.8333, us=bco["us"], exact=bco["exact"],
                            op=bc["op"], words_per_rank=bco["words_per_rank"]),
                 expand=dict(cycles=exp["wired"]["cycles"], clock_hz=SLOW, us=exp["wired"]["cycles"] / SLOW * 1e6,
                             unit_cycles=exp["unit"]["cycles"], exact=exp["wired"]["exact"] and exp["unit"]["exact"]))
    us = sum(p["us"] for p in parts.values())
    exact = gold["status"] == "pass" and all(p.get("exact", True) for p in parts.values())
    rec = dict(schema="opentallas.dsrom-1m.embed.v1", generated_utc=now(), source_commit=a.source_commit,
               context=CTX, position=CTX - 1, exact=exact,
               nodes={"embed": dict(us=round(us, 5), exact=exact, parts=parts,
                                    source=f"owner-rank ROM row read {rom['cycles']} cyc (ot_dsrom_embed_row_reader on "
                                           f"the ROM macro, 320 words) + S81 floorplan wire {wire} cyc + TP4 owner->4 "
                                           f"ranks (all_gather 160 words/rank on tb_w15b_v41_tp4 S81) {bco['cycles']} "
                                           f"cyc + SU 4-copy expand wired {exp['wired']['cycles']} slow cyc; serial")},
               model_us=0.032, golden_check=gold, rom=rom, bcast=bc, expand=exp,
               tool_sha256={"tools/dsrom_1m_embed.py": sha(ROOT / "tools/dsrom_1m_embed.py")})
    Path(a.record).write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps(dict(us=round(us, 4), parts={k: round(v["us"], 4) for k, v in parts.items()}, exact=exact)))
    return 0 if exact else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("golden", "rom", "bcast", "expand", "record"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--ncal", type=int, default=8)
    ap.add_argument("--nmeas", type=int, default=6)
    ap.add_argument("--source-commit", default=None)
    ap.add_argument("--record", default=str(REC))
    a = ap.parse_args()
    return dict(golden=cmd_golden, rom=cmd_rom, bcast=cmd_bcast, expand=cmd_expand, record=cmd_record)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
