`timescale 1ns/1ps
module scheduler_descriptor_baseline_contract #(parameter integer C=0);
 ot_host_if_pb2_observed_rc #(.ENABLE_RETAINED_COMMIT(1),.HEALTH_CUTOFF_EDGES(C==0?0:12),.STEP_RESPONSE_DEADLINE_EDGES(C==1?13:8),.COMPONENT_FIXTURE(C==2?0:1),.NSLOT(C==3?4:1),.ENG_CTX(1),.MODE(0),.MU_OUT(0),.NW(18),.PLB(13),.FMT(1)) dut ();
 initial begin #10;$fatal(1,"SCHED_CONTRACT_NOT_REFUSED");end
endmodule
