import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))

import dsrom_recovery_issuer_parent_binding as B


def test_selected_site_and_debit_replay():
    d=B.build()
    saved=json.loads((B.OUT/'model.json').read_text())
    assert saved==d
    assert d['selected_parent']['pairs']==2417
    assert d['selected_parent']['domain']=='stream_1p2'
    assert d['issuer']['rectangle_contained']
    assert d['issuer']['parent_local_bbox_um']==pytest.approx([4.32,4.32,69.12,12.96])
    assert d['issuer']['raw_FF']==d['issuer']['new_clock_sinks']==47
    assert d['issuer']['estimated_cell_um2']<d['issuer']['cell_budget_um2']
    assert not d['physical_build_admitted']


def test_stream_format_padding_never_truncates_data():
    for word in (0,1,0x123456789a,0xabcdef123456,(1<<48)-1):
        assert int(f'{word:010x}',16)==int(f'{word:012x}',16)==word
    d=B.build()
    assert d['parent_tables']['PHROM']['words']==2048
    assert d['parent_tables']['PHROM']['simultaneous_read_ports']==2
    assert d['parent_tables']['STREAM']['words']==16384
    assert d['parent_tables']['STREAM']['bits']==786432
    assert d['parent_tables']['selected_hard_abstract'] is None
    assert not d['local_native_controls']['full_parent_image']
    assert not d['screen']['full_parent_provider']
