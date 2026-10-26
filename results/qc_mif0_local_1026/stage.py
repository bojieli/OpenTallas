from pathlib import Path
import subprocess,re,sys,json,hashlib
REPO=Path(__file__).resolve().parents[2]
p='rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
original=subprocess.check_output(['git','-C',str(REPO),'show','d4347f1bc:'+p],text=True)
source=(REPO/p).read_text()
# The reference is the pinned original, not the candidate's default branch.
baseline=re.sub(r'\b(qfd_dv_[A-Za-z0-9_]+)\b',r'\1_baseline',original)
(out/'baseline.sv').write_text(baseline)
(out/'candidate.sv').write_text(source)
(out/'models.sv').write_bytes((REPO/'rtl/test/qwen_dv/s5/sram_models_nofatal.sv').read_bytes())
tb=(REPO/'results/qc_sramif_readhalf_2220/tb_readhalf.sv').read_text()
tb=tb.replace('`timescale 1ns/1ps','`timescale 1ps/1fs').replace('always #1 ck = ~ck','always #416.5 ck = ~ck')
tb=tb.replace('qfd_dv_s8x_btab #(.MIF(1), .ROW_WRITE_RELAY(0)) ob','qfd_dv_s8x_btab_baseline #(.MIF(0)) ob')
tb=tb.replace('qfd_dv_s8x_prog #(.MIF(1), .ROW_WRITE_RELAY(0)) op','qfd_dv_s8x_prog_baseline #(.MIF(0)) op')
tb=tb.replace('#(.MIF(1), .ROW_WRITE_RELAY(1), .WR_HALF_CYCLE(1), .RD_HALF_CYCLE(1))','#(.MIF(0), .MIF0_LOCAL_HALF(1))')
tb=tb.replace('wire [255:0] o_bq, n_bq; wire o_f, n_f;','wire [255:0] o_bq, n_bq, z_bq; wire o_f, n_f, z_f;')
tb=tb.replace('.bs_q(),','.bs_q(z_bq),').replace('.fault());','.fault(z_f));')
tb=tb.replace('if (n_f !== o_f)', 'if (z_bq !== o_bq || z_pq !== o_pq || z_f !== o_f) begin ez=ez+1; if(ez<4) $display("DEFAULT-OFF MISMATCH c=%0d",c); end\n        if (n_f !== o_f)')
tb=tb.replace('if (eb || ep || ef)', 'if (eb || ep || ef || ez)')
tb=tb.replace('integer seed = 1;', '''integer writes=0,reads=0,collisions_b=0,collisions_p=0;
  always @(posedge ck) if(c>12) begin
    if(ob.g_btb[0].u_m.w_ce_in) writes++;
    if(ob.g_btb[0].u_m.r_ce_in) reads++;
    if(ob.g_btb[0].u_m.r_ce_in && ob.g_btb[0].u_m.w_ce_in && ob.g_btb[0].u_m.r_addr_in==ob.g_btb[0].u_m.w_addr_in) collisions_b++;
    if(op.g_prog[0].u_lo.r_ce_in && op.g_prog[0].u_lo.w_ce_in && op.g_prog[0].u_lo.r_addr_in==op.g_prog[0].u_lo.w_addr_in) collisions_p++;
  end
  reg [8:0] last_tw_addr=0;
  integer seed = 1;''')
tb=tb.replace('if ((c % 16) == 0) begin bs_addr[8:2] = tw_addr[8:2]; p_idx[8:1] = tw_addr[7:0]; end', '''if((c%16)==0) begin tw_we=1;tw_kind=2;tw_kind_p=3;end
    if((c%16)==1) begin bs_re=1;p_re=1;bs_addr[8:2]=last_tw_addr[8:2];p_idx[8:1]=last_tw_addr[7:0];end
    last_tw_addr=tw_addr;''')
tb=tb.replace('$finish;', '''$display("MIF0_LOCAL_HALF transactions reads=%0d writes=%0d collisions_b=%0d collisions_p=%0d",reads,writes,collisions_b,collisions_p);
    if(nzb<100 || nzp<100 || reads<100 || writes<100 || collisions_b==0 || collisions_p==0) $fatal(1,"WEAK_STIMULUS");
    $finish;''')
assert 'qfd_dv_s8x_btab_baseline' in tb and 'MIF0_LOCAL_HALF(1)' in tb
(out/'tb.sv').write_text(tb)
edge,n=re.subn(r'qfd_dv_s8x_kffn( #\(\.W\(1\), \.ID\(9004 \+ 32\*bk\)\) u_rce_f)',r'qfd_dv_s8x_kff\1',source)
assert n==1,n
(out/'wrong_edge.sv').write_text(edge)
old='u_lra_r (.ck(ck), .d(p_idx[8:1]), .q(pre_lra));'
assert source.count(old)==1
(out/'wrong_row.sv').write_text(source.replace(old,'u_lra_r (.ck(ck), .d(p_idx[8:1] ^ 8\'d1), .q(pre_lra));'))
(out/'source.json').write_text(json.dumps(dict(baseline_commit='d4347f1bc',source_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),candidate_sha256=hashlib.sha256(source.encode()).hexdigest(),reference_sha256=hashlib.sha256(original.encode()).hexdigest(),cycles_added=0,clock_ps=833,N=20000),indent=2)+'\n')
