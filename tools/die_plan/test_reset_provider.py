import subprocess
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parent
MOCK=r'''
set db {}; set serial 0; set instances {}; set nets {}
proc mk {type name fields} {
 global db serial
 set id obj[incr serial]
 dict set db $id [dict merge $fields [dict create type $type name $name]]
 interp alias {} $id {} op $id
 return $id
}
proc op {id method args} {
 global db instances nets
 set row [dict get $db $id]; set type [dict get $row type]
 if {$method eq "getName"} {return [dict get $row name]}
 if {$type eq "block"} {
  if {$method eq "findInst"} {if {[dict exists $instances [lindex $args 0]]} {return [dict get $instances [lindex $args 0]]};return NULL}
  if {$method eq "findNet"} {if {[dict exists $nets [lindex $args 0]]} {return [dict get $nets [lindex $args 0]]};return NULL}
 }
 set keys [dict create getMaster master getInst inst getMTerm mterm getNet net getIoType direction getITerms terms]
 if {[dict exists $keys $method]} {return [dict get $row [dict get $keys $method]]}
 if {$method eq "findITerm"} {if {[dict exists $row pins [lindex $args 0]]} {return [dict get $row pins [lindex $args 0]]};return NULL}
 error "unsupported mock call $type $method"
}
proc net {name} {
 global nets
 if {![dict exists $nets $name]} {dict set nets $name [mk net $name [dict create terms {}]]}
 return [dict get $nets $name]
}
proc cell {name master ports} {
 global db instances
 set m [mk master $master {}];set i [mk inst $name [dict create master $m pins {}]]
 dict set instances $name $i
 foreach {pin spec} $ports {
  lassign $spec direction nn
  set n [net $nn];set mt [mk mterm $pin [dict create direction $direction]]
  set it [mk iterm $name/$pin [dict create inst $i mterm $mt net $n]]
  dict set db $i pins $pin $it
  set terms [dict get $db $n terms];lappend terms $it;dict set db $n terms $terms
 }
 return $i
}
set block [mk block block {}]
net clk;net other_clk;net tap;net other_tap
cell cf CFIFO {cr {INPUT clk} rst {INPUT tap} rs {OUTPUT rs}}
set stages {};set prev rs
for {set k 0} {$k<15} {incr k} {
 set stage f$k;lappend stages $stage
 cell $stage DFFHQNx1_ASAP7_75t_R [list CLK [list INPUT clk] D [list INPUT $prev] QN [list OUTPUT raw$k]]
 cell inv$k INVx1_ASAP7_75t_R [list A [list INPUT raw$k] Y [list OUTPUT n$k]]
 set prev n$k
}
foreach s {e0 e2 e3 e4} {cell $s ROM [list clk [list INPUT clk] rst_n [list INPUT $prev]]}
set c [dict create provider cf provider_master CFIFO provider_pin rs provider_clock cr source_clock_net clk sinks {e0 e2 e3 e4} sink_master ROM sink_pin rst_n sink_clock clk stages $stages tap_net [net tap] tap_key rst_n_t27 tap_parity 0 buffers [dict create INVx1_ASAP7_75t_R [dict create input A output Y inverted 1] BUFx1_ASAP7_75t_R [dict create input A output Y inverted 0]] flop [dict create master DFFHQNx1_ASAP7_75t_R output QN data D clock CLK inverted 1]]
'''


def run(tmp_path,mutation=''):
    p=tmp_path/'run.tcl'
    import hashlib
    lib=tmp_path/'native.lib';lib.write_text('fixed native library contract')
    binding='\ndict set c libraries {'+str(lib)+'} '+hashlib.sha256(lib.read_bytes()).hexdigest()+'\n'
    p.write_text('source {'+str(HERE/'reset_provider.tcl')+'}\n'+MOCK+binding+mutation+r'''
set before $db
set r [ot_reset_provider_preserve $block $c]
if {$db ne $before} {error "checker mutated netlist"}
puts "RESULT [dict get $r status] [dict get $r provider_offset_cycles] [dict size [dict get $r sinks]] [dict get $r absolute_release_cycles]"
''')
    return subprocess.run(['tclsh',str(p)],text=True,capture_output=True)


def test_fifteen_actual_stages_four_sinks_preserved(tmp_path):
    r=run(tmp_path)
    assert r.returncode==0,r.stderr
    assert 'RESULT PRESERVED 15 4 NOT_RUN' in r.stdout


@pytest.mark.parametrize('mutation',[
    'dict set c stages [lrange $stages 0 end-1]\n',
    'dict set db [[dict get $instances f7] findITerm CLK] net [net other_clk]\n',
    'dict set db [[dict get $instances inv3] getMaster] name BUFx1_ASAP7_75t_R\n',
    'dict set db [[dict get $instances e2] findITerm rst_n] net [net rs]\n',
    'dict set db [[dict get $instances cf] findITerm rst] net [net other_tap]\n',
    'dict set c provider missing_provider\n',
    'dict for {path digest} [dict get $c libraries] {dict set c libraries $path [string repeat 0 64]}\n',
])
def test_wrong_depth_clock_polarity_sink_or_provider_refused(tmp_path,mutation):
    r=run(tmp_path,mutation)
    assert r.returncode!=0 and 'OT_RESET_PROVIDER' in r.stderr


def test_native_library_hash_and_ff_polarity_are_required(tmp_path):
    import reset_provider as R
    inv=tmp_path/'inv.lib';seq=tmp_path/'seq.lib'
    inv.write_text('cell (INVx1_ASAP7_75t_R) {pin (A) {direction : input;} pin (Y) {direction : output; function : "!A";}}')
    seq.write_text('cell (DFFHQNx1_ASAP7_75t_R) {ff (IQN,IQNN) {clocked_on : "CLK"; next_state : "!D";} pin (QN) {function : "IQN";}}')
    models,flop=R.models(inv,R.sha(inv),seq,R.sha(seq))
    assert models['INVx1_ASAP7_75t_R']['inverted']==1 and flop['inverted']==1
    with pytest.raises(ValueError,match='Liberty identity mismatch'):
        R.models(inv,'0'*64,seq,R.sha(seq))
    seq.write_text(seq.read_text().replace('"!D"','"D"'))
    with pytest.raises(ValueError,match='function changed'):
        R.models(inv,R.sha(inv),seq,R.sha(seq))
