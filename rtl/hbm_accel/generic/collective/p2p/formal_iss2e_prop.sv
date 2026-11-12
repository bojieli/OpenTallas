`ifdef FORMAL
 // ISS2E invariant: on an advance edge the registered carry-save decision equals the one-edge original f_take of the
 // current fetch state (the state the hold edge registered has not changed), for both successors.
 always @(*) if(rcp[7] && adv) begin
  assert(tt == f_take(r_has(rt),l_t,r_cnt(rt)));
  assert(tn == f_take(r_has(rn),l_n,r_cnt(rn)));
 end
`endif
