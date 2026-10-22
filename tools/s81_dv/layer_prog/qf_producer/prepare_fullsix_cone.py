#!/usr/bin/env python3
"""Freeze private actual-six-frame sources and exact selected wiring. No build."""
from pathlib import Path
import subprocess,json,re,hashlib,shutil
from head_local_contract import ROOT
b=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle';rec=json.loads((b/'selected_vehicle_build_manifest.json').read_text())
out=b/'fullsix_launch_packet';out.mkdir(exist_ok=True)
# Emit declarations and actual43 statements, retaining the actual complete frames.
die=Path('/tmp/s81-selected-ceaed19c4-die.v').read_bytes();assert hashlib.sha256(die).hexdigest()==rec['files'][0].get('selected_die_sha256','61b683b697d17b7d6d1619352d302648d835822677c02097ce48639a0aa399b8')
lines=die.decode().splitlines();selected=json.loads((b/'selected_input_return_cone.json').read_text())['lines'];stmts=[r['text'] for r in selected]
used=set(re.findall(r'\b(?:w_x_|r_x_|nx_|w_r_|r_r_|nr_|u_f_3)[A-Za-z0-9_]+','\n'.join(stmts)))
used={n for n in used if not n.startswith('u_f_3') or n.endswith('_xok')}
decls=[];found=set()
for l in lines:
 if not l.strip().startswith('wire '):continue
 names=set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b',l))&used
 if names:decls.append(l);found|=names
assert used==found,used-found
resets=sorted(set(re.findall(r'\b(?:rs_|rsg_)[A-Za-z0-9_]+','\n'.join(stmts))))
landindices=[int(x) for x in re.findall(r'land_fault\[(\d+)\]','\n'.join(stmts))]
body=['module selected_fullsix_cone(input wire clk,rst_n,input wire[1100:0]source_word,output wire[559:0]rt,output wire[3:0]return_landing_fault);',
 'wire ck_cl3S=clk;wire[15:0]u_s_3S_ck_xc={16{clk}};wire[4415:0]xc;reg[1:0]mkq;',
 'always @(posedge clk or negedge rst_n)if(!rst_n)mkq<=0;else mkq<={mkq[0],1\'b1};',
 'wire[1103:0]xw4={source_word[1100:565],source_word[0],mkq[1],source_word[564:0],mkq[1]};',
 'generate for(genvar c=0;c<4;c++)begin:head ot_s81sl_rly #(.W(1104),.D(6))u_x(.clk(clk),.d(xw4),.q(xc[1104*c+:1104]));end endgenerate',
 f'wire[{max(landindices)}:0]land_fault;']+decls
for r in resets:body.append(f'wire {r}=rst_n; // declared logical diagnosticreset only; native regional date NULL')
for copy,name in enumerate(['3L01','3R01','3L02','3R02']):
 for lane in range(4):body.append(f'assign w_x_f_{name}_l{lane}_src=xc[{1104*copy+276*lane}+:276];')
body+=stmts
body+=['assign rt={140\'d0,w_r_f_3R03_lnd,w_r_f_3R02_src,w_r_f_3R01_lnd,w_r_f_3L03_lnd,w_r_f_3L02_src,w_r_f_3L01_lnd};',
 'assign return_landing_fault={'+','.join(f'land_fault[{i}]' for i in landindices)+'};','endmodule']
(out/'selected_fullsix_cone.sv').write_text('\n'.join(body)+'\n')
manifest=[]
for f in rec['files']:
 p=f['path'];data=subprocess.check_output(['git','show',f['ref']+':'+p]);assert hashlib.sha256(data).hexdigest()==f['sha256']
 manifest.append(f)
(out/'source_files.f').write_text('\n'.join('+incdir+src/'+p for p in rec['incdirs'])+'\n'+'\n'.join('src/'+p['path'] for p in manifest)+'\n')
shutil.copyfile(b/'marker_sources/cells_used.v',out/'cells_used.v')
(out/'contract.json').write_text(json.dumps(dict(scope='SOURCE PREPARATION ONLY; actual fullsix coupled frontend requires ROOTtechnicaladmission',
 source_ref='ceaed19c4',source_files=manifest,source_count=125,selected_statements=43,physical_frames=6,frame_ROMs=1012,
 selected_die_sha256=hashlib.sha256(die).hexdigest(),logical_reset_assumptions=resets,
 genuine_source='Frozen51raw→quantizer→retainedXS source',real_frames=True,no_input_or_return_substitutes=True,
 CAP_plan='Not selected. Actual reset CFG state retained for first preparatory trace; F9/CFG/drain failures are evidence, not waived. No numericPASS.',
 actual_backend_tags=None,native_physical_phase=None,original_deadline_unchanged=True,new_production_RTL=False),indent=2)+'\n')
print('FROZEN_FULLSIX_SOURCE_PREPARATION actual43statements/125sources/6frames; no elaboration or build')
