#!/usr/bin/env python3
"""L2H-GEN2D-RST 10-19: exercise the compact carrier tiles (rtl/hbm_accel/die_glue/hbfd_rrl_c.sv) over varied phase
assertion/release and mid-release reassertion: csync age 3, chop age 1, cpad<N> age exactly N for N = 1..255, every
output low immediately on rst_n_in low.  --mutant compiles with OT_HBFD_RRLC_MUT (counter one edge early) and must FAIL."""
import argparse, pathlib, subprocess, tempfile
p = argparse.ArgumentParser(); p.add_argument('--mutant', action='store_true'); a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[2]
PADS = list(range(1, 256))
with tempfile.TemporaryDirectory(prefix='hbfd_rrlc_') as td:
    d = pathlib.Path(td)
    inst = ''.join(f'wire p{n}; hbfd_rrl_cpad{n} up{n}(clk,rn,p{n});\n' for n in PADS)
    asrt = ' || '.join(f'p{n}!==0' for n in PADS)
    rel = ' || '.join(f'p{n}!==(k>={n})' for n in PADS)
    (d / 'tb.sv').write_text("""`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rn=1; wire s,h; integer k,j,checks=0;
hbfd_rrl_csync us(clk,rn,s); hbfd_rrl_chop uh(clk,rn,h);
""" + inst + """
initial begin
 for(j=0;j<12;j=j+1) begin
  #1.13; rn=0; #0.02;
  if(s!==0 || h!==0) $fatal(1,"ASSERT async"); checks=checks+2;
  if(""" + asrt + """) $fatal(1,"ASSERT async pad"); checks=checks+""" + str(len(PADS)) + """;
  repeat(2) @(negedge clk);
  #(0.17+j*0.31); rn=1;
  for(k=1;k<=(j%4==1 ? 40 : 260);k=k+1) begin
   @(posedge clk); #0.01;
   if(s!==(k>=3) || h!==(k>=1)) $fatal(1,"RELEASE age cycle=%0d sync=%b hop=%b",k,s,h);
   if(""" + rel + """) $fatal(1,"RELEASE age pad cycle=%0d",k);
   checks=checks+2+""" + str(len(PADS)) + """;
  end
  // j%4==1: reassert in flight (counters part-way), the next trial checks a full clean release from there
  #3.3; rn=0; #0.02; if(s!==0 || h!==0 || """ + asrt + """) $fatal(1,"ASSERT async mid-cycle"); checks=checks+1;
  @(negedge clk);
 end
 $display("RESET_CARRIER PASS checks=%0d trials=12 csync_age=3 chop_age=1 cpad_ages=1..255",checks); $finish;
end
endmodule
""")
    cmd = ['iverilog', '-g2012', '-s', 'tb', '-o', str(d / 'sim')] + (['-DOT_HBFD_RRLC_MUT'] if a.mutant else []) + \
          [str(d / 'tb.sv'), str(root / 'rtl/hbm_accel/die_glue/hbfd_rrl_c.sv'), str(root / 'rtl/lib/ot_rst_relay.sv')]
    subprocess.run(cmd, check=True)
    raise SystemExit(subprocess.run(['vvp', str(d / 'sim')]).returncode)
