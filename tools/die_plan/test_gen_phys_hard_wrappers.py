"""Explicit hard-wrapper opt-in cannot synthesize a naked hard-IP shell."""
import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as GP
import gen_rtl as GR


def fixture(tmp_path, monkeypatch):
    raw = json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    raw['partition_types']['mid']['hard'] = True
    module = raw['partition_types']['mid']['module']
    rtl = tmp_path/f'{module}.sv'
    rtl.write_text(f'module {module}(); endmodule\n')
    fl = tmp_path/'kit.f'; fl.write_text(str(rtl)+'\n')
    def emit(raw, out, *a, **kw):
        out.mkdir(parents=True, exist_ok=True)
        (out/'ot_dp_cells.sv').write_text('')
        return []
    monkeypatch.setattr(GR, 'write_rtl', emit)
    monkeypatch.setattr(GP, 'type_macros', lambda p,t:[('u_core','phy','phy.lef','phy_tt.lib',0,0,'R0')])
    seen=[]
    def kit(p,t,out,*a,**kw):
        seen.append((t,p.types[t]['hard'])); return out/t
    monkeypatch.setattr(GP,'write_type_kit',kit)
    return raw,fl,seen


def test_default_skips_hard_and_optin_preserves_plan(tmp_path,monkeypatch):
    raw,fl,seen=fixture(tmp_path,monkeypatch)
    before=copy.deepcopy(raw)
    assert GP.write_phys(raw,tmp_path/'off',types=['mid'],trial=True,kit_rtl={'mid':str(fl)}) == []
    assert GP.write_phys(raw,tmp_path/'on',types=['mid'],trial=True,kit_rtl={'mid':str(fl)},hard_wrappers=['mid']) == [tmp_path/'on'/'mid']
    assert seen == [('mid',True)] and raw == before


@pytest.mark.parametrize('kwargs,match',[
    ({'types':None,'kit_rtl':None},'explicit --types'),
    ({'types':['mid'],'kit_rtl':{}},'explicit --types'),
    ({'hard_wrappers':['unknown']},'existing hard type'),
])
def test_unbound_or_unknown_refused(tmp_path,monkeypatch,kwargs,match):
    raw,fl,_=fixture(tmp_path,monkeypatch)
    args=dict(types=['mid'],kit_rtl={'mid':str(fl)},hard_wrappers=['mid'])
    args.update(kwargs)
    with pytest.raises(GR.GenError,match=match):
        GP.write_phys(raw,tmp_path/'bad',trial=True,**args)


def test_no_macro_refused(tmp_path,monkeypatch):
    raw,fl,_=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(GP,'type_macros',lambda p,t:[])
    with pytest.raises(GR.GenError,match='placed macro'):
        GP.write_phys(raw,tmp_path/'bad',types=['mid'],kit_rtl={'mid':str(fl)},hard_wrappers=['mid'],trial=True)
