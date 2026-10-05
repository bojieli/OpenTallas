"""Preparation checks only: never invoke HDL compilation/elaboration/simulation."""
import importlib.util
import json
from pathlib import Path
import re
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prep',ROOT/'tools/prepare_dsrom_actual_element_gate.py')
prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)

def test_pinned_sources_and_only_common_substitution():
    sources=prep.load_sources(); generated=prep.generate(sources)
    names=set(re.findall(r'^\s*module\s+(\w+)', '\n'.join(sources.values()),re.M))
    for path,original in sources.items():
        ref=generated['ref_'+Path(path).name];cand=generated['cand_'+Path(path).name]
        assert ref==prep.namespace(original,names,'ref_')
        expected=prep.replace_helpers(original) if path=='rtl/common/ot_prefix.sv' else original
        assert cand==prep.namespace(expected,names,'cand_')
        if path!='rtl/common/ot_prefix.sv':
            assert cand==prep.namespace(original,names,'cand_')
    assert 'assign {cout,s}' in generated['cand_ot_prefix.sv']
    original=sources['rtl/common/ot_prefix.sv'];candidate=prep.replace_helpers(original)
    pattern=r'\bmodule\s+(?:ot_v41_ksadd|ot_v41_inc)\b.*?\bendmodule\b'
    assert re.sub(pattern,'HELPER',original,flags=re.S)==re.sub(pattern,'HELPER',candidate,flags=re.S)

def test_namespace_preserves_strings_comments_and_dpi():
    original='module foo; foo u(); // foo\n/* foo */ string s="foo"; import "DPI-C" function void bar(); endmodule'
    assert prep.namespace(original,{'foo'},'r_')=='module r_foo; r_foo u(); // foo\n/* foo */ string s="foo"; import "DPI-C" function void bar(); endmodule'

def test_prepare_refuses_reuse_and_records_hashes(tmp_path):
    out=tmp_path/'fresh'; receipt=prep.prepare(out)
    assert receipt['status']=='PREPARED_NOT_EXECUTED'
    for name,pin in receipt['files_sha256'].items():assert prep.sha((out/name).read_bytes())==pin
    with pytest.raises(FileExistsError):prep.prepare(out)

def test_authoritative_geometry_prerequisite_and_resource_counts():
    m=json.loads(prep.MODEL.read_text());g=m['geometry']
    assert (g['NCH'],g['NCHB'],g['NB'],g['NSEG'],g['LV'])==(16,8,2,8,5)
    assert g['LAT']==1+g['CUT'].bit_count()==8
    assert not m['prerequisites']['widening_required']
    assert m['resources']['static_per_side_per_pair']['fadd_q']==2*(2+1+1)
    assert m['resources']['static_per_side_per_pair']['fadd_bfcolumn']==2*(2+1+1+16+15)
    assert m['resources']['aggregate_memory_bytes']==4*1024**3
    for path,pin in m['new_artifact_pins'].items():assert prep.sha((ROOT/path).read_bytes())==pin

def test_connected_actual_bench_and_immutable_rom():
    b=(ROOT/'rtl/test/tb_dsrom_actual_element_gate.sv').read_text()
    assert b.count('ot_v41_pair_w17w10 #(')==2
    assert 'g_pp.u_rom0.ce_in' in b and 'g_pp.cap0' in b and 'cg_en' in b
    assert 'DIFF public' in b and 'empty go' in b and 'tag/walk scoreboard' in b
    assert 'load_phase(ph,ph==5?6:1)' in b
    cpp=(ROOT/'rtl/test/dsrom_actual_element_rom.cpp').read_text()
    assert 'svGetScope' in cpp and 'addr>=8192' in cpp
    assert 'ifstream' not in cpp and 'golden' not in cpp and 'getenv' not in cpp
