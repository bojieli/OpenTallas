#!/usr/bin/env python3
"""Exact selected s8 column0 leaves + original XHEAD3 stimulus, real leaf answers.
Reference is the fixed hard1/1 original head, not the legacy0/0 parent bench.
"""
from pathlib import Path
import subprocess,re,hashlib,json
R=Path(__file__).resolve().parents[2]
def main():
    t=subprocess.check_output(['git','show','2c3fd91ba:rtl/test/qwen_dv/s5/xhead3/tb_xhead3.sv'],cwd=R).decode()
    t=t.replace('module tb_xhead3;','module tb_s8_column;')
    t=t.replace("reg [511:0] lq = 512'd0, lq_d = 512'd0;",'wire [511:0] lq,lq_d;')
    t=t.replace("reg [7:0] lq_v = 8'hff, lq_v_d = 8'hff, lq_bad = 8'd0, lq_bad_d = 8'd0;",'wire[7:0]lq_v,lq_v_d,lq_bad,lq_bad_d;')
    t=t.replace('lq_d = lq; lq_v_d = lq_v; lq_bad_d = lq_bad; fault_i_d = fault_i;','fault_i_d = fault_i;')
    t='\n'.join(s for s in t.split('\n') if not any(z in s for z in ['lq[32 * i +: 32] = $urandom','lq_v = (urand','lq_bad = (urand']))
    src=(R/'rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv').read_text()
    a=src.index('    wire x00cv0');b=src.index('    // ---- column 1:',a);col=src[a:b]
    assert col.count('ot_qfd_xs_leaf')==8
    def block(side):
        x=col
        mp={'lw_v0':side+'_lwv','lw_ep0':side+'_lwep','lc_v0':side+'_lcv','lc_ep0':side+'_lcep','lw_off0':side+'_lwoff','lw_m0':side+'_lwm','lw_d0':side+'_lwd','lw_ctl0':side+'_lwctl','lr_v0':side+'_lrv','lr_t0':side+'_lrt','lr_ep0':side+'_lrep','lr_p0':side+'_lrp','lq0':'lq' if side=='o' else 'lq_d','lq_v0':'lq_v' if side=='o' else 'lq_v_d','lqb0':'lq_bad' if side=='o' else 'lq_bad_d'}
        x=re.sub(r'\b('+'|'.join(mp)+r')\b',lambda m:mp[m[0]],x)
        if side=='n':x=x.replace('.READ_PIN_PIPE(1)','.READ_PIN_PIPE(NEW_READ)')
        return 'generate begin : '+side+'_real_leaves\n'+x+'\nend endgenerate\n'
    defs='''`ifdef OT_S8_COL_MUT_READ0
 localparam NEW_READ=0;
`else
 localparam NEW_READ=1;
`endif
'''
    t=t.replace('    localparam integer OW =',defs+block('o')+block('n')+'    localparam integer OW =',1)
    monitor='''integer first_or=-1,first_oq=-1,first_nr=-1,first_nq=-1,edge_count=0;
 always @(posedge ck)begin
  #1;edge_count=edge_count+1;
  if(o_lrv[0] && first_or<0)first_or=edge_count;
  if(n_lrv[0] && first_nr<0)first_nr=edge_count;
  if(lq_v[0] && first_oq<0)first_oq=edge_count;
  if(lq_v_d[0] && first_nq<0)first_nq=edge_count;
 end
'''
    t=t.replace('    integer seed, cycles,',monitor+'    integer seed, cycles,',1)
    t=t.replace('$display("S5_XH3_EQ PASS', 'if(first_or<0 || first_nr<0 || first_oq<0 || first_nq<0)$fatal(1,"S8_COLUMN no real read coverage");\n            $display("S8_COLUMN_AGES first_req old=%0d new=%0d first_q old=%0d new=%0d; local leaf read=%0d/%0d",first_or,first_nr,first_oq,first_nq,first_oq-first_or,first_nq-first_nr);\n            $display("S5_XH3_EQ PASS',1)
    t=t.replace('if (mism == 0 && compares > 0 && n_en > 0 && n_vd > 0)\n','if (mism == 0 && compares > 0 && n_en > 0 && n_vd > 0) begin\n').replace('        else begin\n            $display("S5_XH3_EQ FAIL','        end else begin\n            $display("S5_XH3_EQ FAIL')
    t='// GENERATED: exact selected s8 column0 NCH4 READ1/FILL1 chains, real leaf returns. No whole-parent age claim.\n'+t
    (R/'rtl/test/qwen_dv/s8/tb_s8_column.sv').write_text(t)
    print('column source',hashlib.sha256(col.encode()).hexdigest(),'8 actual leaf instances per side')
if __name__=='__main__':main()
