"""Export source hierarchy/clock associations for the real Col8 candidate.
Run from the worktree root. This records source wiring, not physical qualification.
"""
import hashlib,json,pathlib
r=pathlib.Path.cwd();d=r/'results/arch/hbm_col8_parent_1021'
src=['rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_col8_sram.sv','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_leaf_col8_sram.sv','rtl/hdc/v41x/ot_hbm_idx_chunk_col8_face.sv','rtl/hdc/v41x/ot_hbm_idx_col8_sram_face.sv','rtl/hdc/v41x/ot_hbm_idx_col8_sram_landed.sv','rtl/hdc/v41x/ot_hbm_idx_col8_landed.sv','rtl/hdc/v41x/ot_hbm_idx_score_col8.sv','rtl/hdc/v41x/ot_hbm_idx_chunk_rt_c.sv','rtl/hdc/v41x/ot_hidx_meta_sram146.sv','rtl/hdc/v41x/ot_hbm_idx_owned_native.sv','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_fault_static.sv']
g=json.loads((d/'column_geometry.json').read_text());cols=[];res=[];clocksets={}
for q in ['SW','SE','NW','NE']:
 root=f'hb_idx__s_{q}';active={root+'.clk_ctl'}
 for e in range(2):
  for k in ['clk_engine','clk_meta','clk_tail']:active.add(f'{root}.{k}[{e}]')
  for c in range(4):
   leaf=f'{root}.ge[{e}].gc[{c}].leaf';chunk=f'{leaf}.core';ctl=f'{root}.clk_chunk[{e*4+c}]';active.add(ctl)
   res.append(dict(kind='shared_leaf_and_chunk_glue',path=leaf,core=chunk,glue=chunk+'.u_glue',clock=ctl,reset=root+'.rst_c',counted_once_for_columns=4))
   for col in range(4):
    path=f'{chunk}.g_col[{col}].u_col';cp=[f'{root}.clk_hslice[{e*128+c*32+8*col+2*i}]' for i in range(4)];active.update(cp);clks={'ctl':ctl,**{f'cp[{i}]':cp[i] for i in range(4)}};parts=[]
    for a in g['rectangles']:
     n=a['name'];kind=a['kind'];actual=None
     if kind in ['pair','SRAM'] or '.d_pin['in n or '.q_pin['in n:
      # The face-reset successor wraps each wide SRAM seam in u_ring.
      if n.startswith(tuple(f'l{i}.' for i in range(4))):n=n[:3]+'u_ring.'+n[3:]
      actual=path+'.'+n
     owner=a['clock_owner'];owner={k:clks[v] for k,v in owner.items()} if isinstance(owner,dict) else clks[owner]
     parts.append(dict(placement_name=a['name'],kind=kind,exact_source_path=actual,clock_owner=owner,reset_owner=path+'.reset_leaf' if kind!='pair' else path+f'.reset_leaf[{int(a["name"][-1])}]',notes='Exact instance/bit range' if actual else 'Soft placement reserve containing named reset/ring/control logic; not a hard macro instance'))
    cols.append(dict(placement_key=f'{q}.engine{e}.leaf{c}.column{col}',path=path,master='ot_hidx_col8_sram_face_col',quarter_master='ot_hbm_idx_score_quarter_col8_sram',TP=192,ctl_clock=ctl,pair_clocks=cp,pair_clock_formula='clk_hslice[engine*128 + leaf*32 + column*8 + RID*2]',reset_input=f'{chunk}.crst[{col}]',regions=['CTL','PAIR_R0','PAIR_R1','PAIR_R2','PAIR_R3'],parts=parts))
  res.extend([dict(kind=k,path=f'{root}.ge[{e}].{p}',clock=f'{root}.{clk}[{e}]',reset=root+'.rst_c') for k,p,clk in [('engine_glue','ENGINE_GLUE_SOFT_REGION','clk_engine'),('keep_D129_W4','keep_pipe','clk_engine'),('metadata_D146_W25_SRAM','md.u_mem','clk_meta'),('tail','u_t','clk_tail')]])
 res.append(dict(kind='quarter_control',path=root,clock=root+'.clk_ctl',reset_input=root+'.rst_n',ports='Unchanged full quarter interface; half, rank[7:0], first_ord[10:0], nkeys[11:0], keep_en, keep_bitmap[170:0], ql_v, ql_head[7:0], ql_codes[511:0], ql_sc[31:0], ql_w[15:0], beat_v, beat_index[7:0], key_lines[4395:0], score[305:0], fault'))
 assert len(active)==143,(q,len(active));clocksets[q]=sorted(active)
x=dict(status='SOURCE GRAPH FOR DIAGNOSTIC COMPOSITION. R3 stand-in, reset/CTS/route qualification open. No r18 release adoption.',source_commit='c6989e9ea',source_sha256={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in src},geometry_commit='5f4e5992c',geometry_sha256=hashlib.sha256((d/'column_geometry.json').read_bytes()).hexdigest(),columns=cols,residual_regions=res,active_clock_names=clocksets,clock_bits_declared_per_quarter=271,clock_bits_active_per_quarter=143,legacy_unused_odd_hslice_bits_per_quarter=128,counts=dict(columns=128,pairs=512,new_wide_seam_srams=1536,new_metadata_srams=8),ages=dict(column_active_delta_edges=23,wide_seam_edges=5,return_edges=3,quarter_metadata_D=146,quarter_keep_D=129,extra_die_hops='OPEN: regenerate from actual placed graph; do not alias to old latency'),qualification=dict(pair_R0='97c58e235 CLOSED',pair_R1='4c5e0ced5 CLOSED',pair_R2='b2651c581 CLOSED',pair_R3='STANDIN_NOT_A_VIEW',face_chunk_equivalence='PASS 2344 checks,1063 valid/nonzero,0 errors; EP5 unit1578519-1792643845',face_MAIN_FB='live gate, not qualified',metadata_MAIN_FB='live gate, not qualified'))
(d/'source_graph.json').write_text(json.dumps(x,indent=2)+'\n');print('Exported',len(cols),'columns;',len(res),'residual regions; clocks',[len(a) for a in clocksets.values()])
