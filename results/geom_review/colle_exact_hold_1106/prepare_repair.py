import json,pathlib,shutil
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106')
for side in ('e','w'):
 src=r/side/'kit'; dst=r/side/'repair1'; dst.mkdir()
 for p in src.iterdir():
  if p.name in ('run','signoff') or p.name.startswith('sta_'):continue
  if p.is_dir(): shutil.copytree(p,dst/p.name)
  elif p.is_file(): shutil.copy2(p,dst/p.name)
 nick=f'kl_dsfd_coll_lane_{side}_safe8_ntf_compact_m6_pg6_vB'
 b=dst/'run/results/asap7'/nick/'base'; b.mkdir(parents=True)
 shutil.copy2(src/'run/results/asap7'/nick/'base/1_synth.v',b/'1_synth.v')
 prefix=(r/side/'probe.tcl').read_text().split('so_timing STD')[0]+'so_timing STD\n'
 t=prefix+'''set ::env(RESULTS_DIR) /out
source /work/clk_freeze.tcl
ot_clk_freeze /out
set b [ord::get_db_block]
set_routing_layers -signal M2-M6 -clock M4-M5
global_route -guide_file /out/seed.guide
global_route -start_incremental
set nf 0
foreach i [$b getInsts] {
 if {[[$i getMaster] getType] eq "CORE_SPACER"} {
  set pure 1
  foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] ni {POWER GROUND}} {set pure 0}}
  if {$pure} {odb::dbInst_destroy $i; incr nf; continue}
 }
 $i setPlacementStatus LOCKED
}
puts "COLLE_REMOVED_FILLERS $nf"
'''
 p=json.load(open(r/side/'proposal/proposal.json'))
 for x in p['proposals']:
  def q(s):return '{'+s+'}'
  name=x['new_instance']; loc=x['location_dbu']; box=x['bbox_dbu']
  t+=f'''set cap [$b findInst {q(x['capture'])}]
if {{$cap eq "NULL"}} {{error "missing capture"}}
set d [$cap findITerm D]
set old [$d getNet]
if {{[$old getName] ne {q(x['old_net'])}}} {{error "capture net mismatch"}}
set ni [odb::dbInst_create $b [[ord::get_db] findMaster {q(x['master'])}] {name}]
$ni setOrient {x['orient']}
$ni setLocation {loc[0]} {loc[1]}
$ni setPlacementStatus FIRM
set bb [$ni getBBox]
if {{[list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] ne {q(' '.join(map(str,box)))}}} {{error "buffer bbox mismatch"}}
set nn [odb::dbNet_create $b {name}_out]
[$ni findITerm A] connect $old
[$ni findITerm Y] connect $nn
$d connect $nn
foreach nt [$ni getITerms] {{
 set ty [[$nt getMTerm] getSigType]
 if {{$ty ni {{POWER GROUND}}}} continue
 set found 0
 foreach ct [$cap getITerms] {{if {{[[$ct getMTerm] getSigType] eq $ty}} {{$nt connect [$ct getNet]; set found 1; break}}}}
 if {{!$found}} {{error "new buffer PG unbound"}}
}}
puts {{COLLE_INSERTED {name} {x['capture']}}}
'''
 t+='''check_placement -verbose
source /work/prd_route_keep.tcl
ot_prd_route_keep /base/6_final.odb
global_route -end_incremental
ot_clk_freeze_assert exact_four_post_grt
ot_prd_route_keep_restore
write_db /out/5_1_grt.odb
write_sdc /out/5_1_grt.sdc
write_guides /out/route.guide
puts "COLLE_EXACT_FOUR_GRT_COMPLETE"
exit
'''
 (dst/'exact_four.tcl').write_text(t)
 with open(dst/'config.mk','a') as f:f.write('\n# Exact four data-only hold buffers; preserve source ck0 hook.\noverride export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl\nexport OT_ECO_DRT_PRE_CHAIN = /work/ck0_pin.tcl\n')
 (dst/'variant.env').write_text((dst/'variant.env').read_text()+'\nOT_ECO_FROM=route\n')
