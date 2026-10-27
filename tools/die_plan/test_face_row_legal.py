"""Actual Q1 row fragments must fit full cell footprints beside fixed taps."""
from pathlib import Path
import subprocess


def test_q1_fragment_taps_and_shared_occupancy():
    code=Path(__file__).with_name('face_flops.tcl').read_text()
    code=code.split('# BEGIN legal-row allocator',1)[1].split('# END legal-row allocator',1)[0]
    script=code+'''\nset ff_x0 4320;set ff_y0 4320;set ff_x1 211680;set ff_y1 168480
set ff_sw 54;set ff_rh 270;set ff_cpitch 2160
set ff_legal_rows [dict create 152820 {{4320 6588} {103464 112104} {206928 211680}} 153090 {{4320 6588}}]
set ff_legal_occ {}
ff_reserve_rect tap0 4320 152820 4428 153090
ff_reserve_rect tap1 6480 152820 6588 153090
if {[ff_site_legal a 4320 152820 1080 270]} {error tap_overlap}
if {[ff_site_legal a 6480 152820 1080 270]} {error row_fragment_overrun}
set x [ff_find_x a 4320 152820 1080 270]
if {$x != 4428} {error "expected4428 got$x"}
ff_reserve_rect a $x 152820 [expr {$x+1080}] 153090
if {[ff_find_x b 6480 152820 1080 270] ne ""} {error "second full flop cannot fit"}
if {[ff_site_legal b 4428 152820 1080 270]} {error occupied_by_other_face}
if {![ff_site_legal a 4428 152820 1080 270]} {error own_footprint}
if {[ff_site_legal z 8640 152820 1080 270]} {error macro_cut_row}
if {[ff_site_legal z 4428 152821 1080 270]} {error off_row}
if {[ff_site_legal z 4321 153090 1080 270]} {error off_site}
if {![ff_site_legal z 4320 153090 1080 270]} {error adjacent_row}
if {[ff_site_legal z 4320 153090 1080 540]} {error missing_second_row}
puts PASS
'''
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and p.stdout.strip()=='PASS',p.stdout+p.stderr
