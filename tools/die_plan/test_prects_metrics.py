"""Exercise the actual container installer and Tcl dispatch, preserving CTS+ reports."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / 'physical/common_flow/grt183_make.sh'
BODY = '''set calls {}
proc report_metrics { stage when { include_erc true } { include_clock_skew true } } {
  lappend ::calls [list $stage $when $include_erc $include_clock_skew]
  return "$stage:$when:$include_erc:$include_clock_skew"
}
'''


def install(tmp_path, enabled, body=BODY):
    work, scripts = tmp_path / 'kit', tmp_path / 'scripts'
    work.mkdir(exist_ok=True); scripts.mkdir(exist_ok=True)
    (work / 'config.mk').write_text('export OT_SKIP_PRECTS_METRICS = 1\n' if enabled else '')
    script = scripts / 'report_metrics.tcl'
    if not script.exists(): script.write_text(body)
    env = dict(os.environ, OT_GRT183_WORK=str(work), OT_GRT183_SCRIPTS=str(scripts))
    proc = subprocess.run(['bash', str(INSTALL), 'true'], env=env, text=True, capture_output=True)
    return proc, script


def test_default_leaves_orfs_file_identical(tmp_path):
    proc, script = install(tmp_path, False)
    assert proc.returncode == 0
    assert script.read_text() == BODY


def test_only_pre_cts_summaries_skipped_and_patch_idempotent(tmp_path):
    proc, script = install(tmp_path, True)
    assert proc.returncode == 0, proc.stderr
    once = script.read_bytes()
    assert install(tmp_path, True)[0].returncode == 0
    assert script.read_bytes() == once
    tcl = f'''source {{{script}}}
set env(OT_SKIP_PRECTS_METRICS) 1
report_metrics 2 floorplan
report_metrics 3 resizer false false
foreach n {{1 4 5 6}} {{
  set got [report_metrics $n required false true]
  if {{$got ne "$n:required:false:true"}} {{error "later stage changed: $got"}}
}}
if {{[llength $calls] != 4}} {{error "wrong stages: $calls"}}
unset env(OT_SKIP_PRECTS_METRICS)
if {{[report_metrics 3 default] ne "3:default:true:true"}} {{error "default changed"}}
puts DISPATCH_PASS
'''
    p = subprocess.run(['tclsh'], input=tcl, text=True, capture_output=True)
    assert 'DISPATCH_PASS' in p.stdout and not p.stderr, p.stdout + p.stderr


def test_unknown_orfs_signature_fails_before_make(tmp_path):
    proc, _ = install(tmp_path, True, 'proc report_metrics {stage} {error incompatible}\n')
    assert proc.returncode == 2
    assert 'unsupported report_metrics signature' in proc.stderr
