import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_hold_capture_gate_prepare import ROOT,TILE,validate_model,original_logic
from qwen_rom_hold_capture_literal_gate import CANDIDATE,candidate_logic
BASE=ROOT/'results/uarch/qwen_rom_hold_capture_literal_gate_20261002'


def test_committed_maxwell_model_fixed_inventory_and_cost_admission():
    model=json.loads((BASE/'Maxwell_model/model-r2.json').read_text())
    assert validate_model(model)
    for mutation in ['clock','replica','cycle','slot','program','physical']:
        r=copy.deepcopy(model)
        if mutation=='clock':r['signoff']['target_period_ps']=900
        if mutation=='replica':r['inventory']['after']=5
        if mutation=='cycle':r['latency']['new_cycles']=1
        if mutation=='slot':r['area']['positive_extra_route_clock_PG_policy_um2']=0
        if mutation=='program':r['latency']['exact_same_program_55_reference']['program_sha256']='0'*64
        if mutation=='physical':r['tile_PR_admitted']=True
        with pytest.raises(ValueError):validate_model(r)


def test_candidate_cannot_enable_default_or_drop_parent_forwarding():
    raw=(ROOT/CANDIDATE).read_bytes();cone,body=candidate_logic(raw)
    assert body in raw and b'ROM_HOLD_DIRECT_CAPTURE=0' in cone
    with pytest.raises(ValueError):candidate_logic(raw.replace(b'parameter integer ROM_HOLD_DIRECT_CAPTURE = 0',b'parameter integer ROM_HOLD_DIRECT_CAPTURE = 1'))
    with pytest.raises(ValueError):candidate_logic(raw.replace(b'.ROM_HOLD_DIRECT_CAPTURE(ROM_HOLD_DIRECT_CAPTURE)',b'.ROM_HOLD_DIRECT_CAPTURE(0)'))


def test_original_exact_body_and_candidate_non_ROM_functions_unchanged():
    raw=(ROOT/TILE).read_bytes();wrapper,body=original_logic(raw)
    assert body in raw and body in wrapper
    old=raw.decode();new=(ROOT/CANDIDATE).read_text()
    new=new.replace('ot_qwen_rom_tile_logic_hold_capture_candidate','ot_qwen_rom_tile_logic_w12').replace('module ot_qwen_rom_tile_hold_capture_candidate','module ot_qwen_rom_tile_w12')
    new=new.replace('    parameter integer ROM_HOLD_DIRECT_CAPTURE = 0, // Maxwell645ae1dd7; opt-in, no added edges\n','')
    new=new.replace(' .ROM_HOLD_DIRECT_CAPTURE(ROM_HOLD_DIRECT_CAPTURE),','')
    marker='    // -- KV slice'
    assert old[old.index(marker):]==new[new.index(marker):]
