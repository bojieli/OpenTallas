#!/usr/bin/env python3
"""Sustained HBM3E read bandwidth per stack for the Qwen3-8B ROM near-HBM attention stream.

Model before build (AGENTS.md design method 1).  Derives, from the HBM3E timing the
repository already sources, the rate one stack can deliver to ONE in-order local consumer
for the near-HBM KV pattern, and the controller needed to issue at that rate:

  * KV striped stack = (t mod 512) div 128; per layer per stack the stream is
    K(head A), K(head B), V(head A), V(head B), FP8, 2,048 positions x 128 B each
    = 1,048,576 B, read sequentially;
  * the stream must finish in 1 MiB / 0.9 TB/s = 1,165 ns (700 + 700 cycles at 1.2 GHz in
    /tmp/claude-review-20261003/nearhbm/near_hbm_attention_pricing.md r1/r2).

Two parts:
  1. closed-form bounds (peak, command buses, tCCD_L, tFAW/tRRD, row locality, refresh,
     start-up latency) and the r14/credit17 controller ceilings;
  2. a per-pseudo-channel cycle model of the proposed streaming sequencer (the RTL
     ot_hbm_r14_stream_pc implements the same policy), run over one token (36 layers at the
     r2 layer period) at several refresh phases and back-to-back, for REFab and for
     stream-aware REFpb, both strictly on schedule.

Writes results/uarch/qwen_hbm_sustained_bw_20261003/model-r1.json (canonical JSON).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/uarch/qwen_hbm_sustained_bw_20261003/model-r1.json"

SOURCES = [
    "rtl/hdc/kv/ot_hdc_hbm_model.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv",
    "rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv",
    "physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json",
    "configs/hardware/technology.json",
    "results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json",
]

# --- HBM3E timing (ps): rtl/hdc/kv/ot_hdc_hbm_model.sv parameter defaults -------------
# Ramulator 2 HBM3 6400 preset (CMU-SAFARI/ramulator2 hbm3.py @72427a1) for core timings,
# JESD238 for tREFI/tRFC; tRFCpb from rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv (JESD238 Table 93
# via Ramulator 2).  tRREFD is NOT sourced in the repository: assumed 8 ns.
PS = dict(BURST=1024, TCCDL=2560, CL=12500, RCDRD=19375, RP=16250, RAS=28125, RTP=5625,
          RRDS=2500, RRDL=3125, FAW=15000, RFC=350000, RFCPB=200000, REFI=3900000,
          RSP=10000, RREFD=8000)
PS_SOURCE = {
    "BURST": "ot_hdc_hbm_model.sv BURST_PS (tCCD_S = BL8 = 2 tCK at tCK 512 ps, 7.8125 Gb/s)",
    "TCCDL": "ot_hdc_hbm_model.sv TCCDL_PS", "CL": "ot_hdc_hbm_model.sv CL_PS",
    "RCDRD": "ot_hdc_hbm_model.sv RCDRD_PS", "RP": "ot_hdc_hbm_model.sv RP_PS",
    "RAS": "ot_hdc_hbm_model.sv RAS_PS", "RTP": "ot_hdc_hbm_model.sv RTP_PS",
    "RRDS": "ot_hdc_hbm_model.sv RRDS_PS", "RRDL": "ot_hdc_hbm_model.sv RRDL_PS",
    "FAW": "ot_hdc_hbm_model.sv FAW_PS",
    "RFC": "ot_hdc_hbm_model.sv RFC_PS (JESD238, 16 Gb dies 8-high)",
    "REFI": "ot_hdc_hbm_model.sv REFI_PS (JESD238)",
    "RFCPB": "ot_hdc_v41x_idx_hbm.sv RFCPB_PS (JESD238 Table 93 via Ramulator 2 72427a1)",
    "RSP": "ot_hdc_hbm_model.sv RSP_PS (PHY + controller response path, assumed)",
    "RREFD": "ASSUMED (not in repository): REFpb-to-ACT/REFpb spacing, other bank",
}
NB = 32          # banks per PC: 2 SID x 4 BG x 4 (ot_hdc_hbm_model.sv)
NPC = 32         # pseudo-channels per stack (ot_hbm3e_phy.json, JESD238)
SECTOR = 32      # bytes per BL8 burst on a 32-bit PC
ROW_B = 1024     # row (page) per bank per PC
PEAK = 1.0e12    # configs/hardware/technology.json hbm.hbm3e.stack_bandwidth_bytes_s

IDLE_ORDER = [3, 4, 2, 5, 1, 6, 0, 7]   # idle, nothing posted: middle sets first, the extremes last
STREAM_PREF = "near"                    # in-stream: upcoming nearest first, then passed
ENDLESS = False                         # back-to-back: the next descriptor is posted while streaming
BALANCE = 0
HINT = 320                              # descriptor posted this many cycles before go (>= LEAD+tRFCpb+tRCD)
CYC_PS = 2 * 512  # controller clock = HBM CK / 2 (DFI 1:2), tCK 512 ps -> 1.024 ns


def cyc(name: str) -> int:
    return math.ceil(PS[name] / CYC_PS)


T = {k: cyc(k) for k in PS}
T["REFI"] = PS["REFI"] // CYC_PS                    # strict: never later than tREFI
T["REFIPB"] = 2 * (PS["REFI"] // NB // CYC_PS // 2)  # tREFIpb = tREFI / banks, even (2-PC TDM row slot): 118
T["CL_RET"] = T["CL"] + 1 + T["RSP"]                # RD -> data at the consumer

LAYERS = 36
BYTES_LAYER_STACK = 2048 * 2 * 128 * 2              # positions/stack x KV heads x d x (K,V)
SECT_LAYER_PC = BYTES_LAYER_STACK // SECTOR // NPC  # 1,024
NEED_BPS = 0.9e12
NEED_NS = BYTES_LAYER_STACK / NEED_BPS * 1e9
LAYER_PERIOD_NS = 6281 / 1.2                         # r2 per-layer cycles at 1.2 GHz


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------
# Part 2: per-PC cycle model of the streaming sequencer (policy = RTL ot_hbm_r14_stream_pc)
# ------------------------------------------------------------------------------------
def bank_of(j: int) -> int:
    return ((j >> 7) & 7) * 4 + (j & 3)


class PC:
    def __init__(self, p: int, refpb: bool, phase: int):
        self.refpb = refpb
        period = T["REFIPB"] if refpb else T["REFI"]
        self.period = period
        self.next_due = (phase + (p * period) // NPC) % period + period
        self.open = [False] * NB
        self.act_t = [-10**9] * NB
        self.act_ok = [0] * NB
        self.last_rd = [-10**9] * NB
        self.done = [False] * NB
        self.last_act = -10**9
        self.last_act_bg = [-10**9] * 4
        self.faw = [-10**9] * 4
        self.last_rd_bg = [-10**9] * 4
        self.no_act_until = 0
        self.refreshed = 0
        self.rb = -1
        self.choose_lead = T["RAS"] + T["RP"] + 4
        self.j = 0
        self.n = 0
        self.lat_ref = 0          # REF lateness (must stay 0)
        self.forced = 0           # REFpb choices that hit an open/protected bank
        self.refs = 0
        self.rows_act = 0
        self.last_step = 0
        self.go = False
        self.stale = [False] * NB

    # -- refresh helpers --------------------------------------------------------------
    def choose(self) -> int:
        """REFpb bank of the round (RTL ot_hbm_r14_stream_pc key[] / bsel, same formula)."""
        best, bk = None, -1
        streaming = self.j < self.n             # posted or running
        k = (self.j >> 7) & 7
        last = ((self.n - 1) >> 7) & 7 if self.n else -1
        for b in range(NB):
            if self.refreshed >> b & 1:
                continue
            s = b >> 2
            d = (s - k) % 8
            if streaming:
                ahead = (k <= s <= last) or ENDLESS
                if self.open[b]:
                    key = 24 if (self.done[b] or self.stale[b]) else 32
                elif ahead and d <= 2:
                    key = 16 + (2 - d)          # protected: forced only, farthest first
                elif ahead:
                    key = d                     # upcoming (wrapping into the posted next layer)
                else:
                    key = 8 + s                 # passed / outside the descriptor
            else:
                key = IDLE_ORDER.index(s) + (32 if self.open[b] else 0)
            if not self.open[b] and self.act_ok[b] > self.next_due:
                key += 64                       # still in a previous tRFCpb / tRC
            if best is None or key < best:
                best, bk = key, b
        if best is not None and best >= 16:
            self.forced += 1
        return bk

    def step(self, t: int) -> int | None:
        """Advance one cycle; return the cycle of a RD issued (or None)."""
        due = self.next_due
        row_used = False
        rd_block_all = False
        act_block_all = False
        if self.refpb:
            if t == due - self.choose_lead:
                self.rb = self.choose()
            if due - T["RREFD"] < t < due:
                act_block_all = True
            if t == due:
                b = self.rb
                if b < 0 or self.open[b] or t < self.act_ok[b]:
                    self.lat_ref += 1        # illegal REFpb (bank open / tRP unmet): must stay 0
                self.act_ok[b] = max(self.act_ok[b], t + T["RFCPB"])
                self.no_act_until = t + T["RREFD"]
                self.refreshed |= 1 << b
                if self.refreshed == (1 << NB) - 1:
                    self.refreshed = 0
                self.next_due += self.period
                self.refs += 1
                self.rb = -1
                row_used = True
            elif self.rb >= 0 and self.open[self.rb]:
                b = self.rb
                if t >= self.act_t[b] + T["RAS"] and t >= self.last_rd[b] + T["RTP"]:
                    self.open[b] = False
                    self.stale[b] = False
                    self.act_ok[b] = max(self.act_ok[b], t + T["RP"])
                    row_used = True
        else:
            if t >= due - T["RP"] - T["RAS"] - 2:
                act_block_all = True
            if t >= due - T["RP"] - T["RTP"] - 2:
                rd_block_all = True
            if t == due - T["RP"] - 2 and any(self.open):
                for b in range(NB):
                    if self.open[b]:
                        assert t >= self.act_t[b] + T["RAS"] and t >= self.last_rd[b] + T["RTP"]
                        self.open[b] = False
                        self.stale[b] = False
                row_used = True
            if t == due:
                for b in range(NB):
                    self.act_ok[b] = max(self.act_ok[b], t + T["RFC"])
                self.next_due += self.period
                self.refs += 1
                row_used = True
        # -- stream ACT (sets k and k+1) or PRE of finished banks -----------------------
        if not row_used and self.j < self.n:
            k = (self.j >> 7) & 7
            last = ((self.n - 1) >> 7) & 7
            for s in range(k, min(k + 1, last) + 1):
                for g in range(4):
                    b = s * 4 + g
                    if self.done[b] or b == self.rb:
                        continue
                    if self.open[b]:
                        continue
                    if (act_block_all or t < self.no_act_until or t < self.act_ok[b]
                            or t < self.last_act + T["RRDS"] or t < self.last_act_bg[g] + T["RRDL"]
                            or t < self.faw[0] + T["FAW"]):
                        continue
                    self.open[b] = True
                    self.act_t[b] = t
                    self.last_act = t
                    self.last_act_bg[g] = t
                    self.faw = self.faw[1:] + [t]
                    self.act_ok[b] = t + T["RAS"] + T["RP"]
                    self.rows_act += 1
                    row_used = True
                    break
                if row_used:
                    break
        if not row_used:
            for b in range(NB):
                if self.open[b] and (self.done[b] or self.stale[b]) and b != self.rb and \
                        t >= self.act_t[b] + T["RAS"] and t >= self.last_rd[b] + T["RTP"]:
                    self.open[b] = False
                    self.stale[b] = False
                    self.act_ok[b] = max(self.act_ok[b], t + T["RP"])
                    break
        # -- column: one RD per cycle (tCCD_S = 1 cycle) --------------------------------
        if self.go and self.j < self.n and not rd_block_all:
            j = self.j
            b, g = bank_of(j), j & 3
            if self.open[b] and not self.stale[b] and b != self.rb and t >= self.act_t[b] + T["RCDRD"] \
                    and t >= self.last_rd_bg[g] + T["TCCDL"]:
                self.last_rd[b] = t
                self.last_rd_bg[g] = t
                if (j >> 2) & 31 == 31:
                    self.done[b] = True
                self.j += 1
                return t
        return None

    def start(self, n: int):
        self.go = False
        self.j, self.n = 0, n
        self.stale = self.open[:]           # rows of the previous descriptor close first
        self.done = [False] * NB


def run_token(refpb: bool, phase: int, period_cycles: float | None, layers: int = LAYERS):
    """period_cycles None => back-to-back layers (each layer starts when the last ended)."""
    pcs = [PC(p, refpb, phase) for p in range(NPC)]
    per_layer = []
    t0 = 0
    for L in range(layers):
        start = t0 if period_cycles is None else int(round(L * period_cycles))
        post = start if period_cycles is None else max(start - HINT, t0)
        # idle (between streams, no descriptor posted): only refresh events act; step each
        # PC from its last stepped cycle through every refresh choose..due window
        for pc in pcs:
            tt = pc.last_step
            while tt < post:
                lo = pc.next_due - pc.choose_lead
                if tt < lo:
                    tt = min(lo, post)
                    continue
                pc.step(tt)
                tt += 1
            pc.last_step = post
        for pc in pcs:
            pc.start(SECT_LAYER_PC)
        for tt in range(post, start):          # posted: protection on, rows open ahead
            for pc in pcs:
                pc.step(tt)
        for pc in pcs:
            pc.go = True
        t = start
        first_rd = [None] * NPC
        last_rd = [None] * NPC
        while any(pc.j < pc.n for pc in pcs):
            for p, pc in enumerate(pcs):
                r = pc.step(t)
                if r is not None:
                    if first_rd[p] is None:
                        first_rd[p] = r
                    last_rd[p] = r
            t += 1
        # drain: finish PRE of the last set while idle
        for pc in pcs:
            pc.last_step = t
            pc.n = 0
            pc.go = False
        first = min(first_rd) + T["CL_RET"] + 1 - start
        end = max(last_rd) + T["CL_RET"] + 1 - start
        per_layer.append(dict(first_data_cycles=first, end_cycles=end,
                              stream_ns=end * CYC_PS / 1000,
                              data_ns=(end - first) * CYC_PS / 1000))
        t0 = max(last_rd) + T["CL_RET"] + 1
    forced = sum(pc.forced for pc in pcs)
    refs = sum(pc.refs for pc in pcs)
    ends = [x["stream_ns"] for x in per_layer]
    return dict(per_layer_stream_ns=[round(x, 3) for x in ends],
                worst_stream_ns=max(ends), mean_stream_ns=sum(ends) / len(ends),
                first_data_ns=min(x["first_data_cycles"] for x in per_layer) * CYC_PS / 1000,
                layers_over_need=sum(1 for x in ends if x > NEED_NS),
                forced_refpb_choices=forced, refreshes=refs)


def model(full: bool = True) -> dict:
    srcs = {s: sha(s) for s in SOURCES}
    burst_ns = PS["BURST"] / 1000
    pc_peak = SECTOR / (burst_ns * 1e-9)
    peak = pc_peak * NPC
    layer_peak_ns = SECT_LAYER_PC * burst_ns
    # closed-form refresh
    refab_loss_ns = (PS["RP"] + PS["RFC"] + PS["RCDRD"]) / 1000      # PREab, REFab, re-ACT
    refab_long_run = 1 - refab_loss_ns / (PS["REFI"] / 1000)
    start_ns = (1 + T["RCDRD"] + T["CL_RET"]) * CYC_PS / 1000
    bounds = {
        "peak_Bps": peak,
        "peak_matches_technology_json": abs(peak - PEAK) / PEAK < 1e-9,
        "per_PC_peak_Bps": pc_peak,
        "layer_bytes_per_stack": BYTES_LAYER_STACK,
        "layer_sectors_per_PC": SECT_LAYER_PC,
        "layer_ns_at_peak": layer_peak_ns,
        "layer_ns_needed_at_0p9TBps": NEED_NS,
        "layer_slack_ns_at_peak": NEED_NS - layer_peak_ns,
        "startup_latency_ns_first_data": start_ns,
        "column_bus": {
            "organisation": "JESD238 via ot_hbm3e_phy.json: 16 independent 64-bit channels, each two 32-bit PCs; column commands of a channel share its column C/A, 1 tCK each",
            "need_per_PC": "1 RD per 2 tCK (BL8)",
            "channel_column_utilisation_at_peak": 1.0,
            "verdict": "feasible: every column slot carries a RD; no WR/turnaround inside the stream",
        },
        "row_bus": {
            "ACT_per_PC_per_layer": NB, "PRE_per_PC_per_layer": NB,
            "REFpb_per_PC_per_layer_at_peak": layer_peak_ns / (PS["REFI"] / NB / 1000),
            "assumed_row_slot": "one row command per channel per controller cycle (2 tCK), shared by its 2 PCs",
            "row_utilisation_per_channel": (2 * (2 * NB) + 2 * layer_peak_ns / (PS["REFI"] / NB / 1000)) / SECT_LAYER_PC,
        },
        "tCCD_L": {"cycles": T["TCCDL"], "same_BG_RD_spacing_cycles": 4,
                   "verdict": "BG rotates every sector, so a BG is read every 4 cycles >= tCCD_L"},
        "tFAW_tRRD": {"ACT_needed_per_FAW": 4 * PS["FAW"] / 1000 / (4 * 32 * burst_ns),
                      "verdict": "4 ACT per 131 ns needed against 4 per 15 ns allowed"},
        "row_locality": {"row_hit_fraction": 1 - 1 / (ROW_B // SECTOR),
                         "sectors_per_ACT": ROW_B // SECTOR,
                         "verdict": "every bank opened once per layer and read end to end; ACT of the next bank set is issued one set ahead, so tRCD and tRP are hidden"},
        "refresh_REFab_strict": {
            "loss_per_event_ns": refab_loss_ns,
            "long_run_fraction_of_peak": refab_long_run,
            "long_run_Bps": peak * refab_long_run,
            "layer_ns_if_hit": layer_peak_ns + refab_loss_ns + start_ns,
            "layer_Bps_if_hit": BYTES_LAYER_STACK / ((layer_peak_ns + refab_loss_ns + start_ns) * 1e-9),
            "note": "an in-order stream striped over all 32 PCs waits for the slowest PC; with PCs staggered by tREFI/32 = 121.9 ns, a 1.05 us stream almost always overlaps some PC's REFab",
        },
        "refresh_REFpb_stream_aware": {
            "tREFIpb_ns": PS["REFI"] / NB / 1000, "tRFCpb_ns": PS["RFCPB"] / 1000,
            "bank_busy_fraction": PS["RFCPB"] / (PS["REFI"] / NB) / NB,
            "data_bus_loss": 0.0,
            "condition": "the refreshed bank is neither open nor needed within tRFCpb + tRCD (the stream's current set and next two)",
        },
    }
    ctrl = {
        "r14_credit17_today": {
            "per_PC_accept_II_edges": 5, "clock_GHz": 1.0,
            "LEN1_cap_Bps": NPC * SECTOR / 5e-9,
            "column_paths_per_stack": 4, "column_path_cap_Bps": 4 * SECTOR / 1e-9,
            "tCCD_S_edges_ceil_at_1GHz": 2, "tCCD_S_ceil_cap_Bps": NPC * SECTOR / 2e-9,
            "source": "results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json controller / column_paths_per_stack; ot_hbm_r14_pc.sv last_col+2",
        },
        "needed": {
            "RD_per_PC_per_ns": 1 / burst_ns,
            "clock": "controller at HBM CK/2 = 976.5625 MHz (DFI 1:2), tCCD_S = 1 cycle exactly; a 1.2 GHz clock would need fractional (phase) issue",
            "accept": "one descriptor per layer per PC (row, sector count); the sequencer generates 1 RD/cycle with no per-sector request",
            "row_bus": "one row-command slot per channel per cycle shared by 2 PCs",
            "return_width_bits_per_PC_cycle": 256,
            "return_B_per_1p2GHz_edge_per_stack_at_peak": peak / 1.2e9,
        },
        "cycles": {k: T[k] for k in sorted(T)},
        "cycle_ps": CYC_PS,
    }
    out = {
        "schema": "opentallas.qwen-hbm-sustained-bw-model.v1",
        "model_only": True,
        "sources_sha256": srcs,
        "timing_ps": PS, "timing_source": PS_SOURCE,
        "pattern": {
            "stack_of_position": "(t mod 512) div 128",
            "order_per_layer": "K(head A), K(head B), V(head A), V(head B); FP8; 2,048 positions per stack",
            "bytes_per_layer_per_stack": BYTES_LAYER_STACK,
            "address_map_low_to_high": "BG[1:0] | PC[4:0] | column[4:0] (32 sectors = 1 KB row) | bank-set[2:0] (SID + bank-in-group) | row = layer + 36 x context block",
            "consequence": "one layer of one stack = one row index in every bank of every PC; each bank opened once per layer, 32 row hits per ACT; a 128 B KV row (one position, one head) is one PC's 4 BG sectors",
            "need_Bps": NEED_BPS, "need_layer_ns": NEED_NS,
            "layer_period_ns": LAYER_PERIOD_NS,
        },
        "bounds": bounds,
        "controller": ctrl,
    }
    if full:
        global HINT, ENDLESS
        period = LAYER_PERIOD_NS * 1000 / CYC_PS
        runs = {}
        ph_pb = list(range(0, T["REFIPB"], 15))
        ph_ab = [0, 977, 1953, 2930]
        for hint in (320, 200, 100, 0):
            HINT, ENDLESS = hint, False
            runs[f"REFpb_stream_aware_hint{hint}"] = {str(ph): run_token(True, ph, period) for ph in ph_pb}
        HINT = 320
        runs["REFab_staggered_hint320"] = {str(ph): run_token(False, ph, period) for ph in ph_ab}
        ENDLESS = True
        runs["REFpb_stream_aware_back_to_back"] = {"0": run_token(True, 0, None)}
        ENDLESS = False
        out["cycle_model"] = {"runs": runs, "layer_period_cycles": period, "hint_cycles_primary": 320,
                              "idle_order": IDLE_ORDER, "stream_pref": STREAM_PREF}
        summ = {}
        for name, r in runs.items():
            worst = max(v["worst_stream_ns"] for v in r.values())
            mean = sum(v["mean_stream_ns"] for v in r.values()) / len(r)
            summ[name] = {
                "worst_layer_stream_ns": worst, "mean_layer_stream_ns": mean,
                "worst_layer_effective_Bps": BYTES_LAYER_STACK / (worst * 1e-9),
                "mean_layer_effective_Bps": BYTES_LAYER_STACK / (mean * 1e-9),
                "layers_over_need": sum(v["layers_over_need"] for v in r.values()),
                "layers": LAYERS * len(r),
                "meets_0p9TBps_every_layer": worst <= NEED_NS,
                "forced_REFpb_choices": sum(v["forced_refpb_choices"] for v in r.values()),
            }
        out["summary"] = summ
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", default=str(OUT))
    a = ap.parse_args()
    data = model()
    Path(a.result).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data.get("summary", {}), indent=2))


if __name__ == "__main__":
    main()
