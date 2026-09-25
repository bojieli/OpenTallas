"""The DeepSeek-V4.1 configuration of the hardwired decode core: ISA, program,
ISA-level model against the golden, the committed RTL record, the cycle model."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import rtl_hdc_v41_decode_campaign as campaign  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not V.CHECKPOINT.exists(), reason="build the reduced V4.1 v2 fixture (tools/build_deepseek_v41_reduced_model.py)")


def test_isa_package_is_generated_from_the_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "PKG", tmp_path / "isa.svh")
    I.emit_package()
    assert (tmp_path / "isa.svh").read_text() == (ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh").read_text()


def test_encode_decode_round_trip():
    f = dict(unit=I.UNIT_SU, wait=0b10110, pred=I.PRED_ODD, a_base=12345, imm3=0x41200000, sfu=I.SFU_EGATE,
             qe_mode=I.QE_QDQ4E, xu_op=I.XU_EGATHER, he_k=640)
    d = I.decode(I.encode(**f))
    assert all(d[k] == v for k, v in f.items())


def test_dyn_values_cover_the_window_and_the_selection():
    d = I.dyn_values(5, 39)
    D = I.DYN
    assert d[D["POS1"]] == 40 and d[D["N2"]] == 20 and d[D["NSEL1"]] == 16 and d[D["NSEL2"]] == 16
    assert d[D["T1"]] == 56 and d[D["RND_T1"]] == 1 and d[D["ROW1"]] == 40 * 32
    assert d[D["SLOTE"]] == 64 and d[D["CKV2"]] == 19 * 32


def test_schedule_waits_only_on_conflicting_units():
    import hdc_program_v41 as P
    prog = [(dict(unit=I.UNIT_HE), {"H"}, {"MIX"}, "a"),
            (dict(unit=I.UNIT_SU), {"H"}, {"X"}, "b"),        # reads what nobody writes: no wait
            (dict(unit=I.UNIT_SU), {"MIX"}, {"P"}, "c"),      # reads the HE's output: waits for the HE
            (dict(unit=I.UNIT_QE), {"X"}, {"Y"}, "d")]        # reads the stream unit's output
    out = P.schedule(prog)
    assert [f["wait"] for f in out] == [0, 0, 1 << (I.UNIT_HE - 1), 1 << (I.UNIT_SU - 1)]


@needs_checkpoint
def test_program_on_the_isa_model_is_bit_exact_with_the_golden():
    import copy
    import hdc_program_v41 as P
    model = V.Model()
    prompt, expected = V.prompt_and_expected()
    lay = P.Layout(model)
    prog = P.Builder(lay).build()
    pos = len(prompt) - 1
    st = P.golden_prefill(model, prompt[:-1])
    mach = P.Machine(lay, lay.kv_image(st), lay.vm_image(st, pos))
    mach.tokens = list(prompt[:-1])
    got = mach.run(prog, prompt[-1], pos)
    ref = model.decode_token(prompt[-1], pos, copy.deepcopy(st))
    assert got == expected[0] == int(np.argmax(ref))
    assert np.array_equal(G.bits(mach.logits), G.bits(ref))


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    one = record["single_step"]
    assert one["next_token"] == one["golden_next_token"] == one["oracle_next_token"]
    assert one["logit_mismatches"] + one["vector_memory_mismatches"] + one["kv_cache_mismatches"] == 0
    e2e = record["end_to_end"]
    assert e2e["generated_tokens"] == e2e["isa_generated_tokens"] == e2e["golden_generated_tokens"]
    assert e2e["final_vector_memory_mismatches"] + e2e["final_kv_cache_mismatches"] == 0
    assert record["long_context"]["pass"]
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


@needs_checkpoint
def test_timing_model_tracks_the_rtl_within_half_a_percent():
    import hdc_program_v41 as P
    import hdc_timing_v41 as T
    prog = P.Builder(P.Layout(V.Model())).build()
    record = json.loads(campaign.OUT.read_text())
    rtl = record["single_step"]["cycles"]
    assert abs(T.simulate(prog, record["single_step"]["position"]) - rtl) / rtl < 0.005
    for step in record["end_to_end"]["per_step"]:
        assert abs(T.simulate(prog, step["position"]) - step["cycles"]) / step["cycles"] < 0.005
