"""clock.core_input_lockup latch_except / latch_except_hb4 pass plan schema validation (r553 / r560 keys)."""
import copy
import schema as S


def _errs(cil):
    import jsonschema
    sub = S.SCHEMA["properties"]["clock"]["properties"]["core_input_lockup"]
    return sorted(e.message for e in jsonschema.Draft202012Validator(sub).iter_errors(cil))


BASE = {"modules": {"qfd_tile_nk_a0c": ["n_a", "n_b", "tap", "rst_n"]}, "all": True, "pipe": 1, "pipe_except": ["rst_n"]}


def test_absent_keys_unchanged():
    assert _errs(BASE) == []


def test_bit_level_latch_except_and_hb4_accepted():
    c = copy.deepcopy(BASE)
    c["latch_except"] = {"qfd_tile_nk_a0c": ["tap[0]"]}
    c["latch_except_hb4"] = {"qfd_tile_nk_a0c": {"tap[0]": 3}}
    assert _errs(c) == []


def test_port_level_latch_except_accepted_by_schema():
    c = copy.deepcopy(BASE)
    c["latch_except"] = {"qfd_tile_nk_a0c": ["tap"]}
    assert _errs(c) == []


def test_hb4_needs_bit_form_and_small_count():
    c = copy.deepcopy(BASE)
    c["latch_except_hb4"] = {"qfd_tile_nk_a0c": {"tap": 3}}
    assert _errs(c)
    c["latch_except_hb4"] = {"qfd_tile_nk_a0c": {"tap[0]": 99}}
    assert _errs(c)
    c["latch_except"] = {"qfd_tile_nk_a0c": ["tap[x]"]}
    c["latch_except_hb4"] = {"qfd_tile_nk_a0c": {"tap[0]": 3}}
    assert _errs(c)
