#!/usr/bin/env python3
"""Map the concrete CTL glue successor and run the unchanged native census."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
libs = sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT*.lib'))
assert len(libs) == 5, libs
seq = next(p for p in libs if '_SEQ_' in p.name)
macro = Path('physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2')
sources = [Path(p) for p in [
    'rtl/lib/ot_rst_relay_tree3.sv',
    'rtl/dsrom_sys/s81_head/ot_s81hd_util.sv',
    'rtl/dsrom_sys/s81_head/ot_s81hd_ctl.sv',
    'rtl/dsrom_sys/s81_head/ot_s81hd_ctl_peer_r2o.sv',
    'rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv',
    'rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv',
    'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv']]
sources.append(macro/(macro.name+'_bb.v'))
top = 'ot_s81hd_ctl_glue_r2o'
script = ['read_verilog -sv '+str(root/p) for p in sources]
script += ['hierarchy -check -top '+top,
           'tcl '+str(root/'physical/common_flow/ot_keep_regs.tcl'),
           'synth -top '+top+' -flatten',
           'dfflibmap -liberty '+str(seq),
           'abc '+' '.join('-liberty '+str(p) for p in libs)+' -D 833.333',
           'splitnets -ports', 'opt_clean -purge',
           'write_verilog -noattr '+str(out/'mapped.v'),
           'tee -o '+str(out/'stat.txt')+' stat '+' '.join('-liberty '+str(p) for p in libs)]
(out/'synth.ys').write_text('\n'.join(script)+'\n')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
evidence = sources+[Path('physical/common_flow/ot_keep_regs.tcl'),Path('tools/ref_tile/native_census.py'),Path('tools/textbook_lint.py')]
(out/'inputs.json').write_text(json.dumps(dict(top=top,sources={str(p):sha(root/p) for p in evidence},libs={str(p):sha(p) for p in libs}),indent=2)+'\n')
with (out/'synth.log').open('w') as log:
    subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(out/'synth.ys')],stdout=log,stderr=subprocess.STDOUT,check=True)
cmd = [sys.executable,'tools/ref_tile/native_census.py','--netlist',str(out/'mapped.v'),'--top',top,'--out',str(out/'native_census.json')]
for p in libs+[root/macro/(macro.name+'_tt.lib')]:
    cmd += ['--liberty',str(p)]
subprocess.run(cmd,check=True)
print('CTL_OUTPUT_NATIVE_CENSUS_PASS',flush=True)
