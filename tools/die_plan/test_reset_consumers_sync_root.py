"""QC SC synchronizer-root reset localization: actual emitted root contract only."""
import copy
import pytest
from reset_consumers import localize, ResetConsumerError

TEXT = '''module root_fixture(input wire clk, arst_n, start_i, input wire d, ea);
wire rst_root_n, run_root, a0, b0, rst_n_t5, rst_n_t14;
wire rst_n = rst_n_t5;
ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_root_n));
ot_dp_rsync_s2 u_run_root (.clk(clk), .async_rst_n(start_i), .sync_rst_n(run_root));
ot_dp_rrelay a (.clk(clk), .d(rst_root_n), .q(a0));
ot_dp_rgate a1 (.clk(clk), .d(a0), .run(run_root), .q(rst_n_t5));
ot_dp_rrelay b (.clk(clk), .d(rst_root_n), .q(b0));
ot_dp_rgate b1 (.clk(clk), .d(b0), .run(run_root), .q(rst_n_t14));
ot_dp_st #(.W(1)) u_bin_i (.clk(clk), .rst_n(rst_n), .d(d), .ea(ea), .q(q), .eq(eq));
endmodule
'''
TREE = dict(entry='sync', sync_stages=2, start=True,
            tap_roles={'5':'mission', '14':'mission'}, relays=[
                dict(name='a', q='a0', d='rst_root_n', depth=1),
                dict(name='a1', q='rst_n_t5', d='a0', depth=2, tap=5),
                dict(name='b', q='b0', d='rst_root_n', depth=1),
                dict(name='b1', q='rst_n_t14', d='b0', depth=2, tap=14)])
ROW = dict(instance='u_bin_i', pin='rst_n', old_reset='rst_n', new_reset='rst_n_t14', clock_net='clk')


def test_actual_two_flop_root_and_start_keep_same_release_depth():
    txt, receipts = localize(TEXT, [ROW], TREE)
    assert txt == TEXT.replace('u_bin_i (.clk(clk), .rst_n(rst_n)',
                               'u_bin_i (.clk(clk), .rst_n(rst_n_t14)')
    assert receipts[0]['depth'] == 2 and receipts[0]['cycles_added'] == 0


@pytest.mark.parametrize('change', [dict(entry='relayed'), dict(entry=None), dict(sync_stages=3), dict(sync_stages=None)])
def test_sync_root_needs_explicit_exact_declared_entry(change):
    with pytest.raises(ResetConsumerError, match='common reset root'):
        localize(TEXT, [ROW], dict(TREE, **change))


@pytest.mark.parametrize('old,new', [
    ('u_rst_root (.clk(clk)', 'u_rst_root (.clk(otherclk)'),
    ('ot_dp_rsync_s2 u_rst_root', 'ot_dp_rsync_s3 u_rst_root'),
    ('u_rst_root (.clk(clk), .async_rst_n(arst_n)', 'u_rst_root (.clk(clk), .async_rst_n(other_reset)'),
    ('.sync_rst_n(rst_root_n)', '.sync_rst_n(other_root)'),
    ('ot_dp_rsync_s2 u_rst_root', 'ot_dp_rsync_s2 another_root'),
    ('ot_dp_rsync_s2 u_run_root', 'ot_dp_rsync_s3 u_run_root'),
    ('u_run_root (.clk(clk)', 'u_run_root (.clk(otherclk)'),
    ('.async_rst_n(start_i)', '.async_rst_n(other_start)'),
    ('.sync_rst_n(run_root)', '.sync_rst_n(other_run)'),
    ('ot_dp_rsync_s2 u_run_root', 'ot_dp_rsync_s2 another_run'),
    ('.sync_rst_n(rst_root_n)', '.sync_rst_n(rst_root_n), .test_pin(1\'b0)'),
])
def test_wrong_actual_root_or_start_schema_module_pin_clock_fails_closed(old, new):
    with pytest.raises(ResetConsumerError, match='common reset root'):
        localize(TEXT.replace(old, new), [ROW], TREE)


def test_competing_root_driver_refused():
    txt=TEXT.replace('endmodule', 'ot_dp_rrelay extra (.clk(clk),.d(arst_n),.q(rst_root_n));\nendmodule')
    with pytest.raises(ResetConsumerError, match='common reset root'):
        localize(txt, [ROW], TREE)


def test_branch_lineage_and_mission_role_still_fail_closed():
    with pytest.raises(ResetConsumerError, match='edge mismatch'):
        localize(TEXT.replace('b1 (.clk(clk), .d(b0)', 'b1 (.clk(clk), .d(rst_root_n)'), [ROW], TREE)
    changed=copy.deepcopy(TREE);changed['tap_roles']['14']='bootstrap'
    with pytest.raises(ResetConsumerError, match='tap role'):
        localize(TEXT, [ROW], changed)


def test_unknown_common_root_old_failure_stays_failure():
    txt=TEXT.replace('ot_dp_rsync_s2 u_rst_root', 'arbitrary_reset u_rst_root')
    with pytest.raises(ResetConsumerError, match='common reset root'):
        localize(txt, [ROW], TREE)


HOLD_TEXT = TEXT.replace(
    '.sync_rst_n(rst_root_n));',
    ".sync_rst_n(rst_por_n));\n"
    "ot_dp_lockq #(.STABLE(256)) u_rst_lockq "
    "(.clk(clk), .d(rst_por_n), .locked(1'b1), .q(rst_root_n));",
)
HOLD_TREE = dict(TREE, lock=dict(tied=True, stable=256, stages=259))


def test_tied_hold_counter_keeps_localized_relays_at_same_depth():
    txt, receipts = localize(HOLD_TEXT, [ROW], HOLD_TREE)
    assert txt == HOLD_TEXT.replace('u_bin_i (.clk(clk), .rst_n(rst_n)',
                                    'u_bin_i (.clk(clk), .rst_n(rst_n_t14)')
    assert receipts[0]['depth'] == 2 and receipts[0]['cycles_added'] == 0


@pytest.mark.parametrize('old,new', [
    ("u_rst_lockq (.clk(clk)", "u_rst_lockq (.clk(otherclk)"),
    ("ot_dp_lockq #", "unverified_counter #"),
    (".d(rst_por_n)", ".d(arst_n)"),
    (".locked(1'b1)", ".locked(start_i)"),
    (".STABLE(256)", ".STABLE(255)"),
    ("endmodule", "ot_dp_rrelay extra (.clk(clk), .d(a0), .q(rst_root_n));\nendmodule"),
    ("endmodule", "ot_dp_rrelay extra (.clk(clk), .d(a0), .q(rst_por_n));\nendmodule"),
])
def test_tied_hold_counter_refuses_mismatched_emitted_root(old, new):
    with pytest.raises(ResetConsumerError, match='common reset root'):
        localize(HOLD_TEXT.replace(old, new), [ROW], HOLD_TREE)


def test_tied_hold_counter_requires_published_matching_configuration():
    for tree in (TREE, dict(TREE, lock=dict(tied=True, stable=256, stages=258))):
        with pytest.raises(ResetConsumerError, match='common reset root'):
            localize(HOLD_TEXT, [ROW], tree)
