import copy
import json
from pathlib import Path
import source_follow as S

class AP:
    REPO = '/unused'
    DRY = False
    def __init__(self, root):
        self.AP_DIR=root; self.launches=[]; self.active=set(); self.messages=[]
    def sh(self, cmd, **kw): return (0, "tools/die_plan/gen_phys.py" if "--name-only" in cmd else "a"*40, "")
    def unit_active(self,u): return u in self.active
    def launch_unit(self,*args): self.launches.append(args); self.active.add(args[0]); return True
    def log(self,msg): self.messages.append(msg)

def config():
    return {'dies': {'s81': {'src_sha':'old', 'src':'old/path', 'src_follow': {'enabled':True}}}}

def test_failed_preparation_keeps_old_source(tmp_path):
    ap=AP(tmp_path); cfg=config(); state={}
    S.step(ap,cfg,state)
    result=tmp_path/'source_follow'/'s81'/'old'/('a'*12)/'result.json'
    result.write_text(json.dumps({'verdict':'FAIL','reason':'strict bind errors'}))
    cfg=config(); S.step(ap,cfg,state)
    assert cfg['dies']['s81']['src_sha']=='old'
    assert 'held: strict bind errors' in ap.messages[-1]

def test_success_switches_once_and_operator_update_wins(tmp_path):
    ap=AP(tmp_path); cfg=config(); state={}; S.step(ap,cfg,state)
    result=tmp_path/'source_follow'/'s81'/'old'/('a'*12)/'result.json'
    result.write_text(json.dumps({'verdict':'PASS','override':{'src_sha':'a'*40,'src':'new/path'}}))
    S.step(ap,cfg,state)
    assert cfg['dies']['s81']['src']=='new/path'
    cfg=config(); S.step(ap,cfg,state)
    assert cfg['dies']['s81']['src']=='new/path'
    cfg=config(); cfg['dies']['s81']['src_sha']='operator'
    S.apply_ready(cfg,state)
    assert cfg['dies']['s81']['src_sha']=='operator'

def test_inflight_snapshot_does_not_duplicate(tmp_path):
    ap=AP(tmp_path); cfg=config(); state={}
    S.step(ap,cfg,state); S.step(ap,cfg,state)
    assert len(ap.launches)==1


def test_unrelated_merge_does_not_rebind(tmp_path):
    ap=AP(tmp_path); cfg=config(); cfg['dies']['s81']['src_follow']['watch']=['physical/die_plan/s81/']
    S.step(ap,cfg,{})
    assert not ap.launches


def test_main_advances_while_preparing_activates_completed_old_tip(tmp_path):
    ap=AP(tmp_path); state={}; cfg=config()
    S.step(ap,cfg,state)
    rec=state['source_follow']['s81']; first_result=Path(rec['result'])
    first_result.write_text(json.dumps({'verdict':'PASS','override':{'src_sha':'a'*40,'src':'prepared-a'}}))
    ap.active.clear()
    def newer(cmd, **kw):
        return (0, "tools/die_plan/gen_phys.py" if "--name-only" in cmd else "b"*40, "")
    ap.sh=newer
    cfg=config(); S.step(ap,cfg,state)
    assert cfg['dies']['s81']['src_sha']=='a'*40
    assert cfg['dies']['s81']['src']=='prepared-a'
    assert len(ap.launches)==2
    assert state['source_follow']['s81']['tip']=='b'*40
    assert state['source_follow']['s81']['ready']['src_sha']=='a'*40


def test_opaque_library_body_change_keeps_interface_but_width_change_does_not(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
    import bind_elab
    old = 'module leaf(input wire [7:0] d, output wire [7:0] q); assign q=d; endmodule'
    body = "module leaf(input wire [7:0] d, output wire [7:0] q); assign q=d ^ 8'd1; endmodule"
    wider = 'module leaf(input wire [8:0] d, output wire [7:0] q); assign q=d[7:0]; endmodule'
    assert S.same_library_interface(bind_elab, old, body, tmp_path/'body')
    assert not S.same_library_interface(bind_elab, old, wider, tmp_path/'width')


def test_exact_readset_does_not_expand_rtl_search_roots():
    metadata={'full':['/old/wt/rtl/kv/full.sv'], 'lib':['/old/wt/rtl/kv/macro.sv']}
    recipe={'rtl_roots':['rtl'], 'files':['rtl/kv/explicit.sv']}
    used=S.used_hdl_paths(['/old/bind/structural_full/die.sv'],recipe,metadata)
    assert used=={'rtl/kv/full.sv','rtl/kv/macro.sv','rtl/kv/explicit.sv'}
    changed={'rtl/s81/unrelated.sv','rtl/hbm/unrelated.sv','rtl/kv/full.sv','rtl/kv/macro.sv'}
    assert changed & used=={'rtl/kv/full.sv','rtl/kv/macro.sv'}


def test_opaque_parameter_default_change_is_not_same_interface(tmp_path):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
    import bind_elab
    old='module leaf #(parameter W=8)(input wire [W-1:0] d, output wire [W-1:0] q); assign q=d; endmodule'
    new=old.replace('W=8','W=9')
    assert not S.same_library_interface(bind_elab,old,new,tmp_path/'param')
