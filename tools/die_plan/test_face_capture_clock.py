"""Execute the actual input-capture walker against data/clock MTerm controls."""
import subprocess
from pathlib import Path

def test_data_capture_never_follows_clock_mterm():
    source=(Path(__file__).with_name("face_flops.tcl")).read_text()
    a=source.index("proc ff_from_in ")
    b=source.index("# output port:",a)
    body=source[a:b]
    fixture=r"""
proc ff_is_ff {i} {return 1}
proc ff_is_buf {i} {return 0}
proc data_net {m} {return data_it}
proc clock_net {m} {return clock_it}
proc mixed_net {m} {return {clock_it data_it}}
proc data_it {m} {if {$m eq "getInst"} {return data_ff}; return data_mt}
proc clock_it {m} {if {$m eq "getInst"} {return clock_ff}; return clock_mt}
proc data_mt {m} {if {$m eq "getIoType"} {return INPUT}; return SIGNAL}
proc clock_mt {m} {if {$m eq "getIoType"} {return INPUT}; return CLOCK}
"""
    checks=r"""
if {[ff_from_in data_net 0] ne "data_ff"} {error "real data capture lost"}
if {[ff_from_in clock_net 0] ne ""} {error "clock incorrectly claimed a capture"}
if {[ff_from_in mixed_net 0] ne "data_ff"} {error "clock won over real data"}
puts "PASS actual ff_from_in data/clock/mixed controls"
"""
    r=subprocess.run(["tclsh"],input=fixture+body+checks,text=True,capture_output=True)
    assert r.returncode==0 and "PASS actual" in r.stdout, r.stdout+r.stderr
