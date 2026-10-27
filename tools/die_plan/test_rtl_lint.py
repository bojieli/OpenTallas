from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rtl_lint
import gen_phys


def test_lint_reads_strict_frontend_and_one_macro_view(tmp_path):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\nexport VERILOG_DEFINES = -DLANES=4\nexport VERILOG_INCLUDE_DIRS = /work/inc\n')
    (tmp_path / 'macros').mkdir()
    for corner in ('tt', 'ff'):
        (tmp_path / 'macros' / f'memory_{corner}.lib').touch()
    text = rtl_lint.script(tmp_path)
    assert text.count('read_liberty ') == 1 and 'memory_tt.lib' in text
    assert '-DLANES=4' in text
    assert 'read_verilog -defer -sv -noautowire -I/work/inc /work/demo.sv' in text and 'hierarchy -check -top demo' in text
    assert 'check -assert' in text
    assert gen_phys.RUN_KIT.index('/work/rtl_lint.py') < gen_phys.RUN_KIT.index('\\$M synth')


def test_lint_fails_closed_on_missing_tools_or_config(tmp_path):
    assert rtl_lint.run(tmp_path, 'not-a-yosys') == 1
    assert 'NOT RUN' in (tmp_path / 'rtl_lint.json').read_text()


def test_lint_records_file_prefixed_yosys_errors(tmp_path):
    """yosys prints frontend errors as '<file>:<line>: ERROR: ...'; the record must carry them (was errors [])."""
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\n')
    msg = tmp_path / 'msg.txt'
    msg.write_text("/work/demo.sv:16: ERROR: Can't resolve task name `$fatal'.\n")
    fake = tmp_path / 'fake_yosys'
    fake.write_text(f'#!/bin/sh\ncat {msg}\nexit 1\n')
    fake.chmod(0o755)
    assert rtl_lint.run(tmp_path, str(fake)) == 1
    import json
    rec = json.loads((tmp_path / 'rtl_lint.json').read_text())
    assert rec['verdict'] == 'FAIL' and len(rec['errors']) == 1 and 'demo.sv:16: ERROR' in rec['errors'][0], rec


def test_lint_uses_production_top_parameter_specialization(tmp_path):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\nexport VERILOG_TOP_PARAMS = AQ_XMEM 2 WIDTH 16\n')
    text = rtl_lint.script(tmp_path)
    assert 'chparam -set AQ_XMEM 2 -set WIDTH 16 demo' in text
    assert 'hierarchy -check -top demo\n' in text and ' -chparam ' not in text

def test_lint_fails_closed_on_malformed_top_parameters(tmp_path):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\nexport VERILOG_TOP_PARAMS = AQ_XMEM\n')
    assert rtl_lint.run(tmp_path) == 1
    assert 'name/value pairs' in (tmp_path / 'rtl_lint.json').read_text()


def test_empty_config_values_do_not_consume_following_assignments(tmp_path):
    (tmp_path / 'config.mk').write_text(
        'export DESIGN_NAME = demo\n'
        'export VERILOG_FILES = /work/demo.sv\n'
        'export VERILOG_TOP_PARAMS =\n'
        'export VERILOG_DEFINES = -DREAL=1\n'
        'export VERILOG_INCLUDE_DIRS =\n'
        'override export SYNTH_INCLUDE_DIRS := /work/inc\n')
    cfg = rtl_lint.config(tmp_path)
    assert cfg['VERILOG_TOP_PARAMS'] == []
    assert cfg['VERILOG_INCLUDE_DIRS'] == []
    assert cfg['SYNTH_INCLUDE_DIRS'] == ['/work/inc']
    text = rtl_lint.script(tmp_path)
    assert 'chparam' not in text
    assert '-DREAL=1' in text
    assert 'read_verilog -defer -sv -noautowire -I/work/inc /work/demo.sv' in text


def _mapped_kit(tmp_path, cell='TIEHIx1_ASAP7_75t_R'):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.v\n')
    (tmp_path / 'demo.v').write_text('module demo(y);\n  output y;\n  wire y;\n'
                                     f'  {cell} \\u_a.g[1]._3_  (\n    .H(y)\n  );\nendmodule\n')
    lib = tmp_path / 'libs'
    lib.mkdir(exist_ok=True)
    import gzip
    with gzip.open(lib / 'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz', 'wt') as f:
        f.write('library (x) {\n cell (TIEHIx1_ASAP7_75t_R) {\n pin (H) { direction : output; }\n }\n}\n')
    (lib / 'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib').write_text('library (y) {\n cell ("DFFHQNx1_ASAP7_75t_R") { }\n}\n')
    return str(lib / 'asap7sc7p5t_*_RVT_TT_nldm_*.lib*')


def test_mapped_netlist_loads_every_rvt_tt_liberty(tmp_path, monkeypatch):
    pattern = _mapped_kit(tmp_path)
    monkeypatch.setattr(rtl_lint, 'PLATFORM_LIB_GLOB', pattern)
    assert rtl_lint.mapped_cells([tmp_path / 'demo.v']) == {'TIEHIx1_ASAP7_75t_R': 1}
    text = rtl_lint.script(tmp_path)
    for name in ('asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz', 'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib'):
        assert text.count(name) == 1, text
    assert 'hierarchy -check -top demo' in text
    assert rtl_lint.mapped_cell_errors(tmp_path, pattern) == []


def test_mapped_netlist_unknown_cell_fails_closed(tmp_path, monkeypatch):
    pattern = _mapped_kit(tmp_path, 'TIEHIx1_ASAP7_75t_L')
    monkeypatch.setattr(rtl_lint, 'PLATFORM_LIB_GLOB', pattern)
    err = rtl_lint.mapped_cell_errors(tmp_path, pattern)
    assert len(err) == 1 and 'TIEHIx1_ASAP7_75t_L' in err[0]
    fake = tmp_path / 'fake_yosys'
    fake.write_text('#!/bin/sh\nexit 0\n')            # even a passing yosys cannot pass an unknown cell
    fake.chmod(0o755)
    assert rtl_lint.run(tmp_path, str(fake)) == 1
    import json
    rec = json.loads((tmp_path / 'rtl_lint.json').read_text())
    assert rec['verdict'] == 'FAIL' and any('TIEHIx1_ASAP7_75t_L' in e for e in rec['errors']), rec


def test_mapped_netlist_without_liberty_fails_closed(tmp_path):
    _mapped_kit(tmp_path)
    err = rtl_lint.mapped_cell_errors(tmp_path, str(tmp_path / 'nolib' / '*.lib'))
    assert len(err) == 1 and 'no ASAP7 RVT TT liberty' in err[0]


def test_rtl_source_does_not_load_platform_liberties(tmp_path, monkeypatch):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\n')
    (tmp_path / 'demo.sv').write_text('module demo(input a, output y); assign y = a; endmodule\n')
    monkeypatch.setattr(rtl_lint, 'PLATFORM_LIB_GLOB', str(tmp_path / 'x' / '*.lib'))
    assert rtl_lint.mapped_cells([tmp_path / 'demo.sv']) == {}
    assert rtl_lint.mapped_cell_errors(tmp_path) == []
