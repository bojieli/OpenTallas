"""Durable exact-source proof integrates with normal source-only FG lifecycle."""
import copy
import pathlib
import sys
import time
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kit_wave as kw

def fixture(tmp_path):
    cfg={"dies":{"s81":{"src":"/immutable/d2","src_sha":"new","_plan_sha":"plan",
                       "gen_hosts":["epyc9","epyc10"]}}}
    entry=dict(die="s81",stage="src_manifest",state="probe",kind="",fams=["leaf"],
               inp="old-open",inp_probe="old-probe",probe={"*":"obsolete"})
    snapshot=dict(entry,stage="kit_snap")
    st={"items":{"old":dict(die="s81",item="obsolete",status="CANCELLED")},
        "flow_guard":{"open":{"source":entry,"snapshot":snapshot},"fails":[["immutable-fail"]]}}
    kw.FG.fg_state(st)
    ap=SimpleNamespace(AP_DIR=tmp_path,HUB_NAME="intel2",log=lambda s:None)
    marker=lambda die:dict(tree="/immutable/d2",manifest_hash="hash",smoke="PASS")
    def read(root,ident):
        return dict(identity=ident,state="ok",full_ok=True,running=False,links_t=time.time(),
                    details=[dict(host=h,rc=0,basis="links") for h in ident["hosts"]])
    return cfg,st,ap,marker,read

def call(f,read=None,ready=True):
    cfg,st,ap,marker,default=f
    return kw.verified_source_probes(ap,cfg,st,"s81",lambda d,t:ready,marker,read or default)

def test_matching_fresh_receipt_refreshes_inactive_obsolete_probe_source_only(tmp_path):
    f=fixture(tmp_path);cfg,st,ap,marker,read=f;before=copy.deepcopy(st)
    assert call(f)
    assert "source" not in st["flow_guard"]["open"]
    assert st["flow_guard"]["open"]["snapshot"]==before["flow_guard"]["open"]["snapshot"]
    assert st["flow_guard"]["fails"]==before["flow_guard"]["fails"]
    hist=st["flow_guard"]["source_probe_history"][0]
    assert hist["previous"]==before["flow_guard"]["open"]["source"]
    assert hist["inp"]==kw.breaker_inputs(cfg,"s81")
    assert "source" in st["flow_guard"]["probation"]

@pytest.mark.parametrize("status",["RUNNING","LAUNCHING","ENQUEUED","ROUTE-HELD","UNKNOWN"])
def test_active_or_unknown_old_producer_is_preserved(tmp_path,status):
    f=fixture(tmp_path);st=f[1];st["items"]["old"]["status"]=status;before=copy.deepcopy(st)
    assert not call(f)
    assert st==before

@pytest.mark.parametrize("change",[
    {"state":"bad"},{"state":"cheap"},{"full_ok":False},{"running":True},
    {"links_t":0},{"links_t":1},{"identity":{"tree":"wrong"}},
    {"details":[{"host":"epyc9","rc":0}]},
    {"details":[{"host":"epyc9","rc":0},{"host":"epyc10","rc":1}]},
])
def test_wrong_stale_running_or_failed_receipt_never_changes_state(tmp_path,change):
    f=fixture(tmp_path);before=copy.deepcopy(f[1]);read=f[4]
    def wrong(root,ident):
        p=read(root,ident);p.update(change);return p
    assert not call(f,wrong)
    assert f[1]==before

def test_tree_not_ready_and_missing_old_identity_fail_closed(tmp_path):
    f=fixture(tmp_path);before=copy.deepcopy(f[1]);assert not call(f,ready=False);assert f[1]==before
    del f[1]["flow_guard"]["open"]["source"]["inp_probe"];before=copy.deepcopy(f[1])
    assert not call(f);assert f[1]==before

def test_current_input_claim_needs_no_refresh_but_only_source_closes(tmp_path):
    f=fixture(tmp_path);f[1]["flow_guard"]["open"]["source"]["inp_probe"]=kw.breaker_inputs(f[0],"s81")
    assert call(f)
    assert set(f[1]["flow_guard"]["open"])=={"snapshot"}
    assert not f[1]["flow_guard"].get("source_probe_history")

def test_completed_content_fallback_uses_last_actual_result_per_host(tmp_path):
    f=fixture(tmp_path);read=f[4]
    def fallback(root,ident):
        p=read(root,ident);p["details"]=[dict(host="epyc9",rc=2,basis="cache-miss")]+p["details"];return p
    assert call(f,fallback)
