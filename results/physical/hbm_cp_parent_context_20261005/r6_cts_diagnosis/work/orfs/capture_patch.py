from pathlib import Path
import hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl');s=p.read_text()
needle='  check_placement -verbose\n';assert s.count(needle)==1
replacement='''  if {[catch {check_placement -verbose} ot_cp_capture_error]} {
    orfs_write_db /work/cts_failure.odb
    orfs_write_sdc /work/cts_failure.sdc
    puts OT_CP_CTS_FAILURE_CAPTURE
    error $ot_cp_capture_error
  }
'''
print(json.dumps(dict(original_cts_sha256=hashlib.sha256(s.encode()).hexdigest(),capture_only=True)))
p.write_text(s.replace(needle,replacement))
