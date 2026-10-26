"""Exact logical driver grid bridge: zero-based rows, no reversal guesses."""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def grid():
    # Public slang vector is reversed by words; driver cells preserve actual
    # logical [bank][row]. This is why flat vector positions cannot decide it.
    members = {}
    for bank in range(2):
        for row in range(3):
            for bit in range(2):
                flat = (5-(bank*3+row))*2+bit
                members[f'ff:u.m[{flat}]'] = (bank,f'[{bank}][{row}][{bit}]')
    gate = {f'[{word}][{bit}]': f'ff:u.m#t[{word}][{bit}]' for word in range(6) for bit in range(2)}
    return members, gate


def test_complete_logical_grid_matches_flat_words_without_reversal():
    members, gate = grid()
    mapping, shape = lec.slang_flat_word_keys(members,[{},gate])
    assert shape == (2,3,2) and len(mapping) == 12
    assert mapping['ff:u.m#t[0][0]'] == 'ff:u.m[10]'
    assert mapping['ff:u.m#t[5][1]'] == 'ff:u.m[1]'
    assert len(set(mapping.values())) == len(mapping)


def test_reject_partial_or_shifted_driver_grid():
    members, gate = grid()
    missing = dict(members);missing.pop('ff:u.m[0]')
    assert lec.slang_flat_word_keys(missing,[gate]) == ({},())
    shifted = {k:(i,e.replace('[0]','[1]',1)) for k,(i,e) in members.items()}
    assert lec.slang_flat_word_keys(shifted,[gate]) == ({},())


def test_reject_wrong_gate_extent_and_ambiguous_families():
    members, gate = grid()
    wrong = {k:v for k,v in gate.items() if not k.startswith('[5]')}
    assert lec.slang_flat_word_keys(members,[wrong]) == ({},())
    assert lec.slang_flat_word_keys(members,[gate,gate]) == ({},())
    ragged = dict(gate);ragged['[5][2]']='ff:u.m#t[5][2]'
    assert lec.slang_flat_word_keys(members,[ragged]) == ({},())


def test_merged_gate_bits_keep_remaining_proposals_exact():
    members, gate = grid()
    del gate['[3][1]']
    mapping, shape = lec.slang_flat_word_keys(members,[gate])
    assert shape == (2,3,2) and len(mapping) == 11
    assert 'ff:u.m[5]' not in mapping.values()  # logical bank1,row0,bit1 -> flat public5


def test_bridge_updates_only_unmatched_keys_using_real_driver_metadata(tmp_path):
    members, gate = grid()
    # Same metadata shape as read_slang --no-implicit-memories.
    bits = [100+i for i in range(12)]
    cells = {}
    for bank in range(2):
        for row in range(3):
            f=(5-(bank*3+row))*2
            cells[f'$flatten\\u.$driver$m[{bank}][{row}]'] = {
                'type':'$dff','connections':{'Q':bits[f:f+2]}}
    (tmp_path/'gold.aliases.json').write_text(json.dumps({'modules':{'lec_top':{
        'netnames':{'u.m':{'hide_name':0,'bits':bits}},'cells':cells}}}))
    class L:
        hyp={}
        gp={k:i for i,k in enumerate(members)}
        tp={v:i for i,v in enumerate(gate.values())}
        tc=dict(tp)
        matched=[]
        gonly=list(gp)
        tonly=list(tp)
    log=[]
    assert lec.slang_element_keys(L,log,work=tmp_path)==12
    assert set(L.tp)==set(L.gp) and not L.gonly and not L.tonly
    assert any('mixed-radix' in line for line in log)
