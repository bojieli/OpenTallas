BLOCKS = dict(
    sm=(SM_W * SM_H / 1e6, 'measured-placed', SM_CTX + ' die (2202.768 x 2072.79 um, 202 macros; element route OPEN, '
        'hbm_accel_fmax_inventory_20261004/sm/closure.json)'),
    svc=(1.40, 'estimate', 'per-stack stream service: 32 x ot_hbm_accel_stream_pc_wb 12,033 um2 + 2 x ot_hbm_r14_stream_stack '
         '~9,000 + 8 x ot_hbm_accel_cdc_fifo_r2 30,052 (routed, hbm_accel_fmax_inventory_20261004/svc) + expert fetch '
         '(est 0.2 mm2) = 0.84 mm2 at 0.6 utilisation'),
    su=(11.96, 'measured-placed', 'N1024 SU lane array, side 3,458 um (results/rtl/dshbm_1m_allmeasured_20261004/su_n2048/'
        'wire_stages.json, from the placed MLAT4/ALAT3 lane 7,349 um2)'),
    su_fused=(3.59, 'estimate', 'L3 fused SU chains (ot_dsrom_su_norm hc/q/kv, ot_dsrom_su_swiglu, hc_post NG256): +30 % of '
              'the SU lane array for the fused per-lane registers and quant tails (no area record; su_fused/fused.json is '
              'cycles only)'),
    sfu=(8.819, 'model', 'tools/uarch_model.hbm_gpu_design(v41).dedicated_units_mm2.sfu'),
    hc=(6.087, 'model', 'hc_fp32_lanes 5.984 + sinkhorn_select_engram 0.103 (same ledger)'),
    attn_tile=(0.5, 'estimate', 'attention tile ~0.5 mm2 x 64 (hbm_accel_fmax_inventory_20261004/attn/closure.json '
               'blocker field; ledger 16.69 mm2 for the engine is smaller, the estimate is kept conservative)'),
    index=(20.57, 'model', 'tools/uarch_model.hbm_gpu_design(v41).dedicated_units_mm2.indexer (idx_array + sel + '
           'sel_cand + l20_index_topk + actquant; no HBM-die record)'),
    coll=(1.10, 'estimate', 'TU endpoint 1.1 mm2 at 70 % utilisation (hbm_accel_ha2_ar_20261004/measured_composition.json '
          'G-area); routed endpoint context noc_tw_coll_ctx_f12x 0.2916 mm2 (noc/routes/collctx_f12x_r6)'),
    cmdproc=(0.60, 'estimate', 'ot_ds_hbm_cmdproc20 static program store + pipelined issue sequencer (no area record)'),
    vm=(1.50, 'estimate', 'VM / activation-multicast root: x staging 2 x 2,048 b x 128 deep + result publication buffers '
        '(S81 VM slab 0.892 mm2 x 1.7)'),
    barrier=(0.05, 'measured-routed', 'ot_hbm_accel barrier_k32 routed (ctl_takeover_20261005, +384.3 / +39.39 ps), slot'),
    loader=(0.3321, 'measured-slot', 'ot_hbm_accel_loader_host slot 576.288^2 um (tapeout_hbm_loader_20261004; host SS '
            '-3,672 ps, not adopted)'),
    router=(0.1861, 'measured-routed', 'ot_gpu_router_topk_f topk_f3 86,102 um2 (ctl_takeover_20261005) + expert workgroup '
            'steering/descriptor logic est 0.1 mm2 (lever L1, not built)'),
    quant=(0.50, 'estimate', 'ot_hdc_actquant FP4/FP8 quantisers (index_q, chains not fused)'),
    serdes=(18.0, 'model', 'TU SerDes reservation 18 mm2 (results/floorplan/hbm_gpu/v41_hbm_die.json fabric_serdes; '
            'hbm_accel_ha2_ar 40 lanes 16.0-17.1 mm2): real ot_pdie_serdes pin macros + slab'),
    host=(10.0, 'model', 'host UCIe/PCIe reservation 10 mm2 (v41_hbm_die.json ucie_phy): real ot_pdie_ucie pin macro + slab'),
)
