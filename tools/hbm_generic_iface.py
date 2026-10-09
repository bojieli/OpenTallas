#!/usr/bin/env python3
"""HGI-1: the generic HBM-die interface (docs/HBM_GENERIC_INTERFACE.md), reference encoder and validator.

The owner-approved design, and the only encoding:
  * SPEC: every field of the model descriptor (MD), the record header (UOP), the memory descriptor (MDESC) and
    the SU template (SUT), with bit positions, legal values and the consuming block;
  * the per-layer model manifest (JSON) of each model, bound to its MD by sha256;
  * the 64-word MD (3 static fields: cp_vocab, cp_ctx_max, coll_group_size) and the CP's CFG_COMMIT checks.

    python3 tools/hbm_generic_iface.py --out   results/arch/hbm_generic_iface_20261009
    python3 tools/hbm_generic_iface.py --check results/arch/hbm_generic_iface_20261009

The DS descriptor's static fields equal the reset values (DS behaviour): loading it is a no-op for every block.
tools/hgi_sim encodes and decodes records from the tables below (D_UOP_FIELDS, D_MDESC_FIELDS, D_SUT_LAYOUT, D_OPS).
The earlier v0.9 encoding was removed (2026-10-09); its files are in git history only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAGIC = 0x31494748                     # "HGI1" little-endian
NWORDS = 64
CRC_WORD = 63

MODELS = {
    "ds_v41_flash": dict(cfg="compiler/models/deepseek-v4.1-flash/config.json", model_class=1, tp=96, head_rows=0),
    "qwen3_8b": dict(cfg="compiler/models/qwen3-8b/config.json", model_class=2, tp=4, head_rows=37984),
}

# enum encodings ----------------------------------------------------------------------------------------------
FMT = {"FP32": 0, "BF16": 1, "FP8E4M3": 2, "FP4E2M1": 3, "INT8": 4, "U32": 5, "UE8M0": 6}
ERR = {0: "OK", 1: "E_MAGIC", 2: "E_VERSION", 3: "E_CRC", 4: "E_BUSY", 5: "E_RANGE", 6: "E_RESERVED"}
UNITS = ["CTL", "SM", "SU", "SFU", "FUSED", "ATT", "COLL", "ARGMAX", "DMA", "IDX", "HC", "SIMT"]
OPS = {
    "CTL": ["NOP", "LOOP", "ENDLOOP", "END", "FENCE", "TOKX", "AMAX", "ACCEPT"],
    "SM": ["MATVEC"],
    "SU": ["VOP"],
    "SFU": ["GLU"],
    "FUSED": ["HC_PRE_NORM", "ROW_NORM", "HC_POST"],
    "ATT": ["QK", "PV"],
    "COLL": ["ALL_REDUCE_SUM", "ALL_GATHER", "TOPK_MERGE", "ARGMAX_MERGE"],
    "ARGMAX": ["LOCAL"],
    "DMA": ["LOAD", "STORE", "FENCE"],
    "IDX": ["INDEX_Q", "INDEX_SCORES", "TOPK_LOCAL", "SELECT"],
    "HC": ["HC_MIX"],
    "SIMT": ["RUN"],
}
PRED = ["ALWAYS", "POS0", "NOT_POS0", "LAST_ITER"]
SPACE = ["HBM", "VM", "STREAM", "NONE"]
# SU template fields (widths) in packing order: the pipeline fields of tools/hdc_isa_v41.py
SUT_FIELDS = [
    ("a_src", 2), ("a_ind", 2), ("b_src", 2), ("b_half", 1), ("c_src", 2), ("c_pair", 1), ("d_src", 2),
    ("a_rnd", 1), ("a_relu", 1), ("a_min", 1), ("c_clip", 1), ("m1", 3), ("m2", 2), ("qm", 3), ("ad", 3),
    ("sfu", 3), ("e1", 3), ("e2", 2), ("rnd", 1), ("dst", 2), ("red", 2), ("red_sq", 1), ("red_whole", 1),
    ("red_rnd", 1), ("su_vec", 2), ("red_tree", 1), ("imm1", 32), ("imm2", 32), ("imm3", 32),
]


def f32bits(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


# ============================================================================================================
# HGI-1 (owner-approved design)
# ============================================================================================================
D_VERSION = (1, 0)
D_MD_FIELDS = [
    ("magic", 0, 0, 32, "u", "cp", "reject a non-HGI image"),
    ("ver_minor", 1, 0, 8, "u", "cp", "reject an incompatible layout"),
    ("ver_major", 1, 8, 8, "u", "cp", "reject an incompatible layout"),
    ("n_words", 1, 16, 8, "u", "cp", "fixed 64; guards a truncated load"),
    # words 2-31: RESERVED (C8: section B moved to the per-layer model manifest)
    ("manifest_sha256", 32, 0, 256, "u", "sw", "sha256 of the model manifest JSON (C8); binds MD to one model"),
    ("cp_vocab", 40, 0, 18, "u", "hfd_cmdproc", "doorbell / completion token range check (width 18 everywhere)"),
    ("cp_ctx_max", 41, 0, 21, "u", "hfd_cmdproc", "doorbell position range check"),
    ("coll_group_size", 46, 0, 8, "u", "hfd_coll", "aligned groups (C6 set); rank = die_id mod size"),
    # word 49, 53-55: reserved for Qwen MTP (D4); words 50-52: reserved for C4 window/chunk parameters
    ("entry_ar", 56, 0, 32, "u", "hfd_cmdproc", "AR decode step: record offset in the image (16 B units)"),
    ("entry_verify", 57, 0, 32, "u", "hfd_cmdproc", "MTP verify pass (0 = absent)"),
    ("entry_draft", 58, 0, 32, "u", "hfd_cmdproc", "MTP draft pass (0 = absent)"),
    ("image_base", 60, 0, 28, "u", "hfd_cmdproc", "program image in HBM, 4 KiB pages"),
    ("image_pages", 61, 0, 28, "u", "hfd_cmdproc", "program image size, 4 KiB pages"),
    ("crc32", 63, 0, 32, "u", "hfd_cmdproc", "IEEE CRC-32 of words 0..62"),
]
D_RESET = dict(cp_vocab=129280, cp_ctx_max=1 << 20, coll_group_size=96)
# Collective groups: 1/2/4/8 on the NC-8 owner tree plus 96 (DS reset); 16/32/64 are defined encodings that the
# CFG range check rejects (E_RANGE) until a priced variant builds them (REVIEW_20261009 S4).
D_LEGAL = dict(cp_vocab=(1, (1 << 18) - 1), cp_ctx_max=(1, 1 << 20), coll_group_size={1, 2, 4, 8, 96})
D_GROUP_DEFINED_REJECTED = [16, 32, 64]
D_UNITS = UNITS + ["RSV12", "RSV13", "RSV14", "RSV15"]          # C3a: codes 12-15 reserved
# Unit presence per die.  r25 (the generic HBM die) has fixed-function SMs and NO OTG-1/SIMT kernel memory
# (hbm-forks.log 10-09 03:29): SIMT is an OPTIONAL unit, encoding kept for dies that have one.
D_OPTIONAL_UNITS = {"SIMT": "absent on r25; a record to an absent unit faults (completion status 3)"}
D_OPS = {k: list(v) for k, v in OPS.items()}
D_OPS["FUSED"] = ["HC_PRE_NORM", "ROW_NORM", "HC_POST", "SOFTMAX"]  # C1 / G4
D_OPS["DMA"] = ["LOAD", "STORE", "FENCE", "KVWB_DS"]              # C7: kv_dense -> opcode (DS native ring = KVWB_DS)
D_OPS["IDX"] = ["INDEX", "RESERVED1", "TOPK", "RESERVED3", "EHASH"]  # G18: one INDEX frame record; 1 / 3 reserved (E_RANGE)  # TOPK generic top-k; EHASH Engram ids (DS G13)
# DS native lowering (hgi_sim ds_native, gaps G8-G14): quantise-dequantise on the act-quant engine, the o-group
# sub-group reduce with multicast, and the selected compressed-row gather from owner dies.
D_OPS["FUSED"] += ["QDQ_FP8", "QDQ_FP4_E8M0", "QDQ_FP4_E4M3"]                          # G8
D_OPS["COLL"] = ["ALL_REDUCE_SUM", "ALL_GATHER", "TOPK_MERGE", "ARGMAX_MERGE", "GROUP_REDUCE_MCAST", "ROW_GATHER"]  # G10, G14
D_UOP_FIELDS = [  # (name, lsb, width): C3a wait 16, C2 opnd 7 (A,B,C,D,O,R,I)
    ("imm_b", 0, 32), ("imm_a", 32, 32), ("param", 64, 25), ("slot", 89, 3), ("tmpl", 92, 1),
    ("opnd", 93, 7), ("pred", 100, 2), ("wait", 102, 16), ("op", 118, 6), ("unit", 124, 4),
]
D_OPND = ["A", "B", "C", "D", "O", "R", "I"]
D_MDESC_FIELDS = [  # G3 ibcast; C4/GDN-6 6-bit DYN codes and a second loop stride
    ("space", 0, 2), ("fmt", 2, 3), ("ibcast", 5, 1), ("base", 8, 40), ("n", 48, 20), ("m", 68, 20),
    ("stride", 88, 32), ("istride", 120, 16), ("lstride", 136, 32), ("dyn_sel", 168, 6), ("dyn_mul", 174, 27),
    ("n_sel", 201, 6), ("l1stride", 207, 32), ("indexed", 6, 1),
]
# C3b REQUIRED (promoted): indexed descriptor.  indexed=1 replaces the DYN term by an id read from the vector memory:
#   base_eff = base + L*lstride + L1*l1stride + U32(VM[I_eff + L]) * dyn_mul        (dyn_sel ignored)
#   n_sel = 63 (N_FROM_VM): n = U32(VM[I_eff + I.stride + L])                        (second row of the I table)
# I_eff = the record's I descriptor effective base (a VM U32 table written by IDX.TOPK or an SU op; order it by `wait`).
NSEL_FROM_VM = 63
D_DYN = ["ZERO", "POS", "POS1", "TOKEN", "L", "RANK", "SLOT", "POS_SLOT", "L1", "WIN_N0", "WIN_START0", "WIN_N1",
         "WIN_START1", "CHUNK_START", "CHUNK_N", "POS_SLOT1"]          # 16-62: DS FULL_DYN selectors; 63 = N_FROM_VM
D_SUT_LAYOUT = []
_o = 0
for _n, _w in SUT_FIELDS:                                         # G1: packed from bit 0 in list order
    D_SUT_LAYOUT.append((_n, _o, _w))
    _o += _w
D_PARAM = {
    "CTL.LOOP": "[15:0] count, [16] level (0 inner L, 1 outer L1)",
    "CTL.TOKX": "PROPOSED (Q-MTP-1, hardware in hfd_cmdproc): A = U32 [1 + ncol]: A[0] = k (1 <= k <= ncol), A[1..k] = "
                "the committed tokens; the CP emits k completion beats {token A[i], pos + i - 1, status 0}; END follows",
    "CTL.END": "token = A[0] (A required on r25: the ARGMAX / COLL.ARGMAX_MERGE output in VM); A-absent form (latest SIMT RESULT) only on dies with SIMT",
    "SM.MATVEC": "[1:0] fmt (0 BF16, 1 FP8 blk, 2 FP4 blk, 3 INT8), [4:2] positions-1 (P <= 8 slots share one weight read; "
                 "A and O then carry one row per slot, m = P; each slot's result is the single-slot arithmetic) (G18)",
    "SU.VOP": "operands = the template's slots, flagged in opnd (A,B,C,D,O,R,I)",
    "SFU.GLU": "C = route weight (a 1.0 constant with ibcast to disable); imm_a = clamp limit (FLT_MAX disables); out fmt = O.fmt",
    "FUSED.ROW_NORM": "[5:0] d_units (width/128: 32|40 prenorm; 8|2 Qwen TP4 QK-norm; with seg 128 and m > 1 rows, the width of one A row), [13:6] seg (0|128); imm_a = eps; out fmt = O.fmt (FP8|BF16|FP32)",
    "FUSED.SOFTMAX": "[0] multipass; A = scores, B = sink row (data: -2^100 for no sink), O = probabilities; imm_a = scale",
    "ARGMAX.LOCAL": "imm_a = id offset multiplier: global id = local + DYN[RANK] * imm_a (DS 1347: uniform 1,347-row head shards; Qwen3-8B 37984) (G17)",
    "ATT.QK/PV": "[3:0] head lanes (0 encodes 16) (G19), [7:4] 64-slices per head - 1, [8] ring; B = first row source (n rows, n_sel POS1 / "
                 "POS_SLOT1 = the mask), C (optional) = second row source appended after B (e.g. DS selected compressed rows); "
                 "ring = 1: B is a ring of B.m slots (power of two), first row read = slot (POS1 - n) mod B.m, wrapping (G12)",
    "FUSED.QDQ_FP8": "act_quant FP8E4M3 with a UE8M0 scale per 32-element block (hfd_quant): O = dequantised values (G8)",
    "FUSED.QDQ_FP4_E8M0": "FP4E2M1 with a UE8M0 scale per 32-element block: O = dequantised values (G8)",
    "FUSED.QDQ_FP4_E4M3": "FP4E2M1 with an FP8E4M3 scale per block; [7:0] block size (v1 legal set {16}, others E_RANGE; DS 16): O = dequantised values (G8)",
    "COLL.ALL_GATHER": "even-split segments: rank r contributes elements [floor(r*n/G), floor((r+1)*n/G)) of A (n = A.n, "
                       "G = group size); every rank receives all n in O (G9)",
    "COLL.GROUP_REDUCE_MCAST": "[7:0] sub-group size s (2, 4, 8): each aligned sub-group of s ranks reduces A in the rank-order "
                               "pairwise tree, and every sub-group's result is multicast to all ranks of the group; "
                               "O = the sub-groups' results in sub-group order, format O.fmt (G10)",
    "COLL.ROW_GATHER": "I = selected row ids (U32, identical on every rank; count from I row 1 or imm_a); A = this die's "
                       "row store; row i is owned by rank (i div B) mod G and stored there at local row "
                       "(i div (B*G))*B + i mod B; [7:0] B (DS 8); imm_b = destination ranks 0..imm_b-1; "
                       "O = the rows in list order on every destination rank (G14)",
    "IDX.EHASH": "Engram row ids of the slot's token: [2:0] Engram layer index; B = that layer's hash constants (table); "
                 "the engine keeps the n-gram token history (pushed by the first EHASH of a token, restored by "
                 "CTL.ACCEPT); O = U32 ids, one per head and n-gram order, an I table for indexed DMA.LOAD (G13)",
    "SIMT.RUN": "OPTIONAL unit, absent on r25. Where present: [13:0] entry PC; imm_a = SM mask; UR4 = imm_b; UR5.. = effective bases of present descriptors in opnd order",
    "IDX.TOPK": "[11:0] k (1..2048), [12] order (0 descending score, 1 ascending id; 1 legal for k <= 8 only, else E_RANGE) (G15); per outer row of A (m rows of n scores): O = k U32 ids sorted by descending score (order 0), ties lowest index; R (optional) = the k values",
    "IDX.INDEX": "one DS indexer frame (G18): [11:0] k (DS 512), [12] cand_en, [13] keep_en; imm_a = n keys, imm_b = layer; A = post-RoPE query (FP32), B = scaled head weights (BF16 values), C = keep bitmap (keep_en), O / R = local top-k ids (ascending) / values, D = candidates (cand_en)",
    "COLL.ALL_REDUCE_SUM": "rank-order pairwise tree over the group (G = 1, 2, 4, 8); G = 96 is rejected (E_RANGE): DS reduces as 12 groups of 8 with GROUP_REDUCE_MCAST s = 8 (GX11)",
    "COLL.TOPK_MERGE": "from VM: A = local values, B = local ids; the group top imm_a by descending value, ties lowest id; O = ids in ascending id order, R (optional) = values; bit-exact gather path (G18)",
    "SM.MATVEC (indexed B)": "expert fetch by id: B.indexed = 1, I = the id table, CTL.LOOP over k experts (L)",
    "DMA.STORE": "linear append (dense KV, GDN state): O base + DYN[POS]*row bytes",
    "DMA.KVWB_DS": "DS native window-ring KV write-back (unchanged)",
}


def d_spec_json():
    return dict(
        schema="opentallas.hbm_generic_iface.v1", status="PROPOSED design for owner review",
        r25_facts=dict(simt="absent: fixed-function SMs, no kernel memory (hbm-forks.log 10-09 03:29)",
                       ds_program="native unit ops only (hbm-sim lowering), no SIMT.RUN"),
        required_new_logic=["indexed descriptors (MDESC indexed, n_sel N_FROM_VM) in the unit dispatchers", "generic IDX.TOPK decode over the existing selector"],
        version=f"{D_VERSION[0]}.{D_VERSION[1]}", doc="docs/HBM_GENERIC_INTERFACE.md", magic=hex(MAGIC), md_words=NWORDS,
        md_fields=[dict(name=n, word=w, lsb=l, width=wd, kind=k, consumer=c, why=y, reset=D_RESET.get(n),
                        legal=(sorted(D_LEGAL[n]) if isinstance(D_LEGAL.get(n), set) else D_LEGAL.get(n)))
                   for n, w, l, wd, k, c, y in D_MD_FIELDS],
        reserved_words=dict(geometry_in_manifest="2-31", static_reserved="42-45, 47-48, 46 bits 31:8",
                            mtp="49, 53-55", window_chunk="50-52", other="59, 62"),
        coll_group_size_defined_rejected=D_GROUP_DEFINED_REJECTED, errors=ERR, fmt=FMT,
        uop=dict(bits=128, fields=[dict(name=n, lsb=l, width=w) for n, l, w in D_UOP_FIELDS], units=D_UNITS,
                 optional_units=D_OPTIONAL_UNITS,
                 ops=D_OPS, op_code="index in ops[unit]", wait_bit="bit u = unit code u", pred=PRED,
                 opnd_order=D_OPND, param=D_PARAM,
                 record="header(16 B) + [SUT 32 B if tmpl] + one MDESC (32 B) per set opnd bit, in A,B,C,D,O,R,I order",
                 same_unit_order="a unit starts a record only after the previous record of the same unit has made its writes visible to that unit"),
        mdesc=dict(bits=256, fields=[dict(name=n, lsb=l, width=w) for n, l, w in D_MDESC_FIELDS], space=SPACE,
                   dyn=D_DYN + ["DS_FULL_DYN[%d]" % i for i in range(47)] + ["N_FROM_VM"],
                   address="base + L*lstride + L1*l1stride + (indexed ? U32(VM[I_eff+L]) : DYN[dyn_sel])*dyn_mul",
                   indexed="id from VM table I (row 0); n_sel=63 takes n from row 1 (I_eff + I.stride + L); id bounds software-owned: hardware checks only the 40-bit HBM / VM range, the simulator faults out-of-region accesses",
                   istride="0 means 1; ibcast=1 means inner stride 0 (per-row scalar broadcast)"),
        sut=dict(bits=256, fields=[dict(name=n, lsb=l, width=w) for n, l, w in D_SUT_LAYOUT],
                 semantics="tools/hdc_program_v41.py Machine.su1 (R-ARITH chunk8); c_pair partner i XOR 1 always (RoPE pairing is in the weights)"),
        programs=dict(images="one program image per die (rank); all images of a group have identical structure "
                             "record for record (unit, op, opnd, collectives in the same order); they may differ in "
                             "descriptor values and immediates, and a record a rank does not run is CTL.NOP (G11)",
                      rank_masks="not used"),
        ds_lowering_items=dict(
            G8=dict(item="FUSED.QDQ_FP8 / QDQ_FP4_E8M0 / QDQ_FP4_E4M3", needs="existing DS act-quant engine behind FUSED; dispatcher decode"),
            G9=dict(item="ALL_GATHER even-split segment rule", needs="none: the DS collective's split rule, stated"),
            G10=dict(item="COLL.GROUP_REDUCE_MCAST", needs="existing DS o-group reduce on the collective (tree tap at log2 s); dispatcher decode"),
            G11=dict(item="per-die program images of identical structure", needs="compiler only"),
            G12=dict(item="ATT second row source (C) and ring wrap", needs="small hardware: ATT row-fetch front end (second list, mask on a power-of-two ring counter)"),
            G13=dict(item="IDX.EHASH Engram ids", needs="existing DS Engram hash engine (ot_hdc_engram_hash) behind IDX; host-written ids are the bring-up fallback"),
            G14=dict(item="COLL.ROW_GATHER", needs="the DS kv_gather collective; dispatcher decode of the owner rule"),
        ),
        linear_attention=dict(scope="in scope via software (owner decision 2026-10-09)", engines="existing (SM, SU, DMA, COLL)",
                              state="FP32 in region STATE, per layer and local head, stored transposed [dv][dk] (GDN-4)",
                              conv_ring="FP32 [conv_k-1][channels] in region STATE", softplus="SU template (no SFU code)",
                              per_head="second loop level (CTL.LOOP level 1, MDESC l1stride)"),
    )


def d_manifest(name):
    spec = MODELS[name]
    raw = (ROOT / spec["cfg"]).read_bytes()
    t = json.loads(raw)
    t = t.get("text_config", t)
    ds = spec["model_class"] == 1
    hd = t["head_dim"]
    rd = t.get("qk_rope_head_dim", hd)
    layers = []
    for i in range(t["num_hidden_layers"]):
        att = dict(kind="dsa_mla" if ds else "gqa", q_heads=t["num_attention_heads"], kv_heads=t["num_key_value_heads"],
                   head_dim=hd, window=t.get("sliding_window") or 0,
                   rope=dict(dims=rd, offset=hd - rd, pairing_in_weights="adjacent" if ds else "split_half_permuted_to_adjacent",
                             table="yarn" if ds else "plain"))
        if ds:
            att.update(compress_ratio=t["compress_ratios"][i], kv_source=i in t["kv_source_layer_ids"],
                       index_source=i in t["index_source_layer_ids"])
        layers.append(dict(idx=i, mixer=att, engram=ds and i in t.get("engram_layer_ids", []), hc=ds,
                           ffn=dict(kind="moe", experts=t["n_routed_experts"], shared=t["n_shared_experts"],
                                    topk=t["num_experts_per_tok"]) if ds else dict(kind="dense", inter=t["intermediate_size"]),
                           norm=dict(kind="rms", eps=t["rms_norm_eps"], qk_norm=not ds)))
    return dict(schema="opentallas.hgi_model_manifest.v1", model=name, config=spec["cfg"],
                config_sha256=hashlib.sha256(raw).hexdigest(),
                globals=dict(hidden=t["hidden_size"], vocab=t["vocab_size"], rope_theta=t["rope_theta"],
                             rope_scaling=t.get("rope_scaling"), softmax_scale=f"FP32(head_dim^-0.5) = {hex(f32bits(hd ** -0.5))}",
                             weight_fmt="FP8E4M3 block32 / FP4 experts" if ds else "INT8 per-row BF16 scale",
                             kv_fmt="FP8E4M3", tp_size=spec["tp"], head_rows_per_die=spec["head_rows"] or None),
                mixer_kinds_supported=["gqa", "dsa_mla", "gated_deltanet (software, see linear_attention)"],
                layers=layers)


def d_pack(md):
    words = [0] * NWORDS
    for name, w, lsb, width, *_ in D_MD_FIELDS:
        if name == "crc32":
            continue
        v = int(md.get(name, 0))
        assert 0 <= v < (1 << width), (name, v)
        if width > 32:
            for k in range(width // 32):
                words[w + k] = (v >> (32 * k)) & 0xFFFFFFFF
        else:
            words[w] |= v << lsb
    words[CRC_WORD] = zlib.crc32(struct.pack("<63I", *words[:63])) & 0xFFFFFFFF
    return words


def d_hw_check(words, busy=False):
    if busy:
        return 4
    if words[0] != MAGIC:
        return 1
    if ((words[1] >> 8) & 0xFF, words[1] & 0xFF) != D_VERSION or ((words[1] >> 16) & 0xFF) != NWORDS:
        return 2
    if zlib.crc32(struct.pack("<63I", *words[:63])) & 0xFFFFFFFF != words[CRC_WORD]:
        return 3
    used = [0] * NWORDS
    for name, w, lsb, width, *_ in D_MD_FIELDS:
        for k in range(max(1, width // 32)):
            used[w + k] |= 0xFFFFFFFF if width >= 32 else ((1 << width) - 1) << lsb
    if any(words[w] & ~used[w] & 0xFFFFFFFF for w in range(1, CRC_WORD)):
        return 6
    v = {n: (words[w] >> l) & ((1 << wd) - 1) for n, w, l, wd, *_ in D_MD_FIELDS if wd <= 32}
    for k, lim in D_LEGAL.items():
        if (v[k] not in lim) if isinstance(lim, set) else not (lim[0] <= v[k] <= lim[1]):
            return 5
    return 0


def d_build(name):
    man = d_manifest(name)
    mbytes = (json.dumps(man, indent=1, sort_keys=True) + "\n").encode()
    g = man["globals"]
    md = dict(magic=MAGIC, ver_minor=D_VERSION[1], ver_major=D_VERSION[0], n_words=NWORDS,
              manifest_sha256=int.from_bytes(hashlib.sha256(mbytes).digest(), "little"),
              cp_vocab=g["vocab"], cp_ctx_max=1 << 20 if MODELS[name]["model_class"] == 1 else 40960,
              coll_group_size=g["tp_size"], entry_ar=1)
    return man, mbytes, md, d_pack(md)


def d_self_test(words):
    out = {}
    w = list(words); w[0] ^= 1; out["bad_magic"] = d_hw_check(w)
    w = list(words); w[1] ^= 1; out["bad_version"] = d_hw_check(w)
    w = list(words); w[40] ^= 1; out["bad_crc"] = d_hw_check(w)
    out["busy"] = d_hw_check(words, busy=True)
    w = list(words); w[46] = (w[46] & ~0xFF) | 12; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["group_12"] = d_hw_check(w)
    w = list(words); w[46] = (w[46] & ~0xFF) | 16; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["group_16"] = d_hw_check(w)
    w = list(words); w[44] |= 1; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["reserved_bit"] = d_hw_check(w)
    w = list(words); w[40] = (1 << 18) - 0; w[63] = zlib.crc32(struct.pack("<63I", *w[:63])); out["vocab_2p18"] = d_hw_check(w)
    return out


def d_main(out_dir=None, check_dir=None):
    names = list(MODELS)
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "spec.json").write_text(json.dumps(d_spec_json(), indent=1) + "\n")
        summ = {}
        for name in names:
            man, mbytes, md, words = d_build(name)
            assert d_hw_check(words) == 0, name
            neg = d_self_test(words)
            assert neg == dict(bad_magic=1, bad_version=2, bad_crc=3, busy=4, group_12=5, group_16=5, reserved_bit=6,
                               vocab_2p18=6), neg
            (out / f"manifest_{name}.json").write_bytes(mbytes)
            (out / f"md_{name}.hex").write_text("".join(f"{x:08x}\n" for x in words))
            modes = {k: md[k] for k in D_RESET}
            summ[name] = dict(block_modes=modes, equals_reset_ds=modes == D_RESET, crc32=hex(words[CRC_WORD]),
                              negative_cases={k: ERR[v] for k, v in neg.items()})
        assert summ["ds_v41_flash"]["equals_reset_ds"]
        (out / "descriptors.json").write_text(json.dumps(summ, indent=1) + "\n")
        print(json.dumps(summ, indent=1))
    if check_dir:
        d = Path(check_dir)
        assert json.loads((d / "spec.json").read_text()) == json.loads(json.dumps(d_spec_json())), "spec drift"
        for name in names:
            man, mbytes, md, words = d_build(name)
            assert (d / f"manifest_{name}.json").read_bytes() == mbytes, f"{name}: manifest drift"
            assert [int(x, 16) for x in (d / f"md_{name}.hex").read_text().split()] == words, f"{name}: MD drift"
        print("hbm_generic_iface: spec, manifests and descriptors current")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args()
    return d_main(a.out, a.check)


if __name__ == "__main__":
    sys.exit(main())
