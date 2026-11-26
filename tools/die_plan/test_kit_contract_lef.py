"""Declared LEF contracts remain source-hashed and distinct from kit placement."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kit_contract as K

LEF='''MACRO unrelated
 SIZE 1 BY 1 ;
END unrelated
MACRO child
 SIZE 10 BY 10 ;
 PIN clk
  USE CLOCK ;
  PORT
   LAYER M5 ;
   RECT 4.988 9.52 5.036 10 ;
  END
 END clk
 PIN data
  PORT
   LAYER M3 ;
   RECT 0 1 0.084 1.084 ;
  END
 END data
 PIN VDD
  USE POWER ;
  PORT
   LAYER M5 ;
   RECT 0 0 10 10 ;
  END
 END VDD
END child
'''
ROWS=[dict(name='clk',layer='M5',x=5.012,y=9.76),dict(name='data',layer='M3',x=.042,y=1.042)]


def fixture(kd):
    lef=kd/'child.lef';lef.write_text(LEF)
    (kd/'io.tcl').write_text(''.join(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{p['x']} {p['y']}}}\n" for p in ROWS))
    (kd/'master_slice.json').write_text(json.dumps(dict(core_clock_port='clk',islands=[])))
    f=dict(module='child',outline_um=[10,10],pins_file='declared/child.lef',pins_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),pins_canon_sha256=K._canon(ROWS,[10,10]))
    (kd/'freeze.json').write_text(json.dumps(f));return lef,f


def test_declared_lef_slice_contract_passes_exact_pin_rows(tmp_path):
    lef,_=fixture(tmp_path)
    assert K.lef_pin_contract(lef,'child')==([10,10],ROWS)
    errors,info=K.pins_canonical(tmp_path)
    assert not errors and info['plan_file']==str(lef)


def test_declared_lef_requires_whole_file_shape_identity(tmp_path):
    _,f=fixture(tmp_path);f.pop('pins_sha256')
    (tmp_path/'freeze.json').write_text(json.dumps(f))
    with pytest.raises(ValueError,match='whole-file shape hash'):K.pins_canonical(tmp_path)


@pytest.mark.parametrize('mutation',['moved-pin','same-centre-shape','placement'])
def test_declared_lef_identity_and_actual_placement_mutants_fail(tmp_path,mutation):
    lef,_=fixture(tmp_path)
    if mutation=='moved-pin':lef.write_text(LEF.replace('0 1 0.084 1.084','0 2 0.084 2.084'))
    elif mutation=='same-centre-shape':lef.write_text(LEF.replace('4.988 9.52 5.036 10','4.98 9.52 5.044 10'))
    else:
        p=tmp_path/'io.tcl';p.write_text(p.read_text().replace('{0.042 1.042}','{0.042 2.042}'))
    errors,_=K.pins_canonical(tmp_path)
    assert errors


@pytest.mark.parametrize('mutation',['wrong-module','unterminated','duplicate-pin','unknown-format'])
def test_declared_lef_malformed_or_unknown_contract_fails_closed(tmp_path,mutation):
    lef,f=fixture(tmp_path)
    if mutation=='wrong-module':f['module']='missing'
    if mutation=='unterminated':lef.write_text(LEF.replace('END child',''))
    if mutation=='duplicate-pin':lef.write_text(LEF.replace('END child','PIN data\nEND data\nEND child'))
    if mutation=='unknown-format':lef.write_text('this is not LEF or JSON')
    f['pins_sha256']=hashlib.sha256(lef.read_bytes()).hexdigest();(tmp_path/'freeze.json').write_text(json.dumps(f))
    with pytest.raises(ValueError):K.pins_canonical(tmp_path)


def test_macro_lef_pin_rectangles_respect_exact_named_boundaries(tmp_path):
    macros = tmp_path / "macros"
    macros.mkdir()
    (macros / "child.lef").write_bytes(r"""MACRO child
 PIN clk
  PORT
   LAYER M5 ;
   RECT 0 1 1 2 ;
  END
 END clk
 PIN child[0]
  PORT
   LAYER M4 ;
   RECT 2 3 3 4 ;
  END
END child[0] # index must terminate the exact pin name
 PIN unclosed[1]
  PORT
   LAYER M3 ;
   RECT 9 9 10 10 ;
  END
 PIN \legacy.out
  PORT
   LAYER M2 ;
   RECT 4 5 5 6 ;
  END
 END \legacy.out;
 END unclosed[1]
 PIN sig
  PORT
   LAYER M3 ;
   RECT 6 7 7 8 ;
  END
 END sig.member
 END sig
 PIN VSS
  USE GROUND ;
  PORT
   LAYER M7 ;
   RECT 8 9 9 10 ;
  END
 END VSS
END child
MACRO child_aux
 SIZE 20 BY 20 ;
END child_aux""".replace("\n", "\r\n").encode())
    assert K._lef_pins(tmp_path, {}) == {
        "child": [
            ("clk", "M5", 0, 1, 1, 2),
            ("child[0]", "M4", 2, 3, 3, 4),
            (r"\legacy.out", "M2", 4, 5, 5, 6),
        ],
        "child_aux": [],
    }
