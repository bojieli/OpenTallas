"""Private source-only CTS entry proposal. Never invokes CTS or changes flags."""
from pathlib import Path
import hashlib,json,sys
scripts=Path(sys.argv[1]);manifest=json.loads(Path(sys.argv[2]).read_text());out=Path(sys.argv[3])
for rel,want in manifest.items():
 p=scripts.parent/rel;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==want,rel
p=scripts/'cts.tcl';raw=p.read_bytes();body=raw.decode();load='load_design 3_place.odb 3_place.sdc';pre='source_step_tcl PRE CTS';post='source_step_tcl POST CTS';assert all(body.count(x)==1 for x in [load,pre,post]);changes=[(load,load+'\not_pg_cts_canary_begin cts'),(pre,pre+'\not_pg_cts_canary_after_pre cts'),(post,'ot_pg_cts_canary_before_post cts\n'+post+'\not_pg_cts_canary_finish cts\nset ::ot_pg_cts_canary_reached_POST 1')]
for old,new in changes:body=body.replace(old,new,1)
undo=body
for old,new in reversed(changes):undo=undo.replace(new,old,1)
assert undo.encode()==raw
(scripts/'cts_private_native_pg_body.tcl').write_text(body)
wrapper='''# PRIVATE CTS lifecycle proposal. Original source, MM and flags unchanged.
source /work/pg_cts_canary.tcl
unset -nocomplain ::ot_pg_cts_canary_reached_POST
set ot_pg_cts_body_code [catch {source [file join $::env(SCRIPTS_DIR) cts_private_native_pg_body.tcl]} ot_pg_cts_body_result ot_pg_cts_body_options]
set ot_pg_cts_end_code [catch {ot_pg_cts_canary_finish cts} ot_pg_cts_end_result ot_pg_cts_end_options]
if {$ot_pg_cts_body_code == 1} {
 if {$ot_pg_cts_end_code} {puts stderr "OT_PG_CTS_CLEANUP_REFUSED $ot_pg_cts_end_result"}
 return -options $ot_pg_cts_body_options $ot_pg_cts_body_result
}
if {$ot_pg_cts_end_code == 1} {return -options $ot_pg_cts_end_options $ot_pg_cts_end_result}
if {$ot_pg_cts_end_code != 0} {error "OT_PG_CTS_NONLOCAL_CLEANUP_REFUSED code=$ot_pg_cts_end_code result=$ot_pg_cts_end_result"}
if {$ot_pg_cts_body_code != 0} {error "OT_PG_CTS_NONLOCAL_BODY_REFUSED code=$ot_pg_cts_body_code result=$ot_pg_cts_body_result"}
if {![info exists ::ot_pg_cts_canary_reached_POST] || !$::ot_pg_cts_canary_reached_POST} {error OT_PG_CTS_POST_NOT_REACHED}
''';p.write_text(wrapper);out.write_text(json.dumps({'status':'SOURCE_ONLY_NO_CTS_RELEASE','original_entry_sha256':hashlib.sha256(raw).hexdigest(),'whole_original_entry_body_preserved':True,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'outer_wrapper_sha256':hashlib.sha256(wrapper.encode()).hexdigest(),'begin':'after actual load before entire PRE','after_pre':'after complete original PRE before inverter repair','before_post':'before entire original POST','finish':'after entire original POST before primary save, and idempotent outer cleanup on every completion','flags_source_geometry_modified':False},indent=2)+'\n')
