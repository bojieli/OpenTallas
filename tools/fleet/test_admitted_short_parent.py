from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

M = SourceFileLoader('short_parent_reconcile', str(Path(__file__).with_name('ot-heavy-reconcile'))).load_module()


@pytest.mark.parametrize('children,cgroup,admitted', [
    ('456', '0::/user.slice/oth-ubuntu-123-1793600622.scope\n', True),
    ('456', '0::/user.slice/oth-ubuntu-123-1793600622.scope/subgroup\n', True),
    ('456', '0::/user.slice/oth-ubuntu-999-1793600622.scope\n', False),
    ('456', '0::/user.slice/session-123.scope\n', False),
    ('456', '', False), ('', '', False)])
def test_kernel_scope_must_belong_to_exact_launcher(monkeypatch,children,cgroup,admitted):
    files={'/proc/123/task/123/children':children,'/proc/456/cgroup':cgroup}
    monkeypatch.setattr(M,'rd',lambda path: files.get(path,''))
    assert M.admitted_launcher('123') is admitted


def test_admitted_short_parent_is_absent_from_all_waiter_views(monkeypatch):
    cmd='\0'.join(['bash','/usr/local/bin/ot-heavy','--mem','4','--tag','test','--','python3','repair.py',''])
    monkeypatch.setattr(M.os,'listdir',lambda path:['123'])
    monkeypatch.setattr(M,'rd',lambda path:cmd if path=='/proc/123/cmdline' else '')
    monkeypatch.setattr(M,'admitted_launcher',lambda pid:True)
    assert M.waiters({}) == ([],[])
    assert M.prio_waiters({}) == []
    assert M.die_waiter_rows({}) == []


def test_real_unstarted_waiter_stays_in_generic_queue(monkeypatch):
    cmd='\0'.join(['bash','/usr/local/bin/ot-heavy','--mem','4','--','python3','repair.py',''])
    monkeypatch.setattr(M.os,'listdir',lambda path:['123'])
    monkeypatch.setattr(M,'rd',lambda path:cmd if path=='/proc/123/cmdline' else '')
    monkeypatch.setattr(M,'admitted_launcher',lambda pid:False)
    monkeypatch.setattr(M,'admit_size',lambda *a:None)
    monkeypatch.setattr(M,'classify',lambda *a:'repair')
    assert M.waiters({}) == ([4],[4])
