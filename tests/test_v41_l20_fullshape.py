"""The exact TP-4 layer-20 program (the indexed layer) and its ISA-level contracts.

Program: results/rtl/hdc_v41x_fullshape_l20_program.hex (bound for the seed-20260930 1M reference token).
Record:  results/rtl/w17_l20_fullshape_isa.json (tools/v41_fullshape_isa.py --layer 20).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import v41_program_constants as KC  # noqa: E402

PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l20_program.hex"
BIND = ROOT / "results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json"
RECORD = ROOT / "results/rtl/w17_l20_fullshape_isa.json"


def words():
    return [I.decode(int(x, 16), full_shape=True) for x in PROGRAM.read_text().split()]


def test_coll_d_stride_sits_at_a_fixed_offset_clear_of_appended_fields():
    assert I.FULL_LAYOUT["coll_d_stride"] == (2042, I.FULL_D)
    top = max(o + w for n, (o, w) in I.FULL_LAYOUT.items() if n != "coll_d_stride")
    assert top <= 2042
    assert I.FULL_DYN["NEWBLK"] == 52


def test_encoded_program_matches_the_bind_and_its_immediates_the_manifest():
    bind = json.loads(BIND.read_text())
    w = words()
    c = KC.load()
    assert bind["layer"] == 20 and len(w) == bind["instruction_count"] == 144
    for pc, (row, d) in enumerate(zip(bind["instruction_trace"], w)):
        for k, v in row["fields"].items():
            v = I.FULL_DYN[tuple(v)] if isinstance(v, list) else I.FULL_DYN[v] if isinstance(v, str) else v
            assert d[k] == v, (pc, k)
        src = row.get("imm_sources", {})
        for field in ("imm1", "imm2", "imm3"):
            if field in src:
                assert d[field] == KC.bits(c, src[field]), (pc, field)
            else:
                assert d[field] == 0, (pc, row["tag"], field)


def test_index_and_candidate_merges_follow_the_collective_dma_contract():
    merges = [d for d in words() if d["unit"] == I.UNIT_COLL and d["coll_op"] == I.COLL_TOPK_MERGE]
    assert [(m["coll_n"], m["coll_k"]) for m in merges] == [(512, 512), (2048, 2048)]
    assert merges[0]["coll_d_stride"] == I.FULL_DYN["SC1"]
    assert merges[1]["coll_d_stride"] == I.FULL_DYN[("ceil", "SC1", 8)]
    for m in merges:          # ot_chip_v41x_coll_dma (GW = 4): n a multiple of 64, dst 4-word aligned, n <= 2048
        assert m["coll_n"] % 64 == 0 and m["coll_dst"] % 64 == 0 and m["coll_n"] <= 2048
        assert m["coll_ibase"] % 16 == 0 and m["coll_src"] % 16 == 0


def test_weights_proj_is_replicated_and_head_sum_reads_32_weights():
    import rtl_v41_fullshape_layer_campaign as LC
    s = dict(R.SHIPPED, ratio=R.RATIO)
    for rank in range(4):
        rows = {n: r for n, _, r, _ in LC.die_slices(20, rank, s, [], False)}
        assert rows["indexer.weights_proj"] is None
    lay = R.ShapeLayout(R.SHIPPED, tp_exact=True, layer=20)
    assert lay.mat[(20, "iwp")]["n"] == 32


def test_newblk_pins_the_newest_block_only_on_its_owner_rank():
    for pos in (1048575, 199999, 65535):
        sc1 = -(-(pos + 1) // 4)
        owner = pos // sc1
        for rank in range(4):
            v = R.newblk(R.SHIPPED, pos, rank)
            assert v == ((pos - rank * sc1) // 8 if rank == owner else -(-sc1 // 8))


def test_topk_merge_semantics_equal_the_golden_over_global_scores():
    import v41_fullshape_isa as X
    rng = np.random.default_rng(7)
    n, k, stride = 64, 48, 1000
    glob = np.full(4 * stride, -np.inf)

    class Rk:
        def __init__(self, r):
            self.r, self.vm, self.ok = r, np.zeros(4096, np.float32), np.zeros(4096, bool)
            self.dyn = [0] * 64
            self.dyn[I.FULL_DYN["SC1"]] = stride
            self.unwritten, self.log = [], []
        read, write = X.Rank.read, X.Rank.write

    ranks = [Rk(r) for r in range(4)]
    for rk in ranks:
        local = np.round(rng.standard_normal(stride) * 4) / 4             # many ties
        local[:5] = -0.0
        glob[rk.r * stride:(rk.r + 1) * stride] = local
        ids = sorted(int(i) for i in V.topk_lowest_index(local, n))
        rk.write(0, local[ids].astype(np.float32))
        rk.write(512, np.array(ids, np.uint32).view(np.float32))
    f = dict(coll_n=n, coll_src=0, coll_dst=1024, coll_op=I.COLL_TOPK_MERGE, wait=31, coll_k=k, coll_ibase=512,
             coll_d_stride=I.FULL_DYN["SC1"], coll_seq=0, coll_rnd=0)
    X.collective(ranks, f, 0, [])
    want = sorted(int(i) for i in V.topk_lowest_index(glob, k))
    for rk in ranks:
        assert rk.vm[1024:1024 + k].view(np.uint32).tolist() == want


def test_l20_record_is_bit_exact_on_four_ranks_with_the_contract():
    rec = json.loads(RECORD.read_text())
    c = rec["contexts"]["1048576_seed20260930_L20"]
    assert rec["status"] == "pass" and c["verdict"] == "pass"
    assert not c["defects"] and not c["unwritten_reads"]
    names = {r["region"] for r in c["regions"]}
    for want in ("L20.index_scores (rank quarter)", "L20.index_select", "L20.candidate_blocks", "L20.attn",
                 "L20.ffn", "h_out", "pre_out", "ik20 (index key)", "ckv20 (compressed row)"):
        assert want in names
    assert all(r["bit_exact"] for r in c["regions"])
    assert rec["contract"]["COLL_TOPK_MERGE"]["coll_op"] == 2
    assert c["inputs"]["program_sha256"] == KC.sha(PROGRAM)


def test_l20_program_su_ops_are_legal_at_256_lanes():
    import v41_fullshape_isa as X
    import v41_su_legality as S
    for pos in (1048575, 199999):
        d = X.full_dyn(pos)
        for pc, f in enumerate(words()):
            if f["unit"] != I.UNIT_SU:
                continue
            f = dict(f, su_nout=f["su_nout"] + d[f["su_d_nout"]], su_nin=f["su_nin"] + d[f["su_d_nin"]])
            assert not S.check_op(f, 256, 64, 7), (pos, pc)
