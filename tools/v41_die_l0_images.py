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
K_MEM = 1 << 24            # the runtime wrapper's stack model (ot_v41_rt_die.sv); a 2^21-sector RoPE table fits
                           # under the 0.9 usable cap
WIN_STACK, WIN_BASE, WIN_PITCH = 0, 1 << 18, 17
WIN_COUNT = 128 * WIN_PITCH
RESERVED_END = 1 << 19      # first free sector after the window ring (and every default state region)
ROPE_PLAIN_BASE = 1 << 19
ROPE_YARN_BASE = 1 << 19      # an indexed layer holds only the YaRN table, at the same place
CKV_BASE = 1 << 22            # per stack: the striped compressed-KV rows (tools/v41_selection_global_ids.py)
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


def rope_sectors(cs, sn, pos: int, base: int = ROPE_PLAIN_BASE) -> dict:
    """{stack: {sector: word}}: stack k holds pairs 8k..8k+7, two sectors a position, pair = {sin, cos}."""
    pair = [(int(G.bits(sn[p])) << 32) | int(G.bits(cs[p])) for p in range(32)]
    out = {}
    for k in range(4):
        for j in range(2):
            w = 0
            for q in range(4):
                w |= pair[8 * k + 4 * j + q] << (64 * q)
            out.setdefault(k, {})[base + 2 * pos + j] = w
    return out


def slice_of(rank: int, experts: list[int], layer: int = 0) -> dict:
    s = dict(R.SHIPPED, ratio=R.RATIO)
    return {n: dict(tensor=t, rows=list(r) if r else None, cols=list(c) if c else None)
            for n, t, r, c in LC.die_slices(layer, rank, s, experts, False)}


def weight_ops(rk, slices: dict) -> list[dict]:
    out = []
    for e in rk.log:
        if e.get("unit") not in ("QE", "ME", "HE") or e.get("matrix") in ("scores", "pv", "index_scores", None):
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


def dense_vm(vm: np.ndarray, ok: np.ndarray) -> str:
    bits = np.where(ok, G.bits(vm), 0).astype(np.uint32)
    return "".join(f"{int(b):08x}\n" for b in bits)


def rt_weights(wops: list[dict]) -> list[dict]:
    """The runtime wrapper's ROM-field list: QE LINQ and ME weight ops in program order (HE ops use hbank)."""
    out = []
    for o in wops:
        if o["unit"] == "HE":
            continue
        rows = o["rows"] or [0, None]
        cols = o["cols"] or [0, None]
        full_cols = {"F8_E4M3": 1, "I8": 2, "BF16": 0.5}[o["format"]] * o["stored_shape"][1]
        full_rows = o["stored_shape"][0]
        r0, r1 = (rows if o["rows"] else [0, full_rows])
        c0, c1 = (cols if o["cols"] else [0, int(full_cols)])
        if o["unit"] == "QE":
            key = o["wbase"] + (o["expert"] or 0) * (o["istride"] if o["expert"] is not None else 0)
            ent = dict(pc=o["pc"], kind="qe", key=key, tensor=o["tensor"],
                       fmt="fp4" if o["format"] == "I8" else "fp8", rows=[r0, r1], cols=[c0, c1],
                       out="fp32" if o["unrounded"] else "bf16", scale_tensor=o["tensor"][:-len("weight")] + "scale")
        else:
            if "group" in o:
                r0, r1 = r0 + o["group_rows"][0], r0 + o["group_rows"][1]
            ent = dict(pc=o["pc"], kind="me", key=o["wbase"], tensor=o["tensor"], fmt="bf16", rows=[r0, r1],
                       cols=[c0, c1], out="fp32")
            if o["format"] == "F8_E4M3":
                ent.update(source_fmt="fp8", scale_tensor=o["tensor"][:-len("weight")] + "scale",
                           note="wo_a ships FP8 (32x32 UE8M0); the golden dequantises it to BF16 "
                                "(to_bf16(Q8.dense())) -- the ME weight is that BF16 matrix")
        ent.update(tag=o["tag"], expert=o.get("expert"), nout=o["out_rows"], k=o["k"])
        out.append(ent)
    return out


def write_rt(rd: Path, rk, d: Path, pos, rows, ring, ring_cur, rope, wops, golden, yarn=False):
    """The runtime wrapper's contract (rtl/test/v41_runtime/ot_v41_rt_die.sv on claude/w17-fullshape)."""
    import shutil
    rd.mkdir(parents=True, exist_ok=True)
    for n in ("prog.hex", "crom.hex", "hbank.hex"):
        shutil.copyfile(d / n, rd / n)
    V_ = rk.V
    init = np.zeros(1 << 19, dtype=np.float32)
    ok = np.zeros(1 << 19, dtype=bool)
    h = golden["z"]["h_in"].reshape(-1).astype(np.float32)
    for base, vals in ((V_["H"], h), (V_["PF"], golden["z"]["pre_in"].astype(np.float32)),
                       (V_["SSX"], np.array([V.csum(G.mul(h, h))], dtype=np.float32))):
        init[base:base + len(vals)] = vals
        ok[base:base + len(vals)] = True
    (rd / "vm_init.hex").write_text(dense_vm(init, ok))
    (rd / "expect_vm.hex").write_text(dense_vm(rk.vm, rk.ok))
    end = WIN_BASE + WIN_COUNT
    for name, rg in (("hbm0.hex", ring_cur), ("hbm0_without_current_row.hex", ring)):
        words = [0] * end
        for a, w in rg.items():
            words[a] = w
        (rd / name).write_text("".join(f"{w:064x}\n" for w in words))
    for k in range(4):
        (rd / f"hbmsparse{k}.hex").write_text("".join(f"{a:x} {w:064x}\n" for a, w in sorted(rope[k].items())))
    cfg = dict(token=golden["token_history"][-1], pos=pos, user=0, cfg_ik_base=1 << 29, window_region_valid=1,
               window_region_base=WIN_BASE, window_region_count=WIN_COUNT, window_prime_user=0,
               rope_table_present=2 if yarn else 1)
    for k in range(4):
        cfg.update({f"rope_reserved_end{k}": RESERVED_END, f"rope_plain_base{k}": 0 if yarn else ROPE_PLAIN_BASE,
                    f"rope_yarn_base{k}": ROPE_YARN_BASE if yarn else 0})
    (rd / "cfg.txt").write_text("".join(f"{k} {v if isinstance(v, int) and v < 4096 else hex(v)}\n"
                                        for k, v in cfg.items()))
    # the 128 absolute row tags of the window ring (tb_v41_l0_live_chain primes the same 128: pos-127 .. pos)
    (rd / "prime.txt").write_text("".join(f"{r}\n" for r in range(pos - 127, pos + 1)))
    (rd / "weights.json").write_text(json.dumps(rt_weights(wops), indent=1) + "\n")
    (rd / "README.txt").write_text(
        "hbm0_without_current_row.hex: stack 0 K memory from sector 0 through the window ring (window_region_base + "
        "128*17) holding rows pos-127 .. pos-1 (synthetic golden state); the die writes row pos itself (core "
        "g_packed_window_write captures the QDQ8 row, confirmed by W17) -- use this file. hbm0.hex additionally "
        "preloads row pos with the golden's own FP8 window row (the ISA executor proves it equal to the program's "
        "KVQ). hbmsparse<s>.hex: the RoPE entry of pos (plain at L0, YaRN at L20; stack s: pairs 8s..8s+7, sectors "
        "rope_<kind>_base + 2*pos + {0,1}, pair = {sin, cos}). prime.txt: window_prime_row pulses (user 0) before "
        "start, one per line. vm_init/expect_vm: dense 2^19 x 32-bit. LAYER 20 also: ikhbm_region.hex, this rank's "
        "index-key quarter (global keys [r*SC1, (r+1)*SC1) before pos) as '<sector> <word>' lines in the 68-B "
        "super-block layout, sectors relative to the key region (the bench maps the region to its stack/base; the "
        "program writes key pos itself); ckv_s<k>.hex, the compressed rows this die owns (16-row groups striped "
        "die = g[5:4], stack = g[7:6]; 9 sectors a 288-B row at CKV_BASE + 9*local + k on stack k), row pos "
        "excluded (the program writes it). weights.json: the ROM-field weight ops in program order.\n")


def key_superblocks(nib: np.ndarray, sc: np.ndarray) -> dict:
    """{sector: 256-bit int} of index keys in the 68-B super-block layout (ot_hdc_v41x_idx_kstream; tools/
    hdc_images_v41x.py ikhbm_image at the full 128-dim key): key t of the region, super-block b = t // 1024,
    tt = t % 1024: codes (128 E2M1 nibbles, dim d at bits 4d) in sectors (17 b + 1 + tt // 64) * 128 + 2 (tt % 64)
    and + 1 (dims 0..63, 64..127); the 4 UE8M0 bytes (block j at bits 8j) the 32-bit field tt % 8 of sector
    17 b * 128 + tt // 8.  Sectors region-relative."""
    out = {}
    for t in range(len(nib)):
        b, tt = divmod(t, 1024)
        v = int.from_bytes(nib[t].tobytes(), "little")
        cs = (17 * b + 1 + tt // 64) * 128 + 2 * (tt % 64)
        out[cs] = v & ((1 << 256) - 1)
        out[cs + 1] = v >> 256
        ss = 17 * b * 128 + tt // 8
        out[ss] = out.get(ss, 0) | (int.from_bytes(sc[t].tobytes(), "little") << (32 * (tt % 8)))
    return out


def ckv_sectors(nib: np.ndarray, sc: np.ndarray, die: int) -> dict:
    """{stack: {sector: word}} of the compressed rows die `die` owns (tools/v41_selection_global_ids.py: 16-row
    groups striped over dies then stacks; 288-B row = 256 B of E2M1 nibbles + 32 E4M3 scales, 9 sectors, byte 0
    the low byte of a sector) at CKV_BASE + 9 * local + k."""
    import v41_selection_global_ids as SG
    out = {k: {} for k in range(4)}
    g = np.arange(len(nib))
    own = ((g >> 4) & 3) == die
    for gi in g[own]:
        _, stack, local = SG.owner(int(gi))
        row = nib[gi].tobytes() + sc[gi].tobytes()
        for k in range(9):
            out[stack][CKV_BASE + 9 * local + k] = int.from_bytes(row[32 * k:32 * (k + 1)], "little")
    return out


def build(ctx: int, out_root: Path, snapshots: bool, log=print, seed: int = LC.SEED, layer: int = 0) -> dict:
    bind, scratch = X.case(ctx, seed, layer)
    tag = (f"ctx{ctx}" if seed == LC.SEED else f"ctx{ctx}_s{seed}") + (f"_L{layer}" if layer else "")
    program = X.PROGRAM_L20 if layer == 20 else X.PROGRAM
    yarn = bool(R.RATIO[layer])
    ranks = []
    snapdirs = {}

    def on_pc(pc, rks):
        if not snapshots:
            return
        for rk in rks:
            d = snapdirs.setdefault(rk.r, out_root / f"{tag}_r{rk.r}")
            d.mkdir(parents=True, exist_ok=True)
            sparse(d / f"vm_pc{pc:03d}.hex", vm_runs(rk.vm, rk.ok), 8)

    res = X.run_context(ctx, scratch, bind, program, log_fn=log, on_pc=on_pc, ranks_out=ranks, seed=seed,
                        layer=layer)
    if res["verdict"] != "pass":
        raise SystemExit(f"ctx {ctx}: the ISA executor does not pass; no die images written")
    golden = X.load_golden(ctx, scratch, seed, layer)
    pos = golden["position"]
    lay = X.BoundLayout(bind)
    fields = [X.I.decode(int(w, 16), full_shape=True) for w in program.read_text().split()]
    for f, row in zip(fields, lay.bind["instruction_trace"]):
        f["_tag"] = row["tag"]
    # the shared inputs: HE banks, window ring, RoPE entry
    ldir = Path(f"/home/ubuntu/w17work/isa/layout_{'1m' if ctx == 1048576 else '200k'}"
                + ("" if seed == LC.SEED else f"_s{seed}") + (f"_L{layer}" if layer else ""))
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
    st, _ = LC.synthetic_state(m, ctx, seed=seed, layers=[layer])
    win = np.stack(st["win"][layer]).astype(np.float32)
    kv_state = None
    if layer in R.KV_SRC:
        ckv = np.stack(st["ckv"][layer]).astype(np.float32)
        ik = np.stack(st["ik"][layer]).astype(np.float32)
        cn, cscl = LC.pack_fp4_e4m3(ckv)
        sc1 = -(-(pos + 1) // 4)
        kv_state = dict(ckv_nib=cn, ckv_sc=cscl, ik=ik, sc1=sc1, rows=len(ckv))
        del ckv
    del st
    rows = list(range(pos - len(win), pos))
    codes, scales = LC.pack_fp8_ue8m0(win)
    ring = window_ring(codes, scales, rows)
    for t, row in enumerate(rows):
        assert np.array_equal(G.bits(decode_ring(ring, row % 128)), G.bits(win[t])), "window ring round trip"
    cur = golden["z"][f"win{layer}"].reshape(1, -1).astype(np.float32)
    ccodes, cscales = LC.pack_fp8_ue8m0(cur)
    ring_cur = {**ring, **window_ring(ccodes, cscales, [pos])}
    cs, sn = V.rope_cs(m.freqs_yarn if yarn else m.freqs_plain, pos)
    rope = rope_sectors(cs, sn, pos, ROPE_YARN_BASE if yarn else ROPE_PLAIN_BASE)
    prog_words = program.read_text()
    params = dict(FULL_SHAPE=1, N_TP=4, X_ROM=1, X_HE=1, X_ATT=1, SUN=16, VM_AW=19, K_MEM=K_MEM,
                  WIN_STACK=WIN_STACK, WINDOW_HBM_ATTENTION=1, ROPE_MAX_POS=ROPE_MAX_POS, HHW=8, HBAW=16, CROM_AW=15,
                  PROG_AW=14)
    ranks_rec = {}
    for rk in ranks:
        d = out_root / f"{tag}_r{rk.r}"
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
        state_files = {}
        if kv_state is not None:
            # the rank's index-key quarter (global keys [r SC1, (r+1) SC1) before this position; the position's own
            # key is written by the program) and the compressed rows this die owns (the position's row likewise)
            lo = rk.r * kv_state["sc1"]
            hi = min(kv_state["rows"], lo + kv_state["sc1"])
            kn, ksc = LC.pack_fp4_ue8m0(kv_state["ik"][lo:hi])
            rt = out_root / tag / f"r{rk.r}"
            rt.mkdir(parents=True, exist_ok=True)
            kimg = key_superblocks(kn, ksc)
            (rt / "ikhbm_region.hex").write_text("".join(f"{a:x} {w:064x}\n" for a, w in sorted(kimg.items())))
            cimg = ckv_sectors(kv_state["ckv_nib"], kv_state["ckv_sc"], rk.r)
            for k in range(4):
                (rt / f"ckv_s{k}.hex").write_text("".join(f"{a:x} {w:064x}\n" for a, w in sorted(cimg[k].items())))
            state_files = dict(keys=[lo, hi], key_sectors=len(kimg),
                               ckv_rows_owned=int(sum(len(v) for v in cimg.values()) // 9))
        rk.fields = fields
        wops = weight_ops(rk, slice_of(rk.r, golden["experts"], layer))
        (d / "weight_ops.json").write_text(json.dumps(dict(
            context=ctx, rank=rk.r, experts=golden["experts"],
            seed=seed, layer=layer, image_dir=str(scratch / "images" / f"ctx{ctx}_L{layer:02d}_r{rk.r}"),
            image_manifest_sha256=X.sha(scratch / "images" / f"ctx{ctx}_L{layer:02d}_r{rk.r}" / "manifest.json"),
            ops=wops), indent=1) + "\n")
        write_rt(out_root / tag / f"r{rk.r}", rk, d, pos, rows, ring, ring_cur, rope, wops, golden, yarn)
        man = dict(
            schema=SCHEMA + ".rank", context=ctx, position=pos, seed=seed, layer=layer, rank=rk.r,
            state_images=state_files,
            die_parameters=dict(params, RANK=rk.r),
            inputs=dict(host_mode=1, host_token=golden["token_history"][-1], host_pos=pos, host_user=0,
                        host_entry=0, window_region_valid=1, window_region_base=WIN_BASE,
                        window_region_count=WIN_COUNT, window_prime_user=0,
                        window_rows_preloaded=[rows[0], rows[-1]], window_current_row_slot=pos % 128,
                        rope_table_present="2'b10 (YaRN only; an indexed layer)" if yarn else
                        "2'b01 (plain only; L0 is a sliding layer)",
                        rope_plain_base=[0 if yarn else ROPE_PLAIN_BASE] * 4,
                        rope_yarn_base=[ROPE_YARN_BASE if yarn else 0] * 4,
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
    return dict(context=ctx, position=pos, seed=seed, layer=layer, isa_verdict=res["verdict"],
                isa_regions={r["region"]: r["bit_exact"] for r in res["regions"]}, ranks=ranks_rec,
                bench=dict(params, inputs_common=dict(window_region_base=WIN_BASE, window_region_count=WIN_COUNT,
                                                      rope_plain_base=ROPE_PLAIN_BASE, rope_reserved_end=RESERVED_END)),
                sources=dict(bind=str(bind.relative_to(ROOT)), bind_sha256=X.sha(bind),
                             layout_sha256=X.sha(lay.layout_path), program_sha256=X.sha(program)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--context", type=int, action="append")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--snapshots", action="store_true")
    ap.add_argument("--record", type=Path)
    ap.add_argument("--seed", type=int, default=LC.SEED, help="golden seed (20260930: the 1M reference token)")
    ap.add_argument("--layer", type=int, default=0, help="0 or 20")
    a = ap.parse_args()
    ctxs = a.context or [1048576, 200000]
    recs = {X.case_key(c, a.seed, a.layer): build(c, a.out, a.snapshots, seed=a.seed, layer=a.layer) for c in ctxs}
    if a.record:
        srcs = ("tools/v41_die_l0_images.py", "tools/v41_fullshape_isa.py", "tools/rtl_hdc_v41x_attn_campaign.py",
                "tools/v41_fullshape_weight_layout.py", "tools/rtl_v41_fullshape_layer_campaign.py",
                "results/rtl/hdc_v41x_fullshape_l0_program.hex", "results/rtl/w17_l0_fullshape_isa.json",
                "results/rtl/w17_v41_1m_reference_token.json")
        old = json.loads(a.record.read_text()) if a.record.exists() else {}
        rec = dict(schema=SCHEMA, status="input_only",
                   claim_boundary="Die image sets and bench contract for the full-shape L0 RTL run; expected VMs "
                                  "from the passing ISA executor. No RTL verdict.",
                   contexts={**old.get("contexts", {}), **recs}, headline=f"1048576_seed{X.REF_SEED}",
                   source_sha256={s: X.sha(ROOT / s) for s in srcs})
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
        print("wrote", a.record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
