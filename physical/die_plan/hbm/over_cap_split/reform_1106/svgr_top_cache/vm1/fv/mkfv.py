# DIE-HBM-91-OPEN vM1 formal copies: insert invariant asserts (FORMAL only) into module copies.
import sys,re
from pathlib import Path
ref=Path(sys.argv[1]); new=Path(sys.argv[2]); out=Path(sys.argv[3]); out.mkdir(exist_ok=True)
def module(text,name):
    m=re.search(r"^module "+name+r"\b.*?^endmodule",text,re.S|re.M); assert m,name; return m.group(0)
cc_ref=(ref/'ot_svgr_top_cachecut.sv').read_text(); cc_new=(new/'ot_svgr_top_cachecut.sv').read_text()
g=module(cc_ref,'ot_svgr_prod_s_cachecut')
inv_g=(" // FV invariant (gold): read_ordinal_q == o_ord, p_rq[d] == p_ord[d]\n"
       " always @* begin assert(read_ordinal_q==o_ord); for(d=0;d<DLY;d=d+1) assert(p_rq[d]==p_ord[d]); end\n")
g=g.replace("\nendmodule","\n"+inv_g+"endmodule")
(out/'prod_gold.sv').write_text("`default_nettype none\n"+g+"\n")
n=module(cc_new,'ot_svgr_prod_s_cachecut')
a="  always @(posedge stream_clk or negedge srst)if(!srst)rsel<=8'd1;else rsel<=8'd1<<p_ord[DLY-2][2:0];\n"
assert n.count(a)==1
n=n.replace(a,a+"  always @* assert(rsel==(8'd1<<p_ord[DLY-1][2:0]));\n")
(out/'prod_gate.sv').write_text("`default_nettype none\n"+n+"\n")
ca=(new/'ot_svgr_cache136_native.sv').read_text()
a="  genvar wi;for(wi=0;wi<4;wi=wi+1)begin:g_wsel assign wsel[wi]=(wptr<<wi)|(wptr>>(16-wi));end"
assert ca.count(a)==1
ca=ca.replace(a,a+"\n  always @* if(WOH!=0)assert(wptr==(16'd1<<received[3:0]));")
(out/'cache_gate.sv').write_text(ca)
print("ok")
