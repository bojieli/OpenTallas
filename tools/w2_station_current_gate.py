#!/usr/bin/env python3
"""Single changed-source native-quarter gate; peer sources remain read-only."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--registered-check',action='store_true');a=ap.parse_args()
root=Path(__file__).resolve().parents[1];out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
new='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_current_pipeline.sv'
if a.registered_check:
 new='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_check_pipeline.sv'
srcs=(root/'physical/hbm_die_abstracts_20261006/links/native_quarter/sources.f').read_text().splitlines()
files=[];pins={}
for rel in srcs:
 p=root/rel;s=p.read_text();pins[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 # Only actual station banks/cuts change. Provider and parent are unchanged.
 if rel.endswith(('ot_hbm_native_station.sv','ot_hbm_native_frame_station.sv')):
  bank='ot_hbm_w2_protected_bank_check_on' if a.registered_check else 'ot_hbm_w2_protected_bank_current_on'
  cut='ot_hbm_w2_protected_cut_check_on' if a.registered_check else 'ot_hbm_w2_protected_cut_current_on'
  s=s.replace('ot_hbm_w2_protected_bank #',bank+' #').replace('ot_hbm_w2_protected_cut #',cut+' #')
  p=out/p.name;p.write_text(s)
 files.append(str(p))
files.insert(3,str(root/new));
if a.registered_check:
 prior='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_current_pipeline.sv';files.insert(3,str(root/prior));pins[prior]=hashlib.sha256((root/prior).read_bytes()).hexdigest()
pins[new]=hashlib.sha256((root/new).read_bytes()).hexdigest()
b=root/'physical/hbm_die_abstracts_20261006/links/native_quarter/tb_native_quarter_publication.sv'
s=b.read_text();pins[str(b.relative_to(root))]=hashlib.sha256(b.read_bytes()).hexdigest()
# Calendar instrumentation only; exact data, corruption and warm controls unchanged.
s=s.replace('module tb_native_quarter_publication;', 'module tb_native_quarter_publication;\n integer edge_count=0; always @(posedge clk_sm) edge_count<=edge_count+1;\n always @(posedge clk_sm) if(q_ack_v && ack_gate) $display("CALENDAR_QUARTER_ACK edge=%0d",edge_count);\n always @(posedge clk_sm) if(activation_release && activation_release_r) $display("CALENDAR_PARENT_RELEASE edge=%0d",edge_count);\n always @(posedge clk_sm) if(warm_ack) $display("CALENDAR_WARM_ACK edge=%0d",edge_count);')
if a.registered_check:
 aux_rel='rtl/hbm_accel/integrated_20261005/tb_w2_bank_check_pipeline.sv'
 files.append(str(root/aux_rel));pins[aux_rel]=hashlib.sha256((root/aux_rel).read_bytes()).hexdigest()
 (out/Path(aux_rel).name).write_bytes((root/aux_rel).read_bytes())
 s=s.replace(' integer edge_count=0;', ' wire checker_gate_done; tb_w2_bank_check_pipeline checker_gate(clk_sm,checker_gate_done);\n integer edge_count=0;')
 s=s.replace('  cold;launch;', '  wait(checker_gate_done); cold;launch;',1)
 s=s.replace(' integer edge_count=0;', ' integer edge_count=0; integer calendar_base=0;')
 s=s.replace('edge_count);', 'edge_count-calendar_base);')
 s=s.replace('wait(checker_gate_done); cold;', 'wait(checker_gate_done); calendar_base=edge_count; cold;')
b=out/b.name;b.write_text(s);files.append(str(b))
cmd=['iverilog','-g2012','-s','tb_native_quarter_publication','-o',str(out/'gate.vvp'),*files]
with (out/'compile.log').open('w') as f:c=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT)
r=None
if c.returncode==0:
 with (out/'run.log').open('w') as f:r=subprocess.run(['vvp',str(out/'gate.vvp')],cwd=root,stdout=f,stderr=subprocess.STDOUT)
passed=r is not None and r.returncode==0 and 'PASS_NATIVE_QUARTER_PUBLICATION' in (out/'run.log').read_text()
if a.registered_check: passed=passed and 'PASS_W2_CHECK' in (out/'run.log').read_text()
(out/'terminal.json').write_text(json.dumps(dict(compile_exit=c.returncode,runtime_exit=None if r is None else r.returncode,passed=passed,source_pins=pins,generated_source_pins={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.sv')},changed_scope='only actual station banks/cuts; original data/oracle/warm/fault stimuli unchanged',command=cmd),indent=2)+'\n')
print(out, 'PASS' if passed else 'FAIL',flush=True)
raise SystemExit(0 if passed else 1)
