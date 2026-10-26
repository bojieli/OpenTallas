"""Selected TKM chain ABI: native control relays and no functionally dead ID pin.
The profile is bounded to the TP192 split tile; all member wiring stays unchanged.
"""
import re

def apply(text, ports):
    assert re.search(r"module ot_hgi_coll_tkm_tp192_tile_core\s*\(", text)
    assert [p for p in ports if p[0]=='tile_tid']==[['tile_tid','input',6,0]]
    assert not any(p[0] in ('tile_clr_o','tile_conv_o') for p in ports)
    text,n=re.subn(r"(?m)^    input wire \[5:0\] tile_tid,?\n",'',text)
    assert n==1, 'expected one dead ID input declaration'
    text,n=re.subn(r"(?m)^    assign u_tile__tid = tile_tid;[^\n]*", "    assign u_tile__tid = 6'b000000;   // dead tau-only ID; owner ruling 10-25 14:44",text)
    if n!=1:
        text,n=re.subn(r"assign u_tile__tid\[(\d)\] = tile_tid\[\1\];",lambda m:"assign u_tile__tid["+m[1]+"] = 1'b0;",text)
        assert n==6, 'ID member binding must be complete'
    anchor='    input wire tile_conv,'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    output reg tile_clr_o,\n    output wire tile_conv_o,')
    assert text.count('endmodule')==1
    text=text.replace('endmodule',"    // Native chain control: clr +1 core edge; conv +0 core edge (shells remain separately priced).\n    always @(posedge tile_clk) tile_clr_o <= tile_clr;\n    assign tile_conv_o = tile_conv;\nendmodule")
    ports=[p for p in ports if p[0]!='tile_tid']+[['tile_clr_o','output',1,0],['tile_conv_o','output',1,0]]
    return text,ports
