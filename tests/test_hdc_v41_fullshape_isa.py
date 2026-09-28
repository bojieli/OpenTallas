"""The full-shape V4.1 program must encode its real context and router ranges."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import hdc_isa_v41 as isa
import hdc_replay_v41 as replay


def test_full_shape_instruction_fields_round_trip_without_truncation():
    layout = isa.layout_for(full_shape=True)
    assert layout["xu_k"][1] >= 12
    assert layout["su_nin"][1] >= 21
    assert layout["a_base"][1] >= 30
    fields = {"xu_k": 2048, "su_nin": 1_048_576, "a_base": (1 << 29) + 17,
              "qe_obase": (1 << 25) + 3, "me_obase": (1 << 25) + 5}
    word = isa.encode(full_shape=True, **fields)
    decoded = isa.decode(word, full_shape=True)
    assert {name: decoded[name] for name in fields} == fields


def test_reduced_instruction_layout_remains_the_default():
    assert isa.layout_for() == isa.LAYOUT
    assert isa.LAYOUT["xu_k"][1] == 5
    assert isa.LAYOUT["a_base"][1] == 24
    assert isa.LAYOUT["su_nin"][1] == 16


def test_shipped_shape_program_encodes_at_1m():
    """The shape emitter's symbolic DYN slots must have actual ISA codes."""
    prog = replay.build(replay.SHIPPED)
    assert len(prog) == 3842
    words = [isa.encode(full_shape=True, **fields) for fields in prog]
    assert len(words) == len(prog)
    symbolic = next((word, fields) for word, fields in zip(words, prog)
                    if fields.get("me_d_nout") == "T0")
    assert isa.decode(symbolic[0], full_shape=True)["me_d_nout"] == isa.FULL_DYN["T0"]
    assert len(isa.DYN_NAMES) + len(isa.FULL_DYN_KEYS) <= 1 << isa.FULL_D


def test_full_shape_dynamic_values_fit_address_space_at_both_contexts():
    for position in (199_999, 1_048_575):
        values = replay.dyn_values(replay.SHIPPED, position)
        assert values["NC1"] == position + 1
        assert values["SC1"] == (position + 4) // 4
        assert max(values.values()) < 1 << isa.FULL_A
