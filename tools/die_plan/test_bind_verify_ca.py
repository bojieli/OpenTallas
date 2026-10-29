from types import SimpleNamespace as N
from bind import Graph, Rules
from bind_verify import landing_transport_rules


def graph(module, k=2, wrong_source=False):
    leaf=N(path='source',module='leaf',kind='leaf',ports={'q':[10]},dirs={'q':'output'},params={})
    ports={'d':[11 if wrong_source else 10],'q':[20],'clk':[1],'fclk':[2],'rst_n':[3],'ready':[21],'fault':[22]}
    if module!='ot_dp_clk_landing':ports['t_rst_n']=[4]
    if module.endswith('cas'):ports['strap_k']=list(reversed(list(f'{k:06b}')))
    ring=N(path='ring',module=module,kind='leaf',ports=ports,dirs={},params={'K':k})
    flat=N(cells=[leaf,ring],const_drivers={},top_ports={})
    errors=[];g=Graph(flat,Rules({'transport':landing_transport_rules()}),errors)
    return g,errors


def test_both_ca_forms_trace_the_actual_input_and_count():
    for module in ('ot_dp_clk_landing','ot_dp_clk_landing_ca','ot_dp_clk_landing_cas'):
        g,err=graph(module);assert not err
        assert g.source(20)==('pin',0,'q',0,3 if module=='ot_dp_clk_landing' else 2)
        # MUTANT: a disconnected actual data input is never reclassified as its planned source.
        bad,_=graph(module,wrong_source=True);assert bad.source(20)[0]=='undriven'


def test_nonconstant_ca_count_is_rejected():
    g,err=graph('ot_dp_clk_landing_cas');g.F.cells[1].ports['strap_k'][0]=99
    g.source(20);assert any('RULE_STAGES_PORT' in e for e in err)
