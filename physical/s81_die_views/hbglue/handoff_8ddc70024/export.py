#!/usr/bin/env python3
"""One-shot read-only harvest/export of the successful, source-pinned glue ECO.
Run on EPYC1 through admit.sh 60 -- python3 export.py NEW_SCRATCH.
No routing, repair, synthesis, benches, or writes to the closure-loop job.
"""
import hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
JOB=Path('/srv/opentallas-scratch/claude/closure-loop/hbglue_cl_8ddc70024')
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
NAME='ot_dsrom_head_bundle_glue'
SRC='8ddc7002479798a1e3d5ce5875a163d672973e75'
PLAT='/OpenROAD-flow-scripts/flow/platforms/asap7'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=False)
 inp=root/'inputs';out=root/'view';raw=root/'raw';inp.mkdir();out.mkdir();raw.mkdir()
 candidate=JOB/'cl/eco-overlay-recovery-a2/candidate'
 base=next((candidate/'orfs/results/asap7').glob('*/base'))
 installed=next((JOB/'routes/hbglue_cl_8ddc70024/work/orfs/results/asap7').glob('*/base'))
 pins={}
 def copy(p,q):
  q.parent.mkdir(parents=True,exist_ok=True);a=sha(p);shutil.copyfile(p,q);assert sha(q)==a and sha(p)==a
  pins[str(p)]={'sha256':a,'bytes':p.stat().st_size,'copy':str(q.relative_to(root))};q.chmod(0o444)
 for name in ['6_final.odb','6_final.spef','6_final.sdc','6_final.v','eco_drc.rpt']:
  copy(base/name,inp/name)
  if name!='eco_drc.rpt':assert sha(base/name)==sha(installed/name),(name,'installed differs')
 overlay='physical/s81_die_views/hbglue/margin/signoff_cl_hbglue_cl_8ddc70024.sdc'
 copy(JOB/'src'/overlay,inp/'post.sdc')
 assert sha(inp/'post.sdc')=='836a1414ba60d7918d4c1922fc4a71795311d29fabf3a4aa681b19a2f322ccd6'
 for prefix,folder in [('successful',candidate),('failed',JOB/'cl/eco')]:
  for name in ['eco.log','corner.log','corner_sta.json','result.json','orfs/w18_sta_ss.log','orfs/w18_sta_ff.log','orfs/w18_sta_ss.tcl','orfs/w18_sta_ff.tcl']:
   copy(folder/name,raw/prefix/name)
 for name in ['inputs.json','original_hold_eco.tcl','original_hold_eco.sh','original_state.json']:
  copy(JOB/'cl/eco-overlay-recovery-a2'/name,raw/'recovery'/name)
 for name in ['calib.json','calib.env','hold_eco.a1.log','hold_eco.a2.log','eco_install.a2.log','eco_install.a2.sh','job.json']:
  copy(JOB/'cl'/name,raw/name)
 # Hash every historic failed/pre-ECO artifact without copying bulky databases.
 historical={}
 for folder in [JOB/'cl/eco',JOB/'cl/eco-overlay-recovery-a2',installed]:
  for p in folder.rglob('*'):
   if p.is_file() and (folder!=installed or p.name.endswith('.pre_eco')):historical[str(p)]=sha(p)
 write(root/'historical_hashes.json',historical)
 write(root/'inputs.json',{'source_commit':SRC,'job':str(JOB),'files':pins,'installed_final_matches_candidate':True})
 write(root/'admission.json',{'peak_gib':60,'basis':'existing full-shape closure job declared peak 60 GiB; sequential read-only extraction reuses its inventory','guard':'/srv/opentallas-scratch/admit.sh 60','reserve_gib':100,'guard_sha256':sha('/srv/opentallas-scratch/admit_core.py'),'meminfo':Path('/proc/meminfo').read_text(),'loadavg':Path('/proc/loadavg').read_text(),'disk_free_bytes':shutil.disk_usage(root).free,'timestamp':time.time()})
 libnames=['AO_RVT_{C}_nldm_211120.lib.gz','INVBUF_RVT_{C}_nldm_220122.lib.gz','OA_RVT_{C}_nldm_211120.lib.gz','SEQ_RVT_{C}_nldm_220123.lib','SIMPLE_RVT_{C}_nldm_211120.lib.gz']
 for corner in ['ss','ff']:
  libs='\n'.join(f'read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_'+n.format(C=corner.upper()) for n in libnames)
  tcl=f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{libs}
read_db /inputs/6_final.odb
read_sdc /inputs/6_final.sdc
read_spef /inputs/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /inputs/post.sdc
if {{[llength [all_clocks]] != 1 || [get_full_name [lindex [all_clocks] 0]] ne "core_clk"}} {{error "clock mismatch"}}
puts "OT_CLOCK [get_full_name [lindex [all_clocks] 0]] [get_property [lindex [all_clocks] 0] period]"
puts "OT_WS [sta::worst_slack_cmd {'max' if corner=='ss' else 'min'}]"
report_checks -path_delay min_max -group_path_count 1 -format full_clock_expanded
check_setup -verbose
report_parasitic_annotation
write_sdc /out/effective_{corner}.sdc
set f [open /out/ports_{corner}.tsv w]
set block [ord::get_db_block]
puts $f "# die_area [$block getDieArea]"
foreach p [$block getBTerms] {{puts $f "[$p getName]\t[$p getIoType]\t[$p getSigType]\t[llength [$p getBPins]]"}}
close $f
set f [open /out/output_slack_{corner}.tsv w]
foreach p [all_outputs] {{puts $f "[get_full_name $p]\t[get_property $p slack_min]\t[get_property $p slack_max]"}}
close $f
write_timing_model -library_name {NAME}_{corner} /out/{NAME}_{corner}.lib
'''
  if corner=='ss':tcl+=f'write_abstract_lef /out/{NAME}.lef\n'
  tcl+='puts "OT_EXPORT_DONE"\nexit\n'
  (out/f'export_{corner}.tcl').write_text(tcl)
  cmd=['docker','run','--rm','-v',f'{inp}:/inputs:ro','-v',f'{out}:/out',IMAGE,'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/out/export_{corner}.tcl']
  with (out/f'export_{corner}.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  assert r.returncode==0 and 'OT_EXPORT_DONE' in (out/f'export_{corner}.log').read_text(),corner
 assert all(sha(p)==v['sha256'] for p,v in pins.items()),'original changed'
 assert all(sha(p)==h for p,h in historical.items()),'historical artifact changed'
 write(root/'export.json',{'source_commit':SRC,'image':IMAGE,'originals_unchanged':True,'historical_artifacts_unchanged':True,'files':{p.name:sha(p) for p in out.iterdir()},'scope':'component candidate; no die-context placement adoption'})
if __name__=='__main__':main()
