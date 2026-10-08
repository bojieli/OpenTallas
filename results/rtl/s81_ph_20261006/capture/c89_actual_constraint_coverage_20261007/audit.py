"""Verify actual written routed SDC serial/core output coverage, not closure."""
import re
from pathlib import Path
text = (Path(__file__).parent / '6_final.sdc').read_text()
pat = r'set_output_delay ([\d.-]+) -clock \[get_clocks \{([^}]+)\}\] -(min|max) -add_delay \[get_ports \{([^}]+)\}\]'
rows = re.findall(pat, text)
expected = {f't_vm[{i}]' for i in range(1664)} | {f't_st[{i}]' for i in range(64)}
assert {p for _, c, _, p in rows if c == 'vclk_s'} == expected
for port in expected:
    found = [(float(v), c, k) for v, c, k, p in rows if p == port]
    assert sorted(found) == [(120.0, 'vclk_s', 'min'), (372.2221, 'vclk_s', 'max')], port
assert sorted((float(v), c, k) for v, c, k, p in rows if p == 't_ho[0]') == [(107.0, 'vclk', 'min'), (316.6666, 'vclk', 'max')]
print('ACTUAL_SDC_COVERAGE_PASS serial=1728 core=1 min_and_max=present')
