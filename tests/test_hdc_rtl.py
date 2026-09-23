import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import rtl_hdc_decode_campaign as campaign  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced checkpoint: tools/build_qwen3_reduced_model.py")


def test_isa_package_is_generated_from_the_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "PKG", tmp_path / "pkg.sv")
    I.emit_package()
    assert (tmp_path / "pkg.sv").read_text() == (ROOT / "rtl/hdc/ot_hdc_isa_pkg.sv").read_text()


def test_encode_decode_round_trip():
    f = dict(unit=I.UNIT_SU, barrier=1, a_base=12345, imm1=0x3F800000, sfu=I.SFU_EXP)
    d = I.decode(I.encode(**f))
    assert all(d[k] == v for k, v in f.items())


@needs_checkpoint
def test_program_on_the_isa_model_is_bit_exact_with_the_golden():
    model, prompt, expected, cache = P.golden_state()
    lay = P.Layout(model)
    mach = P.Machine(lay, lay.kv_image(cache))
    got = mach.run(P.build_program(lay), prompt[-1], len(prompt) - 1)
    ref = model.decode_token(prompt[-1], len(prompt) - 1, [list(c) for c in cache])
    assert got == expected[0]
    assert np.array_equal(G.bits(mach.logits), G.bits(ref))


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    assert record["single_step"]["next_token"] == record["single_step"]["oracle_next_token"]
    assert record["end_to_end"]["generated_tokens"] == record["end_to_end"]["oracle_generated_tokens"]
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
