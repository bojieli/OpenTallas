import pathlib,subprocess,re,json,hashlib
p=pathlib.Path.cwd();o=p/'codex_final_audit_1020';o.mkdir(exist_ok=True)
root=list((p/'routes').glob('*/work/orfs'));assert len(root)==1;work=root[0]
bases=list((work/'results/asap7').glob('*/base'));assert len(bases)==1;base=bases[0]
ylog=list((work/'logs/asap7').glob('*/base/1_1_yosys_canonicalize.log'));assert len(ylog)==1
libs=sorted(set(re.findall(r'Executing Liberty frontend: (.+)',ylog[0].read_text())))
assert len(libs)>=6,libs
image=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}'],text=True).strip()
mount=['docker','run','--rm','--memory=4g','--memory-swap=4g','-v',str(p/'src')+':/src:ro','-v',str(work)+':/work:ro','-v',str(o)+':/out',image]
args=['python3','/out/tools/ref_tile/native_census.py','--netlist','/work/'+str((base/'6_final.v').relative_to(work)),'--top','qkd_embedding_row_tx_ctx_native32','--out','/out/native_final.json']
for lib in libs:args+=['--liberty',lib]
r=subprocess.run(mount+args,capture_output=True,text=True);(o/'native_final.log').write_text(r.stdout+r.stderr);print('NATIVE',r.returncode,r.stdout[-600:],flush=True)
s='source /src/physical/common_flow/native_pg_binding.tcl\nread_db /work/'+str((base/'6_final.odb').relative_to(work))+'\n'
s+=r'''
ot_pg_audit_snapshot [ord::get_db_block] /out/pg_final.json
set f [open /out/net_geometry.tsv w]
puts $f "net\txmin\tymin\txmax\tymax\tspan_dbu"
set worst 0;set wn "";set pg 0;set unbound 0;set protected 0;set fixed 0
foreach i [[ord::get_db_block] getInsts] {
 foreach it [$i getITerms] {
  if {[$it getSigType] in {POWER GROUND}} {
   incr pg
   if {[$it getNet] eq "NULL"} {incr unbound;if {[$i isDoNotTouch]} {incr protected};if {[$i isFixed]} {incr fixed}}
  }
 }
}
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] in {POWER GROUND CLOCK}} {continue}
 set xmin 999999999;set ymin 999999999;set xmax -1;set ymax -1;set count 0
 foreach it [$net getITerms] {
  set bb [[$it getInst] getBBox]
  set xmin [expr {min($xmin,[$bb xMin])}];set ymin [expr {min($ymin,[$bb yMin])}]
  set xmax [expr {max($xmax,[$bb xMax])}];set ymax [expr {max($ymax,[$bb yMax])}];incr count
 }
 foreach bt [$net getBTerms] {
  foreach bp [$bt getBPins] {foreach bb [$bp getBoxes] {
   set xmin [expr {min($xmin,[$bb xMin])}];set ymin [expr {min($ymin,[$bb yMin])}]
   set xmax [expr {max($xmax,[$bb xMax])}];set ymax [expr {max($ymax,[$bb yMax])}];incr count
  }}
 }
 if {$count<2} {continue}
 set span [expr {$xmax-$xmin+$ymax-$ymin}]
 puts $f "[$net getName]\t$xmin\t$ymin\t$xmax\t$ymax\t$span"
 if {$span>$worst} {set worst $span;set wn [$net getName]}
}
close $f
set b [ord::get_db_block];set dbu [$b getDbUnitsPerMicron];set rect [$b getDieArea]
puts "OT_FINAL_GEOMETRY max_signal_bbox_manhattan_um=[expr {$worst/double($dbu)}] net=$wn outline_um=[expr {[$rect dx]/double($dbu)}]x[expr {[$rect dy]/double($dbu)}]"
puts "OT_FINAL_PG pg=$pg unbound=$unbound protected_unbound=$protected fixed_unbound=$fixed"
exit
'''
(o/'final.tcl').write_text(s)
r2=subprocess.run(mount+['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/final.tcl'],capture_output=True,text=True);(o/'final.log').write_text(r2.stdout+r2.stderr);print(r2.stdout[-2000:],r2.stderr[-1000:],flush=True)
files=[base/'6_final.odb',base/'6_final.v',base/'6_final.sdc',base/'6_final.spef',p/'src/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx_native32.sv',p/'cl/helper_overlay_plan.json']
(o/'identity.json').write_text(json.dumps(dict(source_commit='801bce13604f1a7d7113415ba3508af43296ad28',image=image,base=str(base),liberty=libs,files=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files],geometry_scope='conservative signal-net bounding boxes include complete incident instance rectangles and port shapes; not route-wire-length or parent-crossing qualification'),indent=2)+'\n')
raise SystemExit(max(r.returncode,r2.returncode))
