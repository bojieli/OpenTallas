import sys
from pathlib import Path
import copy
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import w19_norm_opcode_proof as P


def test_typed_F32_U32_bitviews_and_U16_widen():
    one = P.f32(np.float32(1))
    assert one.u32() == 0x3F800000
    seed = P.Value("U32", np.array(0x3F800000, np.uint32))
    assert seed.f32() == 1
    with pytest.raises(ValueError, match="WIDEN"):
        P.bf16_memory(np.array(1, np.float32)).f32()
    with pytest.raises(ValueError, match="dtype"):
        P.Value("F32", np.array(1, np.uint32))


def test_actual_BF16_opcode_recipe_ties_zero_underflow():
    b = np.array([0x3F808000, 0x3F818000, 0xBF808000, 0xBF818000, 0x00008000, 0x00018000, 0x80000000], np.uint32)
    p = [P.C.op("LOAD", "x", source="input")] + P.C.bf16_round("x", "bf16") + [P.C.op("STORE16", src=["bf16"], byte_enable=True, source_bits="31:16")]
    m = P.Machine(p, {"input": P.f32(b.view(np.float32))}).run()
    assert np.array_equal(m.stored_f32().view(np.uint32), P.G.to_bf16(b.view(np.float32)).view(np.uint32))


def test_integer_modulo_and_arithmetic_canonical_zero():
    p = [P.C.op("LOAD", "a", source="input"), P.C.op("IADD", "b", ["a", "@U1"])]
    m = P.Machine(p, {"input": P.Value("U32", np.array(0xFFFFFFFF, np.uint32))}).run()
    assert m.regs["b"].data == 0
    p = [P.C.op("LOAD", "a", source="input"), P.C.op("FMUL", "b", ["a", "@FHALF"])]
    m = P.Machine(p, {"input": P.f32(np.array(-0.0, np.float32))}).run()
    assert m.regs["b"].data.view(np.uint32) == 0
    tiny = np.array(2, np.uint32).view(np.float32)
    m = P.Machine(p, {"input": P.f32(tiny)}).run()
    assert m.regs["b"].data.view(np.uint32) == 1


@pytest.mark.parametrize("mutation", ["RAW", "arity", "constant", "RF", "STORE16", "WIDEN"])
def test_machine_rejects_invalid_instructions(mutation):
    p = [P.C.op("LOAD", "a", source="input"), P.C.op("FMUL", "b", ["a", "a"])]
    if mutation == "RAW": p[1]["src"][0] = "unwritten"
    elif mutation == "arity": p[1]["src"] = ["a"]
    elif mutation == "constant": p[0]["dst"] = "@EPS"
    elif mutation == "RF":
        p = [P.C.op("LOAD", f"a{i}", source="input") for i in range(30)]
        p += [P.C.op("FADD", "s", ["a0", "a1"])] + [P.C.op("FADD", "s", ["s", f"a{i}"]) for i in range(2, 30)]
    elif mutation == "STORE16": p += [P.C.op("STORE16", src=["b"], byte_enable=False, source_bits="31:16")]
    else: p[1] = P.C.op("WIDEN", "b", ["a"])
    with pytest.raises(ValueError):
        P.Machine(p, {"input": P.f32(np.float32(1))}).run()


def arrays():
    rng = np.random.default_rng(190035)
    res = P.G.to_bf16(rng.normal(size=(4, 5120)).astype(np.float32))
    pre = rng.normal(size=4).astype(np.float32)
    post = rng.normal(size=4).astype(np.float32)
    comb = rng.normal(size=(4, 4)).astype(np.float32)
    model = type("Model", (), {"hc": 4})()
    out = P.V.Model.hc_pre(model, res, pre)
    y = out.copy()
    return {"res": res, "pre_coeff": pre, "post_coeff": post, "comb": comb, "y": y, "pre_output": out, "post_output": P.V.Model.hc_post(model, y, res, post, comb)}


def recipes():
    return {"pre": P.C.vector_program("pre"), "post": P.C.vector_program("post"), "norm_scalar": P.C.scalar_norm_program(), "scale": P.C.scale_program()}


def test_all_four_actual_recipes_against_original_golden():
    m, _, _ = P.phases(recipes(), arrays(), np.ones(5120, np.float32), 1e-20)
    assert m["pre"].stored_f32().shape == (5120,)
    assert m["post"].stored_f32().shape == (20480,)
    assert m["norm_scalar"].regs["y"].kind == "F32"


@pytest.mark.parametrize("mutation", ["order", "denominator", "scale_order", "rounding"])
def test_recipe_mutations_fail_original_boundaries(mutation):
    p = recipes()
    a = arrays()
    if mutation == "order":
        adds = [i for i in p["pre"] if i["op"] == "FADD"]
        adds[1]["src"][1], adds[2]["src"][1] = "p3", "p2"
    elif mutation == "denominator": p["norm_scalar"][1]["src"][1] = "@FHALF"
    elif mutation == "scale_order":
        p["scale"][5]["src"] = ["w", "x"]
        p["scale"][6]["src"] = ["xr", "r"]
    else:
        # Omits BF16 ties-to-even lsb correction while preserving valid dependencies.
        p["pre"][-3]["src"][1] = "@U1"
        # Deliberate halfway value makes the omitted parity bit observable.
        a["res"] = np.ones((4, 5120), np.float32)
        a["pre_coeff"] = np.array([0x3F808000, 0, 0, 0], np.uint32).view(np.float32)
        model = type("Model", (), {"hc": 4})()
        a["pre_output"] = P.V.Model.hc_pre(model, a["res"], a["pre_coeff"])
        a["y"] = a["pre_output"].copy()
        a["post_output"] = P.V.Model.hc_post(model, a["y"], a["res"], a["post_coeff"], a["comb"])
    with pytest.raises(AssertionError):
        P.phases(p, a, P.G.to_bf16(np.linspace(.5, 1.5, 5120, dtype=np.float32)), 1e-20)
