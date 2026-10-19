#!/usr/bin/env python3
"""Construct a separate exact-G7 verification fixture. Never edit live inputs."""
import argparse, hashlib, json
from pathlib import Path
DRIVER_SHA='668c9ade6662818fabaa245305f7fbd960954cfb082c5c29d8834cd4acb30f79'
TB_SHA='83123a31d206b42d86b89a3ef7145ce701b76ba3f9210b2a1494b66a12957259'
def sha(b): return hashlib.sha256(b).hexdigest()
def replace_once(s,a,b):
 if s.count(a)!=1: raise ValueError(f'fixture anchor count {s.count(a)}: {a[:80]}')
 return s.replace(a,b,1)
def repair(original):
 if sha(original.encode())!=DRIVER_SHA: raise ValueError('unsupported original driver SHA')
 s=original
 s=replace_once(s,'    always @(negedge ck) begin : seqreq','    always @(negedge ck) if (kva_authority_known[1]) begin : seqreq') if 'begin : seqreq' in s else s
 # Exact original sequencer block is patched below by the guarded anchor.
 old='''        if (`KVA_SEQ_PRG_REQ_V === 1'b1 && !kva_sr_q && kva_nsr < KMAX) begin kva_seqreq[kva_nsr] = cyc; kva_nsr = kva_nsr + 1; end
        kva_sr_q <= (`KVA_SEQ_PRG_REQ_V === 1'b1);'''
 new='''        if (kva_authority_known[1]) begin
            if ($isunknown(`KVA_SEQ_PRG_REQ_V)) smoke_err("unknown authoritative sequence valid");
            if (`KVA_SEQ_PRG_REQ_V === 1'b1 && !kva_sr_q && kva_nsr < KMAX) begin kva_seqreq[kva_nsr] = cyc; kva_nsr = kva_nsr + 1; end
            kva_sr_q <= (`KVA_SEQ_PRG_REQ_V === 1'b1);
        end'''
 s=replace_once(s,old,new)
 s=replace_once(s,"if (kva_kreq[g][0] === 1'b1) begin","if (kva_authority_known[2+g] && kva_kreq[g][0] === 1'b1) begin")
 s=replace_once(s,"if (kva_vreq[g][0] === 1'b1) begin","if (kva_authority_known[10+g] && kva_vreq[g][0] === 1'b1) begin")
 # Reusable ledger owns all retirement state; retain original numerical comparisons.
 s=replace_once(s,"integer kva_nrec = 0, kva_hdrerr = 0, kva_nst = 0;","integer kva_nrec = 0, kva_hdrerr = 0; wire signed [31:0] kva_nst = kva_identity_success_count;")
 s=replace_once(s,"always @(negedge ck) if (kva_tv === 1'b1) begin : face","always @(negedge ck) if (kva_authority_known[0] && kva_tv === 1'b1) begin : face")
 s=replace_once(s,"            if (k < 0) k = (kva_nst < kva_n) ? kva_nst : 0;\n            kva_st[k] = cyc; kva_nst = kva_nst + 1;",'''            if (k < 0) smoke_err("STATUS identity names no programme entry");
            else kva_st[k] = cyc; // Successful count comes only from source-owned ledger.''')
 # End-of-programme checks do not infer success from preloaded expected arrays.
 s=replace_once(s,'        all = 1;','''        kva_identity_final_check = 1;
        @(posedge ck); @(negedge ck); @(posedge ck);
        kva_identity_final_check = 0;
        all = 1;
        for (int ai=0; ai<18; ai++) if (kva_authority_errors[ai] != 0) smoke_err("authority capture/reset checks failed");
        if (kva_authority_admission_errors != 0) smoke_err("source admission before required frontier");
        if (kva_identity_errors != 0 || !kva_identity_programme_executed) smoke_err("PROGRAMME_EXECUTED or source identity checks failed");''')

 s += '\n`include "g7_identity_bind.svh"\n`include "g7_fault_bind.svh"\n'
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument('--driver',type=Path,required=True);p.add_argument('--tb',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists(): raise ValueError('new immutable output directory required')
 original=a.driver.read_text();tb=a.tb.read_bytes()
 if sha(tb)!=TB_SHA:raise ValueError('unsupported original TB SHA')
 fixed=repair(original)
 a.out.mkdir(parents=True);(a.out/'drive_qwk_slice_attn_mu.svh').write_text(fixed)
 (a.out/'tb_qwk_stk_WS.sv').write_bytes(tb)
 (a.out/'receipt.json').write_text(json.dumps({'original_driver':DRIVER_SHA,'driver':sha(fixed.encode()),'tb':sha(tb),'status':'SOURCE_ONLY_NOT_VALIDATED','rtl_changed':False,'gold_reset_programme_deadlines_changed':False},indent=2)+'\n')
if __name__=='__main__':main()
