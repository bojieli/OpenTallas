import sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text()
old = """  reg[31:0] la,lb;
  always @*begin
   la=32'd0;lb=32'd0;
   case(js)
    3'd1:begin la=tb[0][32*g+:32];lb=(MUT==1)?tb[2][32*g+:32]:tb[1][32*g+:32];end
    3'd2:begin la=(MUT==1)?tb[1][32*g+:32]:tb[2][32*g+:32];lb=tb[3][32*g+:32];end
    3'd3:begin la=tb[4][32*g+:32];lb=tb[5][32*g+:32];end
    3'd4:begin la=tb[6][32*g+:32];lb=tb[7][32*g+:32];end
    3'd5:begin la=xr[32*g+:32];lb=jy[32*g+:32];end
    3'd6:begin la=yr[32*g+:32];lb=jy[32*g+:32];end
    default:;
   endcase
  end
"""
new = """  // KV-KITS-16 10-28: the operand muxes take ONE-HOT registered selects, one kept copy per operand (sa for la, sb for
  // lb; same next state nsel and edge as js, so la/lb are unchanged on every cycle). Each select bit drives the 32 AND
  // terms of one operand; js only issues the adder. Routed pv_join 4ea738599325/49aa312a473a: the 3-bit js decode fanned
  // out through 46/17/28-load buffer trees (slew 218 ps) into the adder s1 cone, TT setup -57.34/-41.61 ps. 0 cycles.
  (* keep = "true", dont_touch = "true" *) reg[6:1] sa;
  (* keep = "true", dont_touch = "true" *) reg[5:1] sb;   // sb[5] = slots 5 and 6 (lb = jy in both)
  always @(posedge clk or negedge local_rst_n)if(!local_rst_n)begin sa<=6'd0;sb<=5'd0;end else begin
   sa<={nsel==3'd6,nsel==3'd5,nsel==3'd4,nsel==3'd3,nsel==3'd2,nsel==3'd1};
   sb<={nsel==3'd5||nsel==3'd6,nsel==3'd4,nsel==3'd3,nsel==3'd2,nsel==3'd1};
  end
  wire[31:0] la=({32{sa[1]}}&tb[0][32*g+:32])|({32{sa[2]}}&((MUT==1)?tb[1][32*g+:32]:tb[2][32*g+:32]))|
                ({32{sa[3]}}&tb[4][32*g+:32])|({32{sa[4]}}&tb[6][32*g+:32])|
                ({32{sa[5]}}&xr[32*g+:32])|({32{sa[6]}}&yr[32*g+:32]);
  wire[31:0] lb=({32{sb[1]}}&((MUT==1)?tb[2][32*g+:32]:tb[1][32*g+:32]))|({32{sb[2]}}&tb[3][32*g+:32])|
                ({32{sb[3]}}&tb[5][32*g+:32])|({32{sb[4]}}&tb[7][32*g+:32])|({32{sb[5]}}&jy[32*g+:32]);
"""
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, new)); print("PATCHED", p)
