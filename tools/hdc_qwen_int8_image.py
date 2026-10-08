#!/usr/bin/env python3
"""Reduced Qwen INT8 matrix and embedding images for the TP RTL address map.

This uses the deployed W8 quantizer. The reduced TP golden still has unfolded
norms, so these images establish the code/scale layout, not an O4 token gate.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

import hdc_golden as G
import hdc_program as P
from qwen3_deployment_quality import quantize_w8


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
    parser.add_argument("--tp", type=int, default=2)
    parser.add_argument("--die", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    model = G.Model(P.GR, args.tp)
    print(write_images(Int8Layout(model, args.tp, args.die), args.out))


if __name__ == "__main__":
    main()
