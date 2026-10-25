"""Only explicitly M6-capped Qwen SU cores may carry straight M7 FT legs."""
from tools.die_plan import ft_sites

SLOT=dict(in_face='N',out_face='S',layers=['M7'])

def test_declared_su_m6_ceiling_allows_corridor():
    assert ft_sites.m7_over_core(SLOT,'slw_su_l1',{'hard_cores':[{'obs_max':'M6'}]})

def test_m7_or_unknown_macro_wall_is_not_authorized():
    for core in [{'obs_max':'M7'},{}]:
        assert not ft_sites.m7_over_core(SLOT,'slw_su_l1',{'hard_cores':[core]})

def test_other_design_type_or_nonvertical_route_is_not_authorized():
    for name in ['leaf_t12','q_sm0','slw_st_a']:
        assert not ft_sites.m7_over_core(SLOT,name,{'hard_cores':[{'obs_max':'M6'}]})
    assert not ft_sites.m7_over_core(dict(SLOT,out_face='E'),'slw_su_l1',{'hard_cores':[{'obs_max':'M6'}]})
