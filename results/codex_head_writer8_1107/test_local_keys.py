from pathlib import Path
import subprocess,sys
root=Path(sys.argv[1]);p=root/'tools/die_plan/landing_placement.tcl';s=p.read_text()
a=s[s.index('proc cland_ffkey '):s.index('# chunk width WCH')]
a+='\nproc cland_kbit {kf rev} {scan $kf %d v;return [expr {$rev ? 999999999-$v : $v}]}\n'
a+=s[s.index('proc cland_ctl_rekey '):s.index('# DIE-HEAD-43',s.index('proc cland_ctl_rekey '))] if False else ''
b=s.index('proc cland_ctl_rekey ');e=s.index('proc cland_freg_rekey ',b);a+=s[b:e]
a+=r'''
set wr {u_cland_x/u_ring.g_wreg.sl[2].ch[7].u_wen/q}
set rd {u_cland_x/u_ring.dch[2].u_dsel/g_srep.sr[3].u_sel/di[1]}
if {[cland_ffkey $wr 0 64 566] ne $wr} {error "default placement changed"}
set kw [cland_ffkey $wr 0 64 566 8 8]
set kr [cland_ffkey $rd 0 64 566 8 8]
if {$kw ne {u_cland_x/u_ring.s_d|000000060|999999982|q}} {error "bad writer key: $kw"}
if {$kr ne {u_cland_x/u_ring.s_d|000000156|999999971|}} {error "bad reader key: $kr"}
set rev [cland_ffkey $wr 1 64 566 8 8]
if {$rev ne {u_cland_x/u_ring.s_d|999999939|999999982|q}} {error "bad reversed key: $rev"}
lassign [cland_ctl_rekey [list [list $kw writer] [list $kr reader]] {u_cland_x/u_ring.s_d} 3 566 0] n out
if {$n != 0 || $out ne [list [list $kw writer] [list $kr reader]]} {error "START rekey collapsed local controls"}
puts {PASS: writer/read groups keyed to own payload; reverse order; START rekey preserves them; default unchanged}
'''
a+=s[s.index('proc cland_freg_rekey '):s.index('proc cland_dsel_wch ')]
a+=r'''
set fq0 {u_cland_link_i/g_freg.u_face/q\[0\]$_DFF_P_}
set fq100 {u_cland_link_i/g_freg.u_face/q\[100\]$_DFF_P_}
set fq565 {u_cland_link_i/g_freg.u_face/q\[565\]$_DFF_P_}
set fbase {u_cland_link_i.g_freg.u_face/q}
lassign [cland_freg_rekey [list [list $fq0 q0] [list $fq100 q100] [list $fq565 q565]] $fbase 566 1] nf keyed
if {$nf != 3} {error "standalone face-bank bit names not recognized"}
set ordered [lsort -index 0 $keyed]
if {[lindex $ordered 0 1] ne {q565} || [lindex $ordered end 1] ne {q0}} {error "lsb_high input bank reversed"}
puts {PASS: actual standalone FREG names use numeric bit order aligned with lsb_high pins}
'''
r=subprocess.run(['tclsh'],input=a,text=True,capture_output=True);print(r.stdout+r.stderr,end='');assert r.returncode==0 and 'PASS:' in r.stdout
sys.path.insert(0,str(root/'tools/die_plan'));from landing_place import _local_chunk_config
assert _local_chunk_config({})==''
t={'clock':{'landing_ring_wreg':{'buses':['x'],'write_chunk':8,'dsrep':8}}};cfg=_local_chunk_config(t);assert '{write 8 read 8}' in cfg and 'u_cland_x' in cfg
print('PASS: opt-in placement metadata emitted; absent config unchanged')
