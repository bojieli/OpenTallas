# HBM v13 die netlist port-bind audit (2026-10-14, tools/hbm_die_port_bind.py on the 2240 STA case die.v, a44b378b6 candidate)

VERDICT: FAIL (OWNER NO STUBS). 6 of 107 non-glue die masters have RTL under their die name; every hfd_* block master is a pin-only die shell; 86,701 die-generated glue instances (reset relays, clock buffers, wire stages, stations) have no RTL module.

| die master family | masters | instances | RTL under die name | die ports not in RTL | RTL inputs unconnected | width mismatches | owner |
|---|---:|---:|---:|---:|---:|---:|---|
| hfd_meso | 48 | 70 | 0/48 | 0 | 0 | 0 | die lead (stations) |
| hfd_attn_half | 2 | 64 | 2/2 | 5 | 1 | 0 | attention halves (hbm-phys-1010) |
| hfd_svc | 17 | 34 | 0/17 | 0 | 0 | 0 | stream service (svc) |
| hfd_sm | 1 | 32 | 0/1 | 0 | 0 | 0 | SM compaction (el1013-smh-r11 / hbm VM/SM 2240) |
| hfd_mcast | 4 | 24 | 0/4 | 0 | 0 | 0 | die lead (stations) |
| hfd_gath | 5 | 16 | 0/5 | 0 | 0 | 0 | die lead (stations) |
| hfd_lk_ep | 1 | 9 | 1/1 | 0 | 4 | 0 | LKEP (el1013-lkep-split) |
| ot_pdie_serdes | 1 | 9 | 0/1 | 0 | 0 | 0 | PHY hard IP: link layer RTL (die lead) |
| hfd_cdist | 2 | 8 | 0/2 | 0 | 0 | 0 | die lead |
| hfd_hc | 2 | 5 | 0/2 | 0 | 0 | 0 | HC/norm (el1013-hbm-norm-attn-physical) |
| hfd_hgi_vms | 4 | 4 | 0/4 | 0 | 0 | 0 | VM/SM 2240 |
| hfd_idx_score_native_grid | 1 | 4 | 0/1 | 0 | 0 | 0 | native IDX (el1014-hbm-native-idx-parent) |
| hfd_sfu | 1 | 4 | 0/1 | 0 | 0 | 0 | SFU (el1013-hbm-sfu) |
| hfd_su | 1 | 4 | 0/1 | 0 | 0 | 0 | SU.VOP stream |
| hfd_vm | 4 | 4 | 0/4 | 0 | 0 | 0 | VM8 CP (vm8) |
| ot_hbm3e_phy_v41x_aw30_e8p5 | 1 | 4 | 0/1 | 0 | 0 | 0 | PHY hard IP: needs real DFI controller RTL (die lead) |
| ot_hgi_dma_back | 1 | 4 | 1/1 | 8 | 0 | 0 | DMA back (dbk) |
| hfd_coll | 2 | 2 | 0/2 | 0 | 0 | 0 | COLL/TKM (el1011-hbm-coll) |
| hfd_serdes_slab | 1 | 2 | 0/1 | 0 | 0 | 0 | die lead (link/PHY ctrl RTL) |
| hfd_cmdproc | 1 | 1 | 0/1 | 0 | 0 | 0 | cmdproc (hgi) |
| hfd_hgi_am | 1 | 1 | 1/1 | 2 | 8 | 0 | MTP |
| hfd_hgi_idx | 1 | 1 | 0/1 | 0 | 0 | 0 | HGI IDX topk (Codex hbm_index_physical->Claude) |
| hfd_host_slab | 1 | 1 | 0/1 | 0 | 0 | 0 | die lead (host PHY ctrl RTL) |
| hfd_idx_sel_native_qend | 1 | 1 | 0/1 | 0 | 0 | 0 | native IDX |
| hfd_loader | 1 | 1 | 0/1 | 0 | 0 | 0 | DMA/loader (el1011-hbm-dmafs) |
| hfd_quant | 1 | 1 | 0/1 | 0 | 0 | 0 | quant (el1013-quant-tput)/QDQ |
| hgi_mtp_native | 1 | 1 | 1/1 | 2 | 2 | 0 | MTP (hb_mtp) |
| ot_hbm_host_phy | 1 | 1 | 0/1 | 0 | 0 | 0 | PHY hard IP (die lead) |
| die-generated glue (hfd_rrl/ckb/rly/stn*/att_su_relay) | 23 | 86701 | 0/23 | - | - | - | die lead: generator must emit real RTL for relay/station/clock-buffer/reset-relay masters |
