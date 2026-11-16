import copy
import pytest
from reset_consumers import localize, ResetConsumerError

TEXT='''module fixture(input wire clk, arst_n, input wire [7:0] d, input wire ea);
wire rst_root_n, a0, rst_n_t5, b0, rst_n_t14;
wire rst_n = rst_n_t5;
ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
ot_dp_rrelay a (.clk(clk), .d(rst_root_n), .q(a0));
ot_dp_rrelay a1 (.clk(clk), .d(a0), .q(rst_n_t5));
ot_dp_rrelay b (.clk(clk), .d(rst_root_n), .q(b0));
ot_dp_rrelay b1 (.clk(clk), .d(b0), .q(rst_n_t14));
ot_dp_st #(.W(8)) u_bin_i (.clk(clk), .rst_n(rst_n), .d(d), .ea(ea), .q(q), .eq(eq));
native_core u_core (.clk(clk), .rst_n(rst_n), .data(d));
endmodule
'''
TREE={'relays':[dict(name=n,q=q,d=d,depth=dp) for n,q,d,dp in [('a','a0','rst_root_n',1),('a1','rst_n_t5','a0',2),('b','b0','rst_root_n',1),('b1','rst_n_t14','b0',2)]]}
ROW=dict(instance='u_bin_i',pin='rst_n',old_reset='rst_n',new_reset='rst_n_t14',clock_net='clk')

def test_default_byte_identical_no_parsing_or_tree():
    assert localize('arbitrary old bytes\n',None,None)==('arbitrary old bytes\n',[])

def test_epoch_control_only_connection_changes():
    txt,rs=localize(TEXT,[ROW],TREE)
    assert txt==TEXT.replace('u_bin_i (.clk(clk), .rst_n(rst_n)', 'u_bin_i (.clk(clk), .rst_n(rst_n_t14)')
    assert rs[0]['depth']==2 and rs[0]['cycles_added']==0

def test_native_requires_actual_binder_reset_role():
    r=dict(ROW,instance='u_core')
    with pytest.raises(ResetConsumerError,match='classified'):localize(TEXT,[r],TREE)
    txt,rs=localize(TEXT,[r],TREE,{'u_core.rst_n':dict(kind='control',clocks={'clk':'clk'})})
    assert '.rst_n(rst_n_t14), .data(d)' in txt

@pytest.mark.parametrize('change',[{'instance':'absent'},{'old_reset':'a0'},{'new_reset':'missing'},{'pin':'d','old_reset':'d'},{'clock_net':'otherclk'}])
def test_unknown_consumer_old_net_data_pin_domain_rejected(change):
    with pytest.raises(ResetConsumerError):localize(TEXT,[dict(ROW,**change)],TREE)

def test_different_actual_release_depth_rejected():
    with pytest.raises(ResetConsumerError,match='depth'):localize(TEXT,[dict(ROW,new_reset='b0')],TREE)

def test_false_published_depth_rejected():
    t=copy.deepcopy(TREE);t['relays'][-1]['depth']=3
    with pytest.raises(ResetConsumerError,match='published depth'):localize(TEXT,[ROW],t)

def test_mapped_reset_edge_mutant_rejected():
    s=TEXT.replace('b1 (.clk(clk), .d(b0)', 'b1 (.clk(clk), .d(rst_root_n)')
    with pytest.raises(ResetConsumerError,match='edge mismatch'):localize(s,[ROW],TREE)

def test_reset_clock_mutant_rejected():
    s=TEXT.replace('b1 (.clk(clk)', 'b1 (.clk(otherclk)')
    with pytest.raises(ResetConsumerError,match='domain mismatch'):localize(s,[ROW],TREE)

def test_control_consumer_clock_mutant_rejected():
    s=TEXT.replace('u_core (.clk(clk)', 'u_core (.clk(otherclk)')
    with pytest.raises(ResetConsumerError,match='consumer clock'):localize(s,[dict(ROW,instance='u_core')],TREE,{'u_core.rst_n':dict(kind='control',clocks={'clk':'clk'})})

def test_missing_or_different_root_rejected():
    s=TEXT.replace('u_rst_in (.clk(clk)', 'u_rst_in (.clk(otherclk)')
    with pytest.raises(ResetConsumerError,match='common reset root'):localize(s,[ROW],TREE)

def test_duplicate_and_extra_keys_rejected():
    with pytest.raises(ResetConsumerError,match='duplicate consumer'):localize(TEXT,[ROW,ROW],TREE)
    with pytest.raises(ResetConsumerError,match='five explicit'):localize(TEXT,[dict(ROW,data_reset=True)],TREE)

def test_unknown_tree_and_combinational_reset_rejected():
    with pytest.raises(ResetConsumerError):localize(TEXT,[ROW],None)
    with pytest.raises(ResetConsumerError):localize(TEXT.replace('wire rst_n = rst_n_t5','wire rst_n = ~rst_n_t5'),[ROW],TREE)

# QC-S4Z: mission-role consumer taps rst_n_t<k> are ot_dp_rgate (reset AND run); only the leaf may be gated.
GTEXT = TEXT.replace("ot_dp_rrelay a1 (.clk(clk), .d(a0), .q(rst_n_t5));", "ot_dp_rgate a1 (.clk(clk), .d(a0), .run(rn_a0), .q(rst_n_t5));").replace(
    "ot_dp_rrelay b1 (.clk(clk), .d(b0), .q(rst_n_t14));", "ot_dp_rgate b1 (.clk(clk), .d(b0), .run(rn_b0), .q(rst_n_t14));")

def test_gated_leaf_taps_accepted_equal_depth():
    txt, rs = localize(GTEXT, [ROW], TREE)
    assert ".rst_n(rst_n_t14)" in txt and rs[0]["depth"] == 2 and rs[0]["cycles_added"] == 0

def test_gated_leaf_without_run_rejected():
    with pytest.raises(ResetConsumerError, match="registered reset relay"):
        localize(GTEXT.replace(".run(rn_b0), ", ""), [ROW], TREE)

def test_gated_intermediate_relay_rejected():
    s = GTEXT.replace("ot_dp_rrelay b (.clk(clk), .d(rst_root_n), .q(b0));", "ot_dp_rgate b (.clk(clk), .d(rst_root_n), .run(rn_r), .q(b0));")
    with pytest.raises(ResetConsumerError, match="registered reset relay"):
        localize(s, [ROW], TREE)

def test_gated_non_tap_name_rejected():
    t = copy.deepcopy(TREE)
    s = GTEXT.replace("rst_n_t14", "rst_x_t14"); t["relays"][-1]["q"] = "rst_x_t14"
    with pytest.raises(ResetConsumerError):
        localize(s, [dict(ROW, new_reset="rst_x_t14")], t)


# QC-SC-ROWS-1115: localization between gated taps needs equal published START roles.
RGTEXT = TEXT.replace('ot_dp_rrelay a1 (.clk(clk), .d(a0), .q(rst_n_t5))', 'ot_dp_rgate a1 (.clk(clk), .d(a0), .run(ra), .q(rst_n_t5))') \
    .replace('ot_dp_rrelay b1 (.clk(clk), .d(b0), .q(rst_n_t14))', 'ot_dp_rgate b1 (.clk(clk), .d(b0), .run(rb), .q(rst_n_t14))')

def _rgtree(r5='mission', r14='mission'):
    t = copy.deepcopy(TREE)
    for r in t['relays']:
        if r['q'] == 'rst_n_t5': r.update(tap=5, kind='tap')
        if r['q'] == 'rst_n_t14': r.update(tap=14, kind='tap')
    t['tap_roles'] = {5: r5, 14: r14}
    return t

def test_gated_taps_same_role_accepted():
    txt, rs = localize(RGTEXT, [ROW], _rgtree())
    assert '.rst_n(rst_n_t14)' in txt and rs[0]['cycles_added'] == 0

def test_gated_taps_role_mismatch_rejected():
    with pytest.raises(ResetConsumerError, match='tap role'):
        localize(RGTEXT, [ROW], _rgtree(r14='bootstrap'))


# QC-SC-ROWS-1115: bind self-check, the published reset tree must be the emitted one.
from reset_consumers import verify_published

def test_published_equals_emitted_is_clean():
    assert verify_published(TEXT, TREE) == []

def test_off_by_one_relay_published_vs_emitted_flagged():
    t = copy.deepcopy(TREE)
    t['relays'][3]['d'] = 'a0'          # published b1 hangs on a0, the RTL hangs it on b0
    iss = verify_published(TEXT, t)
    assert iss and 'b1' in iss[0] and 'published' in iss[0]

def test_raw_tap_net_names_do_not_matter_graph_edges_do():
    s = TEXT.replace('.q(b0)', '.q(rr_b0)').replace('.d(b0)', '.d(rr_b0)').replace('wire rst_root_n, a0, rst_n_t5, b0,', 'wire rst_root_n, a0, rst_n_t5, rr_b0,')
    assert verify_published(s, TREE) == []

def test_missing_and_unpublished_relays_flagged():
    t = copy.deepcopy(TREE); t['relays'].append(dict(name='u_ghost', q='g0', d='rst_root_n', depth=1))
    assert any('not in the emitted RTL' in i for i in verify_published(TEXT, t))
    s = TEXT.replace('ot_dp_rrelay b1 (', 'ot_dp_rrelay u_rrl_9 (')
    t2 = copy.deepcopy(TREE); t2['relays'][-1]['name'] = 'b1'
    assert any('u_rrl_9' in i and 'not published' in i for i in verify_published(s, t2))

def test_bind_localization_uses_the_emitted_tree():
    import pathlib
    src = (pathlib.Path(__file__).parent / 'bind.py').read_text()
    i = src.index('reset_localization = t.get("reset", {}).get("consumer_localization")')
    j = src.index('localize(', i)
    seg = src[i:j]
    assert seg.index("_emitted_reset_trees") < seg.index("get(\"collector_tree\")")
    assert 'RCV.verify_published' in src and 'RESET_TREE_SELFCHECK' in src
