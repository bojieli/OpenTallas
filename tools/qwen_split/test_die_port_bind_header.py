"""Real x-tap ANSI headers retain ports despite comment-local header terminators."""
from pathlib import Path
import pytest
from qwen_split.die_port_bind import header, evalw

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv'
EXPECTED={'ck':('input',1),'rst_n':('input',1),'sw':('input',2137),
          'aw':('input',553),'xpf':('input',72),'gi':('input',380),
          'hw_d':('output',1567),'he_d':('output',1567),
          'hw_f':('input',1),'he_f':('input',1),'fault':('output',1)}


def actual_module():
    text=SOURCE.read_text()
    start=text.index('module qfd_xs_tap ')
    return text[start:text.index('endmodule',start)+len('endmodule')]


def parsed(text):
    params,ports=header(text,'qfd_xs_tap')
    return params,{p:(d,evalw(w,params)) for p,(d,w) in ports.items()}


def test_actual_xs_tap_header_including_bench_mutant_comment():
    text=actual_module()
    assert '// bench-only mutant (1: no rounding);' in text
    params,ports=parsed(text)
    assert params=={'NW':'18','AW':'24','XCW':'12','MUT':'0'}
    assert ports==EXPECTED


@pytest.mark.parametrize('comment',[
    '// early terminator ); and fake input wire bogus,\n',
    '/* early terminator ); input wire bogus, */',
    '/* line-like comment // ignored ); */',
    '// fake module qfd_xs_tap(input wire bogus);\n'])
def test_comment_delimiter_mutants_do_not_change_real_ports(comment):
    text=actual_module().replace('input  wire          ck,',comment+'input  wire          ck,',1)
    assert parsed(text)[1]==EXPECTED


def test_real_port_mutations_remain_visible():
    text=actual_module()
    renamed=text.replace('input  wire          ck,','input  wire          clk,',1)
    assert 'ck' not in parsed(renamed)[1] and parsed(renamed)[1]['clk']==('input',1)
    widened=text.replace('[3*NW+13*AW+13:0]  gi','[3*NW+13*AW+14:0]  gi',1)
    assert parsed(widened)[1]['gi']==('input',381)


def test_commented_module_is_not_a_real_header():
    assert header('// module qfd_xs_tap(input wire bogus);\n','qfd_xs_tap')==(None,None)
    assert header('/* module qfd_xs_tap(input wire bogus); */','qfd_xs_tap')==(None,None)
