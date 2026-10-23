"""FT-KV-DIE 10-23: OT_KV_AHUB_FR_REALIGN -- a ks_pvfst pad from the fixed-offset hub fr bundle is accepted only when the
PVFIN start alignment is re-solved after it without another pvfst pad and the hub offsets hold exactly; default refuses."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_die as K

T = dict(FR_OFS=-7, AP_OFS=[-36, -36, -34, -35])


def _m(pads):
    return dict(bundle_eq=dict(bundles={'A.hub_fr': dict(members={'kvs_attn.pvfst->pvfin': dict(stages=12, pads=pads)})}),
                pvfin_align=dict(before=[0, 0], pads=dict(pvfst=0, pvp_0=0, pvp_1=0), after=[0, 0]))


def _realign(pv_pads):
    def f(m):
        m = dict(m); m['pvfin_align'] = dict(before=[-23, -23], pads=pv_pads, after=[0, 0]); return m
    return f


def _ages(fr, ap=T['AP_OFS']):
    return lambda m: dict(FR_OFS=fr, AP_OFS=list(ap))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def test_no_pad_is_untouched():
    m = _m(0)
    assert K.ahub_fr_realign(m, T, None, None, on=False) is m
    assert K.ahub_fr_realign(m, T, None, None, on=True) is m


def test_default_refuses_pvfst_pad():
    assert _raises(lambda: K.ahub_fr_realign(_m(23), T, _realign({}), _ages(-7), on=False))


def test_realign_accepts_exact():
    m = K.ahub_fr_realign(_m(23), T, _realign(dict(pvfst=0, pvp_0=23, pvp_1=23)), _ages(-7), on=True)
    assert m['pvfin_align']['ahub_fr_realign']['pvfst_pads'] == 23


def test_realign_fails_closed():
    assert _raises(lambda: K.ahub_fr_realign(_m(23), T, _realign(dict(pvfst=1, pvp_0=23, pvp_1=23)), _ages(-7), on=True))
    assert _raises(lambda: K.ahub_fr_realign(_m(23), T, _realign(dict(pvfst=0, pvp_0=23, pvp_1=23)), _ages(-6), on=True))
    assert _raises(lambda: K.ahub_fr_realign(_m(23), T, _realign(dict(pvfst=0)), _ages(-7, [-36, -36, -34, -34]), on=True))


if __name__ == '__main__':
    for t in (test_no_pad_is_untouched, test_default_refuses_pvfst_pad, test_realign_accepts_exact, test_realign_fails_closed):
        t()
    print('PASS')
