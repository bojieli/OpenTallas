#!/usr/bin/env python3
"""KVJ-G2 2026-10-17 (kv_static_join_plan item 10, lanes/KV-INT.md): the 669-instance static KV subsystem PLACED in the
kv_die.py --split die.  Opt-in OT_KV_STATIC_DIE=1 (default off: every existing plan is unchanged).

Source of truth: the merged static compiler join (kv_static_kvjf_join.build(): template + boot + 160 boot CDC + HOST
admission + ownership observer + die cfg) with the priced ages (die_ages.json, kv_static_ages.apply).  Nothing here
invents a producer: every join edge is kept bit-exact; a join input with no producer stays an OPEN die input (listed
with its owner in the plan record), never a tie.

Physical homes (beside their consumers, neighbour-only links, every die hop relayed at the plan reach):
  kvpc_<st>_<k>  x128  qkd_kvs_pc / qkd_kvs_pc_h : pc_path_emb + its embedding return station (hop, head on PC 0), at the
                       old controller slot of PC k (abuts the HBM PHY's per-PC DFI words, 378-um PC pitch)
  slg_<st>_<g>   x32   qkd_kvs_grp : landing seg + landing / front calendars + phase launch + drain guard + 5 boot CDCs of
                       one landing group, level with its four PCs, between the HOST slice column and the V ports
  ectl_<st>_<g>  x32   qkd_ectlk   : the engine-control frame re-bound to qkd_ectl3_kiss_s (ECTL A + its static K issuer,
                       ki folded in, kv_static_join_plan (b)); K request / response = one abutting-channel hop to its group
  vport_<st>_<k> x16   (existing qkd_pv16_vport) : V get / rsp to groups 2k / 2k + 1 (RT = 9, 0 relays)
  kvs_ctl        x1    qkd_kvs_ctl : layer programme (boot-loaded, replaces the die's lprg image), writer + writer programme,
                       ownership calendar + observer, boot dispatcher + observer, die cfg; beside the HOST root / D2D end
  kvs_attn       x1    qkd_kvs_attn: the native attention programme (attention calendar), at the PV pairs' D2D end
  kvs_emb        x1    qkd_kvs_emb : embedding join4 + row transmitter, beside the D2D end (port 2)
  kc_<st>        x4    qkd_ctrl_kc : the kc stream-command head of each stack's PC command / fault chain (kept)
Removed (superseded credit write / landing, 0db): ctrl strips (qkd_ctrl / _n), qkd_cdc_wleaf x128, the write queue
(qkd_kvwq_leaf_s_w129_m x128 + qkd_kvwq_ctl_bin x4), the landing strips (qkd_land / _n), the KVN context leaf (qkd_kvnc:
wprg drives the D2D end's kvn_compiled_*), the layer image (qkd_lprg: the join's boot-loaded layer programme).

The tiles are generated WIRES-ONLY parents (rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles.sv, written by
`kv_static_die.py --rtl`): children = the unchanged ROLES RTL with the join's parameters, internal nets = the join's
edges, ports = the edges that leave the tile (one port per distinct source slice), identity straps and clock entries as
ports.  Every replica of a tile kind elaborates the SAME module (checked).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

ON = os.environ.get('OT_KV_STATIC_DIE', '0') == '1'
# KV-DCAL-BOOTCFG 10-19 (= kv_die.DCAL_BC / DCAL_BC_LINK): the D2D end's cfg port <- dcal cfg; boot link_cfg_* -> dcal bcfg
DCAL_BC = os.environ.get('OT_KV_DCAL_BC', '0') == '1'
DCAL_BC_LINK = dict(cfg_tx_we='btx', cfg_rx_we='brx', cfg_addr='bad', cfg_data='bdt')
# KV-PLAN 10-17 (HANDOFF 0cx+4 decision 1): one control root per die half (kvs_hroot_N / kvs_hroot_S), each serving its
# own two stacks (es chain heads, fan words, group gathers, embedding return trains); off = the single top-centre root
HROOT = os.environ.get('OT_KV_HROOT', '0') == '1'
HROOT_RTL = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_half_root.sv'
# KV-PLAN2 10-17 (HANDOFF 0cx+5 decision 2, OT_KV_FANFOLD=1, needs OT_KV_HROOT=1): the stack fan is folded into its stack
# root.  The root's registered fan word feeds ONE 8-group neighbour chain from the root's end of the stack (slot 7 -> 0;
# every root sits at its stack's slot-7 end: S roots at the S|N seam, N roots above the N stacks), and the 18-b group
# gathers ride a concatenating neighbour chain back (slot 0 -> 7 -> root: o_ctl = {i_up[125:0], own}); the chain-end
# group (slot 0) is the variant qkd_kvs_grp_h without i_up (o_ctl = {8{own}}: the upper copies shift out before the
# root).  Done for all four stacks so the group / root replicas stay one master each.  Removes the stack-middle fan
# tile and its two 6-mm feeds (root -> fan 334 b, fan -> root 144 b) from the stack control channels.
FANFOLD = HROOT and os.environ.get('OT_KV_FANFOLD', '0') == '1'
# one generated tile file per design point (the ECTL frame pairing re-orders the fan's frame cfg words)
# KV-INTEG2 10-18: ONE kit design point OT_KV_TILE_KITS=1 (alias OT_KV_KVS_CK1=1; default off, so every existing design
# point and its tile file are unchanged; tile file suffix '_k').  Under it every kit tile takes ONE clock port per domain
# ('ck' core / 'hck' HBM) instead of one '<child>__ck' port per child (each child's entry already joined the same region
# trunk, _clocks_resets: clk_core_<r> / clk_hbm_<r>, so the die net is unchanged; the kit gets one CTS root beside its
# register mass), and every port sits on a fixed canonical face shared by the die frame and the kit:
#   KITS-A singletons kvs_ctl / kvs_attn / kvs_emb (CK1_KINDS, faces KVS_FACES): hard children with a CLOSED view
#     (KIT_HARD) are instantiated without #() when every parameter equals the RTL default (the cluster gate refuses
#     parameters on a hard child);
#   KITS-B replicated grp / grp_h / pc / pc_h / hroot (KIT_KINDS, faces KIT_FACE): FLAT leaf kits (kit_clocks).
KITS = os.environ.get('OT_KV_TILE_KITS', os.environ.get('OT_KV_KVS_CK1', '0')) == '1'
# Stage 1 private ABI pruning only; no physical/register or schedule adoption.
GRP_PRIVATE0 = os.environ.get('OT_KV_GRP_PRIVATE0', '0') == '1'
if GRP_PRIVATE0 and not (ON and HROOT and FANFOLD and KITS and
        os.environ.get('OT_KV_MU', '0') == '1' and os.environ.get('OT_KV_BOOT_AGES', '0') == '1' and
        os.environ.get('OT_KV_DOMSPLIT', '0') != '1'):
    raise ValueError('GRP_PRIVATE0 requires selected static HROOT/FANFOLD/KITS/MU/BOOT_AGES without DOMSPLIT')
KVS_CK1 = KITS
CK1_KINDS = ('ctl', 'attn', 'emb')
KIT_HARD = ('qkd_embedding_row_tx',)
KIT_KINDS = ('grp', 'grp_h', 'pc', 'pc_h', 'hroot')
# KV-DOMSPLIT 10-19 (OT_KV_DOMSPLIT=1; default off: every existing design point and tile file is
# unchanged; tile file suffix '_ds'): no die word mixes the core clock ck and the HBM clock hck.  The group <-> PC bundles
# (slg o_pc<j> -> kvpc i_grp, kvpc o_grp -> slg i_pc<j>) are split per launch domain: the ck fields keep the port name, the
# hck fields ride '<port>_h' (its own die bus, so its relay chain runs on the clk_hbm_<region> trunk: kv_die.py relay
# clock = the launching pin's domain).  The group gather o_ctl (-> the stack root, a ck-only relay tile, -> kvs_ctl boot /
# ownership observers) keeps one ck word: its 10 hck status levels (the five boot CDCs' applied_hbm / fault_hbm, sticky)
# LAND inside the group (qkd_kv_lvl_land: 2-flop async_reg synchroniser on ck, +2 ck edges on the boot observation; the
# observer's own 2-flop stage stays).  Field domains: the measured per-bit launch domains of the base tiles
# (kvs_port_domains bit_domains -> DOMSPLIT_TABLE, `kv_static_die.py --domsplit-table`), fail closed on a field without one.
DOMSPLIT = os.environ.get('OT_KV_DOMSPLIT', '0') == '1'
DOMSPLIT_DIR = 'results/arch/qwen_kv_domsplit_1019'
DOMSPLIT_TABLE = DOMSPLIT_DIR + '/producer_domains.json'
LVL_LAND_RTL = 'rtl/qwen_sys/static_kv_20261014/qkd_kv_lvl_land.sv'
PUBLIC_RTL_FILE = ('rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles' + ('_hroot' if HROOT else '') + ('_ff' if FANFOLD else '') +
            ('_ep' if os.environ.get('OT_KV_ECTL_PAIR', '0') == '1' else '') + ('_k' if KITS else '') +
            ('_mu' if os.environ.get('OT_KV_MU', '0') == '1' else '') +
            ('_ba' if os.environ.get('OT_KV_BOOT_AGES', '0') == '1' else '') +   # MU-ADOPT-KV 10-19 (kv_static.MU); KV-BOOTAGE
            ('_ds' if DOMSPLIT else '') + '.sv')   # KV-DOMSPLIT
RTL_FILE = PUBLIC_RTL_FILE[:-3] + ('_gp0' if GRP_PRIVATE0 else '') + '.sv'
GRP_PRIVATE0_RTL = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_private0.sv'
AGES = 'results/arch/qwen_kv_static_programme_1017/die_ages.json'
STACKS = ('WS', 'WN', 'ES', 'EN')
ORDER = (4, 5, 0, 1, 2, 3, 6, 7)          # kv_static.template: group g holds PCs 4 * ORDER.index(g) + q


def ectl_pair():
    """KV-PLAN-ECTL 10-17 (coordinator decision 2): OT_KV_ECTL_PAIR=1 (default off; read at call time)."""
    return os.environ.get('OT_KV_ECTL_PAIR', '0') == '1'


def ectl_frame(g):
    """physical ECTL frame (kv_die ectl_<st>_<f>: column f // 4, 0 = landing side; row f % 4 along the stack) that hosts
    logical engine g = ECTL A ectl_a_<st>_<g> + K issuer ki_<st>_<g> (residue g: K rows t[2:0] = g live in landing group
    g; astk port e<g>i / e<g>o / f<g><h> carries the hard strap sq = {stack, g}).

    Default: frame g (row g % 4 holds engines {r, r + 4}; group g sits at strip slot ORDER.index(g), so the row-pair of
    groups is the V-port pair {2k, 2k + 1} and 16 of 32 K links cross 2.4-5.6 mm).
    OT_KV_ECTL_PAIR=1: engine g moves to the frame LEVEL with its group: row = ORDER.index(g) // 2 (the group's slot pair,
    i.e. its V-port pair), column = ORDER.index(g) % 2 (= g % 2: the astk's own leaf column of engine g, astk_plan
    eng = 2 r + c).  Logical graph, cfg values (diecfg ectl_a_cfg[5 (8 s + g)]), K / V layouts, astk / hub / PV order are
    unchanged: only which hardened frame (and its four heads) runs engine g, and the die wires frame <-> astk port g."""
    if not ectl_pair():
        return g
    s = ORDER.index(g)
    return 4 * (s % 2) + s // 2


def frame_engine(f):
    """inverse of ectl_frame: the logical engine / landing group run by physical frame f"""
    for g in range(8):
        if ectl_frame(g) == f:
            return g
    raise ValueError(f'no engine for ECTL frame {f}')
PC_PITCH = 378.0
NPC = 32
CORE_CK = ('ck', 'return_ck')
HBM_CK = ('hck', 'pll_hbm', 'pll_hbm_port', 'pll_hbm_ecc', 'pll_hbm_cdc', 'pll_hbm_obs', 'cal_hck', 'front_hck', 'return_hck')
RESETS = ('rst_n', 'rsi', 'hrst_n', 'hrst', 'cal_rst_n')
HBM_RST = ('hrst_n', 'hrst', 'cal_rst_n')
KIND_MASTER = dict(fan='qkd_kvs_fan', grp='qkd_kvs_grp', grp_h='qkd_kvs_grp_h', pc='qkd_kvs_pc', pc_h='qkd_kvs_pc_h', ctl='qkd_kvs_ctl', attn='qkd_kvs_attn',
                   emb='qkd_kvs_emb', hroot='qkd_kvs_hroot')
if GRP_PRIVATE0:
    KIND_MASTER.update(grp='qkd_kvs_grp_private0', grp_h='qkd_kvs_grp_h_private0')
GEN_KINDS = tuple(KIND_MASTER)
CTL_LOCAL = dict(layer_programme='lprg', wprg='wprg', wrn='wrn', ownership='own', own_obs='oobs', boot='boot',
                 boot_obs='bobs', diecfg='dcfg')
GRP_LOCAL = dict(slg='slg', lcal='lcal', fcal='fcal', phase='phase', drain='drain')
# superseded die instances (0db) by name prefix
SUPERSEDED = ('ctrl_', 'cdc_', 'land_', 'wctl_', 'wleaf_', 'kvnc', 'lprg')
# KV-PLAN-FIN 10-17 (OT_KV_PVFIN, default ON with OT_KV_STATIC_DIE): the PV final join as ONE 512-b beat-stream slice
# qkd_pv_fin_s (die element pvfin, master qkd_pvfin, kit physical/ref_tile/qkd_pv_fin_s), W of the attention hub between
# the two PV pair strips; it feeds the stream face qkd_attn_result_face_s in kvs_attn (bundle port fin, 534 b).  Plan:
# results/arch/qwen_kv_pvfin_1017/plan.json (why not the 16,384-b ot_qwen_tp8_pv256_finalize_static_cal: 32 staggered
# column ages + 2 x 16 kb star).
import kv_static_attn_join as _AJ   # noqa: E402
PVFIN = ON and _AJ.STREAM
# KV-RTRUNK 10-17: the PV pairs carry the result trunks (kv_die.PV_RS: pair port bundle pr) -> pvfin.p0 / p1 are wired
RS_PAIRS = PVFIN and os.environ.get('OT_KV_PV_T', '0') == '1' and 'result_trunk' in json.loads(
    (Path(__file__).resolve().parents[2] / 'results/arch/qwen_kv_die/pv_trunk_t/plan.json').read_text())
# RTL-BUILD-KV/FAULT 10-18 (lanes/RTL-BUILD-KV.md P7; OT_KV_AFAULT, default ON with the static die + PVFIN + FANFOLD): the
# attention service-unit fault tree that drives attn_face.unit_fault (10 b) -- a REGISTERED NEIGHBOUR tree, fixed latency,
# no ready / credit:
#   af_<st>_<g>  x32  qkd_kv_cfault_node in each landing group tile (slg): fault_in = {up, vport f, ECTL kiss kf}; the K
#                     issuer of engine g (ectl_<st>_<ectl_frame(g)>.kf, the group's own K link partner) and the V port of
#                     the group pair (vport_<st>_<g // 2>.f, forked to both groups) are local; up = the node of the group
#                     one strip slot below (slot s - 1 -> s, the FANFOLD up-gather direction); the chain-end group (slot
#                     0, qkd_kvs_grp_h) has R = 2 {vport f, kf}; slot 7's node -> kvs_attn ufk_<st>
#   afr          x1   qkd_attn_fault_root in kvs_attn: pin register of the 8 direct lanes (astk af x4 and ahub hf = forks
#                     of the existing af_<st> / hf buses to the sequencer, pvw_0/1 pf fault, pvfin ff) + the two chain
#                     pairs (W = WS | WN, E = ES | EN) -> attn_face.unit_fault
# Latency per leaf = registered node edges + die relay stages of its buses (record()['attn_fault'], compiler-priced).
AFAULT = PVFIN and FANFOLD and os.environ.get('OT_KV_AFAULT', '1') == '1'
AFAULT_NODE = ('rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv', 'qkd_kv_cfault_node')
AFAULT_ROOT = ('rtl/qwen_sys/static_kv_die_20261017/qkd_attn_fault_root.sv', 'qkd_attn_fault_root')
# afr d lanes (LSB first) = (tile port, die source); c lanes = the stack chain ends
AFAULT_D = [('ufs_WS', ('astk_WS', 'af')), ('ufs_WN', ('astk_WN', 'af')), ('ufs_ES', ('astk_ES', 'af')),
            ('ufs_EN', ('astk_EN', 'af')), ('ufh', ('ahub', 'hf')), ('ufp0', ('pvw_0', 'pf')), ('ufp1', ('pvw_1', 'pf')),
            ('uff', ('pvfin', 'ff'))]
AFAULT_C = [f'ufk_{st}' for st in ('WS', 'WN', 'ES', 'EN')]
# KV-DCAL 10-19 (OT_KV_DCAL_FLT=1, needs OT_KV_DCAL_BC=1 + OT_KV_DCAL_BC4=1 + AFAULT; default off): the KV calendar
# sequencer's sticky fault (qkd_d2d_cal_seq_pin_bc4 `fault` = sequencer | COL | RUN | STALE | EARLY, registered, cleared only
# by the tile reset) becomes afr lane d[8] `ufd` on its own relayed kv_oneway bus ks_af_ufd (dcal flt -> kvs_attn ufd):
# afr ND 9, attn_face NF 11, folded into service_fault like every other unit fault (continuous sticky OR, no gating at
# cutoff).  Its latency is priced by record()['attn_fault'] (leaf 'dcal.flt').  STATUS contract owner: KV-RETIRE.
DCAL_FLT = (AFAULT and DCAL_BC and os.environ.get('OT_KV_DCAL_BC4', '0') == '1'
            and os.environ.get('OT_KV_DCAL_FLT', '0') == '1')
if DCAL_FLT:
    AFAULT_D = AFAULT_D + [('ufd', ('dcal', 'flt'))]
PVFIN_FILE = 'rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv'
PVFIN_FRAME = (259.2, 259.2)            # kit qkd_pv_fin_s outline (gate pending)
# KV-INTEG/AHUB 10-18 (RTL-BUILD-KV M2 + P6; OT_KV_AHUB_STATIC, default ON with PVFIN): the die hub `ahub` (master
# qkd_ahub) binds the STATIC six-root hub element qkd_ahub_static_dw (rtl/hdc/nearhbm/qkd_ahub_static_dw.sv = the sealed
# ot_qkd_ahub_static_die_cal of the qualified native service + the registered leaf qkd_ahub_static_io), NOT the legacy
# hub_p / ot_qkd_ahub_die (whose P.V half needs pi_* = 2,084 input bits no static producer drives, and whose reciprocals
# leave only through pl_rz per P.V beat).  Die buses: ks_ahs kvs_attn ahs -> ahub hs (attention root {start_qk, ep,
# layer, ctx, cal[127:16], cal[175:160]}), ap_<st> 43 b (the static ASTK hub word, strip_er_st ap[42:0]), am_<st> 36 b,
# ks_ahfr ahub fr -> pvfin fr (145 b {rz 4 x 32, rz_epoch, rz_valid}, one edge a pass on pvfin's R slot), hf; ONE clock
# entry ck_c.  Removed: hs (seq -> hub: the hub starts on the attention command) and ares (hub ao -> seq ar: the static
# hub has no result face; results leave pvfin -> kvs_attn fin).  Plan-priced parameters: ahub_ages() (record).
AHUB_STATIC = PVFIN and os.environ.get('OT_KV_AHUB_STATIC', '1') == '1'
AHUB_FILE = 'rtl/hdc/nearhbm/qkd_ahub_static_dw.sv'
AHS = ['start_qk', 'ep', 'layer', 'ctx', 'cal[127:16]', 'cal[175:160]']      # kvs_attn ahs = ahub hs (165 b, LSB first)
AHS_W, AHUB_AP_W, AHUB_FR_W = 165, 43, 145
# KV-WIRE2 10-18 (RTL-BUILD-KV/BOOT, results/arch/qwen_kv_boot_path_1018/note.md s5; OT_KV_BOOT, default ON with the
# static die + HROOT): the HOST slice runs IN PARALLEL as the boot owner.  Gateway embgw -> qkd_embgw_boot_s (emf / emr gone;
# new boot word bw 293 b -> kvs_ctl fan root qkd_kv_es_fan_root2_b), es edge word h 783 -> 784 (stack roots
# qkd_kv_es_fan_stack_b), PC chain 779 -> 780, pc_path -> qkd_static_kv_pc_path_fan_nc_b (es merge _b: third source = the
# slice ctrl_es in the boot window; chain station _b: boot word -> slice land_es).  Per PC die words to its HOST slice:
# les (pc land_es -> hsl land_es), hler (hsl land_er -> pc land_er), hes (hsl ctrl_es -> pc hes), ler (pc her -> hsl
# ctrl_er), hcv / hcw (pc hcompletion_* -> hsl ctrl_completion_*); slice lpc strap = k (the kvpc pc strap, note s5.7).
# Runtime paths unchanged (0 edges); boot-path ages = record (note s3 pricing, compiler).
BOOT = ON and HROOT and os.environ.get('OT_KV_BOOT', '1') == '1'
BOOT_RTL = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_half_root_b.sv'
_E = 'rtl/qwen_sys/static_embedding_20261014/'
BOOT_GW = (_E + 'qkd_embgw_boot_s.sv', 'qkd_embgw_boot_s', dict(BD=4, GAP=1, HOLD=64, ROW0=24427, MUT=0))
BOOT_PC = (_E + 'qkd_static_kv_pc_path_fan_nc_b.sv', 'qkd_static_kv_pc_path_fan_nc_b')
BOOT_PC_DEPS = [_E + 'qkd_static_kv_pc_es_merge_b.sv', _E + 'qkd_kv_pc_chain_station_b.sv']
BOOT_HW, BOOT_CW, BOOT_BW = 784, 780, 293
# (pc tile port, hsl port, width, direction pc -> hsl?) of the per-PC boot-owner words (note s5.6)
BOOT_HSL = [('les', 'pc__land_es', 'land_es', 288, True), ('hler', 'pc__land_er', 'land_er', 261, False),
            ('hes', 'pc__hes', 'ctrl_es', 288, False), ('ler', 'pc__her', 'ctrl_er', 261, True),
            ('hcv', 'pc__hcompletion_v', 'ctrl_completion_v', 1, True),
            ('hcw', 'pc__hcompletion_we', 'ctrl_completion_we', 1, True)]
# KV-WIRE2 10-18 (RTL-BUILD-KV/SEQ, lanes/RTL-BUILD-KV.md SEQ; OT_KV_SEQ_S, default ON with the static hub + OT_KV_SEQ_STATIC):
# the die slot `seq` binds qkd_seq_static_s (closed leaves qkd_seq_core_st_s / qkd_seq_xs_s / qkd_seq_fan_s): no kvn_<q>
# rows, no kvn_<q>_cr / mf_<q> (their die edges go with the landing strips), no att_rx / kvn_word_data.  New inputs:
#   prg (537 b) = kvs_attn's attention programme {request_valid, request_position, q_valid, q_beat, q_data} (LSB first),
#   ar  (8 b)   = ar_h {valid, g, beat 6} = the pvfin result stream header (kvs_attn fin: out_valid, out_beat; g = 0 and
#                 beat[5] = 0: one result stream of 32 beats on the static die), exported by kvs_attn,
#   skw (12 b)  = the d2d end's {kvn_word_valid, kvn_word_tag} (its own bundle; srx keeps att_rx_* for kvs_attn).
SEQ_S = AHUB_STATIC and os.environ.get('OT_KV_SEQ_STATIC', '0') == '1' and os.environ.get('OT_KV_SEQ_S', '1') == '1'
SEQ_S_FILE = 'rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv'
PRG = ['request_valid', 'request_position', 'q_valid', 'q_beat', 'q_data']        # kvs_attn prg = seq prg_* (537 b)
PRG_W, ARH_W = 537, 8
# KV-ATTNKIT 10-18 (OT_KV_ATTN_LAND=1, default off until the die lane prices it): the attention control tile kvs_attn
# with a registered boundary (kit qkd_kvs_attn-g1-7834bbc26 EARLY_FAIL_SETUP TT -480.8 ps: logic between the d2d rx pins
# and the first flops, fault-gated outputs, a pin-to-pin arh feed-through).  attention_programme LAND=1 (landed RX
# codec, no added RX edge; TX launch flops), attn_root / attn_face CAL_PIPE=1 (exact), prg <- the programme's launched
# prg_l, arh <- the face's registered hdr_l.  ADDED EDGES (compiler, like one more relay stage on the bundle):
# K.tx_record +1 (attn__tx_valid / attn__tx_payload), ks_prg +1, ks_arh +1; RX bundles K.rx_record / K.tx_slot +0.
ATTN_LAND = os.environ.get('OT_KV_ATTN_LAND', '0') == '1'
ATTN_LAND_EDGES = {'K.tx_record': 1, 'ks_prg': 1, 'ks_arh': 1, 'K.rx_record': 0, 'K.tx_slot': 0}
# HKV-RSTCAP 10-19 (lanes/HKV-RSTCAP.md): face-landed tile wrappers <kit>_fl (reset_ports landed at the face: +3 reset-release
# edges, tile clock; zero steady-state cycles) and, on kvs_attn, fin (pvfin stream) / i_ctl (ctl -> attn issue / run / cal go /
# authority) landed at +1 edge each.  OT_KV_FACE_LAND=1 binds the _fl views (ONLY once CLOSED) and the compiler takes the
# edges (kv_static_programme profile die: att += i_ctl; F_DLY += fin; startup: reset release + 3 per landed tile);
# kv_static_params FAILS when the die.v masters and this flag disagree.
# HKV-DIE3 10-19: PER-TILE selection.  OT_KV_FACE_LAND = 0 (none) | 1 (every tile below) | comma list of tile keys
# (production kvs14r: astk_rly_296 -- the only CLOSED _fl view, qkd_astk_rly_296-fl1-bd369b99e).  A selected tile binds
# its <master>_fl view, which must be CLOSED (face_land_require_closed fails closed on a missing view); the compiler takes
# the edges of the selected tiles only (kv_static_programme._face_land) and kv_static_params checks die.v per tile.
FACE_LAND_TILES = {'kvs_attn': dict(master='qkd_kvs_attn', kit='qkd_kvs_attn', rst_release=3, fin=1, i_ctl=1),
                   # KV-BIND3 10-19: rc1 view (qkd_astk_rly_296-rc1-1b6976095, 10 KEPT reset relay copies): reset release =
                   # flow reset_landing 2 stages + ot_rst_relay SYNC 2 + TREE 1 = 5 edges (startup calendar; COORD 18:16).
                   'astk_rly_296': dict(master='qkd_astk_rly_296', kit='qkd_astk_rly_296', rst_release=5),
                   'hr_core_queue': dict(master='qkd_hr_core_queue', kit='qkd_hr_core_queue', rst_release=3)}
if os.environ.get('OT_KV_BOOT_AGES', '0') == '1':     # KV-BOOTAGE 10-19: the boot-age attention tile's landed view
    FACE_LAND_TILES['kvs_attn'] = dict(FACE_LAND_TILES['kvs_attn'], kit='qkd_kvs_attn_ba1')
_FL_ENV = os.environ.get('OT_KV_FACE_LAND', '0').strip()
FACE_LAND_SEL = (set(FACE_LAND_TILES) if _FL_ENV == '1' else set() if _FL_ENV in ('', '0')
                 else {t.strip() for t in _FL_ENV.split(',') if t.strip()})
if FACE_LAND_SEL - set(FACE_LAND_TILES):
    raise ValueError(f'kv_static_die: OT_KV_FACE_LAND names unknown tiles {sorted(FACE_LAND_SEL - set(FACE_LAND_TILES))}')
FACE_LAND = bool(FACE_LAND_SEL)


def face_land_view(tile):
    t = FACE_LAND_TILES[tile]
    return f"physical/ref_tile/{t['kit']}/views/{t['master']}_fl"


def face_land_require_closed(root=ROOT):
    """every selected tile's <master>_fl view must exist (closure record: LEF + TT/FF libs + insertion.json)"""
    miss = {}
    for tl in sorted(FACE_LAND_SEL):
        vd = Path(root) / face_land_view(tl)
        m = FACE_LAND_TILES[tl]['master'] + '_fl'
        need = [vd / f'{m}.lef', vd / f'{m}_tt.lib', vd / f'{m}_ff.lib', vd / 'insertion.json']
        bad = [str(p.relative_to(root)) for p in need if not p.exists()]
        if bad:
            miss[tl] = bad
    if miss:
        raise ValueError(f'kv_static_die: face-landed tiles selected without a CLOSED _fl view (bind only CLOSED): {miss}')
    return {tl: face_land_view(tl) for tl in sorted(FACE_LAND_SEL)}
FACE_LAND_RST_BUDGET = 128 - 2     # region roots hold reset >= RELAY_FLUSH 128 cycles after the clock runs (kv_rst_window), E_r 2
# KV-WIRE2 10-18 (RTL-BUILD-KV/ASTK (a)-(d), lanes/RTL-BUILD-KV.md ASTK; OT_KV_ASTK_ST, default ON with the static hub): the
# static ASTK strip with its inline e-read (die face qkd_astk_strip_er_die = qkd_astk_strip_er_st + the vh -> read request
# slicing + af | er_fault), the ECTL frames on qkd_ectl3_kiss_st (C = qkd_ectl_c_st: so 413 b, si 633 b, no nb_cr), heads
# ot_qkh_head_native_r4_s / _ft_s (no node beat nb_d: the 32 x 4 nb_<st>_<e>_<h> die words and the ck_a* / ck_b* clock
# entries go).  New die words: ks_acal_<st> (kvs_attn acal = attn_root cal {EXP, Z, LMAX} 48 b -> astk_<st>.cal, one word a
# stack), the e-read requests = relayed fork branches of pvh_<st>_<k> -> astk_<st>.vh<k>, pve_<st> (astk erd 256 b -> the
# stack's PV pair in_e lanes: W stacks pvw_<p>.ie = in_e[255:0], E stacks .iee = in_e[511:256]).  ASTK_W re-cut: not done
# (the frame keeps 220.32 um; the P.V tree columns are gone, so the strip has slack -- follow-up with its kit).
ASTK_ST = AHUB_STATIC and os.environ.get('OT_KV_ASTK_ST', '1') == '1'
# Owner-selected physical strip successor: parameters and read ages must move together.
# Legacy/default sources keep their existing one-edge internal links and centralized e-read.
ASTK_EXPAND = ASTK_ST and os.environ.get('OT_KV_ASTK_EXPAND', '1') == '1'   # HKV-DIE3 10-19: production default ON
ASTK_RL = int(os.environ.get('OT_KV_ASTK_RL', '3' if ASTK_EXPAND else '1'))
ASTK_Z_STRIDE = 4     # actual CLOSED qkd_astk_ctl_s parameter; stride-16 benches are separate evidence
if ASTK_RL < 1 or (not ASTK_EXPAND and ASTK_RL != 1):
    raise ValueError('kv_static_die: ASTK RL changes require OT_KV_ASTK_EXPAND=1 and positive RTL link latency')
ASTK_FILE = 'rtl/qwen_sys/split_20261014/qkd_astk_strip_er_die.sv'
ACAL = ['cal[31:16]', 'cal[47:32]', 'cal[15:0]']            # astk cal = {EXP base, Z start, LMAX start} (LSB first: LMAX)
ECTL_ST_FILE = 'rtl/qwen_sys/static_kv_20261014/qkd_static_ectl_st.sv'
# KV-ECTL4 2026-10-18 (coordinator 0gs (d)): ONE K round trip for all 32 ECTL frames.  The hardened children of
# qkd_ectl3_kiss_st (A qkd_static_ectla_kiss: K issuer ident line RESPONSE_LAT deep; A / B / C: ROW_RETURN_LAT =
# RESPONSE_LAT + 7 return-slot lines, read slot at QK_ISSUE_AGE - 2) carry these as RTL parameters, so the die cannot bind a
# per-frame value: kv_k_rt_eq.py pads every frame's K REQUEST chain (38 b, krq) so 8 (landing seg) + krq + krs stages ==
# ECTLK_RESPONSE_LAT exactly, and the GEN fails when a frame's natural round trip exceeds it.  QK_ISSUE_AGE follows the
# static_qk_calendar write-before-read rule (kv_static_ages.QK_WRITE_BEFORE_READ = 11): QK_ISSUE_AGE = RESPONSE_LAT + 11.
# Budget 80: kvs14q-8503e0c89 (648 x 129.6 ECTL slots) measured 8 + krq + krs = 12..70 (worst ES_6 / WS_6); the
# 725.76 x 261.36 frame adds 131.76 um a row engine; the 10-stage margin keeps the hardened children valid across plan
# iterations (padding absorbs the rest).  Cost: D_QK 57 vs 28 edges a layer (~0.4 % of the token period).
import kv_static_ages as _AGES   # noqa: E402
ECTLK_RESPONSE_LAT = _AGES.K_RT_BUDGET
ECTLK_QK_ISSUE_AGE = ECTLK_RESPONSE_LAT + _AGES.QK_WRITE_BEFORE_READ
ECTLK_ROW_RETURN_LAT = ECTLK_RESPONSE_LAT + 7
# KVR-DERIVE 10-19 (coordinator decision): the static-schedule ages HARD-CODED in closed tiles.  This die binds exactly
# these values; the generator pads a faster path up to the value where that is legal (core-clock pad relays) and
# kv_static_params FAILS every path whose relay-plan age differs (never a mismatch bound; a path already longer than the
# value needs the ONE later re-harden: boot-programmable static-schedule registers, spec in lanes/KVR-DERIVE.md).
#   ECTL_RESPONSE_LAT  qkd_ectl3_kiss_st children (rt80 kit)        8 + krq + krs                 (kv_k_rt_eq pads krq)
#   VPORT_RT           qkd_pv16_vport kit (r6: RT 8)                 9 + pvvq_g + pvrs_g, both sides (pads: pvvq, 15 b)
#   PV_FIRST_INPUT_AGE ot_qwen_tp8_pv_wide_ctl_t kit (OT_KV_PV_T_CTL_KIT spec)   4 + W + DQ + RT_die + 1, all 16 ports
#   PV_LEAD / F_DLY    qkd_kvs_attn (generated tile text: attn_root / attn_face join parameters)
#                      PV_LEAD = D(ks_pvst) to pvw_0 and pvw_1; F_DLY = 1 + (D(ks_pvfst) - PV_LEAD) + D(ks_pvfin) [+ face land]
VPORT_KIT = os.environ.get('OT_KV_VPORT_KIT', 'physical/ref_tile/qkd_pv16_vport_r6/spec.json')
VPORT_RT_SEG = 9          # landing seg vreq capture 1 + VREQ latency 8 (KVJ-F tb_static_landing_vport)
LANDING_SEG = 8           # K request -> response latency of the landing seg


def _kit_params(rel):
    """a kit spec's params from the worktree, else from git HEAD (sparse checkouts); None when absent"""
    f = ROOT / rel
    try:
        txt = f.read_text() if f.exists() else __import__('subprocess').run(
            ['git', '-C', str(ROOT), 'show', f'HEAD:{rel}'], capture_output=True, text=True, check=True).stdout
        return json.loads(txt).get('params') or {}
    except Exception:              # noqa: BLE001
        return None


def tile_ages():
    """the hard-coded tile ages this die binds (+ where each comes from)"""
    vk = _kit_params(VPORT_KIT) or {}
    ck = os.environ.get('OT_KV_PV_T_CTL_KIT', 'qkd_pv_ctl_t_d54f58a95')
    cp = _kit_params(f'physical/ref_tile/{ck}/spec.json') or {}
    at = attn_tile_params()
    return dict(ECTL_RESPONSE_LAT=ECTLK_RESPONSE_LAT, ECTL_QK_ISSUE_AGE=ECTLK_QK_ISSUE_AGE,
                VPORT_RT=int(vk.get('RT', 8)), VPORT_DQ=int(vk.get('DQ', 0)),
                PV_FIRST_INPUT_AGE=int(cp['FIRST_INPUT_AGE']) if 'FIRST_INPUT_AGE' in cp else None,
                PV_LEAD=at.get('PV_LEAD'), F_DLY=at.get('F_DLY'),
                source=dict(ECTL='kv_static_ages.K_RT_BUDGET (qkd_ectl3_kiss_st rt80 children)', VPORT=VPORT_KIT,
                            PV_CTL=f'physical/ref_tile/{ck}/spec.json', ATTN=f'{RTL_FILE} module qkd_kvs_attn'))


def attn_tile_params(text=None):
    """PV_LEAD / F_DLY as the generated qkd_kvs_attn tile binds them (the tile text; the closed kit is that text)"""
    if text is None:
        p = ROOT / RTL_FILE
        if not p.exists():
            return {}
        text = p.read_text()
    m = re.search(r'module\s+qkd_kvs_attn\b(.*?)endmodule', text, re.S)
    if not m:
        return {}
    out = {}
    for k, mod in (('PV_LEAD', 'qkd_attn_service_root'), ('F_DLY', 'qkd_attn_result_face_s')):
        mm = re.search(mod + r'\s*#\s*\((.*?)\)\s*\w+\s*\(', m.group(1), re.S)
        v = re.search(r'\.' + k + r'\((\d+)\)', mm.group(1)) if mm else None
        if v:
            out[k] = int(v.group(1))
    return out


FIN = [('out_valid', 1), ('out_beat', 5), ('out_epoch', 16), ('out_data', 512)]    # pvfin fo = kvs_attn fin (LSB first)
PVFST = ['start_pv', 'ep', 'cal[175:128]']                                        # kvs_attn pvfst = pvfin fs (65 b)
# per-tile frames (um, ASSUMED until kits close): see place()
FRAME = dict(fan=(302.4, 302.4), attn=(302.4, 302.4), emb=(388.8, 302.4), ctl=(1123.2, 172.8), hroot=(302.4, 302.4))
# Special bundles (die-port order = the existing master's binding order, LSB first)
VREQ = [('vreq_valid', 1), ('vreq_t', 14)]                                         # qkd_pv16_vport vq<p>
RSP = ['rsp_valid', 'rsp_v', 'rsp_t', 'rsp_epoch', 'rsp_data']                    # qkd_pv16_vport i<p> (R6)
KREQ = [('req_valid', 1), ('req_t', 14), ('req_v', 1), ('req_epoch', 16), ('req_layer', 6)]   # qkd_ectlk rq
KRSP = ['rsp_valid', 'rsp_data', 'rsp_t', 'rsp_v', 'rsp_epoch', 'rsp_layer']        # qkd_ectlk rs
KG = ['kgo', 'epoch', 'layer']                                                     # qkd_ectlk kg (from the layer programme)
LP = ['attention_run', 'layer', 'ctx_t']                                           # qkd_seq_static lp
KVI = ['compiled_identity', 'compiled_generation']                                  # qkd_d2d_static kvi
D2D_LISTS = None                     # (D2DS_SVC, SEQST_RX, SEQST_KW), set by kv_die before bindings()

_G = {}


def graph():
    """the merged static join with the priced ages (cached per process)"""
    if 'g' not in _G:
        import kv_static_attn_join as AJ      # KVJ-G2b: kvjf build + attention service root / result face + cal_gen
        import kv_static_ages as A
        g, _ = AJ.build()
        ages = json.loads((ROOT / AGES).read_text())
        left = A.apply(g, ages)
        if HROOT:
            _hroot_join(g)
        if BOOT:
            _boot_join(g)
        if AFAULT:
            _afault_join(g)
        if ATTN_LAND:
            _attn_land_join(g)
        import kv_bootage as _KB              # KV-BOOTAGE 10-19 (OT_KV_BOOT_AGES=1): boot-programmable schedule ages
        if _KB.ON:
            _KB.boot_ages_join(g)
        _G['g'], _G['unpriced'] = g, left
        _G['ins'] = {i['name']: i for i in g['instances']}
        _G['spec'] = {}
    return _G['g']


def _attn_land_join(g):
    """KV-ATTNKIT (OT_KV_ATTN_LAND): registered kvs_attn boundary parameters (see ATTN_LAND)"""
    by = {i['name']: i for i in g['instances']}
    for name, k in (('attention_programme', 'LAND'), ('attn_root', 'CAL_PIPE'), ('attn_face', 'CAL_PIPE')):
        if name not in by:
            raise ValueError(f'kv_static_die ATTN_LAND: no instance {name}')
        by[name]['parameters'][k] = 1
    g.setdefault('joins_added', []).append(dict(producer='attention_programme LAND / attn_root, attn_face CAL_PIPE',
        bound_inputs=0, owner_note='KV-ATTNKIT 10-18: registered kvs_attn boundary; added edges ' + json.dumps(ATTN_LAND_EDGES)))


def _hroot_join(g):
    """the es fan root emits one unsteered edge word (qkd_kv_es_fan_root2.h); each stack root's qkd_kv_es_fan_stack
    holds its stack's chain head (one more register: exactly the single root's word one edge later)"""
    by = {i['name']: i for i in g['instances']}
    f = by['fanr']
    f.update(module='qkd_kv_es_fan_root2', source=HROOT_RTL, sha256=None)
    for k, st in enumerate(STACKS):                     # chain d<k>: WS 0, WN 1, ES 2, EN 3
        g['instances'].append(dict(name=f'esh_{st}', role='es_fan_stack', source=HROOT_RTL, module='qkd_kv_es_fan_stack',
                                   sha256=None, parameters={'MUT': 0},
                                   inputs={'ck': None, 'rst_n': None, 'stack': [{'strap': k, 'width': 2}],
                                           'h': [{'instance': 'fanr', 'port': 'h', 'lo': 0, 'width': 783}]}))
        it = by[f'pc_{st}_31']['inputs']['chain_i']
        if it != [{'instance': 'fanr', 'port': f'd{k}', 'lo': 0, 'width': 779}]:
            raise ValueError(f'kv_static_die HROOT: pc_{st}_31.chain_i is not fanr.d{k}: {it}')
        by[f'pc_{st}_31']['inputs']['chain_i'] = [{'instance': f'esh_{st}', 'port': 'd', 'lo': 0, 'width': 779}]


def _boot_join(g):
    """BOOT (note s5): successor modules of the gateway, the fan root, the stack roots and the 128 pc_paths; boot word
    embgw.bw -> fanr.bw; h 784, chain 780.  The pc_path's new slice-facing inputs (land_er, hes) are die joins."""
    by = {i['name']: i for i in g['instances']}
    f = by['fanr']
    if f['module'] != 'qkd_kv_es_fan_root2' or 'bw' in f['inputs']:
        raise ValueError(f'kv_static_die BOOT: fanr is {f["module"]}')
    f.update(module='qkd_kv_es_fan_root2_b', source=BOOT_RTL, sha256=None)
    f['inputs']['bw'] = [dict(instance='embgw', port='bw', lo=0, width=BOOT_BW)]
    gw = by['embgw']
    gw.update(source=BOOT_GW[0], module=BOOT_GW[1], sha256=None, parameters=dict(BOOT_GW[2]))
    for st in STACKS:
        e = by[f'esh_{st}']
        if e['inputs']['h'] != [{'instance': 'fanr', 'port': 'h', 'lo': 0, 'width': 783}]:
            raise ValueError(f'kv_static_die BOOT: esh_{st}.h is {e["inputs"]["h"]}')
        e.update(module='qkd_kv_es_fan_stack_b', source=BOOT_RTL, sha256=None)
        e['inputs']['h'] = [dict(instance='fanr', port='h', lo=0, width=BOOT_HW)]
    n = 0
    for i in g['instances']:
        if i['role'] != 'pc_path':
            continue
        ci = i['inputs']['chain_i']
        if len(ci) != 1 or ci[0]['width'] != 779 or ci[0]['lo'] != 0:
            raise ValueError(f'kv_static_die BOOT: {i["name"]}.chain_i is {ci}')
        i.update(source=BOOT_PC[0], module=BOOT_PC[1], sha256=None)
        i['inputs']['chain_i'] = [dict(ci[0], width=BOOT_CW)]
        for p in ('land_er', 'hes'):
            i['inputs'].setdefault(p, None)
        n += 1
    if n != 128:
        raise ValueError(f'kv_static_die BOOT: {n} pc_path instances')
    for path in [BOOT_RTL, BOOT_GW[0], BOOT_PC[0]] + BOOT_PC_DEPS:
        if not any(d['path'] == path for d in g['source_files']):
            g['source_files'].append(dict(path=path, sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest()))
    g['source_files'].sort(key=lambda d: d['path'])
    g.setdefault('joins_added', []).append(dict(producer='embgw.bw (qkd_embgw_boot_s) -> fanr.bw (qkd_kv_es_fan_root2_b)',
        bound_inputs=1, owner_note='RTL-BUILD-KV/BOOT 10-18 (note s5): boot owner = HOST slice in parallel; pc_path '
        'land_er / hes are die joins from the slice (kv_static_die._die_joins)'))


def _afault_join(g):
    """P7: the attention unit-fault tree nodes (their die-source inputs are tile ports bound by _die_joins; see AFAULT)"""
    import kv_static as K
    by = {i['name']: i for i in g['instances']}

    def add(name, src, params):
        sp = K.source(*src, K.ROOT)
        pp = K.ports(sp, params)
        if name in by:
            raise ValueError(f'kv_static_die AFAULT: instance {name} already present')
        i = dict(name=name, role='producer', source=src[0], module=src[1], sha256=sp['sha256'], parameters=dict(params),
                 inputs={p: None for p, v in pp.items() if v['direction'] == 'input'})
        g['instances'].append(i)
        by[name] = i
        if not any(d['path'] == src[0] for d in g['source_files']):
            g['source_files'].append(dict(path=src[0], sha256=hashlib.sha256((ROOT / src[0]).read_bytes()).hexdigest()))
            g['source_files'].sort(key=lambda d: d['path'])
        return i
    for st in STACKS:
        for s_, gg in enumerate(ORDER):
            add(f'af_{st}_{gg}', AFAULT_NODE, dict(R=2 if s_ == 0 else 3, STAGES=1, MUT=0))
    add('afr', AFAULT_ROOT, dict(ND=len(AFAULT_D), NC=len(AFAULT_C), MUT=0))
    face = by['attn_face']
    nf = face['parameters']['NF']
    if DCAL_FLT and nf == len(AFAULT_D) - 1 + len(AFAULT_C) // 2:     # KV-DCAL: + the calendar sequencer's fault lane
        nf = face['parameters']['NF'] = nf + 1
    if nf != len(AFAULT_D) + len(AFAULT_C) // 2 or face['inputs'].get('unit_fault', 0) is not None:
        raise ValueError(f'kv_static_die AFAULT: attn_face NF {nf} / unit_fault already bound')
    face['inputs']['unit_fault'] = [dict(instance='afr', port='unit_fault', lo=0, width=nf)]
    g.setdefault('joins_added', []).append(dict(producer='af_*:qkd_kv_cfault_node + afr:qkd_attn_fault_root',
        bound_inputs=1, owner_note='RTL-BUILD-KV/FAULT 10-18 (P7): attention unit-fault neighbour tree -> attn_face.unit_fault; '
        'node / root inputs are die joins (kv_static_die._die_joins)'))


def ins():
    graph()
    return _G['ins']


def spec(name):
    """{port: dict(direction, width)} of one join instance (parameters as joined; unpriced -> RTL default)"""
    import kv_static as K
    graph()
    if name not in _G['spec']:
        i = _G['ins'][name]
        s = K.source(i['source'], i['module'])
        par = {k: v for k, v in i['parameters'].items() if k in s['parameters']}
        par = {k: (1 if v is None else v) for k, v in par.items()}
        _G['spec'][name] = K.ports(s, par)
    return _G['spec'][name]


def pc_group():
    """(st, pc) -> group g"""
    return {(st, 4 * ORDER.index(g) + q): g for st in STACKS for g in range(8) for q in range(4)}


def cluster_of(name):
    """join instance -> (die instance, kind, local name)"""
    m = re.fullmatch(r'(pc|embr)_(WS|WN|ES|EN)_(\d+)', name)
    if m:
        k = int(m.group(3))
        return f'kvpc_{m.group(2)}_{k}', ('pc_h' if k == 0 else 'pc'), m.group(1)
    m = re.fullmatch(r'(slg|lcal|fcal|phase|drain)_(WS|WN|ES|EN)_(\d)', name)
    if m:
        return f'slg_{m.group(2)}_{m.group(3)}', 'grp', GRP_LOCAL[m.group(1)]
    m = re.fullmatch(r'bcdc_f_(WS|WN|ES|EN)_(\d)', name)
    if m:
        return f'slg_{m.group(1)}_{m.group(2)}', 'grp', 'bcdcf'
    m = re.fullmatch(r'bcdc_c_(WS|WN|ES|EN)_(\d+)', name)
    if m:
        pc = int(m.group(2))
        return f'slg_{m.group(1)}_{pc_group()[(m.group(1), pc)]}', 'grp', f'bcdc{pc % 4}'
    m = re.fullmatch(r'af_(WS|WN|ES|EN)_(\d)', name)        # P7 attention fault chain node: in its landing group
    if m:
        return f'slg_{m.group(1)}_{m.group(2)}', 'grp', 'af'
    if name == 'afr':
        return 'kvs_attn', 'attn', 'afr'
    m = re.fullmatch(r'cf1_(WS|WN|ES|EN)_(\d)', name)       # KVJ-SMALL cfault tree level 1: beside its group's PCs
    if m:
        return f'slg_{m.group(1)}_{m.group(2)}', 'grp', 'cf1'
    if re.fullmatch(r'cf2_(WS|WN|ES|EN)_\d|cf3_[WE]|cf_root', name) or name == 'fanr':
        return 'kvs_ctl', 'ctl', name      # upper cfault levels + the C3 es fan root: beside the HOST root / writer
    m = re.fullmatch(r'esh_(WS|WN|ES|EN)', name)
    if m:
        return f'kvs_hroot_{m.group(1)}', 'hroot', 'esh'
    if name in ('attn_root', 'attn_face', 'attn_cal'):
        return 'kvs_attn', 'attn', name
    m = re.fullmatch(r'(ectl_a|ki)_(WS|WN|ES|EN)_(\d)', name)
    if m:
        return f'ectl_{m.group(2)}_{ectl_frame(int(m.group(3)))}', 'ectl', 'a' if m.group(1) == 'ectl_a' else 'k'
    if name.startswith('vport_'):
        return name, 'vport', 'vport'
    if name == 'd2d':
        return 'd2d_kv', 'd2d', 'd2d'
    if name == 'embgw':
        return 'embgw', 'embgw', 'embgw'
    if name == 'attention_programme':
        return 'kvs_attn', 'attn', 'attn'
    if name in ('emb_join', 'emb_tx'):
        return 'kvs_emb', 'emb', 'join' if name == 'emb_join' else 'rowtx'
    if name in CTL_LOCAL:
        return 'kvs_ctl', 'ctl', CTL_LOCAL[name]
    raise ValueError(f'kv_static_die: no home for join instance {name}')


def members():
    """die instance -> [join instance names] (generated kinds only, fixed local order)"""
    out = defaultdict(list)
    for n in ins():
        d, kind, _ = cluster_of(n)
        if kind in GEN_KINDS:
            out[d].append(n)
    key = lambda n: (cluster_of(n)[2], n)          # noqa: E731
    return {d: sorted(v, key=key) for d, v in out.items()}


def kind_of(die_inst):
    if die_inst.startswith('kvpc_'):
        return 'pc_h' if die_inst.endswith('_0') else 'pc'
    if die_inst.startswith('slg_'):
        return 'grp'
    if die_inst.startswith('kvs_fan_'):  # noqa
        return 'fan'
    if die_inst.startswith('kvs_hroot_'):
        return 'hroot'
    return dict(kvs_ctl='ctl', kvs_attn='attn', kvs_emb='emb').get(die_inst)


def _d2d_bundles():
    """existing qkd_d2d_static die bundles that static consumers read: RTL port -> (bundle, lo, width)"""
    import kv_static as K
    if 'd2db' in _G:
        return _G['d2db']
    s = K.source('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'qkd_d2d_static')
    w = K.ports(s, {k: v for k, v in dict(MUT=0, NL=2, NTX=K.d2d_ntx_k(), PR=1, TXDP=K.d2d_txdp_k()).items() if k in s['parameters']})
    if D2D_LISTS is None:                # standalone (--rtl): kv_die defines the bundles (it does not import us back ON)
        import kv_die as _kd
        D2DS_SVC, SEQST_RX, SEQST_KW = _kd.D2DS_SVC, _kd.SEQST_RX, _kd.SEQST_KW
    else:
        D2DS_SVC, SEQST_RX, SEQST_KW = D2D_LISTS
    out = {}
    for b, lst in (('svc', D2DS_SVC), ('srx', SEQST_RX), ('skw', SEQST_KW)):
        lo = 0
        for p in lst:
            out[p] = (b, lo, w[p]['width'])
            lo += w[p]['width']
    out['_widths'] = {p: v['width'] for p, v in w.items()}
    _G['d2db'] = out
    return out


# ------------------------------------------------------------------------------------------------ tile interfaces
def tile(die_inst):
    """interface + body of one generated tile instance.
    ports: OrderedDict name -> dict(dir, width, cls, ...); cls in clock / reset / pad / strap / open / sig / special / export
    sig inputs carry key (src die inst, src port on that die inst) for die wiring; exports carry their consumers."""
    mem = members()[die_inst]
    kind = kind_of(die_inst)
    loc = {n: cluster_of(n)[2] for n in mem}
    I = ins()
    d2db = _d2d_bundles()
    ports = OrderedDict()
    body = []
    wires = []
    sig_in = {}            # (src join inst, port, lo, w) or ('d2d', bundle) / ... -> wrapper input port name

    def add_port(name, **kw):
        if name in ports:
            if ports[name]['width'] != kw['width'] or ports[name]['dir'] != kw['dir']:
                raise ValueError(f'{die_inst}: port {name} redefined')
            return name
        ports[name] = dict(kw)
        return name

    def term_of(n, p, k, it, nitems):
        """Verilog term for one join item of input n.p (index k)"""
        src = it.get('instance')
        lo, w = it.get('lo'), it.get('width')
        if 'strap' in it:
            pn = add_port(f'{loc[n]}__{p}', dir='input', width=w, cls='strap', value=it['strap'])
            return pn
        if src in loc:
            return f'w_{loc[src]}__{it["port"]}[{lo + w - 1}:{lo}]'
        sd, skind, sloc = cluster_of(src)
        if kind in ('pc', 'pc_h') and skind in ('d2d', 'embgw'):
            # PCs read the D2D RESULT / gateway status through their group (one long run per group, not per PC)
            nm, _up, _uw, ilo, iw, _expr = pc_pass(src, it['port'], lo, w)
            return add_port(f'x__{nm}', dir='input', width=iw, cls='pass', src=('PASS', nm))
        if skind == 'd2d':
            sp = it['port']
            if sp in d2db:                       # inside an existing die bundle: take the whole bundle, slice here
                b, blo, bw = d2db[sp]
                bwid = sum(v[2] for kk, v in d2db.items() if kk != '_widths' and v[0] == b)
                pn = add_port(f'd2d__{b}', dir='input', width=bwid, cls='sig', src=('d2d_kv', b))
                return f'{pn}[{blo + lo + w - 1}:{blo + lo}]'
            pn = add_port(f'd2d__{sp}', dir='input', width=d2db['_widths'][sp], cls='sig', src=('d2d_kv', sp))
            return f'{pn}[{lo + w - 1}:{lo}]'
        if skind == 'embgw':
            pn = add_port(f'embgw__{it["port"]}', dir='input', width=spec('embgw')[it['port']]['width'], cls='sig',
                          src=('embgw', it['port']))
            return f'{pn}[{lo + w - 1}:{lo}]'
        if skind == 'vport':                     # landing vreq_* <- V port vq<parity>_* (qkd_pv16_vport vq bundle)
            off = dict(vreq_valid=0, vreq_t=1)[p]
            pn = add_port('vreq', dir='input', width=15, cls='special', src=None)
            return f'vreq[{off + lo + w - 1}:{off + lo}]'
        if skind == 'ectl':                      # landing req_* <- the folded K issuer (qkd_ectlk rq bundle)
            off = 0
            for nm, wd in KREQ:
                if nm == it['port']:
                    break
                off += wd
            else:
                raise ValueError(f'{die_inst}: unknown K request field {it["port"]}')
            pn = add_port('kreq', dir='input', width=38, cls='special', src=None)
            return f'kreq[{off + lo + w - 1}:{off + lo}]'
        # another generated tile: one port per distinct source slice, named by its first consumer (replica-generic)
        key = (src, it['port'], lo, w)
        if key not in sig_in:
            sig_in[key] = add_port(f'{loc[n]}__{p}' + (f'__{k}' if nitems > 1 else ''), dir='input', width=w,
                                   cls='sig', src=key)
        return sig_in[key]

    # internal wires: every member output
    for n in mem:
        for p, v in spec(n).items():
            if v['direction'] == 'output':
                wires.append(f'    wire [{v["width"] - 1}:0] w_{loc[n]}__{p};')
    overrides = CTL_OVERRIDE if kind == 'ctl' else (ATTN_OVERRIDE if kind == 'attn' and PVFIN else {})
    if AFAULT and kind == 'attn':
        overrides = {**overrides, **AFAULT_OVERRIDE}
    if AFAULT and kind == 'grp':          # the chain node: slot 0 (R 2) has no up input
        r_ = next(I[n]['parameters']['R'] for n in mem if loc[n] == 'af')
        overrides = {**overrides, ('af', 'fault_in'): (([('afk', 1), ('afv', 1), ('afu', 1)], '{afu, afv, afk}') if r_ == 3
                                                            else ([('afk', 1), ('afv', 1)], '{afv, afk}'))}
    for n in mem:
        sp = spec(n)
        cs = []
        child_ck = [p for p in sp if p in CORE_CK + HBM_CK]
        hbm_only = child_ck and all(p in HBM_CK for p in child_ck)
        for p, v in sp.items():
            if v['direction'] == 'output':
                cs.append(f'.{p}(w_{loc[n]}__{p})')
                continue
            items = I[n]['inputs'].get(p)
            if (loc[n], p) in overrides:
                ov = overrides[(loc[n], p)]
                if len(ov) == 2:                         # several 1-port-per-source inputs, one expression
                    for pn, wd in ov[0]:
                        add_port(pn, dir='input', width=wd, cls='special', src=None)
                    expr = ov[1]
                else:
                    pn, wd, expr = ov
                    add_port(pn, dir='input', width=wd, cls='special', src=None)
                cs.append(f'.{p}({expr})')
                continue
            if items is None:
                if p in CORE_CK or p in HBM_CK:
                    ckn = (('hck' if p in HBM_CK else 'ck') if KVS_CK1 and kind in CK1_KINDS else f'{loc[n]}__{p}')
                    pn = add_port(ckn, dir='input', width=1, cls='clock', domain='hbm' if p in HBM_CK else 'core')
                elif p in RESETS:
                    dom = 'hbm' if (p in HBM_RST or (p == 'rst_n' and hbm_only)) else 'core'
                    pn = add_port('hrst_n' if dom == 'hbm' else 'rst_n', dir='input', width=1, cls='reset', domain=dom)
                elif p == 'por_n':
                    pn = add_port('por_n', dir='input', width=1, cls='pad')
                else:
                    pn = add_port(f'{loc[n]}__{p}', dir='input', width=v['width'], cls='open', owner=open_owner(n, p))
                cs.append(f'.{p}({pn})')
                continue
            terms = [term_of(n, p, k, it, len(items)) for k, it in enumerate(items)]
            cs.append(f'.{p}({terms[0] if len(terms) == 1 else "{" + ", ".join(terms) + "}"})')
        par = I[n]['parameters']
        if any(v is None for v in par.values()):
            # unpriced compiler parameters: the RTL default (recorded in the plan as UNPRICED)
            import kv_static as K
            s = K.source(I[n]['source'], I[n]['module'])
            dflt = _rtl_defaults(I[n]['source'], I[n]['module'])
            par = {k: (dflt.get(k) if v is None else v) for k, v in par.items()}
        if KVS_CK1 and kind in CK1_KINDS and I[n]['module'] in KIT_HARD:
            dflt = _rtl_defaults(I[n]['source'], I[n]['module'])
            if any(str(dflt.get(k)) != str(v) for k, v in par.items()):
                raise ValueError(f'kv_static_die: hard child {n} ({I[n]["module"]}) needs non-default parameters {par}')
            par = {}
        if par.get('MU') == 0:      # MU-ADOPT-KV 10-19: the MU 0 default stays implicit (existing tile text unchanged)
            par = {k: v for k, v in par.items() if k != 'MU'}
        ps = (' #(' + ', '.join(f'.{k}({v})' for k, v in par.items()) + ')') if par else ''
        body.append(f'    {I[n]["module"]}{ps} u_{loc[n]} (' + ', '.join(cs) + ');')
    # outputs: member output slices read by another tile / an existing die master, plus the die-level exports
    outs = OrderedDict()                   # port -> (expr, width, consumers)
    for c, ci in I.items():
        if c in loc:
            continue
        cd, ckind, cloc = cluster_of(c)
        for p, items in ci['inputs'].items():
            for k, it in enumerate(items or []):
                src = it.get('instance')
                if src not in loc:
                    continue
                lo, w = it['lo'], it['width']
                full = lo == 0 and w == spec(src)[it['port']]['width']
                if ckind == 'vport' and it['port'] in RSP:
                    outs.setdefault('rsp', (rsp_expr('slg', RSP), 1056, []))[2].append((cd, f'i{p[2]}'))
                    continue
                if ckind == 'ectl' and it['port'] in KRSP:
                    outs.setdefault('krsp', (rsp_expr('slg', KRSP), 1062, []))[2].append((cd, 'rs'))
                    continue
                if ckind == 'ectl' and it['port'] in KG and kind == 'ctl':
                    outs.setdefault('kg', (rsp_expr('lprg', KG), 23, []))[2].append((cd, 'kg'))
                    continue
                if ckind == 'vport' and p == 'cfg_age':          # KV-BOOTAGE: die cfg {DQ, RT} -> the V port's cfg pin
                    pn = f'{loc[src]}__{it["port"]}__{lo}_{w}'
                    outs.setdefault(pn, (f'w_{loc[src]}__{it["port"]}[{lo + w - 1}:{lo}]', w, []))[2].append((cd, 'cfg'))
                    continue
                if ckind == 'ectl' and p == 'cfg':
                    pn = f'{loc[src]}__{it["port"]}__{lo}_{w}'
                    outs.setdefault(pn, (f'w_{loc[src]}__{it["port"]}[{lo + w - 1}:{lo}]', w, []))[2].append((cd, 'cfg'))
                    continue
                if ckind == 'd2d' and p.startswith('kvn_compiled'):
                    outs.setdefault('kvi', (rsp_expr('wprg', KVI), 61, []))[2].append((cd, 'kvi'))
                    continue
                pn = f'{loc[src]}__{it["port"]}' + ('' if full else f'__{lo}_{w}')
                outs.setdefault(pn, (f'w_{loc[src]}__{it["port"]}' + ('' if full else f'[{lo + w - 1}:{lo}]'), w, []))
                tgt = (cd, p) if ckind == 'd2d' else (cd, ('sig', (src, it['port'], lo, w)))
                if tgt not in outs[pn][2]:
                    outs[pn][2].append(tgt)
    die_x = set()
    for (lp, p), (pn, w) in DIE_EXPORTS.get(kind, {}).items():
        expr = rsp_expr(lp, p) if isinstance(p, (list, tuple)) else f'w_{lp}__{p}'
        outs.setdefault(pn, (expr, w, []))
        die_x.add(pn)
    if kind == 'attn' and ASTK_ST:
        # KV-WIRE2 ASTK: the held attention calendar slice {EXP, Z, LMAX}, one tile pin a stack (a pin faces its strip)
        for st in STACKS:
            outs[f'acal_{st}'] = (rsp_expr('attn_root', ACAL), 48, [])
            die_x.add(f'acal_{st}')
    if kind == 'attn' and SEQ_S and 'fin' in ports:
        # KV-WIRE2 SEQ: the sequencer's result header ar_h {valid, g, beat[5:0]} = the final join's stream header (pure
        # wires from the fin input; g = 0 and beat[5] = 0: the static die has ONE 32-beat result stream)
        outs['arh'] = (('w_attn_face__hdr_l' if ATTN_LAND else "{fin[0], 2'b00, fin[5:1]}"), ARH_W, [])
        die_x.add('arh')
    if kind == 'emb':                      # the D2D RESULT proxy for the PCs (via their groups)
        for key in PASSES:
            nm, up_, uw, ilo, iw, expr = pc_pass(*key)
            if up_[0] == 'kvs_emb':
                add_port(f'd2d__{_d2d_bundles()[key[1]][0]}', dir='input', width=sum(
                    v[2] for kk, v in _d2d_bundles().items() if kk != '_widths' and v[0] == _d2d_bundles()[key[1]][0]),
                    cls='sig', src=('d2d_kv', _d2d_bundles()[key[1]][0]))
                outs[up_[1]] = (expr, uw, [])
    if kind == 'grp':                      # pass words for the group's four PCs (pure wires, no edge)
        for nm, up_, uw, ilo, iw, expr in PASSES.values():
            add_port(f'x__{nm.split("__")[0]}', dir='input', width=uw, cls='sig', src=up_)
            outs[f'y__{nm}'] = (f'x__{nm.split("__")[0]}' + ('' if (ilo == 0 and iw == uw) else f'[{ilo + iw - 1}:{ilo}]'), iw, [])
    for pn, (expr, w, cons) in outs.items():
        add_port(pn, dir='output', width=w, cls='export', expr=expr, consumers=cons, die=pn in die_x)
    return dict(inst=die_inst, kind=kind, ports=ports, wires=wires, body=body, members=mem, loc=loc)


def rsp_expr(local, fields):
    """{last, ..., first} of a member's outputs (LSB first = fields[0])"""
    return '{' + ', '.join(f'w_{local}__{f}' for f in reversed(fields)) + '}'


_DFLT = {}


def _rtl_defaults(path, module):
    if (path, module) not in _DFLT:
        txt = re.sub(r'//[^\n]*', '', (ROOT / path).read_text())
        m = re.search(r'\bmodule\s+' + module + r'\s*#\s*\((.*?)\)\s*\(', txt, re.S)
        d = {}
        for k, v in re.findall(r'(\w+)\s*=\s*([0-9]+)', m.group(1) if m else ''):
            d[k] = int(v)
        _DFLT[(path, module)] = d
    return _DFLT[(path, module)]


# CTL: the layer programme's HOST authority (the die's former lprg image wiring, qkd_static_kv_layer_programme_img):
# start <- the link calendar sequencer tok_start (dcal tks), auth <- HOST {token_epoch_valid, program_ready,
# program_epoch, program_digest}, cohort tag / gen <- HOST (TAG59 = {epoch16, stage6, token18, position13, segment6})
CTL_OVERRIDE = {
    ('lprg', 'start'): ('st', 1, 'st'),
    ('lprg', 'authority_valid'): ('auth', 82, 'auth[0]'),
    ('lprg', 'programme_authorized'): ('auth', 82, 'auth[1]'),
    ('lprg', 'programme_epoch'): ('auth', 82, 'auth[17:2]'),
    ('lprg', 'programme_digest'): ('auth', 82, 'auth[81:18]'),
    ('lprg', 'authority_epoch'): ('cht', 59, 'cht[58:43]'),
    ('lprg', 'authority_token'): ('cht', 59, 'cht[36:19]'),
    ('lprg', 'authority_position'): ('cht', 59, "{5'd0, cht[18:6]}"),
    ('lprg', 'authority_generation'): ('chg', 2, 'chg'),
}
# ATTN (PVFIN): the stream face's final-join inputs = ONE die bundle fin (pvfin fo: one relay chain for valid / beat /
# epoch / data, so they stay edge-aligned)
ATTN_OVERRIDE = {
    ('attn_face', 'f_valid'): ('fin', 534, 'fin[0]'),
    ('attn_face', 'f_beat'): ('fin', 534, 'fin[5:1]'),
    ('attn_face', 'f_epoch'): ('fin', 534, 'fin[21:6]'),
    ('attn_face', 'f_data'): ('fin', 534, 'fin[533:22]'),
}
# P7 (AFAULT): the fault root's die lanes, one 1-b tile port per source bus (LSB first)
AFAULT_OVERRIDE = {
    ('afr', 'd'): ([(pn, 1) for pn, _src in AFAULT_D], '{' + ', '.join(pn for pn, _src in reversed(AFAULT_D)) + '}'),
    ('afr', 'c'): ([(pn, 1) for pn in AFAULT_C], '{' + ', '.join(reversed(AFAULT_C)) + '}'),
}
# die-level exports beyond the join's tile-to-tile edges: (local, port) -> (tile port, width)
DIE_EXPORTS = dict(
    pc={('pc', 'er'): ('pc__er', 261), ('pc', 'ko'): ('pc__ko', 33), ('pc', 'fo'): ('pc__fo', 1),
        ('pc', 'po'): ('pc__po', 328), ('pc', 'completion_v'): ('pc__completion_v', 1),
        ('pc', 'completion_we'): ('pc__completion_we', 1)},
    ctl={('lprg', tuple(LP)): ('lp', 21), ('boot', 'setup_ready'): ('boot__setup_ready', 1),
         ('own', 'native_reserved'): ('own__native_reserved', 1), ('own', 'ownership_valid'): ('own__ownership_valid', 1),
         ('cf_root', 'fault'): ('cf_root__fault', 1)},    # KVJ-G2b: the completion-fault tree root -> HOST
    # KVJ-G2b: the attention service root's PV start word -> both PV pairs' st face {start, context_len, epoch} (LSB first)
    attn={('attn_root', ('start_pv', 'ctx', 'ep')): ('pvst', 31)},
)
if PVFIN:   # KV-PLAN-FIN: the final join's command word {start_pv, ep, cal R/P1/P0} (LSB first)
    DIE_EXPORTS['attn'][('attn_root', tuple(PVFST))] = ('pvfst', 65)
if AHUB_STATIC:   # KV-INTEG/AHUB: the attention command word of the static hub
    DIE_EXPORTS['attn'][('attn_root', tuple(AHS))] = ('ahs', AHS_W)
if SEQ_S:         # KV-WIRE2 SEQ: the attention programme's request / Q beat face -> the static sequencer
    DIE_EXPORTS['attn'][('attn', 'prg_l' if ATTN_LAND else tuple(PRG))] = ('prg', PRG_W)   # ATTN_LAND: launched copy
if BOOT:    # the pc_path's slice-facing outputs (note s5.5)
    DIE_EXPORTS['pc'].update({('pc', p[4:]): (p, w) for _b, p, _s, w, out in BOOT_HSL if out})
DIE_EXPORTS['pc_h'] = DIE_EXPORTS['pc']
import kv_bootage as KB   # noqa: E402  KV-BOOTAGE 10-19 (OT_KV_BOOT_AGES=1)
if KB.ON:   # the pair FIRST_INPUT_AGE bytes {pair 1, pair 0} -> both PV pair clusters (pvw cfa, a die join: kv_bootage)
    DIE_EXPORTS['ctl'][('dcfg', 'age_pv')] = ('dcfg__age_pv', 16)
if AFAULT:   # P7: each group's chain node -> the next slot's group (or, slot 7, the attention control tile)
    DIE_EXPORTS['grp'] = {('af', 'fault'): ('af__fault', 1)}


def _exports(kind):
    out = []
    for (lp, p), (pn, w) in DIE_EXPORTS.get(kind, {}).items():
        out.append((lp, list(p) if isinstance(p, tuple) else p, pn, w))
    return out


# HOST <-> static die joins (kv_static_boot_join.HOST_DIE_JOINS + kvjf own_obs quiet): consumer (join inst, port)
def host_joins():
    out = []
    for dj in graph().get('die_joins', []):
        c, p = dj['consumer'].split('.')
        pr = dj['producer'].split('.')
        out.append((c, p, pr[0], pr[1], dj.get('width'), dj.get('lo')))
    return out


OPEN_OWNERS = [   # (role / local, port prefix) -> owner: producers still being built or decisions owed
    ('pc', 'es_', 'KVJ-C3 (writer 4-lane -> 128-PC fan-out, es_expected_* / es_context)'),
    ('pc', 'emb_issue_v', 'KVJ-C3 (embedding token-run slot player)'),
    ('pc', 'emb_word_index', 'KVJ-C3 (embedding token-run slot player)'),
    ('pc', 'emb_half', 'KVJ-C3 (embedding token-run slot player)'),
    ('pc', 'emb_scale', 'KVJ-C3 (embedding token-run slot player)'),
    ('pc', 'emb_return_slot', 'KVJ-C3 (embedding token-run slot player)'),
    ('embr', 'capture_slot', 'KVJ-C3 (embedding slot player: station capture slots)'),
    ('embr', 'transfer_slot', 'KVJ-C3 (embedding slot player: station transfer slots)'),
    ('join', 'beat_slot', 'KVJ-C3 (embedding slot player: join4 beat slot)'),
    ('attn', 'compiled_', 'KVJ-SMALL / KVJ-B successor (qkd_attn_cal_gen, R stretch)'),
    ('attn', 'fused_program_capability', 'KVJ-E (boot image capability bit)'),
    ('attn', 'request_ready', 'KVJ-SMALL (attention service result face, ahub / seq_static D3)'),
    ('attn', 'result_', 'KVJ-SMALL (attention service result face)'),
    ('attn', 'service_fault', 'KVJ-SMALL (attention service result face)'),
]


def open_owner(n, p):
    lp = cluster_of(n)[2]
    for l_, pre, own in OPEN_OWNERS:
        if l_ == lp and p.startswith(pre):
            return own
    return 'KVJ-G2 die wiring (see plan static_die.die_joins)'


# the PCs' words from outside their group, carried once per group: name -> (pass name, upstream (inst, port), upstream
# width, slice lo, slice width, upstream expression on the producer tile)
PASSES = OrderedDict([
    (('embgw', 'est', 0, 1), ('est__0_1', ('embgw', 'est'), 13, 0, 1, None)),
    (('d2d', 'engine_result_token', 0, 18), ('tok', ('kvs_emb', 'px_tok'), 18, 0, 18, None)),
    (('d2d', 'engine_result_tag', 43, 16), ('tep', ('kvs_emb', 'px_tep'), 16, 0, 16, None)),
])


def pc_pass(src, port, lo, w):
    key = (src, port, lo, w)
    if key not in PASSES:
        raise ValueError(f'kv_static_die: PC word {key} has no group pass')
    nm, up_, uw, ilo, iw, _ = PASSES[key]
    if up_[0] == 'kvs_emb':
        b, blo, _bw = _d2d_bundles()[port]
        return nm, up_, uw, ilo, iw, f'd2d__{b}[{blo + lo + w - 1}:{blo + lo}]'
    return nm, up_, uw, ilo, iw, None


def _fill_passes():
    for key in list(PASSES):
        nm, up_, uw, ilo, iw, _ = PASSES[key]
        if up_[0] == 'kvs_emb':
            PASSES[key] = pc_pass(*key)


def module_text(t, name):
    L = [f'// {name}: GENERATED by tools/qwen_kv_die/kv_static_die.py (wires-only parent of the static join; do not edit)',
         f'module {name} (']
    pl = []
    for pn, v in t['ports'].items():
        if v.get('scalar') or (KITS and t['kind'] in CK1_KINDS + KIT_KINDS and v['cls'] in ('clock', 'reset') and v['width'] == 1):
            pl.append(f'    {v["dir"]} wire {pn}')         # the kit's CTS root / reset pin: a scalar port
            continue
        pl.append(f'    {v["dir"]} wire [{v["width"] - 1}:0] {pn}')
    L.append(',\n'.join(pl))
    L.append(');')
    for pn, w, bname, off in t.get('packed', []):
        L.append(f'    wire [{w - 1}:0] {pn} = {bname}[{off + w - 1}:{off}];')
    L += t['wires']
    L += t['body']
    for pn, v in t['ports'].items():
        if v['dir'] == 'output':
            L.append(f'    assign {pn} = {v["expr"]};')
    L.append('endmodule')
    txt = '\n'.join(L) + '\n'
    return txt


def rel(T, S):
    """the peer S as named from tile T (replica-generic port names)"""
    kt, ks = kind_of(T), kind_of(S)
    if kt in ('pc', 'pc_h'):
        if ks == 'grp':
            return 'grp'
        if ks in ('pc', 'pc_h'):
            return 'prev' if int(S.split('_')[2]) == int(T.split('_')[2]) - 1 else 'next'
        if ks == 'emb':
            return 'next'              # the return train's root word leaves on the same face as a station's
        if ks in ('ctl', 'hroot'):
            return 'next'              # KVJ-C3: the es fan root's stack chain enters PC 31 on a station's chain face
    if kt == 'hroot' and ks in ('pc', 'pc_h'):
        return 'pc'                    # the stack's PC 31 chain end
    if kt == 'ctl' and ks == 'hroot':
        return 'hroot_' + S.split('_')[2]
    if kt == 'grp' and ks in ('pc', 'pc_h'):
        return f'pc{int(S.split("_")[2]) % 4}'
    if ks in ('ctl', 'attn', 'emb'):
        return ks
    return S


def pack(tiles):
    """one bundle port per tile pair (inputs i_<peer>, outputs o_<peer>): every edge between two generated tiles rides
    ONE die bus (one relay chain) per direction; layout = the consumer's per-signal ports sorted by name"""
    layout = {}
    for T, t in tiles.items():
        groups = defaultdict(list)
        for pn, v in t['ports'].items():
            if v['dir'] == 'input' and v['cls'] == 'sig' and isinstance(v.get('src'), tuple) and len(v['src']) == 4:
                groups[cluster_of(v['src'][0])[0]].append((pn, v['width'], v['src']))
        for S, lst in groups.items():
            # order by the PRODUCER's replica-generic key (local name, port, slice): identical text for every replica
            layout[(T, S)] = sorted(lst, key=lambda e: (cluster_of(e[2][0])[2], e[2][1], e[2][2], e[2][3], e[0]))
    for T, t in tiles.items():
        new, packed = OrderedDict(), []
        keyexpr = {}
        for pn, v in t['ports'].items():
            if v['dir'] == 'output':
                for cd, cp in v['consumers']:
                    if isinstance(cp, tuple) and cp[0] == 'sig':
                        keyexpr[cp[1]] = v['expr']
        for pn, v in t['ports'].items():
            if v['dir'] == 'input' and v['cls'] == 'sig' and isinstance(v.get('src'), tuple) and len(v['src']) == 4:
                continue
            if v['dir'] == 'output':
                rest = [c for c in v['consumers'] if not (isinstance(c[1], tuple) and c[1][0] == 'sig')]
                if rest or not v['consumers'] or v.get('die'):
                    new[pn] = dict(v, consumers=rest)
                continue
            new[pn] = v
        ins_ = sorted(((rel(T, S), S, lst) for (TT, S), lst in layout.items() if TT == T))
        for r, S, lst0 in ins_:
            for sfx, lst in ds_parts(T, S, lst0):
                name, off = f'i_{r}{sfx}', 0
                for pn, w, key in lst:
                    packed.append((pn, w, name, off))
                    off += w
                if name in new:
                    raise ValueError(f'kv_static_die: {T} bundle {name} twice')
                new[name] = dict(dir='input', width=off, cls='bundle', peer=S, layout=lst)
        outs_ = sorted(((rel(T, C), C, lst) for (C, S), lst in layout.items() if S == T))
        for r, C, lst0 in outs_:
            lexpr = ds_land(t, T, C, lst0, keyexpr)
            for sfx, lst in ds_parts(C, T, lst0):
                name = f'o_{r}{sfx}'
                if name in new:
                    raise ValueError(f'kv_static_die: {T} bundle {name} twice')
                new[name] = dict(dir='output', width=sum(w for _, w, _ in lst), cls='bundle', peer=C,
                                 peer_port=f'i_{rel(C, T)}{sfx}', consumers=[], layout=lst,
                                 expr='{' + ', '.join(reversed([lexpr.get(key, keyexpr[key]) for _, _, key in lst])) + '}')
        t['ports'], t['packed'], t['keyexpr'] = new, packed, keyexpr
    return tiles


# ------------------------------------------------------------------------------------------------ KV-DOMSPLIT 10-19
def _ds_bkind(kind):
    return {'grp_h': 'grp', 'pc_h': 'pc'}.get(kind, kind)


def ds_key(key):
    """replica-generic name of a producer field (src join inst, port, lo, w): '<local>.<port>[lo+:w]'"""
    return f'{cluster_of(key[0])[2]}.{key[1]}[{key[2]}+:{key[3]}]'


def _ds_table():
    if 'ds_table' not in _G:
        _G['ds_table'] = json.loads((ROOT / DOMSPLIT_TABLE).read_text())['fields']
    return _G['ds_table']


def ds_domain(key):
    """'ck' | 'hck': the measured launch domain of one producer field (fail closed)"""
    bk = _ds_bkind(cluster_of(key[0])[1])
    d = _ds_table().get(bk, {}).get(ds_key(key))
    if d not in ('ck', 'hck'):
        raise ValueError(f'kv_static_die DOMSPLIT: no measured launch domain for {bk} field {ds_key(key)} ({DOMSPLIT_TABLE})')
    return d


def ds_parts(T, S, lst):
    """[(port suffix, fields)] of the bundle S -> T: one part (suffix '') unless DOMSPLIT splits a group <-> PC word into
    its ck part ('') and its hck part ('_h'); the field order inside each part is the bundle's (LSB first)"""
    if not (DOMSPLIT and {_ds_bkind(kind_of(T)), _ds_bkind(kind_of(S))} == {'grp', 'pc'}):
        return [('', lst)]
    ck = [e for e in lst if ds_domain(e[2]) == 'ck']
    hk = [e for e in lst if ds_domain(e[2]) == 'hck']
    return [(sfx, p_) for sfx, p_ in (('', ck), ('_h', hk)) if p_]


def ds_land(t, T, C, lst, keyexpr):
    """DOMSPLIT: the group gather word (slg -> kvs_ctl) stays ONE ck word; its hck fields land in the group on a 2-flop
    async_reg synchroniser (qkd_kv_lvl_land u_hland, clocked by the group's core clock, reset rst_n).  Returns
    {field key: landed expression}; records t['domsplit_land'] = landed bit offsets in the gather word"""
    if not (DOMSPLIT and _ds_bkind(kind_of(T)) == 'grp' and kind_of(C) == 'ctl'):
        return {}
    hk = [(w, key) for _pn, w, key in lst if ds_domain(key) == 'hck']
    if not hk:
        return {}
    P = t['ports']
    ckp = next((pn for pn, v in P.items() if v['cls'] == 'clock' and v.get('domain') == 'core'), None)
    if ckp is None or 'rst_n' not in P:
        raise ValueError(f'kv_static_die DOMSPLIT: {T} has no core clock / rst_n port for the gather landing')
    n = sum(w for w, _ in hk)
    lexpr, o_ = {}, 0
    for w, key in hk:
        lexpr[key] = f'w_hland__q[{o_ + w - 1}:{o_}]'
        o_ += w
    t['wires'].append(f'    wire [{n - 1}:0] w_hland__q;')
    t['body'].append(f'    qkd_kv_lvl_land #(.W({n})) u_hland (.ck({ckp}), .rst_n(rst_n), .d('
                     + '{' + ', '.join(reversed([keyexpr[key] for _, key in hk])) + '}), .q(w_hland__q));')
    bits, o_ = [], 0
    for _pn, w, key in lst:
        if key in lexpr:
            bits += list(range(o_, o_ + w))
        o_ += w
    t['domsplit_land'] = dict(word_width=o_, bits=bits, delay_edges=2)
    return lexpr


def domsplit_table(ports_dir):
    """(run with OT_KV_DOMSPLIT unset, at the design point being split) -> {kind: {field: 'ck'|'hck'}} from the measured
    per-bit launch domains (kvs_port_domains bit_domains) of the base tiles' group <-> PC words and the group gather"""
    if DOMSPLIT:
        raise SystemExit('domsplit_table: run on the base design point (OT_KV_DOMSPLIT unset)')
    T = all_tiles()
    rec = {k: json.loads((Path(ports_dir) / f'{k}_ports.json').read_text())['ports'] for k in ('grp', 'grp_h', 'pc', 'pc_h')}
    out, src = {'grp': {}, 'pc': {}}, []

    def bitdom(kind, port, b):
        v = rec[kind][port]
        for hi, lo, ds in v.get('bit_domains', []):
            if lo <= b <= hi:
                return ds
        return [d for d in v['domains'] if d not in ('none', '?const')]

    for d, t in T.items():
        k = t['kind']
        if k not in rec:
            continue
        for pn, v in t['ports'].items():
            if v['dir'] != 'output' or not v.get('layout'):
                continue
            if not ((k in ('grp', 'grp_h') and (pn == 'o_ctl' or re.fullmatch(r'o_pc\d', pn))) or
                    (k in ('pc', 'pc_h') and pn == 'o_grp')):
                continue
            o_ = 0
            for _pn, w, key in v['layout']:
                ds = {x for b in range(o_, o_ + w) for x in bitdom(k, pn, b)}
                o_ += w
                if len(ds) != 1 or not ds <= {'ck', 'hck'}:
                    raise ValueError(f'domsplit_table: {d}.{pn} field {ds_key(key)} has launch domains {sorted(ds)}')
                bk, fk = _ds_bkind(cluster_of(key[0])[1]), ds_key(key)
                if out[bk].setdefault(fk, ds.copy().pop()) != next(iter(ds)):
                    raise ValueError(f'domsplit_table: {fk} differs between replicas')
                src.append((k, pn))
    return dict(fields=out, measured_ports=sorted(set(src)))


SIDES = {st: (st,) for st in STACKS}       # one fan per stack, in the stack's group column middle


def add_fans(tiles):
    """per die side one wires-only FAN tile between the control tile and that side's 16 groups / 16 ECTL frames: the
    control traffic crosses the centre column as ONE word each way (the PV pairs / HOST row leave a single narrow
    crossing), and the 16 group words leave the fan in that side's free band.  Broadcast bits ride the crossing once."""
    ctl = tiles['kvs_ctl']
    for side, stks in SIDES.items():
        fname = f'kvs_fan_{side}'
        grps = [f'slg_{st}_{g}' for st in stks for g in range(8)]
        ects = [f'ectl_{st}_{g}' for st in stks for g in range(8)]
        fports, fpacked = OrderedDict(), []
        # ---- down: CTL -> groups (+ ECTL kg / cfg)
        union, uexpr, uw = [], {}, {}
        for k, gd in enumerate(grps):
            op = ctl['ports'].pop(f'o_{gd}')
            for _pn, w, key in op['layout']:
                if key not in uexpr:
                    union.append(key)
                    uexpr[key], uw[key] = ctl['keyexpr'][key], w
        kg = ctl['ports']['kg']
        kg['consumers'] = [c for c in kg['consumers'] if c[0] not in ects]
        union.append(('KG',))
        uexpr[('KG',)], uw[('KG',)] = kg['expr'], 23
        cfgs = []
        for pn in list(ctl['ports']):
            v = ctl['ports'][pn]
            if pn.startswith('dcfg__ectl_a_cfg__') and v['consumers'] and v['consumers'][0][0] in ects:
                key = ('CFG', ects.index(v['consumers'][0][0]))
                union.append(key)
                uexpr[key], uw[key] = v['expr'], v['width']
                cfgs.append(key)
                del ctl['ports'][pn]
        if not kg['consumers']:
            pass
        off, uoff = 0, {}
        for key in union:
            uoff[key] = off
            off += uw[key]
        ctl['ports'][f'o_fan_{side}'] = dict(dir='output', width=off, cls='bundle', peer=fname, peer_port='i_ctl',
                                            consumers=[], expr='{' + ', '.join(reversed([uexpr[k_] for k_ in union])) + '}')
        fports['i_ctl'] = dict(dir='input', width=off, cls='bundle', peer='kvs_ctl')
        sl = lambda key: f'i_ctl[{uoff[key] + uw[key] - 1}:{uoff[key]}]'      # noqa: E731
        # KVJ-G2b: the fan -> group words ride TWO neighbour CHAINS (fan -> slot 3 -> 2 -> 1 -> 0, fan -> slot 4 -> ... -> 7),
        # not eight fan -> group bundles (the 8 x 194-b star filled the stack's control channel).  A group's word =
        # the broadcast fields B (same keys for every group: boot data / address, programme fields) + one slot of
        # per-group fields per chain group, own slot first; each group forwards {B, slots rotated by one} (pure wiring,
        # identical replicas, no constant: the chain end's forward output is unconsumed)
        lays = {gd: tiles[gd]['ports']['i_ctl']['layout'] for gd in grps}
        common = set.intersection(*[{key for _pn, _w, key in lst} for lst in lays.values()])
        bl = sorted((pn, w, key) for pn, w, key in lays[grps[0]] if key in common)
        own = {gd: sorted((pn, w, key) for pn, w, key in lst if key not in common) for gd, lst in lays.items()}
        sig = [(pn, w) for pn, w, _ in own[grps[0]]]
        for gd in grps:
            if [(pn, w) for pn, w, _ in own[gd]] != sig or [(pn, w) for pn, w, _ in bl] != \
                    sorted((pn, w) for pn, w, key in lays[gd] if key in common):
                raise ValueError(f'kv_static_die: {gd} control word is not replica-generic')
        bw, pw = sum(w for _, w, _ in bl), sum(w for _, w in sig)
        chains = [[f'slg_{stks[0]}_{ORDER[s_]}' for s_ in c_] for c_ in
                  (((7, 6, 5, 4, 3, 2, 1, 0),) if FANFOLD else ((3, 2, 1, 0), (4, 5, 6, 7)))]
        nslot = len(chains[0])
        for ci, ch in enumerate(chains):
            lsb = [sl(key) for _pn, _w, key in bl] + [sl(key) for gd in ch for _pn, _w, key in own[gd]]
            fports[f'o_ch{ci}'] = dict(dir='output', width=bw + pw * nslot, cls='bundle', peer=ch[0], peer_port='i_ctl',
                                       consumers=[], expr='{' + ', '.join(reversed(lsb)) + '}')
            for j, gd in enumerate(ch):
                t_ = tiles[gd]
                gp = t_['ports']['i_ctl']
                gp.update(width=bw + pw * nslot, peer=fname if j == 0 else ch[j - 1], layout=None)
                offs_, o_ = {}, 0
                for pn, w, _ in bl:
                    offs_[pn], o_ = o_, o_ + w
                for pn, w, _ in own[gd]:
                    offs_[pn], o_ = o_, o_ + w
                t_['packed'] = [(pn, w, b_, offs_[pn] if b_ == 'i_ctl' else o_k) for pn, w, b_, o_k in t_['packed']]
                rot = ([f'i_ctl[{bw - 1}:0]'] + ([f'i_ctl[{bw + pw * nslot - 1}:{bw + pw}]'] if nslot > 1 else []) +
                       [f'i_ctl[{bw + pw - 1}:{bw}]'])
                t_['ports']['o_dn'] = dict(dir='output', width=bw + pw * nslot, cls='bundle',
                                           peer=ch[j + 1] if j + 1 < len(ch) else None,
                                           peer_port='i_ctl' if j + 1 < len(ch) else None, consumers=[],
                                           expr='{' + ', '.join(reversed(rot)) + '}')
        fports['o_kg'] = dict(dir='output', width=23, cls='export', expr=sl(('KG',)), consumers=[(e, 'kg') for e in ects])
        for key in cfgs:
            fports[f'o_c{key[1]}'] = dict(dir='output', width=uw[key], cls='export', expr=sl(key),
                                          consumers=[(ects[key[1]], 'cfg')])
        # ---- up: groups -> CTL (gathers), concatenated in group order
        uoff2, total = [], 0
        for k, gd in enumerate(grps):
            op = tiles[gd]['ports']['o_ctl']
            if not FANFOLD:
                fports[f'i_g{k}'] = dict(dir='input', width=op['width'], cls='bundle', peer=gd)
                op['peer'], op['peer_port'] = fname, f'i_g{k}'
            uoff2.append(total)
            total += op['width']
        if FANFOLD:
            # the concatenating up chain (chain end = the down chain's last group): slot j's word = {upstream, own}
            ch = chains[0]
            gws = {tiles[gd]['ports']['o_ctl']['width'] for gd in ch}
            if len(gws) != 1:
                raise ValueError(f'kv_static_die FANFOLD: group gathers differ in width {gws}')
            gw1 = gws.pop()
            for j, gd in enumerate(ch):
                t_ = tiles[gd]
                op = t_['ports'].pop('o_ctl')
                own_ = op['expr']
                head = j == len(ch) - 1
                if not head:
                    t_['ports']['i_up'] = dict(dir='input', width=total, cls='bundle', peer=ch[j + 1])
                t_['ports']['o_ctl'] = dict(op, width=total, peer=f'kvs_hroot_{side}' if j == 0 else ch[j - 1],
                                            peer_port='i_g' if j == 0 else 'i_up', consumers=[],
                                            expr=(f'{{{len(ch)}{{{own_}}}}}' if head else
                                                  f'{{i_up[{total - gw1 - 1}:0], {own_}}}'))
                if head:
                    t_['kind'] = 'grp_h'
            # root up word bit offset of group k (slot 7, the root's neighbour, = LSB; slot j = j shifts): the root re-orders it into the ctl's group order
            fports['_fold'] = dict(dir='none', gw=gw1, total=total, pos={k: ch.index(gd) for k, gd in enumerate(grps)})
        else:
            fports['o_ctl'] = dict(dir='output', width=total, cls='bundle', peer='kvs_ctl', peer_port=f'i_fan_{side}',
                                   consumers=[], expr='{' + ', '.join(f'i_g{k}' for k in reversed(range(len(grps)))) + '}')
        newp = []
        for pn, w, bname, o in ctl['packed']:
            if bname.startswith('i_slg_') and bname[2:] in grps:
                k = grps.index(bname[2:])
                newp.append((pn, w, f'i_fan_{side}', uoff2[k] + o))
            else:
                newp.append((pn, w, bname, o))
        ctl['packed'] = newp
        for gd in grps:
            ctl['ports'].pop(f'i_{gd}')
        ctl['ports'][f'i_fan_{side}'] = dict(dir='input', width=total, cls='bundle', peer=fname)
        # fan port order: inputs first, then outputs (stable across sides)
        tiles[fname] = dict(inst=fname, kind='fan', ports=OrderedDict(sorted(fports.items(), key=lambda kv: (kv[1]['dir'] != 'input', kv[0]))),
                            wires=[], body=[], members=[], loc={}, packed=[], keyexpr={})
    if HROOT:
        add_hroots(tiles)
    return tiles


def add_hroots(tiles):
    """KV-PLAN 10-17 decision 1: distributed static control.  Per stack one control root tile kvs_hroot_<st>
    (replica-identical, master qkd_kvs_hroot; the S roots at the stack seam, the N roots at the top of the N stacks:
    the half root of decision 1 is the W + E pair, split because the PV column leaves no W <-> E crossing at the seam).
    Down: ONE word ctl -> root {fan, h} (the stack fan word + the es edge word); the root emits the stack's chain head
    (qkd_kv_es_fan_stack) and re-registers the fan word.  Up: the fan's group gathers -> ctl, the PC 31 embedding
    return train -> the embedding tile.  Every word through the root takes exactly ONE register (priced as one relay
    stage: qkd_kv_stack_relays / the chain-head register)."""
    ctl, emb = tiles['kvs_ctl'], tiles['kvs_emb']
    for st in STACKS:
        hd = f'kvs_hroot_{st}'
        t = tiles[hd]
        P = t['ports']
        hin = P['i_ctl']                                  # pack(): the es edge word h (783 b) from the fan root
        HW = hin['width']
        fo = ctl['ports'].pop(f'o_fan_{st}')
        FW = fo['width']
        cp = ctl['ports'].pop(f'o_hroot_{st}')
        ctl['ports'][f'o_hroot_{st}'] = dict(dir='output', width=HW + FW, cls='bundle', peer=hd, peer_port='i_ctl',
                                            consumers=[], expr='{' + fo['expr'] + ', ' + cp['expr'] + '}')
        hin.update(width=HW + FW)
        gp = ctl['ports'].pop(f'i_fan_{st}')
        GW = gp['width']
        ctl['packed'] = [(pn, w, f'i_hroot_{st}' if b == f'i_fan_{st}' else b, o) for pn, w, b, o in ctl['packed']]
        ctl['ports'][f'i_hroot_{st}'] = dict(dir='input', width=GW, cls='bundle', peer=hd)
        rp = emb['ports'].pop(f'i_kvpc_{st}_31')
        RW = rp['width']
        emb['packed'] = [(pn, w, f'i_hroot_{st}' if b == f'i_kvpc_{st}_31' else b, o) for pn, w, b, o in emb['packed']]
        emb['ports'][f'i_hroot_{st}'] = dict(dir='input', width=RW, cls='bundle', peer=hd)
        tiles[f'kvpc_{st}_31']['ports']['o_next'].update(peer=hd, peer_port='i_r')
        P['i_g'] = dict(dir='input', width=GW, cls='bundle', peer=None)
        P['i_r'] = dict(dir='input', width=RW, cls='bundle', peer=None)
        P['rly__ck'] = dict(dir='input', width=1, cls='clock', domain='core')
        if FANFOLD:
            # decision 2: the fan's wiring moves into the root, on the root's registered fan word
            fan = tiles.pop(f'kvs_fan_{st}')
            fd = fan['ports'].pop('_fold')
            gw1, pos = fd['gw'], fd['pos']
            gexpr = '{' + ', '.join(f'w_rly__g[{gw1 * pos[k] + gw1 - 1}:{gw1 * pos[k]}]' for k in reversed(range(len(pos)))) + '}'
            outs = [('o_ctl', GW, 'kvs_ctl', f'i_hroot_{st}', gexpr), ('o_emb', RW, 'kvs_emb', f'i_hroot_{st}', 'w_rly__r')]
            for pn, v in fan['ports'].items():
                if v['dir'] != 'output':
                    continue
                v = dict(v, expr=v['expr'].replace('i_ctl[', 'w_rly__fan['))
                if pn == 'o_ch0':
                    tiles[v['peer']]['ports']['i_ctl'].update(peer=hd)
                P[pn] = v
            for nm, w, peer, pport, expr in outs:
                P[nm] = dict(dir='output', width=w, cls='bundle', peer=peer, peer_port=pport, consumers=[], expr=expr)
            P.move_to_end('o_ctl')
            P.move_to_end('o_emb')
        else:
            fp = tiles[f'kvs_fan_{st}']['ports']
            fp['i_ctl'].update(peer=hd)
            fp['o_ctl'].update(peer=hd, peer_port='i_g')
            for nm, w, peer, pport, expr in (('o_fan', FW, f'kvs_fan_{st}', 'i_ctl', 'w_rly__fan'),
                                             ('o_ctl', GW, 'kvs_ctl', f'i_hroot_{st}', 'w_rly__g'),
                                             ('o_emb', RW, 'kvs_emb', f'i_hroot_{st}', 'w_rly__r')):
                P[nm] = dict(dir='output', width=w, cls='bundle', peer=peer, peer_port=pport, consumers=[], expr=expr)
        t['wires'] += [f'    wire [{FW - 1}:0] w_rly__fan;', f'    wire [{GW - 1}:0] w_rly__g;', f'    wire [{RW - 1}:0] w_rly__r;']
        t['body'].append(f'    qkd_kv_stack_relays #(.HW({HW}), .FW({FW}), .GW({GW}), .RW({RW})) u_rly (.ck(rly__ck), '
                         f'.dn(i_ctl), .g_i(i_g), .r_i(i_r), .fan(w_rly__fan), .g(w_rly__g), .r(w_rly__r));')
        t['hroot'] = dict(HW=HW, FW=FW, GW=GW, RW=RW)
    return tiles


def kit_clocks(tiles):
    """OT_KV_TILE_KITS: per kit tile one clock port per domain (ck / hck), every child clock pin on it.  Pure renaming:
    every child entry of a kind already joined the same region trunk (_clocks_resets: clk_core_<r> / clk_hbm_<r>)."""
    for t in tiles.values():
        if t['kind'] not in KIT_KINDS:
            continue
        P = t['ports']
        ren = {pn: ('hck' if v.get('domain') == 'hbm' else 'ck') for pn, v in P.items() if v['cls'] == 'clock'}
        if not ren:
            continue
        clash = [n for n in ('ck', 'hck') if n in P and n not in ren]
        if clash:
            raise ValueError(f'kv_static_die KITS: {t["inst"]} already has a non-clock port {clash}')
        Q = OrderedDict()
        for pn, v in P.items():
            nm = ren.get(pn, pn)
            if nm not in Q:
                Q[nm] = v
        t['ports'] = Q
        rx = re.compile(r'\b(' + '|'.join(re.escape(k) for k in sorted(ren, key=len, reverse=True)) + r')\b')
        sub = lambda x: rx.sub(lambda m_: ren[m_.group(1)], x)           # noqa: E731
        t['body'] = [sub(x) for x in t['body']]
        t['wires'] = [sub(x) for x in t['wires']]
        for v in Q.values():
            if v.get('expr'):
                v['expr'] = sub(v['expr'])
    return tiles


def all_tiles():
    if 'tiles' not in _G:
        t_ = add_fans(pack({d: tile(d) for d in members()}))
        t_ = kit_clocks(t_) if KITS else t_
        if GRP_PRIVATE0:
            import kv_grp_private0
            kv_grp_private0.apply_tiles(t_, module_text)
        _G['tiles'] = t_
    return _G['tiles']


def rtl_text():
    """one module per tile kind; every replica must produce the identical text"""
    mods = OrderedDict()
    for d, t in all_tiles().items():
        name = KIND_MASTER[t['kind']]
        txt = module_text(t, name)
        if name in mods and mods[name][0] != txt:
            a, b = mods[name][0].splitlines(), txt.splitlines()
            diff = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            raise ValueError(f'kv_static_die: tile {d} differs from {mods[name][1]} ({name}) at line {diff}: '
                             f'{a[diff][:160] if diff < len(a) else ""!r} vs {b[diff][:160] if diff < len(b) else ""!r}')
        mods.setdefault(name, (txt, d))
    hdr = ('`timescale 1ns/1ps\n// KVJ-G2 2026-10-17: the static KV subsystem tiles of the Qwen KV die (kv_die.py --split, '
           'OT_KV_STATIC_DIE=1).\n// GENERATED by tools/qwen_kv_die/kv_static_die.py --rtl from the merged static join '
           '(kv_static_kvjf_join.build) + die_ages.json.\n// Wires-only parents: no logic, no flop, no constant except '
           "the layer programme's 5-b zero extension of the TAG59 position (as the image variant).\n\n")
    return hdr + '\n'.join(v[0] for v in mods.values())


def sources():
    """RTL files the tiles elaborate (children + their dependencies)"""
    import kv_static as K
    s = set()
    for t in all_tiles().values():
        for n in t['members']:
            s.add(ins()[n]['source'])
    s.update(K.pc_emb_sources())
    if BOOT:
        s.update(BOOT_PC_DEPS)
    s.update(K.EMB_SOURCES)
    if K.MU:
        s.update(K.MU_DEPS)
    if DOMSPLIT:
        s.add(LVL_LAND_RTL)
    return sorted(s)


# ------------------------------------------------------------------------------------------------ die bindings
def bindings():
    """kv_die BINDINGS entries for the static die masters (identity ports; por_n off-chip)"""
    out = {}
    seen = {}
    for d, t in all_tiles().items():
        mst = KIND_MASTER[t['kind']]
        if mst in seen:
            continue
        seen[mst] = d
        ports = {pn: [pn] for pn, v in t['ports'].items() if v['cls'] != 'pad'}
        cls = {'por_n': 'by_design: package POR pad (off-chip signal)'} if 'por_n' in t['ports'] else {}
        source_file = GRP_PRIVATE0_RTL if GRP_PRIVATE0 and t['kind'] in ('grp', 'grp_h') else PUBLIC_RTL_FILE
        out[mst] = dict(module=mst, file=source_file, ports=ports, sliced={}, classed=cls)
    # ECTL frame re-bound to the fused A + K issuer composition (qkd_ectl3_kiss_s)
    out['qkd_ectlk'] = dict(module='qkd_ectl3_kiss_st' if ASTK_ST else 'qkd_ectl3_kiss_s',
        file=ECTL_ST_FILE if ASTK_ST else 'rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv',
        parameters=dict(RESPONSE_LAT=ECTLK_RESPONSE_LAT, QK_ISSUE_AGE=ECTLK_QK_ISSUE_AGE, HXK=13, MUT=0),
        ports=dict(si=['si'], so=['so'], t0=['t0'], t1=['t1'], e0=['e0'], e1=['e1'], e2=['e2'], e3=['e3'], s0=['s0'],
                   s1=['s1'], s2=['s2'], s3=['s3'], rq=[f for f, _ in KREQ], rs=list(KRSP), kg=list(KG), cfg=['cfg'],
                   kf=['fault'], ck_a=['ck'], rst_n=['rst_n']),
        sliced=dict(ck_b='ck_a', ck_c='ck_a'), classed={})
    if PVFIN:
        out['qkd_pvfin'] = dict(module='qkd_pv_fin_s', file=PVFIN_FILE, parameters=dict(ADD_LAT=7, MUL_LAT=6, SKEW=1, MUT=0),
            ports=dict(ck=['ck'], rst_n=['rst_n'], fs=['start', 'epoch', 'cal'],
                       p0=['p0_valid', 'p0_beat', 'p0_epoch', 'p0_data'], p1=['p1_valid', 'p1_beat', 'p1_epoch', 'p1_data'],
                       fr=['rz_valid', 'rz_epoch', 'rz'], fo=[f for f, _ in FIN], ff=['fault']),
            sliced={}, classed={})
    if ASTK_ST:
        for mn in ('qkd_astk', 'qkd_astk_n'):
            out[mn] = dict(module='qkd_astk_strip_er_die', file=ASTK_FILE,
                parameters=dict(RL=ASTK_RL, Z_STRIDE=ASTK_Z_STRIDE, **(dict(DISTRIBUTED_ER=1) if ASTK_EXPAND else {})),
                ports=dict(st=['st'], aq=['aq'], am=['am'], ap=['ap'], af=['af'], lt=['lt'], cal=['cal'], erd=['erd'],
                           **{f'e{e}i': [f'so{e}'] for e in range(8)}, **{f'e{e}o': [f'si{e}'] for e in range(8)},
                           **{f'vh{k}': [f'vh{k}'] for k in range(4)},
                           ck_c=['ck_c'], ck_z0=['ck_z'], ck_x0=['ck_x'], ck_e0=['ck_e'], ck_r=['ck_r'], ck_d=['ck_er'],
                           rst_n=['rst_n']),
                sliced={**{f'ck_z{j}': 'ck_z0' for j in range(1, 4)}, **{f'ck_x{j}': 'ck_x0' for j in range(1, 32)},
                        **{f'ck_e{j}': 'ck_e0' for j in range(1, 8)}}, classed={})
    if SEQ_S:
        out['qkd_seq_st'] = dict(module='qkd_seq_static_s', file=SEQ_S_FILE, parameters=dict(MUT=0),
            ports=dict(skw=['kvn_word_valid', 'kvn_word_tag'],
                       prg=['prg_req_v', 'prg_req_pos', 'prg_q_v', 'prg_q_beat', 'prg_q_data'],
                       lp=['lp_run', 'lp_layer', 'lp_ctx_t'], svc=['svc'],
                       **{f'aq_{q}': [f'aq_{q}'] for q in STACKS}, **{f'kc_{q}': [f'kc_{q}'] for q in STACKS},
                       **{f'af_{q}': [f'af_{q}'] for q in STACKS}, ar=['ar_h'], hf=['hf'], hs=['hs'], tk=['tk'],
                       kst=['kst'], ck=['ck'], rst_n=['rst_n']), sliced={}, classed={})
    if AHUB_STATIC:
        out['qkd_ahub'] = dict(module='qkd_ahub_static_dw', file=AHUB_FILE,
            ports=dict(hs=['hs_start', 'hs_ep', 'hs_layer', 'hs_ctx', 'hs_cal_lo', 'hs_cal_r'],
                       **{f'ap_{st}': [f'ap{k}'] for k, st in enumerate(STACKS)},
                       **{f'am_{st}': [f'am{k}'] for k, st in enumerate(STACKS)},
                       fr=['fr_valid', 'fr_epoch', 'fr_rz'], hf=['hf'], ck_c=['ck'], rst_n=['rst_n']),
            sliced={}, classed={})
        # HKV-DIE 10-19 (HKV-ASTK finding): the hub's Z input stride must be the strip's (closed qkd_astk_ctl_s Z_STRIDE 4);
        # the RTL default 16 put every Z word on the wrong hub slot.  The hub kit must be (re)hardened at this value.
        if ASTK_ST:
            out['qkd_ahub']['parameters'] = dict(Z_IN_STRIDE=ASTK_Z_STRIDE)
        # HKV-DIE3 10-19 (HOURLY-KV decision (c)): the die binds the ACTUAL AP_OFS / FR_OFS of the post-station netlist
        # table (kv_static_params ahub_ages), never the RTL defaults while the table disagrees; the hub kit (a5) is
        # hardened at the same constants and kv_static_params AHUB_OFS_BOUND checks kit == die binding == table.
        ofs = ahub_ofs_bound()
        if ofs:
            out['qkd_ahub']['parameters'] = dict(out['qkd_ahub'].get('parameters') or {}, AP_OFS=ofs['AP_OFS_hex'],
                                                 FR_OFS=ofs['FR_OFS'])
    # KV-FACELAND-WIRE 10-19: a top-level tile selected in OT_KV_FACE_LAND binds its face-landed wrapper module
    # <master>_fl (same ports; the kit's rtl/lib/face_land file), so the bound netlist carries the edges the compiler
    # charges (kv_tile_views.py binds the matching CLOSED _fl view, kv_static_params FACE_LAND_BINDING checks die_bound.v)
    for tl in sorted(FACE_LAND_SEL):
        t = FACE_LAND_TILES[tl]
        if t['master'] in out:
            out[t['master']] = dict(out[t['master']], module=t['master'] + '_fl', file=face_land_rtl(tl))
    return out


def face_land_rtl(tile):
    """the face-land wrapper file of the selected tile's kit (spec sources rtl/lib/face_land/*), fail closed"""
    t = FACE_LAND_TILES[tile]
    sp = Path(ROOT) / f"physical/ref_tile/{t['kit']}/spec.json"
    src = [s for s in (json.loads(sp.read_text()).get('sources', []) if sp.exists() else []) if s.startswith('rtl/lib/face_land/')]
    if len(src) != 1:
        raise ValueError(f"kv_static_die: face-landed tile {tile}: kit {t['kit']} names {len(src)} face_land wrapper sources")
    return src[0]


def ahub_ofs_bound(spec=None):
    """OT_KV_AHUB_OFS: a static_params.json (params.ahub_ages) / ahub_ages JSON, or 'a0,a1,a2,a3:fr' (stacks WS WN ES
    EN, two's complement 16-bit each).  None when unset (the die then binds the RTL defaults and kv_static_params FAILS
    AHUB_OFS_BOUND wherever the table needs other values)."""
    spec = spec if spec is not None else os.environ.get('OT_KV_AHUB_OFS', '')
    if not spec:
        return None
    if ':' in spec and not Path(spec).exists():
        ap_s, fr = spec.split(':')
        ap = [int(x, 0) for x in ap_s.split(',')]
        fr = int(fr, 0)
        src = 'literal'
    else:
        p = Path(spec) if Path(spec).is_absolute() else ROOT / spec
        d = json.loads(p.read_text())
        d = (d.get('params') or {}).get('ahub_ages') or d.get('ahub_ages') or d
        ap, fr, src = [int(x) for x in d['AP_OFS']], int(d['FR_OFS']), str(spec)
    if len(ap) != 4 or any(not -32768 <= x < 32768 for x in ap) or not -(1 << 17) < fr < (1 << 17):
        raise ValueError(f'kv_static_die: OT_KV_AHUB_OFS {spec!r}: need 4 16-bit AP_OFS values and an FR_OFS')
    return dict(AP_OFS=ap, FR_OFS=fr, source=src,
                AP_OFS_hex='{' + ', '.join(f"16'h{x & 0xffff:04x}" for x in reversed(ap)) + '}')


# ------------------------------------------------------------------------------------------------ die integration
def _bundle_widths():
    return dict(rsp=1056, krsp=1062, kg=23, kvi=61, lp=21)


def inject(m, K):
    """K = the kv_die module.  Remove the superseded credit elements, place the static tiles, wire the join."""
    import qwen_rom_fulldie as F
    B = m['buses']
    by = {i.name: i for i in m['insts']}
    rec = m.setdefault('static_die', dict(dropped_endpoints=[], dropped_buses=[], opens=[], die_joins=[], notes=[]))
    m['geo']['relay_half_grid'] = bool(m['geo'].get('kv_wq_leaf_s'))   # the relay planner's grid stays as planned
    for k_ in ('kv_wq_leaves', 'kv_wq_binary', 'kv_wq_leaf_s', 'kv_wq_head', 'kv_wq_wide', 'kv_wq_mirror'):
        m['geo'][k_] = False             # the write queue is superseded (static writer -> PC es)
    m.pop('wq_straps', None)
    # ---- 0. geometry of the removed columns (per stack) before removal
    geo = {}
    for st in STACKS:
        ctrl = by[f'ctrl_{st}']
        land = by[f'land_{st}']
        hs = [by[f'hsl_{st}_{k}'] for k in range(NPC)]
        geo[st] = dict(ctrl=(ctrl.x, ctrl.y, ctrl.w, ctrl.h, ctrl.orient, ctrl.master), land=(land.x, land.y, land.w, land.h),
                       hsl_x=hs[0].x, hsl_w=hs[0].w)
    # ---- 1. remove superseded instances; a bus that loses its driver is dropped, its surviving loads recorded open
    gone = {i.name for i in m['insts'] if i.name.startswith(SUPERSEDED) and not i.name.startswith('cdc_dummy')}
    m['insts'][:] = [i for i in m['insts'] if i.name not in gone]
    keep = []
    repoint = {}
    for bid, cl, bits, eps in B:
        if not any(e[0] in gone for e in eps):
            keep.append((bid, cl, bits, eps))
            continue
        if eps[0][0] in gone:
            surv = [e for e in eps[1:] if e[0] not in gone]
            if cl in ('clock_trunk', 'reset'):
                rec['dropped_buses'].append(bid)
                continue
            repoint[bid] = (cl, bits, eps)
            rec['dropped_endpoints'] += [dict(bus=bid, inst=e[0], port=e[1], role='load (driver superseded)') for e in surv]
            continue
        surv = [e for e in eps if e[0] not in gone]
        if len(surv) < 2 and cl not in ('clock_trunk', 'reset'):
            repoint[bid] = (cl, bits, eps)
            rec['dropped_endpoints'] += [dict(bus=bid, inst=e[0], port=e[1], role='driver (loads superseded)') for e in surv]
            continue
        keep.append((bid, cl, bits, surv))
    B[:] = keep
    for k_ in ('forks',):
        if m.get(k_):
            m[k_] = {b_: [e for e in v if e[0] not in gone] for b_, v in m[k_].items() if b_ in {x[0] for x in B}}
            m[k_] = {b_: v for b_, v in m[k_].items() if v}
    if m.get('extra_conns'):
        for g_ in list(m['extra_conns']):
            if g_ in gone:
                del m['extra_conns'][g_]
    for g_ in list(m.get('host_ties', {})):
        if not any(b_[0] == g_ for b_ in B):
            m['host_ties'].pop(g_, None)
    add = B.append
    tiles = all_tiles()
    # ---- 2. place the tiles
    place(m, K, geo, F)
    by = {i.name: i for i in m['insts']}
    # ---- 3. masters of the existing frames
    for st in STACKS:
        for e in range(8):
            by[f'ectl_{st}_{e}'].master = 'qkd_ectlk'
    # ---- 4. join wiring between tiles (one bus a source slice; extra loads = relayed fork branches)
    nets = {}                                   # (driver inst, port) -> [loads]
    widths = {}
    for d, t in tiles.items():
        for pn, v in t['ports'].items():
            if v['dir'] != 'output':
                continue
            if v['cls'] == 'bundle':
                if v['peer'] is None:
                    continue                    # a chain end's forward word (unconsumed by design)
                nets[(d, pn)] = [(v['peer'], v['peer_port'])]
                widths[(d, pn)] = v['width']
                continue
            for cd, cp in v['consumers']:
                nets.setdefault((d, pn), [])
                if (cd, cp) not in nets[(d, pn)]:
                    nets[(d, pn)].append((cd, cp))
                widths[(d, pn)] = v['width']
    # existing-master sources (D2D end bundles / identity ports, gateway status) and the PC pass words
    for d, t in tiles.items():
        for pn, v in t['ports'].items():
            if v['dir'] != 'input':
                continue
            if v['cls'] == 'pass':                       # PC <- its group's y__ word
                st, k = d.split('_')[1], int(d.split('_')[2])
                gd = f'slg_{st}_{pc_group()[(st, k)]}'
                src = (gd, 'y__' + pn[3:])
            elif v['cls'] == 'sig' and isinstance(v['src'], tuple) and len(v['src']) == 2:
                src = v['src']                           # (d2d_kv | embgw | kvs_emb, port)
            else:
                continue
            nets.setdefault(src, [])
            if (d, pn) not in nets[src]:
                nets[src].append((d, pn))
            widths[src] = v['width'] if src[0] not in ('d2d_kv', 'embgw') else v['width']
    # vport <-> group, ECTL <-> group, ECTL kg / cfg (special bundles)
    for st in STACKS:
        for g in range(8):
            gd = f'slg_{st}_{g}'
            vp, par = f'vport_{st}_{g // 2}', g % 2
            add((f'pvvq_{st}_{g // 2}_{par}', 'kv_oneway', 15, [(vp, f'vq{par}'), (gd, 'vreq')]))
            add((f'krq_{st}_{g}', 'kv_oneway', 38, [(f'ectl_{st}_{ectl_frame(g)}', 'rq'), (gd, 'kreq')]))
    seen_buses = {b_[0] for b_ in B}
    fk = m.setdefault('forks', {})
    for (dinst, dport), loads in nets.items():
        if dport == 'rsp':
            for (cd, cp) in loads:
                st, k = cd.split('_')[1], int(cd.split('_')[2])
                add((f'pvrs_{st}_{k}_{cp[1]}', 'kv_oneway', 1056, [(dinst, 'rsp'), (cd, cp)]))
            continue
        if dport == 'krsp':
            for (cd, cp) in loads:
                st_, f_ = cd.split('_')[1], int(cd.split('_')[2])       # bus named by its group (kv_static_ages)
                add((f'krs_{st_}_{frame_engine(f_)}', 'kv_oneway', 1062, [(dinst, 'krsp'), (cd, 'rs')]))
            continue
        bits = widths.get((dinst, dport))
        if dinst == 'd2d_kv' and dport in ('svc', 'srx', 'skw'):
            # existing bundle buses: the static loads are relayed fork branches of hsvc / seqst_rx / seqst_kw
            trunk = dict(svc='hsvc', srx='seqst_rx', skw='seqst_kw')[dport]
            if trunk not in seen_buses:          # SEQ_S: srx has no sequencer load; its first static load is the trunk's
                seen_buses.add(trunk)
                add((trunk, 'kv_oneway', widths[(dinst, dport)], [(dinst, dport), loads[0]]))
                loads = loads[1:]
            fk.setdefault(trunk, [])
            fk[trunk] += [l_ for l_ in loads if l_ not in fk[trunk]]
            continue
        if dinst == 'embgw' and dport == 'est':
            fk.setdefault('est', [])
            fk['est'] += [l_ for l_ in loads if l_ not in fk['est']]
            continue
        if bits is None:
            raise ValueError(f'kv_static_die: no width for {dinst}.{dport}')
        if DCAL_BC and any(l_[0] == 'd2d_kv' and l_[1] in DCAL_BC_LINK for l_ in loads):
            # KV-DCAL-BOOTCFG (OT_KV_DCAL_BC=1): boot target 11 (link_cfg_*) ends on the calendar sequencer's bcfg pins;
            # the sequencer's merged cfg word (dcal_dcfg, kv_die) is the D2D end's only cfg producer
            if 'dcal' not in {i_.name for i_ in m['insts']}:
                raise ValueError('OT_KV_DCAL_BC needs the dcal instance (OT_KV_DCAL=1)')
            loads = [('dcal', DCAL_BC_LINK[l_[1]]) if l_[0] == 'd2d_kv' and l_[1] in DCAL_BC_LINK else l_ for l_ in loads]
            rec.setdefault('dcal_bc', []).append(f'{dinst}.{dport} -> ' + ', '.join(f'{a}.{b}' for a, b in loads))
        bid = _bid(dinst, dport, seen_buses)
        add((bid, 'kv_oneway', bits, [(dinst, dport), loads[0]]))
        if len(loads) > 1:
            fk[bid] = list(loads[1:])
    # the est bus becomes a relayed data trunk (its PC-group branches fork from the gateway pin)
    for i_, (bid, cl, bits, eps) in enumerate(B):
        if bid == 'est' and fk.get('est'):
            B[i_] = (bid, 'kv_oneway', bits, eps)
    # ---- 5. existing-master joins: D2D end, HOST root, sequencer, PHY, HOST slices, kc chain
    _die_joins(m, K, B, add, fk, rec)
    # ---- 6. clocks / resets / straps
    _clocks_resets(m, B, add, rec)
    m['geo']['static_die'] = dict(tiles=len(tiles), join_instances=len(ins()), rtl=RTL_FILE)
    return m


def _export_name(tiles, sd, key):
    t = tiles[sd]
    src, p, lo, w = key
    lp = cluster_of(src)[2]
    full = lo == 0 and w == spec(src)[p]['width']
    pn = f'{lp}__{p}' + ('' if full else f'__{lo}_{w}')
    if pn not in t['ports']:
        raise ValueError(f'kv_static_die: {sd} exports no {pn}')
    return pn


def _bid(inst, port, seen):
    b = re.sub(r'[^A-Za-z0-9_]', '_', f'ks_{inst}__{port}')
    b0, k = b, 1
    while b in seen:
        b = f'{b0}_{k}'
        k += 1
    seen.add(b)
    return b


def _die_joins(m, K, B, add, fk, rec):
    by = {i.name: i for i in m['insts']}
    seen = {b_[0] for b_ in B}

    def bus(bid, cl, bits, eps):
        if bid in seen:
            raise ValueError(f'kv_static_die: bus {bid} exists')
        seen.add(bid)
        add((bid, cl, bits, eps))
    # D2D end <- static (identity die ports on qkd_d2ds), kvi from the writer programme (replaces qkd_kvnc)
    for bid, src, dst, w in (('ks_att_tx_v', ('kvs_attn', 'attn__tx_valid'), 'att_tx_v', 1),
                             ('ks_att_tx_payload', ('kvs_attn', 'attn__tx_payload'), 'att_tx_payload', 548),
                             ('ks_emb_tx_v', ('kvs_emb', 'rowtx__emb_tx_v'), 'emb_tx_v', 1),
                             ('ks_emb_tx_payload', ('kvs_emb', 'rowtx__emb_tx_payload'), 'emb_tx_payload', 548),
                             ('ks_kv_drained', ('kvs_ctl', 'oobs__kv_drained_local'), 'kv_drained_local', 1),
                             ('ks_kv_flush', ('kvs_ctl', 'oobs__kv_flush_local'), 'kv_flush_local', 1),
                             ('ks_kv_active', ('kvs_ctl', 'oobs__kv_active_local'), 'kv_active_local', 1),
                             ('ks_kvi', ('kvs_ctl', 'kvi'), 'kvi', 61)):
        pass   # these are created by the tile export loop (consumers recorded there); kept for the record
    # sequencer lp <- the layer programme (was lprg), layer programme start / authority (was lprg's)
    for i_, (bid, cl, bits, eps) in enumerate(B):
        pass
    bus('ks_lprg_st', 'kv_oneway', 1, [('dcal', 'tks'), ('kvs_ctl', 'st')])
    bus('ks_lprg_auth', 'kv_oneway', 82, [('host', 'auth_lp'), ('kvs_ctl', 'auth')])
    bus('ks_lprg_cht', 'kv_oneway', 59, [('host', 'cohort_tag'), ('kvs_ctl', 'cht')])
    bus('ks_lprg_chg', 'kv_oneway', 2, [('host', 'cohort_gen'), ('kvs_ctl', 'chg')])
    bus('ks_seq_lp', 'kv_oneway', 21, [('kvs_ctl', 'lp'), ('seq', 'lp')])
    # KVJ-G2b: attention service root -> PV pairs (the pvw st face was undriven); PV_LEAD = these relay edges (record)
    if 'pvw_0' in by and 'pvw_1' in by:
        bus('ks_pvst', 'kv_oneway', 31, [('kvs_attn', 'pvst'), ('pvw_0', 'st')])
        fk['ks_pvst'] = [('pvw_1', 'st')]
    # KV-BOOTAGE: the sealed die cfg's pair ages -> both PV pair clusters (static configuration word, no handshake)
    if KB.ON and 'pvw_0' in by and 'pvw_1' in by:
        bus('ks_age_pv', 'kv_oneway', 16, [('kvs_ctl', 'dcfg__age_pv'), ('pvw_0', 'cfa')])
        fk['ks_age_pv'] = [('pvw_1', 'cfa')]
    # KV-PLAN-FIN: attention root -> final join command word; final join beat stream -> the stream face (kvs_attn fin)
    if PVFIN and 'pvfin' in by:
        bus('ks_pvfst', 'kv_oneway', 65, [('kvs_attn', 'pvfst'), ('pvfin', 'fs')])
        bus('ks_pvfin', 'kv_oneway', 534, [('pvfin', 'fo'), ('kvs_attn', 'fin')])
        # KV-RTRUNK 10-17: each PV pair's 534-b result beat stream (qkd_pvw_die_t rs_*: two result trunks -> header in the
        # strip; beat b at pair age out_age + RS_D + b, results/arch/qwen_kv_die/pv_trunk_t/plan.json result_trunk)
        if RS_PAIRS:
            bus('ks_pvp0', 'kv_oneway', 534, [('pvw_0', 'pr'), ('pvfin', 'p0')])
            bus('ks_pvp1', 'kv_oneway', 534, [('pvw_1', 'pr'), ('pvfin', 'p1')])
    # KV-INTEG/AHUB: the static hub's faces (the legacy hub buses hs / ares go; ap narrows to the static 43-b word)
    if AHUB_STATIC and 'ahub' in by:
        for i_ in reversed(range(len(B))):
            bid_, cl_, bits_, eps_ = B[i_]
            if bid_ in ('hs', 'ares'):
                del B[i_]
                seen.discard(bid_)
                rec['dropped_buses'].append(bid_)
            elif re.fullmatch(r'ap_(WS|WN|ES|EN)', bid_):
                B[i_] = (bid_, cl_, AHUB_AP_W, eps_)
        bus('ks_ahs', 'kv_oneway', AHS_W, [('kvs_attn', 'ahs'), ('ahub', 'hs')])
        if PVFIN and 'pvfin' in by:
            bus('ks_ahfr', 'kv_oneway', AHUB_FR_W, [('ahub', 'fr'), ('pvfin', 'fr')])
        rec['opens'].append(dict(where='seq.ar (520 b; qkd_seq_static_s ar_h 8 b)', owner='KV-PLAN3 SEQ swap: the result '
                                 'header {valid, g 0, beat} = the pvfin fo header (out_valid, out_beat), a fork of ks_pvfin; '
                                 'the legacy hub ao that fed it never fires on the static die (no pi_*)'))
        rec['notes'].append('ahub = qkd_ahub_static_dw (KV-INTEG/AHUB): ap_<st> 43 b needs the ASTK strip_er_st binding '
                            '(RTL-BUILD-KV ASTK (a)); seq.hs output unread (the hub starts on kvs_attn ahs)')
    # KV-WIRE2 ASTK: the strips' calendar, e-read requests (vh forks) and e quads -> the PV pairs' in_e
    if ASTK_ST and all(f'astk_{st}' in by for st in STACKS):
        # one held word a stack (point-to-point: the strip's cal pin faces kvs_attn; as w1 forks, the ES branch had no
        # peer face and ran 10 mm round the stack bottom, no relay spot)
        for st in STACKS:
            bus(f'ks_acal_{st}', 'kv_oneway', 48, [('kvs_attn', f'acal_{st}'), (f'astk_{st}', 'cal')])
        names_ = {b_[0] for b_ in B}
        for st in STACKS:
            p_ = STACKS.index(st) % 2
            for k in range(4):
                if f'pvh_{st}_{k}' not in names_:
                    raise ValueError(f'kv_static_die ASTK_ST: no V header word pvh_{st}_{k} (needs OT_KV_PV_T)')
                fk.setdefault(f'pvh_{st}_{k}', []).append((f'astk_{st}', f'vh{k}'))
            bus(f'pve_{st}', 'kv_oneway', 256, [(f'astk_{st}', 'erd'), (f'pvw_{p_}', 'ie' if st[0] == 'W' else 'iee')])
        rec['notes'].append('astk = qkd_astk_strip_er_die (KV-WIRE2 ASTK): e-read request = fork of pvh_<st>_<k> (V header), '
                            f'e quad -> pvw in_e at ASTK_ERL {ASTK_ERL} after the fork; record astk_eread: fork + ASTK_ERL + pve stages vs the '
                            'pair header path (compiler: the pair takes in_e that many edges after vh, or pad)')
    # KV-WIRE2 SEQ: the static sequencer qkd_seq_static_s reads the attention programme and the result stream header
    if SEQ_S and 'seq' in by:
        if any(b_[0] == 'ares' or (b_[1] not in ('clock_trunk', 'reset') and ('seq', 'ar') in b_[3]) for b_ in B):
            raise ValueError('kv_static_die SEQ_S: seq.ar is still driven (ares)')
        bus('ks_prg', 'kv_oneway', PRG_W, [('kvs_attn', 'prg'), ('seq', 'prg')])
        bus('ks_arh', 'kv_oneway', ARH_W, [('kvs_attn', 'arh'), ('seq', 'ar')])
        rec['opens'][:] = [o for o in rec['opens'] if not o['where'].startswith('seq.ar ')]
        rec['notes'].append('seq = qkd_seq_static_s (KV-WIRE2 SEQ): kvn_<q> / kvn_<q>_cr / mf_<q> die edges removed with the '
                            'landing strips; prg <- kvs_attn attention programme, ar_h <- kvs_attn arh (pvfin fin header), '
                            'skw <- d2d {kvn_word_valid, kvn_word_tag}; ages: relay stages of ks_prg / ks_arh / seqst_kw '
                            '(compiler: Q push / KVN arrival / result beat slots of the core)')
    # P7 (AFAULT): the attention unit-fault tree (see AFAULT): group chain + local K / V faults, chain ends and the direct
    # lanes into kvs_attn (afr).  pvw pf = the pair fault only (kv_die splits busy / out_age into pa under AFAULT)
    if AFAULT:
        for st in STACKS:
            for s_, gg in enumerate(ORDER):
                gd = f'slg_{st}_{gg}'
                bus(f'ks_afk_{st}_{gg}', 'kv_oneway', 1, [(f'ectl_{st}_{ectl_frame(gg)}', 'kf'), (gd, 'afk')])
                if s_:
                    bus(f'ks_afc_{st}_{s_}', 'kv_oneway', 1, [(f'slg_{st}_{ORDER[s_ - 1]}', 'af__fault'), (gd, 'afu')])
            for k in range(4):
                bus(f'ks_afv_{st}_{k}', 'kv_oneway', 1, [(f'vport_{st}_{k}', 'f'), (f'slg_{st}_{2 * k}', 'afv')])
                fk[f'ks_afv_{st}_{k}'] = [(f'slg_{st}_{2 * k + 1}', 'afv')]
            bus(f'ks_afe_{st}', 'kv_oneway', 1, [(f'slg_{st}_{ORDER[-1]}', 'af__fault'), ('kvs_attn', f'ufk_{st}')])
        names = {b_[0]: b_ for b_ in B}
        for pn, (si, sp) in AFAULT_D:
            trunk = next((b_[0] for b_ in B if b_[3][0] == (si, sp) and b_[1] not in ('clock_trunk', 'reset', 'constant')), None)
            if trunk is not None and (si, sp) in (('ahub', 'hf'),) + tuple((f'astk_{st}', 'af') for st in STACKS):
                if len(names[trunk][3]) != 2:
                    raise ValueError(f'kv_static_die AFAULT: {trunk} is not point-to-point')
                fk.setdefault(trunk, []).append(('kvs_attn', pn))      # relayed branch of the sequencer's fault bus
            elif trunk is None:
                bus(f'ks_af_{pn}', 'kv_oneway', 1, [(si, sp), ('kvs_attn', pn)])
            else:
                raise ValueError(f'kv_static_die AFAULT: {si}.{sp} already drives {trunk}')
    # HOST <-> boot / ownership / ownership observer (kv_static_boot_join.HOST_DIE_JOINS + kvjf own_obs quiet)
    hostw = {'boot_pr': 143, 'boot_image_target': 4, 'boot_image_ready': 1, 'boot_image_fault': 1, 'boot_image_epoch': 16,
             'boot_image_digest': 64, 'host_launch_quiet': 1, 'host_upstream_quiet': 6}
    t = all_tiles()['kvs_ctl']
    for c, p, pi, pp, w, lo in host_joins():
        if c == 'host':
            loc_, port_ = cluster_of(pi)[2], pp
            bus(f'ks_host_{p}', 'kv_oneway', w or 1, [('kvs_ctl', f'{loc_}__{port_}'), ('host', p)])
        elif pi == 'host':
            loc_ = CTL_LOCAL[c]
            pn = f'{loc_}__{p}'
            if pn not in t['ports']:
                raise ValueError(f'kv_static_die: kvs_ctl has no open {pn} for the HOST join')
            bus(f'ks_host_{p}', 'kv_oneway', t['ports'][pn]['width'], [('host', pp), ('kvs_ctl', pn)])
            t['ports'][pn]['cls'] = 'die_join'
        elif c.startswith('rst_region'):
            rec['die_joins'].append(dict(consumer=c, producer=dj_str(pi, pp, lo, w), status='OPEN: the region roots are '
                                         'created inside the relay pass (kv_die._relays); the dly straps stay until a '
                                         'post-relay diecfg wiring pass exists (owner KVJ-G2 follow-up)'))
    # PHY (per-PC DFI words + the front / return data faces), HOST slices, kc chain
    pi_ = {}
    for i_, (bid, cl, bits, eps) in enumerate(B):
        mt = re.fullmatch(r'dp([io])_(WS|WN|ES|EN)_(\d+)', bid)
        if mt:
            pi_[bid] = mt
    for st in STACKS:
        rev = st[1] == 'S'
        for k in range(NPC):
            pc = f'kvpc_{st}_{k}'
            s = f'hsl_{st}_{k}'
            bus(f'dpi_{st}_{k}', 'phy_dfi', 289, [(f'phy_{st}', f'pi{k}'), (pc, 'pc__pi')])
            bus(f'dpo_{st}_{k}', 'phy_dfi', 328, [(pc, 'pc__po'), (f'phy_{st}', f'po{k}')])
            bus(f'dfh_{st}_{k}', 'phy_dfi', 4, [(f'phy_{st}', f'fh{k}'), (pc, 'pc__front_hbm_data')])
            bus(f'drh_{st}_{k}', 'phy_dfi', 4, [(f'phy_{st}', f'rh{k}'), (pc, 'pc__return_hbm_data')])
            if BOOT:      # note s5.6: the slice is the boot owner beside its PC (registered pins at both ends)
                for b_, pp, sp, w_, out in BOOT_HSL:
                    bus(f'{b_}_{st}_{k}', 'kv_oneway', w_, [(pc, pp), (s, sp)] if out else [(s, sp), (pc, pp)])
                continue
            bus(f'hes_{st}_{k}', 'kv_oneway', 288, [(s, 'ctrl_es'), (pc, 'pc__wes')])
            bus(f'ler_{st}_{k}', 'kv_oneway', 261, [(pc, 'pc__er'), (s, 'ctrl_er')])
            bus(f'hcv_{st}_{k}', 'kv_oneway', 1, [(pc, 'pc__completion_v'), (s, 'ctrl_completion_v')])
            bus(f'hcw_{st}_{k}', 'kv_oneway', 1, [(pc, 'pc__completion_we'), (s, 'ctrl_completion_we')])
        # kc command / fault chain (qkd_ctrl_strip_s / _sr order): S stacks kc -> pc0 .. pc31, fault pc31 .. pc0 -> kc
        order = list(range(NPC)) if rev else list(range(NPC - 1, -1, -1))
        kc = f'kc_{st}'
        prev = (kc, 'ko')
        for k in order:
            bus(f'kck_{st}_{k}', 'kv_oneway', 33, [prev, (f'kvpc_{st}_{k}', 'pc__ki')])
            prev = (f'kvpc_{st}_{k}', 'pc__ko')
        rec['notes'].append(f'kc_{st}: last PC ko unconsumed (the strip parent left it open too)')
        forder = list(reversed(order))
        bus(f'kcf0_{st}', 'constant', 1, [(f'kvpc_{st}_{forder[0]}', 'pc__fi')])
        m.setdefault('host_ties', {})[f'kcf0_{st}'] = (1, 0)
        for a, b in zip(forder, forder[1:]):
            bus(f'kcf_{st}_{b}', 'kv_oneway', 1, [(f'kvpc_{st}_{a}', 'pc__fo'), (f'kvpc_{st}_{b}', 'pc__fi')])
        bus(f'kcf_{st}_kc', 'kv_oneway', 1, [(f'kvpc_{st}_{forder[-1]}', 'pc__fo'), (kc, 'fi')])
    # the sequencer's kc words -> the kept kc heads (re-pointed from the removed strips)
    for st in STACKS:
        bus(f'kc_{st}', 'kv_oneway', 33, [('seq', f'kc_{st}'), (f'kc_{st}', 'kc')])
    rec['opens'] += [
        *([] if BOOT else [dict(where='hsl_<st>_<k>.land_es (x128, 288 b)', owner='KVJ-C3 (writer 4-lane -> PC fan-out feeds '
                                'the HOST slice)')]),
        *([] if SEQ_S else [dict(where='seq.mf_<q> (x4) / seq.kvn_<q>_cr (x4)', owner='Q-KV decision: qkd_seq_static '
             'legacy landing faces (merge fault, KVN credit) have no static producer; seq successor without them or a '
             'static source')]),
        *([] if BOOT else [dict(where='embgw.emr_<q> (x4, 521 b)', owner='KVJ-C3 / Q-KV (static emr source for the boot-only '
                                'gateway)')]),
        dict(where='host.ctrl_completion_fault', owner='KVJ-SMALL (OR of the 128 pc_path completion_fault)'),
        *([] if ASTK_ST else [dict(where='pvw_<p>.ie (1,024 b)', owner='KVE-2 / KVJ-D (ASTK e-read qkd_astk_er_tap in the '
                                   'strip successor)')]),
        *(([] if RS_PAIRS else
            [dict(where='pvfin.p0 / pvfin.p1 (534 b each: valid, beat, epoch, 512-b data)', owner='PV pair successor: '
                  'the 512-b registered RESULT TRUNK in qkd_pvw_die_t (pv_trunk_gen: the 32 column joins inject their held y '
                  'at compiled slots, beat order 0..31, exit at the strip corner facing pvfin); the current po is 16,384 b '
                  'at 32 staggered column ages (COL_D) and cannot feed one capture slot (results/arch/qwen_kv_pvfin_1017)')]) + [
           *([] if AHUB_STATIC else [dict(where='pvfin.fr (145 b: rz_valid, rz_epoch, 4 x 32-b head reciprocals)',
                owner='KVE: static hub ot_qkd_ahub_static_die_cal rz_vector / rz_epoch + the R_AGE slot (the die hub '
                'qkd_ahub = legacy ot_qwen_nearhbm_attn_hub_p has only the debug native_reciprocal, no slot / epoch)')]),
           *([] if AFAULT else [dict(where='pvfin.ff (fault, output)', owner='KVE-2: the attention unit-fault OR tree '
                                     '(attn_face unit_fault)')])]
          if PVFIN else
          [dict(where='kvs_attn.attn_face__f_valid / f_data / f_epoch', owner='KVE: the PV final join '
                'ot_qwen_tp8_pv256_finalize_static_cal (pvw_0/1 po -> 16,384 b) has RTL but no die element / kit')]),
        *([] if AFAULT else [dict(where='kvs_attn.attn_face__unit_fault (10 b)', owner='KVE-2: the 10 sticky service-unit '
             'faults (stacks, hub, PV pairs pf, finalize, V req, e-read, rz-late, K identity, legacy pv, stack) need a die '
             'fault OR tree')]),
        dict(where='kvs_attn.attn_root PV_LEAD / attn_face RESULT_RELAY', owner='compiler: price from this plan (ks_pvst '
             'relay stages) and regenerate the tile (RTL defaults 0 / default now)'),
    ]


def dj_str(i, p, lo, w):
    return f'{i}.{p}' + (f'[{lo + w - 1}:{lo}]' if lo is not None and w else '')


def _clocks_resets(m, B, add, rec):
    """every tile clock port joins its region's trunk as its own entry; resets join the die / HBM reset trees; identity
    straps are die-top constants (class identity strap)"""
    ties = m.setdefault('host_ties', {})
    extra = defaultdict(list)
    for d, t in all_tiles().items():
        reg = d.split('_')[1] if d.startswith(('kvpc_', 'slg_')) else 'c'
        for pn, v in t['ports'].items():
            if v['cls'] == 'clock':
                extra[f'clk_core_{reg}' if v['domain'] == 'core' else f'clk_hbm_{reg}'].append((d, pn))
            elif v['cls'] == 'reset':
                extra['rst_die' if v['domain'] == 'core' else 'rst_hbm'].append((d, pn))
            elif v['cls'] == 'strap':
                cb = f'kvsid_{d}__{pn}'
                add((cb, 'constant', v['width'], [(d, pn)]))
                ties[cb] = (v['width'], v['value'])
    if PVFIN and any(i.name == 'pvfin' for i in m['insts']):
        extra['clk_core_c'].append(('pvfin', 'ck'))
        extra['rst_die'].append(('pvfin', 'rst_n'))
    for st in STACKS:
        kc = f'kc_{st}'
        extra[f'clk_core_{st}'].append((kc, 'ck'))
        extra[f'clk_hbm_{st}'].append((kc, 'pll_hbm'))
        extra['rst_die'].append((kc, 'rsi'))
        extra['rst_hbm'].append((kc, 'hrst'))
    names = {b_[0] for b_ in B}
    for k_ in extra:
        if k_ not in names:
            if k_ == 'clk_hbm_c':
                raise ValueError('kv_static_die: a centre tile has an HBM clock entry')
            raise ValueError(f'kv_static_die: no trunk {k_}')
    for i_, (bid, cl, bits, eps) in enumerate(B):
        if bid in extra:
            B[i_] = (bid, cl, bits, list(eps) + [e for e in extra[bid] if e not in eps])


# ------------------------------------------------------------------------------------------------ floorplan
def place(m, K, geo, F):
    """homes: PCs at the old controller slots (abut the PHY), the HOST slices next, the group tiles level with their four
    PCs up to the V port channel, kc heads at each strip's outer end, centre tiles beside their consumers."""
    by = {i.name: i for i in m['insts']}
    GX, GY = K.GX, K.GY
    up = K.up
    SH = K.SHAVE
    pcw, pch = 270.0, 302.4
    gap = 21.6
    for st in STACKS:
        cx, cy, cw, ch, co, cm = geo[st]['ctrl']
        lx, ly, lw, lh = geo[st]['land']
        west = st[0] == 'W'
        phy = by[f'phy_{st}']
        # PC column: from the PHY's controller face outward
        x_pc = up(phy.x + phy.w + 0.0, GX) if west else up(phy.x - pcw, GX) - GX
        if not west:
            x_pc = phy.x - pcw
        for k in range(NPC):
            yc = cy + PC_PITCH * k + PC_PITCH / 2
            y = up(yc - pch / 2, GY)
            kind = 'pc_h' if k == 0 else 'pc'
            m['insts'].append(F.Inst(f'kvpc_{st}_{k}', KIND_MASTER[kind], round(x_pc, 4), round(y, 4), pcw - SH,
                                     pch - SH, 'R0' if west else 'MY', kind='static', region='strip', domain='hbm'))
        # HOST slice column moves next to the PCs (closes the removed CDC / write-leaf column the PC <-> slice words crossed)
        hs = [by[f'hsl_{st}_{k}'] for k in range(NPC)]
        x_hs = up(x_pc + pcw + gap, GX) if west else up(x_pc - gap - hs[0].w - GX, GX)
        for h in hs:
            h.x = round(x_hs, 4)
        # group tiles: from the slice column to the V port channel
        vps = [by[f'vport_{st}_{k}'] for k in range(4)]
        ects = [by[f'ectl_{st}_{e}'] for e in range(8)]
        # inner edge = the old landing strip's inner edge: the landing <-> V port / engine relay channel stays as planned
        # KV-PLAN3 10-18 OT_KV_KV_CHAN_EXTRA (um): the group tile gives that much width to the K / V channel on its
        # engine side (h3: the 190-um channel beside slg_WS_7 held ~250 small relays and no 1,056-b pvrs relay fitted)
        kx_ = float(os.environ.get('OT_KV_KV_CHAN_EXTRA', '0'))
        if west:
            x_g = up(max(x_hs + hs[0].w + gap, lx + lw - 369.0), GX)    # W of the groups: a control channel
            gw = round(lx + lw - 60.0 - kx_ - x_g, 4)                 # E of them: the K / V channel widened by 60 um
        else:
            x_g = lx + 60.0 + kx_
            gw = round(min(x_hs - gap - x_g, 309.0 - kx_), 4)
        GH = 1188.0                 # group tile height: 324-um gaps between groups (relay spots + the stack fan slot)
        for g in range(8):
            idx = ORDER.index(g)
            y0 = up(cy + PC_PITCH * 4 * idx + (PC_PITCH * 4 - GH) / 2, GY)
            m['insts'].append(F.Inst(f'slg_{st}_{g}', KIND_MASTER['grp_h' if (FANFOLD and idx == 0) else 'grp'], round(x_g, 4), round(y0, 4), gw - SH, GH - SH,
                                     'R0' if west else 'MY', kind='static', region='strip', domain='hbm'))
        fh = 172.8                  # the stack fan: between groups at slots 3 and 4 (the stack middle)
        yf = up(cy + PC_PITCH * 16 - fh / 2, GY)
        if not FANFOLD:     # decision 2 (FANFOLD): the fan lives in the stack root
            m['insts'].append(F.Inst(f'kvs_fan_{st}', 'qkd_kvs_fan', round(x_g, 4), round(yf, 4), gw - SH, fh - SH,
                                     'R0' if west else 'MY', kind='static', region='strip', domain='core'))
        # kc head at the strip's outer end (S stacks: below PC 0; N stacks: above PC 31), on the PC column
        kw, kh = 64.8, 43.2
        ky = cy - kh - 10.8 if st[1] == 'S' else cy + PC_PITCH * NPC + 10.8
        m['insts'].append(F.Inst(f'kc_{st}', 'qkd_ctrl_kc', round(up(x_pc + pcw / 2 - kw / 2, GX), 4), round(up(ky, GY), 4),
                                 kw - SH, kh - SH, 'R0', kind='static', region='strip', domain='hbm'))
    # centre tiles: free spots nearest their anchors
    d2d = by['d2d_kv']
    host = by['host']
    pv = by.get('pvw_1')
    # the control tile sits in the free top-left band (room for its 32 group chains' first relays), W of the HOST row
    # the control tile spans the centre column between the sequencer and the HOST root: both die sides leave it without
    # crossing the PV / HOST column (the only W <-> E crossings up there are narrow)
    sq = by['seq']
    anchors = dict(kvs_ctl=(host.x + host.w / 2, (sq.y + sq.h + host.y) / 2), kvs_emb=(d2d.x - 40.0, d2d.y + d2d.h / 2),
                   kvs_attn=((pv.x - 500.0) if pv else d2d.x, (pv.y + pv.h - 200.0) if pv else d2d.y - 400.0))   # W of the N pair's top: the pair-top gap stays a crossing
    hro = []
    if HROOT:
        # KV-PLAN decision 1: the S half root at the stack seam (where the S stacks' PC 31 chain ends sit), W of the PV
        # column in the seam band between the S and N attention stacks; the N half root at the top of the N stacks
        # (their PC 31 chain ends), W of the N pair's top.  Each serves its own two stacks.
        # the S roots sit at their stack's own seam end (PC 31 / the group column's control channel), NOT beside the PV
        # column: the seam band next to the column is the V word funnel (vport -> pvfork, pvin_*), which a root's four
        # words starved of relay spots (b3110: pvin_ES_3 / pvin_EN_2 at the column's seam corners)
        by = {i.name: i for i in m['insts']}                               # now with the static strip tiles
        for st in ('WS', 'ES'):
            gd, pc, pn = by[f'slg_{st}_7'], by[f'kvpc_{st}_31'], by[f'kvpc_{st[0]}N_0']
            anchors[f'kvs_hroot_{st}'] = (gd.x + gd.w / 2, (pc.y + pc.h + pn.y) / 2)
        for st in ('WN', 'EN'):                                            # above the stack's PC 31 / control channel
            gd, pc = by[f'slg_{st}_0'], by[f'kvpc_{st}_31']
            anchors[f'kvs_hroot_{st}'] = (gd.x + gd.w / 2, pc.y + pc.h + 400.0)
        hro = [(f'kvs_hroot_{st}', 'hroot') for st in ('WS', 'ES', 'WN', 'EN')]
    order = [('kvs_ctl', 'ctl'), ('kvs_emb', 'emb'), ('kvs_attn', 'attn')]
    if ATTN_AT_D2D:
        # QXF-SEAMK 10-18 (TOKEN-XDIE-QWEN F6 placement): kvs_attn against the D2D end's W face, kvs_emb W of it
        anchors.update(d2d_side_anchors(d2d, FRAME['attn'], FRAME['emb']))
        order = [('kvs_ctl', 'ctl'), ('kvs_attn', 'attn'), ('kvs_emb', 'emb')]
    for nm, kind in order + hro:
        w, h = FRAME[kind]
        x, y = free_spot(m, w, h, anchors[nm], GX, GY)
        m['insts'].append(F.Inst(nm, KIND_MASTER[kind], round(x, 4), round(y, 4), w - SH, h - SH, 'R0', kind='static',
                                 region='io', domain='core'))
    # KV-PLAN-FIN: the stream final join between the two PV pair strips (pvw_0 strip = its top, pvw_1 strip = its bottom),
    # W of the attention hub (the reciprocal source): both 512-b pair streams and rz are ~0.5-1.5 mm hops
    ah = by.get('ahub')
    if PVFIN and ah is not None and 'pvw_0' in by and pv is not None:
        w, h = PVFIN_FRAME
        ys = (by['pvw_0'].y + by['pvw_0'].h + pv.y) / 2
        x, y = free_spot(m, w, h, (ah.x - w / 2 - 30.0, ys), GX, GY)
        m['insts'].append(F.Inst('pvfin', 'qkd_pvfin', round(x, 4), round(y, 4), w - SH, h - SH, 'R0', kind='static',
                                 region='io', domain='core'))


# QXF-SEAMK 10-18 (OT_KV_ATTN_AT_D2D=1, default off): kvs14c placed kvs_attn W of the N PV pair top, 2.0 mm S / 0.7 mm W of
# the D2D end, so its four d2d record bundles ran 9-11 relays each way (rx 11, tx slot 9, tx 11: 22 of the +32 exposed
# cycles a decode layer, TOKEN-XDIE-QWEN F6).  With the knob kvs_attn sits W of the HOST root, its N face level with the
# D2D end's bottom (OT_KV_ATTN_D2D_TOP x the end's height above its bottom, default 0: at 0.48 -- N face on the end's
# rx_payload row, seam 0/1/0 -- the kvs_attn -> seq prg word found no relay spot in the HOST / D2D gap, planner dry run
# qxf-seamk caseB), its E face (attn__tx_valid / tx_payload) one halo W of the end's W face, and kvs_emb moves W of it on
# the same row (its embedding row word becomes a 1-2 stage hop, once a token).  kvs14c pin geometry -> rx_record 1,
# tx_slot 0, tx_record 0 stages
# (test_kv_bundle_eq.test_attn_at_d2d_pin_hops); the S-going kvs_attn words (ahs / pvst / pvfst / fin / acal) grow by
# ~1.5-2 mm.  MEASURED (planner dry runs, results/rtl/xdie_qwen_1018/qxf_seamk/planner_dryrun.log): the seam drops to
# rx 1 / tx slot 1 / tx 0 (31 -> 2 stages, vehicle roundtrip 1835 -> 1814) but the S-going words detour around the HOST /
# kvs_ctl / seq column: ahs 46 -> 60, pvst 37 -> 85, pvfst 40 -> 65, fin 45 -> 51, acal +2..+10.  The start / result legs
# sit inside the KV service window, so the net is NOT a gain on this floorplan: default OFF, not proposed for adoption
# until the start words get a direct channel S (KV-PLAN4 floorplan item).
ATTN_AT_D2D = os.environ.get('OT_KV_ATTN_AT_D2D', '0') == '1'
ATTN_D2D_TOP = float(os.environ.get('OT_KV_ATTN_D2D_TOP', '0.0'))


def d2d_side_anchors(d2d, attn_wh, emb_wh, halo=21.6, top=None):
    """centre anchors {kvs_attn, kvs_emb} beside the D2D end d2d (x, y, w, h): kvs_attn's E face one halo W of the end's
    W face, its N face at top x the end's height; kvs_emb one halo W of kvs_attn, same row"""
    aw, ah = attn_wh
    ew, _ = emb_wh
    yt = d2d.y + (ATTN_D2D_TOP if top is None else top) * d2d.h
    return dict(kvs_attn=(d2d.x - halo - aw / 2, yt - ah / 2), kvs_emb=(d2d.x - 2 * halo - aw - ew / 2, yt - ah / 2))


def free_spot(m, w, h, anchor, GX, GY, halo=21.6, rmax=4000.0):
    """the on-grid w x h spot nearest (Manhattan, centre) to anchor that keeps a halo to every frame / keep-out"""
    ax, ay = anchor
    W, H = m['die']['w'], m['die']['h']
    x0, x1, y0, y1 = ax - rmax - w, ax + rmax + w, ay - rmax - h, ay + rmax + h
    occ = [(i.x - halo, i.y - halo, i.x + i.w + halo, i.y + i.h + halo) for i in m['insts']]
    occ += [(x - halo, y - halo, x + ww + halo, y + hh + halo) for _, x, y, ww, hh in m.get('keepouts', [])]
    occ = [r for r in occ if not (r[2] < x0 or r[0] > x1 or r[3] < y0 or r[1] > y1)]
    step = 21.6                          # candidate pitch (the routing cell); positions snap to the placement grid
    n = int(rmax / step)
    cands = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x = round((ax - w / 2 + i * step) / GX) * GX
            y = round((ay - h / 2 + j * step) / GY) * GY
            cands.append((abs(x + w / 2 - ax) + abs(y + h / 2 - ay), x, y))
    cands.sort()
    for _, x, y in cands:
        if x < 21.6 or y < 21.6 or x + w > W - 21.6 or y + h > H - 21.6:
            continue
        if any(not (x + w <= a or x >= c or y + h <= b or y >= d) for a, b, c, d in occ):
            continue
        return x, y
    raise ValueError(f'kv_static_die: no free {w}x{h} spot within {rmax} um of {anchor}')


_ECTL_FACE = {'si': 'E', 'so': 'E', 't0': 'S', 'e0': 'S', 'e1': 'S', 's0': 'S', 's1': 'S', 't1': 'N', 'e2': 'N', 'e3': 'N',
              's2': 'N', 's3': 'N'}


# OT_KV_TILE_KITS: complete canonical face map of the kit tiles (die frame = kit; shared by kvs_tile_kits.py).  Group (R0 =
# W stacks, MY = E stacks): W = control channel (its 4 PCs' words, PC pass words, clocks / resets / identity straps), E =
# K / V channel, N / S = the folded fan chain.  PC: W = the PHY's DFI face (abutted), E = the HOST slice / control channel
# (clocks, resets, straps, er, completion), N / S = the PC chain + group words.  Root (R0 for all four): N = the control /
# embedding tile words, S = the stack (group chain + PC chain head + return train), E = the eight ECTL frames, W = clock.
KIT_FACE = {
    'qkd_kvs_grp': dict(kreq='E', vreq='E', rsp='E', krsp='E', i_ctl='N', o_ctl='N', o_dn='S', i_up='S'),
    'qkd_kvs_pc': dict(i_next='N', o_next='N', pc__ki='N', i_grp='N', o_grp='N', x__est__0_1='N', pc__fo='N',
                       o_prev='S', i_prev='S', pc__ko='S', pc__fi='S',
                       pc__pi='W', pc__po='W', pc__front_hbm_data='W', pc__return_hbm_data='W'),
    'qkd_kvs_hroot': dict(i_ctl='N', o_ctl='N', o_emb='N', o_pc='S', i_r='S', o_ch0='S', i_g='S', o_kg='E',
                          **{f'o_c{e}': 'E' for e in range(8)}),
}
if DOMSPLIT:     # KV-DOMSPLIT: the hck half of a split word sits beside its ck half (same face)
    KIT_FACE['qkd_kvs_pc'].update(i_grp_h='N', o_grp_h='N')
KIT_FACE['qkd_kvs_grp_h'] = KIT_FACE['qkd_kvs_grp']
KIT_FACE['qkd_kvs_pc_h'] = KIT_FACE['qkd_kvs_pc']
KIT_DEFAULT_FACE = dict(qkd_kvs_grp='W', qkd_kvs_grp_h='W', qkd_kvs_pc='E', qkd_kvs_pc_h='E', qkd_kvs_hroot='W')


def pin_face(master, port):
    master = master.removesuffix('_private0')
    if KITS and master in KIT_FACE:
        return KIT_FACE[master].get(port, KIT_DEFAULT_FACE[master])
    return _pin_face(master, port)


def _pin_face(master, port):
    """canonical (R0) face of a static tile's port, or None (auto): the K / V words on the group's engine-side face (the
    landing <-> V port / ECTL channel), every control word (fan, PC bundles) on its PHY-side face (the control channel
    between the HOST slices and the groups), so the control traffic never takes the K / V channel's relay spots"""
    master = master.removesuffix('_private0')
    if master == 'qkd_ectlk':
        return _ECTL_FACE.get(port, 'W')
    if master in ('qkd_kvs_grp', 'qkd_kvs_grp_h'):
        if port in ('krsp', 'kreq', 'rsp', 'vreq', 'afk', 'afv'):
            return 'E'
        if FANFOLD and port in ('i_ctl', 'o_ctl', 'o_dn', 'i_up'):
            # KV-PLAN3: the folded fan chain runs slot 7 (top, the root's end) -> slot 0 down the stack: the down word
            # enters N / leaves S, the up gather enters S / leaves N (on the W face they were 2,327 um per hop: the
            # ends of a 1,188-um face, ks_slg_WN_7__o_dn in v_432)
            return 'N' if port in ('i_ctl', 'o_ctl') else 'S'
        if port in ('afu', 'af__fault'):
            # KV-PLAN3 merge: the fault chain runs slot s-1 -> s (up the stack): enter S, leave N (facing neighbours)
            return 'S' if port == 'afu' else 'N'
        if port.startswith(('i_', 'o_')):
            return 'W'
    if master == 'qkd_kvs_fan':
        return 'W'
    if master in ('qkd_kvs_pc', 'qkd_kvs_pc_h'):
        # KV-PLAN3 10-17: the PC chain words between vertically stacked neighbours (pitch 378 um, PC k+1 above PC k) on
        # the facing N / S faces: auto-placed on a side face they were 515.7 um per hop (> reach) once the pin-hinted
        # re-plan stopped, 114 of the 127 unrepaired hops (t_302).  N: i_next 779 + o_next 299 + pc__ki 33, S: the
        # mirror set = 1,111 b on a 270-um face (4.1 /um)
        f_ = dict(i_next='N', o_next='N', pc__ki='N', o_prev='S', i_prev='S', pc__ko='S', i_grp='N', o_grp='N',
                  i_grp_h='N', o_grp_h='N').get(port)
        if f_:
            return f_
    if ASTK_ST and master in ('qkd_astk', 'qkd_astk_n') and (port in ('erd', 'cal') or re.fullmatch(r'vh\d', port)):
        # KV-WIRE2 ASTK: the e-read words on the strip's S|N seam end (the pvfork V headers and the pair's in_e pins are
        # there); cal from kvs_attn (die top): N face (w1/w2: auto faces left ks_acal_ES / pve_WS 48 / 39 stages)
        if port == 'cal':
            return 'N'
        return 'N' if master == 'qkd_astk' else 'S'
    if KVS_CK1 and master in KVS_FACES:   # KITS-A kits physical/ref_tile/qkd_kvs_{ctl,attn,emb}: the kit uses these faces
        return kvs_face(master, port)
    if master == 'qkd_pvfin':          # kit qkd_pv_fin_s faces
        return dict(p0='S', p1='N', fo='W', ff='W').get(port, 'E')
    return None



# KV-INTEG/KITS-A 10-18: canonical (R0) faces of the singleton tiles (die plan m1 placement: kvs_ctl in the centre band
# between the sequencer (S) and the HOST root / D2D end (N), the W / E stack roots' words leave across the top band W / E;
# kvs_attn W of the N PV pair top, D2D end to its N / NE, the PV final join and the pair strips S; kvs_emb W of the D2D
# end (E), the W stack roots' return trains W, the E ones + the ctl word S).  Rules by port name so a regenerated tile
# (FAULT / BOOT add or change ports) gets faces mechanically: first match wins, the last entry is the default.
KVS_FACES = {
    'qkd_kvs_ctl': [('W', r'^[io]_hroot_W[SN]$'), ('E', r'^[io]_hroot_E[SN]$'), ('S', r'^(lp|o_attn|ck|rst_n)$'),
                    ('N', r'.')],
    'qkd_kvs_attn': [('N', r'^d2d__(srx|rx_payload|att_tx_slot|att_tx_kind|att_tx_beat)$'),
                     ('E', r'^(attn__tx_valid|attn__tx_payload|i_ctl)$'), ('S', r'.')],
    'qkd_kvs_emb': [('W', r'^i_hroot_W[SN]$'), ('S', r'^(i_hroot_E[SN]|i_ctl|ck|rst_n)$'), ('E', r'.')],
}


def kvs_face(master, port):
    for f_, rx in KVS_FACES[master]:
        if re.search(rx, port):
            return f_
    raise ValueError(f'kvs_face: no face for {master}.{port}')


def _pc_pair(p):
    """group W-face PC word pair index j of i_pc<j> / o_pc<j> (and the DOMSPLIT hck halves i_pc<j>_h / o_pc<j>_h)"""
    m_ = re.fullmatch(r'[io]_pc(\d)(?:_h)?', p)
    return int(m_.group(1)) if m_ else None


def face_order(master, face, ports):
    """KV-PLAN3: along-face order (from the face origin) of a static tile's pins, or the given order.  The group's W face
    carries its four PCs' words: interleave i_pc<j> / o_pc<j> bottom-up so pair j sits level with PC j (PC k of the
    slot = 4 slot + j, bottom-up; the even spread puts pair j's centre within ~125 um of PC j's centre)"""
    master = master.removesuffix('_private0')
    if KITS and master in ('qkd_kvs_grp', 'qkd_kvs_grp_h') and face == 'W':
        # kit: PC pairs 0 / 1 below, the clocks / resets / straps / pass words mid-face (beside the register mass), 2 / 3 above
        def key(p):
            j = _pc_pair(p)
            if j is not None:
                return (j + (1 if j >= 2 else 0), p[0] == 'o', p)
            return (2, p not in ('ck', 'hck'), p)
        return sorted(ports, key=key)
    if master in ('qkd_kvs_grp', 'qkd_kvs_grp_h') and face == 'W':
        def key(p):
            j = _pc_pair(p)
            if j is not None:
                return (j, p[0] == 'o', p)
            return (99, False, p)
        return sorted(ports, key=key)
    if master in ('qkd_kvs_pc', 'qkd_kvs_pc_h') and face == 'N':
        # the group words at the N face's E end (canonical E = toward the group column, through the slice gap):
        # k2 left ks_kvpc_EN_29__o_grp at 633 um with o_grp mid-face
        return sorted(ports, key=lambda p: (p in ('i_grp', 'o_grp', 'i_grp_h', 'o_grp_h'), p.startswith('o_grp'), p))
    if master in ('qkd_kvs_grp', 'qkd_kvs_grp_h') and face == 'E' and os.environ.get('OT_KV_GRP_RSP_LOW', '0') == '1':
        # variant: the V response word rsp on the lower half (odd groups: their V port sits just below the group)
        return sorted(ports, key=lambda p: (p != 'rsp', p))
    return ports


def waypoints(m, a, pa, b, pb):
    """KVJ-G2b: planned corridor of a long control-tile word (die points, in order from a to b), or None (shortest path).
    ctl <-> S-stack chain root (PC 31) / stack fan: down the PV pair's side channel (W / E of the centre column) to the
    stack seam row (the free band between the S and N stacks), then along it to the stack's control channel (between the
    HOST slice column and the groups) and down that channel to the fan.  ctl <-> N-stack fan: across the top band into the
    N stack's control channel.  The stack's K / V channel (groups <-> V ports / ECTL, 1 kb words) keeps its relay spots."""
    wpm = os.environ.get('OT_KV_STATIC_WP', 'all')        # all | none | chain (diagnostic corridor variants)
    if wpm == 'none':
        return None
    if HROOT:
        return _hroot_waypoints(m, a, pa, b, pb)
    ends = {(a, pa), (b, pb)}
    other = [e for e in ends if e[0] != 'kvs_ctl']
    if len(other) != 1 or not any(e[0] == 'kvs_ctl' for e in ends):
        return None
    inst, port = other[0]
    mt = re.fullmatch(r'kvs_fan_(WS|WN|ES|EN)', inst)
    mp = re.fullmatch(r'kvpc_(WS|ES)_31', inst)
    if not (mt or mp) or (wpm == 'chain' and not mp):
        return None
    st = (mt or mp).group(1)
    by = {i.name: i for i in m['insts']}
    ctl, pv = by['kvs_ctl'], by.get('pvw_1')
    pv144 = m['geo'].get('pv144') or {}
    if pv is None or 'side_channel_um' not in pv144:
        return None
    west = st[0] == 'W'
    sw, se = pv144['side_channel_um'][:2]
    lx = pv.x - sw / 2 if west else pv.x + pv.w + se / 2
    nst = st[0] + 'N'
    yseam = (by['pvw_0'].y + by['pvw_0'].h + by[f'kvpc_{nst}_0'].y) / 2
    hs, gd = by[f'hsl_{st}_0'], by[f'slg_{st}_0']
    xcc = (hs.x + hs.w + gd.x) / 2 if west else (gd.x + gd.w + hs.x) / 2       # the stack's control channel
    ytop = by[f'kvpc_{nst}_31'].y + by[f'kvpc_{nst}_31'].h + 60.0
    if mp:                                  # the S chain root word: PV side channel -> seam row -> PC 31
        pts = [(lx, ctl.y - 100.0), (lx, yseam)]
    elif st[1] == 'S':                      # the S fan: PV side channel -> seam row -> its own control channel
        pts = [(lx, ctl.y - 100.0), (lx, yseam), (xcc, yseam)]
    else:
        pts = [(xcc, ytop)]
    return pts if a == 'kvs_ctl' else list(reversed(pts))


def _hroot_waypoints(m, a, pa, b, pb):
    """HROOT: an S stack root's words to / from the top tiles (ctl, emb) take the N stack's own CONTROL channel (between
    its HOST slice column and its landing groups) straight down to the seam root: never the PV column's side channels,
    whose seam corners are the V word funnel (vport -> pvfork).  OT_KV_HROOT_WP=side: the side channel variant."""
    ends = {a, b}
    hr = next((e for e in ends if e in ('kvs_hroot_WS', 'kvs_hroot_ES')), None)
    if hr is None or not ends & {'kvs_ctl', 'kvs_emb'}:
        return None
    by = {i.name: i for i in m['insts']}
    h = by[hr]
    top = by['kvs_ctl'] if 'kvs_ctl' in ends else by['kvs_emb']
    nst = hr[-2] + 'N'
    if os.environ.get('OT_KV_HROOT_WP', 'cc') == 'side':
        pv, pv144 = by.get('pvw_1'), m['geo'].get('pv144') or {}
        if pv is None or 'side_channel_um' not in pv144:
            return None
        sw, se = pv144['side_channel_um'][:2]
        lx = pv.x - sw / 2 if hr.endswith('WS') else pv.x + pv.w + se / 2
        pn = by[f'kvpc_{nst}_0']
        ys = (h.y + h.h + pn.y) / 2 if pn.y > h.y + h.h else h.y + h.h / 2
        pts = [(lx, top.y - 100.0), (lx, ys), (h.x + h.w / 2, ys)]
    else:
        hs, gd = by[f'hsl_{nst}_0'], by[f'slg_{nst}_0']
        xcc = (hs.x + hs.w + gd.x) / 2 if hr[-2] == 'W' else (gd.x + gd.w + hs.x) / 2
        ytop = by[f'kvpc_{nst}_31'].y + by[f'kvpc_{nst}_31'].h + 60.0
        pts = [(xcc, ytop), (xcc, h.y + h.h + 60.0)]
    return pts if a != hr else list(reversed(pts))


# ------------------------------------------------------------------------------------------------ record / report
def record(m):
    """plan record: tiles, bus count, relay stages of the static buses, open inputs with owners"""
    t = all_tiles()
    opens = defaultdict(lambda: dict(instances=0))
    for d, tt in t.items():
        for pn, v in tt['ports'].items():
            if v['cls'] == 'open':
                r = opens[(KIND_MASTER[tt['kind']], pn)]
                r.update(master=KIND_MASTER[tt['kind']], port=pn, width=v['width'], owner=v.get('owner'))
                r['instances'] += 1
    st = m.get('relay_stages', {})
    ks = {b: s for b, s in st.items() if b.startswith(('ks_', 'pvvq_', 'pvrs_', 'krq_', 'krs_', 'kck_', 'kcf_', 'hes_',
                                                        'ler_', 'hcv_', 'hcw_', 'les_', 'hler_')) or '__f' in b and b.split('__f')[0].startswith('ks_')}
    return dict(schema='opentallas.qwen_kv.static_die.v1', rtl=RTL_FILE,
                rtl_sha256=hashlib.sha256((ROOT / RTL_FILE).read_bytes()).hexdigest() if (ROOT / RTL_FILE).exists() else None,
                tiles={k: sum(1 for x in t.values() if x['kind'] == k) for k in GEN_KINDS},
                join_instances=len(ins()), unpriced=_G.get('unpriced'),
                static_buses=len(ks), static_relay_stages_max=max(ks.values()) if ks else 0,
                open_tile_inputs=sorted(opens.values(), key=lambda r: (r['owner'] or '', r['master'], r['port'])),
                **({'ahub_ages': ahub_ages(m)} if AHUB_STATIC and 'ks_ahs' in m.get('relay_stages', {}) else {}),
                attn_fault=afault_latency(m),
                face_land=dict(enabled=FACE_LAND, selected=sorted(FACE_LAND_SEL),
                               tiles={k: v for k, v in FACE_LAND_TILES.items() if k in FACE_LAND_SEL},
                               note='views bound only when CLOSED (lanes/HKV-RSTCAP.md)'),
                attn_landing=dict(enabled=ATTN_LAND, added_edges=ATTN_LAND_EDGES if ATTN_LAND else {},
                                  codec_edges=2 if ATTN_LAND else 1,
                                  schedule_binding='compiler must compose launch edges with actual die relay/land ages'),
                **({'astk_eread': astk_eread(m), 'astk_internal': dict(
                    expanded=ASTK_EXPAND, relay_edges=ASTK_RL, z_stride=ASTK_Z_STRIDE,
                    eread_edges=ASTK_ERL, fault_join_edges=1 if ASTK_EXPAND else 0,
                    owner_issue_edges=[2 + e * (2 + ASTK_RL) for e in range(8)] if ASTK_EXPAND else None,
                    calendar_status='MEASURED results/arch/qwen_kv_die/hkv_astk_calendar_1018/astk_calendar_law.json (kv_static_programme applies it under OT_KV_ASTK_EXPAND=1; T8192 slot +42 edges)' if ASTK_EXPAND else 'LEGACY',
                    eread_law='7 + 7*(2+RL): 8 owner leaves with input/output flops and resettable inter-owner relays'
                              if ASTK_EXPAND else 'EP3 + request2 + response2')} if ASTK_ST else {}),
                **{k: v for k, v in m.get('static_die', {}).items()})


# KV-ERTAP 2026-10-18: qkd_astk_er_tap_st registers every pin (route b18fa696b NEEDS_RTL, I2O hold): read pin -> response
# pin = the EP's ERL 3 + 2 request-side + 2 response-side pin-register edges.
ASTK_ERL = 7 + 7 * (2 + ASTK_RL) if ASTK_EXPAND else 7


def astk_eread(m):
    """KV-WIRE2 ASTK: per V port, the e quad's arrival at the PV pair's in_e relative to its V header vh at the pair:
    e_after_header = fork(vh -> astk) + ASTK_ERL + pve - header(pvfork -> pair) edges (relay stages; the pair must take in_e
    that many edges after vh, or the shorter path is padded: compiler / pair owner)."""
    st_, fs_, fk = m.get('relay_stages'), m.get('fork_stages', {}), m.get('forks', {})
    if st_ is None:
        return None
    out = {}
    for st in STACKS:
        for k in range(4):
            tr, ld = f'pvh_{st}_{k}', (f'astk_{st}', f'vh{k}')
            if ld not in fk.get(tr, []):
                continue
            fb = f'{tr}__f{fk[tr].index(ld)}'
            f_ = fs_.get(fb, st_.get(fb, 0))
            out[f'{st}_{k}'] = dict(header=st_.get(tr, 0), fork=f_, erl=ASTK_ERL, pve=st_.get(f'pve_{st}', 0),
                                    e_after_header=f_ + ASTK_ERL + st_.get(f'pve_{st}', 0) - st_.get(tr, 0))
    return out


def ahub_ages(m, pv_lead=0, stack_start_lag=None):
    """KV-INTEG/AHUB: qkd_ahub_static_dw parameters from the plan's relay stages (D = registered die relay stages,
    pin registers excluded; bench tb_qkd_ahub_static_dw proves both formulas edge-exact):
      FR_OFS   = D(ks_pvfst) - PV_LEAD - D(ks_ahfr) - D(ks_ahs) - 1   -> fr lands on pvfin's R slot (cal R after start_pv)
      AP_OFS_s = 2 + L_s + D(ap_s) - D(ks_ahs)  (ap pin flops)         -> hub input ages of stack s = the native
                                                                          service's LMAX / Z input ages
    L_s = the stack's start lag behind the attention root's start_qk (compiler; 0 if not given).  The hub's am word
    reaches astk_s L_h + D(am_s) - L_s edges after the service's (L_h = D(ks_ahs) + 1): the compiler's EXP_START must
    cover it (am_lag_edges)."""
    st = m.get('relay_stages', {})
    lag = stack_start_lag or {}
    dh, df, dp = st.get('ks_ahs', 0), st.get('ks_ahfr', 0), st.get('ks_pvfst', 0)
    lh = dh + 1
    ap = {s: 2 + lag.get(s, 0) + st.get(f'ap_{s}', 0) - dh for s in STACKS}   # KV-AHUBDW: + 1 = the hub's ap pin flops
    return dict(schema='opentallas.qwen_kv.ahub_ages.v1', module='qkd_ahub_static_dw', file=AHUB_FILE,
                relays=dict(ks_ahs=dh, ks_ahfr=df, ks_pvfst=dp, **{f'ap_{s}': st.get(f'ap_{s}', 0) for s in STACKS},
                            **{f'am_{s}': st.get(f'am_{s}', 0) for s in STACKS}),
                PV_LEAD=pv_lead, FR_OFS=dp - pv_lead - df - dh - 1,
                AP_OFS=[ap[s] for s in STACKS], AP_OFS_hex='{' + ', '.join(f"16'h{ap[s] & 0xffff:04x}" for s in reversed(STACKS)) + '}',
                am_lag_edges={s: lh + st.get(f'am_{s}', 0) - lag.get(s, 0) for s in STACKS},
                stack_start_lag={s: lag.get(s, 0) for s in STACKS},
                bench='tools/qwen_kv_die/ahub_static_dw_bench.sh (results/rtl/qwen_kv_static_ahub_1018)')


def afault_latency(m):
    """P7: per fault source, the edges from its fault flop to attn_face.unit_fault (= the afr output): relay stages of
    every die bus on its path (m['relay_stages'] / m['fork_stages'], None before the relay pass) + one edge per
    registered node (group chain nodes, the root pin register).  The compiler takes the max per lane."""
    st_, fs_ = m.get('relay_stages'), m.get('fork_stages', {})
    if not AFAULT:
        return None

    def rs(b):
        if st_ is None:
            return None
        return fs_[b] if b in fs_ else st_.get(b, 0)

    def tot(*xs):
        return None if any(x is None for x in xs) else sum(xs)
    fk = m.get('forks', {})
    lanes, leaves = {}, {}
    for k, (pn, (si, sp)) in enumerate(AFAULT_D):
        trunk = next((b_ for b_, v in fk.items() if ('kvs_attn', pn) in v), None)
        bid = f'{trunk}__f{fk[trunk].index(("kvs_attn", pn))}' if trunk else f'ks_af_{pn}'
        leaves[f'{si}.{sp}'] = dict(lane=k, buses=[bid], latency=tot(rs(bid), 1))
    for st in STACKS:
        lane = len(AFAULT_D) + (0 if st[0] == 'W' else 1)
        down = {}                                        # slot -> edges from that node's output to unit_fault
        acc = tot(rs(f'ks_afe_{st}'), 1)
        for s_ in reversed(range(8)):
            down[s_] = acc
            acc = tot(acc, rs(f'ks_afc_{st}_{s_}'), 1) if s_ else acc
        for s_, gg in enumerate(ORDER):
            path = [f'ks_afk_{st}_{gg}'] + [f'ks_afc_{st}_{j}' for j in range(s_ + 1, 8)] + [f'ks_afe_{st}']
            leaves[f'ectl_{st}_{ectl_frame(gg)}.kf'] = dict(lane=lane, buses=path,
                                                            latency=tot(rs(path[0]), 1, down[s_]))
        for k in range(4):
            opts = []
            for j, gg in enumerate((2 * k, 2 * k + 1)):
                b = f'ks_afv_{st}_{k}' if j == 0 else f'ks_afv_{st}_{k}__f0'
                opts.append(tot(rs(b), 1, down[ORDER.index(gg)]))
            leaves[f'vport_{st}_{k}.f'] = dict(lane=lane, buses=[f'ks_afv_{st}_{k}', f'ks_afv_{st}_{k}__f0'],
                                               latency=None if None in opts else min(opts))
    for v in leaves.values():
        lanes.setdefault(v['lane'], []).append(v['latency'])
    return dict(rtl=[AFAULT_NODE[0], AFAULT_ROOT[0]], leaves=leaves,
                lane_latency_max={k: (None if None in v else max(v)) for k, v in sorted(lanes.items())},
                note='unit_fault lane k = OR of its leaves, each seen `latency` edges after its fault flop (fixed); '
                     'the face folds |unit_fault into service_fault')


def response_lat(m):
    """per ECTL kiss frame: RESPONSE_LAT = landing seg 8 + K request + K response relay stages (kv_static_ages).
    KV-ECTL4: every frame must equal ECTLK_RESPONSE_LAT (kv_k_rt_eq pads krq); a frame off the budget is a GEN error."""
    st = m.get('relay_stages', {})
    out, bad = {}, []
    for s in STACKS:
        for g in range(8):
            r = 8 + st.get(f'krq_{s}_{g}', 0) + st.get(f'krs_{s}_{g}', 0)
            out[f'ectl_{s}_{ectl_frame(g)}'] = dict(RESPONSE_LAT=r, QK_ISSUE_AGE=ECTLK_QK_ISSUE_AGE)
            if r != ECTLK_RESPONSE_LAT:
                bad.append(f'{s}_{g} {r}')
    if bad and m.get('k_rt_eq'):
        raise ValueError(f'kv_static_die: K round trip != ECTLK_RESPONSE_LAT {ECTLK_RESPONSE_LAT} after kv_k_rt_eq: {bad}')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--rtl', action='store_true', help=f'write {RTL_FILE}')
    ap.add_argument('--check', action='store_true', help='the committed RTL equals the generated text')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--domsplit-table', metavar='PORTS_DIR',
                    help=f'KV-DOMSPLIT: write {DOMSPLIT_TABLE} from the measured base tile ports (kvs_port_domains)')
    a = ap.parse_args()
    if a.domsplit_table:
        tab = domsplit_table(a.domsplit_table)
        tab.update(design_point=dict(rtl_file=RTL_FILE, ports_dir=a.domsplit_table))
        (ROOT / DOMSPLIT_TABLE).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / DOMSPLIT_TABLE).write_text(json.dumps(tab, indent=1, sort_keys=True) + '\n')
        print(f'wrote {DOMSPLIT_TABLE}: ' + ', '.join(f'{k} {sum(v == "hck" for v in f.values())} hck / '
                                                      f'{sum(v == "ck" for v in f.values())} ck' for k, f in tab['fields'].items()))
        return 0
    txt = rtl_text()
    p = ROOT / RTL_FILE
    if a.rtl:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
        print(f'wrote {RTL_FILE} ({len(txt.splitlines())} lines)')
    if a.check:
        if not p.exists() or p.read_text() != txt:
            print('STALE: regenerate with --rtl')
            return 1
        print('RTL current')
    if a.summary:
        for d in ('slg_WS_0', 'kvpc_WS_0', 'kvpc_WS_1', 'kvs_ctl', 'kvs_attn', 'kvs_emb'):
            t = all_tiles()[d]
            c = defaultdict(int)
            for v in t['ports'].values():
                c[(v['dir'], v['cls'])] += v['width']
            print(d, t['kind'], len(t['ports']), dict(c))
    return 0


if __name__ == '__main__':
    sys.exit(main())
