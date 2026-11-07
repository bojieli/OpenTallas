# bench-only mutants of the vL7 cache module; each = one exact textual replacement (count must be 1)
import sys,os
src=open(sys.argv[1]).read();out=sys.argv[2]
M={
 # WDECOUPLE mutants
 'W1_no_sticky_on_index':("sector_index[i*24+:24]!=received+i||present[(received+i)%16])sticky<=1;",
                          "present[(received+i)%16])sticky<=1;"),
 'W2_no_sticky_on_epoch':("if(sector_epoch[i*16+:16]!=load_epoch||sector_index","if(sector_index"),
 'W3_no_present_term':("||present[(received+i)%16])sticky<=1;",")sticky<=1;"),
 'W4_wrong_word_index':("if(WDECOUPLE!=0)begin words[(received+i)%16]","if(WDECOUPLE!=0)begin words[(received+i+1)%16]"),
 'W5_present_not_set':("if(WDECOUPLE!=0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end",
                       "if(WDECOUPLE!=0)begin words[(received+i)%16]<=sector_data[i*256+:256];end"),
 # GSEL mutants
 'G1_stale_onehot_on_open':("    else if(open_ok)begin for(qj=0;qj<5;qj=qj+1)","    else if(1'b0)begin for(qj=0;qj<5;qj=qj+1)"),
 'G2_rotate4_always':("q[(qj*GREP+qc)*16+:16]<=(record_phase==3)?","q[(qj*GREP+qc)*16+:16]<=(1'b0)?"),
 'G3_wrong_select_lane':("if(gsel[(j*GREP+gc)*16+gk])gathered","if(gsel[(((j+1)%5)*GREP+gc)*16+gk])gathered"),
 'G4_reset_value_off':("if(!rst_n)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<qj;end",
                       "if(!rst_n)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<((qj+1)%5);end"),
 'G8_open_value_off':("else if(open_ok)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<qj;end",
                      "else if(open_ok)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<((qj+1)%5);end"),
 'G9_complete_off_by_one':("if((gsel[j*GREP*16+:16]&present)==16'd0)complete=0;",
                           "if(({gsel[j*GREP*16+:15],gsel[j*GREP*16+15]}&present)==16'd0)complete=0;"),
 'G5_replica1_not_rotated':("for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)\n      q[","for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<1;qc=qc+1)\n      q["),
 'G6_complete_lane0_only':("if((gsel[j*GREP*16+:16]&present)==16'd0)complete=0;","if((gsel[0+:16]&present)==16'd0)complete=0;"),
 'G7_present_clear_skipped':("if(gsel[i*GREP*16+gk])present[gk]<=0;","if(1'b0)present[gk]<=0;"),
}
os.makedirs(out,exist_ok=True)
for k,(a,b) in M.items():
    assert src.count(a)==1,(k,src.count(a))
    open(os.path.join(out,k+'.sv'),'w').write(src.replace(a,b))
print(' '.join(M))
