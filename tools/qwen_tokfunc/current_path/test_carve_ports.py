from pathlib import Path
import importlib.util

SRC=Path(__file__).resolve().parents[1]/'xdie_bound/bound_carve.py'
spec=importlib.util.spec_from_file_location('bound_carve_test',SRC)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


def test_phy_line_ports_survive_a_literal_carve(tmp_path):
    (tmp_path/'phy.sv').write_text('''module phy (
    input wire clk,
    input wire far_v,
    input wire [582:0] far_flit,
    output wire link_v,
    output wire [582:0] link_flit
);
endmodule
''')
    top=tmp_path/'top.sv'
    text='''module chip (
    input wire clk_core,
    input wire sys_c_far_v,
    input wire [582:0] sys_c_far_flit,
    output wire sys_c_link_v,
    output wire [582:0] sys_c_link_flit
);
    phy sys_c (
        .clk(clk_core),
        .far_v(sys_c_far_v),
        .far_flit(sys_c_far_flit),
        .link_v(sys_c_link_v),
        .link_flit(sys_c_link_flit)
    );
endmodule
'''
    top.write_text(text)
    r=C.carve(top,['sys_c'],'cut',tmp_path/'out')
    assert r['inputs']['sys_c_far_flit']['width']==583
    assert r['outputs']['sys_c_link_flit']['width']==583
    assert r['outputs']['sys_c_link_v']['drivers']==['sys_c.link_v']
    instance=text[text.index('    phy sys_c ('):text.index('    );')+6]
    assert instance in (tmp_path/'out/cut.v').read_text()


def test_port_cache_cannot_mix_different_bound_revisions(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b';a.mkdir();b.mkdir()
    (a/'same.sv').write_text('module same (\ninput wire p\n);\nendmodule\n')
    (b/'same.sv').write_text('module same (\noutput wire p\n);\nendmodule\n')
    assert C.ports_of(a,'same')['p']=='input'
    assert C.ports_of(b,'same')['p']=='output'
