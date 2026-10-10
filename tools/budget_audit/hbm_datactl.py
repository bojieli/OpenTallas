import json
CLK=1.2e9
DS_C=543456.7; QW_C=1258136.1; DF_C=5364526.1; TAU=8.01
def tok(c): return round(CLK/c,1)
rows=[]
def R(**k):
    k.setdefault('new_gap',True); k.setdefault('known_gap',None)
    m=k.get('margin')
    if 'flag' not in k:
        k['flag']='UNKNOWN' if m is None else ('OK' if m>=1.1 else ('THIN' if m>=1.0 else 'GAP'))
    if k.get('tok_s_if_as_designed') is not None and 'tok_s_impact' not in k:
        k['tok_s_impact']=round(k['tok_s_if_as_designed']-k['_tgt'],1)
    k.pop('_tgt',None); rows.append(k)
# --- CP fetch
fd=json.load(open('/home/ubuntu/claude-takeover-20261007/budget-audit-1010/fetch_demand.json'))
ds_img=470912; rtt=104
des=32/rtt; des160=32/160
req=ds_img/DS_C
R(id='hbm_ds_cp_fetch',target='hbm_ds',mode='AR',unit='CP.fetch',resource='record-ring fetch: ot_hgi_seq (NOS 48) -> ot_hgi_cp_die (48 in flight) -> loader kport lane 1 -> ot_hbm_loader_service_boundary native port',
  metric='bytes/cycle',work_per_token=ds_img,work_unit='program bytes fetched per token (DS image is unrolled, 3,952 records, no LOOP replay)',
  required=round(req,3),required_basis='470,912 B / 543,456.7 cyc (ds_native_timing_1M.json result.program.image_bytes, S2.total_cycles); simulator prices 64 B per 2 cycles, unlimited outstanding (tools/hgi_sim/timing.py:398-408)',
  designed=round(des,3),designed_basis='ot_hbm_loader_service_boundary.sv:20-24: ONE native transaction per stack (active), length forced to 1 unless ENABLE_NATIVE_BURST (default 0; ot_hfd_loader_kport drives no native_len) -> one 32 B sector per HBM round trip; RTT 104 cyc (measured first access) = 0.31 B/cyc, 0.20 at the calibration 160',
  measured=None,measured_basis='hgi-e2e.log:14: DS L0 with stub units and the serial lane: FLAT 104 -> 38,134 cyc vs simulator 12,087 (3.15x); the post-F5 e2e numbers (DS 14,015) use the harness FPIPE pipelined-lane model, not the RTL svc boundary',
  margin=round(des/req,2),critical_path=True,tok_s_if_as_designed=round(CLK/(ds_img/des),1),_tgt=2208.1,flag='INFEASIBLE',
  known_gap=None,new_gap=True,owner_stream='hgi-1010',
  fix_hint='wire native bursts (75b874a3f, opt-in, len 8 = 256 B/RTT -> 2.2 B/cyc, margin 2.6) through ot_hfd_loader_kport lane 1 (coalesce in-order ring sectors) and/or allow >1 native transaction per stack; tracked as F5(3) in hgi-takeover.log:286-290 but NOT in hgi-1010 gap list and not in e2e_calibration sensitivity',confidence='derived')
dfb=fd['dflash_b16']['fetched_bytes']; req=dfb/DF_C
R(id='hbm_dflash_cp_fetch',target='hbm_dflash',mode='DFlash',unit='CP.fetch',resource='same fetch path; 6 of 9 DFlash LOOP bodies (24-40 KB verify bodies) exceed the 8 KB ring and are re-fetched every iteration',
  metric='bytes/cycle',work_per_token=dfb,work_unit='program bytes fetched per DFlash b16 step',
  required=round(req,3),required_basis='scripts/fetch_demand.py (simulator ring rule, timing.py:398-408) on dflash.step_program B16 pos 8176: 1,572,320 B over the 5,364,526-cycle step (dflash_timing.json steps[B16 spec])',
  designed=round(des,3),designed_basis='as hbm_ds_cp_fetch (0.31 B/cyc at RTT 104, 0.20 at 160); ot_hgi_seq RW 512 = 8 KB ring (ot_hgi_seq.sv:33)',
  margin=round(des/req,2),critical_path=True,tok_s_if_as_designed=round(TAU*CLK/max(DF_C,dfb/des160),1),_tgt=1791.8,flag='GAP',
  owner_stream='hgi-1010',fix_hint='margin 1.05 at RTT 104, 0.68 at the calibration RTT 160 (tok/s shown at 160). Native bursts (as above) or a 64 KB ring so verify bodies replay; also compiler: split verify bodies <= 8 KB',confidence='derived')
R(id='hbm_qwen_cp_fetch',target='hbm_qwen',mode='AR',unit='CP.fetch',resource='same fetch path; Qwen layer body 3,648 B replays from the 8 KB ring',metric='bytes/cycle',
  work_per_token=fd['qwen_P8191']['fetched_bytes'],work_unit='program bytes fetched per token',required=round(4736/QW_C,4),required_basis='scripts/fetch_demand.py',
  designed=round(des,3),designed_basis='as above',margin=round(des/(4736/QW_C),1),critical_path=False,tok_s_if_as_designed=953.8,_tgt=953.8,new_gap=False,owner_stream='hgi-1010',fix_hint='none',confidence='derived')
R(id='hbm_ds_mtp_cp_fetch',target='hbm_ds_mtp',mode='MTP',unit='CP.fetch',resource='same fetch path; DS MTP step program (draft + verify) is at least the AR image per step',metric='bytes/cycle',
  work_per_token=None,work_unit='program bytes per MTP step',required=None,required_basis='>= AR image 470,912 B per step; step cycles = accepted tokens x 1.2e9 / 3,344.8',
  designed=round(des,3),designed_basis='as hbm_ds_cp_fetch',margin=None,critical_path=True,tok_s_if_as_designed=None,flag='INFEASIBLE',owner_stream='hgi-1010',
  fix_hint='same fix as hbm_ds_cp_fetch; re-run fetch_demand on the DS MTP program once exported',confidence='derived')
# --- CP decode / dispatch
R(id='hbm_ds_cp_dispatch',target='hbm_ds',mode='AR',unit='CP.dispatch',resource='ot_hgi_seq word-serial decode (16 B/edge) + radix-16 iterative effective-base multiplier + dispatch relays (4-17 edges, priced in S2)',
  metric='cycles/record',work_per_token=3952,work_unit='records',required=137.5,required_basis='543,456.7 / 3,952 mean unit service per record (records are a dependency chain: per_unit idle_true_dep dominates in S0); shortest SU records ~99 cyc (ds_native_timing_1M.json S2.per_unit.SU busy/records)',
  designed=None,designed_basis='ot_hgi_seq.sv:9-21: ~8 edges decode for a 119 B record + <=8 iterations a scaled descriptor; addresses computed before the wait, I-table reads after it',
  measured=1.16,measured_basis='results/rtl/hgi_e2e_20261009 STATUS + handoff 4.3: DS L0 real CP + real DMA/SU/COLL/IDX/QUANT 14,015 cyc vs simulator 12,087 (all residual incl. unit ratios, so CP share <= 16%)',
  margin=None,critical_path=True,tok_s_if_as_designed=None,flag='OK',new_gap=False,owner_stream='hgi-1010',fix_hint='isolate CP-only cost in e2e (all-stub run with FPIPE) to grade it measured',confidence='measured')
# --- KV read paths
R(id='hbm_qwen_kv_read_8k',target='hbm_qwen',mode='AR',unit='KV_READ',resource='svc KV row stream (CF-SVC Qwen 8K dense sweep, 1,024 sectors a PC per layer)',metric='fraction of 4.0 TB/s die peak',
  work_per_token=151.0e6,work_unit='bytes of K+V per die per token (36 layers x 2 KV heads x 2 x 8192 x 128 FP8)',required=0.95,required_basis='minimum to hold the designed 953.8: Qwen ATT.QK/PV records are serial on the critical path (no compute to overlap the KV stream inside a record; next record depends on its scores), and the 953.8 schedule allots them the KV stream at 3,166.7 B/cyc = 0.95 of peak (timing.py:274-281). Not a fixed-percentage rule',
  designed=None,designed_basis='svc KV path (ot_hbm_svc_core kind-1 KV row reads, 4 sectors on KV_PC)',measured=0.7985,measured_basis='results/rtl/hbm_system_20261008/svc_kvs.json summary.1024: mean 0.7985 (min 0.638, max 0.915) of peak, REFpb refresh model, 12 runs',
  margin=round(0.7985/0.95,2),critical_path=True,tok_s_if_as_designed=round(CLK/(QW_C+151.0e6/3166.7*(0.95/0.7985-1)),1),_tgt=953.8,
  owner_stream='hbm-phys-1010',fix_hint='real but small shortfall (-6.8 tok/s mean, -17 at min); cross-check with hgi-1010/f per-path table (ATT KV-row achieved BW in RTL); fix only if f confirms on the r25 svc (this is the r16g svc_kvs bench)',confidence='measured')
R(id='hbm_ds_index_keys_1m',target='hbm_ds',mode='AR',unit='KV_READ',resource='svc index-key sweep at 1M (181 sectors a PC)',metric='ns per sweep',work_per_token=None,work_unit='index-key sweeps (IDX.INDEX records x8)',
  required=3100.0,required_basis='IDX.INDEX priced ~3,720 cyc a record (ds_native_timing_1M.json family indexer 29,760 / 8) -> key read must fit well inside it',
  measured=369.6,measured_basis='svc_kvs.json summary.184: mean 369.6 ns (max 827.9), 0.563 of peak',margin=round(3100/827.9,1),critical_path=True,tok_s_if_as_designed=2208.1,_tgt=2208.1,new_gap=False,owner_stream='hbm-phys-1010',fix_hint='none (latency-bound, fits)',confidence='measured')
R(id='hbm_ds_window_rows_1m',target='hbm_ds',mode='AR',unit='KV_READ',resource='svc window rows (17 sectors a PC a layer)',metric='ns per layer',required=None,required_basis='DS ATT T128 priced 147.1 cyc a record (hgi-1010.log g priced shapes) incl. row fetch',
  measured=122.1,measured_basis='svc_kvs.json summary.17: mean 122.1 ns = 146.5 cyc (max 186.3 ns = 224 cyc), 0.146 of peak, latency-bound',margin=round(147.1/(122.1*1.2),2),critical_path=True,tok_s_if_as_designed=round(CLK/(DS_C+80*(186.3*1.2-147.1)),1),_tgt=2208.1,flag='GAP',
  owner_stream='hgi-1010',fix_hint='ATT price 147.1 cannot contain a 146-224 cyc HBM window fetch + compute: prefetch window rows one layer ahead (overlap) or reprice; check ds_native ATT cost vs svc first access',confidence='derived')
# --- ATT unit HBM lane
R(id='hbm_att_unit_hbm_lane',target='hbm_qwen',mode='AR',unit='ATT',resource='IF the die ATT is ot_hgi_att_unit (header: "ATT unit die body", hgi-adapters D4) -- the alternative G12 path (g12/ot_hgi_att_row_sources + record adapter) keeps the legacy gather readers on svc KV lines (row hbm_qwen_kv_read_8k): ONE HBM read lane, 32 B a response, NOUT 8 outstanding',metric='bytes/cycle',
  work_per_token=151.0e6,work_unit='KV bytes per die per token',required=3166.7,required_basis='ATT priced at the die bandwidth (timing.py:274-281); 1 MB a QK/PV record in 331 stream cycles',
  designed=round(8*32/104,2),designed_basis='rtl/hbm_accel/generic/peers/ot_hgi_att_unit.sv:20-21,33 (ONE HBM read lane, NOUT=8): Little 8 x 32 B / 104-cyc RTT = 2.46 B/cyc (cap 32 B/cyc at zero latency); not instantiated in any die view; ALSO row-serial: :344-372 waits hout==0 before the next row (~111 cyc a row at L 104 -> Qwen ~913k cyc a 8,192-row record vs 660.1 priced); 128 hfd_attn_half_* masters missing in index_r25g.json',
  margin=round(8*32/104/3166.7,5),critical_path=True,tok_s_if_as_designed=round(CLK/(QW_C+151.0e6/(8*32/104)),1),_tgt=953.8,flag='INFEASIBLE',
  known_gap='sm_att_hc_meas',new_gap=True,owner_stream='hgi-1010',fix_hint='the ATT record path must bind to the 64 tile pairs on svc KV lines (striped rows, >= 0.9 peak), not one 32 B lane; size outstanding by Little: 3,166.7 B/cyc x ~104 cyc = 330 KB = 10.3k sectors in flight per die',confidence='derived')
# --- DMA write paths
R(id='hbm_ds_kvwb',target='hbm_ds',mode='AR',unit='DMA',resource='DMA.KVWB_DS (DS KV write-back) record service',metric='cycles/record',work_per_token=40,work_unit='records',required=60,required_basis='calibration DMA.store/fence 60 (e2e_calibration.json per_unit DMA.KVWB_DS sim_cost)',
  measured=376,measured_basis='e2e_calibration.json per_unit DMA.KVWB_DS ds_L0 rtl_service 376 (ratio 6.267)',margin=round(60/376,2),critical_path=True,tok_s_if_as_designed=tok(DS_C+40*(376-60)),_tgt=2208.1,
  owner_stream='hgi-1010',fix_hint='posted write-back: retire on acceptance (fence covers visibility) instead of on write completion; or stream KVWB through the svc DMA stream',confidence='measured')
R(id='hbm_qwen_dma_store',target='hbm_qwen',mode='AR',unit='DMA',resource='DMA.STORE (Qwen KV append)',metric='cycles/record',work_per_token=72,work_unit='records (36 layers x K,V)',required=30,required_basis='simulator: kv_append 2,160 cyc / 72 records = 30 a record (qwen_timing_P8191_v10.json family_unit_cycles)',
  measured=258/2,measured_basis='e2e_calibration.json per_unit DMA.STORE qwen_L0 rtl_service 258 over 2 records (ratio 4.3)',margin=round(30/129,2),critical_path=True,tok_s_if_as_designed=tok(QW_C+72*(129-30)),_tgt=953.8,
  owner_stream='hgi-1010',fix_hint='same: posted store retire at acceptance',confidence='measured')
R(id='hbm_dma_load',target='hbm_qwen',mode='AR',unit='DMA',resource='DMA.LOAD via kport / mover (one sector per round trip) until the svc DMA stream binds',metric='ratio rtl/sim',required=1.0,required_basis='e2e_calibration',
  measured=9.204,measured_basis='e2e_calibration.json DMA.LOAD qwen 9.204 (DS 2.813)',margin=round(1/9.204,2),critical_path=True,tok_s_if_as_designed=890.7,_tgt=953.8,known_gap='svc_dma_width',new_gap=False,owner_stream='hgi-1010',fix_hint='svc DMA stream v2 (hgi-1010 c / hbm-phys)',confidence='measured')
R(id='hbm_svc_dma_strip',target='hbm_ds',mode='all',unit='SVC',resource='svc DMA stream convergence wiring in the 259 um svc strip',metric='bits per cut',required=3647,required_basis='hbm-phys-1010.log 06:44 [svc]: SW cuts 0-3 need 3,010-3,647 b',designed=2668,designed_basis='cut capacity ~2,668 b (M4/M6 alternate, 0.096 um a bit)',
  margin=round(2668/3647,2),critical_path=False,tok_s_if_as_designed=None,flag='OK',known_gap='svc_dma_width',new_gap=False,owner_stream='hbm-phys-1010',fix_hint='owner rule 10-10 06:58: no fixed 90% target and DMA->VM is not a weight/KV stream; DMA.LOAD costs only ~20 tok/s DS / 2 Qwen (e2e_calibration dma_full_bw delta), so the svc DMA v2 widening and its strip blocker are NOT required unless hgi-1010/f finds a short weight/KV path',confidence='derived')
# --- weights stream
R(id='hbm_qwen_weight_stream',target='hbm_qwen',mode='AR',unit='SVC',resource='svc -> SM weight stream (PS rows / SM lines) on the r25 die',metric='fraction of 4.0 TB/s die peak',
  work_per_token=None,work_unit='INT8 fmt3 weight bytes per die',required=0.775,required_basis='Qwen SM records are SM-issue bound: gu 12,635 cyc for 2x12288x4096/4 x1.25 = 31.5 MB -> 2,583 B/cyc = 0.775 of peak (timing.py:250-263 cost = fa + max(comp, stream))',
  measured=0.862,measured_basis='proxy only: svc_kvs.json summary.2048 steady stream mean 0.862 (min 0.750) on the r16g svc; r25 svc striping (H8) not qualified (calibration hbm.bytes_per_cycle source)',
  margin=round(0.862/0.775,2),critical_path=True,tok_s_if_as_designed=953.8,_tgt=953.8,known_gap=None,new_gap=False,owner_stream='hgi-1010',
  fix_hint='cross-check for hgi-1010/f (SM weight-stream achieved BW in RTL); not a shortfall at the bench mean. Qualify the r25 SM-line stream at die level (H8); at the bench minimum 0.750 the margin is 0.97 and gu/down become HBM-bound',confidence='modelled')
# --- collectives
R(id='hbm_qwen_allreduce',target='hbm_qwen',mode='AR',unit='COLL.ALL_REDUCE',resource='TP4 256-word all-reduce (endpoint + link + FEC)',metric='cycles/record',work_per_token=72,work_unit='records',required=1350,required_basis='calibration COLL.ALL_REDUCE_SUM 1350 = 928 ns endpoint + 0.2 us FEC budget',
  measured=1230,measured_basis='e2e_calibration.json COLL.ALL_REDUCE_SUM qwen 2,460 / 2 records (ratio 0.911); single-rank method, peers golden',margin=round(1350/1230,2),critical_path=True,tok_s_if_as_designed=953.8,_tgt=953.8,new_gap=False,owner_stream='hgi-1010',
  fix_hint='72 serial all-reduces = 97.2k cyc (7.7% of the token) not overlapped with the next matvec; overlap (start next layer prenorm on partial) is an opportunity',confidence='measured')
R(id='hbm_ds_group_reduce',target='hbm_ds',mode='AR',unit='COLL.GROUP_REDUCE_MCAST',resource='s=8 sub-group reduce + multicast over 96 dies',metric='cycles/record',work_per_token=40,work_unit='records',required=1325.9,required_basis='e2e_calibration sim_cost',
  measured=1205,measured_basis='e2e_calibration.json ratio 0.909',margin=round(1325.9/1205,2),critical_path=True,tok_s_if_as_designed=2208.1,_tgt=2208.1,new_gap=False,owner_stream='hgi-1010',fix_hint='single-rank method: switch-tier contention of 12 sub-groups not measured',confidence='measured')
# --- clock gating wake
R(id='hbm_cg_wake',target='hbm_ds',mode='all',unit='CG_WAKE',resource='ot_cg_tile wake (cgi pin flop, 1 register a hop, HOLD 64) driven by the record adapter busy',metric='cycles exposed per record',required=0,required_basis='wake must lead data; DS SM 1,095 records with idle gaps > HOLD 64 -> a wake per record',
  designed=0,designed_basis='rtl/hbm_accel/cg/ot_cg_tile.sv:5-8 (wake runs ahead of data, fewer registers than the data path); ot_hbm_accel_smh.sv:95-96 wake from the SM record adapter busy; SU tiled bench: 20-edge-late wake settles 63 vs 46 (hbm-phys-1010.log 06:37) -> hidden only if raised at dispatch',
  margin=None,critical_path=False,tok_s_if_as_designed=None,flag='UNKNOWN',new_gap=True,owner_stream='hbm-phys-1010',
  fix_hint='SM wake output / cg_en pins on SM and HC die views are not bound yet (handoff 4.4); bench the die-level wake source at dispatch for SM/HC/ATT: a wake raised at staging end exposes ~2-17 edges a record (DS SM 1,095 records -> up to 18.6k cyc = 3.3%)',confidence='derived')
frag=dict(fragment='hbm_datactl',target='hbm_generic',clock_ghz=1.2,
  target_rates={'DS_AR_native':dict(tok_s=2208.1,source='results/arch/hgi_sim_20261009/ds_native_timing_1M.json result.S2'),
                'DS_AR_gather':dict(tok_s=1747.5,source='results/arch/token_path_20261009/README.md'),
                'DS_MTP':dict(tok_s=3344.8,source='token_path README'),
                'Qwen_AR':dict(tok_s=953.8,source='results/arch/hgi_sim_20261009/qwen_timing_P8191_v10.json result.S2'),
                'Qwen_DFlash_b16':dict(tok_s=1791.8,source='results/arch/hgi_sim_20261009/dflash/dflash_timing.json')},
  cycles_per_token_budget={'DS_AR':DS_C,'Qwen_AR':QW_C,'DFlash_b16_step':DF_C},rows=rows,
  notes=['Tokens are a dependency chain (per_unit idle_true_dep dominates even in S0), so a unit is on the critical path whenever it runs; required = priced service.',
         'Opportunities (not margin gaps): Qwen ARGMAX.LOCAL reads VM at 1 elem/cyc = 76,395 cyc (6.1%) + head_scale 76,503; a STREAM argmax (16/cyc) would cut ~72k cyc -> ~1,016 tok/s.',
         'svc_kvs.json is the r16g svc stream bench; the r25 svc has not had a die-level KV / weight bandwidth bench.'])
json.dump(frag,open('/home/ubuntu/claude-takeover-20261007/budget-audit-1010/hbm_datactl.json','w'),indent=1)
for r in rows: print(r['id'],r['flag'],r.get('margin'),r.get('tok_s_if_as_designed'),r.get('tok_s_impact'))
