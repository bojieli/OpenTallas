#!/usr/bin/env python3
"""Exercise actual reset tile source over varied phase assertion/release; mutant adds one release cycle."""
import argparse, pathlib, subprocess, tempfile
p=argparse.ArgumentParser();p.add_argument('--mutant', action='store_true');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='hbfd_rrl_') as td:
 d=pathlib.Path(td)
 src=(root/'rtl/hbm_accel/die_glue/hbfd_rrl.sv').read_text()
 if a.mutant:
  src=src.replace('assign rst_n = q;', "reg q2; always @(posedge clk or negedge rst_n_in) if (!rst_n_in) q2 <= 0; else q2 <= q; assign rst_n = q2;")
 (d/'dut.sv').write_text(src)
 (d/'tb.sv').write_text("""`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rn=1; wire s,h; integer k,j,checks=0;
hbfd_rrl_sync us(clk,rn,s); hbfd_rrl_hop uh(clk,rn,h);
initial begin
 for(j=0;j<24;j=j+1) begin
  #1.13; rn=0; #0.02;
  if(s!==0 || h!==0) $fatal(1,"ASSERT async"); checks=checks+2;
  repeat(2) @(negedge clk);
  #(0.17+j*0.09); rn=1;
  for(k=1;k<=5;k=k+1) begin
   @(posedge clk); #0.01;
   if(s!==(k>=3) || h!==(k>=1)) $fatal(1,"RELEASE age cycle=%0d sync=%b hop=%b",k,s,h);
   checks=checks+2;
  end
  @(negedge clk);
 end
 $display("RESET_TILE PASS checks=%0d trials=24 sync_age=3 hop_age=1",checks); $finish;
end
endmodule
""")
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(d/'tb.sv'),str(d/'dut.sv'),str(root/'rtl/lib/ot_rst_relay.sv')],check=True)
 raise SystemExit(subprocess.run(['vvp',str(d/'sim')]).returncode)
