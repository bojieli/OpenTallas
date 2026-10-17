import json,copy
from pathlib import Path
RT=Path('physical/ref_tile')
s=copy.deepcopy(json.loads((RT/'hcoll_inj_idx_join/spec.json').read_text()))
name='hcoll_inj_idx_join_rg_1017'
s['name']=name; s['top']='ot_hgi_coll_inj_idx_join_rg'
s['sources']=['rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_inj_idx_join_rg.sv']
s['params']={'INJLAT':12,'MUT':0}
W,H=216.0,432.0
s['outline']={'w':W,'h':H,'exact':True}
s.pop('util',None)
s['clock_port']='clk_r0'; s['clock']='multiple_cts_roots'; s['clock_ports']=['clk_r0','clk_r1']
s['clock_data_paths']='related_same_frequency'; s['clock_relationship']={'kind':'same_pll_fixed_phase','ratio':[1,1],'phase_ps':0}
ctl_in=['inj_rd','inj_idx','inj_addr','idx_tx_v','idx_tx_h','rst_n']
s['clock_entry_domains']={'core':{'ratio':[1,1],'ports':['clk_r0'],'inputs':['rst_n','inj_rd','inj_idx','inj_addr','idx_tx_v','idx_tx_h','su_inj_d_r0','idx_tx_r0'],'outputs':['inj_d_r0','fault']},
                          'r1':{'ratio':[1,1],'ports':['clk_r1'],'inputs':['rst_n_r1','inj_rd_r1','inj_idx_r1','inj_addr_r1','idx_tx_v_r1','idx_tx_h_r1','su_inj_d_r1','idx_tx_r1'],'outputs':['inj_d_r1']}}
s['reset_ports']=['rst_n','rst_n_r1']
# region 0 = lower half, region 1 = upper half. E: idx data halves around the header; W: SU halves around the request
# control; S/N: each region's output half with its own clock entry at the face centre.
s['pins']={'S':['inj_d_r0','clk_r0'],'N':['inj_d_r1','clk_r1'],'E':['idx_tx_r0','idx_tx_v','idx_tx_h','idx_tx_v_r1','idx_tx_h_r1','idx_tx_r1'],
           'W':['su_inj_d_r0','inj_rd','inj_idx','inj_addr','rst_n','fault','rst_n_r1','inj_rd_r1','inj_idx_r1','inj_addr_r1','su_inj_d_r1']}
m=H/2
s['pin_ranges']={'idx_tx_r0':[3.0,m-26],'idx_tx_v':[m-26,m-24],'idx_tx_h':[m-24,m-1],'idx_tx_v_r1':[m+1,m+3],'idx_tx_h_r1':[m+3,m+26],'idx_tx_r1':[m+26,H-3.0],
                 'su_inj_d_r0':[3.0,m-72],'inj_rd':[m-72,m-70],'inj_idx':[m-70,m-62],'inj_addr':[m-62,m-8],'rst_n':[m-8,m-6],'fault':[m-6,m-4],'rst_n_r1':[m+4,m+6],'inj_rd_r1':[m+6,m+8],'inj_idx_r1':[m+8,m+16],'inj_addr_r1':[m+16,m+70],'su_inj_d_r1':[m+72,H-3.0],
                 'inj_d_r0':[3.0,W/2-3],'clk_r0':[W/2,W/2+1],'inj_d_r1':[3.0,W/2-3],'clk_r1':[W/2,W/2+1]}
# outputs on S/N: put the clock in the middle by splitting the output range around it
s['pin_ranges']['inj_d_r0']=[3.0,W-3.0]; s['pin_ranges']['inj_d_r1']=[3.0,W-3.0]
s['pin_ranges']['clk_r0']=[W/2-0.5,W/2+0.5]; s['pin_ranges']['clk_r1']=[W/2-0.5,W/2+0.5]
s['std_area_um2']=8200
s['structural_change']=('cij successor (HBM-TILES-B 10-17) after the hcoll_inj_idx_join gate (HBM-C): one 9,926-sink root at TT '
 'insertion 396 ps, dl[7] slot select 4,208/4,180 loads, rst_q 321 loads. rg: TWO regional roots (clk_r0 lower half, clk_r1 '
 'upper half) by DATA BIT HALF (region r owns bits [256r+:256] of every 512-bit word: staging, SU word, output); per 32-bit '
 'group kept copies of the slot/source selects and of tx_v/write slots (<= ~256 loads each); one reset capture per region. '
 'Ports split by region (die contract bit-range edges, see RTL header). Same edges and faults: original bench MUT0 PASS / '
 'MUT1-4 FAIL on the rg, random lockstep vs the original PASS (skewed clk_r1 and slot mutant FAIL). 216x432: control pins replicated per region (each root captures only its own pins); E idx data 1,024 b per half over ~187 um (5.5/um).')
j=s['job']; j['owner']='Claude:HBM-TILES-B'; j['branch']='claude/hbmc-1017'; j['tag']='rg1'
j['purpose']='cij successor: 2 regional roots by bit half + replicated slot selects (HBM-TILES-B item 3)'
j['record_to']='results/rtl/ref_tile/'+name; j['views_to']=f'physical/ref_tile/{name}/views'
j['benches']=[{"name":"inj_idx_join_rg","cmd":"OUT={RUN}/bench bash -c 'mkdir -p {RUN}/bench && bash rtl/hbm_accel/generic/collective/p2p/run_inj_idx_join_rg_bench.sh'","expect":"pass","pass_regex":"INJ_IDX_JOIN_RG_BENCH PASS","threads":1,"peak_ram_gb":4,"needs":["iverilog"]}]
(RT/name).mkdir(exist_ok=True); (RT/name/'spec.json').write_text(json.dumps(s,indent=1)+'\n'); print(name)
