from pathlib import Path
import subprocess,json,hashlib,sys
root=Path.cwd();old=root/'synth_a7d/synth.ys';out=root/(sys.argv[1] if len(sys.argv)>1 else 'synth_kept_742');out.mkdir(exist_ok=True)
lines=old.read_text().splitlines();script=[]
script.append('set ::env(DESIGN_NAME) ot_s81ph_native_sel_hist_bank')
script.append('set ::env(OT_KEEP_PIN_REGS) 1')
for line in lines:
 if not line:continue
 if line.startswith('read_verilog ') and line.endswith('ot_s81ph_native_sel_lib.sv'):line='read_verilog -sv '+str(root/'results/arch/s81_topk5_1020/gold_hist256.sv')
 if line.startswith('read_verilog ') and line.endswith('ot_s81ph_native_sel_hist_bank.sv'):script.append('yosys read_verilog -sv '+str(root/'rtl/lib/ot_rst_relay.sv'))
 if line.startswith('synth -top '):script.append('source '+str(root/'ot_keep_regs.tcl'))
 line=line.replace(str(root/'synth_a7d'),str(out))
 script.append('yosys '+line)
script.append('yosys write_json '+str(out/'mapped.json'))
(out/'synth.tcl').write_text('\n'.join(script)+'\n')
yosys=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
with (out/'run.log').open('w') as log:r=subprocess.run([str(yosys),'-c',str(out/'synth.tcl')],stdout=log,stderr=subprocess.STDOUT)
print('KEPT_SYNTH_RC',r.returncode);raise SystemExit(r.returncode)
