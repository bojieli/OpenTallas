import json,sys,copy
WT='/home/ubuntu/wt/qe3-hroot-prompt35-1021'
gen=json.load(open(sys.argv[1]))   # generator record (macros original->instance)
inst={m['original'].split('u_ot_pr_core.')[-1]:m['instance'].replace('.','/') for m in gen['macros']}
TOP='qkd_hr_core_prompt_mu4p4_n32'; SRC='rtl/qwen_sys/host_prompt_mu4p4_n32_1021/qkd_hr_core_prompt_mu4p4_n32.sv'
old=json.load(open(WT+'/physical/ref_tile/qkd_hr_core_prompt_n34a/spec.json'))
oldgen_inst={'u53394_c0/u_cell':'u_rank__u_control__u_control.u_control.u_host.u_m.u_core.u_ev_sram.u_mem',
 'u55845_c0/u_cell':'u_rank__u_control__u_control.u_prompt.u_m.u_core.u_sram',
 'u57603_c0/u_cell':'u_rank__u_control__u_packet__u_axi.u_m.u_rx_sram.u_mem',
 'u58136_c0/u_cell':'u_rank__u_program.u_m.g_pm[0].u_pm','u58137_c0/u_cell':'u_rank__u_program.u_m.g_pm[1].u_pm',
 'u58138_c0/u_cell':'u_rank__u_program.u_m.g_pm[2].u_pm','u58139_c0/u_cell':'u_rank__u_program.u_m.g_pm[3].u_pm'}
B='tools/qwen_kv_die/host_cluster/bench/'
R='results/arch/qe3_hroot_prompt35_1021/'
benches=[
 dict(name='prompt_idle_lifecycle',expect='pass',threads=4,peak_ram_gb=8,needs=['verilator'],cmd=f'python3 {B}prompt_idle_lifecycle.py {{RUN}}/idle exact ps4',pass_regex='IDLE_LIFECYCLE PASS'),
 dict(name='prompt_idle_old',expect='fail',threads=4,peak_ram_gb=8,needs=['verilator'],cmd=f'python3 {B}prompt_idle_lifecycle.py {{RUN}}/idle_old old_idle ps4',fail_regex='IDLE_FAIL',fail_witness=R+'ps4_old_idle_FAIL_v5050.log'),
 dict(name='prompt_counters32',expect='pass',threads=4,peak_ram_gb=6,needs=['verilator'],cmd=f'bash {B}prompt_counters32.sh {{RUN}}/cn32',pass_regex='PROMPT_CN32_SUITE PASS'),
 dict(name='prompt_mem_suite',expect='pass',threads=4,peak_ram_gb=6,needs=['verilator'],cmd=f'bash {B}prompt_mem.sh {{RUN}}/mem_suite "pass wide bypass addr" r',pass_regex='PROMPT_MEM_SUITE PASS 2 positive 2 causal mutants'),
 dict(name='prompt_mem_addr',expect='fail',threads=4,peak_ram_gb=6,needs=['verilator'],cmd=f'bash {B}prompt_mem.sh {{RUN}}/mem_addr addr r',fail_regex='PROMPT_MEM FAIL',fail_witness=R+'mem_r_addr_fail_v5050.log'),
 dict(name='prompt_mem_vis',expect='fail',threads=4,peak_ram_gb=6,needs=['verilator'],cmd=f'bash {B}prompt_mem.sh {{RUN}}/mem_vis bypass r',fail_regex='PROMPT_MEM FAIL',fail_witness=R+'mem_r_vis_fail_v5050.log'),
 dict(name='prompt_axi',expect='pass',threads=4,peak_ram_gb=6,needs=['verilator'],cmd=f'bash {B}prompt_axi.sh {{RUN}}/axi prompt_safe4',pass_regex='PASS HOST_AXI_PACKET'),
]
extra=[p for p in old['job']['extra_paths'] if 'host_prompt_mu4p3_n32_1020' not in p and 'prompt_safe/ot_hkv_prompt_mem.sv' not in p]
extra+=['rtl/qwen_sys/host_cluster_20261017/prompt_safe4/','rtl/qwen_sys/host_cluster_20261017/prompt_safe3/','rtl/qwen_sys/host_cluster_20261017/prompt_safe/',
 'rtl/qwen_sys/host_prompt_mu4p4_n32_1021/evidence/','rtl/test/qwen_host/tb_hkv_prompt_mem_r.sv','rtl/qwen_sys/host_cluster_20261017/prompt_rr/qkd_host_ctl_service_pins_rr.sv',
 'rtl/qwen_sys/host_cluster_20261017/prompt_rr/qkd_host_csr_service_pins_rr.sv',R]
def mk(name,tag,outline=None,macros_at=None,ranges_scale=None):
    s=copy.deepcopy(old); s['name']=name; s['top']=TOP; s['sources'][0]=SRC
    for m in s['macros']:
        o=oldgen_inst[m['inst']]; m['inst']=inst[o]
        if macros_at: m['at']=macros_at[o]
    if outline:
        s['outline']={'w':outline[0],'h':outline[1],'exact':True}
    if ranges_scale:
        sx,sy=ranges_scale
        for k,v in s['pin_ranges'].items():
            if v==[59.4,415.8]: s['pin_ranges'][k]=[round(59.4*sx,1),round(415.8*sx,1)]
            elif v==[54.0,378.0]: s['pin_ranges'][k]=[round(54.0*sy,1),round(378.0*sy,1)]
    s['io_flop_at_pins']={'cols':4,'allow_none':True,'macro_out_pins':['rd_out']}
    s['pre_cts_extra']=['physical/ref_tile/qkd_hr_core_prompt_n34a/bnd_branch.tcl']
    j=s['job']; j['owner']='Claude:QE3-HROOT-PROMPT'; j['branch']='claude/qe3-hroot-prompt35-1021'; j['tag']=tag
    j['purpose']='MU4 prompt ps4 (registered SRAM reads) for the MU KV die host root cluster'; j['benches']=benches; j['extra_paths']=sorted(set(extra))
    s['pin_regs']['reason']=s['pin_regs']['reason'].replace('qkd_hr_core_prompt_mu4p3_n32 (sha 4379dbb8)',f'{TOP} (sha {gen["generated_sha256"][:8]})').replace('MU4 ps3','MU4 ps4').replace('mu4p3a gate synth c8920faa',f'mu4p4a gate synth {gen["source_sha256"][:8]}')
    s['reroute_reason']={'kind':'rtl_change','reason':'n34b FAIL (spread 102/100, macro->reg -399, macro->macro -301); n34a placed macro->reg -397: ps4 registered SRAM read outputs.'}
    return s
geo=sys.argv[2]
S=f'QE3-HROOT-PROMPT 10-21 successor of n34a/n34b: SOURCE ps4 native32 ({TOP}, sha {gen["generated_sha256"][:8]}, census max{gen["max_terminal_loads"]}) = ps3 + capture flops DIRECTLY on every used SRAM rd_out (RX + completion-event queues via ot_hkv_prompt_mem_r with the read address from the registered head pointer: no macro->macro path; 4 program macros p_qr) -> macro->flop = clk->q + wire; +2 edges queue visibility, +1 program edge (static). io_flop_at_pins macro_out_pins rd_out anchors the capture flops at the macro pins. CLOCK: n34a measured recipe (pin flops anchored at their faces, boundary on its own balanced+equalised branch bnd_branch.tcl, stem at ck_core beside the central register band; n34a 58.1/55.3 ps).'
a=mk('qkd_hr_core_prompt_n35a','n35a'); a['structural_change']=S+' MAIN: n34a geometry 475.2x432 (GRT ovf 0 measured).'
A={'u_rank__u_control__u_control.u_control.u_host.u_m.u_core.u_ev_sram.u_mem':[43.2,43.2],'u_rank__u_control__packet':None}
b_at={'u_rank__u_control__u_control.u_control.u_host.u_m.u_core.u_ev_sram.u_mem':[43.2,43.2],
 'u_rank__u_control__u_packet__u_axi.u_m.u_rx_sram.u_mem':[302.4,43.2],
 'u_rank__u_control__u_control.u_prompt.u_m.u_core.u_sram':[43.2,324.0],
 'u_rank__u_program.u_m.g_pm[0].u_pm':[302.4,324.0],'u_rank__u_program.u_m.g_pm[1].u_pm':[410.4,324.0],
 'u_rank__u_program.u_m.g_pm[2].u_pm':[302.4,367.2],'u_rank__u_program.u_m.g_pm[3].u_pm':[410.4,367.2]}
b=mk('qkd_hr_core_prompt_n35b','n35b',outline=(518.4,475.2),macros_at=b_at,ranges_scale=(518.4/475.2,475.2/432.0))
b['structural_change']=S+' FALLBACK: ENLARGED outline 518.4x475.2 (fill ~35%), macro channels >=20 um everywhere (the abutted 4x 256x64 stack becomes a 2x2 with 41.7/25.4 um channels), 81 um central column between the 32x546 pair.'
b['slot_change_request']='UNGRANTED: outline [518.4, 475.2]; parent repack needed.'
for s in (a,b):
    s['safe_design_checklist']={"1_pins":"SOURCE: every non-reset pin registered (flow pin regs in the ps4 synth), por_n 2-stage landing; ports/order unchanged; faces <=75%.",
     "2_reach":"pin flops anchored at faces, pin->logic <= ~240 um; rd_out capture flops anchored at the macro pins.",
     "3_fanout":f"native32 census max{gen['max_terminal_loads']} (regenerated; gate re-checks).",
     "4_depth":"macro->flop = clk->q + wire (no logic); header compare/consume reg->reg; read address from a register (no macro->macro).",
     "5_storage":"7 real SRAM macros; std bands between macro rows.",
     "6_floorplan":"fill ~41% (n35a) / ~35% (n35b enlarged); enlarge-not-squeeze.",
     "7_clock":"boundary own balanced+equalised branch, pin flops grouped by face (n34a measured 58.1/55.3 <=80).",
     "8_reset":"control/valid-only reset; queue tag/valid regs reset, capture data flops reset-free."}
    json.dump(s,open(WT+'/tools/ref_tile/specs_qhost_cluster/'+s['name']+'.json','w'),indent=1)
print('ok',a['macros'],b['macros'])
