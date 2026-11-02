from pathlib import Path
import subprocess

def test_nonisolated_native_alignment_measures_after_the_load_transition():
    source=Path(__file__).with_name('core_tap_align.tcl').read_text()
    snippet=source[source.index('    set calibration_rounds 1'):source.index('    set nb [expr {min($nb,')]
    prefix='set d 120;set st 20\n'
    cases=[(True,0,1,1),(True,0,2,1),(True,0,3,6),(True,1,1,1),(True,1,2,6),(False,0,1,6)]
    for calibrate,iso,round_,expected in cases:
        env=f'set ::env(OT_DTAP_ISO) {iso};set r {round_}\n'
        env+='set ::env(OT_DTAP_CALIBRATE) 1\n' if calibrate else 'unset -nocomplain ::env(OT_DTAP_CALIBRATE)\n'
        p=subprocess.run(['tclsh'],input=prefix+env+snippet+f'\nif {{$nb != {expected}}} {{error "bad calibration round"}}\n',text=True,capture_output=True)
        assert p.returncode==0 and not p.stderr,p.stderr
