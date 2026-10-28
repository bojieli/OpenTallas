"""Actual Yosys: parameter-disabled legacy cones are dead; live unknowns still fail."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
import rtl_lint


def test_actual_dead_cone_cleanup_keeps_live_undriven_failure(tmp_path):
    yosys = os.environ.get('YOSYS_TEST_BIN') or shutil.which('yosys')
    if not yosys:
        pytest.skip('actual Yosys binary required')
    source = tmp_path / 'demo.sv'
    source.write_text('module demo #(parameter PIPE=2)(input wire d, output wire q);\n'
                      'wire dead_selector, dead_word;\n'
                      'wire legacy = dead_selector ? dead_word : d;\n'
                      'assign q = PIPE ? d : legacy;\nendmodule\n')
    (tmp_path/'config.mk').write_text(f'export DESIGN_NAME = demo\nexport VERILOG_FILES = {source}\n')
    positive = rtl_lint.script(tmp_path, mount=str(tmp_path))
    script = tmp_path/'probe.ys'
    script.write_text(positive)
    r = subprocess.run([yosys, '-Q', '-T', '-s', str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout+r.stderr
    # The old pass order falsely rejected the same unused cone.
    script.write_text(positive.replace('opt_clean\n',''))
    old = subprocess.run([yosys, '-Q', '-T', '-s', str(script)], capture_output=True, text=True)
    assert old.returncode != 0
    # A live output depending on that undriven cone remains a hard error.
    source.write_text(source.read_text().replace('PIPE ? d : legacy', 'PIPE ? legacy : d'))
    script.write_text(positive)
    bad = subprocess.run([yosys, '-Q', '-T', '-s', str(script)], capture_output=True, text=True)
    assert bad.returncode != 0 and 'no driver' in bad.stdout+bad.stderr
