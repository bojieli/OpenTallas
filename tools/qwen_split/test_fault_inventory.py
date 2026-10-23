from pathlib import Path
import tempfile
from fault_inventory import collect,E


def test_unused_bit_sources_include_new_landing_and_dangling_net():
    rtl='module producer(input wire ck,rst_n,output wire [3:0] fault_code); endmodule\nmodule consumer(input wire [1:0] a); endmodule\nmodule qfd_landh_1_EW_65x30(input wire ck,rs,output wire fault); endmodule'
    mods={m.name:m for m in E.P.parse_modules(rtl,'rtl.sv')}
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)/'die.v';d.write_text('module die();\nwire ck,rst;\nwire [3:0] f;\nproducer p (.ck(ck),.rst_n(rst),.fault_code(f));\nconsumer c (.a(f[1:0]));\nqfd_landh_1_EW_65x30 l (.ck(ck),.rs(rst));\nendmodule\n')
        rows=collect(d,mods,{('producer','fault_code')})
        assert len(rows)==2
        assert rows[0]['unused_bits']==[2,3]
        assert rows[1]['classification']=='LANDING_FAULT_REAL_RTL'
        d.write_text(d.read_text().replace('consumer c (.a(f[1:0]));',''))
        assert collect(d,mods,{('producer','fault_code')})[0]['unused_bits']==[0,1,2,3]
