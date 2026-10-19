"""Functional payload contract: auxiliary reset cannot mask or invent a bad hop."""
import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which('tclsh'), reason='no tclsh')
@pytest.mark.parametrize('contract,bad_bit,missing,verdict,bits,errors', [
    (False, False, False, 'FAIL', 3, 0),  # old fallback incorrectly pairs reset
    (True, False, False, 'PASS', 2, 0),
    (True, True, False, 'FAIL', 2, 0),   # real zero-stage payload still fails
    (True, False, True, 'FAIL', 1, 1),   # disconnected payload fails closed
])
def test_complete_payload_contract(tmp_path, contract, bad_bit, missing, verdict, bits, errors):
    # Mock the tiny ODB interface, retaining the real audit pairing/judgement.
    # Capture has two payload pins plus synchronous reset from another tree.
    script = r'''
namespace eval ord {proc get_db_block {} {return block}}
proc block {method args} {
  if {$method eq "getNets"} {return fnet}
  if {$method eq "findInst"} {return capture}
}
proc fnet {method} {
  if {$method eq "getName"} {return n_fck}
  if {$method eq "getITerms"} {return driver}
}
proc driver {method} {
  if {$method eq "getIoType"} {return OUTPUT}
  if {$method eq "getInst"} {return source}
}
proc source {method} {return source}
proc capture {method} {
  if {$method eq "getName"} {return capture}
  if {$method eq "getMaster"} {return master}
  if {$method eq "getITerms"} {return {clock data0 data1 reset}}
}
proc master {method} {return dsfd_dvrlyh_2_EW}
proc clockterm {method} {return ck}
proc term0 {method} {return {i[0]}}
proc term1 {method} {return {i[1]}}
proc resetterm {method} {return rs}
proc signalnet {method} {return 0}
proc input {pin method} {
  if {$method eq "getIoType"} {return INPUT}
  if {$method eq "getNet"} {
    if {$pin eq "data1" && $::missing} {return NULL}
    return signalnet
  }
  if {$method eq "getMTerm"} {
    return [dict get {clock clockterm data0 term0 data1 term1 reset resetterm} $pin]
  }
}
foreach pin {clock data0 data1 reset} {interp alias {} $pin {} input $pin}
array set ::ot_die_rep_fclk_old {source 1 capture 1}
rename ot_die_rep_fclk_fwd unused_fwd
proc ot_die_rep_fclk_fwd {net bufs depth acc_name} {
  upvar 1 $acc_name acc
  dict set acc capture {2 clockterm}
}
rename ot_die_rep_fclk_back unused_back
proc ot_die_rep_fclk_back {pin bufs} {
  if {$pin eq "reset"} {return {reset_source 0}}
  if {$pin eq "data1" && $::bad_bit} {return {payload 0}}
  return {payload 2}
}
'''
    audit = Path(__file__).with_name('fclk_audit.tcl')
    prefix = tmp_path / 'audit'
    script = (f'source {{{audit}}}\nset ::missing {int(missing)}\nset ::bad_bit {int(bad_bit)}\n' + script)
    if contract:
        script += 'set ::ot_die_rep_fclk_data_ports [dict create dsfd_dvrlyh_2_EW {{i\\[*\\]} 2}]\n'
    script += f'puts "RC [ot_die_rep_fclk_audit {{{prefix}}} {{n_fck}} {{BUF}}]"\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert not result.stderr, result.stderr
    report = json.loads(prefix.with_suffix('.json').read_text())
    assert report['verdict'] == verdict
    assert report['pairing_errors'] == errors
    rows = list(csv.DictReader(prefix.with_suffix('.tsv').open(), delimiter='\t'))
    assert int(rows[0]['data_bits']) == bits
    if contract:
        assert rows[0]['auxiliary_inputs'] == '1'
    assert ('RC 0' in result.stdout) == (verdict == 'PASS')


def test_failing_audit_retains_repaired_database():
    # A failing audit must preserve its costly repaired netlist for endpoint
    # diagnostics, while retaining the nonzero fail exit.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from die_repeaters import step
    text = step.tcl_call('s81', '/work/die_repeaters.json',
                         repeat_nets=['n*_fck*'], fclk_policy='fail')
    assert 'write_db {/work/die_repeaters.fclk.fail.odb}; exit 3' in text
