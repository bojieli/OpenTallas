"""Canonical reset-cell preservation; unused planned tap chains survive synthesis."""
import re
import shutil
import subprocess
from pathlib import Path
import pytest
import bind
import gen_rtl


def test_canonical_control_keep_attributes_are_copied_verbatim():
    cells=bind.wavefront_cells_text()
    for name in ('ot_dp_rrelay','ot_dp_rgate'):
        full=re.search(r'(\(\*[^\n]*\*\)\nmodule '+name+r'\b.*?\nendmodule\n)',gen_rtl.CELLS,re.S).group(1)
        assert 'keep_hierarchy, keep' in full
        assert full in cells


def test_unused_planned_control_chains_survive(tmp_path):
    exe=shutil.which('yosys')
    if not exe:pytest.skip('yosys required')
    top='''module top(input clk,d,output q);
 ot_dp_rrelay used(clk,d,q);
 ot_dp_rrelay planned_dead(clk,d,unused);
 ot_dp_rgate planned_gate(clk,d,d,unused_gate);
endmodule
'''
    cells=bind.wavefront_cells_text()
    # Removing the canonical module keep is the historical binder mutation.
    counts=[]
    for name,defs in [('mutant',cells.replace('keep_hierarchy, keep','keep_hierarchy')),('fixed',cells)]:
        src=tmp_path/(name+'.sv');out=tmp_path/(name+'.json');src.write_text(defs+top)
        p=subprocess.run([exe,'-Q','-q','-p',f'read_verilog -sv {src}; hierarchy -top top; synth -top top; write_json {out}'],capture_output=True,text=True)
        assert p.returncode==0,p.stdout+p.stderr
        import json
        c=json.loads(out.read_text())['modules']['top']['cells']
        counts.append(sum(v['type'].startswith('ot_dp_r') for v in c.values()))
    assert counts==[1,3]
