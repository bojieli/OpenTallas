"""Explicit N/S column fill preserves bit order and legal row/site footprints."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import landing_place as LP
from test_landing_status_slide_resize import COMMON

TCL=Path(__file__).with_name('landing_placement.tcl').read_text()
pytestmark=pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh unavailable')


def _proc(name):
    return re.search(r'proc '+name+r' \{[^\n]*\} \{\n.*?\n\}\n',TCL,re.S).group(0)


def run(tag='ring:i+x+ff',obstacle=False,resize=False,rect='0 0 1.08 1.08', legacy=False):
    script=COMMON+'\n'+''.join(_proc(n) for n in ['cland_occupy','cland_family_w','cland_put_column','cland_put','cland_ffkey','cland_column_select','cland_place_ff'])
    script+='\nset cland_occ {};set cland_famw {};set cland_ff_fill 0.90;set instances {};set places {};set moves 0\n'
    for bit in range(4):
        for slot in range(2):
            inst=f'i{bit}{slot}';name=f'u_ring.s_d[{slot}][{bit}]'
            script+=f'''proc {inst} {{m args}} {{
 switch $m {{getName {{return {{{name}}}}} getMaster {{return DFFHQNx1_ASAP7_75t_R}}
 getPlacementStatus {{return PLACED}} setPlacementStatus {{}} setOrient {{}}
 setLocation {{incr ::moves;dict set ::places {{{name}}} $args}} }}
}}\nlappend instances {inst}\n'''
    script+='proc block {m args} {return $::instances}\nset ff_blk block\n'
    if obstacle:script+='cland_occupy 0 0 270 270\n'
    if legacy:script+='rename cland_column_select actual_select\nproc cland_column_select {args} {return 0}\n'
    script+=f'''if {{[catch {{cland_place_ff u_ring {{{rect}}} {tag}}} e]}} {{puts "ERR $e"}} else {{
 foreach {{n p}} $places {{puts "LOC $n $p"}}
 puts "MOVES $moves"
}}\n'''
    # The real master predicates used by the placement loop.
    script=script.replace('getHeight { return 270 }','getHeight { return 270 } isBlock { return 0 }')
    env={k:v for k,v in os.environ.items() if k!='OT_CLAND_FIT_RESERVE'}
    if resize:env['OT_CLAND_FIT_RESERVE']='resize'
    cp=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,env=env,check=True)
    assert not cp.stderr,cp.stderr
    rows=re.findall(r'LOC (\S+) (\d+) (\d+)',cp.stdout)
    return {n:(int(x),int(y)) for n,x,y in rows},cp.stdout


def test_explicit_tag_only_and_lsb_high_preserved():
    band=dict(ring_place='ff',fill_axis='x')
    assert LP._spread(band)=='+x+ff'
    assert LP._spread(band,'lsb_high')=='+x+ffr'
    assert LP._spread(dict(ring_place='ff'))=='+ff'
    for bad in [dict(fill_axis='x'),dict(ring_place='ff',fill_axis='y')]:
        with pytest.raises(ValueError):LP._spread(bad)


def test_ns_columns_keep_slot_copies_at_same_x_and_bits_advance_x():
    col,_=run();row,_=run(tag='ring:i+ff')
    assert len(col)==len(row)==8
    assert col['u_ring.s_d[0][0]'][0]==col['u_ring.s_d[1][0]'][0]
    assert col['u_ring.s_d[0][1]'][0]>col['u_ring.s_d[0][0]'][0]
    assert row['u_ring.s_d[0][0]'][1]==row['u_ring.s_d[1][0]'][1]
    reverse,_=run(tag='ring:i+x+ffr')
    assert reverse['u_ring.s_d[0][3]']==col['u_ring.s_d[0][0]']
    assert reverse['u_ring.s_d[1][3]']==col['u_ring.s_d[1][0]']


def test_column_fill_avoids_obstacles_and_reserves_resize_family_width():
    placed,out=run(obstacle=True,resize=True,rect='0 0 1.62 1.62')
    assert len(placed)==8,out
    boxes=[]
    for x,y in placed.values():
        assert x%54==0 and y%270==0
        assert 0<=x and x+270<=1620 and 0<=y and y+270<=1620
        assert not (x<270 and y<270)
        box=(x,y,x+270,y+270)
        assert all(min(box[2],b[2])<=max(box[0],b[0]) or min(box[3],b[3])<=max(box[1],b[1]) for b in boxes)
        boxes.append(box)
    placed,out=run(rect='0 0 .1 1.08')
    assert not placed and 'no legal nonoverlapping' in out


def test_quantized_capacity_control_and_dry_run_has_no_cell_mutations():
    # 90% continuous area spacing rounds up to 3 native rows: only six
    # locations fit. Whole-band selection reaches the legal one-row quantum.
    old, negative = run(rect='0 0 .54 1.08', legacy=True)
    assert not old and 'no legal nonoverlapping' in negative
    placed, out = run(rect='0 0 .54 1.08')
    assert len(placed) == 8, out
    assert 'padding reduced by 2 native rows' in out
    assert 'MOVES 8' in out   # failed/successful probes never touch the ODB
    assert len(set(placed.values())) == 8
    for x,y in placed.values():
        assert 0 <= x and x+162 <= 540 and 0 <= y and y+270 <= 1080


def test_infeasible_physical_band_does_not_become_a_density_waiver():
    placed,out=run(rect='0 0 .17 .27')
    assert not placed and 'no legal nonoverlapping' in out
