#!/usr/bin/env python3
"""Route frontend of the centre-aligned forwarded-clock station: exact bench with mutants, mapped synthesis, SDC intake."""
import argparse,gzip,hashlib,json,os,subprocess
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
rtl=ROOT/'rtl/physical/ot_qwen_link_fwd_cx_tmr.sv'
r=run('bench',['bash',str(HERE/'bench.sh'),str(out/'bench')]);assert r.returncode==0 and 'BENCH_OK' in r.stdout,r.stdout
inv=gzip.open(LIB/'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','rt').read();simple=gzip.open(LIB/'asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz','rt').read()
(out/'combo.lib').write_text(inv[:inv.rfind('}')]+simple[simple.index('cell ('):simple.rfind('}')]+ '\n}\n')
seq=LIB/'asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
(out/'synth.ys').write_text(f'''read_verilog -sv {rtl}
synth -top ot_qwen_link_fwd_cx_station
dfflibmap -liberty {seq}
abc -liberty {out}/combo.lib
opt_clean
write_verilog -noattr {out}/mapped.v
''')
r=run('synth',[yosys,'-Q','-T','-s',str(out/'synth.ys')]);assert r.returncode==0,r.stderr
(out/'intake.tcl').write_text(f'''read_liberty {seq}
read_liberty {out}/combo.lib
read_verilog {out}/mapped.v
link_design ot_qwen_link_fwd_cx_station
read_sdc {HERE}/clocks.sdc
source {HERE}/reset_inventory.tcl
report_clock_properties [all_clocks]
foreach c {{fclk_ab fclk_ba}} {{
 set endpoints [all_registers -clock $c -data_pins]
 if {{[llength $endpoints]<528}} {{error "capture bank missing: $c"}}
 report_checks -to $endpoints -path_delay min_max -group_path_count 2 -format full_clock_expanded
}}
report_checks -to [get_ports ab_o*] -path_delay min_max -format full_clock_expanded
check_setup -verbose
puts "CX_FRONTEND_PASS"
exit
''')
r=run('sta',[sta,'-exit',str(out/'intake.tcl')]);assert r.returncode==0 and 'CX_FRONTEND_PASS' in r.stdout and 'Error' not in r.stdout+r.stderr,r.stdout+r.stderr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[rtl,*[x for x in HERE.iterdir() if x.is_file()]]
record=dict(pass_all=True,source_sha256={str(x.relative_to(ROOT)):sha(x) for x in inputs},mapped_sha256=sha(out/'mapped.v'),
 bench=(out/'bench/summary.txt').read_text(),
 scope='Route frontend: two-hop exact bench (golden PASS, wrong-clock negative + 6 RTL mutants FAIL), mapped ASAP7 synthesis, 4-clock port SDC intake. Unrouted STA is not closure.',adoption=False)
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'pass_all':True,'out':str(out)}))
