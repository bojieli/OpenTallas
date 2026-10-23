#!/usr/bin/env python3
"""ELEM-XFV/XFIN: synth (ORFS yosys, config = Codex native r1 config, already SRAM-extended) + native census, fresh dir."""
import pathlib,subprocess,json,re,hashlib,sys
r=pathlib.Path.cwd();w=r/'native';s=r/'src';p=w/'config.mk'
macro='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1'
c=p.read_text()
if 'ADDITIONAL_LEFS' not in c: p.write_text(c+'export ADDITIONAL_LEFS = /src/'+macro+'.lef\n')
c=p.read_text()
if 'ot_s81dv_fp_n32.sv' not in c:
    c=c.replace('/src/rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv','/src/rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv /src/rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv',1)
    p.write_text(c)
files=re.search(r'export VERILOG_FILES = (.*)',p.read_text())[1].split()
man={'sources':{x:hashlib.sha256((s/x.removeprefix('/src/')).read_bytes()).hexdigest() for x in files},'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(r/'source_manifest.json').write_text(json.dumps(man,indent=2)+'\n')
cmd=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth']
with (w/'synth.log').open('w') as f: rc0=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
nl=w/'results/asap7/opentallas_ot_s81dv_xfin_asap7_ref_gate/base/1_2_yosys.v'
print('SYNTH_RC',rc0,'NETLIST',nl.exists(),flush=True)
n=len(re.findall(r'\n  ot_sram_1r1w_32x64_m1\s+',nl.read_text()));print('ACTUAL_SRAM_INSTANCES',n,flush=True)
b=json.load(open(r/'baseline_native.json'))
cmd=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work','openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist','/work/results/asap7/opentallas_ot_s81dv_xfin_asap7_ref_gate/base/1_2_yosys.v','--top','ot_s81dv_xfin','--out','/work/native_census.json']
for x in b['liberty']:cmd+=['--liberty',x['path']]
for corner in ['tt','ff']:cmd+=['--liberty','/src/'+macro+'_'+corner+'.lib']
subprocess.run(cmd)
st=json.load(open(w/'native_census.json'));print('ACTUAL_NATIVE',st['status'],st['max_dynamic_loads'],len(st['violations']),len(st['role_errors']) if isinstance(st['role_errors'],list) else st['role_errors'],flush=True)
area=re.search(r"Chip area for top module '\\\\ot_s81dv_xfin': ([\d.]+)",(w/'reports/asap7/opentallas_ot_s81dv_xfin_asap7_ref_gate/base/synth_stat.txt').read_text())
print('CHIP_AREA',area and area[1],flush=True)
