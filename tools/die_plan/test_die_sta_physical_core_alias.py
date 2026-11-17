"""Exact physical aliases and clock-qualified endpoints of signed early taps."""
from unittest.mock import patch
import die_sta_related as R
from test_die_sta_core_insertion import REG


def test_early_physical_instance_is_not_also_put_on_nearest_generic_tap():
    h=dict(inst='logical',physical_inst='u_bound.u_real',physical_master='m',module='m',outline_um=[10,10])
    plan=dict(partitions=[dict(name='p',type='T')],partition_types={'T':dict(hard_cores=[h])})
    taps={'std':dict(part='p')}
    model=dict(name='core:m',real=True,meta=dict(verdict='SIGNED'),etm={},part_delay_ps=0)
    cm={('p','logical'):('m','std',1,None)}
    with patch.object(R,'map_cores_to_taps',return_value=cm),patch.object(R,'core_view_model',return_value=model),patch.object(R,'core_outlines',return_value={('p','logical'):[10,10]}):
        views,cov=R.build_views(plan,taps,'FF',REG,250,{'m':'view'},{},2,0,exclude={('p','u_bound.u_real')})
        assert cov['early_core_tap_instances']==1 and cov['core_instances_real']==0
        assert not any(m.get('real') for m in views['std'])
        # Another instance's explicit root cannot suppress this one.
        views,cov=R.build_views(plan,taps,'FF',REG,250,{'m':'view'},{},2,0,exclude={('p','u_bound.u_other')})
        assert cov['early_core_tap_instances']==0 and cov['core_instances_real']==1


def test_signed_clock_qualified_endpoint_matches_only_its_exact_clock():
    taps={'t':dict(part='p')};plan=dict(partitions=[dict(name='p',type='T')])
    ecm={'t':[dict(module='m',pin='clk')]}
    def labels(name,verdict='SIGNED'):
        return R.missing_views({'t':[dict(name=name,real=True,meta=dict(verdict=verdict))]},taps,plan,ecm)['t']
    assert labels('core:m:clk')==[]
    assert labels('core:m:fclk')==['core:m']
    assert labels('core:m:clk','FAIL')
    assert labels('core:m')==[]  # existing single-root provider remains valid
