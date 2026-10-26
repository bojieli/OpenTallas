"""Evaluate generated SDCs against real OpenSTA port objects, including a mutant."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys
import schema


def evaluate(tmp_path, text, declarations):
    if not shutil.which('docker'):
        pytest.skip('docker unavailable')
    tmp_path.mkdir()
    (tmp_path/'probe.v').write_text('module probe('+declarations+'); assign q=d; endmodule\n')
    (tmp_path/'probe.sdc').write_text(text)
    (tmp_path/'probe.tcl').write_text('''
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog /work/probe.v
link_design probe
read_sdc /work/probe.sdc
set names {}
foreach p $non_clk_in {lappend names [get_full_name $p]}
puts "NON_CLK [join [lsort $names] { }]"
write_sdc /work/evaluated.sdc
exit
''')
    cmd = (['docker'] if os.access('/var/run/docker.sock', os.W_OK) else ['sudo','docker'])
    p = subprocess.run(cmd+['run','--rm','-v',f'{tmp_path}:/work','openroad/orfs:latest',
        '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/work/probe.tcl'],
        text=True, capture_output=True)
    assert p.returncode == 0, p.stdout+p.stderr
    assert '[ERROR' not in p.stdout+p.stderr, p.stdout+p.stderr
    line = next(x for x in p.stdout.splitlines() if x.startswith('NON_CLK '))
    return set(line.split()[1:]), (tmp_path/'evaluated.sdc').read_text()


def test_partition_clock_objects_excluded_and_old_mutant_caught(tmp_path):
    p = schema.Plan(json.loads((HERE/'examples/tiny_plan.json').read_text()))
    clocks = [n for n,x,y in gen_phys.clock_pins(p,'src')]
    text = gen_phys.sdc(p,'src',gen_phys.type_pins(p,'src'))
    decl = ','.join('input '+n for n in clocks)+',input d,input arst_n,output q'
    names, serialized = evaluate(tmp_path/'good',text,decl)
    assert names == {'d','arst_n'}
    # The former name regex sees opaque Port objects, so every clock is treated as data.
    old = text.replace('[all_inputs -no_clocks]',
        '[lsearch -inline -all -not -regexp [all_inputs] {^(clk.*)$}]')
    bad, _ = evaluate(tmp_path/'old_mutant',old,decl)
    assert set(clocks) <= bad


def test_kv_core_vector_clock_objects_excluded(tmp_path):
    f = HERE.parents[1]/'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py'
    spec = importlib.util.spec_from_file_location('kv_core_sdc',f)
    m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    text = m.sdc(833,250,40,['ck','hck[0]','hck[1]'],[],'probe')
    names, serialized = evaluate(tmp_path/'kv',text,'input ck,input [1:0] hck,input d,output q')
    assert names == {'d'}
