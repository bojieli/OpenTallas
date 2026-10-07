#!/usr/bin/env python3
"""Expose actual checked owned identity and bind four native clients once."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rtl/hbm_accel/control_20261007/service_mux'
def build():
 p=ROOT/'rtl/hbm_accel/integration/ot_hbm_loader_service_join.sv';src=p.read_text()
 s=src.replace('module ot_hbm_loader_service_join #','module ot_hbm_sm_loader_identity_join #',1)
 s=s.replace(' input wire clk,rst_n,',' output wire[191:0] rsp_identity,\n input wire clk,rst_n,',1)
 s=s.replace(' assign req_r=0;',' assign rsp_identity=0;\n assign req_r=0;',1)
 s=s.replace(' assign rsp_v=response_enable;',' assign rsp_identity=selected_owned.id;\n assign rsp_v=response_enable;',1)
 if 'output wire[191:0] rsp_identity' not in s:raise ValueError('source join header changed')
 (OUT/'ot_hbm_sm_loader_identity_join.sv').write_text('// Source SHA256 '+hashlib.sha256(p.read_bytes()).hexdigest()+'; only checked identity output added.\n'+s)
 shared=' input wire hardware_owner_valid'+src.split(' input wire hardware_owner_valid',1)[1].split('\n);',1)[0]
 shared=shared.replace(' output wire rsp_v,input wire rsp_r,output wire rsp_we,output wire[15:0] rsp_tag,output wire[255:0] rsp_data,\n','')
 header='''// One existing shared-service client, four locally captured native requesters.
module ot_hbm_sm_shared_service_join #(parameter ENABLE=0,LOCAL_DIE=0,RANK_LIMIT=96,NCLIENT=4)(
 input wire clk,rst_n,
 input wire[NCLIENT-1:0]c_req_v,output wire[NCLIENT-1:0]c_req_r,input wire[NCLIENT-1:0]c_req_we,
 input wire[NCLIENT*37-1:0]c_req_addr,input wire[NCLIENT*256-1:0]c_req_data,input wire[NCLIENT*16-1:0]c_req_tag,input wire[NCLIENT*94-1:0]c_req_context,
 output wire[NCLIENT-1:0]c_rsp_v,input wire[NCLIENT-1:0]c_rsp_r,output wire[NCLIENT-1:0]c_rsp_we,c_rsp_error,c_rsp_identity_checked,c_rsp_context_checked,
 output wire[NCLIENT*256-1:0]c_rsp_data,output wire[NCLIENT*16-1:0]c_rsp_tag,output wire[NCLIENT*192-1:0]c_rsp_identity,output wire[NCLIENT*94-1:0]c_rsp_context,
 output wire issuer_req_valid,output wire[36:0]issuer_req_addr,output wire[15:0]issuer_req_tag,output wire[93:0]issuer_req_context,
'''
 body='''
);
 wire req_v,req_r,req_we,rsp_v,rsp_r,rsp_we;
 wire[36:0]req_addr;wire[255:0]req_data,rsp_data;wire[15:0]req_tag,rsp_tag;
 wire[31:0]req_strb={32{req_we}};wire[191:0]rsp_identity;
 wire mux_fault,join_fault;
 assign issuer_req_valid=req_v;assign issuer_req_addr=req_addr;assign issuer_req_tag=req_tag;
 assign fault=mux_fault||join_fault;
 ot_hbm_sm_service_mux #(.ENABLE(ENABLE),.NCLIENT(NCLIENT)) mux(.service_fault(join_fault),.fault(mux_fault),.issuer_context(issuer_req_context),.*);
 ot_hbm_sm_loader_identity_join #(.ENABLE(ENABLE),.LOCAL_DIE(LOCAL_DIE),.RANK_LIMIT(RANK_LIMIT)) service(.fault(join_fault),.*);
endmodule
'''
 (OUT/'ot_hbm_sm_shared_service_join.sv').write_text(header+shared+body)
if __name__=='__main__':build()
