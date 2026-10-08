#!/usr/bin/env python3
"""Actual route frontend: full wrapper exact test, synthesis and clock-SDC intake."""
import argparse,gzip,hashlib,json,os,subprocess,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
LIB=ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs'
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve()
yosys=os.environ.get('YOSYS',str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'))
sta=os.environ.get('STA',str(Path.home()/'.local/opentallas-tools/opensta-be771a0/bin/sta'))
def run(name,args):
 r=subprocess.run(args,capture_output=True,text=True,cwd=ROOT);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 return r
inventory=json.loads((HERE/'closure_job.template.json').read_text())['archive_paths']
for rel in inventory: assert (ROOT/rel).exists(), 'Archive dependency absent: '+rel
spec=importlib.util.spec_from_file_location('physical_driver', ROOT/'tools/run_abi3_physical.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
hooks=['POST_IO_PLACEMENT=physical/qwen_link_forwarded_tmr_pair/regions.tcl','POST_CTS=physical/qwen_link_forwarded_tmr_pair/propagate.tcl','PRE_GLOBAL_ROUTE=physical/qwen_link_forwarded_tmr_pair/propagate.tcl','POST_DETAIL_ROUTE=physical/qwen_link_forwarded_tmr_pair/audit.tcl']
driver.resolve_floorplan([0,0,560.568,69.072],[2.16,2.16,558.408,66.912],[],['M2','M7'],hooks)
rtl=ROOT/'rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv' 
for neg in [0,1]:
 r=run(f'compile{neg}',['iverilog','-g2012','-s','tb_qwen_link_forwarded_tmr_pair',f'-Ptb_qwen_link_forwarded_tmr_pair.NEG={neg}','-o',str(out/'bench'),str(rtl),str(HERE/'pair.sv'),str(HERE/'tb_pair.sv')]);assert r.returncode==0,r.stderr
 r=run(f'bench{neg}',['vvp',str(out/'bench')]);assert ('PASS NL=1' in r.stdout and r.returncode==0) if neg==0 else ('clock ownership mismatch' in r.stdout and r.returncode!=0),r.stdout
inv=gzip.open(LIB/'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','rt').read();simple=gzip.open(LIB/'asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz','rt').read()
(out/'combo.lib').write_text(inv[:inv.rfind('}')]+simple[simple.index('cell ('):simple.rfind('}')]+ '\n}\n')
seq=LIB/'asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
ys=f'''read_verilog -sv {rtl} {HERE}/pair.sv
synth -top ot_qwen_link_forwarded_tmr_pair
dfflibmap -liberty {seq}
abc -liberty {out}/combo.lib
opt_clean
write_verilog -noattr {out}/mapped.v
'''
(out/'synth.ys').write_text(ys);r=run('synth',[yosys,'-Q','-T','-s',str(out/'synth.ys')]);assert r.returncode==0,r.stderr
(out/'intake.tcl').write_text(f'''read_liberty {seq}
read_liberty {out}/combo.lib
read_verilog {out}/mapped.v
link_design ot_qwen_link_forwarded_tmr_pair
read_sdc {HERE}/clocks.sdc
source {HERE}/propagate.tcl
source {HERE}/reset_inventory.tcl
report_clock_properties [all_clocks]
foreach c {{ab_hop1 ba_hop1}} {{
 set endpoints [all_registers -clock $c -data_pins]
 if {{[llength $endpoints]<528}} {{error "direction capture bank missing: $c"}}
 report_checks -to $endpoints -path_delay min_max -group_path_count 2 -format full_clock_expanded
}}
check_setup -verbose
puts "FORWARDED_FRONTEND_PASS"
exit
''')
r=run('sta',[sta,'-exit',str(out/'intake.tcl')]);assert r.returncode==0 and 'FORWARDED_FRONTEND_PASS' in r.stdout and 'Error:' not in r.stdout+r.stderr,r.stdout+r.stderr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[rtl,*[x for x in HERE.iterdir() if x.is_file()],seq,LIB/'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz',LIB/'asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz']
record=dict(pass_all=True,source_sha256={str(x.relative_to(ROOT)):sha(x) for x in inputs},logs_sha256={x.name:sha(x) for x in out.glob('*.log')},mapped_sha256=sha(out/'mapped.v'),scope='Actual route frontend only: reversed physical direction full two-hop bench and wrong-clock negative, mapped ASAP7 synthesis, six actual clock SDC intake with both 528-bit capture banks. Unrouted STA is not physical closure.',adoption=False)
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'pass_all':True,'out':str(out)}))
