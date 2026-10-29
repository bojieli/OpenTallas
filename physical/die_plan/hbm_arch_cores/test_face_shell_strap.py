#!/usr/bin/env python3
"""Regression (HBM-CORES-KITS-10, OWNER 10-25 option B): declared ID straps (strap_* inputs) pass through the face shell
without a face register, and the kit SDC carries exactly the one allowed set_false_path -from [get_ports {strap_*}]."""
import importlib.util, re, sys
from pathlib import Path
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fs', H / 'face_shell.py')
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
widths = {'clk': 1, 'rst_n': 1, 'strap_qid': 2, 'qidx': 2, 'd': 8, 'q': 8}
dirs = {'clk': 'input', 'rst_n': 'input', 'strap_qid': 'input', 'qidx': 'input', 'd': 'input', 'q': 'output'}
st = fs.strap_inputs(widths, dirs)
assert st == ['strap_qid'], st
assert fs.strap_inputs({'strap_o': 1}, {'strap_o': 'output'}) == []        # an output is never a strap
passthru = {'clk', 'rst_n'} | set(st)
keep = {n: w for n, w in widths.items()}
sv = fs.emit_shell('shell', 'core', {}, widths, dirs, keep, passthru, 'clk', scalars={'clk', 'rst_n'})
assert not re.search(r'u_bin_strap_qid', sv), 'strap got a face register'
assert re.search(r'u_bin_qidx', sv) and re.search(r'u_bin_d\b', sv), 'data inputs lost their face register'
assert re.search(r'\.strap_qid\(strap_qid\)', sv), 'strap not passed straight to the core'
# SDC: the generator's sdc() emits the false_path and sdc_lint accepts it with the straps context
sys.path.insert(0, str(H.parents[2] / 'tools' / 'die_plan'))
sys.path.insert(0, str(H))
src = (H / 'gen_core_kit_hbm.py').read_text()
m = re.search(r'\n    if straps:\n(.*?)\n    return s \+', src, re.S)
assert m and "set_false_path -from [get_ports {{{' '.join(sorted(straps))}}}]" in m.group(1), 'gen sdc() lacks the strap false_path'
assert 'lint_ctx["straps"] = kit_straps' in src and '"straps.json"' in src, 'gen does not declare straps for sdc_lint / face_guard'
print('PASS face_shell strap passthrough + gen strap SDC/declaration')
