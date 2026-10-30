"""Cell evidence accepts real modern Yosys count/area tables and legacy stat."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('cell_evidence',Path(__file__).with_name('cells.py'))
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

MODERN='''=== child ===
        +----------------------------Count including submodules.
        |        +-------------------Area including submodules.
        |        |        +----------Local count, excluding submodules.
        |        |        |        +-Local area, excluding submodules.
      677   92.729      355   45.767 cells
        1    1.244        1    1.244 not_a_total_cell_name
=== top ===
    80413 1.14E+04     8818 1.48E+03 cells
=== design hierarchy ===
        +----------------------------Count including submodules.
    80413 1.14E+04     8818 1.48E+03 top
      677   92.729      355   45.767 child
'''

def test_modern_counts_use_including_children_not_local_or_sum():
    assert C.parse_stat(MODERN)=={'child':677,'top':80413}

def test_hierarchy_without_per_module_top_still_identifies_total():
    text=MODERN.replace('=== top ===\n    80413 1.14E+04     8818 1.48E+03 cells\n','')
    assert C.parse_stat(text)['top']==80413

def test_legacy_format_and_hierarchy_override_unchanged():
    text='=== child ===\nNumber of cells: 17\n=== top ===\nNumber of cells: 5\n=== design hierarchy ===\ntop 1\n child 2\nNumber of cells: 39\n'
    assert C.parse_stat(text)=={'child':17,'top':39}

def test_new_stat_does_not_invent_counts_from_net_bit_or_area_rows():
    assert C.parse_stat('=== top ===\n 999 5.0 12 0.1 wires\n 123 1.0 2 .4 wire bits\n')=={}

def test_actual_synth_stat_filename_is_read_as_stat_and_discovered(tmp_path):
    path=tmp_path/'cells'/'synth_stat.txt';path.parent.mkdir();path.write_text(MODERN)
    assert C.load_source(path,{}, {})==[('modules',{'child':677,'top':80413})]
    assert C.discover(tmp_path)==[path]


def test_pure_hierarchy_local_zero_dash_keeps_measured_total():
    text='=== top ===\n 38 1.0 - - cells\n=== design hierarchy ===\n 38 1.0 - - top\n'
    assert C.parse_stat(text)=={'top':38}
