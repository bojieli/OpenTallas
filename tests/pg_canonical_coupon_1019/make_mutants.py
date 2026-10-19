from pathlib import Path
p=Path(__file__).parent
s=(p/'coupon.sv').read_text()
mut={"or":s.replace('y<=a_q ^ b_q','y<=a_q | b_q'),
"bypass":s.replace('y<=a_q ^ b_q','y<=a ^ b'),
"reset_early":s.replace('reset_b<=reset_first','reset_b<=1'),
"reset_missing":s.replace('reset_b<=0','reset_b<=1')}
for n,v in mut.items():
 assert v!=s
 (p/('mut_'+n+'.sv')).write_text(v)
