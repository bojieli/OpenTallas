"""A supply-window trim must not move or rename an explicitly anchored lattice."""
import copy
import pytest
from phy_bumps import sites


def domain():
    return dict(nets=['VDDPHY_SW', 'VSS'], rect_um=[17.28,26060.4,1870.56,27032.4],
                bumps=dict(rect_um=[17.28,26060.4,1870.56,27032.4],pitch_um=45,
                           origin_um=[50.4,26096.4],counts=[41,21]))


def test_trim_retains_all_existing_sites_and_parity():
    trimmed = domain()
    old = copy.deepcopy(trimmed)
    old['rect_um'][2] = old['bumps']['rect_um'][2] = 1883.52
    old['bumps'].pop('origin_um');old['bumps'].pop('counts')
    assert sites(trimmed) == sites(old)
    assert len(sites(trimmed)) == 861
    assert sites(trimmed)[0] == ('VDDPHY_SW',33.12,36.0)
    assert sites(trimmed)[1][0] == 'VSS'
    rephased = copy.deepcopy(trimmed)
    rephased['bumps'].pop('origin_um');rephased['bumps'].pop('counts')
    assert sites(rephased) != sites(trimmed)


def test_legacy_centred_sites_unchanged():
    d = domain();d['bumps'].pop('origin_um');d['bumps'].pop('counts')
    r=d['bumps']['rect_um'];p=d['bumps']['pitch_um'];x0,y0,*_=d['rect_um']
    nx,ny=int((r[2]-r[0])//p),int((r[3]-r[1])//p)
    sx=(r[0]+r[2]-(nx-1)*p)/2-x0;sy=(r[1]+r[3]-(ny-1)*p)/2-y0
    assert sites(d)==[(d['nets'][(i+j)%2],round(sx+i*p,3),round(sy+j*p,3))for i in range(nx)for j in range(ny)]


@pytest.mark.parametrize('change',[
    {'counts':[True,21]}, {'counts':[0,21]}, {'counts':[42,21]},
    {'origin_um':[float('nan'),26096.4]}, {'origin_um':[0,26096.4]},
    {'origin_um':[50.4005,26096.4]}, {'pitch_um':45.0005},
    {'exclude_um':[[49,26095,51,26097]]},
])
def test_invalid_anchor_fails_without_dropping_or_moving_sites(change):
    d=domain();d['bumps'].update(change)
    with pytest.raises(ValueError):sites(d)


@pytest.mark.parametrize('key',['origin_um','counts'])
def test_anchor_fields_are_required_together(key):
    d=domain();d['bumps'].pop(key)
    with pytest.raises(ValueError):sites(d)
