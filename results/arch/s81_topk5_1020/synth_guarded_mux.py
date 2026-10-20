"""Kept-copy pilot mapping only, not a substitute for canonical gate inventory."""
from pathlib import Path
import subprocess,sys,json,hashlib
root=Path.cwd(); baseline=root/'synth_a7d/synth.ys'
out=root/(sys.argv[1] if len(sys.argv)>1 else 'synth_guarded_mux_v1');out.mkdir(exist_ok=True)
top='ot_s81ph_native_guarded_mux'
script=[f'set ::env(DESIGN_NAME) {top}', 'set ::env(OT_KEEP_PIN_REGS) 1',
        'yosys read_verilog -sv '+str(root/'rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_guarded_mux.sv'),
        'yosys hierarchy -check -top '+top,
        'source '+str(root/'ot_keep_regs.tcl')]
for line in baseline.read_text().splitlines():
    if not line or line.startswith(('read_verilog ','hierarchy ')):continue
    line=line.replace('ot_s81ph_native_sel_hist_bank',top).replace(str(root/'synth_a7d'),str(out))
    script.append('yosys '+line)
script.append('yosys write_json '+str(out/'mapped.json'))
(out/'synth.tcl').write_text('\n'.join(script)+'\n')
(out/'provenance.json').write_text(json.dumps({'baseline_ys_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((root/'rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_guarded_mux.sv').read_bytes()).hexdigest(),'kind':'pilot ABC833, no physical or production inventory claim'},indent=2)+'\n')
with (out/'run.log').open('w') as log:
    r=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-c',str(out/'synth.tcl')],stdout=log,stderr=subprocess.STDOUT)
print('GUARDED_MUX_SYNTH_RC',r.returncode);raise SystemExit(r.returncode)
