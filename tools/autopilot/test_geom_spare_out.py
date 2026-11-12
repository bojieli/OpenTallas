"""KW-FIX-45 11-11 (DIE-HBM-100): kit spare_out.json bits (constant-tied spare outputs) are not unregistered pins."""
import json
import re
import geom_rules as G


def vehicle(tmp_path):
    p = tmp_path / "dump.tsv"
    p.write_text("D\t0\t0\t100\t100\n"
                 "C\t1\tB\tBUFx2_ASAP7_75t_R\t10\t10\t11\t11\tbuf\n"
                 "C\t2\tS\tDFF\t20\t20\t21\t21\tff\n"
                 "P\t0\ta\tINPUT\tSIGNAL\tM4\t0\t10\n"
                 "P\t1\tspare[0]\tOUTPUT\tSIGNAL\tM4\t100\t10\n"
                 "P\t2\tz\tOUTPUT\tSIGNAL\tM4\t100\t20\n"
                 "N\tSIGNAL\tp0\ti1\nN\tSIGNAL\ti1\tp1\nN\tSIGNAL\tp2\n")
    return G.Design(p)


def write(tmp_path, bits, schema="opentallas.kit_spare_out.v1"):
    f = tmp_path / "spare_out.json"
    f.write_text(json.dumps(dict(schema=schema, bits=bits)))
    return str(f)


def test_spare_output_is_not_unregistered(tmp_path):
    D = vehicle(tmp_path)
    sr = re.compile("^strap_")
    base = G.pin_reg_metrics(D, sr)
    bits, err = G.spare_out_bits(write(tmp_path, ["spare[0]"]))
    got = G.pin_reg_metrics(D, sr, frozenset(), None, bits)
    assert not err and bits == frozenset(["spare[0]"])
    assert got["pins_spare_out"] == 1
    assert got["pins_unregistered"] == base["pins_unregistered"] - 1
    assert "spare[0]" not in got["unregistered_sample"]


def test_other_unregistered_outputs_keep_failing(tmp_path):
    D = vehicle(tmp_path)
    bits, _ = G.spare_out_bits(write(tmp_path, ["spare[0]"]))
    got = G.pin_reg_metrics(D, re.compile("^strap_"), frozenset(), None, bits)
    assert "z" in got["unregistered_sample"] or got["pins_unregistered"] >= 1


def test_input_named_like_a_spare_bit_is_not_exempt(tmp_path):
    D = vehicle(tmp_path)
    bits, _ = G.spare_out_bits(write(tmp_path, ["a"]))
    assert G.pin_reg_metrics(D, re.compile("^strap_"), frozenset(), None, bits)["pins_spare_out"] == 0


def test_bad_or_missing_file_grants_no_exemption(tmp_path):
    assert G.spare_out_bits(None) == (frozenset(), [])
    bits, err = G.spare_out_bits(write(tmp_path, ["x"], schema="wrong"))
    assert bits == frozenset() and err
    bits, err = G.spare_out_bits(write(tmp_path, ["x", "x"]))
    assert bits == frozenset() and err
    bits, err = G.spare_out_bits(str(tmp_path / "missing.json"))
    assert bits == frozenset() and err


def test_default_metrics_unchanged_without_spare(tmp_path):
    D = vehicle(tmp_path)
    a = G.pin_reg_metrics(D, re.compile("^strap_"))
    b = G.pin_reg_metrics(D, re.compile("^strap_"), frozenset(), None, frozenset())
    a.pop("pins_spare_out"); b.pop("pins_spare_out")
    assert a == b
