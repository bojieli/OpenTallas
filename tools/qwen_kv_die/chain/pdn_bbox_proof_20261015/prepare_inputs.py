#!/usr/bin/env python3
"""Prepare the exact mechanism fixture from C21sa elements.lef and its technology LEF.

Usage: prepare_inputs.py ELEMENTS_LEF TECH_LEF OUTPUT_DIR
Copy this proof directory and chain/pdn_bbox_obs.{py,tcl} into OUTPUT_DIR,
then run proof_driver.sh in the pinned ORFS image through admitted ot-run.
"""
from pathlib import Path
import re
import shutil
import sys

source, tech, output = map(Path, sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
text = source.read_text()
header = 'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'
for name, file in [('qfd_xs_tap', 'tap.lef'), ('qfd_tt_ctlm_static_s', 'master.lef')]:
    match = re.search(r'(?ms)^MACRO ' + name + r'\n.*?^END ' + name + r'\s*$', text)
    if not match:
        raise ValueError('missing actual fixture master ' + name)
    output.joinpath(file).write_text(header + match[0].rstrip() + '\nEND LIBRARY\n')
shutil.copyfile(tech, output / 'tech.lef')
output.joinpath('fixture.v').write_text('module fixture(); qfd_tt_ctlm_static_s ctl(); qfd_xs_tap tap(); endmodule\n')
script = output.joinpath('pdn_bbox_obs.py').read_text()
index = script.index("if __name__ == '__main__':")
for kind, pattern in [('pg', r'(PIN VDD\s+.*?RECT\s+)([-0-9.]+)'),
                      ('cover', r'(OBS\s+LAYER\s+\S+\s*;\s*RECT\s+)([-0-9.]+)')]:
    mutant = '''_good_aliases = aliases
def aliases(text, names):
    result = _good_aliases(text, names)
    def changed(match):
        return match[1] + str(Decimal(match[2]) + Decimal('0.001'))
    return re.sub(PATTERN, changed, result, count=1, flags=re.S)

'''.replace('PATTERN', repr(pattern))
    output.joinpath('pdn_bbox_obs_' + kind + '_mutant.py').write_text(script[:index] + mutant + script[index:])
