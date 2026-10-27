"""Narrow only a shield's outer edge; retain PG and actual clock geometry."""
import shield_notches as N
import die_clock_128 as C
import clock_routed as R


def row(rect,net='VSS',special=True):return dict(layer='M9',net=net,special=special,rect=rect)


def test_pg_overlap_creates_twenty_nm_gap_then_outer_trim_keeps_clock_edge():
    rows=[row([0,0,640,10000]),row([660,-100,1140,10100]),row([680,0,1320,10000]),row([-1140,0,-500,10000],'clock',False)]
    fixed,edits=N.trim_shields(rows,{640})
    assert len(edits)==1 and fixed[0]['rect']==[0,0,620,10000]
    assert fixed[1:]==rows[1:]
    assert rows[0]['rect']==[0,0,640,10000]


def test_exact_minimum_gap_and_pg_only_gap_are_not_edited():
    rows=[row([0,0,640,10000]),row([680,0,1160,10000]),row([2000,0,2480,10000]),row([2500,0,2980,10000])]
    assert N.trim_shields(rows,{640})==(rows,[])


def test_native_postpass_requires_created_shield_swire_provenance():
    text='\n'.join(N.tcl('VSS',.64))
    assert 'shield provenance missing' in text and '[info exists provenance($sw)]' in text
    assert 'round(0.04*' in text
    merged='\n'.join(C.shield_merge_tcl('VSS',dict(width=.64)))
    assert 'ot_merge_shields VSS' in merged and 'ot_trim_shield_notches VSS' in merged
    w=dict(name='clock',segs=[('M9',0.,0.,0.,10.)])
    lines=R.shield_only_tcl(C.combo_tcl([w],dict(width=.64,space=.5),'VSS'))
    assert 'lappend ::ot_clock_shield_swires $fsw' in lines
