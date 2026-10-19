"""Fleet-only experiment: fixed age for odd-hop source-forwarded local rings."""
from pathlib import Path
import subprocess
import tempfile
import os

ROOT = Path(__file__).resolve().parents[2]


def main():
    with tempfile.TemporaryDirectory(prefix='stream_land_', dir=ROOT / 'tools/landed_parent') as td:
        d = Path(td)
        (d / 'tb.sv').write_text(r'''`timescale 1ns/1ps
module tb;
  reg src=0; always #0.5 src=~src;
  // Source edges are .5+n. Destination roots compensate to the same epoch,
  // with independent offsets at both extremes of the proposed 80ps allowance.
  reg [2:0] dst=0;
  initial begin #0.42; forever begin dst[0]=1; #0.5; dst[0]=0; #0.5; end end
  initial begin #0.50; forever begin dst[1]=1; #0.5; dst[1]=0; #0.5; end end
  initial begin #0.58; forever begin dst[2]=1; #0.5; dst[2]=0; #0.5; end end
  reg rsi=0;
  reg [343:0] data=0;
  wire [343:0] out[0:5];
  function automatic [343:0] word(input integer n);
    for(integer b=0;b<344;b=b+1) word[b]=(((n*12347)+(b*977)) >> (b%17)) & 1;
  endfunction
  genvar p,h;
  generate for(p=0;p<3;p=p+1) begin:gp
    for(h=0;h<2;h=h+1) begin:gh
      ot_pl_stream_land #(.W(344),.HOPS(1+2*h)) u(src,dst[p],rsi,data,out[p*2+h]);
      integer n=-1,run=0,checks=0;
      always @(posedge dst[p]) begin
        n=n+1;
        if(!rsi) run=0; else run=run+1;
        #0.001;
        // Actual reset warm protocol, not arbitrary discarded comparison:
        // epoch1 + leaf1 + rq1 + ring4 writes + capture1. Full stable stream then exact age3.
        if(run>=10) begin
          if(out[p*2+h] !== word(n-3))
            $fatal(1,"stream mismatch phase%0d hops%0d n%0d",p,1+2*h,n);
          checks=checks+1;
        end
        if(n==1199) begin
          if(checks<1100) $fatal(1,"insufficient comparisons");
          $display("STREAM_LAND phase%0d hops%0d PASS checks%0d",p,1+2*h,checks);
        end
      end
    end
  end endgenerate
  integer source_n=0;
  always @(posedge src) begin data <= word(source_n); source_n=source_n+1; end
  integer n;
  initial begin
    for(n=0;n<1200;n=n+1) begin
      // Change only at safe source falling edge (away from both root phases).
      rsi=!(n<8 || (n>=600 && n<=608));
      if(n==608) begin #0.501; rsi=1; #0.499; end
      else #1;
    end
    #0.9; $finish;
  end
endmodule
''')
        transport = ROOT/'rtl/common/landed_parent/ot_pl_stream_land.sv'
        mutant = os.environ.get('STREAM_MUTANT') == '1'
        if mutant:
            changed = transport.read_text().replace('.i(payload[HOPS])', '.i(payload[0])')
            assert changed != transport.read_text()
            transport = d/'bypass_payload_mutant.sv'
            transport.write_text(changed)
        subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb',
                        '--Mdir', str(d/'obj'), '-o', 'sim', str(d/'tb.sv'),
                        str(ROOT/'rtl/common/landed_parent/ot_pl_land.sv'),
                        str(transport)], check=True)
        sim = subprocess.run([str(d/'obj/sim')], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(sim.stdout, end='')
        if mutant:
            assert sim.returncode != 0 and 'stream mismatch' in sim.stdout, 'mutant did not witness actual payload age mismatch'
            print('STREAM_LAND BYPASS_PAYLOAD_MUTANT WITNESS PASS')
        else:
            sim.check_returncode()


if __name__ == '__main__':
    main()
