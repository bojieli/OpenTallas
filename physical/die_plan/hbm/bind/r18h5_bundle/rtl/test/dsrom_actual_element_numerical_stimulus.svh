// Input-only deterministic stimulus codebooks.
function automatic [7:0] q_code(input integer i);
 case(i%15)
 0: q_code=8'h0;
 1: q_code=8'h1;
 2: q_code=8'h7;
 3: q_code=8'h8;
 4: q_code=8'h38;
 5: q_code=8'h3b;
 6: q_code=8'h40;
 7: q_code=8'h77;
 8: q_code=8'h7e;
 9: q_code=8'h80;
 10: q_code=8'hb8;
 11: q_code=8'hbd;
 12: q_code=8'hc0;
 13: q_code=8'hf7;
 14: q_code=8'hfe;
 default: q_code=0;
 endcase
endfunction
function automatic [15:0] bf_code(input integer i);
 case(i%11)
 0: bf_code=16'h0;
 1: bf_code=16'h3f00;
 2: bf_code=16'h3f80;
 3: bf_code=16'h3f81;
 4: bf_code=16'hbf80;
 5: bf_code=16'h4000;
 6: bf_code=16'h4b80;
 7: bf_code=16'hcb80;
 8: bf_code=16'h3380;
 9: bf_code=16'hb380;
 10: bf_code=16'h80;
 default: bf_code=0;
 endcase
endfunction
function automatic [7:0] input_xcode(input integer pos,unit_id,block_id,lane,half);
 input_xcode=q_code(lane*3+pos*7+unit_id*5+block_id*11+half*2);
endfunction
function automatic integer input_xexp(input integer pos,unit_id,block_id,half);
 case((pos+unit_id+block_id+half)%5)
 0:input_xexp=-9;
 1:input_xexp=-1;
 2:input_xexp=0;
 3:input_xexp=2;
 4:input_xexp=8;
 default:input_xexp=0;
 endcase
endfunction
function automatic [15:0] input_xbcode(input integer pos,unit_id,block_id,lane);
 input_xbcode=bf_code(lane*3+pos*7+unit_id*5+block_id*2);
endfunction
function automatic integer active_segments(input integer phase_id);
 active_segments=phase_id<6?8:4;
endfunction
function automatic integer contract_nseg(input integer phase_id);
 contract_nseg=phase_id>=9?2:1;
endfunction
function automatic integer is_BF_phase(input integer phase_id);
 is_BF_phase=(phase_id==3 || phase_id==8 || phase_id==11);
endfunction
