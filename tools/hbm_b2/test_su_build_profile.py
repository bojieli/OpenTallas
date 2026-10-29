"""Explicit per-slice source profiles preserve body, addresses and role ownership."""
import re
import pytest
from su_build_profile import apply_profile,SLICE


def source():
    return '\n'.join(f'  ot_hbm_su_static_pgslice_lg #(.QID({qid}), .G({g}), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0)) su_{role}{g} (\n    .payload(actual_{role}_{g}[127:0])\n  );' for role,qid in [('NW',2),('NE',3)] for g in range(4))


@pytest.mark.parametrize('profile,delta,ii', [('m5a3w1',3,{'2':19,'3':1,'6':37,'7':15}),('m5a4w1',4,{'2':22,'3':1,'6':55,'7':24})])
def test_only_explicit_eight_profiles_change(profile,delta,ii):
    old=source();new,r=apply_profile(old,profile)
    assert SLICE.sub('PROFILE',old)==SLICE.sub('PROFILE',new)
    assert len(r['slices'])==8 and r['side_hardware']==dict(mlat=3,alat=3)
    for row in r['slices']:
        assert row['linear_cycle_delta']==delta and row['bank_commit_cycle_delta']==1
        assert row['target_side_ii']==ii
    assert new.count('.WCOPY(1)')==8


@pytest.mark.parametrize('mutant', ['missing','wrong_qid','wrong_group','extra_south','unknown_profile'])
def test_profile_refuses_incomplete_source(mutant):
    old=source();profile='m5a4w1'
    if mutant=='missing':old=old.replace(' su_NW0 (',' su_missing (')
    if mutant=='wrong_qid':old=old.replace('.QID(2)','.QID(0)',1)
    if mutant=='wrong_group':old=old.replace('.G(0)','.G(1)',1)
    if mutant=='extra_south':old+='\n  ot_hbm_su_static_pgslice_lg #(.QID(0), .G(0), .MLAT(4), .ALAT(4), .LEAF(1)) su_SW0 (\n  );'
    if mutant=='unknown_profile':profile='default'
    with pytest.raises(ValueError):apply_profile(old,profile)
