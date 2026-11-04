"""Actual Yosys: parameter-disabled legacy cones are dead; live unknowns still fail."""
import json
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


UNDRIVEN = ("Warning: Wire $paramod$60da\\ot_qwen_w12_matvec_part.\\x_addr [95] is used but has no driver.\n"
            "Warning: Wire $paramod$60da\\ot_qwen_w12_matvec_part.\\x_addr [94] is used but has no driver.\n")


def test_dead_undriven_only_needs_only_undriven_check_problems():
    """DIE-QC-61 11-01: the flattened re-check runs only when check -assert failed on undriven wires alone."""
    fail = "\nERROR: Found and reported 2 problems during 'check -assert'.\n"
    assert rtl_lint.dead_undriven_only("Warning: Replacing memory \\rk with list of registers.\n" + UNDRIVEN + fail)
    assert not rtl_lint.dead_undriven_only(UNDRIVEN)                       # no check failure
    assert not rtl_lint.dead_undriven_only(UNDRIVEN + "Warning: multiple conflicting drivers for top.\\w:\n" + fail)
    assert not rtl_lint.dead_undriven_only(UNDRIVEN + "ERROR: Module `\\nope' referenced in module `\\top' is not part "
                                           "of the design.\n")
    assert not rtl_lint.dead_undriven_only("Warning: found logic loop in module top:\n" + fail)


def test_actual_open_pruned_output_passes_flat_recheck_live_one_fails(tmp_path):
    """DIE-QC-61 11-01 (QC CB matvec_part x_addr): a child output bit never driven (pruned group) that the parent
    leaves open passes on the flattened live-design re-check; the same bit consumed by the parent still fails."""
    yosys = os.environ.get('YOSYS_TEST_BIN') or shutil.which('yosys')
    if not yosys:
        pytest.skip('actual Yosys binary required')
    source = tmp_path / 'demo.sv'
    child = ('module part(input wire clk, input wire [1:0] d, output reg [3:0] a);\n'
             'integer i; always @(posedge clk) for (i = 0; i < 2; i = i + 1) a[i*2 +: 1] <= d[i];\nendmodule\n')
    source.write_text(child + 'module demo(input wire clk, input wire [1:0] d, output wire q);\n'
                      'part u (.clk(clk), .d(d), .a());\nassign q = d[0];\nendmodule\n')
    (tmp_path/'config.mk').write_text(f'export DESIGN_NAME = demo\nexport VERILOG_FILES = {source}\n')
    assert rtl_lint.run(tmp_path, yosys) == 0
    rec = json.loads((tmp_path / 'rtl_lint.json').read_text())
    assert rec['verdict'] == 'PASS' and rec.get('flat_recheck_dead_undriven', 0) > 0
    source.write_text(child + 'module demo(input wire clk, input wire [1:0] d, output wire q);\n'
                      'wire [3:0] a; part u (.clk(clk), .d(d), .a(a));\nassign q = a[3];\nendmodule\n')
    assert rtl_lint.run(tmp_path, yosys) == 1
