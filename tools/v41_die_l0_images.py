#!/usr/bin/env python3
"""Per-rank image sets for the full-shape layer-0 RTL die run (ot_chip_v41x_die FULL_SHAPE=1, X_ROM=1).

    python3 tools/v41_die_l0_images.py --context 1048576 [--context 200000] [--out /home/ubuntu/w17work/die]
        [--snapshots] [--record results/rtl/w17_die_l0_images.json]

For each context C and rank r it writes <out>/ctx<C>_r<r>/:

  prog.hex          the encoded production L0 program (results/rtl/hdc_v41x_fullshape_l0_program.hex,
                    2048-bit words; identical at 1M and 200K -- DYN carries the position)
  crom.hex          the constant ROM as the bound layout places it, THIS rank's contents (the attention sinks
                    are the rank's 16 heads), sparse `@addr` records of 64-bit {hi, lo} words (lo = FP32, hi = +0)
  hbank.hex         the HCP weight banks (X_HE=1): hc_attn_fn at bank word 0, hc_ffn_fn at 7680, as
                    tools/v41_fullshape_weight_layout.py pack_he_fp32 lays them out (8 banks x HHW=8 FP32
                    lanes); entry index = bank_word * 8 + bank, 256-bit {lane7 .. lane0}
  vm_init.hex       the harness preload, exactly as tools/v41_fullshape_isa.py preloads it: H (4 x 5120, the
                    golden shard's h_in), PF (pre_in) and SSX = csum(h_in^2); every other element 0
  hbm_s<k>.hex      sparse `@sector` images of HBM stack k (256-bit sectors): the packed FP8 window ring on
                    WIN_STACK (tools/v41_l0_live_chain.py layout: sector window_base + slot*17 + g, g < 16 the
                    265-bit group words' 256-bit payloads, sector +16 the 16 UE8M0 scales) holding the 127 rows
                    before this position at slot = row mod 128, and the plain RoPE table entry of this position
                    (stack k holds pairs 8k .. 8k+7 in sectors plain_base + 2*pos + {0, 1}, pair = {sin, cos});
                    every other sector 0.  hbm_s0_with_current_row.hex additionally holds the golden's own
                    window row of this position at slot pos mod 128 (for a bench whose die does not write it)
  expect_vm.hex     the ISA executor's final vector memory of this rank (every written element; the rest 0)
  vm_pc<NNN>.hex    (--snapshots) the executor's vector memory after each PC, for localising a divergence
  weight_ops.json   every weight op in program order: PC, unit, tag, wbase / istride / expert id, the matrix
                    and this rank's exact checkpoint slice (tensor, rows, cols, format, image file sha256)
  manifest.json     every die parameter and cfg/host input the bench must drive, the image hashes and the
                    source records they came from

The ISA executor runs once per context (all four ranks in lockstep) and must pass bit-exact against the golden
before any image is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_fullshape_isa as X  # noqa: E402  (sets HDC_V41_ARITH=chunk8)
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import rtl_hdc_v41x_attn_campaign as A  # noqa: E402
import rtl_v41_fullshape_layer_campaign as LC  # noqa: E402

OUT = Path("/home/ubuntu/w17work/die")
SCHEMA = "opentallas.rtl.w17_die_l0_images.v1"
# die / bench contract (manifest)
K_MEM = 1 << 22            # a 2^21-sector read-only RoPE table must fit under the 0.9 usable cap
WIN_STACK, WIN_BASE, WIN_PITCH = 0, 1 << 18, 17
WIN_COUNT = 128 * WIN_PITCH
RESERVED_END = 1 << 19      # first free sector after the window ring (and every default state region)
ROPE_PLAIN_BASE = 1 << 19
ROPE_MAX_POS = 1 << 20
HE_BASES = {"hc_attn_fn": 0, "hc_ffn_fn": 7680}


def sha(p) -> str:
    return X.sha(Path(p))


def sparse(path: Path, regions: dict, width_hex: int):
    """`@addr` + one word a line; regions: {base: iterable of ints}."""
    with path.open("w") as f:
        for base, words in sorted(regions.items()):
            words = list(words)
            if not words:
                continue
            f.write(f"@{base:x}\n")
            f.write("".join(f"{int(w):0{width_hex}x}\n" for w in words))


def vm_runs(vm: np.ndarray, ok: np.ndarray) -> dict:
    """Written elements as contiguous runs {base: bits}."""
    idx = np.nonzero(ok)[0]
    if not idx.size:
        return {}
    cut = np.nonzero(np.diff(idx) != 1)[0] + 1
    bits = G.bits(vm)
    return {int(r[0]): bits[r].tolist() for r in np.split(idx, cut)}


def window_ring(codes: np.ndarray, scales: np.ndarray, rows: list[int]) -> dict:
    """{sector: 256-bit word} of the packed FP8 window ring for (row position, codes, UE8M0 bytes)."""
    out = {}
    for t, row in enumerate(rows):
        slot = row % 128
        word = A.row_word(0, codes[t], np.repeat(scales[t], 2))
        sc = 0
        for g in range(16):
            blk = (word >> (265 * g)) & ((1 << 265) - 1)
            assert blk >> 264 == 0
            out[WIN_BASE + slot * WIN_PITCH + g] = blk & ((1 << 256) - 1)
            sc |= (blk >> 256) << (8 * g)
        out[WIN_BASE + slot * WIN_PITCH + 16] = sc
    return out


def decode_ring(ring: dict, slot: int) -> np.ndarray:
    """The BF16 row back from its ring sectors (self-check of the encoding)."""
    sc = ring[WIN_BASE + slot * WIN_PITCH + 16]
    vals = []
    for g in range(16):
        w = ring[WIN_BASE + slot * WIN_PITCH + g]
        e = ((sc >> (8 * g)) & 255) - 127
        vals += [V.E4M3[(w >> (8 * x)) & 255] * 2.0 ** e for x in range(32)]
    return np.array(vals, dtype=np.float32)


def rope_sectors(cs, sn, pos: int) -> dict:
    """{stack: {sector: word}}: stack k holds pairs 8k..8k+7, two sectors a position, pair = {sin, cos}."""
    pair = [(int(G.bits(sn[p])) << 32) | int(G.bits(cs[p])) for p in range(32)]
    out = {}
    for k in range(4):
        for j in range(2):
            w = 0
            for q in range(4):
                w |= pair[8 * k + 4 * j + q] << (64 * q)
            out.setdefault(k, {})[ROPE_PLAIN_BASE + 2 * pos + j] = w
    return out


def slice_of(rank: int, experts: list[int]) -> dict:
    s = dict(R.SHIPPED, ratio=R.RATIO)
    return {n: dict(tensor=t, rows=list(r) if r else None, cols=list(c) if c else None)
            for n, t, r, c in LC.die_slices(0, rank, s, experts, False)}


def weight_ops(rk, slices: dict) -> list[dict]:
    out = []
    for e in rk.log:
        if e.get("unit") not in ("QE", "ME", "HE") or e.get("matrix") in ("scores", "pv"):
            continue
        name = e["matrix"].split(".group")[0]
        f = rk.fields[e["pc"]]
        ent = slices[name]
        man = rk.man["files"][f"w.{name}"]
        row = dict(pc=e["pc"], unit=e["unit"], tag=f["_tag"], matrix=e["matrix"], **ent,
                   format=man["format"], stored_shape=man["shape"], image_file=f"w.{name}.bin",
                   image_sha256=man["sha256"], out_rows=e["rows"], k=e["k"])
        if f"w.{name}.scale" in rk.man["files"]:
            sm = rk.man["files"][f"w.{name}.scale"]
            row.update(scale_file=f"w.{name}.scale.bin", scale_format=sm["format"], scale_shape=sm["shape"],
                       scale_sha256=sm["sha256"])
        if e["unit"] == "QE":
            row.update(wbase=f["qe_wbase"], istride=f["qe_istride"], expert=e.get("expert"),
                       expert_id_vm=f["qe_ibase"] if f["qe_ind"] else None, fp4=bool(f["qe_fp4"]),
                       unrounded=bool(f["qe_unrounded"]), x_vm=f["qe_xbase"], out_vm=f["qe_obase"], nb=f["qe_nb"],
                       tiles=f["qe_tiles"])
        elif e["unit"] == "ME":
            row.update(wbase=f["me_wbase"], split=1 << f["me_split"], x_vm=f["me_xbase"], out_word=f["me_obase"],
                       tiles=f["me_tiles"], me_k=f["me_k"])
            if ".group" in e["matrix"]:
                g = int(e["matrix"].split("group")[1])
                row.update(group=g, group_rows=[g * 1024, (g + 1) * 1024],
                           note="rows of this rank's wo_a slice (checkpoint rows = slice rows[0] + group_rows)")
        else:
            row.update(wbase=f["he_wbase"], he_k=f["he_k"], x_vm=f["he_xbase"], out_vm=f["he_obase"],
                       hbank_base=HE_BASES[name])
        out.append(row)
    return out


def build(ctx: int, out_root: Path, snapshots: bool, log=print) -> dict:
    ranks = []
    snapdirs = {}

    def on_pc(pc, rks):
        if not snapshots:
            return
        for rk in rks:
            d = snapdirs.setdefault(rk.r, out_root / f"ctx{ctx}_r{rk.r}")
            d.mkdir(parents=True, exist_ok=True)
            sparse(d / f"vm_pc{pc:03d}.hex", vm_runs(rk.vm, rk.ok), 8)

    res = X.run_context(ctx, X.SCRATCH, X.BIND[ctx], X.PROGRAM, log_fn=log, on_pc=on_pc, ranks_out=ranks)
    if res["verdict"] != "pass":
        raise SystemExit(f"ctx {ctx}: the ISA executor does not pass; no die images written")
    golden = X.load_golden(ctx, X.SCRATCH)
    pos = golden["position"]
    lay = X.BoundLayout(X.BIND[ctx])
    fields = [X.I.decode(int(w, 16), full_shape=True) for w in X.PROGRAM.read_text().split()]
    for f, row in zip(fields, lay.bind["instruction_trace"]):
        f["_tag"] = row["tag"]
    # the shared inputs: HE banks, window ring, RoPE entry
    ldir = Path(f"/home/ubuntu/w17work/isa/layout_{'1m' if ctx == 1048576 else '200k'}")
    he = {}
    for name, base in HE_BASES.items():
        rec = lay.layout["matrices"][name]
        img = np.fromfile(ldir / f"{name}.he.bin", dtype="<u4").reshape(-1, 8, 8)
        if X.sha(ldir / f"{name}.he.bin") != rec["output_image_sha256"] or rec["base_word"] != base:
            raise SystemExit(f"{name}: HE bank image differs from the bound layout")
        for w in range(img.shape[0]):
            for b in range(8):
                he[(base + w) * 8 + b] = sum(int(img[w, b, l]) << (32 * l) for l in range(8))
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    st, _ = LC.synthetic_state(m, ctx, layers=[0])
    win = np.stack(st["win"][0]).astype(np.float32)
    rows = list(range(pos - len(win), pos))
    codes, scales = LC.pack_fp8_ue8m0(win)
    ring = window_ring(codes, scales, rows)
    for t, row in enumerate(rows):
        assert np.array_equal(G.bits(decode_ring(ring, row % 128)), G.bits(win[t])), "window ring round trip"
    cur = golden["z"]["win0"].reshape(1, -1).astype(np.float32)
    ccodes, cscales = LC.pack_fp8_ue8m0(cur)
    ring_cur = {**ring, **window_ring(ccodes, cscales, [pos])}
    cs, sn = V.rope_cs(m.freqs_plain, pos)
    rope = rope_sectors(cs, sn, pos)
    prog_words = X.PROGRAM.read_text()
    params = dict(FULL_SHAPE=1, N_TP=4, X_ROM=1, X_HE=1, X_ATT=1, SUN=16, VM_AW=19, K_MEM=K_MEM,
                  WIN_STACK=WIN_STACK, WINDOW_HBM_ATTENTION=1, ROPE_MAX_POS=ROPE_MAX_POS, HHW=8, HBAW=16, CROM_AW=15,
                  PROG_AW=14)
    ranks_rec = {}
    for rk in ranks:
        d = out_root / f"ctx{ctx}_r{rk.r}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "prog.hex").write_text(prog_words)
        crom = {int(a): [(int(G.bits(rk.crom[a, 1])) << 32) | int(G.bits(rk.crom[a, 0]))]
                for a in np.nonzero(rk.crom_ok)[0]}
        sparse(d / "crom.hex", crom, 16)
        sparse(d / "hbank.hex", {a: [w] for a, w in he.items()}, 64)
        V_ = rk.V
        h = golden["z"]["h_in"].reshape(-1).astype(np.float32)
        pre = {V_["H"]: G.bits(h).tolist(), V_["PF"]: G.bits(golden["z"]["pre_in"].astype(np.float32)).tolist(),
               V_["SSX"]: [int(G.bits(np.float32(V.csum(G.mul(h, h)))))]}
        sparse(d / "vm_init.hex", pre, 8)
        for k in range(4):
            reg = dict(rope[k])
            if k == WIN_STACK:
                reg.update(ring)
            sparse(d / f"hbm_s{k}.hex", {a: [w] for a, w in reg.items()}, 64)
        reg0 = {**rope[WIN_STACK], **ring_cur}
        sparse(d / "hbm_s0_with_current_row.hex", {a: [w] for a, w in reg0.items()}, 64)
        sparse(d / "expect_vm.hex", vm_runs(rk.vm, rk.ok), 8)
        rk.fields = fields
        wops = weight_ops(rk, slice_of(rk.r, golden["experts"]))
        (d / "weight_ops.json").write_text(json.dumps(dict(
            context=ctx, rank=rk.r, experts=golden["experts"],
            image_dir=str(X.SCRATCH / "images" / f"ctx{ctx}_L00_r{rk.r}"),
            image_manifest_sha256=X.sha(X.SCRATCH / "images" / f"ctx{ctx}_L00_r{rk.r}" / "manifest.json"),
            ops=wops), indent=1) + "\n")
        man = dict(
            schema=SCHEMA + ".rank", context=ctx, position=pos, rank=rk.r,
            die_parameters=dict(params, RANK=rk.r),
            inputs=dict(host_mode=1, host_token=golden["shard"]["token_history"][-1], host_pos=pos, host_user=0,
                        host_entry=0, window_region_valid=1, window_region_base=WIN_BASE,
                        window_region_count=WIN_COUNT, window_prime_user=0,
                        window_rows_preloaded=[rows[0], rows[-1]], window_current_row_slot=pos % 128,
                        rope_table_present="2'b01 (plain only; L0 is a sliding layer)",
                        rope_plain_base=[ROPE_PLAIN_BASE] * 4, rope_yarn_base=[0] * 4,
                        rope_reserved_end=[RESERVED_END] * 4, cfg_ik_base=1 << 29, cfg_me_xs=0, cfg_q_base=0,
                        cfg_q_lbase=0, cfg_q_lead=512, cfg_q_rate=0, cfg_users=1, cfg_prompt_len=0, cfg_gen_len=0,
                        note="cfg_* as tools/v41_l0_live_chain.py's bench drives them (the L0 program reads no "
                             "index/Q-stream state); collectives through the die's coll engine (unit 6 descriptors "
                             "in prog.hex), coll_go port idle"),
            images={p.name: X.sha(p) for p in sorted(d.glob("*")) if p.suffix in (".hex", ".json")
                    and not p.name.startswith("vm_pc") and p.name != "manifest.json"},
            snapshots=snapshots,
            expect_vm_elements=int(rk.ok.sum()),
            weight_ops=len(wops))
        (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        ranks_rec[str(rk.r)] = dict(dir=str(d), manifest_sha256=X.sha(d / "manifest.json"), images=man["images"],
                                    weight_ops=len(wops), expect_vm_elements=man["expect_vm_elements"])
        log(f"ctx {ctx} rank {rk.r}: {d} ({len(wops)} weight ops, {man['expect_vm_elements']} VM elements)")
    return dict(context=ctx, position=pos, isa_verdict=res["verdict"],
                isa_regions={r["region"]: r["bit_exact"] for r in res["regions"]}, ranks=ranks_rec,
                bench=dict(params, inputs_common=dict(window_region_base=WIN_BASE, window_region_count=WIN_COUNT,
                                                      rope_plain_base=ROPE_PLAIN_BASE, rope_reserved_end=RESERVED_END)),
                sources=dict(bind=str(X.BIND[ctx].relative_to(ROOT)), bind_sha256=X.sha(X.BIND[ctx]),
                             layout_sha256=X.sha(lay.layout_path), program_sha256=X.sha(X.PROGRAM)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--context", type=int, action="append")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--snapshots", action="store_true")
    ap.add_argument("--record", type=Path)
    a = ap.parse_args()
    ctxs = a.context or [1048576, 200000]
    recs = {str(c): build(c, a.out, a.snapshots) for c in ctxs}
    if a.record:
        srcs = ("tools/v41_die_l0_images.py", "tools/v41_fullshape_isa.py", "tools/rtl_hdc_v41x_attn_campaign.py",
                "tools/v41_fullshape_weight_layout.py", "tools/rtl_v41_fullshape_layer_campaign.py",
                "results/rtl/hdc_v41x_fullshape_l0_program.hex", "results/rtl/w17_l0_fullshape_isa.json")
        old = json.loads(a.record.read_text()) if a.record.exists() else {}
        rec = dict(schema=SCHEMA, status="input_only",
                   claim_boundary="Die image sets and bench contract for the full-shape L0 RTL run; expected VMs "
                                  "from the passing ISA executor. No RTL verdict.",
                   contexts={**old.get("contexts", {}), **recs},
                   source_sha256={s: X.sha(ROOT / s) for s in srcs})
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
        print("wrote", a.record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
