"""DIE-KV-64 11-03: budgets.id_straps_in_type_types ties plan-declared hard-core ID straps inside the type (no leaked
strap_* type ports) when every die instance carries the plan value; anything else is a bind gap (fail closed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_strap_alias import SU, A, W, _bind_vehicle  # noqa: E402
from bind import short_id  # noqa: E402

NM = short_id(f"S_u_su__{A}", 80)


def _tie(b, names=("src",)):
    b.plan.setdefault("budgets", {})["id_straps_in_type_types"] = list(names)


def test_tied_inside_type_has_no_strap_port(tmp_path):
    raw, b = _bind_vehicle(SU)
    _tie(b)
    b.emit(tmp_path)
    assert not any("u_su" in g for g in getattr(b, "emit_gaps", []))
    assert b.parent_id_ports["src"] == {}
    rtl = (tmp_path / "rtl" / (raw["partition_types"]["src"]["module"] + ".sv")).read_text()
    assert f"parameter [{W - 1}:0] {NM} = {W}'b{16:0{W}b}" in rtl
    assert f"input wire [{W - 1}:0] strap_" not in rtl
    top = next((tmp_path / "rtl").glob("*_bound_top.sv")).read_text()
    assert f".{NM}({W}'b{16:0{W}b})" in top          # override = the same plan value
    assert not any(v for v in b.parent_id_values.values())


def test_other_types_keep_parent_tied_ports(tmp_path):
    raw, b = _bind_vehicle(SU)
    _tie(b, ("other_type",))
    b.emit(tmp_path)
    (nm, d), = b.parent_id_ports["src"].items()
    assert nm.startswith("strap_") and d["port"] == A


def test_non_uniform_instances_are_a_gap(tmp_path):
    raw, b = _bind_vehicle(SU)
    _tie(b)
    k = ("strap", "u_su", A, 0)
    b.tparams["src"][k] = ["0", "1"]                         # two instances disagree on bit 0
    b.emit(tmp_path)
    assert any("one value on every instance" in g for g in b.emit_gaps)


def test_declared_value_mismatch_stays_a_gap(tmp_path):
    raw, b = _bind_vehicle(SU, value=17)
    part = next(iter(b.tvals["src"]))
    b.tparams["src"] = {("strap", "u_su", A, i): [str((16 >> i) & 1)] for i in range(W)}
    b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    _tie(b)
    b.emit(tmp_path)
    assert any("u_su" in g for g in b.emit_gaps)
