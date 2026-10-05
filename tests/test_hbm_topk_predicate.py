"""Small model/source guards; actual numerical evidence is the remote RTL gate."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/rtl/hbm_topk_predicate_20261005'

def test_model_before_rtl_replays():
    tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='hbm_topk_predicate_lookahead_model')
    ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<isolated model>','exec'),ns)
    assert ns[node.name]()==json.loads((BASE/'model_before_RTL.json').read_text())

def test_pinned_original_and_default_comparison():
    original=(BASE/'inputs/ot_gpu_router_topk_ip_f.sv').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='74a669e6d21b25945de777257813bfc4d9f6e7db25fdc261751d1381c9b742f2'
    successor=(ROOT/'rtl/gpu/ot_gpu_router_topk_ip_pred.sv').read_text()
    assert 'parameter integer LOOKAHEAD = 0' in successor
    start=original.decode().index('            next_pos[cj] = 8;')
    end=original.decode().index('\n        end\n    end',start)
    assert original.decode()[start:end] in successor
    assert 'x_ge = x_r[cj][W-1] &&' in successor
    assert 'committed_ge[ci] = lane[cj][ci*W+W-1] &&' in successor

def test_payload_and_pipeline_text_preserved():
    original=(BASE/'inputs/ot_gpu_router_topk_ip_f.sv').read_text()
    successor=(ROOT/'rtl/gpu/ot_gpu_router_topk_ip_pred.sv').read_text()
    for begin,end in [('            old_list = f_r[cj]', '            next_pos[cj] = 8;'),
                      ('    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin\n            fin_v', '\nendmodule')]:
        text=original[original.index(begin):original.index(end,original.index(begin))]
        if begin.startswith('            old_list'):
            text=text[:text.index('            next_pos')] if '            next_pos' in text else text
            # Original comparison setup is immediately followed by new predicate arm.
        assert text in successor
