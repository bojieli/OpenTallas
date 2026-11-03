"""Source-only CTS wrapper control flow. No native PG or CTS qualification."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).parent
cases={'success':('set ::ot_pg_cts_post_reached 1; set ::active 0',False,True),'body_error':('error ORIGINAL_BODY_ERROR',False,False),'nonlocal_body':('return EARLY',False,False),'missing_post':('set x 1',False,False),'cleanup_error':('set ::ot_pg_cts_post_reached 1',True,False),'nonlocal_cleanup':('set ::ot_pg_cts_post_reached 1','return',False)}
for tag,(body,bad,ok) in cases.items():
 with tempfile.TemporaryDirectory() as td:
  t=Path(td);(t/'cts.native_pg_original.tcl').write_text(body+'\n')
  end='error CLEANUP_ERROR' if bad is True else 'return -code return CLEANUP_RETURN' if bad=='return' else 'set ::active 0'
  harness=f'''set ::env(SCRIPTS_DIR) {{{t}}}
set ::active 1
proc ot_native_pg_status {{}} {{return [dict create active $::active]}}
proc ot_pg_native_birth_end {{}} {{{end}}}
set code [catch {{source {{{r/'native_pg_birth_cts_driver.tcl'}}}}} message]
if {{($code==0) != {int(ok)}}} {{error "unexpected {tag} code=$code message=$message"}}
if {{"{tag}" eq "body_error" && $message ne "ORIGINAL_BODY_ERROR"}} {{error PRIMARY_ERROR_LOST}}
puts PASS
'''
  (t/'run.tcl').write_text(harness);p=subprocess.run(['tclsh',str(t/'run.tcl')],capture_output=True,text=True)
  assert p.returncode==0 and p.stdout.strip().endswith('PASS'),(tag,p.stdout,p.stderr)
 print(tag,'PASS')
