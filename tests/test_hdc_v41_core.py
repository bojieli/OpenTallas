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


def test_same_unit_hazards_and_sequential_units():
    import hdc_program_v41 as P
    su = dict(unit=I.UNIT_SU, su_nout=1, su_nin=8)
    prog = [(dict(su), {"A"}, {"B"}, "a"),
            (dict(su), {"C"}, {"B"}, "b"),                    # same-unit WAW: in order, no wait
            (dict(unit=I.UNIT_QE), {"D"}, {"E"}, "c"),
            (dict(unit=I.UNIT_QE), {"D"}, {"F"}, "d"),        # the QE runs one op at a time
            (dict(unit=I.UNIT_ME), {"E"}, {"G"}, "e")]        # c is complete once d issued: no wait
    out = P.schedule(prog)
    assert [f["wait"] for f in out] == [0, 0, 0, 0, 0]
    prog[3] = (dict(unit=I.UNIT_QE, pred=I.PRED_ODD), {"D"}, {"F"}, "d")   # d may be skipped: e waits
    assert P.schedule(prog)[4]["wait"] == 1 << (I.UNIT_QE - 1)


def test_stream_lane_axis():
    import hdc_program_v41 as P
    assert P.su_vec_mode(dict(su_nout=1, su_nin=1, sfu=I.SFU_RSQRT)) == I.VEC_SCALAR
    assert P.su_vec_mode(dict(su_nout=64, su_nin=16, red=I.RED_MAX)) == I.VEC_O     # a segment per lane
    assert P.su_vec_mode(dict(su_nout=1, su_nin=160, red=I.RED_SUM)) == I.VEC_SCALAR
    assert P.su_vec_mode(dict(su_nout=4, su_nin=160)) == I.VEC_I
    assert P.su_vec_mode(dict(su_nout=64, su_nin=4)) == I.VEC_O


def test_segmented_sum_is_the_golden_split_sum():
    import hdc_program_v41 as P
    rng = np.random.default_rng(1)
    x = rng.standard_normal(160).astype(np.float32)
    f = P.segmented(dict(su_nout=1, su_nin=160, a_si=1, red=I.RED_SUM, o_si=1), 8)
    assert f["su_nout"] == 8 and f["su_nin"] == 20 and f["a_so"] == 20 and f["red_tree"] == 1
    seg = V.split_sum_parts([G.reduce_sum(s) for s in x.reshape(8, 20)])
    assert G.bits(seg) == G.bits(V.split_sum(x, 8))
    assert G.bits(V.split_sum_parts([1.5, 2.25, 3.0])) == G.bits(np.float32((1.5 + 2.25) + (3.0 + 0.0)))


def test_chase_distance_follows_the_write_order():
    import hdc_program_v41 as P
    base = dict(unit=I.UNIT_SU, su_nout=1, su_nin=32, a_si=1, o_si=1, dst=I.DST_VM)
    prev = dict(base, a_base=0, o_base=100, su_vec=I.VEC_I)                  # writes 100.. in 4 vectors of 8
    same = dict(base, a_base=100, o_base=200, su_vec=I.VEC_I)                # reads them in the same order
    assert P.chase_distance(prev, same, lanes=8) == 4                         # vector v needs v: D = n1
    last = dict(base, su_nin=1, a_base=131, o_base=300, su_vec=I.VEC_SCALAR)  # reads the last element
    assert P.chase_distance(prev, last, lanes=8) == 1                         # prev must retire whole
    other = dict(base, a_base=500, o_base=600, su_vec=I.VEC_I)               # reads nothing prev writes
    assert P.chase_distance(prev, other, lanes=8) == 5


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
