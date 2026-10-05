#!/usr/bin/env python3
"""Row-striped ROM bank map for every DeepSeek-V4.1 layer die (W10 build item 1 of docs/MICROARCH_MODEL.md).

    python3 tools/v41_rom_striped_bankmap.py --snapshot <HF snapshot dba1be0a...> \
        --output results/uarch/v41_rom_striped_bankmap.json

The microarchitecture model's V4.1 ROM proposal (tools/uarch_model.py PRESETS["proposal"]) stripes the rows of
every matrix over all ROM macros of a die, a macro owning WHOLE output rows, BF16 matrices on a 4,096-macro
subset.  This tool binds every weight matrix of every layer die to (macro, address range, word order) under
exactly that rule and measures what it implies:

* binding: every output row of every matrix goes to one macro; within a macro a matrix's rows are stored
  k-outer (address = base + block * rows_here + row_index), so all elements consume the same x block;
* exact-once: every (matrix, row) is bound once and every macro's address intervals are disjoint and inside
  the 8,192-word depth, so every weight word appears exactly once;
* per-phase read cycles: for each dependent weight phase of the model's DAG (a_proj, wq_b, cmp.wk, wo_a,
  wo_b, router, shared_gu, experts_gu, down) the cycles are the most words any one macro must read in that
  phase (one word per macro per cycle).  Routed-expert phases are data-dependent: reported for the model's
  six active experts per die-layer (mean over draws and worst case) and for the true expected occupancy.

The per-phase cycles are compared with the model's t_read.  A mismatch is RECORDED, not tuned away.

Placement (deterministic, documented so an RTL or physical flow can regenerate it):
* dense phases: rows sorted by words-per-row, each to the macro with the fewest words so far in that phase,
  ties to the macro with most free depth then lowest id (longest-processing-time first);
* BF16 matrices: only on the BF16 macro subset, macro ids floor(i * N / NB) for i < NB (spread uniformly);
* routed experts: expert j of the die (id order) places its w1|w3 rows on macros (j mod T_gu) * 1152 + r,
  T_gu = floor(N / 1152), and its w2 rows on (j mod T_dn) * 1280 + r, T_dn = floor(N / 1280): consecutive ids
  cycle through aligned tiles, so a collision needs two active experts in the same tile;
* hc_*_fn (FP32, the model's hub), pooled constants and Engram spill rows fill remaining depth (capacity only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_die_macromap as M  # noqa: E402

DEPTH = 8192
import uarch_model as U  # noqa: E402

# macros carrying BF16 lanes: read from the model (PRESETS["proposal"].bf16_stripe_macros), never a literal;
# None there means every macro carries BF16 (W10 BF16_PAIR: BF16 on the standard pair)
BF16_MACROS = U.PRESETS["proposal"].get("bf16_stripe_macros")


def bf16_count(n: int) -> int:
    return n if BF16_MACROS is None else min(BF16_MACROS, n)
WPW = {"fp4": 64, "fp8": 32, "bf16": 16}
EXPERT = {"w1": (576, 5120), "w3": (576, 5120), "w2": (1280, 2304)}   # rank quarter (rows, K)
TOPK, N_EXPERTS = 6, 384
# the model's node for each dense tensor (tools/decode_critical_path.py a_proj fuses wq_a|wkv|weights_proj|
# compressor wkv,wgate; tools/arch_budget_v41.py cmp.wk is indexer.wk)
PHASE = {
    "attn.wq_a.weight": "a_proj", "attn.wkv.weight": "a_proj", "attn.indexer.weights_proj.weight": "a_proj",
    "attn.compressor.wkv.weight": "a_proj", "attn.compressor.wgate.weight": "a_proj",
    "attn.wq_b.weight": "wq_b", "attn.indexer.wq_b.weight": "wq_b", "attn.indexer.wk.weight": "cmp.wk",
    "attn.wo_a.weight": "wo_a", "attn.wo_b.weight": "wo_b", "ffn.gate.weight": "router",
    "ffn.shared_experts.w1.weight": "shared_gu", "ffn.shared_experts.w3.weight": "shared_gu",
    "ffn.shared_experts.w2.weight": "down",
}
PHASES = ("a_proj", "wq_b", "cmp.wk", "wo_a", "wo_b", "router", "shared_gu", "experts_gu", "down")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bf16_set(n: int, nb: int) -> np.ndarray:
    return np.unique((np.arange(nb, dtype=np.int64) * n) // nb)


def dense_matrices(entries: list[dict], layer: int) -> list[dict]:
    """The striped weight matrices of one dense layer, from W1's rank-local reservations."""
    out = []
    for e in entries:
        local = e["tensor"].split(f"layers.{layer}.")[1]
        if local not in PHASE:
            continue
        if e["dtype"] == "F8_E4M3":
            rows, K = e["rank_shape"]
            fmt = "bf16" if local == "attn.wo_a.weight" else "fp8"
        else:
            assert e["dtype"] == "BF16", e
            rows, K = e["source_shape"]
            if e["split"] == "program_declared_output_row_quarter":
                rows //= 4
            fmt = "bf16"
        out.append(dict(tensor=e["tensor"], phase=PHASE[local], fmt=fmt, rows=rows, K=K,
                        words_per_row=math.ceil(K / WPW[fmt]), split=e["split"]))
    return out


class Die:
    def __init__(self, n: int, nb: int):
        self.n = n
        self.bf = bf16_set(n, nb)
        self.fill = np.zeros(n, dtype=np.int64)          # next free address per macro
        self.bind = []                                   # (tensor, row0, rows, macro array, base array, wpr)

    def place_rows(self, tensor, macros, wpr):
        """Rows 0..len(macros)-1 of `tensor` to `macros` (one row each here, k-outer inside the macro)."""
        base = self.fill[macros].copy()
        # a macro given several rows of one tensor stores them k-outer: base + block * rows_here + i
        uniq, cnt = np.unique(macros, return_counts=True)
        np.add.at(self.fill, uniq, cnt * wpr)
        self.bind.append(dict(tensor=tensor, macros=macros, base=base, wpr=wpr))


def word_addresses(b: dict) -> tuple[np.ndarray, np.ndarray]:
    """(macro, address) of every word of one bound tensor, shape (rows, words_per_row): k-outer, so the
    word of block k of the i-th row held by a macro sits at base + k * rows_here + i."""
    m = b["macros"]
    order = np.argsort(m, kind="stable")
    ms = m[order]
    first = np.r_[0, np.flatnonzero(ms[1:] != ms[:-1]) + 1]
    cnt = np.diff(np.r_[first, len(ms)])
    idx = np.empty(len(m), dtype=np.int64)
    here = np.empty(len(m), dtype=np.int64)
    idx[order] = np.arange(len(ms)) - np.repeat(first, cnt)
    here[order] = np.repeat(cnt, cnt)
    base0 = np.empty(len(m), dtype=np.int64)
    base0[order] = np.repeat(b["base"][order][first], cnt)
    k = np.arange(b["wpr"])[None, :]
    return np.broadcast_to(m[:, None], (len(m), b["wpr"])), base0[:, None] + k * here[:, None] + idx[:, None]


def place_dense(die: Die, mats: list[dict]):
    """LPT placement of one dense layer's phases; returns per-phase per-macro word loads."""
    loads = {}
    for ph in PHASES:
        ms = [m for m in mats if m["phase"] == ph]
        if not ms:
            continue
        load = np.zeros(die.n, dtype=np.int64)
        for fmt_bf in (True, False):
            for m in sorted([m for m in ms if (m["fmt"] == "bf16") == fmt_bf], key=lambda m: -m["words_per_row"]):
                allowed = die.bf if fmt_bf else np.arange(die.n)
                rows = m["rows"]
                macros = np.empty(rows, dtype=np.int64)
                got = 0
                while got < rows:
                    # fewest phase words, then most free depth, then lowest id
                    order = np.lexsort((allowed, die.fill[allowed], load[allowed]))
                    lvl = load[allowed[order]]
                    k = min(rows - got, int(np.searchsorted(lvl, lvl[0], side="right")))
                    take = allowed[order[:k]]           # only the macros at the current minimum phase load
                    macros[got:got + len(take)] = take
                    load[take] += m["words_per_row"]
                    got += len(take)
                die.place_rows(m["tensor"], macros, m["words_per_row"])
        loads[ph] = load
    return loads


def place_experts(die: Die, layer_ranges: list[dict]):
    """Tile each expert's gu and down rows over the field; returns per-layer expert offset tables."""
    gu_rows, dn_rows = EXPERT["w1"][0] * 2, EXPERT["w2"][0]
    gu_wpr, dn_wpr = EXPERT["w1"][1] // 64, EXPERT["w2"][1] // 64
    tables = []
    j = 0
    for r in layer_ranges:
        ids = list(range(r["first"], r["last"] + 1))
        gu_off, dn_off = [], []
        for e in ids:
            go = (j % max(1, die.n // gu_rows)) * gu_rows      # aligned tiles: T = floor(N / rows)
            do = (j % max(1, die.n // dn_rows)) * dn_rows
            g = (go + np.arange(gu_rows)) % die.n
            d = (do + np.arange(dn_rows)) % die.n
            for fam, sl in (("w1", g[:gu_rows // 2]), ("w3", g[gu_rows // 2:])):
                die.place_rows(f"layers.{r['layer']}.ffn.experts.{e}.{fam}", sl, gu_wpr)
            die.place_rows(f"layers.{r['layer']}.ffn.experts.{e}.w2", d, dn_wpr)
            gu_off.append(go)
            dn_off.append(do)
            j += 1
        tables.append(dict(layer=r["layer"], ids=ids, gu_off=np.array(gu_off), dn_off=np.array(dn_off)))
    return tables


def expert_cycles(n, t, active_idx, shared_down_load, which):
    rows, wpr = (EXPERT["w1"][0] * 2, EXPERT["w1"][1] // 64) if which == "gu" else (EXPERT["w2"][0], EXPERT["w2"][1] // 64)
    load = np.zeros(n, dtype=np.int64) if shared_down_load is None else shared_down_load.copy()
    off = t["gu_off"] if which == "gu" else t["dn_off"]
    for i in active_idx:
        load[(off[i] + np.arange(rows)) % n] += wpr
    return int(load.max())


def expert_stats(n, t, shared_down, rng, draws):
    """Cycles of experts_gu and down for (a) the model's 6 active experts on this die-layer and (b) the true
    occupancy: 6 of 384 drawn, those owned here."""
    ne = len(t["ids"])
    out = {}
    for mode in ("model_six", "true_occupancy"):
        gu, dn, k = [], [], []
        for _ in range(draws):
            if mode == "model_six":
                act = rng.choice(ne, size=min(TOPK, ne), replace=False)
            else:
                pick = rng.choice(N_EXPERTS, size=TOPK, replace=False)
                act = [i for i, e in enumerate(t["ids"]) if e in set(pick.tolist())]
            k.append(len(act))
            gu.append(expert_cycles(n, t, act, None, "gu"))
            dn.append(expert_cycles(n, t, act, shared_down, "dn"))
        out[mode] = dict(active_mean=round(float(np.mean(k)), 3),
                         experts_gu=dict(mean=round(float(np.mean(gu)), 2), max_seen=int(max(gu)),
                                         p_collision_free=round(float(np.mean(np.array(gu) <= EXPERT["w1"][1] // 64)), 3)),
                         down=dict(mean=round(float(np.mean(dn)), 2), max_seen=int(max(dn))))
    # adversarial worst case: six experts sharing one gu tile (possible when ne >= 6 * tiles)
    tiles_gu = n // (EXPERT["w1"][0] * 2)
    out["worst_case"] = dict(experts_gu=min(TOPK, math.ceil(ne / max(1, tiles_gu))) * (EXPERT["w1"][1] // 64),
                             down=min(TOPK, math.ceil(ne / max(1, n // EXPERT["w2"][0]))) * (EXPERT["w2"][1] // 64)
                             + int(shared_down.max()))
    return out


def check_exact_once(die: Die, mats_all: list[tuple[str, int, int]]):
    """Every (tensor, row) bound once; every macro's [base, base + wpr) intervals disjoint and < DEPTH."""
    seen = {}
    starts, ends, mids = [], [], []
    for b in die.bind:
        seen[b["tensor"]] = seen.get(b["tensor"], 0) + len(b["macros"])
        # rows of one tensor on one macro share a k-outer region [base0, base0 + rows_here * wpr)
        u, first, cnt = np.unique(b["macros"], return_index=True, return_counts=True)
        mids.append(u)
        starts.append(b["base"][first])
        ends.append(b["base"][first] + cnt * b["wpr"])
    for name, rows, _ in mats_all:
        assert seen.get(name) == rows, (name, seen.get(name), rows)
    assert len(seen) == len(mats_all)
    m, s, e = np.concatenate(mids), np.concatenate(starts), np.concatenate(ends)
    o = np.lexsort((s, m))
    m, s, e = m[o], s[o], e[o]
    same = m[1:] == m[:-1]
    assert np.all(s[1:][same] >= e[:-1][same]), "overlapping address intervals"
    return int(e.max()), int(sum(r * w for _, r, w in mats_all))


def model_t_read():
    rec = json.loads((ROOT / "results/uarch/v41_rom.json").read_text())
    row = next(r for r in rec["rows"] if r["design"] == "proposal")
    return {v["key"]: v["t_read"] for v in row["layer20_matvecs"].values()}, row["params"]


def derive(snapshot: Path, draws: int, seed: int, only=None, keep=None):
    meta = M.Headers(snapshot)
    owners = json.loads(M.OWNERS.read_text())
    macromap = M.derive(snapshot, compact_woa=False)
    by_die = {d["die"]: d for d in macromap["layer_dies"]}
    t_model, params = model_t_read()
    assert params["bf16_stripe_macros"] == BF16_MACROS and params["mapping"] == "striped"
    rng = np.random.default_rng(seed)
    dies = []
    for stage in range(owners["stage_count"]):
        dense_layers = [o["layer"] for o in owners["layer_owners"] if o["dense_owner_stage"] == stage]
        ranges = [dict(layer=o["layer"], first=r["expert_ids"][0], last=r["expert_ids"][1])
                  for o in owners["layer_owners"] for r in o["routed_expert_candidate_owners"] if r["stage"] == stage]
        dense = {L: M.dense_entries(meta, L, False) for L in dense_layers}
        for rank in range(4):
            name = f"layer_s{stage:02d}_r{rank}"
            if only and name not in only:
                continue
            w1 = by_die[name]
            n = w1["macros"][M.WIDE]                     # the die's macro count in W1's (contiguous) map
            die = Die(n, bf16_count(n))
            phase_loads, mats_all = {}, []
            for L in dense_layers:
                mats = dense_matrices(dense[L], L)
                phase_loads[L] = place_dense(die, mats)
                mats_all += [(m["tensor"], m["rows"], m["words_per_row"]) for m in mats]
            tables = place_experts(die, ranges)
            for t in tables:
                for e in t["ids"]:
                    for fam in ("w1", "w3", "w2"):
                        mats_all.append((f"layers.{t['layer']}.ffn.experts.{e}.{fam}", EXPERT[fam][0],
                                         EXPERT[fam][1] // 64))
            # capacity-only occupants: hc fn (hub), pooled constants, Engram spill (W1 counts)
            grp = w1["macros_by_group"]
            other_words = (grp.get("VM.CONSTANT_HE", {}).get(M.WIDE, 0) + grp["ENGRAM.spill"][M.WIDE]) * DEPTH
            max_addr, weight_words = check_exact_once(die, mats_all)
            free = int((DEPTH - die.fill).sum())
            per_layer = []
            for L in dense_layers:
                pl = phase_loads[L]
                meas = {ph: int(pl[ph].max()) for ph in pl}
                per_layer.append(dict(layer=L, dense_phase_cycles=meas))
            ex = []
            for t in tables:
                # a die owning this layer's dense part adds the shared expert's w2 to the down phase
                sd = phase_loads[t["layer"]].get("down") if t["layer"] in phase_loads else np.zeros(n, np.int64)
                ex.append(dict(layer=t["layer"], experts_owned=len(t["ids"]),
                               **expert_stats(n, t, sd, rng, draws)))
            if keep is not None:
                keep.append(die)
            dies.append(dict(die=name, stage=stage, rank=rank, macros=n, bf16_macros=len(die.bf),
                             dense_layers=dense_layers, weight_words=weight_words,
                             max_address=max_addr, capacity_ok=bool(max_addr <= DEPTH and other_words <= free),
                             other_words_capacity_only=other_words, free_words_after_weights=free,
                             dense=per_layer, experts=ex))
    return dies, t_model


def compare(dies, t_model):
    """Per-phase measured cycles against the model's t_read (the model prices the busiest die for every layer)."""
    busiest = max(dies, key=lambda d: (d["macros"], d["die"]))
    worst = {}
    for d in dies:
        for L in d["dense"]:
            for ph, c in L["dense_phase_cycles"].items():
                worst[ph] = max(worst.get(ph, 0), c)
        for e in d["experts"]:
            worst["experts_gu"] = max(worst.get("experts_gu", 0), e["model_six"]["experts_gu"]["mean"])
            worst["down"] = max(worst.get("down", 0), e["model_six"]["down"]["mean"])
    b = {}
    for L in busiest["dense"]:
        b.update(L["dense_phase_cycles"])
    for e in busiest["experts"]:
        b["experts_gu"] = max(b.get("experts_gu", 0), e["model_six"]["experts_gu"]["mean"])
        b["down"] = max(b.get("down", 0), e["model_six"]["down"]["mean"])
    rows = {ph: dict(model_t_read=t_model.get(ph), busiest_die=b.get(ph), worst_die=worst.get(ph),
                     equal=bool(b.get(ph) == t_model.get(ph)))
            for ph in PHASES}
    return busiest["die"], rows


def price(rows):
    """The model's proposal re-priced with the measured per-phase read cycles (busiest die) as t_read."""
    import copy
    import uarch_model as U
    meas = {ph: r["busiest_die"] for ph, r in rows.items() if r["busiest_die"] is not None}
    orig = U.price_matvec

    def patched(nd, name, d, clock, c):
        r = orig(nd, name, d, clock, c)
        if r is not None and r["key"] in meas:
            r["t_read_model"], r["t_read"] = r["t_read"], meas[r["key"]]
            r["issue"] = max(r["t_read"], r["t_mac"], r["t_x"], r["t_ret"])
        return r
    d = copy.deepcopy(U.PRESETS["proposal"])
    base = U.evaluate(d)
    U.price_matvec = patched
    try:
        got = U.evaluate(d)
    finally:
        U.price_matvec = orig
    return dict(model_tokens_s=round(base["tokens_s"], 1), measured_bankmap_tokens_s=round(got["tokens_s"], 1),
                measured_T_us=round(got["T_us"], 3), model_T_us=round(base["T_us"], 3),
                note="lm_head (BF16, not on a layer die) keeps the model's t_read")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--draws", type=int, default=400)
    p.add_argument("--seed", type=int, default=20260929)
    p.add_argument("--die", action="append", help="only these dies (tests)")
    a = p.parse_args(argv)
    dies, t_model = derive(a.snapshot, a.draws, a.seed, a.die)
    bus, rows = compare(dies, t_model)
    ok = all(r["equal"] for r in rows.values())
    rec = dict(
        schema="opentallas.v41.rom_striped_bankmap.v1",
        verdict="PASS" if ok else "FAIL_model_t_read_mismatch",
        claim_boundary=("binding rule and measured per-phase read cycles under the proposal's whole-row striping; "
                        "a FAIL means the model's t_read (words / macros) is not realisable by whole-row "
                        "ownership, not that the binding is wrong"),
        rule=dict(bf16_macros=BF16_MACROS, bf16_macro_ids=("every macro" if BF16_MACROS is None else
                                                          f"floor(i * N / {BF16_MACROS}), i < {BF16_MACROS}"),
                  word_order="k-outer: address = base + block * rows_here + row_index",
                  dense="LPT per phase: fewest phase words, then most free depth, then lowest id",
                  experts="expert j (die id order): w1|w3 rows on (j mod floor(N/1152))*1152 + r, w2 rows on (j mod floor(N/1280))*1280 + r"),
        checkpoint_revision=a.snapshot.name,
        source_sha256={str(q.relative_to(ROOT)): sha(q) for q in
                       [Path(__file__).resolve(), ROOT / "tools/v41_floorplan_die_macromap.py",
                        ROOT / "tools/uarch_model.py", ROOT / "results/uarch/v41_rom.json", M.OWNERS]},
        draws=a.draws, seed=a.seed,
        busiest_die=bus, phase_cycles_vs_model=rows, priced=price(rows),
        all_capacity_ok=all(d["capacity_ok"] for d in dies),
        dies=dies)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], busiest=bus, capacity=rec["all_capacity_ok"],
                          phases=rows, priced=rec["priced"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
