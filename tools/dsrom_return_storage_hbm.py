#!/usr/bin/env python3
"""DS-ROM: what the "return storage" is, and the array priced with KV HBM sized to a target batch and with
minimal return storage (model only; read-only on tools/uarch_model.py and on every committed record).

Stage 1 (`run`):  executes the unified model (cons_v41_rom with the S58 selection settings, exactly as
                  tools/dsrom_isopower_history.py on claude/dsrom-isopower-history-20261003 @ 8bb540cd1) at 1M and
                  200K with the index reader bandwidth capped at what 1, 2 and >=3 HBM3E stacks deliver.
                  Writes raw.json.
Stage 2 (`compose`): arithmetic on raw.json and pinned records -> model.json.
"""
import copy, hashlib, json, math, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os
# The model runs against the unified model at $DSROM_MODEL_ROOT (default: this checkout). The first record
# (ad04a76d3) pinned e634046fe (2,563.7 / 2,680.6); the 2026-10-03 re-run is on the merged origin/main HEAD
# (32d865831 hub-edge wire correction): 2,535.5 / 2,649.7.  compose() takes the PAIR1 (M0) baseline from raw.json.
MODEL_ROOT = Path(os.environ.get("DSROM_MODEL_ROOT", ROOT))
sys.path.insert(0, str(MODEL_ROOT / "tools"))
OUT = ROOT / "results/uarch/dsrom_return_storage_hbm_20261003"
CTXS = (1048576, 200000)
PINS = {}


def git_json(rev, path):
    rev = subprocess.check_output(["git", "rev-parse", rev], cwd=ROOT, text=True).strip()
    b = subprocess.check_output(["git", "show", f"{rev}:{path}"], cwd=ROOT)
    PINS[f"{rev}:{path}"] = hashlib.sha256(b).hexdigest()
    return json.loads(b)


# ------------------------------------------------------------------------------------------------ stage 1: run
READERS = {"4_stacks": 4 * 750, "3_stacks": 3 * 750, "2_stacks": 2 * 750, "1_stack": 750}   # B/cycle at 1.2 GHz; 0.9 TB/s a stack
# (the product preset has idx_reader_Bpc=None, i.e. the die's full 4-stack 3.6 TB/s: 4_stacks must reproduce 2,563.7)


def run():
    import uarch_model as u
    cap = json.loads((MODEL_ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json").read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    S = 58
    saved = copy.deepcopy(u.PRESETS["proposal"])
    rom = {}
    try:
        for ctx in CTXS:
            for name, bpc in READERS.items():
                t0 = time.time()
                u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[S]["BF16_pairs_per_die"]
                u.PRESETS["proposal"]["idx_reader_Bpc"] = bpc
                with u._cons_ctx(ctx):
                    p = u.cons_v41_rom(S, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                                       field_concurrency=u.FIELD_CONCURRENCY,
                                       added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                                       dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                                       ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                                       vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
                u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(copy.deepcopy(saved))
                rom[f"{ctx}/{name}"] = dict(ctx=ctx, reader_Bpc=bpc, ar_tokens_s=p["ar_tokens_s_b1"],
                                            mtp_tokens_s=p["mtp_tokens_s_b1"], ar_sat=p["ar_saturated_tokens_s"],
                                            mtp_sat=p["mtp_saturated_tokens_s"], busiest=p["busiest_stage"],
                                            busiest_us=p["busiest_stage_us"], capacity_users=p["capacity_users_1m"],
                                            wall_s=round(time.time() - t0, 1))
                print(ctx, name, rom[f"{ctx}/{name}"], flush=True)
    finally:
        u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(saved)
    src = (MODEL_ROOT / "tools/uarch_model.py").read_bytes()
    (OUT / "raw.json").write_text(json.dumps(dict(rom=rom, uarch_model_sha256=hashlib.sha256(src).hexdigest()), indent=1))


# ------------------------------------------------------------------------------------------------ stage 2: compose
FF_UM2_PER_BIT = 0.37908      # DFFASRHQNx1_ASAP7_75t_R, the reservation cell (return lifetime audit 93efabc2d)
FF_UTIL = 0.5                 # the reservation's placement utilisation
MM2_PER_BIT = FF_UM2_PER_BIT / FF_UTIL / 1e6
W_ENTRY, W_HELD = 65, 66      # node/root FIFO entry {tag32, data32, err1}; root held entry adds a valid bit


def return_bits(NP, R=128, RD=64, ROOTD=128, pair_buf=0):
    """ot_v41_ret / ot_v41_retn_w17w10 declared state: 2NP-R binary nodes, each two RD-deep 65-bit FIFOs plus one
    RST=1 output register (66 bits); R roots, each a ROOTD-deep input FIFO (65) and a ROOTD-entry held-sibling
    buffer (66).  pair_buf: extra 65-bit entries per pair (credit-flow source buffer)."""
    return (2 * NP - R) * (2 * RD * W_ENTRY + W_HELD) + R * ROOTD * (W_ENTRY + W_HELD) + NP * pair_buf * W_ENTRY


def next_pow2(x):
    return 1 << math.ceil(math.log2(x))


# Credit-based minimum (Little's law): a node side must hold lambda x RTT entries; lambda <= 1 entry/cycle,
# RTT = parent pop -> credit register -> child decision -> RST data register = 4 cycles  =>  RD = 4.
# Roots keep ROOTD 128 (the held-sibling buffer has no timeout and is the only place a row's out-of-order
# siblings meet).  The source pair keeps a second 8-row x 65-bit partial buffer so a stalled pair can start
# its next round (uarch_model strip: 8 rows x FP32 chunk partial per element).
HUB_EDGE_SERDES_US = 2 * 45 / 1.2e9 * 1e6   # 32d865831 hub_edge_hop_wire_s: board hop pays 2 x 45 SerDes endpoint stages (DIE_SHRUNK_INTERIM) at 1.2 GHz
CREDIT = dict(RD=4, ROOTD=128, pair_buf=8)
ROUND_ROWS = 8                # partials one element emits per stream round (uarch_model.py strip pricing)
CHAIN_FLOOR = 40              # uarch_model.CHAIN_FLOOR: no stream round is shorter (cycles)

C1 = dict(  # isopower history 8bb540cd1 (C1 constants and composed results)
    S=58, layer_dies=464, head_dies=8, table_dies=36, dies=508, packages=254, stacks=960, die_mm2=786.23,
    die_static_excl_hbm_w=50.196, head_w=738.5, table_w=3324.4, par2_ucie_w=849.0, hop_us=23.2 / 57,
    ar={"1048576": 2347.4, "200000": 2445.0}, mtp={"1048576": 3539.3, "200000": 3854.2},
    ar_sat=80833.5, mtp_sat={"1048576": 35262.3, "200000": 35702.4},
    dyn_mJ_ar={"1048576": 118.6, "200000": 102.3}, dyn_mJ_mtp={"1048576": 170.4, "200000": 164.5},
    verify_m1_us={"1048576": 928.64, "200000": 845.68}, par2_delta_us=dict(ar=35.94, verify=70.41),
    m0_ar={"1048576": 2563.7, "200000": 2680.6}, m0_mtp={"1048576": 3809.4, "200000": 4176.7},
    tau4={"1048576": 3813.0, "200000": 4149.0})
HBM = {"1048576": dict(tau4=5314.0, ar=2261.7, best=25292.7, best_w=22638.0, total_mm2=450864.0, stacks=384, dies=96),
       "200000": dict(tau4=5325.6, ar=2266.0, best=41663.8, best_w=32974.0, total_mm2=450864.0, stacks=384, dies=96)}
STACK_MM2 = 1089.0            # 8 x 121 mm2 core + 121 mm2 base (isopower history; core public secondary, base ASSUMED)
STACK_IDLE_W = 2.8
STACK_USABLE_B = 22.5e9 * 0.9
DRAFT_OVER_AR = 0.1173
TAU_MODEL = 3.649
# KV state per user on the busiest (L20 source-layer) rank die, risk_ds_context_capacity a88164c57
PER_USER_DIE_B = {"1048576": 93458432.0, "200000": 17935168.0}
SCAN_LAYERS = (2, 8, 14, 20, 24, 28, 32, 36)   # index-scanning layers (L24..L36 scan the 16,384-key candidate set)


def compose():
    raw = json.loads((OUT / "raw.json").read_text())
    audit = git_json("origin/main", "results/uarch/dsrom_return_scaling_source_audit_20261002/model.json")
    life = git_json("93efabc2d9fd6f3402a6f586798b45fd97adbabc", "results/rtl/dsrom_return_lifetime_audit_20261002/model.json")
    r4 = git_json("origin/main", "results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/model-r4.json")
    budget = git_json("origin/main", "results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/inputs/compiled_budget.json")
    screen = git_json("origin/main", "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json")
    capm = git_json("e697d6eaef01ef7b60bd9ff330a3adc99c2adabc", "results/uarch/dsrom_4096_comparable_capacity_20261002/model.json")
    out = dict(schema="opentallas.dsrom.return-storage-hbm.v1",
               scope="model only: arithmetic on pinned records plus read-only unified-model runs; no RTL, P&R or model inference")

    # ---------------------------------------------------------------- Q1 what return storage is
    assert return_bits(8192) == audit["current_compiled"]["declared_lower_bits"] == 138469120
    assert return_bits(4096) == budget["return"]["declared_lower_bits"]
    assert abs(return_bits(8192) * MM2_PER_BIT - 104.9817480192) < 1e-6
    assert return_bits(2048, R=64) == r4["single_parallel_successor"]["return_bits_per_shard"]
    al = life["allocated_existing_state_bits"]
    q1 = dict(
        what="The FIFOs and buffers of the field's adding return tree (rtl/v41rom/ot_v41_ret.sv ot_v41_ret_node/"
             "ot_v41_ret_root; rtl/v41die/ot_v41_retn_w17w10.sv). Each ROM element pair emits FP32 partial dot products "
             "tagged {position, row, lo, k, nseg}; a binary tree of 2NP-R nodes adds two partials only when they are "
             "golden csum-tree siblings (so the K-split sums stay bit-exact in golden order), else forwards one; R=128 "
             "roots pair the remaining siblings, round to BF16 and write the finished rows to the vector memory.",
        stored_values="FP32 partial sums of matvec rows (every q/BF field matvec of every phase: a_proj, wq_b, wo_a/"
                      "wo_b, router, shared/routed expert gu/down, cmp.wk, ...), 65 bits each: 32-bit tag + 32-bit FP32 "
                      "value + error bit; root held buffer adds a valid bit.",
        why="No backpressure exists anywhere in the path: a node accepts every arriving partial (overflow is a fault), "
            "the root output has no ready/ACK and the VM write is implicitly always-accepted. Siblings arrive out of "
            "order because different pairs finish their rows at different times, and when partials are not siblings "
            "two inputs arrive per cycle against one output. The deep FIFOs are the slack that keeps a fault-free "
            "run from overflowing without flow control. Nothing in the source sizes RD=64 from a measured "
            "occupancy: it is the W10 generator parameter.",
        declared_bits=dict(node_two_FIFOs=al["node_two_payload_FIFOs"], node_RST=al["node_RST_payload_valid"],
                           root_input_FIFO=al["root_input_FIFO"], root_held=al["root_sibling_payload_valid"],
                           total_at_NP8192=al["sum"]),
        formula="bits = (2NP-R)(2*RD*65 + RST*66) + R*ROOTD*(65+66); RD=64, RST=1, ROOTD=128, R=128",
        area_rule="FF reservation at 0.37908 um2/bit (DFFASRHQNx1) and 50% utilisation = 0.758 um2 a bit; "
                  "no SRAM, no occupancy credit, no embedded-slot credit",
        scaling={f"NP{n}": dict(bits=return_bits(n), mm2=round(return_bits(n) * MM2_PER_BIT, 2)) for n in (1024, 2048, 4096, 8192)},
        scaling_note="Linear in compiled pairs per die NP (power of two), not in stages or context. At NP4096 it is "
                     "52.90 mm2, at a PAR2 shard (NP2048, R64) 26.45 mm2.",
        provenance=dict(
            tool_label=capm.get("full_return_requirement_provenance"),
            finding="No user or owner text in AGENTS.md, docs/, TASKS or the memory notes asks for 138.5 Mbit or 105 mm2. "
                    "The owner's standing rules that it traces to are 'finite producer/consumer flow control' and "
                    "'real macro read/capture timing' (AGENTS ROM reliability policy 2026-10-02) and exact golden "
                    "reduction order. 'Full return' meant: keep EVERY declared bit of the as-written NP8192 RTL "
                    "until a source ledger proves less (dsrom_4096_partition_token_options.py: 'Keep full return "
                    "reservation fixed until its exact source ledger proves a partitionable component').",
            records_say=dict(return_is_fundamental_lower_bound=False,
                             audit_meaning=audit["equations"]["meaning"],
                             lifetime_status=life["status"]),
            measured_live=dict(static_legacy_case_peak_bits=life["sound_bounds"]["retained_static_case_receiver_subtotal_peak_bits"],
                               fraction_of_declared=round(life["sound_bounds"]["retained_static_case_receiver_subtotal_peak_bits"] / al["sum"], 4),
                               caveat="one pinned static source-transcription case, not the L0/L20 program; the full "
                                      "occupancy join was requested and never executed")),
        not_return_storage="The 'capture home' (dsrom_capture_home / I66) is a 0.14 mm2 enclosure for ROM/scalar "
                           "capture cells, unrelated to the return tree.")
    # history: the S-selection screen (ee3de0a11 framework, usable field 442.81 mm2) re-run with return sized at the
    # actual compiled NP
    rows = screen["all_stage_capacity_rows"]
    usable = rows[0]["usable_field_mm2"]
    hist = {}
    for name, f in (("record_fixed_NP8192", lambda P: return_bits(8192) * MM2_PER_BIT),
                    ("as_declared_at_compiled_pow2_NP", lambda P: return_bits(next_pow2(P)) * MM2_PER_BIT),
                    ("credit_RD4_at_pow2_NP", lambda P: return_bits(next_pow2(P), **CREDIT) * MM2_PER_BIT),
                    ("zero", lambda P: 0.0)):
        ok = [r for r in rows if r["field_need_mm2"] + r["RNE_increment_mm2"] + r["WAKE_increment_mm2"]
              + f(r["pairs_per_die"]) <= usable]
        s = min(r["stages"] for r in ok)
        r = next(x for x in rows if x["stages"] == s)
        hist[name] = dict(min_stages=s, pairs_per_die=r["pairs_per_die"], return_mm2=round(f(r["pairs_per_die"]), 2),
                          tp4_dies=4 * s + 44)
    r41 = next(x for x in rows if x["stages"] == 41)
    q1["stage_selection_history"] = dict(
        basis="ee3de0a11 capacity screen: need = field + RNE + WAKE + return <= 442.81 mm2 usable field",
        S41=dict(need=round(r41["full_conservative_field_need_mm2"], 1), of_which_return=104.98,
                 without_return=round(r41["full_conservative_field_need_mm2"] - 104.98, 1)),
        min_stages_by_return_sizing=hist,
        reading="The 104.98 mm2 was charged at NP8192 at every stage count, although S58 compiles NP4096. Sized at "
                "the compiled NP the same screen passes at %d stages; with a credit-sized tree at %d; with none at %d."
                % (hist["as_declared_at_compiled_pow2_NP"]["min_stages"], hist["credit_RD4_at_pow2_NP"]["min_stages"],
                   hist["zero"]["min_stages"]))
    # PAR2 decision (r4 composition) decomposed
    eo = budget["exact_once_area_ledger_mm2"]
    pair1 = dict(frames=eo["full_compiled_q_BF_catalog_frames"], cfg=eo["config_prospective_body_plus_local_mux"],
                 RNE=eo["RNE_BF724_upper_proxy"], WAKE=eo["WAKE_full_compiled_upper_proxy"],
                 return_=eo["declared_return_FF50_proxy"], fixed_debit=eo["inherited_service_routes_clockPG_debit"],
                 native_residual=47.208013178655904)
    tot = sum(pair1.values())
    assert abs(tot - r4["composed_conservative_branch"]["total_mm2"]) < 1e-6
    pad_frac = r4["charged_padding_q_pairs"] / 4096
    q1["par2_decision"] = dict(
        S58_PAIR1_die_mm2=round(tot, 2), over_reticle_mm2=round(tot - 858, 2), terms_mm2={k: round(v, 2) for k, v in pair1.items()},
        padding_sites=r4["charged_padding_q_pairs"], padding_frames_mm2=round(pair1["frames"] * pad_frac, 2),
        with_zero_return=round(tot - pair1["return_"], 2), with_credit_return=round(tot - pair1["return_"] + return_bits(4096, **CREDIT) * MM2_PER_BIT, 2),
        with_credit_return_and_padding_trimmed=round(tot - pair1["return_"] + return_bits(4096, **CREDIT) * MM2_PER_BIT - pair1["frames"] * pad_frac, 2),
        reading="PAR2 was triggered by 66.3 mm2. Return is 52.9 of the 924.3, so removing it ENTIRELY still leaves "
                "13.4 mm2 over: return alone could not have avoided PAR2 at S58. The binding terms are the 465.5 mm2 "
                "fixed debit (287 mm2 of it an unmapped legacy complement) and 721 padding sites (power-of-two NP).")
    out["q1"] = q1

    # ---------------------------------------------------------------- minimal return sizing (B)
    NPs = (4096, 2048)
    q1b = {}
    for NP in NPs:
        R = 128 if NP == 4096 else 64
        cur = return_bits(NP, R=R)
        cr = return_bits(NP, R=R, **CREDIT)
        env = 2 * NP * ROUND_ROWS * W_ENTRY + R * 128 * (W_ENTRY + W_HELD)
        q1b[f"NP{NP}_R{R}"] = dict(current_bits=cur, current_mm2=round(cur * MM2_PER_BIT, 2),
                                   credit_bits=cr, credit_mm2=round(cr * MM2_PER_BIT, 2),
                                   two_round_envelope_bits=env, two_round_envelope_mm2=round(env * MM2_PER_BIT, 2),
                                   burst_per_root_per_round=NP // R * ROUND_ROWS, round_cycles_min=CHAIN_FLOOR)
    out["minimal_return"] = dict(
        rule="Little's law: entries = arrival rate x residence time. With credits a node side needs rate (1/cycle) x "
             "credit round trip (4 cycles) = 4 entries; the backlog then waits at its source pair, which holds one "
             "round (8 rows) and gets one more round of buffer so its next round can start. Without credits, the "
             "most that can ever be live is every partial of the rounds in flight: NP x 8 x 65 bits a round.",
        designs=q1b,
        latency_effect="None priced: the drain rate is the same 1 result/cycle/root either way, and the model's issue "
                       "term already paces matvecs to the result write (t_ret). Adoption still needs the RTL "
                       "measurement AGENTS requires.")

    # ---------------------------------------------------------------- die composition as a function of stages
    # Screen basis (current C1 per-die screen 786.23 = r4 shard + post-r4 increments 64.55 + re-frame 26.79).
    act_rank = 1711 + 1664                 # active pairs per rank at S58 (r4 census); 195,750 pair-stages a rank-chain
    PS = act_rank * 58
    fixed = pair1["fixed_debit"] + pair1["native_residual"]
    refr_pair1 = 2 * 26.79
    var_site = (tot - fixed - pair1["return_"] + refr_pair1) / 4096          # per compiled site, increments fixed
    var_site_hi = var_site + 2 * 64.55 / 4096                               # increments scale with pairs
    def fit(trim, ret, hi, fixed_delta=0.0):
        vs = var_site_hi if hi else var_site
        lim = 858 - (fixed + fixed_delta) - (0 if hi else 64.55)
        for S in range(40, 200):
            P = math.ceil(PS / S)
            NP = P if trim else next_pow2(P)
            rb = {"current": return_bits(next_pow2(P)) if not trim else return_bits(P),
                  "credit": return_bits(next_pow2(P) if not trim else P, **CREDIT), "zero": 0}[ret]
            area = vs * NP + rb * MM2_PER_BIT
            if area <= lim:
                return dict(stages=S, active_pairs=P, compiled_sites=NP, die_mm2=round(area + 858 - lim, 1))
    staging = {}
    for trim in (False, True):
        for ret in ("current", "credit", "zero"):
            staging[f"{'trim' if trim else 'pow2'}_{ret}"] = dict(conservative=fit(trim, ret, True), lower=fit(trim, ret, False))
    out["pair1_staging"] = dict(
        basis="One die per TP rank (PAIR1). Per-die = fixed 465.48 (r4 debit + residual) + variable per compiled site "
              "(frames incl. 0.60 re-frame, cfg, RNE, WAKE) + return. 'conservative' lets the post-r4 64.55 mm2 "
              "increments scale with pairs; 'lower' keeps them fixed per die. trim = no power-of-two padding sites "
              "(non-power-of-two tree: an RTL generator change); pow2 = current rule.",
        rows=staging)

    # ---------------------------------------------------------------- KV stacks (A)
    # the model's only HBM-bandwidth term is the index reader at the die's full stack bandwidth (preset
    # idx_reader_Bpc=None): raw.json shows 4 stacks are needed on scanning dies for an unchanged 1M rate
    bw_floor_scan = 4
    kv = {}
    for ctx in ("1048576", "200000"):
        per = PER_USER_DIE_B[ctx]
        kv[ctx] = dict(per_user_on_busiest_rank_die_B=per, users_per_stack=int(STACK_USABLE_B // per),
                       batch_rows={})
        for B in (1, 8, 32, 64, 216, 866):
            cap_st = math.ceil(B * per / STACK_USABLE_B)
            kv[ctx]["batch_rows"][str(B)] = dict(capacity_stacks_per_die=cap_st,
                                                 scan_die_stacks=max(cap_st, bw_floor_scan), other_die_stacks=max(cap_st, 1))
    rr = raw["rom"]
    out["kv_sizing"] = dict(
        rule="stacks per rank die = max(capacity: batch x per-user state on that die / 20.25 GB usable, bandwidth floor). "
             "Bandwidth floor: the 32 rank dies holding the eight index-scanning layers keep 4 stacks (the model's "
             "scan runs at the die's stack bandwidth; 3 stacks cost 1.1% AR and 6.4% saturated rate at 1M, see "
             "model_check); every other rank die keeps 1 "
             "(user rule: window KV and gathered rows stay in HBM; row gathers are latency- not bandwidth-bound). "
             "Head dies keep 4 each (draft state; not re-sized here).",
        bandwidth_floor_scan_die=bw_floor_scan, per_context=kv,
        model_check={k: dict(ar=v["ar_tokens_s"], mtp=v["mtp_tokens_s"], ar_sat=v["ar_sat"], busiest=v["busiest"],
                             busiest_us=v["busiest_us"]) for k, v in rr.items()},
        binding="Bandwidth, not capacity: one stack holds 216 users at 1M and 1,129 at 200K on the busiest die, while "
                "best batch needs ~35 users (AR) and ~10 (MTP). Capacity first adds stacks above 216 users (1M) on "
                "1-stack dies.")

    # ---------------------------------------------------------------- scenarios
    def stacks_for(ranks, rule):
        if rule == "C1":
            return 4 * ranks + 4 * C1["head_dies"]
        return len(SCAN_LAYERS) * 4 * bw_floor_scan + (ranks - 4 * len(SCAN_LAYERS)) + 4 * C1["head_dies"]

    cons = staging["trim_credit"]["conservative"]
    lo = staging["trim_credit"]["lower"]
    cur_trim = staging["trim_current"]["conservative"]
    pw = staging["pow2_current"]["conservative"]
    scen_defs = [
        ("C1 (today)", dict(S=58, par2=True, kv="C1", die=786.23)),
        ("A: KV stacks sized to batch", dict(S=58, par2=True, kv="A", die=786.23)),
        ("B0: return -> credit RD4 only", dict(S=58, par2=True, kv="C1", die=round(786.23 - 26.45 + q1b["NP2048_R64"]["credit_mm2"], 2))),
        ("B: credit return + trimmed padding, PAIR1", dict(S=cons["stages"], par2=False, kv="C1", die=cons["die_mm2"])),
        ("C: A + B", dict(S=cons["stages"], par2=False, kv="A", die=cons["die_mm2"])),
        ("ref: trimmed padding, return as declared, PAIR1", dict(S=cur_trim["stages"], par2=False, kv="C1", die=cur_trim["die_mm2"])),
        ("ref: no RTL change, PAIR1 at NP2048", dict(S=pw["stages"], par2=False, kv="C1", die=pw["die_mm2"])),
        ("ref: no RTL change, PAIR1 at NP2048 + A", dict(S=pw["stages"], par2=False, kv="A", die=pw["die_mm2"])),
        ("ref: C1 PAR2 re-staged to full shards (S48) + A", dict(S=48, par2=True, kv="A", die=786.23)),
    ]
    hop = C1["hop_us"] + HUB_EDGE_SERDES_US
    m0_ar = {c: rr[f"{c}/4_stacks"]["ar_tokens_s"] for c in ("1048576", "200000")}
    m0_mtp = {c: rr[f"{c}/4_stacks"]["mtp_tokens_s"] for c in ("1048576", "200000")}
    # PAR2 (C1) at this model = M0 + the recorded PAR2 crossing deltas (abd77c4e1: 35.94 us AR; MTP step from C1 constants)
    par2_mtp_step_us = {c: TAU_MODEL * 1e6 / C1["mtp"][c] - TAU_MODEL * 1e6 / C1["m0_mtp"][c] for c in m0_ar}
    c1_ar = {c: 1e6 / (1e6 / m0_ar[c] + C1["par2_delta_us"]["ar"]) for c in m0_ar}
    c1_mtp = {c: TAU_MODEL * 1e6 / (TAU_MODEL * 1e6 / m0_mtp[c] + par2_mtp_step_us[c]) for c in m0_ar}
    # verify: the recorded m=1 verify plus this model's AR shift (the hub-edge wires land on verify as on AR)
    ver_shift = {c: 1e6 / m0_ar[c] - 1e6 / C1["m0_ar"][c] for c in m0_ar}
    out["baseline_at_model"] = dict(m0_ar=m0_ar, m0_mtp=m0_mtp, c1_ar=c1_ar, c1_mtp=c1_mtp, ver_shift_us=ver_shift,
                                    hop_us=hop, record_m0_ar=C1["m0_ar"],
                                    hop_check="57 stage hops x %.4f us hub-edge SerDes wire = %.2f us vs measured AR shift %.2f us at 1M"
                                    % (HUB_EDGE_SERDES_US, 57 * HUB_EDGE_SERDES_US, ver_shift["1048576"]))
    scen = []
    for name, d in scen_defs:
        S, par2 = d["S"], d["par2"]
        ranks = 4 * S
        layer = ranks * (2 if par2 else 1)
        dies = layer + 44
        stacks = stacks_for(ranks, d["kv"])
        logic = layer * d["die"] + 44 * C1["die_mm2"]
        dram = stacks * STACK_MM2
        static = layer * C1["die_static_excl_hbm_w"] + stacks * STACK_IDLE_W + C1["head_w"] + C1["table_w"] + (C1["par2_ucie_w"] * S / 58 if par2 else 0)
        row = dict(scenario=name, stages=S, par2=par2, layer_dies=layer, dies=dies, packages=dies // 2, stacks=stacks,
                   layer_die_mm2=d["die"], logic_mm2=round(logic), dram_mm2=round(dram), total_mm2=round(logic + dram),
                   dram_share=round(dram / (logic + dram), 3), static_w_icg=round(static), stack_idle_w=round(stacks * STACK_IDLE_W),
                   ctx={})
        for ctx in ("1048576", "200000"):
            ar_us = (1e6 / c1_ar[ctx] if par2 else 1e6 / m0_ar[ctx]) + (S - 58) * hop
            step_model = (TAU_MODEL / c1_mtp[ctx] if par2 else TAU_MODEL / m0_mtp[ctx]) * 1e6 + (S - 58) * hop
            ver = C1["verify_m1_us"][ctx] + ver_shift[ctx] + (C1["par2_delta_us"]["verify"] if par2 else 0) + (S - 58) * hop
            tau4 = 4e6 / (ver + DRAFT_OVER_AR * ar_us)
            ar, mtp = 1e6 / ar_us, TAU_MODEL * 1e6 / step_model
            best = C1["ar_sat"]
            P = static + C1["dyn_mJ_ar"][ctx] * 1e-3 * best
            h = HBM[ctx]
            batch = {}
            for B in (1, 8, 32, 64):
                rate = min(B * ar, best)
                Pb = static + C1["dyn_mJ_ar"][ctx] * 1e-3 * rate
                batch[str(B)] = dict(ar_tok_s=round(rate), tok_s_per_kw=round(rate / Pb * 1e3, 1))
            row["ctx"][ctx] = dict(ar=round(ar, 1), mtp_model_tau=round(mtp, 1), mtp_tau4=round(tau4, 1),
                                   best_batch_tok_s=best, best_batch_w=round(P), best_tok_s_per_kw=round(best / P * 1e3, 1),
                                   best_tok_s_per_Mmm2=round(best / (logic + dram) * 1e6, 1),
                                   vs_hbm=dict(ar=round(ar / h["ar"], 3), tau4=round(tau4 / h["tau4"], 3),
                                               per_kw=round(best / P / (h["best"] / h["best_w"]), 2),
                                               per_mm2=round(best / (logic + dram) / (h["best"] / h["total_mm2"]), 2)),
                                   by_batch=batch)
        scen.append(row)
    out["scenarios"] = scen
    out["scenario_bases"] = dict(
        per_user="PAR2 rows: C1 rates (dsrom_parallelism abd77c4e1). PAIR1 rows: the unified model's S58 rank-die rate "
                 "(M0, no PAR2 crossings) + 0.407 us a stage hop per added stage (23.2 us / 57, the isopower method). "
                 "MTP at the model tau 3.649 and at tau 4 (verify m=1 + PAR2 verify delta + hops + draft 0.1173 x AR).",
        best_batch="AR saturated 80,833.5 tok/s (head-bound 12.37 us; unchanged by stage count or stack count >= 3 on scan dies).",
        power="ICG-only always-on static: 50.196 W a layer die excluding stack idle (incl. 30.6 W SerDes), 2.8 W a stack, "
              "head 738.5 W, table 3,324.4 W, PAR2 UCIe traffic upper bound 849 W (scaled by stages); dynamic 118.6 / "
              "102.3 mJ a token (AR, 1M / 200K).",
        silicon="logic = layer dies x layer-die screen + 44 head/table dies x 786.23 (isopower convention); DRAM 1,089 mm2 a stack.",
        hbm_comparator={k: v for k, v in HBM.items()})
    out["scenario_c"] = scenario_c(out, fit, staging, scen, rr)
    out["pins"] = PINS
    out["raw_uarch_model_sha256"] = raw["uarch_model_sha256"]
    (OUT / "model.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(hist=hist, staging=staging, scen=[(r["scenario"], r["stages"], r["dies"], r["stacks"], r["total_mm2"],
                                                             r["static_w_icg"], r["ctx"]["1048576"]["ar"], r["ctx"]["1048576"]["mtp_tau4"],
                                                             r["ctx"]["1048576"]["best_tok_s_per_kw"], r["ctx"]["1048576"]["vs_hbm"]) for r in scen]), indent=1))


# ------------------------------------------------------------------------------------------------ scenario C (owner-approved 2026-10-03)
HBM_ACCEL = dict(  # claude/hbm-accelerator-study-20261003 @ a3ed9c36d ladder.json compare.ds[1] (unvalidated model rungs, 1M; 200K within 0.2%)
    src="a3ed9c36d:results/uarch/hbm_accelerator_study_20261003/ladder.json compare.ds[1]",
    ar=3015.2, mtp_tau3649=6001.1, mtp_tau4=6579.0, logic_mm2=32688, stacks=384, dram_mm2=384000, total_mm2=416688,
    system_w_ar_b1=9774.0, static_w_gated=5367.7, dyn_J=1.4614, dies=96)
LAYER_SERDES_W = 30.6          # of the 50.196 W layer-die always-on (isopower history 8bb540cd1)
PG_RESIDUAL = 0.10             # ASSUMED: a power-gated die region keeps 10% of its leakage (header leakage, retention-free:
                               # ROM is mask-programmed, KV is in HBM, only the live token's activations move with the token)
LINK_PG_RESIDUAL = 0.10        # ASSUMED: a lane-gated SerDes keeps 10% (CDR/PLL standby) and re-locks inside the pre-wake window
PHY_MM2 = dict(central=10.0, low=8.0, high=15.0)   # technology.json hbm.hbm3e phy_area_mm2_per_stack (assumed, 8-15)
PHY_EDGE_MM = 8.5              # consolidation.json shoreline.phy_edge_mm (GH100 long edge / 3)


def scenario_c(out, fit, staging, scen, rr):
    C = next(r for r in scen if r["scenario"] == "C: A + B")
    C1r = next(r for r in scen if r["scenario"] == "C1 (today)")
    S = C["stages"]
    ranks = 4 * S
    scan_dies = 4 * len(SCAN_LAYERS)
    one_stack = ranks - scan_dies
    res = dict(stages=S, layer_dies=C["layer_dies"], dies=C["dies"], packages=C["packages"], stacks=C["stacks"])

    # ---- item 2: S69 vs S73
    res["stage_decision"] = dict(
        decision="S73 (conservative) is the baseline; S69 is not adopted",
        evidence=[
            "The 64.55 mm2 is the r4->C1 screen step 694.88 (r4 single_parallel_successor.conservative_priced_per_shard_mm2) "
            "-> 759.44 (dsrom_capture_clock_selected_union whole_selector_replacement_screen_mm2).",
            "Traced terms are per-die services: two-port PAR2 corridor 4.32 (capture_home inputs/budget.json "
            "composed_whole_area.new_two_port_corridor_reservation_mm2; PAR2-only, vanishes in PAIR1), selector station 0.60 "
            "and 1.68 once, capture enclosure 0.14 ('same_envelope_reserved_per_shard_die'), clock reserve 0.014 "
            "(dsrom_selected_parent_caller r7 whole_reticle_join; dsrom_capture_home model.json).",
            "Terms that DO scale with elements: shared broadcast BUF 0.76 ('3,726,496 BUF/shard'), finite spatial element "
            "clock increment 0.46 ('901/2724 BUF' per element) -- about 1.2 mm2 per 2,048-pair shard.",
            "The bulk, ~58 mm2 between 694.88 and the 753.03 'latest_owner_screen_already_including_corridor' "
            "(topk_finite_track_turn_model r2), has no per-term source ledger in the records read; its scaling is unproven.",
        ],
        reading="Of the 64.55 mm2 only ~6.5 mm2 is traced: ~5.3 per-die and ~1.2 per-element. Fixed-per-die (S69) needs the "
                "untraced ~58 mm2 to be shown per-die; until then the owner-approved S73 stands. S69 is an upside of "
                "4 stages / 16 dies / -1.9 us AR (+1.2% per-user), assigned to workstream W2 as a ledger task.",
        S69_upside=dict(stages=staging["trim_credit"]["lower"]["stages"], dies=4 * staging["trim_credit"]["lower"]["stages"] + 44))

    # ---- item 3: stage power gating
    layer_logic_w = C1["die_static_excl_hbm_w"] - LAYER_SERDES_W
    pg = {}
    for ctx in ("1048576", "200000"):
        ar = C["ctx"][ctx]["ar"]; dyn = C1["dyn_mJ_ar"][ctx] * 1e-3
        rows = {}
        for B in (1, 8, 32, 64):
            rate = min(B * ar, C1["ar_sat"])
            # a stage is busy for t_token/S per token it carries; one neighbour is pre-woken per token in flight
            f = min(1.0, (min(B, rate / ar) + 1) / S) if rate < C1["ar_sat"] else min(1.0, rate / ar / S + 1 / S)
            base = C["static_w_icg"]
            logic_pg = C["layer_dies"] * layer_logic_w * (1 - f) * (1 - PG_RESIDUAL)
            link_pg = C["layer_dies"] * LAYER_SERDES_W * (1 - f) * (1 - LINK_PG_RESIDUAL)
            st_icg, st_pg, st_pgl = base, base - logic_pg, base - logic_pg - link_pg
            rows[str(B)] = dict(tok_s=round(rate), active_stage_fraction=round(f, 3),
                                static_kw=dict(icg=round(st_icg / 1e3, 2), pg_logic=round(st_pg / 1e3, 2), pg_logic_links=round(st_pgl / 1e3, 2)),
                                tok_s_per_kw=dict(icg=round(rate / (st_icg + dyn * rate) * 1e3, 1),
                                                  pg_logic=round(rate / (st_pg + dyn * rate) * 1e3, 1),
                                                  pg_logic_links=round(rate / (st_pgl + dyn * rate) * 1e3, 1)))
        mtp = C["ctx"][ctx]["mtp_model_tau"]; dyn_m = C1["dyn_mJ_mtp"][ctx] * 1e-3
        b1 = rows["1"]["static_kw"]
        pg[ctx] = dict(by_batch=rows,
                       b1_mtp_tau3649=dict(tok_s=mtp, **{k: round(mtp / (v * 1e3 + dyn_m * mtp) * 1e3, 1) for k, v in b1.items()}))
    ha = HBM_ACCEL
    pg["hbm_accelerator"] = dict(ar_tok_s_per_kw_b1=round(ha["ar"] / ha["system_w_ar_b1"] * 1e3, 1),
                                 mtp_tok_s_per_kw_b1=round(ha["mtp_tau3649"] / (ha["static_w_gated"] + ha["dyn_J"] * ha["mtp_tau3649"]) * 1e3, 1),
                                 mtp_power_basis="static 5,367.7 W + 1.4614 J per emitted token (AR energy, so MTP per-kW is an upper bound)",
                                 best_batch="not modelled in a3ed9c36d; the HBM comparator's best is 25,293 tok/s at 22.6 kW (1,117 tok/s per kW)")
    pg["basis"] = ("Layer-die always-on 50.196 W = 30.6 W SerDes + 19.6 W logic. A stage is gated except while it carries a token "
                   "plus one pre-woken neighbour: active fraction (min(B, rate/AR) + 1)/S. Gated logic keeps %.0f%%, gated "
                   "links keep %.0f%% (both ASSUMED). Head (738.5 W), Engram table (3,324.4 W) and HBM stack idle (2.8 W, KV "
                   "retained) are not gated. Dynamic AR energy unchanged (118.6 / 102.3 mJ a token). Pre-wake hides the "
                   "wake latency inside one stage time (~5.5 us at S73), an RTL/PDN requirement for W5."
                   % (PG_RESIDUAL * 100, LINK_PG_RESIDUAL * 100))
    pg["reading"] = ("Gating matters only at low batch: at batch 1 it cuts static %.1f -> %.1f kW (logic+links); by batch 32 the "
                     "pipeline is ~45%% busy and saturated rate is head-bound, so best-batch tok/s per kW moves little. "
                     "The un-gated Engram table dies (3.3 kW) become the largest always-on term."
                     % (pg["1048576"]["by_batch"]["1"]["static_kw"]["icg"], pg["1048576"]["by_batch"]["1"]["static_kw"]["pg_logic_links"]))
    res["power_gating"] = pg

    # ---- item 4: HBM PHY / shoreline saved
    phy = {k: dict(per_die_mm2=3 * v, array_mm2=round(3 * v * one_stack, 1)) for k, v in PHY_MM2.items()}
    phy_fit = {k: fit(True, "credit", True, fixed_delta=-3 * v) for k, v in PHY_MM2.items()}
    res["hbm_phy_credit"] = dict(
        one_stack_rank_dies=one_stack, scan_rank_dies=scan_dies, phy_mm2_per_stack=PHY_MM2,
        saved=phy, shoreline_freed_mm_per_die=3 * PHY_EDGE_MM,
        ledger_status="The HBM PHY is not a named term in the r4/C1 ledger: it is part of E (IO/PHY exclusions, "
                      "'actual_E_and_H_received': false) inside the uniform 418.27 mm2 inherited debit. The credit is real "
                      "only once that debit is replaced by explicit per-die rectangles (workstream W4).",
        if_taken_on_every_rank_die=dict(conservative_stages={k: v["stages"] for k, v in phy_fit.items()}),
        caveat="Scan-layer dies keep 4 PHYs, so a uniform-pairs partition gains the credit only if scan stages carry fewer "
               "pairs or the 32 scan dies keep the larger outline; stated as the bound, not adopted.",
        shoreline_reading="25.5 mm of the die edge freed per one-stack die: room for the TP-4 board SerDes and the stage "
                          "links without the 60% beachfront ceiling (technology.json max_beachfront_utilization).")
    # complement-removal sensitivity (287 mm2 unmapped legacy complement replaced by an explicit E)
    comp = {}
    for E in (287.02, 150.0, 75.0):
        r = fit(True, "credit", True, fixed_delta=E - 287.02)
        comp[f"E_{E:g}"] = dict(stages=r["stages"], dies=4 * r["stages"] + 44)
    res["complement_removal_sensitivity"] = dict(
        rule="fixed debit 465.48 = 287.02 unmapped complement + the rest; replace the complement by an explicit E (IO/PHY, "
             "halos, clock/PG) of the stated size", rows=comp,
        reading="The owner-approved C keeps S73, which still charges the 287 mm2. Every 100 mm2 of the complement that W4 "
                "proves unnecessary is worth several stages; adopt only from the regenerated area ledger.")

    # ---- item 5: restated numbers
    def row(r, label):
        x = dict(design=label, dies=r["dies"], packages=r["packages"], stacks=r["stacks"], logic_mm2=r["logic_mm2"],
                 dram_mm2=r["dram_mm2"], total_mm2=r["total_mm2"], static_kw_icg=round(r["static_w_icg"] / 1e3, 2))
        for ctx in ("1048576", "200000"):
            c = r["ctx"][ctx]
            x[ctx] = dict(ar=c["ar"], mtp_tau3649=c["mtp_model_tau"], mtp_tau4=c["mtp_tau4"],
                          best_tok_s=c["best_batch_tok_s"], best_w=c["best_batch_w"],
                          dynamic_kw_at_best=round((c["best_batch_w"] - r["static_w_icg"]) / 1e3, 2),
                          best_tok_s_per_kw=c["best_tok_s_per_kw"], best_tok_s_per_Mmm2_total=c["best_tok_s_per_Mmm2"],
                          best_tok_s_per_Mmm2_logic=round(c["best_batch_tok_s"] / r["logic_mm2"] * 1e6),
                          b1_ar_tok_s_per_kw=c["by_batch"]["1"]["tok_s_per_kw"])
        return x
    cr = row(C, "Scenario C (S73 PAIR1, credit return, trimmed padding, KV sized)")
    for ctx in ("1048576", "200000"):
        b = pg[ctx]["by_batch"]
        cr[ctx]["b1_ar_tok_s_per_kw_pg"] = b["1"]["tok_s_per_kw"]["pg_logic_links"]
        cr[ctx]["static_kw_b1_pg"] = b["1"]["static_kw"]["pg_logic_links"]
        cr[ctx]["b1_mtp_tok_s_per_kw_pg"] = pg[ctx]["b1_mtp_tau3649"]["pg_logic_links"]
    hb = dict(design="HBM accelerator (a3ed9c36d, unvalidated model rungs)", dies=ha["dies"], stacks=ha["stacks"], logic_mm2=ha["logic_mm2"],
              dram_mm2=ha["dram_mm2"], total_mm2=ha["total_mm2"], static_kw=ha["static_w_gated"] / 1e3,
              ar=ha["ar"], mtp_tau3649=ha["mtp_tau3649"], mtp_tau4=ha["mtp_tau4"],
              b1_ar_tok_s_per_kw=pg["hbm_accelerator"]["ar_tok_s_per_kw_b1"],
              b1_mtp_tok_s_per_kw=pg["hbm_accelerator"]["mtp_tok_s_per_kw_b1"],
              note="DRAM at 1,000 mm2 a stack in a3ed9c36d vs 1,089 here; per-mm2 compares use each record's own basis")
    res["restated"] = dict(C=cr, C1=row(C1r, "C1 today (S58 PAR2) at this model"), hbm_accelerator=hb)
    return res


if __name__ == "__main__":
    {"run": run, "compose": compose}[sys.argv[1]]()
