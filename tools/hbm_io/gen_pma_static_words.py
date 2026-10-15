#!/usr/bin/env python3
"""Separate fixed-slice structural PMA gearbox, with unchanged source control FSM."""
import argparse,hashlib,json,pathlib
ORIGINAL_SHA='f1088a53729847bfcf1bd6436a0c96c61083a86cee48941170d3aa72123ebe04'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--original',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();assert sha(a.original)==ORIGINAL_SHA
 old=a.original.read_text();new=old.replace('module ot_hbm_pma_block_gearbox #(', 'module ot_hbm_pma_block_gearbox_static_words #(')
 start=new.index(' genvar g;generate');end=new.index(' initial if(',start)
 new=new[:start]+''' // Each word is actual fixed wiring/storage. No variable full-bank shift.
 wire [NI-1:0] write_word_sel;
 wire [NO-1:0] read_word_sel;
 localparam integer READ_LEAVES=1 << $clog2(NO);
 wire [WO-1:0] bank_read[0:3];
 wire [WO-1:0] selected_read;
 wire [WO-1:0] read_valid_data;
 reg [WO-1:0] selected_bank;
 genvar g,w,r,t;
 generate for(w=0;w<NI;w=w+1)begin:write_decode
  assign write_word_sel[w]=(wi==w);
 end
 for(r=0;r<NO;r=r+1)begin:read_decode
  assign read_word_sel[r]=(ri==r);
 end
 for(g=0;g<4;g=g+1)begin:storage
  // All fixed slices keep the same one actual bank clock root.
  for(w=0;w<NI;w=w+1)begin:word
   always @(posedge wclk_bank[g])
    if(rst_n && (w_start || wa) && wb==g && write_word_sel[w])
     bank[g][w*WI+:WI]<=d;
  end
  wire [WO-1:0] tree[0:2*READ_LEAVES-2];
  for(r=0;r<READ_LEAVES;r=r+1)begin:read_leaf
   if(r<NO)assign tree[READ_LEAVES-1+r]=bank[g][r*WO+:WO] & {WO{read_word_sel[r]}};
   else assign tree[READ_LEAVES-1+r]={WO{1'b0}};
  end
  for(t=0;t<READ_LEAVES-1;t=t+1)begin:read_or
   assign tree[t]=tree[2*t+1] | tree[2*t+2];
  end
  assign bank_read[g]=tree[0];
 end endgenerate
 // Preserve four-state behavior for an unknown bank or invalid read index.
 always @* begin
  selected_bank={WO{1'bx}};
  case(rb)
   2'd0:selected_bank=bank_read[0];
   2'd1:selected_bank=bank_read[1];
   2'd2:selected_bank=bank_read[2];
   2'd3:selected_bank=bank_read[3];
  endcase
 end
 assign selected_read=selected_bank;
 assign read_valid_data=(ri>=0 && ri<NO) ? selected_read : {WO{1'bx}};
''' + new[end:]
 original_read='q<=bank[rb][ri*WO+:WO] ^'
 assert new.count(original_read)==1
 new=new.replace(original_read,'q<=read_valid_data ^')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(new)
 provenance={'original_path':str(a.original),'original_sha256':sha(a.original),'candidate_sha256':sha(a.out),'generator_sha256':sha(pathlib.Path(__file__)),'scope':'OPT_IN_REAL_FIXED_SLICE_STORAGE_AND_BALANCED_PREDECODED_READ','control_fsm_bytes_unchanged':old[old.index(' initial if('):].replace(original_read,'q<=read_valid_data ^')==new[new.index(' initial if('):],'new_state_bits':0,'new_clocks':0,'new_cycles':0,'physical_qualified':False}
 assert provenance['control_fsm_bytes_unchanged']
 a.out.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(provenance))
if __name__=='__main__':main()
