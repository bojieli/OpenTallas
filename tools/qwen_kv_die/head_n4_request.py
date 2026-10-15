"""Exact N4 gather/M2 score reservations in the actual86.4um source bands.

No hard ECTL dimension changes. Homes may extend into the full head-column
intake corridor; all physical outlines remain real and must clear the generator.
"""
from pathlib import Path
import head_staged_plan as H
import head_placement_lattice as L

ROOT=Path(__file__).resolve().parents[2]


def homes(rows):
    by={i['name']:i for i in rows};gathers=[];scores=[]
    score_path=ROOT/'physical/ref_tile/qkh_head_sstage/views/qkh_head_sstage/qkh_head_sstage.lef'
    score_size,score_pins=H.lef(score_path)
    score_macro=L.lef(str(score_path))
    gather_macro=L.from_pin_tcl(ROOT/'results/arch/qwen_split_1014/head_ingress_n4_1417/gather_pins.tcl',(324,21.6))
    score_cy=(min(y for x,y in score_pins['ck'])+max(y for x,y in score_pins['ck']))/2
    for head in (i for i in rows if i['master']=='qkd_rhead'):
        parts=head['name'].split('_');h=int(parts[-1]);ectl=by['ectl_'+'_'.join(parts[1:-1])]
        fx,fy=H.FLIPS[ectl['orient']];lower=h<2
        def place(name,master,x,y,w,height,orient,clock_y,m5=False):
            wx=ectl['x']+(ectl['w']-x-w if fx else x)
            wy=ectl['y']+(ectl['h']-y-height if fy else y)
            macro=gather_macro if m5 else score_macro
            (wx,wy),origin_rule=L.snap(macro,orient,(wx,wy))
            return dict(name=head['name']+'/'+name,master=master,xy=[round(wx,6),round(wy,6)],
                size_um=[w,height],orient=orient,origin_rule=origin_rule,siting_scope='exact declared gather pins until real view exists; actual S2 LEF; site/track CRT before allocator',adopted=False,qualified=False,
                clock='independent native phi-R; actual view and full incident pin audit required')
        orient=next(o for o,v in H.FLIPS.items()if v==(fx,fy!=lower))
        x=416.016 if h in (0,3) else 86.4
        y=-84.288 if lower else 191.208
        gathers.append(place('u_gather','qkh_head_gather_stage',x,y,324.,21.6,orient,10.812,True))
        tier=1 if h in (1,2) else 2
        y=-28.08*tier-.048 if lower else 129.6+5.448+28.08*(tier-1)
        scores.append(place('u_s2','qkh_head_sstage',432.,y,*score_size,ectl['orient'],score_cy))
    assert len(gathers)==len(scores)==128
    return dict(gather_reservations=gathers,score_return_reservations=scores,
        fixed_cycles=dict(input=4,score_return=2,added_vs_rawR4=6,added_vs_N3=2),
        gather_outline_um=[324,21.6],gather_pitch_um=.192,
        gather_gross_two_track_fraction=1575*.096/324,
        gather_local_two_track_fraction=.5,
        physical_obligations=['actual NS gather route and local PG/OBS cut audit',
            'all ABC->gather->T1->T2 and score->S1->S2->C native paths',
            'actual T1/S1 homes, source-current full N4+M2 RTL binding',
            'full8192 composition and static compiler6-edge cost'])
