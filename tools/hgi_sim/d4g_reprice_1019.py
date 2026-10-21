#!/usr/bin/env python3
"""HBM-REPRICE (10-19): re-price the HBM d4g token (DS AR + Qwen3-8B AR; MTP is the next release) with EVERY latency /
throughput change recorded since GEN2, each one an explicit knob of this file (TERMS below; no hidden constants).

BASE = d4g_2ring_qbg of the HBM-B-RTL3 / HBM-PRICE5 pricer (hgi_sim.d4g_quadrant_1017: plan_study machinery + quadrant
placement + static-schedule adders AG/XQT/D2/SU/SFUD/SFUC/BD, two rings + QBG) with the latency ledger AS PRICED
(hc_tree 28 + 2 XQ: the ledger snapshot of the price of record, 1905.4 / 946.2).  This is the basis of the token
composition (tools/token_compose_xdie.py hbm_ds: hds_sched reproduces 629,775.1 cycles).  The accepted-cost ledger price of
record (HBM.D4G_PLAN_B, DS AR 1849.2) = BASE + term `collq` below.

Every term is priced ALONE on top of BASE (`only_<term>`) and ALL together (`all`); the composed delta of `all` minus the
sum of the single-term deltas is reported as the interaction.  Grades: measured (the latency is a bench / RTL measurement
on current RTL; the exposure comes from the S2 static schedule), priced (analytic rule / contract on a measured anchor),
modelled (estimate pending an RTL measurement or a lane decision).

The per-record rules (`rp` knob on the d4g knob; applied after d4g_quadrant_1017.d4g_added on the record's unit cost):
  collq        MEASURED COLL gather master spans + ISA ring-A +2 (HBM-COLLQ, d4g_collq_price_1018: ag_collq + ra_extra).
  pg_cmd       pgslice_lg LANDED region form (TW-HBM-PGLG e7ea9096c, bench m0 PASS 8db52396a): lane commands r1/r2 +2,
               r0/r3 +5 edges; the 128 lanes are lockstep, so an SU-executed record ends on the slowest region: +5.
  pg_operand   same: red_sel / tree_cmd / rf_dsec issued +10, slice_x / tree_o / pt_ro / inj_q +10: +10 on an SU
               reduction record (sut.red) -- the reducer operand reaches qcore 10 edges later.
  pg_vmwrite   same: drain VM write +12 serial (+16 stream): +12 on an SU-executed record that writes VM.
  pg_reset     same: pg_stream reset/epoch +1 epoch of the 4:3 pg_clk (4 fast edges), once per token (programme start).
  hc_tree      HC chain pin registers +11 (HH-9 CPR, bench RAW0 165 -> 176) + U-relay/DRLY 2 (+2): ledger hc_tree 28 -> 41.
               Closed-ring layout (DIE-HBM-LEAD 10-19 01:40, HC-RINGPLAN 9d1689ba4): the b7->b0 die relay goes but its edge
               moves into bank 0 (bankq0 DRLY 1 -> 2), so hub/root params and the calendar stay at 41: +13 a HC_MIX /
               HC_PRE_NORM record.
  hc_xr        HC root<->quarter crossings LANDED (HC-XRDU l7_wire land smoke: XRD 11 + XRU 11) instead of the priced
               2 x COLL_RING relay stages: +(22 - 2 COLL_RING) a HC record (modelled: GEN2b land smoke, not die STA).
  bank_pin     VM bank pin flop (hfd_vms_bank_native_q0_faces, HBM-BANKLAT / VEH-TOPKFIX2): every fixed-latency VM read
               client answer +1 edge: +1 on every record with a VM-space operand read (x-load, SU/SFU taps, COLL reads,
               IDX op readers, ARGMAX, DMA back).  The GEN2c relay-lane depths (1..75 stages/dir) are NOT this term (see
               info_gen2c_xload).
  su_red       SU reducer ingress widened to 128 words/edge (HH-6 per-pgslice csum8 pre-tree, PT 70 edges, bench measured
               211 vs model 234 edges): hgi_sim.d4g_su_red_1018 su_red = "pretree".
  e86_tkm      e86 TKM tile input register (HH-4 tile_rg PRE=1, tkm_static TLAT 4): +2 NT = +64 edges a TKM op at TP192:
               +64 on a COLL.TOPK_MERGE record.
  qcore_r6     qcore r6 write-conflict fault flag +1 edge: status only (coordinator ACCEPTED, HBM-HCBANK 02:40): 0 cycles.
  att_s32      (HBM-REPRICE2) HBM-ATTGAP choice S32: 32-row sub-runs keep the QK+PV programme resident (1,019 / 971 words);
               busiest-SM span QK 861 / PV 1,171 (2 sub-runs + go bubble, GEN2b die SM master, 40/40 bit-exact) replaces
               the SM COMPONENT of the priced record (b_measured_model T640 qk 288 / pv 386); first access / dispatch
               (fa 259) and publish 64 stay at price because the span excludes them (LB2-HBM VEH-ATT note).  T128 records:
               component x the one-op ratio 684/288, 839/386 (modelled).  Variant `bigprog` (2,048-word programme store,
               COORD 0jx, HBM-SMBUDGET): one op a SM at 684 / 839.
  att_merge    DS: HBM-ATTGAP on-die SU PV merge model 400.8 (T640; one-op 335.5) / 335.5 (T128) minus the priced merge
               99 / 79 already inside the PV record (modelled; SU RTL bench pending).  Qwen: 16-SM pairwise tree
               4 x (1 XQ + DEP 10 + LAT 9) (modelled).
  att_qwen     VEH-ATT3 MEASURED Qwen spans (D4G8 L0 + chained L1, 80/80 bit-exact, P 8192, 512 rows/SM): the attention
               stream at the per-SM line rate QK 65,536 B / 1,195 = 54.84, PV 65,536 / 2,364 = 27.72 B/cyc/SM on 16 SMs
               instead of the die HBM rate.
  att_prog     0: S32 resident programmes (measured).   att_desc  0: window staging (modelled check PASS; Qwen: no ring).
  pt_p2        HBM-PRETREE p2 (registered operand select): pre-tree PT 70 -> 81 edges, applied on the su_red pre-tree
               (attribution = su_red+pt_p2 minus su_red).
  idx_link     idx_link pipelined successor ot_hbm_idx_topk_link_static_p (HBM-IDXPIPE, AD-HBM-IDXK): +5 edges on every
               link output (frame 1397 -> 1402): +5 on IDX.INDEX / IDX.TOPK.
  idx_pin      rootctl_am_pin pair (VEH-TOPKFIX2 05b86e194, HBM-IDXAM2 r3): INDEX round trip +2 (r3) +1 (am_pin, op_SW
               n12 -> n13) = +3 an IDX.INDEX; TOPK per record of m rows +(m + 3) (r3) +1 (RT_EXTRA 2 / ACK 14);
               ARGMAX r2 done +7 (+1 VMX 5 -> 6) = +8 an ARGMAX record.  (These ledger rows were 'measured' without a
               knob, i.e. never charged.)
  land         d4g landed half-cycle hops (HBM-LANDING/DCC hland-dcc 447dfe960, priced -1.13 % DS AR / -0.07 % Qwen):
               applied as the recorded factor (priced; the land plan is not in this bundle).

Info variants (not composed): info_gen2c_xload (x-load VM round trip at the GEN2c measured 51 edges: SM_X 25.5 stages),
info_attgap_total[_bigprog] (HBM-ATTGAP's own accounting: span vs the exposed record total, whole merge added; reproduces
its 1,787.3 / 1,847.4 as a check), info_bl_coll / info_bl_dma / info_bl_idx / info_banklat_all (HBM-BANKLAT GEN2c relay-lane
budgets, INFO_TERMS; info_banklat_all is on top of `all`).

    PYTHONPATH=tools python3 -m hgi_sim.d4g_reprice_1019 --jobs 40 --out results/arch/hbm_reprice_1019/price.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import multiprocessing as mp
from pathlib import Path

from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import d4g_su_red_1018 as SR      # patches timing.su_cost (su_red mode per job)
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import timing as T

CLK = Q.CLK
ROOT = Q.ROOT

# ---------------------------------------------------------------------------------------------------------------- terms
# name: (value, grade, applies, source)   -- the ONLY constants of the re-price
TERMS = {
    "collq": (1, "measured", "C1 gathers: measured gather-master span; non-gather COLL +2 (ring-A merge register)",
              "d4g_collq_price_1018 ag_collq + ra_extra 2 (HBM-COLLQ c8d42a3a4; ledger HBM.D4G_PLAN_B)"),
    "pg_cmd": (5, "measured", "+5 an SU-executed record (lane commands r0/r3 +5, r1/r2 +2; lockstep lanes)",
               "TW-HBM-PGLG e7ea9096c region form, bench m0 PASS 8db52396a (lanes/TW-HBM-PGLG.md)"),
    "pg_operand": (10, "measured", "+10 an SU reduction record (red_sel/tree_cmd/slice_x/tree_o +10)",
                   "TW-HBM-PGLG e7ea9096c (lanes/H-D4G.md [TW-HBM-PGLG -> H-D4G-GEN2])"),
    "pg_vmwrite": (12, "measured", "+12 an SU-executed record writing VM (drain write +12 serial; +16 stream)",
                   "TW-HBM-PGLG e7ea9096c / HH-14 tb r2 4a91027b0 (SWQ 16)"),
    "pg_reset": (4, "modelled", "+4 once per token (pg_stream +1 epoch of the 4:3 pg_clk)",
                 "TW-HBM-PGLG pg_stream split (lanes/TW-HBM-PGLG.md)"),
    "hc_tree": (41, "measured", "hc_tree 28 -> 41 (+13 a HC_MIX / HC_PRE_NORM record); closed ring keeps 41 (b0 DRLY 2)",
                "HH-9 c4e9df3fe RAW0 176, HBM-RTL5 U +2, HBM-HCRING fc916e52b, DIE-HBM-LEAD 10-19 01:40, HC-RINGPLAN 9d1689ba4"),
    "hc_xr": (22, "modelled", "HC root<->quarter crossings XRD 11 + XRU 11 landed vs 2 x COLL_RING priced",
              "HC-XRDU cca87123f l7_wire land smoke (GEN2b), hc_eng XRD/XRU 11/11"),
    "bank_pin": (1, "priced", "+1 a record with a VM-space operand read (bank pin flop on every answer)",
                 "HBM-BANKLAT main 01636549a (contract rule), measured on IDX TOPK (VEH-TOPKFIX2 05b86e194)"),
    "su_red": ("pretree", "priced", "SU reduction = 128-word pre-tree (PT 70 edges) + reducer pairwise tree",
               "HH-6 claude/hh6-sured-1018 bc43419eb, d4g_su_red_1018 pretree (bench 211 vs model 234 edges)"),
    "e86_tkm": (64, "measured", "+64 a COLL.TOPK_MERGE record (+2 NT at TP192)",
                "HH-4 claude/hh4-e86-1018 a5f17ebc7 tkm_static TLAT 4, calendar mutant MUT 3"),
    "qcore_r6": (0, "measured", "write-conflict fault flag +1 edge: status only, 0 token cycles",
                 "HH-11 c663070f1; coordinator ACCEPTED (HBM-HCBANK 10-19 02:40)"),
    "att_s32": (dict(qk=861, pv=1171, qk1=684, pv1=839), "measured",
                "DS T640 SM component qk 288 -> 861, pv 386 -> 1,171 (HBM-ATTGAP S32: busiest SM, 2 x 32-row sub-runs + 5 "
                "go bubble; fa 259 / publish 64 kept at price -- the span excludes HBM first access, x-load, publish, "
                "merge); T128 at the one-op ratio 684/288, 839/386 (modelled); BIGPROG variant: one op 684 / 839",
                "HBM-ATTGAP main 7f35a3e4b results/rtl/hbm_ds_layer_tput_1018/hbm_attgap_1019/unit/L2_s32_pos.json "
                "(40/40 bit-exact, resident 1,019 / 971 words); one-op VEH-ATT 07a99bc0a"),
    "att_merge": (dict(ds640=400.8, ds128=335.5, ds640_one=335.5, levels=4, dep=10, lat=9), "modelled",
                  "DS PV + (HBM-ATTGAP SU merge 400.8 T640 / 335.5 T128 [one-op 335.5] - priced merge 99 / 79); "
                  "Qwen PV + 4 x (1 XQ + DEP 10 + LAT 9) (16-SM pairwise tree, no priced merge)",
                  "HBM-ATTGAP att_gap_price.py merge model (SU quadrant programme + ring AG + top levels in norm; "
                  "SU RTL bench pending); Qwen VEH-ATT finding (3)"),
    "att_qwen": (dict(qk_bytes_rate=65536 / 1195, pv_bytes_rate=65536 / 2364, nsm=16), "measured",
                 "Qwen ATT at the measured per-SM line rate (QK 54.84 / PV 27.72 B/cyc/SM, P 8192, 512 rows/SM) on 16 "
                 "SMs instead of the die HBM rate (spans measured; exposure from the S2 schedule)",
                 "VEH-ATT3 claude/veh-att3-1019 fb8fd695b results/rtl/hbm_qwen_layer_tput_1018/veh_att3_1019/unit/"
                 "{L0_L0_pos,chain_L1_pos}.json (80/80 bit-exact; QK 1,195 / PV 4 x 591 = 2,364)"),
    "att_prog": (0, "measured", "0: S32 sub-runs keep QK+PV resident (1,019 KV8 / 971 KV4 words <= 1,024)",
                 "HBM-ATTGAP L2_s32_pos.json calendars word-identical"),
    "att_desc": (0, "modelled", "0: window staging (fixed descriptors, DMA refresh i+1 -> i off-path; Qwen has no "
                 "window ring)", "HBM-ATTGAP window_staging_check.json PASS (260 tokens); DMA ~134 KB/layer/token"),
    "pt_p2": (81, "measured", "SU pre-tree PT 70 -> 81 edges (p2 registered operand select, PT_RED 69 -> 80); "
              "only with su_red", "HBM-PRETREE claude/hh6-sured-1018 0d52a4877 (bench MUT 0 PASS / MUT 512 FAIL); "
              "COORD 0kb"),
    "idx_link": (5, "measured", "+5 an IDX.INDEX / IDX.TOPK record (link outputs +5)",
                 "HBM-IDXPIPE b4717e464 / AD-HBM-IDXK c94204038 (frame 1397 -> 1402)"),
    "idx_pin": (dict(index=3, topk_fixed=4, argmax=8), "measured",
                "IDX.INDEX +3, IDX.TOPK +(m + 4), ARGMAX +8",
                "HBM-IDXAM2 r3 bench + VEH-TOPKFIX2 am_pin bench (RT_EXTRA 2 / ACK 14, VMX 6, op_SW n13)"),
    "land": (dict(ds=-1.13, qwen=-0.07), "priced", "recorded factor on tok/s (half-cycle landed hops)",
             "HBM-LANDING/DCC hland-dcc 447dfe960 (HANDOFF 10-18 07:35)"),
}
COMPOSED = [k for k in TERMS]                     # every term enters `all`
# INFO terms (priced, NOT composed): GEN2c bank-client relay-lane budgets (HBM-BANKLAT) -- closures still running and the
# GEN2d floorplan is meant to shorten them; one-way stage = round trip / 2 (the x-load convention of the previous lane).
INFO_TERMS = {
    "gen2c_xload": (dict(SM_X=51 / 2), "x-load VM round trip 51 edges (GEN2c measured) -> SM_X 25.5", "GEN2c / HBM-BANKLAT-XL"),
    "bl_coll": (dict(COLL_VM=74 / 2), "COLL VM_RT 74 (BANK_RT 72) -> COLL_VM 37", "HBM-BANKLAT-COLL budget"),
    "bl_dma": (dict(VM_HBM=83 / 2), "DMA RR_RT 80 -> issue->drain lag >= 83 -> VM_HBM 41.5", "HBM-BANKLAT-DMA budget"),
    "bl_idx": (dict(idx=171, argmax=65), "+171 an IDX.INDEX / IDX.TOPK (op readers VM_RT_EXTRA), +65 an ARGMAX "
               "(rootctl VM_RT) -- upper bound (whole budget exposed)", "HBM-BANKLAT-IDX budgets (n12 / rootctl_am g2c routes)"),
}
PT_BASE = SR.PT_EDGES                             # 70: the HH-6 pre-tree bench as priced before p2
BASE_HC_TREE = 28                                 # the price-of-record ledger value (hc_tree knob before HCRING)
BM = S.BM                                         # results/hbm_sm_attention_1015/b_measured_model.json
PER_RUN = {}                                      # per-term added cycles (sum over records) of one job


def _add(name, v):
    PER_RUN[name] = PER_RUN.get(name, 0.0) + v


def _reads_vm(r):
    for k, d in (getattr(r, "desc", None) or {}).items():
        if k != "O" and getattr(d, "space", None) == "VM":
            return True
    return False


def _writes_vm(r):
    d = (getattr(r, "desc", None) or {}).get("O")
    return getattr(d, "space", None) == "VM"


def _att_T(r):
    k = getattr(r, "mtp_kind", "") or ""
    return "128" if "B128" in k else ("640" if "B640" in k else None)


def rp_added(r, c, kn):
    """the re-price adders of one record (module doc); kn['rp'] = set of term names on"""
    rp = kn.get("rp") or set()
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    if kn.get("census"):
        _add(f"calls:{op}", 1)
        u = kn.setdefault("_uniq", set())
        if id(r) not in u:
            u.add(id(r))
            _add(f"uniq:{op}", 1)
            _add(f"vmread:{op}", 1 if _reads_vm(r) else 0)
            _add(f"vmwrite:{op}", 1 if _writes_vm(r) else 0)
            sut = getattr(r, "sut", None)
            _add(f"red:{op}", 1 if isinstance(sut, dict) and sut.get("red") else 0)
            _add(f"suexec:{op}", 1 if Q.su_exec(r) else 0)
            _add(f"kind:{op}:{getattr(r, 'mtp_kind', '')}", 1)
            _add(f"cost:{op}", c)
    if not rp and not kn.get("bl_idx"):
        return 0.0
    sut = getattr(r, "sut", None)
    red = isinstance(sut, dict) and sut.get("red")
    add = 0.0

    def a(name, v):
        nonlocal add
        if v:
            add += v
            _add(name, v)

    if "pg_cmd" in rp and Q.su_exec(r):
        a("pg_cmd", TERMS["pg_cmd"][0])
    if "pg_operand" in rp and r.unit == "SU" and red:
        a("pg_operand", TERMS["pg_operand"][0])
    if "pg_vmwrite" in rp and Q.su_exec(r) and _writes_vm(r):
        a("pg_vmwrite", TERMS["pg_vmwrite"][0])
    if op in ("HC.HC_MIX", "FUSED.HC_PRE_NORM"):
        if "hc_tree" in rp:
            a("hc_tree", TERMS["hc_tree"][0] - BASE_HC_TREE)
        if "hc_xr" in rp:
            a("hc_xr", TERMS["hc_xr"][0] - 2 * kn["xq"])
    if "bank_pin" in rp and _reads_vm(r):
        a("bank_pin", TERMS["bank_pin"][0])
    if "e86_tkm" in rp and op == "COLL.TOPK_MERGE" and c > 0:
        a("e86_tkm", TERMS["e86_tkm"][0])
    if op in ("IDX.INDEX", "IDX.TOPK"):
        if "idx_link" in rp:
            a("idx_link", TERMS["idx_link"][0])
        if "idx_pin" in rp:
            p = TERMS["idx_pin"][0]
            if op == "IDX.INDEX":
                a("idx_pin", p["index"])
            else:
                A = r.desc.get("A") if getattr(r, "desc", None) else None
                m = max(1, int(getattr(A, "m", 1) or 1)) if A is not None else 1
                a("idx_pin", m + p["topk_fixed"])
    if kn.get("bl_idx"):
        if op in ("IDX.INDEX", "IDX.TOPK"):
            a("bl_idx", INFO_TERMS["bl_idx"][0]["idx"])
        elif r.unit == "ARGMAX":
            a("bl_idx", INFO_TERMS["bl_idx"][0]["argmax"])
    if "idx_pin" in rp and r.unit == "ARGMAX":
        a("idx_pin", TERMS["idx_pin"][0]["argmax"])
    if op in ("ATT.QK", "ATT.PV"):
        w = op.split(".")[1].lower()
        Tn = _att_T(r)
        one = bool(kn.get("bigprog"))                            # BIGPROG: one op a SM (2,048-word programme store)
        if Tn is not None and "att_s32" in rp:                   # DS (option B records): SM component -> measured span
            m = TERMS["att_s32"][0]
            comp = BM["measured_comp"][Tn][w]
            if kn.get("attgap_total"):                           # info: HBM-ATTGAP's own comparison (vs exposed total)
                span = m[w + "1"] if one else m[w]
                ref = BM["exposed"]["per_record"][Tn][w]
                a("att_s32", max(0.0, span - ref) if Tn == "640" else 0.0)
            elif Tn == "640":
                a("att_s32", (m[w + "1"] if one else m[w]) - comp)
            else:                                                # T128: one-op ratio (modelled; S32 not needed at T128)
                a("att_s32", comp * (m[w + "1"] / BM["measured_comp"]["640"][w] - 1.0))
        if Tn is None and "att_qwen" in rp:                      # Qwen ATT (timing.cost: fa + bytes / bw + fixed)
            m = TERMS["att_qwen"][0]
            b = r.desc["B"]
            dyn = T.Dyn(kn.get("_qpos", 8191))
            try:
                _, P, _, _, _ = T.eff(b, dyn, r.layer if isinstance(r.layer, int) else 0)
            except Exception:
                P = 8192
            nbytes = P * 128 * T.ESZ[b.fmt]
            rate = m[f"{w}_bytes_rate"] * m["nsm"]
            cur = nbytes / T.cv("hbm", "bytes_per_cycle") + T.cv("units", "ATT.fixed")
            a("att_qwen", max(0.0, nbytes / rate - cur))
        if "att_desc" in rp and w == "qk" and TERMS["att_desc"][0]:
            L = getattr(r, "layer", None)
            seen = kn.setdefault("_desc_layers", set())
            if L not in seen:
                seen.add(L)
                a("att_desc", TERMS["att_desc"][0])
        if "att_merge" in rp and w == "pv":
            mm = TERMS["att_merge"][0]
            if Tn is not None:
                if kn.get("attgap_total"):
                    tree = mm["ds640_one"] if (one and Tn == "640") else mm["ds" + Tn]
                    a("att_merge", tree)                         # HBM-ATTGAP adds the whole merge on the 808 total
                else:
                    tree = mm["ds640_one"] if (one and Tn == "640") else mm["ds" + Tn]
                    a("att_merge", max(0.0, tree - BM["model_terms"]["merge"][Tn]))
            else:
                a("att_merge", mm["levels"] * (1 + kn["xq"] + mm["dep"] + mm["lat"]))
    return add


_PREV_ADDED = Q.d4g_added


def d4g_added(r, c, kn):
    return _PREV_ADDED(r, c, kn) + rp_added(r, c, kn)


Q.d4g_added = d4g_added


def _job(job):
    PER_RUN.clear()
    kn = job[-1]
    if kn:
        kn.pop("_desc_layers", None)
        kn.pop("_uniq", None)
    SR.PT_EDGES = (kn or {}).get("pt_edges", PT_BASE)
    name, res = SR._any(job)
    res = dict(res, rp_added={k: round(v, 1) for k, v in PER_RUN.items()})
    return name, res


def base_knob(st, led):
    k = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
    k["hc_tree"] = BASE_HC_TREE + 2 * k["xq"]            # price of record (explicit; independent of the ledger file)
    return k


def with_terms(base, terms, **extra):
    k = dict(base, **extra)
    rp = set()
    for t in terms:
        if t == "collq":
            k.update(ag_collq=True, ra_extra=Q.COLLQ_RA_EXTRA)
        elif t == "su_red":
            k["su_red"] = TERMS["su_red"][0]
        elif t == "pt_p2":
            k["pt_edges"] = TERMS["pt_p2"][0]
        elif t in ("land", "pg_reset", "qcore_r6", "att_prog"):
            pass                                          # post-hoc / zero terms (table)
        else:
            rp.add(t)
    k["rp"] = rp
    k["_terms"] = sorted(terms)
    return k


def post_hoc(row, terms):
    """per-token terms outside the record schedule: pg_reset cycles once a token, land factor"""
    ar, qc = row["ds_ar_cycles"], row["qwen_cycles"]
    if "pg_reset" in terms:
        ar += TERMS["pg_reset"][0]
        qc += TERMS["pg_reset"][0]
    if "land" in terms:
        f = TERMS["land"][0]
        ar = ar / (1 + f["ds"] / 100)
        qc = qc / (1 + f["qwen"] / 100)
    return ar, qc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=40)
    ap.add_argument("--only", default="", help="comma list of variants (debug)")
    ap.add_argument("--census", action="store_true", help="base only, per-op record census (debug)")
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    led = Q.load_ledger()
    vb = PS.VARIANTS["b"]
    base = base_knob(st, led)
    variants = {"base": (vb, with_terms(base, []))}
    sched_terms = [t for t in COMPOSED if t not in ("land", "pg_reset", "qcore_r6", "att_prog", "att_desc", "pt_p2")]
    for t in sched_terms:
        variants[f"only_{t}"] = (vb, with_terms(base, [t]))
    variants["all"] = (vb, with_terms(base, COMPOSED))
    variants["all_no_collq"] = (vb, with_terms(base, [t for t in COMPOSED if t != "collq"]))
    variants["all_bigprog"] = (vb, with_terms(base, COMPOSED, bigprog=True))    # expected post-HBM-SMBUDGET row
    ATT_T = ["att_s32", "att_merge", "att_qwen", "att_prog", "att_desc"]
    LAT_T = [t for t in COMPOSED if t not in ATT_T and t != "collq"]
    variants["rec"] = (vb, with_terms(base, ["collq"]))                     # accepted price of record (1849.2)
    variants["rec_lat"] = (vb, with_terms(base, ["collq"] + LAT_T))          # ledger row HBM.D4G_GEN2_LATENCY
    variants["rec_att"] = (vb, with_terms(base, ["collq"] + ATT_T))          # ledger row HBM.D4G_SM_ATTENTION
    variants["rec_att_bigprog"] = (vb, with_terms(base, ["collq"] + ATT_T, bigprog=True))
    variants["only_su_red_p2"] = (vb, with_terms(base, ["su_red", "pt_p2"]))  # pt_p2 attribution = this - only_su_red
    variants["only_att_s32_bigprog"] = (vb, with_terms(base, ["att_s32"], bigprog=True))
    variants["only_att_merge_bigprog"] = (vb, with_terms(base, ["att_merge"], bigprog=True))
    # check: HBM-ATTGAP's own accounting (span vs exposed record total, whole merge added) -> its 1,787.3 / 1,847.4
    variants["info_attgap_total"] = (vb, with_terms(base, ["att_s32", "att_merge"], attgap_total=True))
    variants["info_attgap_total_bigprog"] = (vb, with_terms(base, ["att_s32", "att_merge"], attgap_total=True, bigprog=True))
    stx = dict(st)
    for nm, sk in (("gen2c_xload", "plan_b_x51"), ("bl_coll", "plan_b_blcoll"), ("bl_dma", "plan_b_bldma")):
        stx[sk] = dict(st["plan_b"], **INFO_TERMS[nm][0])
        variants[f"info_{nm}"] = (dict(vb, stages=sk), with_terms(base, []))
    variants["info_bl_idx"] = (vb, with_terms(base, [], bl_idx=True))
    stx["plan_b_blall"] = dict(st["plan_b"], **INFO_TERMS["gen2c_xload"][0], **INFO_TERMS["bl_coll"][0], **INFO_TERMS["bl_dma"][0])
    variants["info_banklat_all"] = (dict(vb, stages="plan_b_blall"), with_terms(base, COMPOSED, bl_idx=True))
    if a.census:
        variants = {"base": (vb, dict(with_terms(base, []), census=True))}
    if a.only:
        keep = set(a.only.split(",")) | {"base"}
        variants = {k: v for k, v in variants.items() if k in keep}
    jobs = []
    for k, (v, kn) in variants.items():
        s_ = stx if str(v.get("stages", "")).startswith("plan_b_") else st
        jobs.append(("ds", f"{k}|AR", "AR", v, s_, kn))
        jobs.append(("qwen", f"{k}|qwen", v, s_, kn))
    with mp.Pool(min(a.jobs, len(jobs))) as pool:
        res = dict(pool.map(_job, jobs, chunksize=1))
    if a.census:
        cen = {k: dict(cycles=v.get("cycles"), tok_s=v.get("tok_s"), census=v.get("rp_added")) for k, v in res.items()}
        print(json.dumps(cen, indent=1, default=str))
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(cen, indent=1, default=str) + "\n")
        return 0
    table = {}
    for k, (v, kn) in variants.items():
        ds, qw = res[f"{k}|AR"], res[f"{k}|qwen"]
        row = dict(ds_ar_cycles=ds["cycles"], qwen_cycles=round(CLK / qw["tok_s"], 1) if not qw.get("cycles") else qw["cycles"])
        terms = kn.get("_terms", [])
        ar, qc = post_hoc(row, terms)
        row.update(ds_ar_cycles=round(ar, 1), qwen_cycles=round(qc, 1), ds_ar_tok_s=round(CLK / ar, 1),
                   qwen_tok_s=round(CLK / qc, 1), terms=terms,
                   rp_added_sum=dict(ds=ds.get("rp_added", {}), qwen=qw.get("rp_added", {})))
        table[k] = row
    b = table["base"]
    for r in table.values():
        r["d_ds_ar_pct"] = round(100 * (r["ds_ar_tok_s"] / b["ds_ar_tok_s"] - 1), 2)
        r["d_qwen_pct"] = round(100 * (r["qwen_tok_s"] / b["qwen_tok_s"] - 1), 2)
        r["d_ds_ar_cycles"] = round(r["ds_ar_cycles"] - b["ds_ar_cycles"], 1)
        r["d_qwen_cycles"] = round(r["qwen_cycles"] - b["qwen_cycles"], 1)
    # per-term attribution (alone on BASE) + post-hoc terms + interaction
    attr = {}
    for t in COMPOSED:
        if t == "pt_p2" and "only_su_red_p2" in table:          # p2 on top of the pre-tree it modifies
            r, r0 = table["only_su_red_p2"], table["only_su_red"]
            dc = round(r["d_ds_ar_cycles"] - r0["d_ds_ar_cycles"], 1)
            qc = round(r["d_qwen_cycles"] - r0["d_qwen_cycles"], 1)
        elif f"only_{t}" in table:
            r = table[f"only_{t}"]
            dc, qc = r["d_ds_ar_cycles"], r["d_qwen_cycles"]
        else:
            r1 = dict(ds_ar_cycles=b["ds_ar_cycles"], qwen_cycles=b["qwen_cycles"])
            ar, qq = post_hoc(r1, [t])
            dc, qc = round(ar - b["ds_ar_cycles"], 1), round(qq - b["qwen_cycles"], 1)
        attr[t] = dict(value=TERMS[t][0], grade=TERMS[t][1], applies=TERMS[t][2], source=TERMS[t][3],
                       ds_ar_cycles=dc, qwen_cycles=qc,
                       ds_ar_pct=round(100 * (b["ds_ar_cycles"] / (b["ds_ar_cycles"] + dc) - 1), 2),
                       qwen_pct=round(100 * (b["qwen_cycles"] / (b["qwen_cycles"] + qc) - 1), 2),
                       flag_over_5pct=bool(abs(100 * (b["ds_ar_cycles"] / (b["ds_ar_cycles"] + dc) - 1)) > 5
                                           or abs(100 * (b["qwen_cycles"] / (b["qwen_cycles"] + qc) - 1)) > 5))
    al = table["all"]
    inter = dict(ds_ar_cycles=round(al["d_ds_ar_cycles"] - sum(x["ds_ar_cycles"] for x in attr.values()), 1),
                 qwen_cycles=round(al["d_qwen_cycles"] - sum(x["qwen_cycles"] for x in attr.values()), 1))
    by_grade = {}
    for t, x in attr.items():
        g = by_grade.setdefault(x["grade"], dict(ds_ar_cycles=0.0, qwen_cycles=0.0))
        g["ds_ar_cycles"] = round(g["ds_ar_cycles"] + x["ds_ar_cycles"], 1)
        g["qwen_cycles"] = round(g["qwen_cycles"] + x["qwen_cycles"], 1)
    out = dict(schema="opentallas.hbm_d4g_reprice_1019.v1", lane="HBM-REPRICE2",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, base_knob={k: (sorted(v) if isinstance(v, set) else v) for k, v in base.items()},
               terms={k: dict(value=v[0], grade=v[1], applies=v[2], source=v[3]) for k, v in TERMS.items()},
               info_terms={k: dict(value=v[0], applies=v[1], source=v[2]) for k, v in INFO_TERMS.items()},
               table=table, attribution=attr, interaction=inter, by_grade=by_grade,
               composed=dict(ds_ar_tok_s=al["ds_ar_tok_s"], qwen_tok_s=al["qwen_tok_s"],
                             ds_ar_pct_vs_base=al["d_ds_ar_pct"], qwen_pct_vs_base=al["d_qwen_pct"],
                             ds_ar_pct_vs_record=round(100 * (al["ds_ar_tok_s"] / table["rec"]["ds_ar_tok_s"] - 1), 2),
                             groups={g: dict(ds_ar_tok_s=table[g]["ds_ar_tok_s"], qwen_tok_s=table[g]["qwen_tok_s"],
                                             ds_ar_pct_vs_record=round(100 * (table[g]["ds_ar_tok_s"] / table["rec"]["ds_ar_tok_s"] - 1), 2),
                                             qwen_pct_vs_record=round(100 * (table[g]["qwen_tok_s"] / table["rec"]["qwen_tok_s"] - 1), 2))
                                     for g in ("rec_lat", "rec_att", "rec_att_bigprog", "all_bigprog")}))
    print(json.dumps(dict(table={k: {x: v[x] for x in ("ds_ar_tok_s", "qwen_tok_s", "d_ds_ar_pct", "d_qwen_pct")}
                                 for k, v in table.items()}, attribution=attr, interaction=inter), indent=1, default=str))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
