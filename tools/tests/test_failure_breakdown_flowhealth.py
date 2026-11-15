import importlib.util, os
spec = importlib.util.spec_from_file_location('fb', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'failure_breakdown.py'))
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)


def test_provisional_prefix_does_not_hide_the_class():
    """FLOW-HEALTH-1 11-15: 'PROVISIONAL[...] <class text>' cut at 240 chars labelled 12 kit_rtl rows 'other flow error'"""
    prov = 'PROVISIONAL[' + ','.join('m%d:routed' % i for i in range(30)) + '] resign:none '
    r = {'status': 'FAIL', 'class': 'FLOW', 'reason': prov + 'kit-RTL bind of record names HDL sources that are gone @kit_rtl: preferred HDL source missing: /x.sv'}
    assert fb.label(r) == 'kit input missing'
    r2 = {'status': 'FAIL', 'class': 'FLOW', 'reason': 'unclassified @kit_rtl: boom ' + prov}
    assert fb.label(r2) == 'kit_rtl'


def test_class_first_leaves_plain_text_alone():
    assert fb._class_first('plain text') == 'plain text'
    assert fb._class_first('GRT-ARM[halve] PROVISIONAL[a:x] real') == 'real GRT-ARM[halve] PROVISIONAL[a:x]'


def test_signed_types_are_skipped():
    st = {'kv3_phy', 'kv3_phy_v1'}
    assert fb.signed_type('kv3_phy', st) and fb.signed_type('kv3_phy_v1#12x3/ab', st)
    assert not fb.signed_type('kv3_phy_v2', st)
