#!/usr/bin/env python3
"""Optional fixed-position R8 ABI v2. Derive taps from the actual word ledger; v1 is untouched."""
import argparse,json,re
from pathlib import Path
ABI="kv_pc_r8_position_bank_v2_fixed_decode"
STACKS=("WS","WN","ES","EN")
WIDTH={"x__tok":18,"x__tep":16}
def generate(ledger,out,rtl):
 d=json.loads(Path(ledger).read_text()); rows={}
 for m in d["members"]:
  match=re.fullmatch(r"slg_(WS|WN|ES|EN)_([0-6])",m["sink"])
  if not match or m["sink_port"] not in WIDTH:raise ValueError("not a declared PC position word")
  stack,group=STACKS.index(match[1]),int(match[2]);port=m["sink_port"]
  profile=1 if m["base_type"]=="kv3_pc" else 0 if m["base_type"]=="kv3_pc_v1" else None
  if profile is None or (profile==1)!=(group==4):raise ValueError("physical profile/position mismatch")
  if type(m["pad"]) is not int or not 0<=m["pad"]<=127:raise ValueError("unsupported delay")
  cover={i for lo,hi in m["sink_bits"] for i in range(lo,hi+1)}
  if cover!=set(range(WIDTH[port])):raise ValueError("ledger must contain one complete word")
  key=(stack,group,port)
  if key in rows:raise ValueError("duplicate position word")
  rows[key]=dict(profile=profile,pad=m["pad"],member=m["id"],physical_type=m["physical_type"])
 expected={(s,g,p) for s in range(4) for g in range(7) for p in WIDTH}
 if set(rows)!=expected:raise ValueError("incomplete 28-position/two-word census")
 profiles={}
 for profile in (0,1):
  subset={k:v for k,v in rows.items() if v["profile"]==profile}
  t=max(v["pad"] for k,v in subset.items() if k[2]=="x__tok")
  e=max(v["pad"] for k,v in subset.items() if k[2]=="x__tep")
  n=len(subset)//2
  profiles[profile]=dict(tok_max=t,epoch_max=e,instances=n,ff_per_instance=18*t+16*e)
 victim=next(k for k,v in sorted(rows.items()) if k[2]=="x__tok" and v["pad"]>0)
 functions=[]
 for port,fn in (("x__tok","tok_count"),("x__tep","epoch_count")):
  body=[f"function automatic integer {fn}(input [1:0] s,input [2:0] g);","begin",f" {fn}=0;"]
  for profile in (0,1):
   body += [f" if (PROFILE=={profile}) case ({{s,g}})"]
   for (s,g,p),v in sorted(rows.items()):
    if p==port and v["profile"]==profile and v["pad"]:
     body += [f" 5'd{s*8+g}: {fn}={v['pad']};"]
   body += [f" default: {fn}=0;"," endcase"]
  if port=="x__tok":
   s,g,_=victim
   body += [f" if (MUT==1 && s==2'd{s} && g==3'd{g}) {fn}={rows[victim]['pad']-1};"]
  body += ["end","endfunction"];functions.append("\n".join(body))
 p0,p1=profiles[0],profiles[1]
 text=f"""// Generated from the actual R8 word ledger. OPTIONAL COPY; not a physical release.
// Existing static position IDs only. No software/runtime delay selector or new wrapper pins.
(* keep_hierarchy=1 *)
module kv_pc_r8_position_bank_v2 #(parameter integer PROFILE=0,parameter integer MUT=0)
(input wire clk,input wire[1:0] stack_id,input wire[2:0] group_id,
 input wire[17:0] tok_i,input wire[15:0] epoch_i,output wire[17:0] tok_o,output wire[15:0] epoch_o);
localparam integer TOK_MAX=(PROFILE==1)?{p1['tok_max']}:{p0['tok_max']};
localparam integer EPOCH_MAX=(PROFILE==1)?{p1['epoch_max']}:{p0['epoch_max']};
{functions[0]}
{functions[1]}
wire [7:0] tok_tap=tok_count(stack_id,group_id);
wire [7:0] epoch_tap=epoch_count(stack_id,group_id);
generate
 if (TOK_MAX>0) begin:gt
  (* keep=1 *) reg[17:0] pipe[0:TOK_MAX-1];
  for(genvar j=0;j<TOK_MAX;j=j+1) begin:r
   if(j==0) always @(posedge clk) pipe[j]<=tok_i;
   else always @(posedge clk) pipe[j]<=pipe[j-1];
  end
  assign tok_o=(tok_tap==0)?tok_i:pipe[tok_tap-1];
 end else assign tok_o=tok_i;
 if(EPOCH_MAX>0) begin:ge
  (* keep=1 *) reg[15:0] pipe[0:EPOCH_MAX-1];
  for(genvar j=0;j<EPOCH_MAX;j=j+1) begin:r
   if(j==0) always @(posedge clk) pipe[j]<=epoch_i;
   else always @(posedge clk) pipe[j]<=pipe[j-1];
  end
  assign epoch_o=(epoch_tap==0)?epoch_i:pipe[epoch_tap-1];
 end else assign epoch_o=epoch_i;
endgenerate
endmodule
"""
 rtl=Path(rtl);rtl.parent.mkdir(parents=True,exist_ok=True);rtl.write_text(text)
 variants=[]
 for s in range(4):
  for g in range(7):
   v=rows[(s,g,"x__tok")]
   variants.append(dict(stack=s,group=g,profile=v["profile"],tok=rows[(s,g,"x__tok")]["pad"],epoch=rows[(s,g,"x__tep")]["pad"]))
 cost=sum(p["instances"]*p["ff_per_instance"] for p in profiles.values())
 result=dict(abi=ABI,scope=d["scope"],source=d["source"],source_sha256=d["source_sha256"],
             profiles=profiles,variants=variants,words=[dict(stack=s,group=g,port=p,**v) for (s,g,p),v in sorted(rows.items())],
             new_wrapper_pins=0,static_id_inputs=5,old_ff=28*52,new_ff=cost,extra_ff=cost-28*52,
             mutant_position=dict(stack=victim[0],group=victim[1]),
             physical_qualified=False,default_enabled=False,
             remaining="Does not solve fault-OR leg or header boot-go R8 conflicts; current RT20 ledger must be regenerated before adoption")
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/"contract.json").write_text(json.dumps(result,indent=1)+"\n")
 return result
if __name__=="__main__":
 a=argparse.ArgumentParser(description=__doc__);a.add_argument("ledger");a.add_argument("--out",required=True);a.add_argument("--rtl",required=True)
 x=a.parse_args();r=generate(x.ledger,x.out,x.rtl);print(json.dumps({k:r[k] for k in ("abi","profiles","old_ff","new_ff","extra_ff","remaining")},indent=1))
