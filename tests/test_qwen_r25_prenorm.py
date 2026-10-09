"""Isolated successor graph/quantization tests; synthetic data, no quality claim."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import hdc_golden as G
import hdc_golden_v41 as V
import qwen3_deployment_quality as Q

torch.set_num_threads(2)


class PrenormGraphTest(unittest.TestCase):
    def make_model(self, path, prenorm):
        cfg = dict(num_hidden_layers=1, hidden_size=64, num_attention_heads=4,
                   num_key_value_heads=2, head_dim=16, intermediate_size=64,
                   vocab_size=64, rms_norm_eps=1e-6, rope_theta=1000000.)
        (path / "config.json").write_text(json.dumps(cfg))
        gen = torch.Generator().manual_seed(23)
        def rand(shape):
            return torch.randn(shape, generator=gen).to(torch.bfloat16)
        state = {"model.embed_tokens.weight": rand((64, 64)),
                 "model.norm.weight": rand((64,)), "lm_head.weight": rand((64, 64))}
        prefix = "model.layers.0."
        for name, shape in {
            "input_layernorm.weight": (64,), "post_attention_layernorm.weight": (64,),
            "self_attn.q_proj.weight": (64, 64), "self_attn.k_proj.weight": (32, 64),
            "self_attn.v_proj.weight": (32, 64), "self_attn.o_proj.weight": (64, 64),
            "self_attn.q_norm.weight": (16,), "self_attn.k_norm.weight": (16,),
            "mlp.gate_proj.weight": (64, 64), "mlp.up_proj.weight": (64, 64),
            "mlp.down_proj.weight": (64, 64),
        }.items():
            state[prefix + name] = rand(shape)
        with patch.object(Q, "load_state", return_value={k: v.clone() for k, v in state.items()}):
            model = Q.Qwen3(path, "contract", "w8", "fp8", device="cpu", order="r25", prenorm=prenorm)
        return model, state

    def test_raw_checkpoint_quantization_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, raw = self.make_model(Path(tmp), True)
            lay = model.layers[0]
            qkv = torch.cat([raw[f"model.layers.0.self_attn.{p}_proj.weight"] for p in ("q", "k", "v")])
            codes, scales, _ = Q.quantize_w8(qkv)
            self.assertTrue(torch.equal(lay["qkv"]["q"], codes.t().contiguous()))
            self.assertTrue(torch.equal(lay["qkv"]["s"], scales.t().contiguous()))
            self.assertTrue(torch.equal(lay["ln1"], raw["model.layers.0.input_layernorm.weight"]))
            folded = (qkv.float() * lay["ln1"].float()[None]).to(torch.bfloat16)
            folded_codes, folded_scales, _ = Q.quantize_w8(folded)
            self.assertFalse(torch.equal(codes, folded_codes) and torch.equal(scales, folded_scales))

    def test_actual_forward_projects_explicit_norm_at_input_rounding(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, _ = self.make_model(Path(tmp), True)
            calls = []
            actual_mv = model.mv
            def capture(x, weights, tp=1):
                calls.append((x.clone(), weights, tp))
                return actual_mv(x, weights, tp)
            model.mv = capture
            tokens = torch.tensor([[1, 2]])
            initial = model.embed_rows(tokens).reshape(2, 64).numpy()
            weight = model.layers[0]["ln1"].float().numpy()
            norm = np.stack([G.mul(G.mul(row, G.rsqrt(G.add(
                G.mul(G.reduce_chunked(G.mul(row, row)), np.float32(1/64)), np.float32(model.eps)))), weight)
                for row in initial])
            out = model.forward(tokens, model.new_cache(cap=16))
            self.assertTrue(torch.isfinite(out).all())
            self.assertTrue(np.array_equal(calls[0][0].numpy().view(np.uint32), norm.view(np.uint32)))
            weights = calls[0][1]
            codes = weights["q"].t().numpy().astype(np.float32)
            expected = V.mul(V.csum(V.mul(codes[None], G.to_bf16(norm)[:, None])), weights["s"].float().numpy().reshape(1, -1))
            got = actual_mv(calls[0][0], weights).numpy()
            self.assertTrue(np.array_equal(got.view(np.uint32), expected.view(np.uint32)))
            after_mv_mutant = Q.mul(actual_mv(torch.from_numpy(initial), weights), Q.rstd_g(torch.from_numpy(initial), model.eps)[:, None]).numpy()
            self.assertFalse(np.array_equal(got.view(np.uint32), after_mv_mutant.view(np.uint32)))

    def test_history_and_invalid_folded_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy, _ = self.make_model(Path(tmp), False)
            self.assertNotIn("ln1", legacy.layers[0])
            with self.assertRaises(ValueError):
                Q.Qwen3(Path(tmp), "contract", "w8", "fp8", device="cpu", order="r25",
                        prenorm=True, wfile={"fold": True})


if __name__ == "__main__":
    unittest.main()
