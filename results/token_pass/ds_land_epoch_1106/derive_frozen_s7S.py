from pathlib import Path
import re,json,hashlib
R=Path('/srv/opentallas-scratch2/claude/codex-ds-img2-service-1105');S=Path('/srv/opentallas-scratch2/claude/tok-ds-2/v0copy/rtl')
C=S/'s81p_dsdv_slice_lepe_nh_mus_C__t1.sv';L=S/'s81p_dsdv_slice_lepe_nh_mus_LP__t1.sv';T=S/'s81_bound_top.sv'
def graph(p):
 s=p.read_text();g={}
 for line in s.splitlines():
  m=re.search(r'ot_dp_rrelay\s+(\w+)\s*\([^\n]*\.d\((\w+)\)[^\n]*\.q\((\w+)\)',line)
  if m:g[m[3]]=(m[2],1,m[1])
 for dest,src in re.findall(r'wire\s+(\w+)\s*=\s*(\w+)\s*;',s):g[dest]=(src,0,'alias')
 def age(n):
  if n=='arst_n':return 0
  src,d,_=g[n];return age(src)+d
 return s,g,age
c,cg,ca=graph(C);l,lg,la=graph(L)
assert 'assign w_u_s_7S_5_Y = rst_n;' in c
assert re.search(r'u_bout_lpc_o0[^\n]*\.d\(\{w_u_s_7S_8_Y\[0\], w_u_s_7S_5_Y\[0\]\}\)',c)
assert re.search(r'u_bin_lpc_i0[^\n]*\.d\(lpc_i0\[1:0\]\)[^\n]*\.q\(lpc_i0_q\)',l)
assert '.rs_k(lpc_i0_q[0])' in l and '.rs_n(w_10_Y[0])' in l and 'assign w_10_Y = rst_n;' in l
s=T.read_text()
def inst(n):return re.search(r'\b'+n+r'\s*\((.*?)\n    \);',s,re.S)[1]
ci,li=inst('s_7S_C'),inst('s_7S_LP')
def port(i,n):return re.search(r'\.'+n+r'\((\w+)\)',i)[1]
assert port(ci,'rst_o_1')==port(li,'arst_n')
assert port(ci,'lpc_o0')==port(li,'lpc_i0')
mu=R/'external/srv/opentallas-scratch2/claude/wt/tok-ds-2/rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv'
assert mu.read_text().count('.DEPTH(3)')==2
c_local=ca('rst_n');lp_arst=ca('rst_o_1');kn_source=c_local+2;nk_source=lp_arst+la('rst_n')
out=dict(scope='Frozen11-01 S81 s_7S_C -> s_7S_LP u_lnl1; not currentwc1 qualification',reference_origin='s_7S_C.arst_n release edge0',source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [C,L,T,mu]},derived_edges=dict(C_local_rst=c_local,C_rst_o_1_LP_arst=lp_arst,C_lpc_tx=c_local+1,LP_lpc_rx_kn_rs=kn_source,LP_local_rst_nk_rs=nk_source,KN_writer_rq_origin=kn_source+4,KN_reader_rq_origin=nk_source+4),formula='EPOCH_BIAS=(reader_release_edge-writer_release_edge) mod(2D)',D=4,K=2,KN_bias=(nk_source-kn_source)%8,NK_bias=(kn_source-nk_source)%8,pin_cycles_added=0,observed_trace=dict(LP_arst=31,LP_lpc_rx=33,KN_writer_rq=37,KN_reader_rq=43),current_bound_adopted=False)
assert out['KN_bias']==6 and out['NK_bias']==2
(R/'frozen_s7S_epoch_receipt_v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
