"""A queued branch object is fetched before retrying the unchanged wave gate."""
import autopilot as A
import canary_gate as G

SHA='a'*40
ROW=dict(src='codex/new-kit@'+SHA)
ERR=(False,'source integrity error: cannot compare kit flow with canary reference')


def exercise(monkeypatch, *, final=(True,'matching NO-REGRESSION'), present=False, fetch_ok=True):
    calls=[];state=dict(present=present,assess=0)
    def assess(*args):
        state['assess']+=1
        return ERR if state['assess']==1 else final
    def shell(cmd,**kwargs):
        calls.append(cmd)
        if 'fetch' in cmd:
            state['present']=fetch_ok;return (0 if fetch_ok else 1),'',''
        assert 'rev-parse' in cmd
        return (0,SHA,'') if state['present'] else (1,'','missing')
    monkeypatch.setattr(G,'assess',assess);monkeypatch.setattr(A,'sh',shell)
    return A.canary_wave_gate(ROW),calls,state


def test_missing_published_source_is_fetched_then_gate_rechecks(monkeypatch):
    result,calls,state=exercise(monkeypatch)
    assert result==(True,'matching NO-REGRESSION') and state['assess']==2
    assert any(c[-3:]==['-q','origin','codex/new-kit'] for c in calls)
    assert all(SHA+'^{commit}' in c for c in calls if 'rev-parse' in c)


def test_measured_regression_after_fetch_stays_held(monkeypatch):
    reg=(False,'matching reference REGRESSION')
    result,calls,state=exercise(monkeypatch,final=reg)
    assert result==reg and state['assess']==2


def test_fetch_failure_or_unrelated_integrity_failure_stays_held(monkeypatch):
    result,calls,state=exercise(monkeypatch,fetch_ok=False)
    assert result==ERR and state['assess']==1
    result,calls,state=exercise(monkeypatch,present=True)
    assert result==ERR and state['assess']==1 and not any('fetch' in c for c in calls)


def test_normal_canary_result_never_fetches(monkeypatch):
    monkeypatch.setattr(G,'assess',lambda *a:(True,'advisory reference pending'))
    monkeypatch.setattr(A,'sh',lambda *a,**k:(_ for _ in ()).throw(AssertionError('unexpected git call')))
    assert A.canary_wave_gate(ROW)==(True,'advisory reference pending')
