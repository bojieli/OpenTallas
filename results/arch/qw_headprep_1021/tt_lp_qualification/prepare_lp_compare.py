from pathlib import Path
import subprocess,json,sys
r=Path(sys.argv[1]).resolve();base='d2c8e45a7'
def get(p):return subprocess.check_output(['git','show',base+':'+p])
for folder in ['results/rtl/qw_tlprod_1020/images','results/rtl/qw_calr_1020/ctlm9c']:
 for p in subprocess.check_output(['git','ls-tree','-r','--name-only',base,folder],text=True).splitlines():
  if '/images/' in p:dst=p.split('/images/',1)[1]
  elif p.endswith('.hex'):dst='calr/'+p.rsplit('/',1)[1]
  else:continue
  q=r/dst;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(get(p))
s=get('results/rtl/qw_tlprod_1020/tb_np10.sv').decode()
s=s.replace('qfd_tt_ctlm_dv_lpf #(','qfd_tt_ctlm_dv_lpf_hp #(').replace('qfd_tt_ctlm_dv_np_lp u_lp','qfd_tt_ctlm_dv_lpf_hp_lp u_lp')
# Resolve exact selected historical top invocation, preserving the entire real-calendar stimulus.
s=s.replace('qfd_tt_ctlm_dv_np_lp #(','qfd_tt_ctlm_dv_lpf_hp_lp #(')
params=json.loads((r/'tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_hp_h16z.json').read_text())['params']
pars=', '.join(f'.{k}({v})' for k,v in params.items())
s=s.replace('qfd_tt_ctlm_dv_lpf_hp_lp u_lp',f'qfd_tt_ctlm_dv_lpf_hp_lp #({pars}) u_lp')
assert 'qfd_tt_ctlm_dv_np_lp' not in s
s=s.replace('    wire [0:0] fo_cf, lo_cf;', '''    wire [17:0] fo_emb_position,lo_emb_position;reg[17:0] dlo_emb_position[0:6];
    wire [1:0] fo_emb_user,lo_emb_user;reg[1:0] dlo_emb_user[0:6];
    always @(posedge clk)begin: hp_delay integer j;dlo_emb_position[0]<=fo_emb_position;dlo_emb_user[0]<=fo_emb_user;for(j=1;j<=6;j=j+1)begin dlo_emb_position[j]<=dlo_emb_position[j-1];dlo_emb_user[j]<=dlo_emb_user[j-1];end end
    wire [0:0] fo_cf, lo_cf;''')
s=s.replace('.emb_token(fo_emb_token),','.emb_token(fo_emb_token), .emb_position(fo_emb_position), .emb_user(fo_emb_user),').replace('.emb_token(lo_emb_token),','.emb_token(lo_emb_token), .emb_position(lo_emb_position), .emb_user(lo_emb_user),')
s=s.replace('            if (warm > 38) begin','''            if (warm > 38) begin
                nc=nc+1;if(lo_emb_position!==dlo_emb_position[5] || lo_emb_user!==dlo_emb_user[5])begin bad=bad+1;if(bad<=5)$display("LP_MISMATCH true emb position/user cycle=%0d",cyc);end''')
assert 'wire [17:0] fo_emb_position' in s and '.emb_position(fo_emb_position)'in s
(r/'tb_hp_calr.sv').write_text(s)
files=(r/'source.f').read_text().splitlines()+['rtl/qwen_dv/headprep/lp_h16z/qfd_tt_ctlm_dv_lpf_hp_lp.sv','tb_hp_calr.sv']
(r/'hp_calr.f').write_text('\n'.join(dict.fromkeys(files))+'\n')
