from pathlib import Path
p=Path(__file__).parent
s=(p/'coupon.sv').read_text()
mut={"or":s.replace('y<=a_q ^ b_q','y<=a_q | b_q'),
"bypass":s.replace('y<=a_q ^ b_q','y<=a ^ b'),
"reset_early":s.replace('u_reset_b(clk,rst_n,reset_first,reset_b)','u_reset_b(clk,rst_n,1\'b1,reset_b)'),
"reset_missing":s.replace('if(!rst_n) q<=0','if(!rst_n) q<=1')}
for n,v in mut.items():
 assert v!=s
 (p/('mut_'+n+'.sv')).write_text(v)
