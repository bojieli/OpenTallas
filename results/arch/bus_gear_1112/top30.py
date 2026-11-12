#!/usr/bin/env python3
"""BUS-GEAR-1 top-30 table: families.tsv rows picked by corridor need (width x open types touched), with the
bus content / duty class / gearbox verdict read from RTL + plan (annotations below; DUTY = per-token use)."""
import csv
F = {(r['die'], r['family']): r for r in csv.DictReader(open('families.tsv'), delimiter='\t')}
A = [  # (die, family, content, duty, gearbox verdict)
 ('s81', 'x_*_in', 'slice C x_o -> leaf ft x3-5 -> station -> frame x_i (4 x 276-b V-format fragments, fwd clk xk)', 'LOW: x beats per frame op << frame op cycles (ffn.down 2889, wo_a 4224, FGU 3680)', 'CANDIDATE B 2:1 (2 x 276 lanes, 2 beats)'),
 ('s81', 'x_*_out', 'slice C x_o1 -> leaf ft -> frame p1..p3 ft -> frame p4 x_i', 'LOW (as x_in)', 'CANDIDATE B 2:1'),
 ('s81', 'up_s', 'leaf leafup_o -> slice C (leaf gather up)', 'per leaf op return; not read yet', 'study'),
 ('s81', 'dn_s', 'slice C leafdn_o -> leaf (leaf scatter)', 'per leaf op; not read yet', 'study'),
 ('s81', 'attn__svc', 'cut through ONE svc engine (dsdv_svc_rs, "not bit-sliceable")', 'n/a (internal netlist cut)', 'NO: not a transaction bus; needs svc RTL re-partition'),
 ('s81', 'attnh__svc', 'svc hi<->lo cut, 8.03 pins/um', 'n/a (internal cut)', 'NO (as attn)'),
 ('s81', 'fi_*_p*_r0r1', 'frame_int: 3017 1-bit LANDED nets of the flat col_h9_l4 netlist (lp.py), 1167-1264 b', 'n/a (arbitrary internal nets, no valid/beat)', 'NO: no transaction semantics; M8 grant (B) path'),
 ('s81', 'hbmrd__phy_hbm__svc_*', 'PHY -> svc HBM read data 1120 b', 'HIGH during attention KV read', 'NO'),
 ('s81', 'hbm__svc', 'svc HBM req/wdata 682 b', 'LOW (writes/requests)', 'maybe (small)'),
 ('hbm', 'L8', 'hub u_ctl_Q_p00..09 -> PHY_N: row/col cmd 40 b + col_data 256 + col_strb 32 per PC (x10)', 'LOW: col_data/strb only valid on col_we (writes = KV append / spill)', 'CANDIDATE A 2:1 on col_data+strb (-144 b/PC)'),
 ('hbm', 'L9', 'hub u_ctl_Q_p10..15 -> PHY_NC via vsN4-6/root: same as L8 (x6)', 'LOW (writes only)', 'CANDIDATE A 2:1'),
 ('hbm', 'L21', 'PHY_N -> hub dram_rdata/rvalid (x10 PCs)', 'HIGH: weight + KV read stream', 'NO'),
 ('hbm', 'L22', 'PHY_NC -> hub dram_rdata (x6)', 'HIGH', 'NO'),
 ('hbm', 'L160', 'hub -> q_b000 idx-score quarter input (4986 b)', 'IDX scan stream', 'cost = IDX stretch (priced below)'),
 ('hbm', 'L1228', 'hub -> q_b100 idx-score quarter input (4986 b)', 'IDX scan stream', 'cost = IDX stretch'),
 ('hbm', 'L161', 'q_b000 -> q_b010 idx quarter cut 4512 b', 'IDX', 'cost = IDX stretch'),
 ('hbm', 'L10', 'q_b002 -> q_b003 u_hcb sum_out chain 4401 b', 'IDX/FUSED scorer chain', 'cost = IDX stretch'),
 ('hbm', 'L11', 'q_b011 -> q_b010 4401 b', 'IDX', 'cost = IDX stretch'),
 ('hbm', 'L15', 'q_b001 -> q_b002 u_hcb sum_in 4128 b', 'IDX', 'cost = IDX stretch'),
 ('hbm', 'L1220', 'q_b100 -> q_b110 -> q_spu1 (ft, E face 8 pins/um) -> q_b102: re-broadcast of the hub idx stream', 'IDX scan stream', 'CANDIDATE C 2:1 only if IDX stretch is cheap'),
 ('hbm', 'L1201', 'q_b102 -> q_b111 -> q_b103 3332 b re-broadcast', 'IDX', 'as L1220'),
 ('hbm', 'L8300', 'idx return 1615 b chain over q_b000..b011', 'per-token IDX result', 'study'),
 ('hbm', 'L1204', 'q_su21 -> q_su20 pretree_ro_v/x 4448 b', 'SU pretree (per SU op)', 'study'),
 ('hbm', 'L33', 'hub -> q_spu1 -> q_spb2 -> sm2 data 1615 b', 'SM load', 'study'),
 ('hbm', 'L156', 'hub -> root idx return 4796 b (cr 274 + argmax 274 + index_rq 136 + vm_rr 8x257)', 'once per IDX record', 'maybe 2:1'),
 ('qc', 'sl_*_stm__b_tw_data_stm_ctl', 'stm -> ctl tw_data 2103 b', 'not read yet', 'study'),
 ('qc', 'sl_*_ctl__b_hw_ctl_hc0', 'ctl -> hc0 hw 1573 b', 'not read yet', 'study'),
 ('qc', 'sl_*_fw__x_fw_ctl_p2', 'fw -> ctl x data 536 b (sl_sc ft, 9.1-9.4k ft bits per sl_sc)', 'not read yet', 'sl_sc re-floor READY p99<1 (VL2QC-SC 00:48)'),
 ('qc', 'sl_*_fw__x_fw_fe', 'fw -> fe x 539 b (x3 phases)', 'not read yet', 'as above'),
 ('kv', 'L363', 'kv3_hg -> kv3_hgi i_ectl 1559 b x32 at 12.49 pins/um', 'KV attention stream', 'study'),
]
cols = ['die', 'family', 'wmax', 'hops', 'open_types', 'types', 'dens', 'content', 'duty', 'verdict', 'open_list']
with open('top30.tsv', 'w') as f:
    f.write('\t'.join(cols) + '\n')
    for die, fam, c, du, v in A:
        r = F.get((die, fam), {})
        f.write('\t'.join([die, fam, r.get('wmax', ''), r.get('hops', ''), r.get('open_types', ''), r.get('types', ''),
                           r.get('dens', ''), c, du, v, r.get('open_list', '')]) + '\n')
print(len(A))
