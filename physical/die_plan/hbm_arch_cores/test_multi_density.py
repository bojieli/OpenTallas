"""Native multi-port density contracts reject stale/missing roots rather than bypass CTS hold."""
import importlib.util
import json
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('coregen_multidensity',HERE/'gen_core_kit_hbm.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def contract(tmp_path,**changes):
    x=dict(schema='opentallas.hbm_multi_density.v1',module='vms',clock_ports=['clk','clk_m0'],
           layout='density',review=dict(verdict='PASS'),common_alignment=True,merge_roots=False)
    x.update(changes);p=tmp_path/'contract.json';p.write_text(json.dumps(x));return p

def test_exact_roots_and_both_planned_layouts(tmp_path):
    for mode in ['density','columns']:
        c=m.multiport_density_contract(contract(tmp_path,layout=mode),'vms',['clk_m0','clk'])
        assert c['layout']==mode and len(c['sha256'])==64

@pytest.mark.parametrize('change',[
    dict(clock_ports=['clk']),dict(clock_ports=['clk','clk','clk_m0']),dict(module='old'),
    dict(review=dict(verdict='FAIL')),dict(common_alignment=False),dict(merge_roots=True),dict(layout='blind'),
])
def test_reject_missing_stale_or_unreviewed_native_contract(tmp_path,change):
    with pytest.raises(ValueError,match='MULTIPORT_CTS_HOLD'):
        m.multiport_density_contract(contract(tmp_path,**change),'vms',['clk','clk_m0'])
