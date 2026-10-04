import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_isa_v41 as I
import uarch_model as U
import dsrom_s81_native_he_bootstrap_build as B


def test_native_he_literal_offsets_match_actual_fullshape_ISA():
 text=(ROOT/'tools/runtime/dsrom/s81_native_he_bootstrap.hpp').read_text()
 layout=I.layout_for(full_shape=True)
 for name in ['he_nout','he_k','he_wbase','he_xbase','he_obase','mx_m','mx_xps','mx_ops']:
  target=name if name.startswith('he_') else 'he_'+name.removeprefix('mx_')
  match=re.search(r'input\.'+target+r'=field\(op,(\d+),(\d+)\)',text)
  assert match and tuple(map(int,match.groups()))==layout[name]
 literal=(ROOT/'tools/runtime/dsrom/s81_minimum_prefix.cpp').read_text()
 match=re.search(r'DsromS81PrefixOperation\{1, 5, "[^"]+", \{([^}]+)',literal)
 words=[int(x,16) for x in re.findall(r'0x([a-f0-9]+)u',match[1])]
 op=I.decode(sum(x<<(32*j) for j,x in enumerate(words)),full_shape=True)
 assert (op['he_nout'],op['he_k'],op['he_xbase'],op['he_obase'])==(24,2560,0,41024)


def test_actual_HE_and_chunk8_sources_only_with_positive_model_costs():
 m=U.dsrom_s81_native_he_bootstrap()
 assert m['HE']['FP32_MAC_lanes']==64 and m['HE']['input_LOAD_read_edges']==2560
 assert m['HE']['minimum_issue_edges']==7680
 assert m['SSX']['SW']==256 and m['SSX']['source_H_words']==20480
 assert m['SSX']['vector_accepts']==80 and m['SSX']['result_address']==40960
 assert m['adapter']['reserved_HE_write_seats']==32 and m['adapter']['DFF_cell_floor_mm2']>0
 assert m['PF']['addresses']==list(range(41152,41156))
 assert m['combined_single_user_added_us'] is None and not m['adopted']
 sources=B.SOURCES
 assert 'rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv' in sources
 assert 'rtl/hdc/ot_hdc_sfu.sv' in sources # original ot_hdc_vline provider
 assert not any('hcproj' in p or 'prefix_sim' in p for p in sources)


def test_adapter_header_compiles_and_has_no_FP_interpreter(tmp_path):
 p=tmp_path/'header.cpp';p.write_text('#include "s81_native_he_bootstrap.hpp"\nint main(){return 0;}\n')
 subprocess.run(['g++','-std=c++17','-fsyntax-only','-I'+str(ROOT/'tools/runtime/dsrom'),str(p)],check=True)
 text=(ROOT/'tools/runtime/dsrom/s81_native_he_bootstrap.hpp').read_text()
 assert 'ports.scalar_visible' in text and 'ports.HE_visible' in text
 assert 'HE reserved 32-word publication queue overflow' in text
 assert 'ssx_seen' in text and 'vector==80' in text
 assert not re.search(r'\b(float|double|sqrt|fma|golden)\s*\(',text)


def test_current_pin_inventory_and_model_exact_replay():
 pins=B.pin()
 assert len(pins)==len(B.SOURCES) and all(len(x)==64 for x in pins.values())
 p=ROOT/'results/uarch/dsrom_s81_native_he_bootstrap_20261004/model.json'
 assert json.loads(p.read_text())==U.dsrom_s81_native_he_bootstrap()
