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

MAIN_PIN = "9ead91a15"   # Codex committed the protected CDC, the II1 refill and their receipts here
CDC_RES = ROOT / "results/rtl/hbm_collective_cdc_20261007"
PINS = {  # every input, by repo path, as committed at MAIN_PIN (and this branch); fail closed on any mismatch
    "tools/hbm_collective_cdc_model.py":
        "4828bd7efede63d963ebbd73cf0af1d48441e089287b9dabcbc3fdcb9ed76f8f",
    "rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv":
        "a4e1bda9a0ab083503462a8c755f35cbe3aa52786e455e29c66834e915463497",
    "rtl/hbm_accel/collective_cdc_20261007/tb_protected_cdc.sv":
        "2ad089b349abf3d9c7441edbcf3ff6dbfb6ccfc6d6648c65e761e5c216a355d0",
    "rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv":
        "1fe0c8ebc52a154a2be9eb018590db158c9cd9c9da5730cbdf1d990bd54a1aad",
    "rtl/hbm_accel/collective_cdc_20261007/tb_protected_cdc_refill.sv":
        "e80d1178a1f94c1f5ca5d644249b085ad4dd4ecdc66ab0b71c427b0549ba9708",
    "results/rtl/hbm_collective_cdc_20261007/model.json":
        "12144e2b8785d27992acdb05723c337f2c50323470c6aeacf93bf50a019e0221",
    "results/rtl/hbm_collective_cdc_20261007/diagnosis.json":
        "34534859390626e5f459e751e9b3846d0f88e2116d533b59fb0d9c245bae03ec",
    "results/rtl/hbm_collective_cdc_20261007/refill_model.json":
        "16c42c35aa81bd3dfda94654580c7a5a924e85fa04a577912ea9f0ce78b25cf5",
    "results/rtl/hbm_collective_cdc_20261007/admission_comparison.json":
        "138921dcf18f76ce522ce1bf01d371be189a67e9b1b8f4c5831f0aa70ce0f54c",
    "results/rtl/hbm_collective_cdc_20261007/refill_pass/record.json":
        "0b1f2c043edd1398fb1b5b662f2125067534798b23881e58bee07613d75014b0",
    "results/rtl/hbm_collective_cdc_20261007/refill_nominal_pass/record.json":
        "d0677a1b570feb334cb773de30064faea94f838a80498f37d915ffef99ae4692",
    "results/rtl/hbm_collective_cdc_20261007/final_pass/record.json":
        "68022549e199da2f113c1dcf62fabdc02158935462d110e9e1148776c3f24f17",
    "results/rtl/hbm_collective_cdc_20261007/nominal_pass/record.json":
        "10fb7f858c0110660492d9a163b75f89ea5cab516584ba140df746cccf051e6b",
    "tools/dshbm_1m_coll.py":
        "aa96b2bfeb69653d1b67362a30dce1348530c0fc821f3b7692e4181c82e4beb0",
    "tools/w19_hbm_token_compose.py":
        "532e750860030c2142cc514da714582083a70519f28dff0fc49cdd7d46ca936a",
    "rtl/hbm_accel/collective_full_20261007/ot_hbm_collective_full_candidate.sv":
        "3834d5406541cc4dccbbaeb95877b98c22180ce432cd1315d867fa8ead9852a8",
    "rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_die_entry.sv":
        "a702c30234042843ed722a8d6f96a0d2add1d70993d658ddad300c882805dd65",
    "rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv":
        "5366ef10cf135546f19f07fbe1a6f3e7fc4052a159479eb63acf7970be99648b",
    "results/uarch/hbm_collective_clock_entry_20261007/model.json":
        "d4ce9be276fddd3cd3ced22cb6a6a61583e36d0e8307f530f002e0c9d35f93dc",
    "rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv":
        "d93086deb486fa2f2d3d30f4d4cdef2c7b4658c863a31e5b2d366ce8d4cfa8e9",
    "results/rtl/hbm_collective_full_20261007/storage_model.json":
        "ed03682d76b4a2448b632953d82898fc3ec46656e782fd83bb4fb224d3a719bc",
    "results/rtl/dshbm_1m_allmeasured_20261004/collectives.json":
        "7e5a6822df09500efebe7d7b937545116f66d530026b80e4ac2dcdedf6f1ebda",
    "results/rtl/dshbm_baseline_measured_20261004/program.json":
        "a6218d2da6578bc36d510ba925091fc19272a33211a03f10efedd1b72a799491",
    "results/rtl/dshbm_matched_reference_20261005/composition.json":
        "d64a44a2f1382658e66e620fe2d01372497c5a38d6c60a8f2697053cb4993a7f",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.json":
        "f0e8d51af00ec806eddea2f031e4ecaab6316557c9c4a78c00827dc84323d2c5",
    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.json":
        "6d516bd39f8d4b0b43970c35014bf855febd57e7d80157b6fd39fed3e61a362a",
}


def verify_inputs():
    bad = [p for p, h in PINS.items() if sha(ROOT / p) != h]
    if bad:
        raise SystemExit("INPUT_PIN_MISMATCH (fail closed): " + ", ".join(bad))
    return dict(main_pin=MAIN_PIN, files=len(PINS), pins=PINS)


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
    snap_model = json.loads((CDC_RES / "model.json").read_text())
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
    p["credit_counter_bits"] = math.ceil(math.log2(p["SWCRED"] + 1))
    p["rx_forward_flight_cycles"] = math.ceil((col["budget"]["endpoint_phy_ns"] + col["budget"]["cable_ns"]) / 2
                                              * 1e-9 * p["clk_hz"])
    p["rx_forward_flight_basis"] = "half of the endpoint PHY Tx+Rx budget + one of the two 3 m cable legs"
    S = p["sync_stages"]
    p["tx_min_depth_full_rate"] = p["WSTG"] + 1 + (S + 1) + 2 + 1 + (S + 1) + 1
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
    """Monotonic counter register in a source domain sampled by a 2-flop synchroniser in the other domain.
    kind 'gray'  : one Gray transition per increment; a sample inside the metastability window resolves to the
                   old or the new value (both legal neighbours).
    kind 'binary': a W-bit binary register; a sample inside the window takes each changing bit from old or new
                   at random (the illegal mixture a binary multi-bit crossing can produce) -- NEGATIVE only.
    kind 'pulse' : a toggle (bit 0 of the count) synchronised and edge-detected; two increments between samples
                   are seen as none -- NEGATIVE only."""

    def __init__(self, rng, meta, kind="gray", width=64):
        self.upd = []
        self.rng, self.meta, self.kind, self.width = rng, meta, kind, width
        self.s0 = self.s1 = 0
        self.prev_tog = 0
        self.count = 0          # pulse-mode reconstructed count

    def bump(self, t):
        self.upd.append(t)

    def value_at(self, t):
        lo = hi = len(self.upd)
        while lo > 0 and self.upd[lo - 1] >= t - self.meta:
            lo -= 1
        while hi > lo and self.upd[hi - 1] >= t:
            hi -= 1
        if hi == lo:
            return lo
        if self.kind == "binary":
            m = (1 << self.width) - 1
            a, b = lo & m, hi & m
            mask = self.rng.getrandbits(self.width)
            mixed = (a & ~mask) | (b & mask)
            return lo - a + mixed           # same high part, low W bits mixed
        return lo + self.rng.randint(0, hi - lo)

    def edge(self, t):
        self.s1, self.s0 = self.s0, self.value_at(t)
        if self.kind == "pulse":
            tog = self.s1 & 1
            if tog != self.prev_tog:
                self.count += 1
            self.prev_tog = tog

    def visible(self):
        return self.count if self.kind == "pulse" else self.s1


def simulate(cfg, seed):
    """One link direction, cycle accurate on two independent clocks.
    sender (partner, write-clock edges) -> Lf flight -> CDC write (W) -> CDC read/head (R) -> WSTG wire -> RB ->
    consumer.  Credit producer modes:
      'gray'           RX contract: a READY level (core domain, raised only after both domains are released +
                       (S+1) cycles) and a retirement counter K (+1 per RB pop, at most one a core cycle) as a W-bit
                       Gray register, both synchronised (S flops) into the PHY domain and returned to the partner
                       after ret_ps; the partner spends avail = (READY ? C : 0) + K_seen - sent  (mod 2^W).
      'binary'/'pulse' NEGATIVE transports of the same counter.
      'local'          TX contract: issue only while issued - sync(rb) < C (wire flight counted).
      'local_cdc_only' NEGATIVE: gate on the CDC occupancy alone (wb - sync(rb) < C), wire flight ignored.
    Head modes: 'plain' (original II1), 'serial3' (candidate II3), 'refill' (Codex II1 refill, B'), 'rot3' (B).
    Assertions recorded (never masked): OVERFLOW, LOSS_write_domain_in_reset, ORDER, RB_OVERFLOW,
    CREDIT_OVERGRANT (partner credit > C), CREDIT_LEAK (quiesced K != C + pops),
    INCOMPLETE (deadlock / starvation)."""
    rng = random.Random(seed)
    Tw, Tr, D, N, C = cfg["Tw"], cfg["Tr"], cfg["D"], cfg["N"], cfg["C"]
    S = cfg.get("sync_stages", 2)
    Wc = cfg.get("credit_bits", 9)
    meta = cfg.get("meta_ps", 20.0)
    edges = cfg.get("release_edges", 2)
    cmode = cfg["credit_mode"]
    mode = cfg["II_mode"]
    ce = set(cfg.get("ce", ()))
    ce_cyc = cfg.get("ce_cycles", 5)
    wph, rph = rng.uniform(0, Tw), rng.uniform(0, Tr)

    def rel(t0, ph, T):
        return math.ceil((t0 - ph) / T) * T + ph + edges * T

    R = {}

    def fresh_read():
        R.update(rb=0, cap=0, head=None, banks=[None] * 3, wire=[], rbq=[], K=0, pending=0, granted=0,
                 wb_sync=Sync(rng, meta), pops_total=0, rcyc=0)

    W = {}

    def fresh_write():
        W.update(wb=0, mem={}, rb_sync=Sync(rng, meta),
                 k_sync=Sync(rng, meta, "gray" if cmode in ("gray", "local", "local_cdc_only") else cmode, Wc),
                 khist=[], rdy0=False, rdy1=False)

    P = {}

    def fresh_partner():
        P.update(sent=0, link=[], skip_ctr=0, burst_left=0, off_left=0)

    fresh_read(); fresh_write(); fresh_partner()
    w_rel = rel(cfg.get("reset", (0.0, 0.0))[0], wph, Tw)
    r_rel = rel(cfg.get("reset", (0.0, 0.0))[1], rph, Tr)

    def t_grant_of():
        return max(w_rel, r_rel) + (S + 1) * max(Tw, Tr)
    t_grant = t_grant_of()
    seq_out = 0
    occ_max = flight_max = rb_max = 0
    errs = []
    first_arrival = last_pop = None
    first_send = None
    ev = cfg.get("reset_event")
    ev_done = ev is None
    tail_ps = cfg.get("ret_ps", 0) + (cfg["Lf"] + 40) * max(Tw, Tr)
    t_done = None
    traffic = cfg["traffic"]
    out_r_pat = cfg.get("out_r", "always")
    tw, tr = wph, rph
    horizon = cfg.get("horizon_cycles", 40 * N + 6000) * max(Tw, Tr)
    def partner(t, rb_vis):
        nonlocal first_send, flight_max
        ok = False
        # ---- partner / sender
        want = P["sent"] < N
        if want:
            if traffic == "sustained":
                pass
            elif traffic[0] == "random":
                want = rng.random() < traffic[1]
            elif traffic[0] == "bursts":
                if P["burst_left"] == 0 and P["off_left"] == 0:
                    P["burst_left"] = rng.randint(1, traffic[1])
                    P["off_left"] = rng.randint(0, traffic[2])
                if P["burst_left"] > 0:
                    P["burst_left"] -= 1
                else:
                    P["off_left"] -= 1
                    want = False
        if want and cfg.get("skip_every"):
            if P["skip_ctr"] >= cfg["skip_every"]:
                P["skip_ctr"] = 0
                want = False
        if want:
            if cmode in ("gray", "binary", "pulse"):
                lag = t - cfg["ret_ps"]
                kp, rdy = 0, False
                for th, v, rd in reversed(W["khist"]):
                    if th <= lag:
                        kp, rdy = v, rd
                        break
                # trim history
                if len(W["khist"]) > 4096:
                    W["khist"] = W["khist"][-2048:]
                if cfg.get("advert") == "preload":      # NEGATIVE: partner preloads C at its own reset
                    rdy = True
                avail = ((C if rdy else 0) + kp - P["sent"]) % (1 << Wc)
                if avail > C:
                    errs.append(f"CREDIT_OVERGRANT avail={avail} C={C}")
                    return
                ok = avail > 0
            elif cmode == "local":
                ok = P["sent"] - rb_vis < C
            elif cmode == "local_cdc_only":
                ok = W["wb"] - rb_vis < C
            else:
                raise ValueError(cmode)
            if ok:
                if first_send is None:
                    first_send = t
                P["link"].append((t + cfg["Lf"] * Tw - 1e-6, P["sent"]))
                P["sent"] += 1
                P["skip_ctr"] += 1
                flight_max = max(flight_max, P["sent"] - rb_vis)

    while min(tw, tr) < horizon and not errs:
        if t_done is not None and min(tw, tr) > t_done + tail_ps:
            break
        tnow = min(tw, tr)
        if not ev_done and tnow >= ev[0]:
            ev_done = True
            kind = ev[1]
            nw = tnow + rng.uniform(0, 40 * Tw)
            nr = tnow + rng.uniform(0, 40 * Tr)
            if kind == "coordinated":                   # cold POR to both endpoint domains AND the partner port
                fresh_read(); fresh_write(); fresh_partner()
                w_rel, r_rel = rel(nw, wph, Tw), rel(nr, rph, Tr)
                seq_out = 0
                t_grant = t_grant_of()
            elif kind == "stale_partner":               # NEGATIVE: endpoint reset, partner keeps credits / flight
                fresh_read(); fresh_write()
                w_rel, r_rel = rel(nw, wph, Tw), rel(nr, rph, Tr)
                t_grant = t_grant_of()
            elif kind == "read_only":                   # NEGATIVE: unilateral core-domain reset
                fresh_read()
                r_rel = rel(nr, rph, Tr)
        if tw <= tr:                                    # ================= write (PHY for RX) edge
            t = tw
            tw += Tw
            if t < w_rel:
                if any(a <= t for a, _ in P["link"]):
                    errs.append("LOSS_write_domain_in_reset")
                if cmode in ("gray", "binary", "pulse"):
                    partner(t, 0)                       # a remote partner is not reset with our PHY domain
                continue
            rb_vis = W["rb_sync"].visible()             # registered sync output (pre-edge)
            arr = [x for x in P["link"] if x[0] <= t]
            P["link"] = [x for x in P["link"] if x[0] > t]
            for _, s in arr:
                occ = W["wb"] - rb_vis
                occ_max = max(occ_max, occ + 1)
                if occ >= D:
                    errs.append(f"OVERFLOW occ={occ} D={D} seq={s}")
                    break
                W["mem"][W["wb"] % D] = s
                W["wb"] += 1
                R["wb_sync"].bump(t)
                if first_arrival is None:
                    first_arrival = t
            # credit counter as seen in this domain, history for the partner's return flight
            if cmode in ("gray", "binary", "pulse"):
                W["khist"].append((t, W["k_sync"].visible(), W["rdy1"]))
            partner(t, rb_vis)
            W["rb_sync"].edge(t)
            W["k_sync"].edge(t)
            lvl = t - meta >= t_grant if not (t_grant - meta <= t < t_grant) else rng.random() < 0.5
            W["rdy1"], W["rdy0"] = W["rdy0"], lvl
        else:                                           # ================= read (core for RX) edge
            t = tr
            tr += Tr
            if t < r_rel:
                continue
            R["rcyc"] += 1
            rc = R["rcyc"]
            wvis = R["wb_sync"].visible()
            out_r = True
            if out_r_pat != "always" and out_r_pat[0] == "stall":
                out_r = not (out_r_pat[1] <= rc < out_r_pat[1] + out_r_pat[2])
            mem = W["mem"]
            pop = None
            rb = R["rb"]
            if mode == "plain":
                if rb < wvis and out_r:
                    pop = mem[rb % D]
            elif mode == "serial3":
                h = R["head"]
                if h is None:
                    if rb < wvis:
                        s = mem[rb % D]
                        R["head"] = [s, rc + 2 + (ce_cyc if s in ce else 0)]
                elif rc >= h[1] and out_r:
                    pop = h[0]
                    R["head"] = None
            elif mode == "refill":                      # Codex B': pop at hp==2 reloads the next visible word
                h = R["head"]
                if h is None:
                    if rb < wvis:
                        s = mem[rb % D]
                        R["head"] = [s, rc + 2 + (ce_cyc if s in ce else 0)]
                elif rc >= h[1] and out_r:
                    pop = h[0]
                    if rb + 1 < wvis:                   # (rb_next Gray != wgs), registered sync value
                        s = mem[(rb + 1) % D]
                        R["head"] = [s, rc + 1 + (ce_cyc if s in ce else 0)]
                    else:
                        R["head"] = None
            elif mode == "rot3":
                b = R["banks"][rb % 3]
                if b is not None and rc >= b[1] and out_r:
                    pop = b[0]
                    R["banks"][rb % 3] = None
                cap = R["cap"]
                if cap < wvis and cap - rb < 3 and R["banks"][cap % 3] is None and \
                        not (pop is not None and cap % 3 == rb % 3):
                    s = mem[cap % D]
                    R["banks"][cap % 3] = [s, rc + 2 + (ce_cyc if s in ce else 0)]
                    R["cap"] = cap + 1
            if pop is not None:
                if pop != seq_out:
                    errs.append(f"ORDER got {pop} want {seq_out}")
                seq_out += 1
                R["rb"] += 1
                if mode != "rot3":
                    R["cap"] = R["rb"]
                W["rb_sync"].bump(t)
                R["wire"].append((rc + cfg["WSTG"], pop))
                last_pop = t

            while R["wire"] and R["wire"][0][0] <= rc:
                R["rbq"].append(R["wire"].pop(0)[1])
            if cfg.get("RB") is not None and len(R["rbq"]) > cfg["RB"]:
                errs.append("RB_OVERFLOW")
            rb_max = max(rb_max, len(R["rbq"]))
            cons = cfg.get("consumer", "always")
            go = True
            if cons != "always":
                if cons[0] == "random":
                    go = rng.random() < cons[1]
                elif cons[0] == "stall":
                    go = not (cons[1] <= rc < cons[1] + cons[2])
            if R["rbq"] and go:
                R["rbq"].pop(0)
                R["pops_total"] += 1
                if cmode in ("gray", "binary", "pulse"):
                    R["pending"] += 1
            # credit producer (core domain): retirement counter, one Gray step a cycle
            if cmode in ("gray", "binary", "pulse"):
                if R["pending"] > 0:
                    R["K"] += 1
                    R["pending"] -= 1
                    W["k_sync"].bump(t)
            R["wb_sync"].edge(t)
            if t_done is None and seq_out >= N and not R["wire"] and not R["rbq"] and R["pending"] == 0:
                t_done = t
    if not errs and seq_out < N:
        errs.append(f"INCOMPLETE {seq_out}/{N}")
    if not errs and cmode in ("gray", "binary", "pulse") and R["pending"] == 0:
        kv = W["k_sync"].visible()
        if kv != R["pops_total"]:
            errs.append(f"CREDIT_LEAK seen={kv} want={R['pops_total']}")
    span = (last_pop - first_arrival) if (first_arrival is not None and last_pop is not None) else None
    return dict(ok=not errs, errors=errs[:2], occ_max=occ_max, rb_max=rb_max, flight_max=flight_max,
                delivered=seq_out,
                flits_per_read_cycle=round((seq_out - 1) / (span / Tr), 4) if span and seq_out > 1 else None)


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
    """Equal-terms comparison A / B / B' / C plus the producer, reset and flight contract checks."""
    Tw = p["link_period_ps"]
    Tr = p["core_period_ps"]
    D, C, S = p["D"], p["SWCRED"], p["sync_stages"]
    ret_ps = p["credit_return_ns"] * 1000.0
    Lf_cons = p["rx_forward_flight_cycles"]
    seeds = range(4 if quick else 16)
    N = 600 if quick else 1500
    base = dict(Tw=Tw, Tr=Tr, D=D, N=N, Lf=8, WSTG=p["WSTG"], RB=2 ** p["RXAW"], ret_ps=ret_ps,
                credit_mode="gray", credit_bits=p["credit_counter_bits"], ce_cycles=p["ce_repair_cycles"],
                sync_stages=S, C=C)
    traffics = ["sustained", ("bursts", 300, 200), ("random", 0.7)]
    consumers = ["always", ("random", 0.5), ("stall", 400, 900)]
    rows = []
    H = p["head_latency_cycles"]
    bound0 = residency_bound(Tw, Tr, S, H, 1, 0, 0)
    Kb = 0
    while residency_bound(Tw, Tr, S, H, 1, Kb + 1, 0) <= D - 1:
        Kb += 1
    n_ok = Kb // p["ce_repair_cycles"]

    def run(name, over, expect_ok, vary=True, bound=None, min_rate=None, group="option"):
        res = []
        rng = random.Random(sum(map(ord, name)))
        grid = [(t, c) for t in traffics for c in consumers] if vary else [(None, None)]
        for t, c in grid:
            for s in seeds:
                cfg = dict(base, traffic="sustained", consumer="always",
                           reset=(rng.uniform(0, 30 * Tw), rng.uniform(0, 30 * Tr)))
                cfg.update(over)
                if vary:
                    cfg["traffic"], cfg["consumer"] = t, c
                if callable(cfg.get("ce")):
                    cfg["ce"] = cfg["ce"](random.Random(s))
                res.append(simulate(cfg, seed=s * 7919 + len(rows)))
        ok = all(r["ok"] for r in res)
        occ = max(r["occ_max"] for r in res)
        rates = [r["flits_per_read_cycle"] for r in res if r["flits_per_read_cycle"]]
        rate = round(min(rates), 4) if rates else None
        good = ok == expect_ok
        if expect_ok and bound is not None:
            good = good and occ <= bound
        if expect_ok and min_rate is not None:
            good = good and rate is not None and rate >= min_rate
        rows.append(dict(name=name, group=group, expect_ok=expect_ok, runs=len(res), all_ok=ok, occ_max=occ,
                         flight_max=max(r["flight_max"] for r in res), bound=bound, min_rate_required=min_rate,
                         min_rate=rate, errors=sorted({e.split(" ")[0] for r in res for e in r["errors"]}),
                         verdict="PASS" if good else "FAIL"))

    # ---------------- options on equal terms (RX, Gray credit producer, 256 credits unless stated)
    run("orig_II1_C256", dict(II_mode="plain"), True)
    run("NEG_candidate_II3_C256", dict(II_mode="serial3"), False, vary=False)
    run("A_II3_C64", dict(II_mode="serial3", C=D), True, bound=D)
    run("A_II3_C64_head_held_2000", dict(II_mode="serial3", C=D, out_r=("stall", 50, 2000)), True, vary=False,
        bound=D)
    run("NEG_A_II3_C65_head_held_2000", dict(II_mode="serial3", C=D + 1, out_r=("stall", 50, 2000)), False,
        vary=False)
    for m, tag in (("refill", "Bprime_refill"), ("rot3", "B_rot3")):
        run(f"{tag}_C256", dict(II_mode=m), True, bound=bound0)
        run(f"{tag}_C256_conservative_loop_full_rate", dict(II_mode=m, Lf=Lf_cons), True, vary=False,
            bound=bound0, min_rate=0.98)
        run(f"{tag}_ce_{n_ok}_within_budget", dict(II_mode=m, ce=lambda r: set(r.sample(range(50, N), n_ok))),
            True, vary=False, bound=residency_bound(Tw, Tr, S, H, 1, n_ok * p["ce_repair_cycles"], 0))
        run(f"NEG_{tag}_ce_storm_beyond_budget", dict(II_mode=m, ce=lambda r: set(range(100, 100 + 6 * (n_ok + 3), 3))),
            False, vary=False)
        run(f"NEG_{tag}_stress_read_1024p6ps", dict(II_mode=m, Tr=p["stress_read_period_ps"]), False, vary=False)
    run("C_II3_D256_C256", dict(II_mode="serial3", D=C), True, bound=C)
    # ---------------- producer contract (Gray counter, width, transport)
    g = "producer"
    run("P_gray_W9_conservation", dict(II_mode="refill", traffic=("bursts", 300, 200)), True, vary=False, group=g)
    run("NEG_P_width8_deadlock", dict(II_mode="refill", credit_bits=8), False, vary=False, group=g)
    run("NEG_P_binary_counter_sync", dict(II_mode="refill", credit_mode="binary", meta_ps=150.0, Tw=Tw * 1.003),
        False, vary=False, group=g)
    run("NEG_P_pulse_sync", dict(II_mode="refill", credit_mode="pulse", meta_ps=150.0, Tw=Tw * 1.003), False,
        vary=False, group=g)
    # ---------------- reset contract
    g = "reset"
    run("R_write_late_both_ready", dict(II_mode="refill", reset=(400 * Tw, 0.0)), True, vary=False, bound=bound0,
        group=g)
    run("R_read_late_both_ready", dict(II_mode="refill", reset=(0.0, 400 * Tr)), True, vary=False, bound=bound0,
        group=g)
    run("NEG_R_partner_preloaded_write_late", dict(II_mode="refill", reset=(400 * Tw, 0.0), advert="preload"),
        False, vary=False, group=g)
    run("NEG_R_partner_preloaded_read_late", dict(II_mode="refill", reset=(0.0, 400 * Tr), advert="preload"),
        False, vary=False, group=g)
    run("R_coordinated_midstream_reset", dict(II_mode="refill", reset_event=(300 * Tw, "coordinated")), True,
        vary=False, bound=bound0, group=g)
    run("NEG_R_stale_partner_credits", dict(II_mode="refill", reset_event=(300 * Tw, "stale_partner")), False,
        vary=False, group=g)
    run("NEG_R_unilateral_core_reset", dict(II_mode="refill", reset_event=(300 * Tw, "read_only")), False,
        vary=False, group=g)
    # ---------------- flight contract (TX: core writes, PHY pacer reads; local gate counts the WSTG flight)
    g = "flight"
    tx = dict(II_mode="refill", credit_mode="local", Lf=p["WSTG"], RB=None, Tw=Tr, Tr=Tw)
    run("F_TX_gate_D64_pacer_stall", dict(tx, C=D, out_r=("stall", 300, 500)), True, bound=D, group=g)
    run("NEG_F_TX_gate_ignores_wire_flight", dict(tx, C=D, credit_mode="local_cdc_only", out_r=("stall", 300, 500)),
        False, vary=False, group=g)
    run("F_TX_full_rate_at_Dtx_min", dict(tx, C=p["tx_min_depth_full_rate"]), True, vary=False,
        min_rate=0.98, group=g)
    run("F_TX_below_Dtx_min_rate_loss_info", dict(tx, C=p["tx_min_depth_full_rate"] - 8), True, vary=False,
        group=g)
    # ---------------- frequency lock / plesiochronous (write clock 1% fast = scaled ppm stress, short loop)
    g = "plesio"
    fast = Tw / 1.01
    run("PL_fast1pct_skip_every_50", dict(II_mode="refill", Tw=fast, skip_every=50, N=12000), True, vary=False,
        bound=D, group=g)
    run("NEG_PL_fast1pct_no_skip", dict(II_mode="refill", Tw=fast, N=12000), False, vary=False, group=g)
    run("NEG_PL_fast1pct_skip_every_200", dict(II_mode="refill", Tw=fast, skip_every=200, N=12000), False,
        vary=False, group=g)
    return rows


def refill_params(p):
    rm = json.loads((CDC_RES / "refill_model.json").read_text())
    nt = rm["normal_timing"]
    assert rm["width"] == p["W"] and rm["depth"] == p["D"] and nt["read_initiation_interval"] == 1
    return dict(II=nt["read_initiation_interval"], empty_start_cycles=nt["empty_start_capture_plus_validate_cycles"],
                additional_state_bits=rm["additional_state_bits"], status=rm["status"],
                measured=["results/rtl/hbm_collective_cdc_20261007/refill_pass/record.json (full 545x64 independent-clock stress)",
                          "results/rtl/hbm_collective_cdc_20261007/refill_nominal_pass/record.json (833/833 ps nominal)"],
                measured_pass=[json.loads((CDC_RES / x).read_text()).get("passed") for x in
                               ("refill_pass/record.json", "refill_nominal_pass/record.json")])


def contracts(p):
    """Producer / reset / flight contracts as exact inequalities (each has a simulator check and a negative)."""
    S, C, D, Wst = p["sync_stages"], p["SWCRED"], p["D"], p["WSTG"]
    rtt_lab = p["rx_credit_rtt_cycles"]
    rtt_cons = p["rx_forward_flight_cycles"] + (S + 1) + 3 + Wst + 2 + 1 + (S + 1) + \
        math.ceil(p["credit_return_ns"] * 1e-9 * p["clk_hz"])
    return dict(
        producer=dict(
            who="the RECEIVING endpoint produces every credit for its RX port (the native RTL has no producer: the "
                "tb stub preloads eg_cred=1<<RXAW and rx_credit=rb_pop is a core-clock pulse with no crossing)",
            counter="K: free-running RETIREMENT counter in the CORE domain, +1 per receive-buffer pop (never per "
                    "CDC pop), at most one step a core cycle, W_c = ceil(log2(C+1)) = %d bits, Gray-coded register; "
                    "READY: one level bit in the core domain" % p["credit_counter_bits"],
            crossing="K and READY -> %d-flop synchronisers in the PHY domain -> carried to the partner by the PHY TX "
                     "(control symbol / header field); the partner keeps sent (W_c bits) and spends "
                     "avail = (READY_seen ? C : 0) + K_seen - sent  (mod 2^W_c)" % S,
            grant="the initial C is NOT transported as counts: the partner adds the configured C when it sees READY "
                  "(a single synchronised level), so no multi-bit jump and no ramp backlog (a one-step-a-cycle ramp "
                  "of C grants shares the counter with pops and leaves a permanent pending backlog under a "
                  "continuous stream); 0 cycles per token",
            inequalities=["2^W_c > C (else avail = C reads 0: deadlock, NEG_P_width8_deadlock)",
                          "0 <= C + K_seen - sent <= C at the partner for every sample (Gray: old/new only; binary "
                          "multi-bit sampling over-grants, NEG_P_binary_counter_sync)",
                          "conservation after quiesce: K_seen == RB pops (pulse sync leaks, NEG_P_pulse_sync)",
                          "full rate: C >= RTT; labelled loop %d, conservative loop (fwd PHY+cable %d + CDC %d + "
                          "WSTG %d + RB 2 + K reg/sync %d + return %d) = %d cycles; margin %d" %
                          (rtt_lab, p["rx_forward_flight_cycles"], S + 4, Wst, S + 2,
                           math.ceil(p["credit_return_ns"] * 1e-9 * p["clk_hz"]), rtt_cons, C - rtt_cons)],
            rtt_conservative_cycles=rtt_cons, margin_cycles=C - rtt_cons),
        reset=dict(
            ordering="PHY (por_link) and core (por_stream) reset in either order; async assert, 2-edge local release",
            grant_rule="grant ramp starts only at t >= max(t_rel_core, t_rel_phy) + (S+1) cycles of the slower "
                       "domain, i.e. after endpoint_rearm_ready has seen both releases and the reset values of every "
                       "Gray rail were flushed through the synchronisers",
            entry="cold POR is coordinated with the partner port (link down): partner sent/credit state and PHY "
                  "in-flight flits are discarded with the endpoint queues; a new generation re-grants C",
            exit="no flit can reach the CDC write port before its domain is released because the partner holds 0 "
                 "credits until the first grant",
            forbidden=["partner keeps credits/flight across an endpoint reset (NEG_R_stale_partner_credits)",
                       "unilateral runtime reset of one domain (NEG_R_unilateral_core_reset: read pointer restarts "
                       "against a live write pointer -> stale/out-of-order data)",
                       "partner credits preloaded at the partner's own reset, as the current tb stub does "
                       "(eg_cred=1<<RXAW): write domain late -> loss, read domain late -> overflow "
                       "(NEG_R_partner_preloaded_*)"]),
        flight=dict(
            tx_gate="issue a TX flit only while issued - sync(rb_tx) < D_tx; this counts the %d WSTG stages and the "
                    "Gray/sync lag, so WSTG flight + CDC occupancy <= D_tx for any pacer stall (exact)" % Wst,
            tx_full_rate="D_tx >= WSTG + 1 + (S+1) + %d + 1 + (S+1) + 1 = %d (model; checked)" %
                         (p["refill_empty_start"], p["tx_min_depth_full_rate"]),
            negative="gating on CDC occupancy alone overflows by the WSTG flight under a pacer stall",
            switch_ingress="SWCRED=256 switch-ingress credits cover the TX loop (WSTG + CDC + PHY/cable/switch + "
                           "113.8 ns return + RX Gray sync) ~= the conservative RX loop, %d cycles, margin %d" %
                           (rtt_cons, C - rtt_cons)),
        frequency=dict(
            locked="Tw == Tr (same reference, independent phase): drain II=1 >= arrival; occupancy <= %d" %
                   residency_bound(p["link_period_ps"], p["core_period_ps"], S, p["head_latency_cycles"], 1, 0, 0),
            plesiochronous="f_phy = f_core (1+delta): the partner must leave >= 1 idle per M flits with "
                           "M <= (Tw/Tr)/(1 - Tw/Tr) ~= 1/delta (200 ppm -> M <= 4999); checked at delta = 1%% with "
                           "M = 50 (pass) and M = 200 / no idle (overflow). Ethernet rate matching (IPG / alignment "
                           "marker deletion) must be shown to deliver this to the endpoint, else lock the clocks",
            credit_starved="if the partner is credit-starved and the drain is slower than arrival, the CDC settles at "
                           "C - r_drain * L_loop_min flits; a third legal route is therefore C <= D - 1 - base + "
                           "r_drain * L_loop_min with a MEASURED physical lower bound on the loop latency (short-loop "
                           "negatives NEG_PL_* and NEG_*_stress_read_1024p6ps overflow; not relied on)"))


def refill_area_timing(p):
    dff = p["dff_um2_per_bit"]
    return dict(
        basis="structural estimate from ot_hbm_collective_protected_cdc_refill.sv (Codex measures mapping/SS/FF)",
        state_bits_added=0,
        logic_added_per_fifo="rb_next Gray (6 XOR2) + 7-bit compare with wgs (7 XNOR + AND tree) + refill AND + "
                             "6-bit address 2:1 mux + load OR + hp next-state term: ~35 cells",
        area_um2_added_16_fifos="~60-100 (35 cells x 0.1-0.18 um2 x 16), i.e. < 0.05 % of the 193,492 um2 "
                                "encoded storage; vs B rotation +12,093 um2",
        critical_path_as_written="head bank Q -> 14 x check72 syndromes (7 XOR levels) -> normal/out_v (OR, 4) -> "
                                 "pop (2) -> refill (1) -> address select refill?rb_next:rb -> buffer tree to the "
                                 "64:1 x 648 read-mux selects (fan-out ~20k pins on the LSB, ~6 levels) -> mux tree "
                                 "(6) -> bank load mux (1) -> D: ~27 levels, est. 650-800 ps SS vs 773 ps budget "
                                 "(833 - 60 uncertainty): AT RISK",
        fix_no_function_change="drive the read address from REGISTERED hp: addr = (hp==0) ? rb : rb_next. Load is only "
                               "asserted on capture (hp==0) or refill (hp==2), so encoded_d is identical; the read mux "
                               "then starts from flops (~12 levels, ~350 ps) and the late path is syndrome -> pop -> "
                               "refill -> load-enable fan-out (648 b, ~5 levels): ~19 levels, est. 480-570 ps",
        same_as_II3="syndrome -> hn -> capture -> load already exists in the II3 candidate; only the refill -> "
                    "address-select edge is new",
        activity="the head bank reloads 648 encoded bits and the read mux switches every cycle in a stream (3x the "
                 "II3 data activity on that path); clocked flop count unchanged; no measured power")


def compare(p, wl, opt, rp):
    """B' (Codex's measured refill) vs B (rotation) vs A / C on equal terms."""
    S, D, H = p["sync_stages"], p["D"], p["head_latency_cycles"]
    Tw, Tr = p["link_period_ps"], p["core_period_ps"]
    K = 0
    while residency_bound(Tw, Tr, S, H, 1, K + 1, 0) <= D - 1:
        K += 1
    B = opt["B_rotated_II1"]
    bp = dict(
        summary="Codex II1 refill: on an accepted pop with the next word already visible (rb_next Gray != wgs) the "
                "SAME protected head bank loads the next encoded word and stays in present; empty start keeps "
                "capture + validate; CE/UE permissions unchanged",
        measured=rp["measured"], measured_pass=rp["measured_pass"],
        throughput_flits_per_edge=1.0, empty_start_cycles=rp["empty_start_cycles"],
        occupancy_bound=residency_bound(Tw, Tr, S, H, 1, 0, 0), ce_stall_budget_read_cycles=K,
        ce_repairs_tolerated_per_gap_free_stream=K // p["ce_repair_cycles"],
        cost_serialisation=B["cost_serialisation"], cost_latency=B["cost_latency"],
        state_bits_added=rp["additional_state_bits"], area=refill_area_timing(p))
    rows = {}
    for k, o in (("A_credit_bound", opt["A_credit_bound"]), ("B_rotated_II1", B), ("Bprime_refill_II1", bp),
                 ("C_deep_fifo", opt["C_deep_fifo"])):
        rows[k] = dict(throughput=o["throughput_flits_per_edge"],
                       AR_us=o["cost_serialisation"]["AR_us"] + o["cost_latency"]["AR_us"],
                       MTP_step_us=o["cost_serialisation"]["MTP_step_us"] + o["cost_latency"]["MTP_step_us"],
                       area_um2_added={"A_credit_bound": 0, "B_rotated_II1": B["area_um2_added"],
                                       "Bprime_refill_II1": "~60-100 (logic only)",
                                       "C_deep_fifo": opt["C_deep_fifo"]["area_um2_added_flops"]}[k],
                       credits=64 if k == "A_credit_bound" else 256,
                       evidence={"Bprime_refill_II1": "RTL measured by Codex + this model"}.get(k, "this model only"))
    return bp, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/rtl/hbm_collective_cdc_design_20261007"))
    ap.add_argument("--name", default="comparison_refill.json")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    pins = verify_inputs()
    p = params()
    rp = refill_params(p)
    p["refill_empty_start"] = rp["empty_start_cycles"]
    wl = workload()
    opt, common = analytic(p, wl)
    bp, table = compare(p, wl, opt, rp)
    con = contracts(p)
    rows = campaign(p, a.quick)
    verdict = all(r["verdict"] == "PASS" for r in rows)
    bprime_ok = all(r["verdict"] == "PASS" for r in rows if "refill" in r["name"] or r["group"] != "option")
    out = dict(
        schema="opentallas.hbm-collective-cdc-design.v2",
        status="DESIGN_MODEL_RECOMMENDATION (no RTL change; RTL owned by Codex /hbm/collective)",
        supersedes_nothing="results/rtl/hbm_collective_cdc_design_20261007/options.json (b49366616, recommended B "
                           "rotation) is kept as its own historical record",
        recommendation="Bprime_refill_II1" if bprime_ok else "B_rotated_II1",
        recommendation_basis="B' meets every producer/reset/flight/frequency contract check below on equal terms with "
                             "B, adds 0 state bits (B: +12,093 um2), and is measured RTL owned by the implementer; "
                             "B rotation stays the fallback only if B' cannot close SS after the registered-hp "
                             "address fix",
        comparison=table, options=dict(opt, Bprime_refill_II1=bp), contracts=con,
        params=p, workload=wl, common=common,
        simulation=dict(model="cycle-accurate two-clock queue: independent clock edges with random phase; registered "
                              "Gray pointers and the Gray credit counter through 2-flop synchronisers (pre-edge "
                              "values used, 20 ps metastability window resolving old/new); staggered and mid-stream "
                              "reset; credit return flight; CE held-repair stalls; order, loss, overflow, over-grant "
                              "and credit conservation asserted on every run",
                        rows=rows, all_pass=verdict),
        inputs=pins,
        sources={k: dict(path=v, sha256=sha(ROOT / v)) for k, v in SRC.items()},
        tool_sha256=sha(Path(__file__)),
    )
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    (od / a.name).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['verdict']:4s} {r['group']:8s} {r['name']:46s} ok={r['all_ok']!s:5s} occ={r['occ_max']:4d} "
              f"fl={r['flight_max']:4d} bound={r['bound']} rate={r['min_rate']} {','.join(r['errors'])}")
    for k, v in table.items():
        print(k, v)
    print("RECOMMEND", out["recommendation"], "ALL_PASS", verdict)
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
