#!/usr/bin/env python3
"""Source-owned native provider binding generated from installed span metadata.

Candidate only: caller installed means actual external installation/enrollment,
never inferred from the existence of this generated source.
"""
import argparse,hashlib,json
from pathlib import Path
from hbm_sm_native_production_model import model
from hbm_sm_native_allocation_build import build as allocation
ROOT=Path(__file__).resolve().parents[1]

def build(manifest,out):
    mp,out=Path(manifest),Path(out);m=json.loads(mp.read_text());model(m['record_count'])
    if m['schema']!='opentallas.native_sm.installed_spans.v1':raise ValueError('native installed source required')
    out.mkdir(parents=True,exist_ok=True);allocation(mp,out/'ot_hbm_sm_native_allocation.sv')
    cases=[]
    for i,r in enumerate(m['records']):
        if i!=r['record'] or r['x_stride']!=3328 or r['result_stride']!=32:raise ValueError('native source contract mismatch')
        xb,xe,rb,rows=r['x_byte_base'],r['x_extent'],r['result_byte_base'],r['result_rows']
        def covers(base,size,reserved):
            return any(s['base']==base and s['end']==base+size and s['reserved_only']==reserved for s in m['spans'])
        if not(covers(xb,xe*3328,False) and covers(rb,rows*32,True)):raise ValueError('source tuple lacks allocated span')
        if any(type(x)!=int or x<0 or x>=1<<37 for x in [xb,xb+xe*3328,rb,rb+rows*32]):raise ValueError('provider address overflow')
        cases.append(f"16'd{i}:begin found=1;weight_base=32'd{r['weight_line_base']};weight_limit=33'd{r['weight_line_base']+r['weight_lines']};x_base=37'd{xb};x_limit=38'd{xb+xe*3328};x_extent=8'd{xe};x_ring=7'd{r['x_ring_base']};result_base=37'd{rb};result_limit=37'd{rb+rows*32};result_rows=13'd{rows};end")
    table='''// Immutable exact installer spans; no grant produced. Source SHA256 HASH
module ot_hbm_sm_native_tuple(input wire[15:0] record_id,output reg found,
 output reg[31:0]weight_base,output reg[32:0]weight_limit,
 output reg[36:0]x_base,output reg[37:0]x_limit,output reg[7:0]x_extent,output reg[6:0]x_ring,
 output reg[36:0]result_base,result_limit,output reg[12:0]result_rows);
 always @*begin found=0;weight_base=0;weight_limit=0;x_base=0;x_limit=0;x_extent=0;x_ring=0;result_base=0;result_limit=0;result_rows=0;
 case(record_id)
 CASES
 default:begin end
 endcase end
endmodule
'''.replace('HASH',hashlib.sha256(mp.read_bytes()).hexdigest()).replace('CASES','\n'.join(cases))
    (out/'ot_hbm_sm_native_tuple.sv').write_text(table)
    # Add explicit external abort and actual-arrive tap in a separate leaf namespace.
    original=(ROOT/'rtl/hbm_accel/control_20261007/native_join/ot_hbm_sm_native_owner_join.sv').read_text()
    leaf=original.replace('module ot_hbm_sm_native_owner_join #','module ot_hbm_sm_native_provider_leaf #',1)
    leaf=leaf.replace(' input wire  clk,',' input wire peer_fault,\n output wire native_arrive,native_compute_fault,\n input wire  clk,',1)
    leaf=leaf.replace(' assign fault=owner_fault || sm_fault;',' assign native_arrive=arrive;\n assign native_compute_fault=sm_fault;\n assign fault=owner_fault || sm_fault || peer_fault;')
    leaf=leaf.replace('.sm_fault(sm_fault)', '.sm_fault(sm_fault || peer_fault)')
    if '.sm_fault(sm_fault || peer_fault)' not in leaf:raise ValueError('native abort source changed')
    (out/'ot_hbm_sm_native_provider_leaf.sv').write_text(leaf)
    return m

# Separate callable so source regeneration is explicit for the full shared parent.
def shared_parent(manifest,out):
    m=json.loads(Path(manifest).read_text());out=Path(out)
    src=(ROOT/'rtl/hbm_accel/control_20261007/service_mux/ot_hbm_sm_shared_service_join.sv').read_text()
    shared=' input wire hardware_owner_valid'+src.split(' input wire hardware_owner_valid',1)[1].split('\n);',1)[0]
    shared=shared.replace('output wire busy,','output wire service_busy,').replace('output wire fault','output wire fault')
    header='''// Actual native clients + ONE sharedservice join; fifth client is checked SU reads.
// Generated installedsource constants; installation/liveissuer/PHY remain real external contracts.
module ot_hbm_sm_native_production #(parameter ENABLE=0,PROTECT=0,DESC_HOPS=32,LOCAL_DIE=0,RANK_LIMIT=96)(
 input wire clk,rst_n,installed,run_valid,output wire run_ready,
 input wire[72:0]run_owner,input wire[4:0]run_source,input wire[15:0]issuer_tag,
 input wire[93:0]issuer_grant_context,
 output wire done,input wire done_ready,input wire release_in,output wire released,native_busy,
 output wire su_publication_valid,input wire su_publication_ready,output wire[93:0]su_publication_context,
 input wire su_release_valid,output wire su_release_ready,input wire[93:0]su_release_context,
 input wire su_req_v,output wire su_req_r,input wire su_req_we,input wire[36:0]su_req_addr,
 input wire[255:0]su_req_data,input wire[15:0]su_req_tag,input wire[93:0]su_req_context,
 output wire su_rsp_v,input wire su_rsp_r,output wire su_rsp_we,su_rsp_error,
 output wire[255:0]su_rsp_data,output wire[15:0]su_rsp_tag,output wire[191:0]su_rsp_identity,
 output wire[93:0]su_rsp_context,output wire su_rsp_identity_checked,su_rsp_context_checked,
 output wire issuer_req_valid,output wire[36:0]issuer_req_addr,output wire[15:0]issuer_req_tag,output wire[93:0]issuer_req_context,
'''
    body='''
);
 wire[4:0]c_req_v,c_req_r,c_req_we,c_rsp_v,c_rsp_r,c_rsp_we,c_rsp_error,c_rsp_identity_checked,c_rsp_context_checked;
 wire[184:0]c_req_addr;wire[1279:0]c_req_data,c_rsp_data;wire[79:0]c_req_tag,c_rsp_tag;
 wire[469:0]c_req_context,c_rsp_context;wire[959:0]c_rsp_identity;
 wire native_fault,shared_fault;
 wire issuer_mismatch=issuer_req_valid&&hardware_owner_valid&&issuer_grant_context!=issuer_req_context;
 wire association_fault=|(c_rsp_v[3:0]&~(c_rsp_identity_checked[3:0]&c_rsp_context_checked[3:0]));
 wire abort_native=shared_fault||issuer_mismatch||association_fault;
 assign fault=native_fault||abort_native;
 assign c_req_v[4]=su_req_v;assign su_req_r=c_req_r[4];assign c_req_we[4]=su_req_we;
 assign c_req_addr[148+:37]=su_req_addr;assign c_req_data[1024+:256]=su_req_data;assign c_req_tag[64+:16]=su_req_tag;assign c_req_context[376+:94]=su_req_context;
 assign su_rsp_v=c_rsp_v[4];assign c_rsp_r[4]=su_rsp_r;assign su_rsp_we=c_rsp_we[4];assign su_rsp_error=c_rsp_error[4];
 assign su_rsp_data=c_rsp_data[1024+:256];assign su_rsp_tag=c_rsp_tag[64+:16];assign su_rsp_identity=c_rsp_identity[768+:192];assign su_rsp_context=c_rsp_context[376+:94];
 assign su_rsp_identity_checked=c_rsp_identity_checked[4];assign su_rsp_context_checked=c_rsp_context_checked[4];
 ot_hbm_sm_native_clients #(.ENABLE(ENABLE),.PROTECT(PROTECT),.DESC_HOPS(DESC_HOPS)) clients(
 .clk(clk),.rst_n(rst_n),.installed(installed),.run_valid(run_valid),.run_ready(run_ready),.run_owner(run_owner),.run_source(run_source),.issuer_tag(issuer_tag),
 .program_base(32'dPBASE),.program_limit(33'dPLIMIT),.program_storage_limit(33'dPSLIMIT),.record_count(16'dNRECORD),
 .su_publication_valid(su_publication_valid),.su_publication_ready(su_publication_ready),.su_publication_context(su_publication_context),
 .su_release_valid(su_release_valid),.su_release_ready(su_release_ready),.su_release_context(su_release_context),
 .done(done),.done_ready(done_ready),.fault(native_fault),.release_in(release_in),.released(released),.busy(native_busy),
 .c_req_v(c_req_v[3:0]),.c_req_r(c_req_r[3:0]),.c_req_we(c_req_we[3:0]),.c_req_addr(c_req_addr[147:0]),.c_req_data(c_req_data[1023:0]),.c_req_tag(c_req_tag[63:0]),.c_req_context(c_req_context[375:0]),
 .c_rsp_v(c_rsp_v[3:0]),.c_rsp_r(c_rsp_r[3:0]),.c_rsp_we(c_rsp_we[3:0]),.c_rsp_error(c_rsp_error[3:0]),.c_rsp_data(c_rsp_data[1023:0]),.c_rsp_tag(c_rsp_tag[63:0]),.service_fault(abort_native));
 ot_hbm_sm_shared_service_join #(.ENABLE(ENABLE),.LOCAL_DIE(LOCAL_DIE),.RANK_LIMIT(RANK_LIMIT),.NCLIENT(5)) service(
 .hardware_owner_valid(hardware_owner_valid&&!issuer_mismatch),.busy(service_busy),.fault(shared_fault),.*);
endmodule
'''
    for key,value in dict(PBASE=m['program_base'],PLIMIT=m['program_limit'],PSLIMIT=m['program_storage_limit'],NRECORD=m['record_count']).items():body=body.replace(key,str(value))
    (out/'ot_hbm_sm_native_production.sv').write_text(header+shared+body)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();build(a.manifest,a.out);shared_parent(a.manifest,a.out)
