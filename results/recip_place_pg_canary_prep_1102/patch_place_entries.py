#!/usr/bin/env python3
"""PRIVATE canary-only stage instrumentation. No CAD invocation or flag edits."""
from pathlib import Path
import hashlib,json,sys
scripts=Path(sys.argv[1]);out=Path(sys.argv[2]);manifest=json.loads(Path(sys.argv[3]).read_text())
for rel,want in manifest.items():
 candidate=scripts.parent/rel
 assert candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest()==want,('normal post-MM readset changed',rel)
stages=[('3_1_place_gp_skip_io','global_place_skip_io','2_floorplan.odb','GLOBAL_PLACE_SKIP_IO'),('3_2_place_iop','io_placement','3_1_place_gp_skip_io.odb','IO_PLACEMENT'),('3_3_place_gp','global_place','3_2_place_iop.odb','GLOBAL_PLACE'),('3_4_place_resized','resize','3_3_place_gp.odb','RESIZE'),('3_5_place_dp','detail_place','3_4_place_resized.odb','DETAIL_PLACE')]
results=[]
for stage,name,db,hook in stages:
 p=scripts/(name+'.tcl');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['scripts/'+name+'.tcl'],name
 src=raw.decode();load='load_design '+db+' 2_floorplan.sdc';pre='source_step_tcl PRE '+hook;post='source_step_tcl POST '+hook
 assert all(src.count(x)==1 for x in [load,pre,post]),name
 injections=[(load,load+'\not_pg_place_canary_begin '+name),(pre,pre+'\not_pg_place_canary_after_pre '+name),(post,post+'\not_pg_place_canary_finish '+name+'\nset ::ot_pg_place_canary_reached_stage {'+stage+'}')]
 body=src
 for old,new in injections:body=body.replace(old,new,1)
 # Removing only exact injected commands must recover ALL original stage bytes.
 recovered=body
 for old,new in reversed(injections):recovered=recovered.replace(new,old,1)
 assert recovered.encode()==raw
 bodypath=scripts/(name+'_private_pg_canary_body.tcl');bodypath.write_text(body)
 wrapper='''# PRIVATE diagnostic only; normal flags/source/body retained, no strict admission change.
source /work/pg_place_canary.tcl
unset -nocomplain ::ot_pg_place_canary_reached_stage
set ot_pg_place_canary_body_code [catch {source [file join $::env(SCRIPTS_DIR) __BODY__]} ot_pg_place_canary_body_result ot_pg_place_canary_body_options]
set ot_pg_place_canary_cleanup_code [catch {ot_pg_place_canary_finish __API_STAGE__} ot_pg_place_canary_cleanup_result ot_pg_place_canary_cleanup_options]
if {$ot_pg_place_canary_body_code == 1} {
  if {$ot_pg_place_canary_cleanup_code} {puts stderr "OT_PG_CANARY_CLEANUP_REFUSED $ot_pg_place_canary_cleanup_result"}
  return -options $ot_pg_place_canary_body_options $ot_pg_place_canary_body_result
}
if {$ot_pg_place_canary_cleanup_code == 1} {return -options $ot_pg_place_canary_cleanup_options $ot_pg_place_canary_cleanup_result}
if {$ot_pg_place_canary_cleanup_code != 0} {error "OT_PG_CANARY_NONLOCAL_CLEANUP_REFUSED code=$ot_pg_place_canary_cleanup_code result=$ot_pg_place_canary_cleanup_result"}
if {$ot_pg_place_canary_body_code != 0} {error "OT_PG_CANARY_NONLOCAL_BODY_REFUSED code=$ot_pg_place_canary_body_code result=$ot_pg_place_canary_body_result"}
if {![info exists ::ot_pg_place_canary_reached_stage] || $::ot_pg_place_canary_reached_stage ne {__STAGE__}} {error OT_PG_CANARY_STAGE_POST_NOT_REACHED}
'''.replace('__BODY__',bodypath.name).replace('__STAGE__',stage).replace('__API_STAGE__',name)
 p.write_text(wrapper)
 results.append(dict(stage=stage,entry=name+'.tcl',original_sha256=hashlib.sha256(raw).hexdigest(),instrumented_body_sha256=hashlib.sha256(body.encode()).hexdigest(),entry_wrapper_sha256=hashlib.sha256(wrapper.encode()).hexdigest(),original_whole_body_preserved=True,begin_before_entire_PRE=True,finish_after_POST_before_primary_save=(name!='io_placement'),io_save_before_POST_retained=(name=='io_placement')))
out.write_text(json.dumps(dict(status='PREP_ONLY_SOURCE_PATCH_NO_CAD',stages=results,flags_source_MM_geometry_changed=False),indent=2)+'\n')
