#!/usr/bin/env python3
"""Source-pin an actual six-kind HC trace vehicle; no numerical models in DUT."""
from pathlib import Path
import ast,hashlib,json,subprocess
def readbytes(p):
 return p.read_bytes() if p.exists() else subprocess.check_output(["git","show","HEAD:"+str(p.relative_to(ROOT))],cwd=ROOT)
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'rtl/dsrom_sys/s81_suhc/test'
tb=(OUT/'tb_s81_hc_master.sv').read_text()
# Exact3:4 clocks after1ps quantization: controller417ps half, serial556ps half.
tb=tb.replace('always #0.4255 sk = ~sk;','always #0.5555 sk = ~sk;')
monitor='''
    // Observations at the same pre-NBA edge values consumed by the real RTL.
    integer tr_edge=0,tr_start=0,tr_tag=0,tr_kind=0;
    always @(posedge sk) if(srs) begin
      tr_edge=tr_edge+1;
      if(dut.g_hier.u_cb.u_seq.take) begin
        tr_start=tr_edge;tr_tag=dut.g_hier.u_cb.u_seq.e_d[6:0];
        tr_kind=dut.g_hier.u_cb.u_seq.c_arg[22:20];
        $display("HC6 take edge=%0d tag=%0d kind=%0d cmd=%h",tr_edge,tr_tag,tr_kind,dut.g_hier.u_cb.u_seq.e_d);
      end
      if(dut.g_hier.u_cb.u_seq.rq_v!=0)
        $display("HC6 rq_internal edge=%0d age=%0d tag=%0d kind=%0d mask=%h rows=%h",tr_edge,tr_edge-tr_start,tr_tag,tr_kind,dut.g_hier.u_cb.u_seq.rq_v,dut.g_hier.u_cb.u_seq.rq_row);
      if(rq_v!=0)$display("HC6 rq_public edge=%0d age=%0d tag=%0d kind=%0d mask=%h rows=%h",tr_edge,tr_edge-tr_start,tr_tag,tr_kind,rq_v,rq_row);
      if(rs_v!=0)$display("HC6 rs_public edge=%0d age=%0d tag=%0d kind=%0d mask=%h",tr_edge,tr_edge-tr_start,tr_tag,tr_kind,rs_v);
      if(dut.g_hier.u_cb.u_seq.y_take)$display("HC6 post_take edge=%0d age=%0d tag=%0d row=%0d",tr_edge,tr_edge-tr_start,tr_tag,dut.g_hier.u_cb.u_seq.ci);
      if(dut.g_hier.u_cb.u_seq.n_ypop)$display("HC6 post_pop edge=%0d age=%0d tag=%0d",tr_edge,tr_edge-tr_start,tr_tag);
      if(y_v&&y_rdy)$display("HC6 y_public edge=%0d beat=%0d",tr_edge,yb);
      if(wq_v!=0)$display("HC6 write_public edge=%0d age=%0d tag=%0d kind=%0d mask=%h rows=%h",tr_edge,tr_edge-tr_start,tr_tag,tr_kind,wq_v,wq_row);
      if(dut.g_hier.u_cb.u_seq.ssq_v)$display("HC6 cseq_ss edge=%0d age=%0d tag=%0d data=%h",tr_edge,tr_edge-tr_start,tr_tag,dut.g_hier.u_cb.u_seq.ssq);
      if(dut.g_hier.u_cb.u_seq.rr_v)$display("HC6 cseq_rr edge=%0d age=%0d tag=%0d data=%h",tr_edge,tr_edge-tr_start,tr_tag,dut.g_hier.u_cb.u_seq.rr_);
      if(nt_ssv)$display("HC6 bottom_ss edge=%0d age=%0d tag=%0d",tr_edge,tr_edge-tr_start,tr_tag);
      if(nt_rrv)$display("HC6 bottom_rr edge=%0d age=%0d tag=%0d",tr_edge,tr_edge-tr_start,tr_tag);
      if(dut.g_hier.u_cb.u_seq.wd_q)$display("HC6 writer_done edge=%0d age=%0d tag=%0d kind=%0d",tr_edge,tr_edge-tr_start,tr_tag,tr_kind);
      if(dut.g_hier.u_cb.u_seq.d_v)$display("HC6 done_internal edge=%0d age=%0d tag=%0d kind=%0d",tr_edge,tr_edge-tr_start,tr_tag,tr_kind);
    end
'''
tb=tb[:tb.rfind('endmodule')]+monitor+'\nendmodule\n'
(OUT/'tb_s81_hc_trace.sv').write_text(tb)
seqpath=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv'
seq=seqpath.read_text()
assert seq.count('ssq <= t_ss;')==1
seq=seq.replace('ssq <= t_ss;','ssq <= t_ss ^ (trace_scalar_mut ? 32\'h01000000 : 32\'d0);')
seq=seq.replace('    // the comb\'s geometry', '    reg trace_scalar_mut; initial trace_scalar_mut=$test$plusargs("TRACE_UNUSED_MUT");\n    // the comb\'s geometry',1)
(OUT/'ot_s81_hc_cseq_trace.sv').write_text(seq)
ntpath=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv'
nt=ntpath.read_text()
assert nt.count('ssq <= ss;')==1
nt=nt.replace('ssq <= ss;','ssq <= ss ^ (trace_scalar_mut ? 32\'h01000000 : 32\'d0);')
nt=nt.replace('    localparam integer LA = AL, LM = ML;', '    reg trace_scalar_mut; initial trace_scalar_mut=$test$plusargs("TRACE_MUT");\n    localparam integer LA = AL, LM = ML;',1)
(OUT/'ot_s81_hc_ntree_trace.sv').write_text(nt)
ns={}
for node in ast.parse((ROOT/'tools/s81_suhc/hc_gate.py').read_text()).body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('RTL','FP') for t in node.targets):
  ns[node.targets[0].id]=({k.arg:ast.literal_eval(k.value)for k in node.value.keywords}if isinstance(node.value,ast.Call)else ast.literal_eval(node.value))
files=ns['RTL']+ns['FP']['rtl']+['rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf_bankpipe.sv']
files=[('rtl/dsrom_sys/s81_suhc/test/ot_s81_hc_cseq_trace.sv' if f=='rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv'else f)for f in files]
files=[('rtl/dsrom_sys/s81_suhc/test/ot_s81_hc_ntree_trace.sv'if f=='rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv'else f)for f in files]
files+=['rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_trace.sv']
(ROOT/'tools/s81_hc_trace/sources.txt').write_text('\n'.join(files)+'\n')
record={'scope':'actual full-native arithmetic HC unit six-kind trace; external VM LVM10 and back-to-back ready-obeying Y are declared unit stimuli, not actual integrated production calendar','shape':{'NG':256,'D':5120,'HIER':1,'HALF':1,'CSPLIT':1,'TAIL_SPLIT':2,'HEAD_ROWS':10,'CNL_PIN':1,'CHAIN_STEP':6,'LANE_SPECIALIZE':1,'PIPE':1,'PIPE_PD':40,'NTREE':1,'NT_K':67,'CCF_BP':3},'memory_request_basis':'160GB initial fullnative reserve from measured nativeverilator144.8GB class, rather than claim defaultHC30.2GB DPI evidence predicts nativepeak','timing_unit':'pre-NBA serial edges relative actual accepted command; captured at same values real RTL consumes','source':{f:hashlib.sha256(readbytes(ROOT/f)).hexdigest()for f in files},'source_model_edit':{'CSEQ':'disabled diagnosticfaultmux, +TRACE_UNUSED_MUT flips discarded CSEQscalar input bit24; normalinputbitwiseidentical','CNRSQ':'disabled diagnosticfaultmux,+TRACE_MUT flips live actual NTbottomscalar inputbit24; mustrejectgolden, no goldenoutputinjection','TB':'observations only, exact3:4 rounded clocks417ps/556ps halfperiod; existinggolden assertions retained'},'profile_status':'UNMEASURED; no compiler ages emitted until successful actual native build/run'}
(ROOT/'results/rtl/s81_hc_trace_1016/prebuild.json').write_text(json.dumps(record,indent=2)+'\n')
