"""bind_elab frontends: default native script unchanged; opt-in slang and typed-string staging."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import bind_elab as E


def _src(tmp_path):
    f = tmp_path / 'die.sv'
    f.write_text('module die(input wire a, output wire y);\n  wrap u_w(.a(a), .y(y));\nendmodule\n'
                 'module wrap(input wire a, output wire y);\n  core u_c(.a(a), .y(y));\nendmodule\n'
                 'module core #(parameter string LABEL = "x")(input wire a, output wire y);\n'
                 '  assign y = ~a;\nendmodule\n')
    return f


def test_native_default_reads_each_file(tmp_path):
    f = _src(tmp_path)
    s = E.yosys_script(dict(top='die'), [str(f)], [], [], tmp_path / 'o.json')
    assert f'read_verilog -sv -overwrite' in s and 'read_slang' not in s


def test_unknown_frontend_rejected(tmp_path):
    f = _src(tmp_path)
    with pytest.raises(E.ElabError, match='unknown asbuilt.frontend'):
        E.yosys_script(dict(top='die', frontend='bogus'), [str(f)], [], [], tmp_path / 'o.json')


def test_slang_blackboxes_non_structural_modules_and_restores_hdlname(tmp_path):
    f = _src(tmp_path)
    s = E.yosys_script(dict(top='die', frontend='slang', dissolve=['wrap']), [str(f)], [], [], tmp_path / 'o.json')
    assert 'read_slang' in s and 'read_verilog' not in s
    assert '--blackboxed-module core' in s
    assert '--blackboxed-module wrap' not in s and '--blackboxed-module die' not in s
    assert 'setattr -mod -set hdlname "wrap" =wrap =wrap$*' in s


def test_structural_sources_stub_private_bodies_keep_wrappers(tmp_path):
    f = _src(tmp_path)
    original = f.read_text()
    staged, = E.structural_sources([str(f)], {'die', 'wrap'}, tmp_path / 'st')
    text = Path(staged).read_text()
    assert f.read_text() == original
    assert 'core u_c' in text and 'wrap u_w' in text
    assert 'assign y = ~a' not in text and 'module core' in text


def test_string_parameter_staging_preserves_defaults_and_original(tmp_path):
    f = tmp_path / 'src.sv'
    original = 'module foo #(parameter string LABEL="abc", parameter N=7)();\nlocalparam string X="001";\nendmodule\n'
    f.write_text(original)
    files, rec = E.string_parameter_compat([str(f)], tmp_path / 'stage')
    assert f.read_text() == original
    text = Path(files[0]).read_text()
    assert 'parameter LABEL="abc"' in text and 'localparam X="001"' in text
    assert len(rec) == 1 and rec[0]['original'] == str(f)
    unchanged = tmp_path / 'plain.sv'
    unchanged.write_text('module bar; endmodule\n')
    assert E.string_parameter_compat([str(unchanged)], tmp_path / 'stage') == ([str(unchanged)], [])
