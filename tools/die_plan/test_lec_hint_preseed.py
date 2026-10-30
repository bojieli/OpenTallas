"""Prior hints may seed discovery; all reset and induction obligations remain."""
import inspect
import lec
from test_lec_memory_layout import _seq, _sim_prove


def design(tmp_path, mutant=False):
    g,gm=_seq(tmp_path,"g",["rn","en","x"],["ga","o"],
       lambda m,l:{"ga":m.AND(l["rn"],l["x"]),"o":l["ga"]})
    t,tm=_seq(tmp_path,"t",["rn","en","x"],["ta","o"],
       lambda m,l:{"ta":m.AND(l["rn"],l["x"]^int(mutant)),"o":l["ta"]})
    return lec.Lec(g,gm,t,tm)


def run(tmp_path,monkeypatch,mutant=False,hint=None):
    L=design(tmp_path,mutant)
    L.preseed_hints=hint or [["gate","ff:u_dut.ta",["eq","gold","ff:u_dut.ga",0]]]
    monkeypatch.setattr(lec,"prove",_sim_prove)
    log=[]
    lec.correspond(L,tmp_path,100,log,rounds=0,sim_iters=0,words=1)
    m,_=L.build(with_compare=True,with_hyp=True)
    return L,_sim_prove(m),log


def test_old_hint_is_proved_before_final_compare(tmp_path,monkeypatch):
    L,status,log=run(tmp_path,monkeypatch)
    assert status and set(status.values())=={"proved"}
    assert any("untrusted hints preseeded" in s for s in log)


def test_wrong_old_hint_is_dropped_and_mutant_still_fails(tmp_path,monkeypatch):
    L,status,log=run(tmp_path,monkeypatch,True)
    assert "differs" in status.values()
    assert ("gate","ff:u_dut.ta") not in L.hyp


def test_missing_old_hint_key_gets_no_assumption(tmp_path,monkeypatch):
    L,status,log=run(tmp_path,monkeypatch,True,
        [["gate","ff:u_dut.missing",["eq","gold","ff:u_dut.ga",0]]])
    assert "differs" in status.values()
    assert ("gate","ff:u_dut.missing") not in L.hyp


def test_default_opt_in_and_final_hint_refinement_remain():
    s=inspect.getsource(lec.check)
    assert 'os.environ.get("OT_LEC_HINTS_PRESEED") == "1"' in s
    assert s.index('L.preseed_hints = supplied') < s.index('correspond(L, out')
    assert s.index('correspond(L, out') < s.index('apply_hints(L, json.loads(hf.read_text())')


def test_opt_in_is_forwarded_into_native_docker_run():
    s=inspect.getsource(lec.via_docker)
    assert 'if os.environ.get("OT_LEC_HINTS_PRESEED") == "1":' in s
    assert '["-e", "OT_LEC_HINTS_PRESEED=1"]' in s


def test_hint_only_mode_disables_search_but_not_existing_proof_gates():
    s=inspect.getsource(lec.check)
    assert 'os.environ.get("OT_LEC_HINTS_ONLY") == "1"' in s
    assert 'OT_LEC_HINTS_ONLY requires explicit preseed mode and a hints file' in s
    assert 'correspond(L, out, conflicts, log, rounds=0, sim_iters=0)' in s
    assert s.index('rounds=0, sim_iters=0)') < s.index('apply_hints(L, json.loads(hf.read_text())')
    assert 'noreset_filter(L, log' in s and 'kept_registers(L, kf)' in s
    assert 'prove(m, out, conflicts, log, tag="miter")' in s
    assert 'OT_LEC_HINTS_ONLY=1' in inspect.getsource(lec.via_docker)
