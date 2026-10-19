import json,copy
from pathlib import Path
RT=Path('physical/ref_tile')
s=copy.deepcopy(json.loads((RT/'hbm_argmax_swvm/spec.json').read_text()))
name='hbm_argmax_swvm_r2_1017'
s['name']=name; s['top']='ot_hbm_argmax_static_sw_vm_r2'
s['sources']=['rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv','rtl/lib/ot_rst_relay.sv',
 'physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv','physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv',
 'rtl/gpu/ot_gpu_fadd.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv']
s['params']={'TP':192}
W=H=118.8
s['outline']={'w':W,'h':H,'exact':True}
s['pins']={'W':['vm_rq','vm_rr'],'E':['cq','cq_seq','cr'],'N':['die_id','go','mode','imm_a','a_mirror','a_base','n','o_base','o_is','busy','done','fault','nan_flag'],'S':['rst_n','clk']}
s['pin_ranges']={'rst_n':[W/2-6,W/2-4],'clk':[W/2-0.5,W/2+0.5]}
s['std_area_um2']=6300
s['pin_regs']={'enable':False,'reason':'r2 RTL registers every input at the pin (command, vm_rr, cr) and every output is a flop; the added edges are in the r2 timeline (go +1, VM capture +5 incl. the share merge chain, ACK 13).'}
s['structural_change']=('argmax successor r2 (HBM-TILES-B 10-17) after the hbm_argmax_swvm gate (HBM-C): rst_n 2,137 loads -> '
 'ot_rst_relay 3 regions; 258 input->reg endpoints >3 lv -> input pin registers on every input; vm_rr 2,056 b -> 264 b '
 '{lane valid8, data256}: the 8:1 sector select moved into the IDX VM share bank-pair leaves (ot_hbm_idx_vm_share_static_am, '
 'equal-latency 4-hop OR chain). Fits the r6 slot 118.8 sq: W 400 pins (3.4/um), E 614 (5.2/um), N ~103, S clk/rst. '
 'Bench run_argmax_r2.sh vs ot_hbm_argmax_static_sw_vm: same requests/writes/events in order at constant offsets '
 '(rq +1, writes +6, events +7), MUT1-3 FAIL.')
j=s['job']; j['owner']='Claude:HBM-TILES-B'; j['tag']='r2'
j['purpose']='argmax successor r2: pin registers, reset relay, 264-b VM response (8:1 select in the IDX share); r6 slot 118.8 sq'
j['record_to']='results/rtl/ref_tile/'+name; j['views_to']=f'physical/ref_tile/{name}/views'
j['extra_paths']=['rtl/test/hbm_netlist_v16/run_argmax_r2.sh','rtl/test/hbm_netlist_v16/tb_argmax_sw_vm_r2.sv',
 'rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv','rtl/hbm_accel/generic/ot_hbm_argmax_static.sv',
 'rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv','rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_am.sv','physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv']
j['benches']=[{"name":"argmax_r2_equiv_and_mutants","cmd":"bash rtl/test/hbm_netlist_v16/run_argmax_r2.sh {RUN}/bench","expect":"pass","pass_regex":"ARGMAX_R2_BENCH PASS","threads":1,"peak_ram_gb":4,"needs":["iverilog"]}]
(RT/name).mkdir(exist_ok=True); (RT/name/'spec.json').write_text(json.dumps(s,indent=1)+'\n'); print(name)
