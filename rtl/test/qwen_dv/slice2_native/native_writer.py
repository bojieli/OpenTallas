from pathlib import Path
import gzip,re,subprocess,os,json
root=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[root/f'asap7sc7p5t_{k}_RVT_TT_nldm_{d}.lib{ext}' for k,d,ext in [('AO','211120','.gz'),('INVBUF','220122','.gz'),('OA','211120','.gz'),('SEQ','220123',''),('SIMPLE','211120','.gz')]]
texts=[gzip.open(p,'rt').read() if str(p).endswith('.gz') else p.read_text() for p in libs]
parts=[]
for text in texts:
 start=re.search(r'(?m)^\s*cell\s*\(',text).start()
 parts.append(text[start:text.rfind('}')])
header=texts[0][:re.search(r'(?m)^\s*cell\s*\(',texts[0]).start()]
Path('out/native.lib').write_text(header+'\n'.join(parts)+'\n}\n')
script='read_liberty -lib out/native.lib; read_verilog -sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/test/qwen_dv/slice2_native/native_writer.sv; synth -top native_writer -noabc; dfflibmap -liberty out/native.lib; abc -liberty out/native.lib; clean; write_verilog -noattr out/native.v'
with open('out/native_synth.log','w') as log:subprocess.run(['yosys','-p',script],stdout=log,stderr=subprocess.STDOUT,check=True)
cmd=['python3','tools/ref_tile/native_census.py','--netlist','out/native.v','--top','native_writer','--out','out/native_census.json']
for p in libs:cmd+=['--liberty',str(p)]
subprocess.run(cmd,check=True)
