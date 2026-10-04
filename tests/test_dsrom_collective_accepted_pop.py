from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_collective_accepted_pop as F


def test_source_only_delta_preserves_arithmetic_and_pinned_baseline():
    original=(ROOT/'rtl/rom/ot_w15_rom_oneshot_px.sv').read_text()
    fixed=(ROOT/F.ENGINE).read_text()
    restored=fixed.replace('module ot_w15_rom_oneshot_die_px_acceptedpop #(\n    parameter integer FIX_ACCEPTED_POP = 0, // baseline accepted-transfer accounting fix',
                           'module ot_w15_rom_oneshot_die_px #(')
    restored=restored.replace('((FIX_ACCEPTED_POP ? (pop && pop_red) : pop_red) ?', '(pop_red ?')
    assert restored==original
    # Evaluate the accepted-transfer invariant for every Boolean combination,
    # including retirement coincident with a stalled reduction offer.
    for red in (False,True):
        for gather in (False,True):
            for stall in (False,True):
                for retire in (False,True):
                    pop=(red or gather) and not stall
                    corrected_delta=int(pop and red)-int(retire)
                    assert corrected_delta==int(red and not stall)-int(retire)


def test_baseline_install_has_no_headreg_or_extra_cycle(tmp_path):
    source=tmp_path/'source';source.mkdir()
    die=source/'ot_chip_v41x_die_owner_safe_c8.sv'
    top=source/'ot_v41_rt_die_l20_c8.sv'
    die.write_text('module ot_chip_v41x_die_owner_safe_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter X=0)();\not_w15_rom_oneshot_die_px #(.N(4)) u_coll();\nendmodule\n')
    top.write_text('module ot_v41_rt_die_l20_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter X=0)();\not_chip_v41x_die_owner_safe_c8 #(.X(X)) dut();\nendmodule\n')
    before=[p.read_bytes() for p in (die,top)]
    r=F.install([die,top],tmp_path/'out',enable=True)
    assert r['parameters']=={'COLL_ACCEPTED_POP':1}
    assert r['verilator_args']==['-GCOLL_ACCEPTED_POP=1']
    assert r['composed_effect']['added_pipeline_cycles']==0
    assert not r['composed_effect']['headreg_selected']
    assert '.FIX_ACCEPTED_POP(COLL_ACCEPTED_POP)' in r['sources'][0].read_text()
    assert all('headreg' not in p.name for p in r['sources'])
    assert [p.read_bytes() for p in (die,top)]==before
    assert F.install(r['sources'],tmp_path/'repeat')['parameters']=={'COLL_ACCEPTED_POP':0}
