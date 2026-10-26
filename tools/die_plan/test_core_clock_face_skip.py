"""Regression for data flops falsely anchored through a vector core clock port."""
import pathlib
import re
import subprocess


def test_vector_clock_and_reset_ports_are_not_data_faces():
    root = pathlib.Path(__file__).resolve().parents[2]
    text = (root / 'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py').read_text()
    expr = next(line.strip().split(' = ', 1)[1] for line in text.splitlines() if line.strip().startswith('skip = '))
    rx = eval(expr, {'re': re, 'clks': ['ck', 'g_t_2_u_l8__clk'], 'rsts': ['rst_n']})
    checks = [('ck',1),('ck[0]',1),('ck[2]',1),('g_t_2_u_l8__clk[0]',1),('rst_n',1),('rst_n[0]',1),('ck_status[0]',0),('xck[0]',0),('ck_a',0)]
    script = 'set rx {' + rx + '}\n'
    for name, expected in checks:
        script += 'if {[regexp $rx {' + name + '}] != ' + str(expected) + '} {error {bad ' + name + '}}\n'
    script += 'puts PASS\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert result.returncode == 0 and result.stdout.strip() == 'PASS' and not result.stderr, result
