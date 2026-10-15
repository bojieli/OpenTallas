from pathlib import Path
import head_placement_lattice as L


VIEW=Path(__file__).resolve().parents[2]/'physical/ref_tile/qkh_head_chunk_stage/views/qkh_head_chunk_stage/qkh_head_chunk_stage.lef'


def test_actual535_all_signal_rectangles_on_site_and_track_after_each_mirror():
    macro=L.lef(str(VIEW))
    for orient in ('R0','MX','MY','R180'):
        xy,rule=L.snap(macro,orient,(2530.123,2678.328))
        nm=[round(v*1000)for v in xy]
        assert nm[0]%54==nm[1]%270==0
        result=L.C.check_placement(macro,orient,*nm)
        assert sum(r['offtrack']for r in result['layers'].values())==0
        assert rule['x']['joint_period_nm']==432
        assert rule['y']['joint_period_nm']==2160
        assert rule['y']['legal_origins_mod_joint_nm']==([1080]if orient in('MX','R180')else[0])


def test_six_nm_origin_mutant_exposes_actual535_pin_track_failure():
    macro=L.lef(str(VIEW));xy,_=L.snap(macro,'MY',(2530.123,2678.328))
    result=L.C.check_placement(macro,'MY',round(xy[0]*1000)+6,round(xy[1]*1000))
    assert sum(r['offtrack']for r in result['layers'].values())>0
