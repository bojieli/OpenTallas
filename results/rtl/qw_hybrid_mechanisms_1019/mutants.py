from pathlib import Path
s=Path('qfd_d8_mechanism.sv').read_text()
mutants={
 'slot':('wire [2:0] slot=expected[2:0];','wire [2:0] slot=expected[2:0]^3\'d1;'),
 'epoch':("record={1'b1,wc,din}","record={1'b1,(wc^4'd1),din}"),
 'written':("record={1'b1,wc,din}","record={1'b0,wc,din}"),
 'enable':('&& w_en;','&& !w_en;'),
 'metadata':('dout<=readword[W-1:0]','dout<=(readword[W-1:0] ^ ({{(W-1){1\'b0}},1\'b1} << (W-1)))'),
 'pending_reset':('pe<=0;pv<=0;pr<=0;','pe<=0;'),
}
for name,(old,new) in mutants.items():
 assert old in s,name
 Path('mut_'+name+'.sv').write_text(s.replace(old,new))
