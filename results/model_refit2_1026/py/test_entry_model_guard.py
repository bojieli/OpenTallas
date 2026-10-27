import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common


def test_unmodelled_hidden_entry_chain_fails_closed(tmp_path):
    p=tmp_path/"s.tcl"
    p.write_text("set ot_h_entry_n 3\n")
    with pytest.raises(ValueError,match="explicit tree nodes"):
        common.parse_spec(p)


def test_explicit_trunk_nodes_are_preserved(tmp_path):
    p=tmp_path/"s.tcl"
    p.write_text("set ot_h_entry_n 0\nset ot_ms_root {1.0 2.0}\nset ot_ms_tree {\n {TR0 root 2.0 2.0 BUFx8_ASAP7_75t_R}\n}\nset ot_ms_leaves {\n}\nset ot_ms_macros {\n}\n")
    q=common.parse_spec(p)
    assert q["root"]==(1.,2.) and q["tree"]["TR0"]["par"]=="root"
