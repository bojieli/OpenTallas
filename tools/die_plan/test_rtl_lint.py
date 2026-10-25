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
