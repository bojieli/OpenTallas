#!/usr/bin/env python3
"""Architecture choice for the HBM collective PROTECTED link CDC (design model, not RTL).

Problem (Codex /hbm/collective, 2026-10-07): the protected dual-clock FIFO candidate
(ot_hbm_collective_protected_cdc, W=545, AW=6 -> 64 slots) drains at II=3 read cycles
(capture -> validate -> present on ONE protected head bank), while the native PHY side
writes up to one flit a PHY edge and the switch egress holds SWCRED=256 credits that are
returned only at receive-buffer pop (downstream of the CDC).  The RX CDC write port cannot
back-pressure the PHY.  The matched-SRAM full gate still uses the original II=1 CDC.

Options compared:
  A  advertise credits C <= D so the II=3 CDC can never overflow;
  B  II=1 protected drain: three protected head banks in rotation (capture/validate/present
     overlapped), the verified W2 protected-bank semantics unchanged per bank;
  C  a deeper protected FIFO (D >= C) at II=3.

Every inequality below is checked by a cycle-accurate two-clock queue simulator (two
independent clock edge streams, Gray pointer two-flop synchronisers with a metastability
window that randomly resolves old/new, staggered cold reset entry, credit-return delay,
correctable-error repair stalls) under randomized and adversarial traffic, with negatives
that must overflow.  Usage:  python3 tools/hbm_collective_cdc_design.py [--out DIR] [--quick]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SNAP = Path("/home/ubuntu/.claude/jobs/724d7460/tmp/cdc_snapshot_1130")
SNAP_PINS = {  # the read-only snapshot this design answers (central files are untracked and evolving)
    "hbm_collective_cdc_model.py": "4828bd7efede63d963ebbd73cf0af1d48441e089287b9dabcbc3fdcb9ed76f8f",
    "collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv":
        "a4e1bda9a0ab083503462a8c755f35cbe3aa52786e455e29c66834e915463497",
    "collective_cdc_20261007/tb_protected_cdc.sv": "2ad089b349abf3d9c7441edbcf3ff6dbfb6ccfc6d6648c65e761e5c216a355d0",
}
SRC = dict(
    native="rtl/hbm_accel/collective_full_20261007/ot_hbm_collective_full_candidate.sv",
    die_entry="rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_die_entry.sv",
    reset_entry="rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv",
    clock_model="results/uarch/hbm_collective_clock_entry_20261007/model.json",
    protected_bank="rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv",
    storage_model="results/rtl/hbm_collective_full_20261007/storage_model.json",
    collectives="results/rtl/dshbm_1m_allmeasured_20261004/collectives.json",
    program="results/rtl/dshbm_baseline_measured_20261004/program.json",
    matched="results/rtl/dshbm_matched_reference_20261005/composition.json",
    sram="physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.json",
    sram64="physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.json",
)


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def load(rel):
    return json.loads((ROOT / rel).read_text())


# ----------------------------------------------------------------------------------------------
# Parameters, all from sources
# ----------------------------------------------------------------------------------------------
def params():
    cm = load(SRC["clock_model"])
    sm = load(SRC["storage_model"])
    col = load(SRC["collectives"])
    snap_model = json.loads((SNAP / "hbm_collective_cdc_20261007/model.json").read_text()) \
        if (SNAP / "hbm_collective_cdc_20261007/model.json").exists() else None
    W = 545
    words = (W + 63) // 64
    p = dict(
        W=W, secded_words=words, encoded_bits=words * 72,                 # 9 x 72 = 648
        D=64, AW=6, SWCRED=256, RXAW=8, TXAW=6, WSTG=14, NPT=8,           # die_entry / native defaults
        cdc_fifos=16,                                                    # 8 ports x (TX, RX)
        sync_stages=2,                                                   # *_sync0/_sync1 per rail
        II_candidate=3,                                                  # capture, validate, present
        head_latency_cycles=3,                                           # same 3 stages in B, overlapped
        added_read_cycles_vs_original=2,                                 # model.json head_capture_plus_validate
        ce_repair_cycles=5,                                              # W2 bank five-edge held repair
        bank_words=words + 5,                                            # data words + 5 control codes
        core_period_ps=833.333333, link_period_ps=833.333333,            # 1.2 GHz both, independent phase
        stress_read_period_ps=1024.6,                                    # snapshot tb stress clock
        clk_hz=1.2e9,
        credit_return_ns=col["budget"]["credit_return_ns"],             # 113.8 ns, sizes the 256-flit RB
        port_payload_gbps=col["port"]["payload_gbps"],
        dff_um2_per_bit=cm["area"]["non_async_dff_lower_bound_um2"] / cm["reset_entry"]["state_bits"],
        reset_release_edges=cm["reset_entry"]["synchronous_release_edges"],
        packet_sram_II=1 / sm["timing"]["sustained_dequeue_bandwidth_fraction"],
        ledger_sram_added_cycles=sm["timing"]["added_queue_latency_vs_async_head_cycles"],
    )
    if snap_model:
        assert snap_model["width"] == W and snap_model["depth"] == p["D"]
        assert snap_model["normal_timing"]["read_initiation_interval"] == p["II_candidate"]
    # local credit-loop RTT of the switch egress -> RB pop -> credit (flits at 1 per edge)
    local = p["sync_stages"] + 1 + p["head_latency_cycles"] + p["WSTG"] + 2
    p["rx_credit_rtt_cycles"] = math.ceil(p["credit_return_ns"] * 1e-9 * p["clk_hz"]) + local
    p["rx_credit_rtt_basis"] = ("credit_return_ns (labelled vendor loop that sized the 256-flit RB) x 1.2 GHz + local "
                                "sync %d + Gray reg 1 + head %d + WSTG %d + RB 2" %
                                (p["sync_stages"], p["head_latency_cycles"], p["WSTG"]))
    return p


# ----------------------------------------------------------------------------------------------
# Workload: per-token RX serialisation (port streaming at 1 flit/PHY edge) and CDC traversals
# ----------------------------------------------------------------------------------------------
def workload():
    import dshbm_1m_coll as C
    import w19_hbm_token_compose as WC
    rec = load(SRC["collectives"])
    prog = load(SRC["program"])
    out = {}
    for hub in ("matched", "ha2hub"):
        for P in (1, 6):
            ser = n = cross = 0
            mx = 0.0
            for lay in prog["layers"]:
                for op in lay["ops"]:
                    if op["kind"] not in ("all_gather", "all_reduce", "topk_merge", "kv_gather") or \
                            op["tag"].startswith(WC.OFF_PATH_COLL):
                        continue
                    for c in rec["classes"]:
                        if c["hub"] != hub or c["P"] != P:
                            continue
                        if op["kind"] == "all_reduce" and c["kind"] == "all_reduce" or \
                                op["kind"] != "all_reduce" and c["kind"] != "all_reduce" and \
                                c["flits_per_rank"] == C.gather_pf(op["bytes"], P):
                            ser += c["serialisation_cycles"]
                            cross += c["crossings"]
                            mx = max(mx, c["serialisation_cycles"])
                            n += 1
                            break
            out[f"{hub}_P{P}"] = dict(collectives=n, serialisation_cycles=round(ser, 1), crossings=cross,
                                      max_class_serialisation_cycles=mx)
    m = load(SRC["matched"])["gate"]
    out["gate"] = dict(AR_us=m["AR_us"], MTP_step_us=m["MTP_step_us"], AR_row=m["AR_row"], MTP_row=m["MTP_row"])
    out["basis"] = ("serialisation_cycles = measured RX arrival stream at the RTL port rate (rx_last - first) per on-path "
                    "collective class (tools/dshbm_1m_coll.per_token convention, OFF_PATH excluded); AR = P1, MTP step = P6; "
                    "crossings: all-reduce 2, gathers 1; each crossing passes one TX CDC and one RX CDC")
    return out


# ----------------------------------------------------------------------------------------------
# Cycle-accurate two-clock queue simulator
# ----------------------------------------------------------------------------------------------
class Sync:
    """Monotonic pointer register in a source domain sampled by a 2-flop synchroniser.
    A sample whose edge falls within `meta` after an update resolves randomly old/new
    (Gray code: either neighbour is legal); one Gray transition per update is assumed."""

    def __init__(self, rng, meta):
        self.upd = []          # update times of the source register (one increment each)
        self.rng, self.meta = rng, meta
        self.s0 = self.s1 = 0

    def bump(self, t):
        self.upd.append(t)

    def value_at(self, t):
        # count of updates strictly before t - meta, plus a random prefix of those in the window
        lo = hi = len(self.upd)
        while lo > 0 and self.upd[lo - 1] >= t - self.meta:
            lo -= 1
        while hi > lo and self.upd[hi - 1] >= t:
            hi -= 1
        return lo + (self.rng.randint(0, hi - lo) if hi > lo else 0)

    def edge(self, t):
        self.s1, self.s0 = self.s0, self.value_at(t)


def simulate(cfg, seed):
    """One direction of the link: sender (write domain) -> CDC (write W / read R) -> head -> wire -> RB -> consumer.
    cfg keys:
      Tw, Tr          write/read clock periods (ps); phase random
      D               CDC slots;  II_mode 'serial3' | 'rot3' | 'plain'
      C               sender credits; credit_mode 'downstream' (returned at RB pop, +ret_ps) | 'local' (writer-visible
                      CDC frees: issued - synced read pointer, wire flight counted)
      Lf              sender->CDC forward flight (write cycles);  WSTG wire stages after the CDC (read cycles)
      RB              receive-buffer depth (None = infinite), consumer 'always' | ('random', p) | ('stall', start, len)
      traffic         'sustained' | ('bursts', on_max, off_max) | ('random', p) ; N flits total
      ce              list of flit sequence numbers whose head capture hits a correctable error (each costs
                      ce_cycles read cycles of held repair in its bank)
      reset           (w_release_ps, r_release_ps); advert 'both_ready' | 'own_release'
    Returns metrics; an overflow/loss/order error is recorded, never masked."""
    rng = random.Random(seed)
    Tw, Tr, D, N = cfg["Tw"], cfg["Tr"], cfg["D"], cfg["N"]
    meta = cfg.get("meta_ps", 20.0)
    wph, rph = rng.uniform(0, Tw), rng.uniform(0, Tr)
    w_rel, r_rel = cfg.get("reset", (0.0, 0.0))
    # cold reset entry: async assert, two local release edges per domain
    w_rel = math.ceil((w_rel - wph) / Tw) * Tw + wph + cfg.get("release_edges", 2) * Tw
    r_rel = math.ceil((r_rel - rph) / Tr) * Tr + rph + cfg.get("release_edges", 2) * Tr
    wb_sync = Sync(rng, meta)   # write pointer -> read domain
    rb_sync = Sync(rng, meta)   # read (commit) pointer -> write domain
    wb = rb = cap = 0
    mem = {}
    link = []                   # (arrive_time, seq)
    returns = []                # credit return times
    credit = cfg["C"]
    advertised = False
    if cfg.get("advert", "both_ready") == "both_ready":
        t_adv = max(w_rel, r_rel) + (cfg.get("sync_stages", 2) + 1) * max(Tw, Tr)
    else:
        t_adv = w_rel
    issued = 0
    seq_out = 0
    ce = set(cfg.get("ce", ()))
    ce_cyc = cfg.get("ce_cycles", 5)
    mode = cfg["II_mode"]
    banks = [None] * 3          # rot3: [state, seq, ready_cycle]
    hp = None                   # serial3: [seq, ready_cycle]
    wire = []                   # (arrive_read_cycle, seq)
    rb_q = []
    rb_max = 0
    occ_max = 0
    errs = []
    first_arrival = last_pop = None
    rcyc = 0
    traffic = cfg["traffic"]
    burst_left, off_left = 0, 0
    tw = wph
    tr = rph
    horizon = cfg.get("horizon_cycles", 40 * N + 4000) * max(Tw, Tr)
    while (seq_out < N or wire or rb_q) and min(tw, tr) < horizon and not errs:
        if tw <= tr:                                    # ---------------- write-domain edge
            t = tw
            tw += Tw
            if t < w_rel:
                if any(a <= t for a, _ in link):
                    errs.append("LOSS_write_domain_in_reset")
                continue
            rb_sync.edge(t)
            vis_free_from = rb_sync.s1
            while returns and returns[0] <= t:
                returns.pop(0)
                credit += 1
            arr = [x for x in link if x[0] <= t]
            link = [x for x in link if x[0] > t]
            for _, s in arr:
                occ = wb - vis_free_from
                occ_max = max(occ_max, occ + 1)
                if occ >= D:
                    errs.append(f"OVERFLOW occ={occ} D={D} seq={s}")
                    break
                mem[wb % D] = s
                wb += 1
                wb_sync.bump(t)
                if first_arrival is None:
                    first_arrival = t
            if not advertised and t >= t_adv:
                advertised = True
            if advertised and issued < N:
                want = True
                if traffic == "sustained":
                    pass
                elif traffic[0] == "random":
                    want = rng.random() < traffic[1]
                elif traffic[0] == "bursts":
                    if burst_left == 0 and off_left == 0:
                        burst_left = rng.randint(1, traffic[1])
                        off_left = rng.randint(0, traffic[2])
                    if burst_left > 0:
                        burst_left -= 1
                    else:
                        off_left -= 1
                        want = False
                if want:
                    if cfg["credit_mode"] == "local":
                        ok = issued - rb_sync.s1 < cfg["C"]
                    else:
                        ok = credit > 0
                    if ok:
                        if cfg["credit_mode"] != "local":
                            credit -= 1
                        link.append((t + cfg["Lf"] * Tw - 1e-6, issued))
                        issued += 1
        else:                                           # ---------------- read-domain edge
            t = tr
            tr += Tr
            if t < r_rel:
                continue
            rcyc += 1
            wb_sync.edge(t)
            wvis = wb_sync.s1
            out_r = True                                # RX CDC: rd = !empty; RB depth >= credits
            pop = None
            if mode == "plain":                         # original ot_link_afifo: head visible when non-empty
                if rb < wvis:
                    pop = mem[rb % D]
            elif mode == "serial3":                     # candidate: capture, validate(+repair), present
                if hp is None:
                    if rb < wvis:
                        s = mem[rb % D]
                        hp = [s, rcyc + 2 + (ce_cyc if s in ce else 0)]
                elif rcyc >= hp[1] and out_r:
                    pop = hp[0]
                    hp = None
            elif mode == "rot3":                        # B: three protected banks, rotation by commit index
                b = banks[rb % 3]
                if b is not None and rcyc >= b[1] and out_r:
                    pop = b[0]
                    banks[rb % 3] = None
                # capture the next sequential slot into its rotation bank (bank freed on an earlier edge)
                if cap < wvis and cap - rb < 3 and banks[cap % 3] is None and not (pop is not None and cap % 3 == rb % 3):
                    s = mem[cap % D]
                    banks[cap % 3] = [s, rcyc + 2 + (ce_cyc if s in ce else 0)]
                    cap += 1
            if pop is not None:
                if pop != seq_out:
                    errs.append(f"ORDER got {pop} want {seq_out}")
                seq_out += 1
                rb += 1
                if mode != "rot3":
                    cap = rb
                rb_sync.bump(t)
                wire.append((rcyc + cfg["WSTG"], pop))
                last_pop = t
            while wire and wire[0][0] <= rcyc:
                rb_q.append(wire.pop(0)[1])
            if cfg.get("RB") is not None and len(rb_q) > cfg["RB"]:
                errs.append("RB_OVERFLOW")
            rb_max = max(rb_max, len(rb_q))
            cons = cfg.get("consumer", "always")
            go = True
            if cons != "always":
                if cons[0] == "random":
                    go = rng.random() < cons[1]
                elif cons[0] == "stall":
                    go = not (cons[1] <= rcyc < cons[1] + cons[2])
            if rb_q and go:
                rb_q.pop(0)
                if cfg["credit_mode"] == "downstream":
                    returns.append(t + cfg["ret_ps"])
    if not errs and seq_out < N:
        errs.append(f"INCOMPLETE {seq_out}/{N}")
    span = (last_pop - first_arrival) if (first_arrival is not None and last_pop is not None) else None
    return dict(ok=not errs, errors=errs[:2], occ_max=occ_max, rb_max=rb_max, delivered=seq_out,
                flits_per_read_cycle=round((seq_out - 1) / (span / Tr), 4) if span else None)


# ----------------------------------------------------------------------------------------------
# Analytic bounds per option (the inequalities the simulator checks)
# ----------------------------------------------------------------------------------------------
def residency_bound(Tw, Tr, S, head, II, K_stall, N_stream):
    """Upper bound of writer-visible CDC occupancy (flits) when the drain is never back-pressured:
    arrivals at <= 1 a write edge during the writer-view residency of the oldest flit
    ((S+1) read edges to see it + 1 capture alignment + head pipeline + stall, then (S+1)+1 write
    edges for the pop to become visible), plus the backlog drift when the drain rate 1/(II*Tr)
    is below the arrival rate 1/Tw over a gap-free stream of N_stream flits."""
    res = (S + 2 + head + K_stall) * Tr + (S + 2) * Tw + 2 * 20.0
    drift = max(0.0, 1.0 - Tw / (II * Tr)) * N_stream
    return math.ceil(res / Tw) + 1 + math.ceil(drift)


def analytic(p, wl):
    Tw = p["link_period_ps"]
    Tr = p["core_period_ps"]
    S, D, C = p["sync_stages"], p["D"], p["SWCRED"]
    rtt = p["rx_credit_rtt_cycles"]
    cyc_us = 1e6 / p["clk_hz"]
    m1, m6 = wl["matched_P1"], wl["matched_P6"]
    gate = wl["gate"]

    def ser_cost(II):  # extra cycles when the per-port drain is 1/II of the line rate (matched hub keeps up)
        return dict(AR_cycles=round((II - 1) * m1["serialisation_cycles"]),
                    MTP_step_cycles=round((II - 1) * m6["serialisation_cycles"]),
                    AR_us=round((II - 1) * m1["serialisation_cycles"] * cyc_us, 2),
                    MTP_step_us=round((II - 1) * m6["serialisation_cycles"] * cyc_us, 2))

    def lat_cost(add):  # +add read cycles per CDC traversal, TX and RX per crossing
        return dict(AR_cycles=2 * add * m1["crossings"], MTP_step_cycles=2 * add * m6["crossings"],
                    AR_us=round(2 * add * m1["crossings"] * cyc_us, 3),
                    MTP_step_us=round(2 * add * m6["crossings"] * cyc_us, 3))

    def pct(c):
        return dict(AR_pct=round(100 * c["AR_us"] / gate["AR_us"], 2),
                    MTP_step_pct=round(100 * c["MTP_step_us"] / gate["MTP_step_us"], 2))

    dff = p["dff_um2_per_bit"]
    base_bits = p["cdc_fifos"] * D * p["encoded_bits"]
    bank_bits = p["bank_words"] * 72
    sram = load(SRC["sram"])
    K_ce_budget_B = None
    # B: largest total repair stall (read cycles) inside one gap-free stream that keeps occupancy < D
    for K in range(0, 400):
        if residency_bound(Tw, Tr, S, p["head_latency_cycles"], 1, K, 0) > D - 1:
            K_ce_budget_B = K - 1
            break
    opt = {}
    sA = ser_cost(p["II_candidate"])
    lA = lat_cost(p["added_read_cycles_vs_original"])
    opt["A_credit_bound"] = dict(
        summary="Keep the II=3 protected CDC; the link partner may hold at most D credits for this port",
        inequality="C_adv <= D - R_rsv, with credits returned at any point at or after the CDC pop as seen by the "
                   "WRITE domain (RB pop qualifies: it is downstream of the CDC); R_rsv = 0",
        derivation=["writer-visible occupancy = wb - sync(rb) counts every flit written and not yet seen popped",
                    "each such flit still holds its credit: the credit returns only at RB pop, which follows the CDC "
                    "pop by >= WSTG read cycles, and the sender spends a credit before the flit can reach the CDC",
                    "hence writer-visible occupancy <= outstanding credits <= C; C <= D => no overflow for ANY "
                    "clock ratio, phase, drain stall (CE repair, incoherent rails), consumer stall or reset order "
                    "provided the write domain leaves reset before the first arrival"],
        C_safe=D, C_native=C, credit_rtt_cycles=rtt,
        throughput_flits_per_edge=round(min(1.0, Tw / (p["II_candidate"] * Tr), D / rtt), 4),
        full_rate_requires="D >= C >= RTT*rate = %d flits and II*Tr <= Tw (impossible at II=3, Tw=Tr)" % rtt,
        cost_serialisation=dict(**sA, **pct(sA)),
        cost_latency=dict(**lA, **pct(lA)),
        area_um2_added=0.0, area_note="0 storage; the 64-credit advertisement is a switch-side parameter",
        residual=["throughput 1/3 per port on every streaming collective (cost above)",
                  "the external switch must honour a per-port 64-credit pool distinct from the 256-flit RB",
                  "the RB (256 deep) is left 75% unused while C <= 64",
                  "the packet-SRAM receive queue is II=3 as well, so the same 1/3 bound exists downstream"])
    lB = lat_cost(p["added_read_cycles_vs_original"])
    occB = residency_bound(Tw, Tr, S, p["head_latency_cycles"], 1, 0, 0)
    opt["B_rotated_II1"] = dict(
        summary="Three W2 protected head banks in rotation (bank = commit index mod 3): capture, validate and present "
                "overlap so the drain is II=1; a separate protected capture pointer runs <= 3 ahead of the protected "
                "commit pointer, which alone is Gray-synchronised (credit-safe).  Same per-flit checks, same "
                "fail-closed faults, same first-flit latency as the candidate.",
        inequalities=dict(
            drain_rate="Tw >= II*Tr (=Tr at II=1): the PHY write clock is not faster than the core read clock "
                       "(frequency-locked, independent phase per hbm_collective_clock_entry model)",
            occupancy="occ_vis <= ceil(((S+2+H+K)*Tr + (S+2)*Tw + 2*t_meta)/Tw) + 1 + ceil(max(0,1-Tw/(II*Tr))*N_stream)"
                      " <= D - 1, with S=2 sync, H=3 head, K = total repair stall read cycles inside one gap-free stream",
            occupancy_value_K0=occB,
            ce_stall_budget_read_cycles=K_ce_budget_B,
            ce_repairs_tolerated_per_gap_free_stream=K_ce_budget_B // p["ce_repair_cycles"],
            credits="C_adv = 256 unchanged; RB depth 2^RXAW = 256 >= C so the CDC drain is never back-pressured",
            reset="credits advertised only after BOTH domains released and synchronised (t_adv >= max(t_w, t_r) + "
                  "(S+1) cycles); otherwise a read domain held in reset lets C - D flits overflow",
            tx_direction="TX CDC: core issue gated by issued - sync(rb_tx) < D_tx counting WSTG flight; full rate "
                         "when D_tx >= WSTG + 2S + H + 4 = %d" % (p["WSTG"] + 2 * S + p["head_latency_cycles"] + 4)),
        throughput_flits_per_edge=1.0,
        cost_serialisation=dict(AR_cycles=0, MTP_step_cycles=0, AR_us=0.0, MTP_step_us=0.0),
        cost_latency=dict(**lB, **pct(lB)),
        cost_latency_note="+2 read cycles per CDC traversal vs the original unprotected II=1 CDC; equal to the "
                          "II=3 candidate's first-flit latency",
        area_bits_added_per_fifo=2 * bank_bits + 6 * 72 + 2 * 72,
        area_um2_added=round(p["cdc_fifos"] * (2 * bank_bits + 8 * 72) * dff, 1),
        area_note="2 extra protected head banks ((9+5) x 72 b each) + protected capture pointer bank ((1+5) x 72) + "
                  "protected 2-bit rotation code; DFF lower bound %.4f um2/bit; ECC check slices x3 and a 3:1 "
                  "648-bit output mux not in the figure" % dff,
        residual=["requires frequency lock of PHY and core clocks (or a PHY rate-matcher guaranteeing <= 1 flit per "
                  "core cycle); a write clock faster than the read clock overflows a long gap-free stream (negative)",
                  "more than %d correctable-error repairs inside one gap-free stream overflow (detected, sticky "
                  "fault, fail closed); not silent" % (K_ce_budget_B // p["ce_repair_cycles"]),
                  "capture pointer and rotation code must themselves be protected banks (W2) and checked against "
                  "commit (cap - rb in [0,3]); mismatch = fault",
                  "the 64:1 x 648-bit capture mux now launches every cycle: SS timing of mem->bank path unchanged "
                  "in depth but now at full activity",
                  "the packet-SRAM receive queue (II=3) must take the same rotation or the 1/3 bound moves there"])
    D_C = C
    sC = ser_cost(p["II_candidate"])
    extra_bits = (p["cdc_fifos"] // 2) * (D_C - D) * p["encoded_bits"]
    opt["C_deep_fifo"] = dict(
        summary="Keep II=3, size the RX CDC to the credit pool so the writer can never see it full",
        inequality="D >= C_adv (timing-free, same argument as A); the drain-rate-only bound for a burst of N "
                   "flits is D >= ceil(N*(1 - Tw/(II*Tr))) + base, which for C=256 at II=3 is ~%d" %
                   residency_bound(Tw, Tr, S, p["head_latency_cycles"], p["II_candidate"], 0, C),
        D_required=D_C,
        sustained="1 flit/edge is NOT absorbable by any finite depth at II=3 (drift 2/3 flit per edge); the credit "
                  "loop throttles the sender to 1/3",
        throughput_flits_per_edge=round(Tw / (p["II_candidate"] * Tr), 4),
        cost_serialisation=dict(**sC, **pct(sC)),
        cost_latency=dict(**lA, **pct(lA)),
        area_bits_added=extra_bits,
        area_um2_added_flops=round(extra_bits * dff, 1),
        area_sram_note="no dual-clock macro in the asap7 set (all 1r1w macros have one clk); an SRAM can only sit "
                       "behind a flop CDC in one domain, which is the existing RB arrangement. Single-clock "
                       "equivalent for reference: %d x ot_sram_1r1w_256x256 = %.0f um2" %
                       (p["cdc_fifos"] // 2 * 3, p["cdc_fifos"] // 2 * 3 * sram["area"]["macro_area_um2"]),
        residual=["pays the full 1/3 throughput cost of A plus ~%.2f mm2 of flops and a 256:1 x 648 read mux" %
                  (extra_bits * dff / 1e6),
                  "reset/CE robust (timing-free bound) but solves overflow only, not rate"])
    common = dict(
        storage_bits_all_options=base_bits, storage_um2_flops=round(base_bits * dff, 1),
        original_cdc="ot_link_afifo_quiet, II=1, unprotected (matched-SRAM full gate uses it)",
        ledger_underpricing=dict(
            finding="the unified ledger charges the II=3 packet SRAM +%d cycles x 265 collectives; at II=3 the "
                    "receive drain bounds the port at 1/3 of line rate, i.e. +%d cycles AR / +%d MTP step per token "
                    "(matched hub, which keeps up with the line)" % (p["ledger_sram_added_cycles"],
                                                                      sA["AR_cycles"], sA["MTP_step_cycles"]),
            AR_us=sA["AR_us"], MTP_step_us=sA["MTP_step_us"]))
    return opt, common


# ----------------------------------------------------------------------------------------------
# Simulation campaign
# ----------------------------------------------------------------------------------------------
def campaign(p, quick=False):
    Tw = p["link_period_ps"]
    Tr = p["core_period_ps"]
    D, C, S = p["D"], p["SWCRED"], p["sync_stages"]
    ret_ps = p["credit_return_ns"] * 1000.0
    seeds = range(4 if quick else 16)
    N = 600 if quick else 1500
    base = dict(Tw=Tw, Tr=Tr, D=D, N=N, Lf=8, WSTG=p["WSTG"], RB=2 ** p["RXAW"], ret_ps=ret_ps,
                credit_mode="downstream", ce_cycles=p["ce_repair_cycles"], sync_stages=S)
    traffics = ["sustained", ("bursts", 300, 200), ("random", 0.7)]
    consumers = ["always", ("random", 0.5), ("stall", 400, 900)]

    def resets(rng):
        return (rng.uniform(0, 30 * Tw), rng.uniform(0, 30 * Tr))

    rows = []

    def run(name, cfg_over, expect_ok, vary=True, bound=None):
        res = []
        rng = random.Random(hash(name) & 0xffff)
        grid = [(t, c) for t in traffics for c in consumers] if vary else [(cfg_over.get("traffic", "sustained"),
                                                                            cfg_over.get("consumer", "always"))]
        for t, c in grid:
            for s in seeds:
                cfg = dict(base, traffic=t, consumer=c, reset=resets(rng))
                cfg.update(cfg_over)
                if vary:
                    cfg["traffic"], cfg["consumer"] = t, c
                if callable(cfg.get("ce")):
                    cfg["ce"] = cfg["ce"](random.Random(s))
                res.append(simulate(cfg, seed=s * 7919 + len(rows)))
        ok = all(r["ok"] for r in res)
        occ = max(r["occ_max"] for r in res)
        rates = [r["flits_per_read_cycle"] for r in res if r["flits_per_read_cycle"]]
        row = dict(name=name, expect_ok=expect_ok, runs=len(res), all_ok=ok, occ_max=occ,
                   bound=bound, within_bound=(bound is None or occ <= bound),
                   max_rate=max(rates) if rates else None,
                   errors=sorted({e.split(" ")[0] for r in res for e in r["errors"]}),
                   verdict="PASS" if (ok == expect_ok and (bound is None or occ <= bound or not expect_ok))
                   else "FAIL")
        rows.append(row)
        return row

    # baseline: original unprotected II=1 CDC, 256 credits
    run("orig_II1_C256", dict(II_mode="plain", C=C), True)
    # the problem as posed: candidate II=3 with the native 256 credits
    run("NEG_candidate_II3_D64_C256", dict(II_mode="serial3", C=C, traffic="sustained"), False, vary=False)
    # A: C = D, adversarial: CE storm on every flit, read domain released late, random stalls
    run("A_II3_D64_C64", dict(II_mode="serial3", C=D), True, bound=D)
    run("A_II3_D64_C64_ce_storm_late_read",
        dict(II_mode="serial3", C=D, ce=lambda r: set(range(0, N, 1)), reset=(0.0, 400 * Tr)), True,
        vary=False, bound=D)
    run("A_II3_D64_C64_advert_own_release_read_held",
        dict(II_mode="serial3", C=D, advert="own_release", reset=(0.0, 400 * Tr)), True, bound=D)
    run("NEG_A_II3_D64_C65_advert_own_release_read_held",
        dict(II_mode="serial3", C=D + 1, advert="own_release", reset=(0.0, 400 * Tr), traffic="sustained"),
        False, vary=False)
    # B: II=1 rotation, native credits
    bB = residency_bound(Tw, Tr, S, p["head_latency_cycles"], 1, 0, 0)
    run("B_rot3_D64_C256", dict(II_mode="rot3", C=C), True, bound=bB)
    Kb = 0
    while residency_bound(Tw, Tr, S, p["head_latency_cycles"], 1, Kb + 1, 0) <= D - 1:
        Kb += 1
    n_ok = Kb // p["ce_repair_cycles"]
    run("B_rot3_C256_ce_within_budget",
        dict(II_mode="rot3", C=C, ce=lambda r: set(r.sample(range(50, N), n_ok))), True,
        bound=residency_bound(Tw, Tr, S, p["head_latency_cycles"], 1, n_ok * p["ce_repair_cycles"], 0))
    run("NEG_B_rot3_ce_storm_beyond_budget",
        dict(II_mode="rot3", C=C, traffic="sustained", ce=lambda r: set(range(100, 100 + 6 * (n_ok + 2), 3))),
        False, vary=False)
    run("NEG_B_rot3_advert_before_read_release",
        dict(II_mode="rot3", C=C, traffic="sustained", advert="own_release", reset=(0.0, 300 * Tr)),
        False, vary=False)
    run("NEG_B_rot3_write_clock_1pct_fast_long_stream",
        dict(II_mode="rot3", C=C, traffic="sustained", Tw=Tw / 1.01, N=12000), False, vary=False)
    run("NEG_B_rot3_stress_read_1024p6ps",
        dict(II_mode="rot3", C=C, traffic="sustained", Tr=p["stress_read_period_ps"]), False, vary=False)
    run("B_rot3_stress_read_1024p6ps_C64",
        dict(II_mode="rot3", C=D, Tr=p["stress_read_period_ps"]), True, bound=D)
    # B TX direction: core -> PHY, local credits counting the wire flight
    run("B_TX_rot3_local_D64", dict(II_mode="rot3", C=D, credit_mode="local", Lf=p["WSTG"], RB=None), True, bound=D)
    run("NEG_TX_serial3_no_local_gate", dict(II_mode="serial3", C=10 ** 9, credit_mode="local", Lf=p["WSTG"],
                                             RB=None, traffic="sustained"), False, vary=False)
    # C: deep FIFO
    run("C_II3_D256_C256", dict(II_mode="serial3", D=C, C=C), True, bound=C)
    run("C_II3_D256_C256_ce_storm_late_read",
        dict(II_mode="serial3", D=C, C=C, ce=lambda r: set(range(N)), reset=(0.0, 600 * Tr)), True,
        vary=False, bound=C)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/rtl/hbm_collective_cdc_design_20261007"))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    p = params()
    wl = workload()
    opt, common = analytic(p, wl)
    rows = campaign(p, a.quick)
    verdict = all(r["verdict"] == "PASS" for r in rows)
    out = dict(
        schema="opentallas.hbm-collective-cdc-design.v1",
        status="DESIGN_MODEL_RECOMMENDATION (no RTL change; RTL owned by Codex /hbm/collective)",
        recommendation="B_rotated_II1",
        params=p, workload=wl, options=opt, common=common,
        simulation=dict(model="cycle-accurate two-clock queue: independent clock edge streams with random phase, "
                              "Gray pointers through 2-flop synchronisers with a 20 ps metastability window "
                              "(random old/new), staggered cold reset (2 release edges per domain), credit return "
                              "delay, CE held-repair stalls, order and overflow checked on every flit",
                        rows=rows, all_pass=verdict),
        snapshot_pins={k: dict(expected=v, actual=sha(SNAP / k)) for k, v in SNAP_PINS.items()},
        sources={k: dict(path=v, sha256=sha(ROOT / v)) for k, v in SRC.items()},
        tool_sha256=sha(Path(__file__)),
    )
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    (od / "options.json").write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['verdict']:4s} {r['name']:48s} ok={r['all_ok']!s:5s} occ_max={r['occ_max']:4d} "
              f"bound={r['bound']} rate={r['max_rate']} {','.join(r['errors'])}")
    for k, v in opt.items():
        print(k, "thr", v["throughput_flits_per_edge"], "ser", v["cost_serialisation"], "lat", v["cost_latency"])
    print("ALL_PASS", verdict)
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
