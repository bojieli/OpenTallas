import json,sys,copy
W='/home/ubuntu/wt/qw-ctlm7-1020'
SRC=['rtl/qwen_dv/lp7_np/qfd_tt_ctlm_dv_np_lp.sv','rtl/qwen_dv/lp7_np/qfd_tt_ctlm_dv_np_helpers.sv',
     'rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv',
     'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_bb.v',
     'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v']
def mk(base_path,name,tag,extra_note):
    d=json.load(open(base_path))
    old=d['name']
    d['name']=name; d['top']='qfd_tt_ctlm_dv_np_lp'; d['sources']=SRC; d['params']={}
    d['views_to']=f'physical/ref_tile/{name}/views'; d['record_to']=f'results/rtl/ref_tile/{name}'
    d['landed_record']='results/arch/landed_parent_1018/ctlm6_np/qfd_tt_ctlm_dv_lpf_lp_record.json'
    # name-based reset-copy hooks do not apply to the bounded netlist (construct caps every load <= 32, native PASS)
    d['pin_hook_after_flops']=[f'physical/ref_tile/{name}/lp_cone_regions.tcl']
    d.pop('post_stage_audits',None)
    j=d['job']
    j['owner']='QW-SUVM8/CTLM7'; j['branch']='claude/qw-ctlm7-1020'; j['tag']=tag
    j['purpose']=('QW-SUVM8/CTLM7 10-20 '+tag+': CTLM candidate7 = Codex candidate6 bounded native32 netlist (ctlm6_bound_macro, no X refinement) '
      'rebuilt from depth-safe exact RTL (XPF schedule twin, PW observer twin, cal_mu fault flags/seal_bad/bend/rng CSA/one-hot seg select, '
      'f_idx split + ctx_mask4 X-arm source fixes); old-RTL vs new-netlist lockstep PASS. Kit = '+old+' floorplan/pins/clock domains. '+extra_note)
    j['views_to']=d['views_to']; j['record_to']=d['record_to']
    ep=[p for p in j.get('extra_paths',[]) if 'qfd_tt_ctlm_dv_safe5' not in p or 'bench_witness' in p]
    ep+=['rtl/qwen_dv/lp7_np','rtl/test/qwen_dv/ctlm7_xpf','results/arch/landed_parent_1018/ctlm6_np']
    j['extra_paths']=ep
    j['benches']=[]
    d['structural_recut_status']='CTLM7 candidate7: gate evidence for the bounded netlist; ck_hr own-entry (lp entry_pins) NOT applied in this kit.'
    return d
for base,name,tag,note in [(W+'/physical/ref_tile/qfd_tt_ctlm_dv_safe5/spec.json','qfd_tt_ctlm_dv_safe7','safe7','Main.'),
                           ('/tmp/ctlm7_safe5c_spec.json','qfd_tt_ctlm_dv_safe7c','safe7c','Parallel fallback: safe5c ck_core/rst_n on the S face (centre of the core S pin band).')]:
    d=mk(base,name,tag,note)
    json.dump(d,open(f'{W}/physical/ref_tile/{name}/spec.json','w'),indent=1)
    print(name,'ok')
