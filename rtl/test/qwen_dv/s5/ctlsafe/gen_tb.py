from pathlib import Path
import sys
root=Path(__file__).resolve().parents[5];sys.path.insert(0,str(root/'tools'))
import die_port_bind as P
s=(Path(__file__).parent/'ctl_gate2_snapshot.sv').read_text();m=next(m for m in P.parse_modules(P.strip_comments(s),'ctl') if m.name=='qfd_dv_s5_ctl');env=m.env()
ports=[(n,m.ports[n][0],m.width(n,env)) for n in m.ports]
lines=['module tb_ctl_bounded;','reg ck=0; always #5 ck=~ck;','integer cycle,j,failures=0,compares=0; integer mutate;']
for n,d,w in ports:
 if n=='ck':continue
 lines.append(f'{"reg" if d=="input" else "wire"} [{w-1}:0] {n}{"" if d=="input" else "_ref, "+n+"_dut"};')
for typ,label,suffix in [('qfd_dv_s5_ctl','u_ref','ref'),('qfd_dv_s5_ctl_bounded4','u_dut','dut')]:
 lines.append(f'{typ} {label}('+','.join(f'.{n}({n if d=="input" else n+"_"+suffix})' for n,d,w in ports)+');')
lines+=['initial begin','mutate=$test$plusargs("mutate");','rst_n=0;','for(cycle=0;cycle<8000;cycle=cycle+1) begin','@(negedge ck);']
for n,d,w in ports:
 if d!='input' or n in ['ck','rst_n']:continue
 for lo in range(0,w,32):
  b=min(32,w-lo);lines.append(f'{n}[{lo} +: {b}]=$urandom;')
lines+=['rst_n=(cycle>=8)&&!(cycle>=1700&&cycle<1708)&&!(cycle>=4300&&cycle<4308);','@(posedge ck); #1;','if(cycle>16) begin']
for n,d,w in ports:
 if d!='output':continue
 expr=f'{n}_dut'
 if n=='w16_data':expr=f'({expr} ^ (mutate ? {w}\'d1 : {w}\'d0))'
 lines += [f'compares=compares+1; if({n}_ref !== {expr}) begin failures=failures+1; if(failures<5)$display("CTL_MISMATCH {n} cycle=%0d",cycle);end']
lines+=['end','end','if(failures) begin $display("CTL_BOUND_EQ FAIL mismatches=%0d compares=%0d",failures,compares);$finish;end','else begin $display("CTL_BOUND_EQ PASS compares=%0d cycles=%0d",compares,cycle);$finish;end','end','endmodule']
(Path(__file__).parent/'tb_ctl_bounded.sv').write_text('\n'.join(lines)+'\n')
