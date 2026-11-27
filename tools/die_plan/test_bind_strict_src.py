"""tests for tools/die_plan/bind_strict_src.py (BIND-STRICT-SRC 11-11): the strict-bind source-tree checks."""
import json
import sys

import pytest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_strict_src as S  # noqa: E402
from scoped_bind_inputs import materialize_clock_libraries  # noqa: E402

RING_OLD = "module ot_dp_clk_landing_cas #(parameter integer W = 8) (input logic clk, input logic [W-1:0] d, output logic [W-1:0] q);\nassign q = d;\nendmodule\n"
RING_NEW = ("module ot_dp_clk_landing_cas #(parameter integer W = 8, parameter integer QREG = 0) "
            "(input logic clk, input logic [W-1:0] d, output logic [W-1:0] q);\nassign q = d;\nendmodule\n")
TOP = ("module bound_top (input logic clk, input logic [7:0] d, output logic [7:0] q);\n"
       "  ot_dp_clk_landing_cas #(.W(8), .QREG(1)) u_r (.clk(clk), .d(d), .q(q));\nendmodule\n")
GROUP = ("module grp (input logic clk);\n  qfd_head_su_mem9 u_u_head0 (.clk(clk));\n"
         "  other_leaf #(.A(1)) u_u_exp0 (.clk(clk));\nendmodule\n")
MEM9 = "module qfd_head_su_mem9 (input logic clk);\nendmodule\n"
OTHER = "module other_leaf #(parameter A = 0) (input logic clk);\nendmodule\n"


def tree(tmp_path, ring):
    t = tmp_path / "tree"
    (t / "rtl").mkdir(parents=True, exist_ok=True)
    (out := tmp_path / "out" / "rtl").mkdir(parents=True, exist_ok=True)
    (t / "rtl/ring.sv").write_text(ring)
    (t / "rtl/other.sv").write_text(OTHER)
    (out / "top.sv").write_text(TOP)
    return t, out


def run(tmp_path, ring, extra_files=(), products=(), roots=None, lib=()):
    t, out = tree(tmp_path, ring)
    files = [str(t / "rtl/ring.sv"), str(t / "rtl/other.sv")] + [str(f) for f in extra_files] + [str(out / "top.sv")]
    roots = roots if roots is not None else [t.resolve(), out.parent.resolve()]
    return S.check(files, list(lib), [], [str(out / "top.sv")], list(products), roots)[0]


def test_green(tmp_path):
    assert run(tmp_path, RING_NEW) == []


def test_parse_header_and_body_parameters():
    d = S.definitions("module m #(parameter int A = 1, B = $clog2(4), parameter [3:0] C = 2) (input x);\n"
                      "parameter D = 5, E = 6;\nlocalparam F = 1;\nendmodule\nmodule n (input x);\nendmodule\n")
    assert d["m"] >= {"A", "B", "C", "D", "E"} and d["n"] == set()
    assert S.instances("m #(.A(1), .B(f(2))) u (.x(y));") == [("m", ["A", "B"], 1)]


def test_param_unknown_stale_ring_fails(tmp_path):
    errs = run(tmp_path, RING_OLD)           # stale ring without QREG, bound RTL overrides .QREG(1)
    assert len(errs) == 1 and errs[0].startswith("BIND_PARAM_UNKNOWN") and "QREG" in errs[0]


def test_outside_path_fails_and_opt_in_passes(tmp_path):
    ext = tmp_path / "elsewhere"
    ext.mkdir()
    (ext / "x.sv").write_text("module x_leaf (input a);\nendmodule\n")
    errs = run(tmp_path, RING_NEW, extra_files=[ext / "x.sv"])
    assert len(errs) == 1 and errs[0].startswith("BIND_SRC_OUTSIDE") and "x.sv" in errs[0]
    t = tmp_path / "tree"
    roots = [t.resolve(), (tmp_path / "out").resolve(), ext.resolve()]       # declared external root
    assert run(tmp_path, RING_NEW, extra_files=[ext / "x.sv"], roots=roots) == []
    assert run(tmp_path, RING_NEW, extra_files=[ext / "x.sv"], lib=[ext / "x.sv"]) == []   # as-built capture exempt


def test_missing_file_fails(tmp_path):
    errs = run(tmp_path, RING_NEW, extra_files=[tmp_path / "tree/rtl/gone.sv"])
    assert any(e.startswith("BIND_SRC_MISSING") for e in errs)


def test_group_master_unregistered_fails_and_registered_passes(tmp_path):
    t, out = tree(tmp_path, RING_NEW)
    g = out / "grp.sv"
    g.write_text(GROUP)
    errs = run(tmp_path, RING_NEW, products=[g])
    assert len(errs) == 1 and errs[0].startswith("BIND_GROUP_MASTER") and "qfd_head_su_mem9" in errs[0]
    (t / "rtl/mem9.sv").write_text(MEM9)
    assert run(tmp_path, RING_NEW, extra_files=[t / "rtl/mem9.sv"], products=[g]) == []


def test_allowed_roots_data_driven(tmp_path):
    r = S.allowed_roots(tmp_path / "repo", tmp_path / "o", tmp_path / "p/plan.json", tmp_path / "base",
                        {"external_roots": [str(tmp_path / "ext")]}, [str(tmp_path / "flag")])
    names = {x.name for x in r}
    assert names == {"repo", "o", "p", "base", "ext", "flag"}


CLOCK_LIBS = (
    'rtl/common/ot_meso_fifo.sv',
    'rtl/common/ot_dp_clk_landing.sv',
    'rtl/common/ot_dp_clk_landing_ca.sv',
)


def scoped_clock_carrier(tmp_path, aligned):
    carrier = tmp_path / 'carrier'
    authority = tmp_path / 'sealed'
    for root in (carrier, authority):
        (root / 'rtl/common').mkdir(parents=True)
    for i, rel in enumerate(CLOCK_LIBS):
        (authority / rel).write_text(f'module clock_leaf_{i}; endmodule\n')
        (carrier / rel).symlink_to(authority / rel)
    table = carrier / 'landing.json'
    table.write_text(json.dumps({'count_aligned': {'schema': 'land/1'} if aligned else {}}))
    manifest = carrier / 'asbuilt.json'
    manifest.write_text(json.dumps({'clock_landing_table': table.name}))
    return carrier, authority, manifest


@pytest.mark.parametrize('aligned', [False, True])
def test_clock_landing_extras_copied_before_ordinary_strict(tmp_path, aligned):
    carrier, authority, manifest = scoped_clock_carrier(tmp_path, aligned)
    expected = CLOCK_LIBS if aligned else CLOCK_LIBS[:2]
    files = [carrier / rel for rel in expected]
    roots = [carrier]
    control, _ = S.check(files, [], files, [], [], roots)
    assert len(control) == 1 and control[0].startswith(f'BIND_SRC_OUTSIDE {len(expected)}')
    assert materialize_clock_libraries(carrier, manifest, authority) == list(expected)
    assert materialize_clock_libraries(carrier, manifest, authority) == []
    for rel in expected:
        assert (carrier / rel).read_bytes() == (authority / rel).read_bytes()
        assert not (carrier / rel).is_symlink()
        assert (carrier / rel).stat().st_ino != (authority / rel).stat().st_ino
    if not aligned:
        assert (carrier / CLOCK_LIBS[2]).is_symlink()
    assert S.check(files, [], files, [], [], roots)[0] == []


def test_clock_extra_foreign_leaf_refuses_before_copying(tmp_path):
    carrier, authority, manifest = scoped_clock_carrier(tmp_path, True)
    wrong = tmp_path / 'other.sv'
    wrong.write_bytes((authority / CLOCK_LIBS[-1]).read_bytes())
    alias = carrier / CLOCK_LIBS[-1]
    alias.unlink()
    alias.symlink_to(wrong)
    with pytest.raises(ValueError, match='declared source file'):
        materialize_clock_libraries(carrier, manifest, authority)
    assert all((carrier / rel).is_symlink() for rel in CLOCK_LIBS)


def test_clock_extra_source_directory_alias_refuses(tmp_path):
    carrier, authority, manifest = scoped_clock_carrier(tmp_path, True)
    for rel in CLOCK_LIBS:
        (carrier / rel).unlink()
    d = carrier / 'rtl/common'
    d.rmdir()
    d.symlink_to(authority / 'rtl/common', target_is_directory=True)
    with pytest.raises(ValueError, match='leaf alias'):
        materialize_clock_libraries(carrier, manifest, authority)
    assert d.is_symlink()


def test_clock_landing_table_requires_private_containment(tmp_path):
    carrier, authority, manifest = scoped_clock_carrier(tmp_path, True)
    table = carrier / 'landing.json'
    borrowed = authority / table.name
    borrowed.write_bytes(table.read_bytes())
    table.unlink()
    table.symlink_to(borrowed)
    with pytest.raises(ValueError, match='inside the as-built base'):
        materialize_clock_libraries(carrier, manifest, authority)
    assert all((carrier / rel).is_symlink() for rel in CLOCK_LIBS)
