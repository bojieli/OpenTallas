"""Bound-only kits retain validation and identical kits without an unused die top."""
import copy
import json
import sys
import time
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import gen_phys as GP
import gen_rtl as GR
import schema as S


def fixture(tmp_path):
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    # An unselected hard type can force the retained, no-generated-wrapper
    # emitter path for comparison: write_rtl skips it and still builds die_top.
    raw['partition_types']['src']['hard']=True
    module=raw['partition_types']['mid']['module']
    rtl=tmp_path/f'{module}.sv'
    rtl.write_text(f'module {module}(input clk,rst_n,input [7:0] cfg_i,output reg [7:0] cfg_o);\n'
                   'always @(posedge clk) cfg_o <= cfg_i;\nendmodule\n')
    fl=tmp_path/'bound.f';fl.write_text(str(rtl)+'\n')
    return raw,fl


def test_actual_bound_kit_outputs_equal_retained_die_emitter_path(tmp_path,monkeypatch,record_property):
    raw,fl=fixture(tmp_path);validate=S.validate;calls=[]
    def counted(plan):
        calls.append(plan)
        return validate(plan)
    monkeypatch.setattr(S,'validate',counted)
    slow=tmp_path/'retained';fast=tmp_path/'bound_only'
    t=time.perf_counter()
    GP.write_phys(raw,slow,types=['src','mid'],kit_rtl={'mid':str(fl)},trial=True,skip_ir=True,rc_cal=False)
    slow_s=time.perf_counter()-t
    t=time.perf_counter()
    GP.write_phys(raw,fast,types=['mid'],kit_rtl={'mid':str(fl)},trial=True,skip_ir=True,rc_cal=False)
    fast_s=time.perf_counter()-t
    assert len(calls)==2 and calls[0] is raw and calls[1] is raw
    before={str(p.relative_to(slow/'mid')):p.read_bytes().replace(str(slow).encode(),b'<OUT>')
            for p in (slow/'mid').rglob('*') if p.is_file()}
    after={str(p.relative_to(fast/'mid')):p.read_bytes().replace(str(fast).encode(),b'<OUT>')
           for p in (fast/'mid').rglob('*') if p.is_file()}
    assert before==after
    assert {'config.mk','constraint.sdc','freeze.json','plan_pins.json'}<=before.keys()
    assert list((slow/'_rtl').glob('*_top.sv'))
    assert not (fast/'_rtl').exists()
    assert (slow/'run_kit.sh').read_bytes()==(fast/'run_kit.sh').read_bytes()
    record_property('retained_seconds',slow_s);record_property('bound_only_seconds',fast_s)
    print(f'BOUND_ONLY_MEASURE retained={slow_s:.6f}s optimized={fast_s:.6f}s kit_files={len(before)} identical')


def test_bound_only_does_not_call_rtl_emitter(tmp_path,monkeypatch):
    raw,fl=fixture(tmp_path)
    monkeypatch.setattr(GR,'write_rtl',lambda *a,**k:pytest.fail('unused die emitter called'))
    assert GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},trial=True,skip_ir=True,rc_cal=False)


def test_bound_only_invalid_plan_still_fails_before_kit_creation(tmp_path,monkeypatch):
    raw,fl=fixture(tmp_path);raw['die']['period_ps']=0
    monkeypatch.setattr(GP,'write_type_kit',lambda *a,**k:pytest.fail('invalid plan reached kit writer'))
    with pytest.raises(GR.GenError,match='plan invalid'):
        GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},trial=True)


def test_mixed_selection_still_emits_generated_wrapper(tmp_path,monkeypatch):
    raw,fl=fixture(tmp_path);emit=GR.write_rtl;seen=[]
    def tracked(*args,**kwargs):
        seen.append(args[3]);return emit(*args,**kwargs)
    monkeypatch.setattr(GR,'write_rtl',tracked)
    monkeypatch.setattr(GP,'write_type_kit',lambda p,t,out,*a,**k:out/t)
    assert GP.write_phys(raw,tmp_path/'out',types=['mid','sink'],kit_rtl={'mid':str(fl)},trial=True)
    assert seen==[['sink']]
    assert (tmp_path/'out/_rtl/tiny_sink_part.sv').is_file()


def landing_fixture(raw):
    # A real declaration-only sidecar for the four physical partitions. No
    # boundary crosses regions in this minimum vehicle; invalid declarations
    # and undeclared bound rings must still fail in Landings/kit_rtl_land_slots.
    return dict(regions=[dict(tag="all", box_um=[0, 0, 3456, 864])], ports=[])


def test_bound_landing_outputs_equal_retained_emitter_path(tmp_path,monkeypatch,record_property):
    raw,fl=fixture(tmp_path);landing=landing_fixture(raw)
    emit=GR.write_rtl;calls=[]
    def tracked(*args,**kwargs):
        calls.append(args[3]);return emit(*args,**kwargs)
    monkeypatch.setattr(GR,'write_rtl',tracked)
    slow=tmp_path/'retained_landing';fast=tmp_path/'bound_landing'
    start=time.perf_counter()
    GP.write_phys(raw,slow,types=['src','mid'],kit_rtl={'mid':str(fl)},landing=landing,
                  trial=True,skip_ir=True,rc_cal=False)
    retained_s=time.perf_counter()-start
    start=time.perf_counter()
    GP.write_phys(raw,fast,types=['mid'],kit_rtl={'mid':str(fl)},landing=landing,
                  trial=True,skip_ir=True,rc_cal=False)
    bound_s=time.perf_counter()-start
    assert calls==[['src']],calls
    def files(out):
        return {str(p.relative_to(out/'mid')):p.read_bytes().replace(str(out).encode(),b'<OUT>')
                for p in (out/'mid').rglob('*') if p.is_file()}
    assert files(slow)==files(fast)
    assert (slow/'run_kit.sh').read_bytes()==(fast/'run_kit.sh').read_bytes()
    assert not (fast/'_rtl').exists()
    record_property('retained_landing_seconds',retained_s)
    record_property('bound_landing_seconds',bound_s)
    print(f'BOUND_LANDING_MEASURE retained={retained_s:.6f}s optimized={bound_s:.6f}s identical')


def test_bound_landing_never_emits_unused_wrappers(tmp_path,monkeypatch):
    raw,fl=fixture(tmp_path)
    monkeypatch.setattr(GR,'write_rtl',lambda *a,**k:pytest.fail('unused landed die emitter called'))
    assert GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},
                         landing=landing_fixture(raw),trial=True,skip_ir=True,rc_cal=False)


def test_bound_landing_invalid_plan_still_fails_before_kit(tmp_path,monkeypatch):
    raw,fl=fixture(tmp_path);raw['die']['period_ps']=0
    monkeypatch.setattr(GP,'write_type_kit',lambda *a,**k:pytest.fail('invalid plan reached kit writer'))
    with pytest.raises(GR.GenError,match='plan invalid'):
        GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},
                      landing=landing_fixture(raw),trial=True)


def test_bound_landing_stale_sidecar_still_fails(tmp_path):
    import clock_landings as CL
    raw,fl=fixture(tmp_path);landing=landing_fixture(raw)
    landing['collector']={'types':{}}
    with pytest.raises(CL.LandingError,match='SIDECAR_STALE'):
        GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},
                      landing=landing,trial=True)
    assert not (tmp_path/'out/mid').exists()


def test_bound_landing_rejects_ring_absent_from_sidecar(tmp_path):
    raw,fl=fixture(tmp_path);rtl=Path(fl.read_text().strip())
    rtl.write_text(rtl.read_text().replace('endmodule',
        "ot_dp_clk_landing_ca #(.W(8), .DEPTH(8)) u_cland_cfg_i ();\nendmodule"))
    with pytest.raises(GR.GenError,match='bound count-aligned rings not declared'):
        GP.write_phys(raw,tmp_path/'out',types=['mid'],kit_rtl={'mid':str(fl)},
                      landing=landing_fixture(raw),trial=True)


def test_bound_landing_still_rejects_mixed_unbound_soft_type(tmp_path):
    raw,fl=fixture(tmp_path)
    with pytest.raises(GR.GenError,match='have no bound RTL'):
        GP.write_phys(raw,tmp_path/'out',types=['mid','sink'],kit_rtl={'mid':str(fl)},
                      landing=landing_fixture(raw),trial=True)
