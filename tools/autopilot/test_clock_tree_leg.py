"""Actual clock-leg diagnostic uses connected graph edges, including long roots."""
import geom_rules as G
from test_auto_geom import dump


def fixture(tmp_path,mid_x=100,macro=False):
    p=dump(tmp_path/'clock.tsv',die=(0,0,1000,200),flops=[(1,400,50)],
           pins=[(0,'clk','INPUT',0,50,'CLOCK')],
           nets=[('CLOCK','p0',['i10']),('CLOCK','i10',['i11c']),
                 ('CLOCK','i11',['i1c']+(['i20c'] if macro else []))],
           macros=[(20,390,55,410,65)] if macro else [])
    p.write_text(p.read_text()+f'C\t10\tB\tINVx1\t{mid_x-.5}\t49.5\t{mid_x+.5}\t50.5\tinv\n'
                 +'C\t11\tK\tICG\t299.5\t49.5\t300.5\t50.5\tgate\n'
                 +'Q\t10\tPLACED\nQ\t11\tPLACED\n')
    return G.Design(p)


def test_placed_rooted_buffer_gate_and_macro_clock_legs(tmp_path):
    m=G.clock_tree_leg_metrics(fixture(tmp_path,macro=True))
    assert m['clock_tree_leg_max']==200 and m['clock_tree_leg_worst']=='inv -> gate'
    assert m['clock_tree_leg_edges']==4 and m['clock_tree_clock_cells']==2
    assert m['clock_tree_unrooted_sinks']==0 and not m['clock_tree_trace_errors']


def test_long_root_leg_cannot_be_hidden_by_short_leaf_or_nearby_unrelated_cell(tmp_path):
    d=fixture(tmp_path,mid_x=600)
    d.cells[99]=('K','CKBUF',-.5,49.5,.5,50.5,'unrelated')
    m=G.clock_tree_leg_metrics(d)
    assert m['clock_tree_leg_max']==600 and m['clock_tree_leg_worst']=='clk -> inv'
    assert m['clock_tree_clock_cells']==2


def test_unrooted_and_ambiguous_clock_input_fail_to_claim_rooted_tree(tmp_path):
    d=fixture(tmp_path)
    d.cell_in[11].append((0,True))
    m=G.clock_tree_leg_metrics(d)
    assert m['clock_tree_unrooted_sinks']==1 and m['clock_tree_leg_edges']==0
    assert 'ambiguous clock-cell input' in m['clock_tree_trace_errors']
