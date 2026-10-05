#!/usr/bin/env python3
"""Qwen INT8 images for the reduced RTL and shipped TP-2 weight contract.

This uses the deployed W8 quantizer. The reduced TP golden still has unfolded
norms, so these images establish the code/scale layout, not an O4 token gate.
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import torch

import hdc_golden as G
import hdc_program as P
from qwen3_deployment_quality import quantize_w8


def quantize_full_rows_then_partition(weight: torch.Tensor, *, die: int,
                                      axis: str, norm: Optional[torch.Tensor] = None,
                                      tp: int = 2):
    """Quantize full output rows, then take one TP die's rows or columns.

    The deployed W8 scale is chosen from every column of an output row. For
    o/down (input-column split), quantizing the die slice would choose a
    different scale and codes. q/k/v and gate/up first fold the appropriate
    RMSNorm weight in FP32, exactly as Prep.layer in the quality harness does.
    ``weight`` may contain a selected set of complete checkpoint rows: W8 is
    independently quantized per output row, so this supports small exact tests.
    """
    if axis not in ("rows", "columns") or tp < 1 or not 0 <= die < tp:
        raise ValueError((axis, die, tp))
    if weight.ndim != 2 or weight.shape[{"rows": 0, "columns": 1}[axis]] % tp:
        raise ValueError("TP axis must divide the complete matrix")
    full = weight.to(torch.float32)
    if norm is not None:
        if norm.ndim != 1 or norm.numel() != full.shape[1]:
            raise ValueError("norm length must equal the full input dimension")
        full = full * norm.to(torch.float32)[None, :]
    codes, scales, _ = quantize_w8(full)
    if axis == "rows":
        n = codes.shape[0] // tp
        sl = slice(die * n, (die + 1) * n)
        return codes[sl].contiguous(), scales[sl].contiguous()
    k = codes.shape[1] // tp
    return codes[:, die * k:(die + 1) * k].contiguous(), scales.contiguous()


def layer_tp2_matrices(snapshot: Path, layer: int, die: int, *, rows_per_matrix: Optional[int] = None):
    """Stream one shipped checkpoint layer into exact TP-2 W8 slices.

    ``rows_per_matrix`` limits each source matrix to its first complete rows
    for a quick image preflight; an unrestricted call emits the entire layer.
    The returned arrays are row-major codes plus one BF16 scale per row. Their
    mapping to ROM engine words belongs to the shipped-shape program emitter.
    """
    from safetensors import safe_open
    from hdc_qwen_fullshape_placement_w12 import TP
    if not 0 <= layer < 36 or not 0 <= die < TP:
        raise ValueError('shipped layer or TP die out of range')
    snapshot = Path(snapshot)
    idx = json.loads((snapshot / "model.safetensors.index.json").read_text())["weight_map"]

    def get(key):
        with safe_open(str(snapshot / idx[key]), framework="pt", device="cpu") as sf:
            return sf.get_tensor(key)

    p = f"model.layers.{layer}."
    norms = {"input": get(p + "input_layernorm.weight"),
             "post": get(p + "post_attention_layernorm.weight")}
    specs = (("q", "self_attn.q_proj.weight", "rows", "input"),
             ("k", "self_attn.k_proj.weight", "rows", "input"),
             ("v", "self_attn.v_proj.weight", "rows", "input"),
             ("o", "self_attn.o_proj.weight", "columns", None),
             ("gate", "mlp.gate_proj.weight", "rows", "post"),
             ("up", "mlp.up_proj.weight", "rows", "post"),
             ("down", "mlp.down_proj.weight", "columns", None))
    result = {}
    for short, name, axis, norm_name in specs:
        key = p + name
        w = get(key)
        full_shape = tuple(w.shape)
        if rows_per_matrix is not None:
            if rows_per_matrix < 1:
                raise ValueError("rows_per_matrix must be positive")
            # Row-split shards select global rows first. Column-split shards
            # share the same complete rows and must share their BF16 scales.
            if axis == "rows":
                per_die = full_shape[0] // TP
                lo = die * per_die
                w = w[lo:lo + min(rows_per_matrix, per_die)]
                # The row selection has happened; quantize its full columns.
                q, s = quantize_full_rows_then_partition(w, die=0, axis="columns",
                                                        norm=norms.get(norm_name), tp=1)
                selected_rows = (lo, lo + len(w))
            else:
                w = w[:rows_per_matrix]
                q, s = quantize_full_rows_then_partition(w, die=die, axis="columns", tp=TP)
                selected_rows = (0, len(w))
        else:
            q, s = quantize_full_rows_then_partition(w, die=die, axis=axis,
                                                    norm=norms.get(norm_name), tp=TP)
            selected_rows = ((die * full_shape[0] // TP, (die + 1) * full_shape[0] // TP)
                             if axis == "rows" else (0, full_shape[0]))
        source_hash = hashlib.sha256(w.contiguous().view(torch.int16).numpy().tobytes()).hexdigest()
        norm_hash = (hashlib.sha256(norms[norm_name].contiguous().view(torch.int16).numpy().tobytes()).hexdigest()
                     if norm_name is not None else None)
        result[short] = dict(codes=q, scales=s, source=key, full_shape=full_shape,
                             selected_rows=selected_rows, tp_axis=axis,
                             source_rows_sha256=source_hash, norm_sha256=norm_hash)
    return result


def first_layer_tp2_matrices(snapshot: Path, die: int, *, rows_per_matrix: Optional[int] = None):
    """Backward-compatible layer-0 source for the reduced/shipped audit."""
    return layer_tp2_matrices(snapshot, 0, die, rows_per_matrix=rows_per_matrix)


def shipped_vocab_rows(snapshot: Path, kind: str, *, start: int, count: int, die: Optional[int] = None):
    """Quantize a bounded embedding or TP2 lm_head row window from the lock.

    Rows are independent under W8, so consecutive windows compose into the
    complete shipped image without changing any code or BF16 row scale.
    ``start`` is a local die row for lm_head and a global token for embedding.
    """
    from safetensors import safe_open
    if kind not in ('embedding', 'lm_head') or start < 0 or count < 1:
        raise ValueError('invalid vocabulary image window')
    if kind == 'lm_head':
        from hdc_qwen_fullshape_placement_w12 import TP
        rows_die = 151936 // TP
        if not 0 <= die < TP or start + count > rows_die:
            raise ValueError('lm_head TP window exceeds die vocabulary slice')
        key, global_start = 'lm_head.weight', die * rows_die + start
    else:
        if die is not None or start + count > 151936:
            raise ValueError('embedding window exceeds global vocabulary')
        key, global_start = 'model.embed_tokens.weight', start
    snapshot = Path(snapshot)
    index = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    with safe_open(str(snapshot / index[key]), framework='pt', device='cpu') as sf:
        rows = sf.get_slice(key)[global_start:global_start + count]
    codes, scales, _ = quantize_w8(rows.float())
    return {'codes': codes.contiguous(), 'scales': scales.contiguous(),
            'source': key, 'global_start': global_start, 'count': count,
            'kind': kind, 'die': die}


def write_first_layer_tp2_images(snapshot: Path, out: Path, *, die: int,
                                  rows_per_matrix: Optional[int] = None):
    """Write independently inspectable row-major W8 code/scale arrays."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    matrices = first_layer_tp2_matrices(snapshot, die, rows_per_matrix=rows_per_matrix)
    manifest = dict(schema="qwen3-8b-o4-int8-layer0-tp2.v1", die=die, tp=2,
                    checkpoint_snapshot=Path(snapshot).name,
                    checkpoint_index_sha256=hashlib.sha256((Path(snapshot) / "model.safetensors.index.json").read_bytes()).hexdigest(),
                    checkpoint_config_sha256=hashlib.sha256((Path(snapshot) / "config.json").read_bytes()).hexdigest(),
                    producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    quantizer_sha256=hashlib.sha256(Path(__file__).with_name("qwen3_deployment_quality.py").read_bytes()).hexdigest(),
                    quantization="signed INT8 W8 full output row before TP slicing; BF16 row scale",
                    norm_fold="FP32 weight times BF16 norm, before W8, for q/k/v/gate/up",
                    complete_layer=rows_per_matrix is None, matrices={})
    for name, item in matrices.items():
        cp, sp = out / f"{name}_codes.npy", out / f"{name}_scale_bf16.npy"
        np.save(cp, item["codes"].numpy())
        np.save(sp, item["scales"].view(torch.int16).numpy().view(np.uint16))
        manifest["matrices"][name] = dict(source=item["source"], full_shape=item["full_shape"],
                                          selected_rows=item["selected_rows"], tp_axis=item["tp_axis"],
                                          source_rows_sha256=item["source_rows_sha256"],
                                          norm_sha256=item["norm_sha256"],
                                          codes_shape=list(item["codes"].shape),
                                          codes_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),
                                          scales_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())
    (out / "int8_layer0_tp2.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def write_first_layer_tp2_audit(snapshot: Path, out: Path, *, rows: int = 8):
    """Source-pinned two-die preflight for the first real checkpoint layer."""
    with tempfile.TemporaryDirectory(prefix="qwen-o4-int8-layer0-") as tmp:
        manifests = [write_first_layer_tp2_images(snapshot, Path(tmp) / f"die{d}",
                                                   die=d, rows_per_matrix=rows)
                     for d in (0, 1)]
    shared_scales = {}
    for name in ("o", "down"):
        hashes = [m["matrices"][name]["scales_sha256"] for m in manifests]
        shared_scales[name] = hashes[0] == hashes[1]
    if not all(shared_scales.values()):
        raise AssertionError("input-column TP split did not preserve shared full-row scales")
    record = dict(schema="qwen3-8b-o4-int8-layer0-audit.v1", verdict="PASS",
                  boundary="first-layer image quantization only; no full-shape token or RTL verdict",
                  rows_per_source_matrix=rows, shared_full_row_scales=shared_scales,
                  die_manifests=manifests)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


class Int8Layout(P.Layout):
    """Keep ISA word addresses while adding dense INT8 codes and row scales."""

    def __init__(self, model, tp=2, die=0):
        self.code_words = []
        self.scale_words = {}
        self.quantized = {}
        super().__init__(model, tp, die)
        embed = np.asarray(model.w["model.embed_tokens.weight"], dtype=np.float32)
        codes, scales, _ = quantize_w8(torch.from_numpy(embed.copy()))
        self.embed_codes = codes.numpy().view(np.uint8)
        self.embed_scales = scales.view(torch.int16).numpy().view(np.uint16).reshape(-1)

    def place_matrix(self, w):
        result = super().place_matrix(w)
        base, n, k = result["base"], result["n"], w.shape[1]
        assert base == len(self.code_words)
        codes_t, scales_t, _ = quantize_w8(torch.from_numpy(np.asarray(w, dtype=np.float32).copy()))
        codes = codes_t.numpy().view(np.uint8)
        scales = scales_t.view(torch.int16).numpy().view(np.uint16).reshape(-1)
        split, kc, rounds = result["split"], result["k"], result["tiles"]
        per_round = P.GR // split
        padded = np.zeros((rounds * per_round * P.W * P.IL, k), dtype=np.uint8)
        padded[:n] = codes
        blocks = padded.reshape(rounds, per_round, P.IL, P.W, split, kc)
        for r in range(rounds):
            for kk in range(kc):
                for j in range(P.IL):
                    word = np.empty(P.W * P.GR, dtype=np.uint8)
                    for g in range(P.GR):
                        q, c = divmod(g, split)
                        word[g * P.W:(g + 1) * P.W] = blocks[r, q, j, :, c, kk]
                    self.code_words.append(word)
        for row, scale in enumerate(scales):
            addr = base + row // P.W
            slot = self.scale_words.setdefault(addr, np.zeros(P.W, dtype=np.uint16))
            assert slot[row % P.W] == 0
            slot[row % P.W] = scale
        self.quantized[base] = (codes, scales, result)
        assert len(self.code_words) == len(self.words)
        return result

    def matrix_code(self, base, row, column):
        codes, _, meta = self.quantized[base]
        assert 0 <= row < codes.shape[0] and 0 <= column < codes.shape[1]
        split, kc = meta["split"], meta["k"]
        per_round = P.GR // split
        tile, slot, lane = row // (P.W * P.IL), row // P.W % P.IL, row % P.W
        round_idx, q = divmod(tile, per_round)
        c, kk = divmod(column, kc)
        word = base + round_idx * kc * P.IL + kk * P.IL + slot
        return self.code_words[word][(q * split + c) * P.W + lane]


def write_images(layout, out):
    out.mkdir(parents=True, exist_ok=True)
    dense_scales = [layout.scale_words.get(i, np.zeros(P.W, dtype=np.uint16))
                    for i in range(len(layout.code_words))]
    (out / "matrix_int8.hex").write_text(P.hexwords((P.pack_lanes(w, 8) for w in layout.code_words),
                                                      8 * P.W * P.GR))
    (out / "matrix_scale_bf16.hex").write_text(P.hexwords((P.pack_lanes(w, 16) for w in dense_scales),
                                                            16 * P.W))
    embed_lanes = 64
    assert layout.embed_codes.shape[1] % embed_lanes == 0
    (out / "embed_int8.hex").write_text(P.hexwords((P.pack_lanes(w, 8) for w in
                                                       layout.embed_codes.reshape(-1, embed_lanes)),
                                                    8 * embed_lanes))
    (out / "embed_scale_bf16.hex").write_text(P.hexwords(layout.embed_scales, 16))
    sources = [Path(__file__), Path(P.__file__), Path(G.__file__),
               Path(__file__).with_name("qwen3_deployment_quality.py"), G.CHECKPOINT]
    images = [out / name for name in ("matrix_int8.hex", "matrix_scale_bf16.hex",
                                     "embed_int8.hex", "embed_scale_bf16.hex")]
    meta = {"tp": layout.tp, "die": layout.die, "matrix_words": len(layout.code_words),
            "matrix_scale_words": len(dense_scales), "embedding_rows": len(layout.embed_scales),
            "embedding_codes_per_word": embed_lanes,
            "embedding_element_address_base": layout.emb_word * P.W * P.GR,
            "input_sha256": {str(path.relative_to(G.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sources},
            "image_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in images},
            "claim_boundary": "Reduced image layout and embedding-row gate only; the full TP token and production bank layout remain open."}
    (out / "int8_image.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shipped-snapshot", type=Path,
                        help="Emit shipped Qwen3-8B layer-0 TP2 row-major W8 arrays")
    parser.add_argument("--rows-per-matrix", type=int,
                        help="Preflight using this many complete rows per source matrix")
    parser.add_argument("--audit-out", type=Path,
                        help="Write a source-pinned two-die first-layer audit record")
    parser.add_argument("--tp", type=int, default=2)
    parser.add_argument("--die", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.audit_out is not None:
        if args.shipped_snapshot is None:
            parser.error("--audit-out requires --shipped-snapshot")
        print(json.dumps(write_first_layer_tp2_audit(args.shipped_snapshot, args.audit_out,
                                                      rows=args.rows_per_matrix or 8), indent=2))
        return
    if args.out is None:
        parser.error("--out is required unless --audit-out is supplied")
    if args.shipped_snapshot is not None:
        if args.tp != 2:
            parser.error("shipped snapshot currently requires --tp 2")
        print(json.dumps(write_first_layer_tp2_images(args.shipped_snapshot, args.out,
                                                        die=args.die,
                                                        rows_per_matrix=args.rows_per_matrix), indent=2))
        return
    model = G.Model(P.GR, args.tp)
    print(write_images(Int8Layout(model, args.tp, args.die), args.out))


if __name__ == "__main__":
    main()
