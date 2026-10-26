from pathlib import Path
import importlib.util
import json
import pytest
from tools.die_plan import bind_smoke as S


def test_top_preserves_new_parent_strap_literal(tmp_path):
    top=tmp_path/'top.sv'
    top.write_text("module t;\n wire [0:0] x;\n cb c_E0_bf_00 (\n .a(x),\n .strap_u_t_0_0_tile_id(16'b0000000110000000)\n );\nendmodule\n")
    wires,instances=S.parse_top(top)
    assert wires['x']['width']==1
    assert S.tile_identity(instances[0],0,0)==384
    assert "16'b0000000110000000" in '\n'.join(instances[0]['text'])


@pytest.mark.parametrize('prefix',['strap_','S_'])
def test_tile_identity_uses_declared_value_for_both_spellings(prefix):
    inst=dict(name='tile',conns=[(prefix+'u_t_0_1_tile_id',"16'h0180")])
    assert S.tile_identity(inst,0,1)==384
    assert (S.tile_identity(inst,0,1)&~15)+S.SLOT[0,1]==386


def test_missing_or_ambiguous_identity_is_not_inferred_from_partition_name():
    with pytest.raises(ValueError,match='exactly one'):
        S.tile_identity(dict(name='c_E0_bf_00',conns=[]),0,0)
    with pytest.raises(ValueError,match='exactly one'):
        S.tile_identity(dict(name='tile',conns=[('strap_u_t_0_0_tile_id',"16'd384"),('S_u_t_0_0_tile_id',"16'd384")]),0,0)


@pytest.mark.parametrize('expr',["16'bxxxxxxxxxxxxxxxx","8'd384","16'b2"])
def test_unknown_wrong_width_or_invalid_id_rejected(expr):
    with pytest.raises(ValueError):
        S.tile_identity(dict(name='tile',conns=[('strap_u_t_0_0_tile_id',expr)]),0,0)


def test_only_input_strap_literals_are_omitted_from_open_nets():
    assert S.strap_literal('strap_u_fab_sidx',"3'b111",'input')
    assert not S.strap_literal('data','signal_wire','input')
    with pytest.raises(ValueError,match='non-strap'):
        S.strap_literal('data',"1'b0",'input')
    with pytest.raises(ValueError,match='non-strap'):
        S.strap_literal('strap_u_fab_sidx',"3'b111",'output')


def test_whole_observer_reads_all48_exact_new_id_literals(tmp_path):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('make_observer',root/'tools/qwen_tokfunc/current_path/make_observer.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    rows=['module t;'];cid=0
    for side in 'EW':
        for col in range(6):
            for sub in ('bf','bn','tf','tn'):
                rows.extend([f' cb c_{side}{col}_{sub}_00 (',f" .strap_u_t_0_0_tile_id(16'b{cid<<4:016b})",' );'])
                cid+=1
    rows.append('endmodule');top=tmp_path/'top.sv';top.write_text('\n'.join(rows))
    pair=tmp_path/'pair';pair.mkdir();(pair/'pair.json').write_text(json.dumps(dict(whole_qc=True)))
    out=tmp_path/'observer.sv';m.make(top,pair,out)
    assert out.read_text().count(' CLUSTER ')==48
    # A duplicate literal must fail rather than silently substituting a nickname-derived ID.
    top.write_text(top.read_text().replace(f"{47<<4:016b}",f"{46<<4:016b}"))
    with pytest.raises(ValueError,match='duplicate cluster'):
        m.make(top,pair,tmp_path/'bad.sv')
