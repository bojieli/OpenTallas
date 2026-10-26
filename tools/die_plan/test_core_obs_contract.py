"""A coarse/default obstruction cannot grant layers occupied by a core contract."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import die_trial
import g2


def test_parent_cannot_mask_core_m7():
    t={'contents':[{'inst':'u','origin_um':[0,0],'outline_um':[40,40],'obs_max':'M5'}],
       'hard_cores':[{'inst':'u_a','origin_um':[4,4],'outline_um':[10,10],'obs_max':'M7'}]}
    assert g2.probe_blockages(t)[0]['obs_max']=='M7'
    t['contents'][0]['obs_max']='M8'
    assert g2.probe_blockages(t)[0]['obs_max']=='M8'


def test_die_trial_keeps_stricter_declared_and_real_view(monkeypatch):
    t={'hard_cores':[{'module':'leaf','origin_um':[0,0],'outline_um':[10,20],'lef':'view.lef','obs_max':'M7'}]}
    monkeypatch.setattr(die_trial,'lef_top_layer',lambda path:'M5')
    assert die_trial.core_obs(t)[0][4:] == ('M7','leaf',True)
    t['hard_cores'][0]['obs_max']='M5'
    monkeypatch.setattr(die_trial,'lef_top_layer',lambda path:'M7')
    assert die_trial.core_obs(t)[0][4:] == ('M7','leaf',True)


def test_declared_core_without_view_is_not_a_real_view(monkeypatch):
    t={'hard_cores':[{'module':'leaf','origin_um':[0,0],'outline_um':[10,20],'obs_max':'M7'}]}
    monkeypatch.setattr(die_trial,'lef_top_layer',lambda path:None)
    assert die_trial.core_obs(t)[0][4:] == ('M7','leaf',False)
    t['hard_cores'][0].pop('obs_max')
    assert die_trial.core_obs(t)[0][4:] == ('M5','leaf',False)
