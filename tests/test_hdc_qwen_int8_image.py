"""The reduced INT8 image matches the deployed quantizer and RTL row addresses."""
import sys
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_program as P  # noqa: E402
from hdc_qwen_int8_image import (Int8Layout, first_layer_tp2_matrices,
                                  write_first_layer_tp2_images, write_images)  # noqa: E402


@pytest.mark.skipif(not G.CHECKPOINT.exists(), reason="reduced Qwen checkpoint missing")
def test_tp2_int8_image_addresses_and_quantizer(tmp_path):
    layout = Int8Layout(G.Model(P.GR, 2), 2, 0)
    assert len(layout.quantized) == 17
    assert len(layout.code_words) == layout.emb_word == 10240
    rng = np.random.default_rng(20260928)
    for base, (codes, scales, _) in layout.quantized.items():
        for _ in range(32):
            row = int(rng.integers(codes.shape[0]))
            column = int(rng.integers(codes.shape[1]))
            assert layout.matrix_code(base, row, column) == codes[row, column]
            assert layout.scale_words[base + row // P.W][row % P.W] == scales[row]
    meta = write_images(layout, tmp_path)
    assert meta["matrix_words"] == 10240
    assert meta["embedding_rows"] == 4096
    first_code_word = int((tmp_path / "matrix_int8.hex").read_text().splitlines()[0], 16)
    first_scale_word = int((tmp_path / "matrix_scale_bf16.hex").read_text().splitlines()[0], 16)
    assert first_code_word == P.pack_lanes(layout.code_words[0], 8)
    assert first_scale_word == P.pack_lanes(layout.scale_words[0], 16)
    assert layout.embed_codes.shape == (4096, 128)


def test_shipped_first_layer_quantizes_full_rows_before_tp2_slice(tmp_path):
    """Real checkpoint: O/down use one scale per full row on both dies."""
    import torch
    from safetensors import safe_open
    import qwen3_deployment_quality as Q

    try:
        snapshot = Q.find_snapshot()
    except FileNotFoundError:
        pytest.skip("shipped Qwen3-8B checkpoint missing")
    index = __import__("json").loads((snapshot / "model.safetensors.index.json").read_text())["weight_map"]

    def read(name):
        with safe_open(str(snapshot / index[name]), framework="pt", device="cpu") as f:
            return f.get_tensor(name)

    # Sampling complete rows is exact: W8 selects its scale independently per
    # output row, and we compare against an independent full-row quantization.
    outputs = [first_layer_tp2_matrices(snapshot, die, rows_per_matrix=24) for die in (0, 1)]
    for short, name in (("o", "self_attn.o_proj.weight"), ("down", "mlp.down_proj.weight")):
        full = read("model.layers.0." + name)[:24].float()
        q, s, _ = Q.quantize_w8(full)
        half = full.shape[1] // 2
        for die in (0, 1):
            got = outputs[die][short]
            assert torch.equal(got["codes"], q[:, die * half:(die + 1) * half])
            assert torch.equal(got["scales"], s)
        assert torch.equal(outputs[0][short]["scales"], outputs[1][short]["scales"])
        # The old producer quantized each K slice independently.  Real rows
        # demonstrate that this changes the deployed image.
        old_q, old_s, _ = Q.quantize_w8(full[:, :half])
        assert not (torch.equal(old_q, outputs[0][short]["codes"]) and
                    torch.equal(old_s, outputs[0][short]["scales"]))

    for short, name, norm in (("q", "self_attn.q_proj.weight", "input_layernorm.weight"),
                              ("k", "self_attn.k_proj.weight", "input_layernorm.weight"),
                              ("v", "self_attn.v_proj.weight", "input_layernorm.weight"),
                              ("gate", "mlp.gate_proj.weight", "post_attention_layernorm.weight"),
                              ("up", "mlp.up_proj.weight", "post_attention_layernorm.weight")):
        key = "model.layers.0."
        w = read(key + name)
        n = w.shape[0] // 2
        scale = read(key + norm).float()
        for die in (0, 1):
            ref, ref_scale, _ = Q.quantize_w8(w[die * n:die * n + 24].float() * scale[None])
            assert torch.equal(outputs[die][short]["codes"], ref)
            assert torch.equal(outputs[die][short]["scales"], ref_scale)
    manifest = write_first_layer_tp2_images(snapshot, tmp_path, die=1, rows_per_matrix=24)
    assert not manifest["complete_layer"] and set(manifest["matrices"]) == set(outputs[1])
    for name in manifest["matrices"]:
        assert np.array_equal(np.load(tmp_path / f"{name}_codes.npy"), outputs[1][name]["codes"].numpy())
        assert np.array_equal(np.load(tmp_path / f"{name}_scale_bf16.npy").view(np.int16),
                              outputs[1][name]["scales"].view(torch.int16).numpy())


def test_shipped_first_layer_audit_source_pins():
    import qwen3_deployment_quality as Q
    import torch
    from safetensors import safe_open
    try:
        snapshot = Q.find_snapshot()
    except FileNotFoundError:
        pytest.skip("shipped Qwen3-8B checkpoint missing")
    record = json.loads((ROOT / "results/rtl/qwen_o4_int8_layer0_image_audit.json").read_text())
    index = json.loads((snapshot / "model.safetensors.index.json").read_text())["weight_map"]

    def source_tensor(name):
        with safe_open(str(snapshot / index[name]), framework="pt", device="cpu") as sf:
            return sf.get_tensor(name)

    assert record["verdict"] == "PASS" and record["rows_per_source_matrix"] == 8
    assert record["shared_full_row_scales"] == {"o": True, "down": True}
    for die, manifest in enumerate(record["die_manifests"]):
        assert manifest["die"] == die and not manifest["complete_layer"]
        assert manifest["checkpoint_snapshot"] == snapshot.name
        for name, path in (("checkpoint_index_sha256", snapshot / "model.safetensors.index.json"),
                           ("checkpoint_config_sha256", snapshot / "config.json"),
                           ("producer_sha256", ROOT / "tools/hdc_qwen_int8_image.py"),
                           ("quantizer_sha256", ROOT / "tools/qwen3_deployment_quality.py")):
            assert manifest[name] == hashlib.sha256(path.read_bytes()).hexdigest()
        for item in manifest["matrices"].values():
            lo, hi = item["selected_rows"]
            source = source_tensor(item["source"])[lo:hi].contiguous().view(torch.int16).numpy()
            assert item["source_rows_sha256"] == hashlib.sha256(source.tobytes()).hexdigest()
            if item["norm_sha256"]:
                layer = item["source"].split(".")[:3]
                norm = ("input_layernorm.weight" if item["source"].split(".")[3] == "self_attn"
                        else "post_attention_layernorm.weight")
                n = source_tensor(".".join(layer + [norm])).contiguous().view(torch.int16).numpy()
                assert item["norm_sha256"] == hashlib.sha256(n.tobytes()).hexdigest()
