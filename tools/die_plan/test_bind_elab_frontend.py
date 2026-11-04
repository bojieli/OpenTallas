"""bind_elab frontends: default native script unchanged; opt-in slang and typed-string staging."""
import hashlib
import os
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


def _stage_names(root, pins=None):
    base, out = root / 'wt', root / 'bind'
    (base / 'rtl').mkdir(parents=True)
    out.mkdir()
    f = base / 'rtl' / 'a.sv'
    f.write_text('module die; endmodule\nmodule leaf(input a); wire x; endmodule\n')
    g = out / 'stub.sv'
    g.write_text('module stub; parameter string S = "x"; endmodule\n')
    key = E.stage_keyer(base, out, pins)
    names = [Path(n).name for n in E.structural_sources([str(f)], {'die'}, out / 'st', key=key)]
    names += [Path(n).name for n in E.string_parameter_compat([str(g)], out / 'c', key=key)[0]]
    return names, key


def test_stage_names_do_not_depend_on_worktree_or_out_location(tmp_path):
    """CAPEND 11-04: the staged name feeds the $src_ digest and through it the collector bit order."""
    a, _ = _stage_names(tmp_path / 'one')
    b, _ = _stage_names(tmp_path / 'other' / 'deeper')
    assert a == b


def test_stage_hash_roots_reproduce_the_published_bind_digest(tmp_path):
    pins = {'base': '/published/wt', 'out': '/published/bind'}
    a, _ = _stage_names(tmp_path / 'one', pins)
    b, _ = _stage_names(tmp_path / 'two', pins)
    assert a == b
    assert a[0] == hashlib.sha256(b'/published/wt/rtl/a.sv').hexdigest()[:12] + '_a.sv'
    assert a[1] == hashlib.sha256(b'/published/bind/stub.sv').hexdigest()[:12] + '_stub.sv'


def test_stage_key_outside_roots_keeps_path_and_is_recorded(tmp_path):
    key = E.stage_keyer(tmp_path / 'wt', tmp_path / 'bind')
    assert key(Path('/elsewhere/x.sv')) == '/elsewhere/x.sv' and key.outside == {'/elsewhere/x.sv'}


def test_stage_hash_roots_rejects_unknown_root(tmp_path):
    with pytest.raises(E.ElabError):
        E.stage_keyer(tmp_path, tmp_path, {'bse': '/x'})


def test_stage_src_key_include_span_independent_of_location(tmp_path):
    """16 S81 svc types: an `included .svh reaches src as a path relative to the elab out dir."""
    keys = []
    for root in (tmp_path / 'a', tmp_path / 'b' / 'deep' / 'er'):
        base, out = root / 'wt', root / 'x' / 'bind'
        keys.append(E.stage_src_key(base, out)(os.path.relpath(base / 'rtl/r.svh', out) + ':3.1-3.9'))
    assert keys[0] == keys[1] == 'base:rtl/r.svh:3.1-3.9'


def test_stage_src_key_pins_reproduce_published_text_and_keep_staged_spans(tmp_path):
    base, out = tmp_path / 'wt', tmp_path / 'p' / 'bind'
    key = E.stage_src_key(base, out, {'base': '/c/wt/h10', 'out': '/c/kit/s81/bind_h10'})
    assert key('../../wt/rtl/r.svh:3.1-3.9') == '../../../wt/h10/rtl/r.svh:3.1-3.9'
    assert key('structural_full/ab_x.sv:6.8') == 'structural_full/ab_x.sv:6.8'
    assert key('structural_full/ab_x.sv:6.8|../../wt/r.svh:1.1') == 'structural_full/ab_x.sv:6.8|../../../wt/h10/r.svh:1.1'
    assert key(None) is None

