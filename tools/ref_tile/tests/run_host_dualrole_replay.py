#!/usr/bin/env python3
"""Fleet-only actual mapped-STA regression; no placement, route, or closure claim.

Consumes an immutable failed-gate snapshot and a candidate generated SDC. Every
negative changes a real mapped clock/producer connection or an explicit reviewed
master/port binding; frozen gate inputs are mounted read-only.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--gate',type=Path,required=True);p.add_argument('--sdc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
gate=a.gate.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
old=gate/'routes/gate/work/orfs';rel='asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base'
net=old/'results'/rel/'1_2_yosys.v';log=old/'logs'/rel/'1_synth.log'
liblines=[x for x in log.read_text().splitlines() if x.startswith('read_liberty ')]
base=net.read_text();sdc=a.sdc.read_text();(out/'exact.v').write_text(base);(out/'exact.sdc').write_text(sdc)
master='ot_sram_1r1w2c_32x546_m1_p192_mir'
inst='u_ot_pr_core.u_rank__u_phy__u_rx.g_afw.u_af.g_mm.g_pad32.u_m'
pattern=re.escape(master)+r'\s+\\?'+re.escape(inst)+r'\s*\(.*?\n\s*\);'
m=re.search(pattern,base,re.S);assert m,'exact actual macro instance not found';block=m.group()
assert len(re.findall(r'\.wclk\(ck_phy_fam\)',block))==1
wrong_clock=block.replace('.wclk(ck_phy_fam)','.wclk(ck_core)')
wrong_producer,n=re.subn(r'\.w_ce_in\([^)]*\)',r'.w_ce_in(u_rank__raw_rx_cr)',block);assert n==1
for name,changed in [('wrong_clock',wrong_clock),('wrong_producer',wrong_producer)]:
 (out/(name+'.v')).write_text(base[:m.start()]+changed+base[m.end():]);(out/(name+'.sdc')).write_text(sdc)
needle='master {'+master+'}';assert needle in sdc
(out/'wrong_master.v').write_text(base);(out/'wrong_master.sdc').write_text(sdc.replace(needle,'master {UNREVIEWED_MASTER}',1))
# The source/Liberty parser refuses this earlier; also check actual pin lookup fails closed.
needle='{w_ce_in} {wclk}';assert needle in sdc
(out/'missing_port_role.v').write_text(base);(out/'missing_port_role.sdc').write_text(sdc.replace(needle,'{UNREVIEWED_INPUT} {wclk}',1))
readlef=['read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef','read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef']
for n in ('ot_sram_1r1w_32x546_m1_p192_mir',master):readlef.append(f'read_lef /src/physical/asap7_memory_macros/{n}/{n}.lef')
expected={'exact':'PASS ACTUAL_MAPPED_DUAL_ROLE_OWNERSHIP','wrong_clock':'differs from its exact reviewed root','wrong_producer':'wrong domain','wrong_master':'master differs','missing_port_role':'unreviewed actual dual SRAM input pin'}
results={};image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
for name,witness in expected.items():
 script='\n'.join(liblines+readlef)+f'\nread_verilog /work/{name}.v\nlink_design qkd_hr_cdc_pc_sram\nset ::env(OT_HOLD_MM) 1\n'
 script+=f'if {{[catch {{read_sdc /work/{name}.sdc}} err]}} {{error "ACTUAL_ROLE_REFUSAL $err"}}\n'
 script+='puts "PASS ACTUAL_MAPPED_DUAL_ROLE_OWNERSHIP"\nexit\n';(out/(name+'.tcl')).write_text(script)
 cmd=['docker','run','--rm','-v',str(gate/'src')+':/src:ro','-v',str(out)+':/work',image,'bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/'+name+'.tcl']
 with(out/(name+'.log')).open('w') as f:run=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 text=(out/(name+'.log')).read_text();assert witness in text,(name,run.returncode,text[-1000:])
 assert (run.returncode==0)==(name=='exact'),(name,run.returncode)
 results[name]={'exit':run.returncode,'witness':witness,'netlist_sha256':hashlib.sha256((out/(name+'.v')).read_bytes()).hexdigest(),'sdc_sha256':hashlib.sha256((out/(name+'.sdc')).read_bytes()).hexdigest()}
 print('ACTUAL_DUAL_ROLE',name,'PASS' if name=='exact' else 'REFUSED',flush=True)
(out/'results.json').write_text(json.dumps(dict(image=image,source_gate=str(gate),original_mapped_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),results=results,claim='mapped ownership only; not layout/signoff/adoption'),indent=2)+'\n')
