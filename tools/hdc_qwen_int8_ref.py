#!/usr/bin/env python3
"""Reduced TP-2 ISA reference for the deployed Qwen signed-INT8 arithmetic.

This is a reduced, unfolded-norm vehicle. It deliberately does not claim a
full-shape O4 token: it supplies independent expected memories and logits for
the RTL package gate, including post-accumulation BF16 row scales.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
from hdc_qwen_int8_image import Int8Layout, write_images


class Int8Machine(P.Machine):
    def __init__(self, lay, kv):
        super().__init__(lay, kv)
        self.codes = np.stack(lay.code_words).reshape(-1).view(np.int8)
        self.embed = lay.embed_codes.view(np.int8).reshape(-1)
        self.embed_scales = G.from_bits(lay.embed_scales.astype(np.uint32) << 16)

    def wrom_f32(self, elems):
        elems = np.asarray(elems)
        embed_base = self.lay.emb_word * P.W * P.GR
        if np.all(elems < embed_base):
            return self.codes[elems].astype(np.float32)
        if np.all(elems >= embed_base):
            offsets = elems - embed_base
            row = offsets // self.lay.H
            return G.mul(self.embed[offsets].astype(np.float32), self.embed_scales[row])
        raise AssertionError("matrix and embedding source mixed in one ISA operation")

    def me(self, f, dyn):
        super().me(f, dyn)
        if f["me_wsrc"]:
            return
        wb = f["me_wbase"] + dyn[f["me_d_wbase"]]
        codes, scales_bf16, meta = self.lay.quantized[wb]
        scales = G.from_bits(scales_bf16.astype(np.uint32) << 16)
        n = f["me_nout"] + dyn[f["me_d_nout"]]
        rows = np.arange(n)
        assert len(scales) == n, (wb, len(scales), n)
        if f["me_oen"]:
            # Output rows are laid out in round/tile/slot order by the ISA.
            split = 1 << f["me_split"]
            per_round = P.GR // split
            tile, slot, lane = rows // (P.W * P.IL), rows // P.W % P.IL, rows % P.W
            out_words = f["me_obase"] + tile * f["me_ots"] + slot * f["me_ojs"]
            addr = out_words * P.W + lane
            self.vm[addr] = G.mul(self.vm[addr], scales)
        if f["me_amax"]:
            self.logits = G.mul(self.logits, scales)
            self.argmax = int(np.argmax(self.logits))


def build(out: Path, ngen: int = 3):
    model = G.Model(P.GR, 2)
    prompt, _ = G.prompt_and_expected()
    layouts = [Int8Layout(model, 2, d) for d in range(2)]
    progs = [P.build_program(lay) for lay in layouts]
    group = P.TPGroup(layouts)
    group.m = [Int8Machine(lay, mach.kv) for lay, mach in zip(layouts, group.m)]
    sequence, steps, generated = list(prompt), [], []
    for pos in range(len(prompt) + ngen - 1):
        token_in = sequence[pos]
        token_out = group.run(progs, token_in, pos)
        steps.append((token_in, token_out, int(G.bits(group.val))))
        if pos >= len(prompt) - 1:
            generated.append(token_out)
            sequence.append(token_out)
    out.mkdir(parents=True, exist_ok=True)
    for d, lay in enumerate(layouts):
        write_images(lay, out / f"die{d}")
        words, desc = P.encode_segments(progs[d])
        (out / f"prog_d{d}.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        (out / f"desc_d{d}.hex").write_text(P.hexwords(desc, 64))
        (out / f"crom_d{d}.hex").write_text(P.hexwords(((P.f32(hi) << 32) | P.f32(lo) for lo, hi in lay.crom), 64))
        (out / f"expect_vm_d{d}.hex").write_text(P.hexwords(G.bits(group.m[d].vm), 32))
        (out / f"expect_kv_d{d}.hex").write_text(P.hexwords(G.bits(group.m[d].kv), 32))
    (out / "prompt.hex").write_text(P.hexwords(prompt, 16))
    (out / "generated.hex").write_text(P.hexwords(generated, 16))
    (out / "expect_steps.hex").write_text(P.hexwords(((a << 48) | (b << 32) | c for a, b, c in steps), 64))
    record = {"tp": 2, "steps": [dict(pos=p, token_in=a, token_out=b, logit_bits=c)
                                  for p, (a, b, c) in enumerate(steps)],
              "generated": generated, "program_words_per_die": [len(P.encode_segments(x)[0]) for x in progs],
              "matrix_words_per_die": [len(x.code_words) for x in layouts],
              "claim_boundary": "Reduced unfolded-norm signed-INT8 ISA reference; RTL bit-exactness and full O4 pending."}
    (out / "int8_tp2_reference.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ngen", type=int, default=3)
    args = ap.parse_args()
    print(json.dumps(build(args.out, args.ngen), indent=2))
