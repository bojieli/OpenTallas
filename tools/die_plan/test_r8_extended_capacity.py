import pytest
import r8
import r8_strap_lec as L
from test_r8_strap_pads import _binder

def test_default_capacity_and_scoped_extension():
 assert r8.strap_pad_capacity()==15 and r8.strap_pad_width()==4
 assert r8.strap_pad_capacity({'r8_strap_pad_max':63})==63
 assert r8.strap_pad_width({'r8_strap_pad_max':63})==6
 for bad in [True,14,63.0,'63']:
  with pytest.raises(ValueError):r8.strap_pad_capacity({'r8_strap_pad_max':bad})

def test_large_real_pc_spans_need_declared_hardware_capacity():
 b=_binder({'a':[0,0,2],'b':[62,32,26]})
 b.types={'T':{'r8_strap_pad_max':63}}
 b.r8_strap_sites({'T':['a','b']})
 assert not b.errors and b.r8_pad_width('T')==6
 assert sorted(v['span'] for v in b.r8_sites['T'].values())==[24,32,62]
 for v in b.r8_sites['T'].values():assert max(v['counts'].values())<=63
 old=_binder({'a':[0,0,2],'b':[62,32,26]});old.r8_strap_sites({'T':['a','b']})
 assert len(old.errors)==3 and not old.r8_sites
 over=_binder({'a':[0,0,0],'b':[64,0,0]});over.types={'T':{'r8_strap_pad_max':63}};over.r8_strap_sites({'T':['a','b']})
 assert any('pad 64 > strap capacity 63' in e for e in over.errors)

def test_extended_bank_lec_parser_harness_and_width_guard():
 text=('module m (\n    input wire [5:0] strap_r8pad_u_x   // parent-tied R8 pad-count strap\n);\n'
       '    ot_dp_dly_cnt #(.W(16), .DMAX(62), .CW(6)) u_r8b_s (.clk(clk), .strap_cnt(strap_r8pad_u_x), .d(x), .q(q));\nendmodule\n')
 b=L.banks_of(text);assert b[0]['CW']==6 and b[0]['DMAX']==62
 assert L.structure_ok(text)
 assert not L.structure_ok(text.replace('[5:0]','[3:0]'))
 h=L.harness('T',b,{'strap_r8pad_u_x':62},{'strap_r8pad_u_x':62},'extended')
 assert "6'd62" in h and '.CW(6)' in h and '[5:0]' in h


def test_width_is_per_bank_span_not_blanket_type_capacity():
 b=_binder({'a':[0,0,0],'b':[62,12,24]});b.types={'T':{'r8_strap_pad_max':62}};b.r8_strap_sites({'T':['a','b']})
 assert not b.errors
 assert sorted(b.r8_pad_width('T',site) for site in b.r8_sites['T'])==[4,5,6]
