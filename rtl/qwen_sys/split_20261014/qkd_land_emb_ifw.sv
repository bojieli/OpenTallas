`timescale 1ns/1ps
// Die endpoint of the closed embedding landing engine. Compact gateway words
// retain every functional field and both credits. The removed full-link fields
// are protocol constants on this dedicated embedding hop; no data state changes.
module qkd_land_emb_ifw #(parameter integer MUT=0, PACK_MUT=0)(
 input wire ck,rst_n,input wire[1:0] st,
 input wire[287:0] emf,input wire emf_cr,
 output wire[519:0] emr,output wire emr_cr,
 output wire[297:0] dno,input wire[261:0] upi,
 input wire[31:0] cri,input wire fi,gfi,output wire mf);
 wire[529:0] full_r;
 wire[3:0] seq = PACK_MUT ? (emf[285:282]^4'b0001) : emf[285:282];
 // Full link tag={EMB class,kind,poison,reserved[2:0],sequence}.
 wire[529:0] full_f={emf_cr,5'b0,1'b1,emf[287:286],1'b0,3'b0,seq,231'b0,emf[281:1],emf[0]};
 qkd_land_emb #(.MUT(MUT)) u_body(.ck(ck),.rst_n(rst_n),.st(st),
 .emf(full_f),.emr(full_r),.dno(dno),.upi(upi),.cri(cri),.fi(fi),.gfi(gfi),.mf(mf));
 assign emr={full_r[522:521],full_r[520],full_r[516:513],full_r[512:1],full_r[0]};
 assign emr_cr=full_r[529];
endmodule
