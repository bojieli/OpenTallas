import json,re,pathlib
root=pathlib.Path(__file__).resolve().parents[3]; out=pathlib.Path(__file__).parent
profiles=json.load(open(root/'results/head_lep_next_1029/leaf_profiles.json'))
s=['`timescale 1ns/1ps','module tb_native_cut;','reg clk=0; always #5 clk=~clk;','integer n,j; reg [31:0] rnd=32\'h71bc2d09;','function automatic [31:0] rng(input [31:0] x); rng=x^(x<<13)^((x^(x<<13))>>17)^(((x^(x<<13))^((x^(x<<13))>>17))<<5); endfunction']
checks=[]; drive=[]
for role in ('ep','credit'):
 text=(root/f'rtl/dsrom_sys/s81_head/ot_s81hd_{role}_native.sv').read_text()
 ports=re.findall(r'(input|output) wire (\[[^]]+\] )?(\w+)',text.split(');',1)[0])
 con=[]; ref=[]
 for direction,width,name in ports:
  if name=='clk': con.append('.clk(clk)');ref.append('.clk(clk)');continue
  v=f'{role}_{name}'; w=width or ''
  if direction=='input':
   s.append(f'reg {w}{v};');drive.append((v,name))
   con.append(f'.{name}({v})'); ref.append(f'.{name}({v})')
  else:
   s.append(f'wire {w}{v}_g,{v}_d;');con.append(f'.{name}({v}_d)');ref.append(f'.{name}({v}_g)')
   checks.append(f'if ({v}_d !== {v}_g) $fatal(1,"MISMATCH {v} at %0d",n);')
 s.append(f'ot_s81hd_{role}_native dut_{role}('+','.join(con)+');')
 if role=='ep':
  params=','.join(f'.{k}({v})' for k,v in profiles['ep']['parameters'].items())
  s.append('ot_s81ph_link_ep_safe4 #('+params+') ref_ep('+','.join(ref)+",.ch_b(1'b1));")
 else:
  # Instantiate the original two natural modules directly, independently of wrapper.
  s.append('ot_link_credit_rx_b64 #(.W(553),.DEPTH(12),.WFREE(1),.LOCAL_HIT(1),.LOCAL_POP(1)) ref_ski(.clk(clk),.rst_n(credit_rst_in_n),.head_rst_n(credit_head_rst_n),.l_valid(credit_lo_v),.l_data(credit_lo_d),.l_credit(credit_lo_r_g),.o_valid(credit_ep_in_v_g),.o_ready(credit_ep_in_r),.o_data(credit_ep_in_d_g),.fault(credit_fault_g));')
  s.append('ot_link_credit_tx_rc #(.W(553),.CRED(12),.NR(3)) ref_sko(.clk(clk),.rst_n(credit_rst_out_n),.i_valid(credit_ep_out_v),.i_ready(credit_ep_out_r_g),.i_data(credit_ep_out_d),.l_valid(credit_li_v_g),.l_data(credit_li_d_g),.l_credit(credit_li_r));')
s+=['initial begin']
for v,name in drive: s.append(f'{v}=0;')
s+=['for(n=0;n<1024;n=n+1) begin','@(negedge clk);']
for v,name in drive:
 if 'rst' in name:s.append(f'{v}= (n<8 || (n>=510 && n<518)) ? 0 : \'1;')
 else:s.append(f'for(j=0;j<$bits({v});j=j+1) begin rnd=rng(rnd); {v} = ({v} << 1) | rnd[0]; end')
# use a single scalar/vector-independent random assignment based on $bits with shift
s=[re.sub(r'(\w+)\[j\]=rnd\[0\]',r'\1 = (\1 << 1) | rnd[0]',line) for line in s]
s+=['@(posedge clk); #1;']+checks+['if(n==20 && $test$plusargs("mutant")) begin if ((~credit_lo_r_d) !== credit_lo_r_g) $fatal(1,"MUTANT CAUGHT ready polarity"); end','end','$display("NATIVE_CUT PASS cycles=%0d",n); $finish; end','endmodule']
(out/'tb_native_cut.sv').write_text('\n'.join(s)+'\n')
