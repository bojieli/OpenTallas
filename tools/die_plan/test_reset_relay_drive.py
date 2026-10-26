"""Opt-in electrical reset relay: invariant cycle/port shape and legal pad geometry."""
import copy
import reset_tree as R


def test_padspread_preserves_graph_and_depth():
    topo = R.topology([('a', 300, 0), ('b', 600, 200)], (0, 0))
    a = R.assign(topo, 7)
    b = R.assign(topo, 7, pad_spread=True)
    assert [(r['name'],r['d'],r['q'],r['depth']) for r in a['relays']] == [
        (r['name'],r['d'],r['q'],r['depth']) for r in b['relays']]
    assert any(x['xy'] != y['xy'] for x,y in zip(a['relays'],b['relays']))
    assert b['max_hop_um'] <= a['max_hop_um']
    assert not R.verify(b)


def test_padspread_obstacles_and_short_edge():
    boxes = [(40,-5,60,5)]
    out = R._pad_sites((0,0),(100,100),4,boxes,(-1,-1,101,101), boxes)
    assert all(R._free(x,boxes,(-1,-1,101,101)) for x in out)
    assert all(not R._seg_hits(a,b,boxes) for a,b in zip([(0,0)]+out,out+[(100,100)]))
    assert R._pad_sites((0,0),(5,0),3) == [(5,0)]*3


def test_plain_default_and_external_direct_q():
    t = R.build([('a',100,0),('out',200,0)],(0,0),depth=3)
    t.update(taps=['a','out'],n_clock_taps=1,outs=[[200,0]],entry='relayed',sync_stages=2)
    assert all(R.relay_cell(t,r)=='ot_dp_rrelay' for r in t['relays'])
    t['relay_driver']=True
    assert all(R.relay_cell(t,r)=='ot_dp_rrelay' for r in t['relays'] if r['tap']==1)
    assert any(R.relay_cell(t,r)=='ot_dp_rrelay_drive' for r in t['relays'] if r['tap']!=1)
    rtl='\n'.join(R.rtl_lines(t))
    assert 'ot_dp_rrelay u_rst_in' in rtl
    assert 'ot_dp_rrelay_drive u_rst_in' not in rtl


def test_kit_driver_cells_and_replacement():
    import kit_rsync as K
    assert "module ot_dp_rrelay_drive" not in K.cells_text()
    text = K.cells_text(driver=True)
    assert "module ot_dp_rrelay_drive" in text and "module ot_dp_rgate_drive" in text
    assert K.TREE.match("    ot_dp_rgate_drive u_rrl_2_g (.clk(clk), .d(a), .run(b), .q(c));")
    assert K.TREE.match("    ot_dp_rrelay_drive u_srl_12 (.clk(clk), .d(a), .q(c));")
