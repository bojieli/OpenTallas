module cone #(parameter VM_OWNED_LEASE=1,ME_STALL=1,ME_IDLE_GATE=1)(input rst_n_i,me_mem_ok_i,me_idle,me_wake,vm_me_lease,output me_en,vm_me_wanted);
    assign vm_me_wanted = !rst_n_i || (((ME_STALL == 0) || me_mem_ok_i) &&
                              ((ME_IDLE_GATE == 0) || !me_idle || me_wake));
    assign me_en = !rst_n_i || (vm_me_wanted &&
                       ((VM_OWNED_LEASE == 0) || vm_me_lease));
endmodule
module tb #(parameter NEG=0);reg r,m,i,w,l;wire e,intent;integer k,n=0;reg expected;
cone #(.VM_OWNED_LEASE(NEG?0:1)) dut(r,m,i,w,l,e,intent);
initial begin
for(k=0;k<32;k=k+1)begin {r,m,i,w,l}=k;#1;
 expected=!r||(m&&(!i||w));
 if(intent!==expected)$fatal(1,"original enable altered");
 if(e!==(!r||(expected&&l)))$fatal(1,"unpaid ME edge");n=n+1;end
// CAP with no ME frame followed by original intent rise and ADMIT without ME lease.
r=1;m=0;i=0;w=0;l=0;#1;if(intent!==0)$fatal; m=1;#1;
if(intent!==1||e!==0)$fatal(1,"unpaid held-frame intent rise");
l=1;#1;if(e!==1)$fatal(1,"paid ME edge missing");
$display("PASS direct lease enable truth table32 + held-frame intent rise");$finish;end endmodule
