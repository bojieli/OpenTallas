#!/usr/bin/env python3
"""HBM-V15-HARDEN (2026-10-15): ref_tile specs for unowned v15.1 die-master leaves.
Faces follow the v15.1 dataflow: VM/landing side N, PHY/writeback side S, control/status W, outputs to clients E."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_die_views as views
OUT=ROOT/'tools/ref_tile/specs_hbm_v15_harden'
SR128='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
SR1K='physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2'
COMMON_EXTRA=['tools/hbm_v15_harden','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2','physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2',SR128,SR1K]
def ports(path,top,params=None):
    return views.L.parse_module(path,top,params or {})['ports']
def bench(script,mut_list,passre,countre=None,ram=4):
    b=[dict(name='exact',cmd=f'bash tools/hbm_v15_harden/{script} {{RUN}}/bench/exact 0',expect='pass',threads=1,peak_ram_gb=ram,needs=['iverilog'],pass_regex=passre)]
    if countre:b[0]['min_count_regex']=countre
    for m in mut_list:b.append(dict(name=f'mutant{m}',cmd=f'bash tools/hbm_v15_harden/{script} {{RUN}}/bench/mut{m} {m}',expect='fail',threads=1,peak_ram_gb=ram,needs=['iverilog']))
    return b
AREA={'hv15_svc_pc':502,'hv15_vm_status4':83,'hv15_vm_cal_sw':389,'hv15_vm_cal_se':362,'hv15_vm_cal_nw':378,'hv15_vm_cal_ne':362}
def spec(name,top,sources,faces,macros,outline,purpose,benches,params=None,extra=()):
    p=ports(sources[0],top,params)
    planned=[x for f in faces.values() for x in f]
    missing=[x for x in p if x not in planned]; extra_p=[x for x in planned if x not in p]
    assert not missing and not extra_p,(name,missing,extra_p)
    bits={f:sum(p[x][1] for x in v) for f,v in faces.items()}
    s=dict(name=name,top=top,kind='tile',sources=sources,clock_port='clk',reset_ports=['rst_n'],pins=faces,
           layer_cap='M5',recipe=2,macros=macros,
           route=dict(pd=0.5,period_ps=833.333,threads=8,peak_ram_gb=24,hold_margin_ns=0.03),
           job=dict(owner='Claude:HBM-V15-HARDEN',branch='claude/hbm-v15-harden-1015',tag='hv15',purpose=purpose,
                    extra_paths=COMMON_EXTRA+list(extra),record_to=f'results/rtl/ref_tile/{name}',benches=benches))
    if params:s['params']=params
    if name in AREA:s['std_area_um2']=AREA[name]
    else:s['outline']=outline
    (OUT/f'{name}.json').write_text(json.dumps(s,indent=1)+'\n')
    print(name,top,'face bits',bits,'ports',len(p))
OUT.mkdir(parents=True,exist_ok=True)
pc='rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_pc.sv'
spec('hv15_svc_pc','ot_hbm_svc_static_pc',[pc,SR128+'/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
 dict(N=['fill_v','fill_bank','fill_epoch','fill_slot','fill_data','read_v','read_bank','read_epoch','read_slot','out_v','out_data'],
      S=['k_v','k_rdy','k_addr','k_len','k_tag','k_we','k_wdata','k_wstrb','k_wr_done','kr_v','kr_rdy','kr_tag','kr_beat','kr_data'],
      W=['clk','rst_n','open_v','open_bank','open_epoch','open_count','retire_v','retire_bank','retire_epoch','cmd_v','cmd_write','cmd_bank','cmd_epoch','cmd_addr','cmd_step'],
      E=['block_ready','bank_owned','busy','done','fault']),
 [dict(view=SR128,count=1)],dict(w=172.8,h=151.2),
 'v15.1 svc band leaf: one physical HBM PC (real 128x256 payload SRAM); hardened once, instantiated by all 17 hfd_svc_v15_* band masters (34 inst). PHY-boundary k_rdy/kr_rdy only (owner 10-14: flow control only at the HBM-stack boundary).',
 bench('bench_svc_pc.sh',[1],r'STATIC_PC PASS',r'read_vectors=(\d+)'))
s4='rtl/hbm_accel/generic/vm/static/ot_vms_status4_static.sv'
spec('hv15_vm_status4','ot_vms_status4_static',[s4],dict(W=['clk','rst_n','quadrant_status'],E=['vmstat']),[],dict(w=43.2,h=43.2),
 'v15.1 vm_status4: four quadrant vmstat -> CP vmstat19, three fixed rungs.',bench('bench_status4.sh',[1],r'VMS_STATIC_STATUS4 PASS'))
cal='rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv'
for q in ('SW','SE','NW','NE'):
    top='hfd_hgi_vm_calendar_'+q
    p=ports(cal,top)
    outs=[x for x,(d,w) in p.items() if d=='output' and x not in ('calendar_v','active','done','fault','ordinal')]
    spec('hv15_vm_cal_'+q.lower(),top,[cal,'rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv',SR1K+'/ot_sram_1r1w_1024x256_m2_r2c2_bb.v'],
     dict(W=['clk','rst_n','cfg_we','cfg_addr','cfg_data','start_v','start_base','start_limit','start_loops'],E=outs,S=['calendar_v','active','done','fault','ordinal']),
     [dict(view=SR1K,count=1)],dict(w=259.2,h=151.2),
     f'v15.1 VM calendar {q}: compiler programme SRAM (1024x256) drives VM slice slots, LG selects, ring/replay, response enables on fixed cycles (no credits).',
     bench('bench_calendar.sh',[1,2],r'VMS_STATIC_CALENDAR PASS',r'PASS(\d+) gapless'))
dbk='rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static.sv'
for k in range(4):
    spec(f'hv15_dma_back_stk{k}','ot_hgi_dma_back_static',[dbk,SR128+'/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
     dict(N=['rq','rr'],S=['wd','wa','wb_reserve_v','wb_reserve_bank','wb_fill_bank','wb_reserve_epoch','wb_fill_epoch','wb_reserve_sectors','wb_reserve_base','wb_fill_start','wb_ready'],
          W=['clk','rst_n','cycle','mv_v','mv','issue_at','drain_at','mv_wb_bank','mv_wb_epoch','mv_src','mv_done','mv_fault','quiet','busy']),
     [dict(view=SR128,count=8)],dict(w=432.0,h=302.4),
     f'v15.1 hb_dbk_{("SW","SE","NW","NE")[k]}: static scheduled DMA STORE back engine, STK={k}, eight real landing SRAMs, VM RG1 direct (bank n+1/n+7), fixed cycles.',
     bench('bench_dma_back.sh',[1,2],r'PASS DMA static actual production',ram=8),params=dict(STK=k),extra=['rtl/hbm_accel/generic/vm/static'])
# monolithic delivery kit removed 10-15: local gate FAIL pin_fit (8,960 pins on S = 124 % of slots), clock span > 600 um,
# 2,048-bit runtime part-select -> structural split below (ot_hbm_svc_static_vm_delivery_split).
spl='rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_static_vm_delivery_split.sv'
SPLIT_PURPOSE=('structural split of delivery_<q> (monolithic gate: 8,960 fill pins on one face = 124 %% of slots, > 600 um clock span, '
 '2,048-bit runtime group mux): 8 identical VM-bank lane leaves + 1 control leaf under a wires-only parent, cycle- and bit-identical '
 '(lockstep equivalence + production bench); cost 0 cycles. %s')
dsb=lambda: bench('bench_delivery_split.sh',[1,2],r'DELIVERY_SPLIT_BENCH PASS',r'checks=(\d+)',ram=8)
spec('hv15_vmdel_bank','ot_hbm_svc_vmdel_bank',[spl,SR128+'/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
 dict(S=['fill_v','fill_bank','fill_slot','fill_epoch','fill_data'],N=['dq'],
      W=['clk','rst_n','bank_id','owned','epochs','issue','rb','rg','rs','clear_bank','begin_bank','landing_fault','dq_v','out_group','sector_hi','full0','full1','pc_fault']),
 [dict(view=SR128,count=4)],dict(w=302.4,h=172.8),SPLIT_PURPOSE%'Leaf: PCs b,8+b,16+b,24+b (4 real SRAMs) + dq[b]; hardened once, 8 per quadrant.',dsb())
spec('hv15_vmdel_ctl','ot_hbm_svc_vmdel_ctl',[spl],
 dict(W=['clk','rst_n','begin_v','begin_bank','begin_epoch','start','start_bank','start_epoch','start_base_sector','block_ready','busy','fault'],
      E=['full0','full1','pc_fault','owned','epochs','issue','rb','rg','rs','clear_bank','landing_fault','dq_v','out_group','sector_hi']),
 [],dict(w=43.2,h=43.2),SPLIT_PURPOSE%'Leaf: begin/start/aperture/owned/epoch/running state, block_ready/fault aggregation.',dsb())
