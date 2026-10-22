import pathlib,subprocess,json,sys,hashlib
p=pathlib.Path.cwd();o=p/'codex_pg_pickup_1020';o.mkdir(exist_ok=True)
bases=list((p/'routes/gate/work/orfs/results/asap7').glob('*/base'));assert len(bases)==1,bases
base=bases[0]
for stage in ['4_1_cts','5_1_grt']:
 db=base/(stage+'.odb');assert db.exists(),db
 script='read_db /base/'+stage+'.odb\n'
 script+=r'''
set pg 0;set unbound 0;set protected 0;set fixed 0;set both 0
set fp [open /out/STATESTAGE.tsv w]
puts $fp "instance\tmaster\tpin\tdont_touch\tfixed\tplacement"
foreach inst [[ord::get_db_block] getInsts] {
 foreach it [$inst getITerms] {
  if {[$it getSigType] ni {POWER GROUND}} {continue}
  incr pg
  if {[$it getNet] ne "NULL"} {continue}
  incr unbound
  set dt [$inst isDoNotTouch];set fx [$inst isFixed]
  if {$dt} {incr protected};if {$fx} {incr fixed};if {$dt && $fx} {incr both}
  puts $fp "[$inst getName]\t[[$inst getMaster] getName]\t[[$it getMTerm] getName]\t$dt\t$fx\t[$inst getPlacementStatus]"
 }
}
close $fp
puts "OT_PG_STATE total=$pg unbound=$unbound protected_unbound=$protected fixed_unbound=$fixed both=$both"
exit
'''.replace('STATESTAGE',stage)
 (o/(stage+'.tcl')).write_text(script)
 r=subprocess.run(['docker','run','--rm','--memory=4g','--memory-swap=4g','-v',str(p/'src')+':/src:ro','-v',str(base)+':/base:ro','-v',str(o)+':/out','openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/'+stage+'.tcl'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (o/(stage+'.log')).write_text(r.stdout)
 assert r.returncode==0,r.stdout[-2000:]
 print(stage,r.stdout[-1500:],flush=True)
