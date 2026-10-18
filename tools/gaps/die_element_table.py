#!/usr/bin/env python3
"""Authoritative element table for the CURRENT die revisions (owner 10-17/10-18: every open element of the four dies
must have a live job or a live owner; list the elements that are very hard to iterate).

v2 (ELEMENT-TABLE 10-18). Element list per die comes from the current die case / bind / contract, never from memory:
  S81 p4k        claude/s81-die5-1017: bind5/port_bind.json masters (die.v of p4k), bind/bind_table_p4k.json
                 (view per master, frame members, child views, owed child views), bind5/residual.json (bind verdict)
  Qwen compute   claude/rtl-build-qc-1018 inventory.json + port_bind_dv2f12 masters (dv2f12 die.v; dv2f13 never
                 generated, dv2f14 = Q-DIE11 branch for the RTL) + forwarded-lane family (Q-DIE11-RLY)
  Qwen KV        kvj-g2 static die (claude/kvj-g2-1017 kv_static_die.py masters) + the last MEASURED strict bind
                 (kvs13l4 port_bind; kvs14a-place/port_bind.json replaces it automatically once KV-PLAN3's prep passes)
  HBM d4g        claude/hd4g-1017 gen0/view_bindings.json cells (+ contract soft_parents) + gen1_bindings_plan.json
Children of every master come from its RTL: modules instantiated (recursively) in the master's RTL at the die
branch / bind ref that have ever been a hardened element (closure job block, ref_tile kit top, registry row).
Live or 24-h work in a die's namespace that matches no element is attached by the SUCCESSOR / FAMILY tables or stem,
else listed as "unattached recent work" (a successor the die case does not bind yet, or obsolete work).

State (stage): CLOSED+native / CLOSED (native owed) / routing / gating / bench / RTL-only / NOT STARTED / PHY model.
  routing = live closure-loop job; gating = live ref_gate (fleet or local ot-run client); bench = live bench client.
Owner: live job owner, else lane files modified in the last 3 h that name the element, running ot-run clients,
  systemd units. IDLE-NO-OWNER = open, nothing live, no 3-h lane names it.
Hard to iterate: one iteration > ~3 h (measured closure-job wall, live job elapsed, or lane-recorded HARD_NOTES) or
  >= 3 failed closure verdicts; reason from measured data (route RAM, sinks at the gate) + the lane notes.
Writes gaps/die_element_table.json + gaps/die_element_table.md. Read-only: it deletes/revokes/submits nothing.
Usage: python3 die_element_table.py [--no-ssh] [--quiet]
"""
import argparse, collections, glob, gzip, json, os, re, statistics, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

TAKEOVER = Path('/home/ubuntu/claude-takeover-20261007')
GAPS = TAKEOVER / 'gaps'
LANES = TAKEOVER / 'lanes'
CACHE = GAPS / 'die_inputs'
OUT_JSON = GAPS / 'die_element_table.json'
OUT_MD = GAPS / 'die_element_table.md'
JOBS = Path.home() / '.local/state/closure_loop/jobs'
REVOKED = TAKEOVER / 'revoked_closures.json'
REG_URL = 'http://127.0.0.1:8765/api/elements'
FLEET_URL = 'http://127.0.0.1:8765/api/fleetjobs'
GIT_WTS = ['/home/ubuntu/wt/elemtable-1018', '/home/ubuntu/wt/elemtable-1017']   # own read-only worktrees
GIT_DIR_FALLBACK = '/home/ubuntu/OpenTallas/.git'      # object store only, never the shared checkout
E4 = 'ot-epyc4'
LIVE_ST = {'READY', 'RUNNING', 'ECO', 'QUEUED', 'PENDING', 'SUBMITTED', 'BENCH', 'GATE'}
FAIL_ST = {'NEEDS_RTL', 'NEEDS_HUMAN', 'REFUSED', 'INVALID', 'FLOORPLAN_MARGIN', 'PREROUTE_MARGIN'}
LANE_OWNER_H = 3.0
HARD_H = 3.0
HARD_FAILS = 3
NOW = time.time()

# ---- per-die sources -------------------------------------------------------------------------------------------
S81 = dict(design='DeepSeek ROM (S81-DV)', die='S81 p4k', branch='origin/claude/s81-die5-1017',
           port_bind='results/arch/s81_dv_1016/bind5/port_bind.json',
           bind_table='results/arch/s81_dv_1016/bind/bind_table_p4k.json',
           residual='results/arch/s81_dv_1016/bind5/residual.json',
           ns=r'^(dsdv_|dsfd_|ot_s81|s81|col_h|ot_dsrom_su_hcpost|ot_v41_rom_elem_q)',
           die_re=r's81die5|case_p4k|s81bind3|s81-die5', lanes_re=r'^(S81|RTL-BUILD-S81)')
QC = dict(design='Qwen ROM', die='Qwen compute dv2f12/dv2f14', branch='origin/claude/q-die11-1018',
          inv_branch='origin/claude/rtl-build-qc-1018',
          inventory='results/arch/qwen_split_compute_1014/rtl_build_qc_1018/inventory.json',
          port_bind='results/arch/qwen_split_compute_1014/rtl_build_qc_1018/port_bind_dv2f12_main4f7440ccf.json',
          ns=r'^(qfd_|ot_qfd_|qfwd)', die_re=r'dv2f1[2-9]|q-die1[01]|qwen_rom_fulldie|qdie1[01]',
          lanes_re=r'^(Q-DIE|RTL-BUILD-QC)')
KV = dict(design='Qwen ROM', die='Qwen KV kvj-g2', branch='origin/claude/kvj-g2-1017',
          remote=['/srv/opentallas-scratch/claude/qwen-kvsys/kvs14b-place/port_bind.json',
                  '/srv/opentallas-scratch/claude/qwen-kvsys/kvs14a-place/port_bind.json',
                  '/srv/opentallas-scratch/claude/qwen-kvsys/kvs13l4-pvclean/port_bind.json'],
          static_tools=['tools/qwen_kv_die/kv_static_die.py', 'tools/qwen_kv_die/kv_die.py'],
          ns=r'^(qkd_|ot_qkd_|ot_qkh_|qkh_|ot_qwen_tp8_pv|ot_qkvd)', die_re=r'kvs14|kvplan[34]|kv-plan[34]|kv-case|qwen-kvsys',
          lanes_re=r'^(KV-INTEG|KV-PLAN|KV-CASE|KV-WIRE|KV-RTRUNK|RTL-BUILD-KV)')
HB = dict(design='HBM accelerator', die='HBM d4g', branch='origin/claude/hd4g-1017',
          bindings='results/arch/hbm_die_d4g/gen0/view_bindings.json',
          contract='results/arch/hbm_die_d4g/gen0/contract.json.gz',
          gen1='results/arch/hbm_die_d4g/gen1_bindings_plan.json',
          ns=r'^(ot_hbm|ot_hgi|hfd_|hbfd_|hdie_|hgi_|hbm_|ot_hfd|ot_vms|ot_static_cmd|hcoll_|hsu_)',
          die_re=r'hd4g|d4g_gen|/d4g', lanes_re=r'^(H-D4G|HBM-B-RTL|RTL-BUILD-HBM)')
DIES = [S81, QC, KV, HB]

# successor / child leaves whose names share no stem with their die master (curated from the lane files)
SUCCESSOR = {
    'S81 p4k': {'ot_s81_kp4_dec': 'ot_pdie_serdes', 'ot_s81_kp4_enc': 'ot_pdie_serdes', 'ot_s81_kp4_deca': 'ot_pdie_serdes',
                'ot_s81_kp4_decb': 'ot_pdie_serdes', 'dsfd_engram_lkp_static14': 'dsfd_engram_mix4_half',
                'dsfd_engram_lkp_static10': 'dsfd_engram_mix4_half'},
    'Qwen KV kvj-g2': {'ot_qkd_ahub_static': 'qkd_ahub', 'ot_qkd_ahub_core': 'qkd_ahub', 'qkd_ahub_core': 'qkd_ahub',
                       'qkd_ahub_die': 'qkd_ahub', 'qkd_d2d_static': 'qkd_d2ds', 'qkd_pv_fin_s': 'qkd_pvfin',
                       'qkd_pv_ctl_t': 'ot_qwen_tp8_pv_wide_ctl_t'},
    'HBM d4g': {'ot_hgi_coll_tkm_tile_e86': 'ot_hgi_coll_tkm_m_tp192', 'ot_hgi_coll_tkm_tile': 'ot_hgi_coll_tkm_m_tp192',
                'ot_hgi_sfu_store_leaf3_r9': 'ot_hgi_sfu_programme_store_r10', 'ot_hgi_sfu_core_split2': 'ot_hgi_sfu_core_split3',
                'ot_hbm_sm_vm_wr_q_t': 'ot_hbm_sm_vm_wr_q_t_lanes', 'ot_hbm_sm_vm_wr_q_t_faces4': 'ot_hbm_sm_vm_wr_q_t_lanes',
                'ot_hbm_smh_rp4_one': 'ot_hbm_accel_smh_attn'},
}
# family prefixes -> die master (regex on the job block / kit top); '(...)' parents are synthetic family rows
FAMILY = {
    'S81 p4k': [(r'^(ot_s81sl_|s81sl_|ot_s81dv_x|s81dv_x)', 'ot_s81sl_slice'), (r'^dsdv_gunit_', 'dsdv_gunit'),
                (r'^dsdv_sh_', 'dsdv_seq_host'), (r'^(dsdv_svc_|ot_s81_su_)', 'dsdv_svc_rs'),
                (r'^(s81dvbk_|dsdv_bk_)', 'dsdv_bk_col'), (r'^(ot_s81_kp4_|s81lk_)', 'ot_pdie_serdes'),
                (r'^(s81ctrl_|dsfd_ctrl)', 'dsfd_ctrl_rg2'), (r'^(dsfd_engram|s81engm|ot_s81_engram)', 'dsfd_engram_mix4_half'),
                (r'^(dsfd_bf_|dsfd_cfifo|ot_s81_cfg7|dsfd_rly_38)', 'col_h9'), (r'^dsfd_dvland', 'dsfd_dvland_276'),
                (r'^dsfd_dvrlyh?_', '(die relay stations)')],
    'Qwen compute dv2f12/dv2f14': [(r'^(qfd_c_b16|qfd_tile_n[kl]_rp2|qfd_romleaf|qfd_crom)', 'qfd_c_b16_dv'),
                                  (r'^qfd_(dv_slice|slice|sp_|su_|seq_su|cst_|xcst_|chead|xhead|lst_)', 'qfd_dv_slice2_w'),
                                  (r'^qfd_tt_', 'qfd_tt_ctlm_dv'), (r'^qfd_(native59|n59)', 'qfd_native59_dv_service'),
                                  (r'^(qfd_coll|qfd_static_ch546|qfd_io_coll|qfd_ucie_six_five|qfd_io_(serdes|ucie|xfifo))',
                                   'qfd_collective_static_io_production'),
                                  (r'^qfd_(rlyh0?|landh0?|rly)(_|$)', '(die forwarded lanes / relays)'),
                                  (r'^qfd_(embed|emb_|io_emb)', 'qfd_embedding_word_provider'), (r'^qfd_sys', 'qfd_sys_face'),
                                  (r'^qfd_d2d', 'qfd_d2d_static'), (r'^qfd_rst', 'qfd_rstseq')],
    'Qwen KV kvj-g2': [(r'^(qkd_ahub|ot_qkd_ahub)', 'qkd_ahub'), (r'^qkd_hr_core', 'qkd_host_rt'),
                       (r'^qkd_astk', 'qkd_astk'), (r'^qkd_ectl', 'qkd_ectl_a_tp8_epoch_direct'), (r'^qkd_seq', 'qkd_seq_st'),
                       (r'^(qkd_pv|ot_qwen_tp8_pv)', 'ot_qwen_tp8_pv_join_t'), (r'^qkd_kvs_', '(kvj-g2 static tiles)'),
                       (r'^qkd_(embgw|emb)', 'qkd_embgw'), (r'^qkd_(hslice|hsl)', 'qkd_hslice'), (r'^qkd_d2d', 'qkd_d2ds'),
                       (r'^(qkd_ctrl|qkd_kvwq)', 'qkd_ctrl_pc'), (r'^(ot_qkh_|qkh_)', 'ot_qkh_lane8'),
                       (r'^qkd_rlys?_', 'qkd_rlys_36'), (r'^qkd_cdc', 'qkd_cdc_wleaf')],
    'HBM d4g': [(r'^hbfd_rly_136', '(gen1 136-b lane relays)'), (r'^(hbm_su_pg|ot_hbm_su_static_pg|ot_hbm_su_pg)', 'ot_hbm_su_static_pgslice_lg__pv*'),
                (r'^(ot_hgi_sfu_store|hbm_sfu_store|ot_hgi_sfu_programme)', 'ot_hgi_sfu_programme_store_r10'),
                (r'^(hdie_host_cfg|ot_hbm_host_cfg)', 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b'), (r'^(hgi_sm_xl|ot_hgi_sm_xl)', 'ot_hgi_sm_xload_cl2_ctlx'),
                (r'^(hbm_hcq|ot_hbm_hc)', 'ot_hbm_hc_q_static'), (r'^(hcoll_|ot_hgi_coll|ot_hfd_coll)', 'ot_hfd_coll_q3_hard_v7x'),
                (r'^(hbm_su_qcore|ot_hbm_su_static_qcore)', 'ot_hbm_su_static_qcore'),
                (r'^(hbm_su_sfustore|ot_hbm_su_static_sfustore)', 'ot_hbm_su_static_sfustore__pv*'),
                (r'^(hfd_vms|hfd_hgi_vms)', 'hfd_vms_bank_native_q1_core_pr'), (r'^ot_hbm_idx', 'ot_hbm_idx_score_static'),
                (r'^ot_hbm_svc_vmdel', 'ot_hbm_svc_vmdel_lane'), (r'^hdie_col', 'ot_hbm_static_cfg_collar')],
}
# lane-recorded iteration facts (lane files 10-17/18), quoted as the reason; (hours or None, text)
HARD_NOTES = {
    ('S81 p4k', '(die top)'): (6.0, 'die GEN + repeater GRT with 2,532 relay stations on ot-pve1 64 GB (S81-DIE5 case_p4k_r); then land plan + die STA (bind3 run_all.sh pattern)'),
    ('S81 p4k', 'dsdv_svc_rs'): (5.0, 'SVC6: hierarchical x16 benches hung 4-5 h in top re-elaboration at 66 GB; protect-lib bench (13 s top build) now 7 variants x 100 GB on epyc4'),
    ('S81 p4k', 'ot_s81sl_slice'): (3.0, 'whole-slice build ~15 GB / 25 min elaboration per bench run, compile-bound on ot-pve1; xfin ENG +~61k flops CRITICAL gate'),
    ('S81 p4k', 'dsfd_ctrl_rg2'): (6.5, 'S81-CTRL3: 16x rg2 C++ bench build at -O2/-j4 ran 6.5 h then killed (now -O1, ~1 min); c1 route missed TT -6.4 / FF -6.6'),
    ('S81 p4k', 'ot_pdie_serdes'): (4.0, 'kp4_dec parent --cts gate killed twice at CTS (exit 143 on agidock128, 23:48 and 00:20); kp4 deca/decb never closed'),
    ('S81 p4k', 'col_h9'): (4.0, 'frame cluster (S81U-3F) never hardened; bf_col_cl parent gate waits on lane4r + fp views'),
    ('S81 p4k', 'dsfd_engram_mix4_half'): (None, 'NO RTL (unbound bind master); Engram mix owed in-slice (S81U-MIX / RTL-BUILD-S81 2a-2d) or the p4k_nomix4 patch'),
    ('Qwen compute dv2f12/dv2f14', '(die top)'): (8.0, 'dv2f12 chain GEN + repeaters (166k) + GRT (overflow 72k) + STA TT ran for hours and was killed (exit 143) before FF/SS; dv2f13 GEN failed on the clock grant'),
    ('Qwen compute dv2f12/dv2f14', 'qfd_c_b16_dv'): (5.0, '128-GB cluster gates on ot-epyc4 (diagc/diagct, diag16c/diag16ct); 8-region gates died at CTS (Tcl bug); child-flop spread FAIL -> centre-fed / 16-region retry'),
    ('Qwen compute dv2f12/dv2f14', 'qfd_tt_ctlm_dv'): (4.0, 'TT head h16b repair_timing runs long (EARLY_FAIL_HOLD false positive, resubmitted 01:14)'),
    ('Qwen KV kvj-g2', '(die top)'): (None, 'kvj-g2 static die not placeable 10-17 18:13 .. 10-18 01:27 (relay planner); kvs14a prep FAILED 01:31 and 01:40 (576 stack-local pin-bit over-reach) -> no case, no strict bind, no GRT'),
    ('Qwen KV kvj-g2', 'qkd_astk'): (3.0, 'ASTK e-read strip + static ECTL (CRITICAL ectla) benches: 6 mutants x 24 GB on ot-pve1, timeout 5000 s'),
    ('HBM d4g', '(die top)'): (6.0, 'GEN0 chain since 10-17 21:34: ETM OOM (rc 137 at 48 GB) on idx_score / idx_topk_link, re-drive at 112 GB; GEN1 needs relay_layer + lockstep + regen; GRT0 not reached'),
    ('HBM d4g', 'ot_hbm_idx_score_static'): (3.0, 'ETM at GEN OOM at 48 GB -> 112 GB re-drive (H-D4G2)'),
    ('HBM d4g', 'ot_hbm_idx_topk_link_static'): (3.0, 'ETM at GEN OOM at 48 GB -> 112 GB re-drive (H-D4G2)'),
    ('HBM d4g', 'ot_hgi_sfu_programme_store_r10'): (3.0, 'CRITICAL r10 store cluster: r10n2 leaf split_equiv + coordinator review rounds; sfup SYNTH until closed'),
}
PHY_RE = re.compile(r'(hbm3e_phy|^ot_pdie_(serdes|ucie)$|ucie_x64_phy|serdes_112g_x12_phy|^qkd_hbm3e_phy|outline_marker|'
                    r'^qfd_(ckbump|sigbump|clkrx)$|^qkd_(ckbump|fwdbump)$|_bb$|ot_s81_pma_bm|hbm3e_dev_bm)')
RELAY_RE = re.compile(r'^(dsfd_dvrlyh?_|dsfd_rly_\d|hbfd_rly_|qkd_rlys_|qfd_rlyh?0?_|qfd_landh0?_|hfd_stn_)')
STD_RE = re.compile(r'_ASAP7_')
SV_KW = {'module', 'if', 'else', 'for', 'begin', 'end', 'assign', 'always', 'always_ff', 'always_comb', 'case', 'generate',
         'function', 'task', 'return', 'wire', 'logic', 'reg', 'input', 'output', 'localparam', 'parameter', 'initial',
         'assert', 'property', 'while', 'repeat', 'foreach', 'unique', 'priority', 'int', 'integer', 'genvar'}


# ---- helpers ---------------------------------------------------------------------------------------------------
def log(*a):
    if not ARGS.quiet: print(*a, file=sys.stderr)


def ago(t): return '%.1fh' % max(0.0, (NOW - t) / 3600.0) if t else '-'


def ptime(s):
    try: return datetime.fromisoformat(str(s)[:25]).timestamp()
    except Exception: return None


def git_base():
    for wt in GIT_WTS:
        if os.path.isdir(wt):
            try:
                top = subprocess.run(['git', '-C', wt, 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                                     timeout=30).stdout.strip()
                if top == wt: return ['git', '-C', wt]
            except Exception: pass
    return ['git', '--git-dir', GIT_DIR_FALLBACK]


GIT = None
_blob, _modidx = {}, {}


def git_show(ref, path):
    k = (ref, path)
    if k not in _blob:
        r = subprocess.run(GIT + ['show', f'{ref}:{path}'], capture_output=True, timeout=120)
        _blob[k] = r.stdout if r.returncode == 0 else None
    return _blob[k]


def git_json(ref, path):
    raw = git_show(ref, path)
    if raw is None: return None
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    return json.loads(raw)


def git_head(ref):
    r = subprocess.run(GIT + ['log', '-1', '--format=%h %ci', ref], capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else None


def module_index(ref):
    """module name -> path at ref (first declaration in *.sv / rtl/*.v)."""
    if ref not in _modidx:
        idx = {}
        r = subprocess.run(GIT + ['grep', '-I', '-n', '-E', r'^\s*module\s+[A-Za-z_][A-Za-z0-9_]*', ref, '--', '*.sv', 'rtl/*.v'],
                           capture_output=True, text=True, timeout=300)
        for line in r.stdout.splitlines():
            m = re.match(r'[^:]+:([^:]+):\d+:\s*module\s+([A-Za-z_]\w*)', line)
            if m: idx.setdefault(m.group(2), m.group(1))
        _modidx[ref] = idx
    return _modidx[ref]


INST_RE = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\()', re.M)


def module_children(ref, path, module):
    raw = git_show(ref, path)
    if not raw: return set()
    t = raw.decode(errors='replace')
    t = re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', ' ', t, flags=re.S))
    m = re.search(r'^\s*module\s+' + re.escape(module) + r'\b(.*?)^\s*endmodule', t, re.S | re.M) if module else None
    body = m.group(1) if m else t
    return {x.group(1) for x in INST_RE.finditer(body) if x.group(1) not in SV_KW}


def remote_or_cache(paths, tag):
    """first readable remote path on E4 -> cached copy; else the cache."""
    CACHE.mkdir(exist_ok=True)
    if not ARGS.no_ssh:
        for p in paths:
            try:
                r = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', '-o', 'BatchMode=yes', E4, f'cat {p} 2>/dev/null'],
                                   capture_output=True, timeout=120)
                if r.returncode == 0 and r.stdout.strip():
                    c = CACHE / f'{tag}.json'; c.write_bytes(r.stdout)
                    (CACHE / f'{tag}.src').write_text(f'{E4}:{p} fetched {time.strftime("%m-%d %H:%M")}\n')
                    return json.loads(r.stdout), f'{E4}:{p}'
            except Exception as e: log('ssh', p, e)
    c = CACHE / f'{tag}.json'
    if c.exists():
        src = (CACHE / f'{tag}.src').read_text().strip() if (CACHE / f'{tag}.src').exists() else str(c)
        return json.load(open(c)), f'cache ({src})'
    return None, None


def ssh_text(cmd):
    if ARGS.no_ssh: return ''
    try:
        return subprocess.run(['ssh', '-o', 'ConnectTimeout=8', '-o', 'BatchMode=yes', E4, cmd], capture_output=True,
                              text=True, timeout=60).stdout
    except Exception: return ''


def collapse(m): return re.sub(r'__pv\d+$', '__pv*', m)


def stem(n):
    n = re.sub(r'__pv(\d+|\*)$', '', n)
    toks = n.split('_')
    while len(toks) > 2 and re.fullmatch(r'([a-z]{0,5}\d+[a-z]*|physical|native|faces\d*|lanes|one|m|pr|rr|c|cl|hq\d*)', toks[-1]):
        toks.pop()
    return '_'.join(toks)


def aliases(e):
    if e.startswith('kit:'): return {e[4:]}
    if e.startswith('('): return set()
    out = {e}
    for p in ('ot_hgi_', 'ot_hbm_', 'ot_s81sl_', 'ot_s81dv_', 'ot_qfd_', 'ot_', 'dsfd_', 'qfd_', 'qkd_', 'hfd_', 'dsdv_'):
        if e.startswith(p) and len(e) - len(p) >= 6: out.add(e[len(p):])
    s = stem(e)
    if len(s) >= 10: out.add(s)
    return {a.replace('__pv*', '') for a in out if len(a.replace('__pv*', '')) >= 6}


def mentions(text, al, minlen=8):
    return any(len(a) >= minlen and re.search(r'(?<![A-Za-z0-9_])' + re.escape(a) + r'(?![A-Za-z0-9])', text) for a in al)


def row(element, kind, parent='(die)', source='', count='', note='', view=None, closed=False, native=None, rtl=None,
        no_rtl=False):
    return dict(element=element, kind=kind, parent=parent, source=source, count=count, note=note, view=view,
                view_closed=closed, view_native=native, rtl=rtl, no_rtl=no_rtl)


def view_flags(v):
    s = str(v or '')
    closed = 'CLOSED' in s and 'NOT CLOSED' not in s
    nat = 'PASS' if 'native PASS' in s else ('FAIL' if 'native FAIL' in s else None)
    return closed, nat


# ---- die element lists -----------------------------------------------------------------------------------------
def die_s81():
    b = S81['branch']; src = {}
    pb = git_json(b, S81['port_bind']) or {}; bt = git_json(b, S81['bind_table']) or {}; res = git_json(b, S81['residual']) or {}
    bs = res.get('bind', {}).get('summary', {})
    src['bind'] = (f"{b}:{S81['port_bind']} ({git_head(b)}) verdict {res.get('bind', {}).get('verdict')}: unbound "
                   f"{bs.get('unbound_masters')} / unconnected {bs.get('input_unconnected')} / undriven {bs.get('undriven_net_bits')} b")
    src['grt'] = str(res.get('grt', {}).get('dir', ''))
    rows = []
    btm = bt.get('masters') or {}
    alias_bt = {'ot_s81sl_slice': 'dsdv_slice', 'dsdv_bk_sel': 'dsfd_bk_selector', 'dsdv_bk_col': 'dsfd_bk_collector'}
    relay_views = bt.get('relay_views') or {}
    for m, v in (pb.get('masters') or {}).items():
        if STD_RE.search(m): continue
        rt = v.get('rtl'); ref = b
        mm = re.search(r'rtl_extra/([0-9a-f]{40})/(.*)$', rt or '')
        if mm: ref, rt = mm.group(1), mm.group(2)
        elif rt and not rt.startswith('rtl/'): rt = None
        bm = btm.get(m) or btm.get(alias_bt.get(m, '')) or {}
        view = bm.get('view') or relay_views.get(m)
        closed, nat = view_flags(view)
        kind = 'phy' if PHY_RE.search(m) else ('relay' if RELAY_RE.search(m) else
                                                ('cluster' if m.startswith(('col_h', 'dsdv_', 'ot_s81sl_slice')) else 'tile'))
        rows.append(row(m, kind, count=v.get('instances'), source='p4k die.v (bind5 port_bind)', view=view, closed=closed,
                        native=nat, rtl=(ref, rt) if rt else None, no_rtl=not v.get('rtl'),
                        note=(bm.get('view_note') or '') + (' | bind FAIL' if v.get('verdict') == 'FAIL' else '')))
    for fm in bt.get('frame_members') or []:
        closed, nat = view_flags(fm.get('view'))
        ref = fm.get('ref') or 'origin/main'
        if not ref.startswith('origin/') and not re.fullmatch(r'[0-9a-f]{40}', ref): ref = 'origin/' + ref
        rows.append(row(fm['master'], 'tile', parent='col_h9', source='bind_table frame_members', view=fm.get('view'),
                        closed=closed, native=nat, note=fm.get('view_note') or '', rtl=(ref, fm.get('path')) if fm.get('path') else None))
    par_map = [('dsdv_svc_rs', 'dsdv_svc_rs'), ('ot_pdie_serdes', 'ot_pdie_serdes'), ('kp4', 'ot_pdie_serdes'), ('col_h9', 'col_h9'),
               ('dsdv_gunit', 'dsdv_gunit'), ('dsdv_seq_host', 'dsdv_seq_host'), ('ot_s81sl_slice', 'ot_s81sl_slice')]
    for m, v in (bt.get('child_views') or {}).items():
        p = next((pv for k, pv in par_map if k in str(v.get('parent'))), '(die)')
        closed, nat = view_flags(v.get('view'))
        rows.append(row(m, 'tile', parent=p, source='bind_table child_views', view=v.get('view'), closed=closed, native=nat))
    for m, why in (bt.get('child_views_owed') or {}).items():
        p = 'dsdv_gunit' if 'gunit' in m else ('ot_pdie_serdes' if 'kp4' in m else ('ot_s81sl_slice' if 's81sl' in m else '(die)'))
        rows.append(row(m, 'tile', parent=p, source='bind_table child_views_owed', note='OWED: ' + why))
    src['bind_table'] = f"{b}:{S81['bind_table']}"
    return rows, src


def die_qc():
    src = {}
    inv = git_json(QC['inv_branch'], QC['inventory']) or {}
    pb = git_json(QC['inv_branch'], QC['port_bind']) or {}
    src['inventory'] = f"{QC['inv_branch']}:{QC['inventory']} ({git_head(QC['inv_branch'])}): {inv.get('verdict', '')[:110]}"
    src['rtl'] = f"{QC['branch']} ({git_head(QC['branch'])}) = Q-DIE11 (dv2f14)"
    owed = inv.get('hardening_owed_not_missing_rtl') or {}
    rows = []
    for m, v in (pb.get('masters') or {}).items():
        rt = v.get('rtl') if str(v.get('rtl', '')).startswith('rtl/') else None
        kind = 'phy' if (v.get('kind') == 'model' or PHY_RE.search(m)) else ('cluster' if m in owed and m != 'qfd_sys_face' else 'tile')
        o = owed.get(m) or {}
        rows.append(row(m, kind, count=v.get('instances'), source='dv2f12 die.v (port_bind, main RTL)',
                        rtl=(QC['branch'], rt) if rt else None,
                        note=(f"hardening owed ({o.get('owner')}) {o.get('note', '')}".strip() if o else '') +
                             (' | bind FAIL (1 input unconnected; closes on the next GEN)' if v.get('verdict') == 'FAIL' else '')))
    rows.append(row('(die forwarded lanes / relays)', 'relay', source='dv2f12 496 qfd_rly + Q-DIE11-RLY qfwd kits (OT_SPLIT_FWD_LANES)',
                    note='138 fwd-lane masters on gen1; full kit set via gen_fwd_lane_kits.py after the dv2f14 GEN'))
    return rows, src


def die_kv():
    src = {}
    pb, where = remote_or_cache(KV['remote'], 'kv_port_bind')
    stale = 'kvs13l4' in str(where)
    src['bind'] = str(where) + (' (STALE: last measured strict bind; kvj-g2 has none)' if stale else '')
    tools_txt = ''.join((git_show(KV['branch'], p) or b'').decode(errors='replace') for p in KV['static_tools'])
    src['static_die'] = f"{KV['branch']} ({git_head(KV['branch'])}) kv_static_die.py masters"
    st = ssh_text('tail -2 /srv/opentallas-scratch/claude/qwen-kvsys/kvs14a-place/STATUS.log 2>/dev/null')
    if st: src['kvs14a'] = ' / '.join(st.strip().splitlines())[-220:]
    rows = []
    idx = module_index(KV['branch'])
    for m, v in sorted((pb or {}).get('masters', {}).items()):
        cls = v.get('cls')
        rows.append(row(m, 'phy' if cls == 'HARD_PHY' else ('relay' if cls == 'RELAY' else 'tile'), count=v.get('n_instances'),
                        source=('kvs13l4 bind (last measured)' if stale else 'kvs14a bind'), rtl=(KV['branch'], idx[m]) if m in idx else None,
                        note=f'bind {cls}' + (' (width/port mismatch)' if cls == 'MISMATCH' else '') +
                             ('' if (m in tools_txt or not stale) else ' | NOT named in kvj-g2 kv_die/kv_static_die (likely replaced)')))
    have = {r['element'] for r in rows}
    for m in sorted(set(re.findall(r"'((?:qkd|ot_qkd)_[A-Za-z0-9_]+)'", tools_txt))):
        if m in have or m not in idx: continue
        if not re.search(r'qkd_kvs_|qkd_pvfin|qkd_pv_fin_s|qkd_ectlk|qkd_kv_es_fan|qkd_ectl3_kiss|qkd_d2d_static|qkd_kv_cfault', m): continue
        rows.append(row(m, 'cluster' if m.startswith('qkd_kvs_') else 'tile', source='kvj-g2 static die master', rtl=(KV['branch'], idx[m]),
                        note='generated static tile: no kit yet (KV-INTEG M1)' if m.startswith('qkd_kvs_') else ''))
        have.add(m)
    return rows, src


def die_hbm():
    src = {}
    b = HB['branch']
    vb = git_json(b, HB['bindings']) or {}
    con = git_json(b, HB['contract']) or {}
    g1 = git_json(b, HB['gen1']) or {}
    src['bindings'] = f"{b}:{HB['bindings']} ({git_head(b)}) {vb.get('summary')}"
    gl = ssh_text('ls /srv/opentallas-scratch/claude/hd4g/gen0 2>/dev/null | tr "\\n" " "')
    if gl: src['gen0_dir'] = 'epyc4 hd4g/gen0: ' + gl[:120]
    m_src = {}
    for v in (con.get('instances') or {}).values(): m_src.setdefault(v.get('master'), v.get('source'))
    rows = []
    for c in vb.get('cells') or []:
        m = c['master']; stt = c.get('status') or ''
        kind = 'phy' if PHY_RE.search(m) else ('relay' if RELAY_RE.search(m) else 'tile')
        s = m_src.get(m)
        rows.append(row(collapse(m), kind, count=c.get('instances'), source='d4g GEN0 view_bindings', view=c.get('view'),
                        closed='BOUND_ROUTED' in stt, rtl=(b, s) if s and s.endswith(('.sv', '.v')) else None,
                        note=stt + (f" open {c.get('open_units')} -> {c.get('rtl_lanes')}" if c.get('open_units') else '')))
    for sp in con.get('soft_parents') or []:
        for ch in (sp.get('children') or {}).values():
            rows.append(row(ch, 'tile', parent=sp.get('master'), source='contract soft_parents', rtl=(b, m_src.get(ch)) if m_src.get(ch) else None))
    rows.append(row('(gen1 136-b lane relays)', 'relay', source='gen1_bindings_plan', note='lane relay layer planned on GEN0 pins (GEN1)'))
    for u in g1.get('bind_closed') or []:
        for m in u.get('masters') or []:
            rows.append(row(m, 'relay', parent='(gen1 136-b lane relays)', source='gen1 bind_closed', closed=True, view='closed view on main (gen1 plan)'))
    for u in g1.get('bind_pending') or []:
        kits = u.get('kit') if isinstance(u.get('kit'), list) else [u.get('kit')]
        for k in kits:
            rows.append(row('kit:' + os.path.basename(k or ''), 'tile', parent='ot_hbm_su_static_pgslice_lg__pv*', source='gen1 bind_pending',
                            note=u.get('status', '')[:160]))
    return rows, src


# ---- state sources ---------------------------------------------------------------------------------------------
def load_jobs():
    by = collections.defaultdict(list); kit_top = {}
    for f in glob.glob(str(JOBS / '*.json')):
        try:
            d = json.load(open(f)); mt = os.path.getmtime(f)
        except Exception: continue
        s = d.get('spec') or {}
        b = s.get('block')
        if not b: continue
        for rr in s.get('record') or []:
            mm = re.match(r'physical/ref_tile/([^/]+)/views', str(rr.get('to', '')) if isinstance(rr, dict) else '')
            if mm: kit_top.setdefault(mm.group(1), b)
        ev = d.get('events') or []
        # one iteration = 'launched route|calibrate' -> its first end event (route/calibrate done|failed, verdict,
        # EARLY_FAIL/NEEDS_*). 'updated' is NOT an end: deep-release / snapshot-trim events land days later.
        t0 = None; iters = []; cur = None
        for e in ev:
            te = ptime(e.split(' ')[0])
            if re.search(r'launched (route|calibrate)\b', e):
                if t0 is None: t0 = te
                if cur is None: cur = te
            elif cur is not None and te and re.search(r'(route|calibrate) (done|failed|FAIL)|\bverdict\b|EARLY_FAIL|NEEDS_(RTL|HUMAN)|REFUSED|INVALID|cancel', e):
                if te > cur: iters.append((te - cur) / 3600.0)
                cur = None
        t1 = ptime(d.get('updated')) or mt
        st = s.get('stages') if isinstance(s.get('stages'), dict) else {}
        ram = max([(st.get(k) or {}).get('peak_ram_gb') or 0 for k in ('route', 'calibrate') if isinstance(st.get(k), dict)] or [0])
        by[b].append(dict(name=d.get('name'), status=str(d.get('status')), t=t1, t0=t0, iters=iters, owner=s.get('owner'),
                          stage=d.get('stage_key'), ram=ram or s.get('peak_ram_gb') or 0,
                          reason=str(d.get('reason') or (ev[-1] if ev else ''))[:200]))
    for v in by.values(): v.sort(key=lambda j: j['t'])
    return by, kit_top


def load_kits(kit_top):
    """kit -> top from worktree ref_tile specs; top -> latest gate (time, verdict, sinks, kit)."""
    gates = {}
    for f in glob.glob('/home/ubuntu/wt/*/physical/ref_tile/*/spec.json'):
        kit = f.split('/')[-2]
        if kit not in kit_top:
            try: kit_top[kit] = json.load(open(f)).get('top')
            except Exception: pass
    for f in glob.glob('/home/ubuntu/wt/*/physical/ref_tile/*/gate_result.json'):
        kit = f.split('/')[-2]; top = kit_top.get(kit)
        if not top: continue
        try:
            d = json.load(open(f)); t = ptime(d.get('generated')) or os.path.getmtime(f)
        except Exception: continue
        if top not in gates or t > gates[top]['t']:
            gates[top] = dict(t=t, verdict=d.get('verdict'), sinks=(d.get('clock') or {}).get('max_root_sinks'), kit=kit)
    return gates


def load_native_receipts():
    out = {}
    for f in glob.glob('/home/ubuntu/wt/*/physical/ref_tile/*/native_audit.json'):
        try: d = json.load(open(f))
        except Exception: continue
        c = d.get('cell'); t = os.path.getmtime(f)
        if c and (c not in out or t > out[c][1]):
            out[c] = ('PASS' if d.get('pass') else 'FAIL: ' + str(d.get('fail_why'))[:80], t, f)
    return out


def load_clients():
    """local ot-run clients (python3 .../ot-run; identical argv counted once)."""
    out, seen = [], set()
    r = subprocess.run(['ps', '-eo', 'pid,etimes,args'], capture_output=True, text=True)
    for l in r.stdout.splitlines()[1:]:
        p = l.split(None, 2)
        if len(p) < 3 or not re.match(r'python3 \S*/ot-run\b', p[2]) or p[2] in seen: continue
        seen.add(p[2])
        cmd = p[2].split(' -- ', 1)[-1]
        out.append(dict(text=p[2], elapsed=int(p[1]), desc=f"ot-run[{p[0]}] {int(p[1]) / 3600:.1f}h {cmd[:90]}"))
    return out


def load_units():
    out = []
    try:
        r = subprocess.run(['systemctl', '--user', 'list-units', '--type=service', '--state=running', '--no-legend', '--plain'],
                           capture_output=True, text=True, timeout=30)
    except Exception: return out
    for l in r.stdout.splitlines():
        u = l.split()[0] if l.split() else ''
        if not u or re.search(r'fleet-viz|monitor|closure-loop|verdict-watch|pipewire|dbus|portal|permission|driftline|openrealtime|promptclub|queqiao', u):
            continue
        s = subprocess.run(['systemctl', '--user', 'show', u, '-p', 'ExecStart', '--no-pager'], capture_output=True, text=True).stdout
        m = re.search(r'argv\[\]=([^;]*)', s)
        if not m: continue
        argv = m.group(1).split(); txt = ' '.join(argv)
        for a in argv:
            if a.endswith('.sh') and os.path.isfile(a):
                try:
                    txt += '\n' + open(a, errors='replace').read()
                    for g in sorted(glob.glob(os.path.join(os.path.dirname(a), '*.sh')))[:6]:
                        txt += '\n' + open(g, errors='replace').read()[:20000]
                except Exception: pass
        out.append(dict(unit=u, text=txt))
    return out


def load_lanes():
    out = {}
    for f in glob.glob(str(LANES / '*.md')) + glob.glob(str(LANES / '*.txt')):
        mt = os.path.getmtime(f)
        if NOW - mt <= LANE_OWNER_H * 3600 and Path(f).stem != 'ELEMENT-TABLE':
            out[Path(f).stem] = dict(t=mt, text=open(f, errors='replace').read())
    return out


def resolve(ch, refs):
    for ref in refs:
        p = module_index(ref).get(ch)
        if p: return ref, p
    return None, None


# ---- main ------------------------------------------------------------------------------------------------------
def main():
    global GIT
    GIT = git_base()
    log('git via', ' '.join(GIT[:3]))
    dies = []
    for spec, fn in ((S81, die_s81), (QC, die_qc), (KV, die_kv), (HB, die_hbm)):
        rows, src = fn()
        seen, uniq = set(), []
        for r in rows:
            if r['element'] in seen: continue
            seen.add(r['element']); uniq.append(r)
        dies.append(dict(spec=spec, design=spec['design'], die=spec['die'], sources=src, rows=uniq))
        log(spec['die'], len(uniq))
    log('jobs / kits / registry / fleet / clients')
    jobs, kit_top = load_jobs()
    gates = load_kits(kit_top)
    try: revoked = set(json.load(open(REVOKED)))
    except Exception: revoked = set()
    try: reg = json.load(urllib.request.urlopen(REG_URL, timeout=150))['rows']
    except Exception as e: log('registry', e); reg = []
    regby = {r['element']: r for r in reg}
    try: fleet = json.load(urllib.request.urlopen(FLEET_URL, timeout=60))['rows']
    except Exception as e: log('fleetjobs', e); fleet = []
    natives = load_native_receipts()
    clients = load_clients(); units = load_units(); lanes = load_lanes()
    hardenable = set(jobs) | {t for t in kit_top.values() if t} | set(regby)

    # ---- children from RTL (recursive instantiation scan, nearest hardened ancestor = parent) ----
    log('RTL child scan')
    for d in dies:
        have = {r['element'] for r in d['rows']}
        refs_base = [d['spec']['branch'], 'origin/main']
        work = [(r['element'], r['rtl'][0], r['rtl'][1], r['element'] if not r['element'].endswith('__pv*') else '', 0)
                for r in d['rows'] if r.get('rtl') and r['rtl'][1] and r['kind'] not in ('phy', 'relay')]
        visited = set()
        while work:
            owner, ref, path, mod, depth = work.pop()
            key = (ref, path, mod)
            if key in visited or depth > 6 or len(visited) > 3000: continue
            visited.add(key)
            for ch in module_children(ref, path, mod):
                if STD_RE.search(ch) or ch == mod: continue
                ref2, p2 = resolve(ch, [ref] + refs_base)
                if ch in hardenable and not PHY_RE.search(ch):
                    if ch not in have:
                        d['rows'].append(row(ch, 'tile', parent=owner, source=f'RTL child of {owner}', rtl=(ref2, p2) if p2 else None))
                        have.add(ch)
                    if p2: work.append((ch, ref2, p2, ch, depth + 1))
                elif p2:
                    work.append((owner, ref2, p2, ch, depth + 1))
        kids = collections.Counter(r['parent'] for r in d['rows'])
        for r in d['rows']:
            if kids.get(r['element']) and r['kind'] == 'tile': r['kind'] = 'cluster'

    # ---- live work -> cells ----
    fleet_cells = collections.defaultdict(list); fleet_text = []
    for f in fleet:
        nm = f.get('name') or ''
        desc = f"{f.get('host')}:{f.get('kind')}:{nm[:60]} ({ago(f.get('start'))})"
        if f.get('kind') == 'loop route':
            try:
                fleet_cells[json.load(open(JOBS / f'{nm}.json'))['spec']['block']].append(('routing', desc, f.get('start'))); continue
            except Exception: pass
        m = re.match(r'ref_gate (\S+)', nm)
        if m and kit_top.get(m.group(1)):
            fleet_cells[kit_top[m.group(1)]].append(('gating', desc + f' kit {m.group(1)}', f.get('start'))); continue
        fleet_text.append((desc, nm + ' ' + str(f.get('detail')), f.get('start')))
    for c in clients:
        m = re.search(r'ref_gate_(.+?)_\d{8}-\d{6}\.sh', c['text'])
        if m and kit_top.get(m.group(1)):
            fleet_cells[kit_top[m.group(1)]].append(('gating', c['desc'], NOW - c['elapsed'])); continue
        fleet_text.append((c['desc'], c['text'], NOW - c['elapsed']))

    die_of = {}
    for d in dies:
        for r in d['rows']: die_of.setdefault(r['element'], d['die'])

    # ---- successor / family / stem attach of live or 24-h work ----
    recent = {b for b, v in jobs.items() if NOW - v[-1]['t'] < 24 * 3600} | set(fleet_cells) | \
             {g for g, v in gates.items() if NOW - v['t'] < 24 * 3600}
    unattached = []
    for c in sorted(recent):
        if not c or c in die_of or collapse(c) in die_of or STD_RE.search(c): continue
        d = next((x for x in dies if re.search(x['spec']['ns'], c)), None)
        if not d: continue
        names = {r['element'] for r in d['rows']}
        tgt = SUCCESSOR.get(d['die'], {}).get(c)
        if not tgt:
            for rx, p in FAMILY.get(d['die'], []):
                if re.search(rx, c): tgt = p; break
        if not tgt:
            sc = stem(c)
            hits = [n for n in names if len(stem(n)) >= 10 and (stem(n) == sc or sc.startswith(stem(n) + '_') or stem(n).startswith(sc + '_'))]
            if len(hits) == 1: tgt = hits[0]
        if tgt and tgt.startswith('(') and tgt not in names:
            d['rows'].append(row(tgt, 'relay' if ('relay' in tgt or 'lane' in tgt) else 'cluster', source='family group')); names.add(tgt)
        if tgt and tgt in names:
            d['rows'].append(row(c, 'tile', parent=tgt, source='successor/family (live or 24-h work)')); die_of[c] = d['die']
        else:
            unattached.append((d['die'], c))

    def state_of(e, r):
        names = [e] if '__pv*' not in e else (sorted(b for b in jobs if collapse(b) == e) or [e])
        if e.startswith('kit:'): names = [kit_top.get(e[4:]) or e]
        js = sorted([j for n in names for j in jobs.get(n, [])], key=lambda j: j['t'])
        live = [j for j in js if j['status'] in LIVE_ST and NOW - j['t'] < 24 * 3600]
        closed = [j for j in js if j['status'] == 'CLOSED' and j['name'] not in revoked]
        fails = [j for j in js if j['status'] in FAIL_ST or j['status'].startswith('EARLY_FAIL')]
        fl = [x for n in names for x in fleet_cells.get(n, [])]
        al = set().union(*(aliases(n) for n in names)) | aliases(e)
        for desc, txt, t0 in fleet_text:
            if al and mentions(txt, al, 10):
                fl.append(('bench' if re.search(r'bench|lockstep|equiv|tb_|verilator|iverilog|svc_rs|hgi_sim|sim', txt) else 'other', desc, t0))
        un = [u['unit'] for u in units if al and mentions(u['text'], al, 10)]
        rg = regby.get(names[0]) or {}
        nat = (rg.get('die_bindable') or {}).get('native')
        rc = natives.get(names[0])
        if rc and (not nat or rc[1] > (rg.get('closed_t') or 0)): nat = rc[0]
        if r.get('view_native') == 'PASS' and not str(nat or '').startswith('PASS'): nat = 'PASS (bind table)'
        return dict(names=names, jobs=js, live=live, closed=closed, fails=fails, fleet=fl, units=un, reg=rg, native=nat,
                    gate=gates.get(names[0]), al=al)

    out_rows = []
    for d in dies:
        spec = d['spec']
        drun = [desc for desc, txt, t0 in fleet_text if re.search(spec['die_re'], txt)]
        dt0 = [t0 for desc, txt, t0 in fleet_text if re.search(spec['die_re'], txt) and t0]
        dl = sorted((ln for ln in lanes if re.search(spec['lanes_re'], ln)), key=lambda ln: -lanes[ln]['t'])
        hn = HARD_NOTES.get((d['die'], '(die top)'))
        out_rows.append(dict(design=d['design'], die=d['die'], element='(die top)', kind='die', count='', parent='',
                             stage='die run LIVE' if drun else 'NO DIE RUN', live=' ; '.join(drun)[:400],
                             owner=', '.join(dl[:5]) or 'none', last_activity='0.0h' if drun else '-', last_t=NOW if drun else None,
                             reason='; '.join(f'{k}: {v}' for k, v in d['sources'].items())[:600], source='die case',
                             hard=bool(hn), iter_h=max([hn[0] or 0] + [(NOW - t) / 3600 for t in dt0]) if hn else None,
                             hard_reason=hn[1] if hn else '', fails=0, bucket='die'))
        for r in d['rows']:
            e = r['element']; st = state_of(e, r)
            lat = st['jobs'][-1] if st['jobs'] else None
            live = [('routing', f"{j['name']} {j['status']}/{j['stage'] or '-'}", j['t0'] or j['t']) for j in st['live']] + st['fleet']
            kinds = [k for k, _, _ in live]
            closed_ok = bool(st['closed']) and (not lat or lat['status'] in ('CLOSED', 'CANCELLED') or lat['status'] in LIVE_ST
                                                or lat['t'] <= st['closed'][-1]['t'])
            closed_ok = closed_ok or bool(r.get('view_closed')) or (st['reg'].get('category') or '').startswith('closed')
            nat = str(st['native'] or '')
            if r['kind'] == 'phy': stage = 'PHY model'
            elif closed_ok and nat.startswith('PASS'): stage = 'CLOSED+native'
            elif 'routing' in kinds: stage = 'routing'
            elif 'gating' in kinds: stage = 'gating'
            elif 'bench' in kinds: stage = 'bench'
            elif closed_ok: stage = 'CLOSED (native FAIL)' if nat.startswith('FAIL') else 'CLOSED (native owed)'
            elif r.get('no_rtl'): stage = 'NOT STARTED (no RTL)'
            elif r.get('rtl') or st['jobs'] or st['gate']: stage = 'RTL-only'
            else: stage = 'NOT STARTED'
            if stage == 'CLOSED+native' and kinds: stage += ' (+' + kinds[0] + ')'
            if stage == 'RTL-only' and lat and (lat['status'] in FAIL_ST or lat['status'].startswith('EARLY_FAIL')):
                stage = f"RTL-only (last {lat['status']})"
            own = sorted((ln for ln, v in lanes.items() if st['al'] and mentions(v['text'], st['al'], 8)), key=lambda ln: -lanes[ln]['t'])
            if e.startswith('(') or not st['al']:
                own = sorted((ln for ln in lanes if re.search(spec['lanes_re'], ln)), key=lambda ln: -lanes[ln]['t'])[:2]
            jown = sorted({str(j['owner']) for j in st['live'] if j.get('owner')})
            owner = ', '.join(jown + own[:4] + [f'unit:{u}' for u in st['units']]) or 'none'
            ts = [j['t'] for j in st['jobs']] + ([st['gate']['t']] if st['gate'] else []) + ([NOW] if live else [])
            last = max(ts) if ts else None
            walls = [x for j in st['jobs'] for x in j.get('iters') or []]
            med = round(statistics.median(walls), 1) if walls else None
            live_h = max([(NOW - t0) / 3600 for _, _, t0 in live if t0] or [0])
            ram = max([j['ram'] or 0 for j in st['jobs']] or [0])
            sinks = (st['gate'] or {}).get('sinks') or 0
            hn = HARD_NOTES.get((d['die'], e))
            why = []
            if med and med > HARD_H: why.append(f'median route iteration {med} h ({len(walls)} attempts, launch->verdict)')
            if live_h > HARD_H: why.append(f'live job running {live_h:.1f} h')
            if len(st['fails']) >= HARD_FAILS:
                why.append(f"{len(st['fails'])} failed verdicts ({', '.join(sorted(set(j['status'] for j in st['fails']))[:4])})")
            if ram >= 96: why.append(f'route RAM {ram:g} GB')
            if sinks >= 40000: why.append(f'{sinks:,} sinks on one root at the gate')
            if hn: why.append(hn[1])
            hard = not stage.startswith('CLOSED+native') and (bool(hn) or (med or 0) > HARD_H or live_h > HARD_H or len(st['fails']) >= HARD_FAILS)
            est = max([x for x in (med, live_h if live_h > HARD_H else None, hn[0] if hn else None) if x] or [0]) or None
            reason = (f"latest {lat['name']} {lat['status']} {ago(lat['t'])}: {lat['reason']}" if lat else
                      (f"registry: {st['reg'].get('category')}" if st['reg'] else 'no closure job'))
            if st['gate']: reason = f"gate {st['gate']['kit']} {st['gate']['verdict']} {ago(st['gate']['t'])} | " + reason
            if r.get('view'): reason = f"view {str(r['view'])[:90]} | " + reason
            if r.get('note'): reason = r['note'][:160] + ' | ' + reason
            out_rows.append(dict(design=d['design'], die=d['die'], element=e, kind=r['kind'], count=r['count'], parent=r['parent'],
                                 stage=stage, live=' ; '.join(x[1] for x in live)[:400], owner=owner[:240],
                                 last_activity=ago(last) if last else '-', last_t=last, reason=reason[:420], source=r['source'],
                                 native=st['native'], registry_category=st['reg'].get('category'),
                                 fails=len(st['fails']), iter_h=round(est, 1) if est else None, hard=hard, hard_reason='; '.join(why)[:420]))

    # parents: child summary; an open parent whose children have live work is covered through them
    for d in dies:
        rs = [r for r in out_rows if r['die'] == d['die'] and r['kind'] != 'die']
        for p in rs:
            ch = [r for r in rs if r['parent'] == p['element'] and r is not p]
            if not ch: continue
            c = collections.Counter('closed' if r['stage'].startswith('CLOSED+') else
                                    ('live' if (r['stage'] in ('routing', 'gating', 'bench') or '(+' in r['stage'] or 'children live' in r['stage'])
                                     else ('phy' if r['stage'].startswith('PHY') else 'open')) for r in ch)
            p['children'] = dict(c)
            p['reason'] = f"children {len(ch)}: closed {c.get('closed', 0)} / live {c.get('live', 0)} / open {c.get('open', 0)} | " + p['reason']
            if p['stage'].startswith(('RTL-only', 'NOT STARTED', 'CLOSED (native owed)')) and c.get('live'):
                p['stage'] = p['stage'] + ' (children live)'
            if p['element'].startswith('(') and p['stage'].startswith(('RTL-only', 'NOT STARTED')):
                p['stage'] = 'family: ' + ('all closed' if not c.get('open') and not c.get('live') else 'open')
                if not c.get('open') and not c.get('live'): p['stage'] = 'CLOSED+native (family)'

    def bucket(r):
        s = r['stage']
        if r['kind'] == 'die': return 'die'
        if s.startswith('PHY'): return 'n/a'
        if s.startswith('CLOSED+native'): return 'closed+native'
        if s in ('routing', 'gating', 'bench') or s.endswith('(children live)'): return 'live'
        return 'open-with-owner' if r['owner'] != 'none' else 'IDLE-NO-OWNER'
    for r in out_rows: r['bucket'] = bucket(r)

    def version(r):
        # owner 10-18 question: does every open element have at least one version routing or in STA?
        st = r['stage']
        if r['bucket'] in ('die', 'n/a', 'closed+native'): return None
        if r['bucket'] == 'live': return 'live now (route/gate/bench)'
        if st.startswith('CLOSED') or st.startswith('family'): return 'routed version exists (native/STA owed)'
        return 'NO version routed or in STA'
    for r in out_rows: r['version'] = version(r)

    summ = collections.OrderedDict()
    for d in dies:
        rs = [r for r in out_rows if r['die'] == d['die'] and r['kind'] != 'die']
        c = collections.Counter(r['bucket'] for r in rs); sc = collections.Counter(re.sub(r' \(.*', '', r['stage']) for r in rs)
        summ[d['die']] = dict(total=len(rs), **{k: c.get(k, 0) for k in ('closed+native', 'live', 'open-with-owner', 'IDLE-NO-OWNER', 'n/a')},
                              version=dict(collections.Counter(r['version'] for r in rs if r['version'])),
                              stages=dict(sc), hard=sum(1 for r in out_rows if r['die'] == d['die'] and r['hard']))
    hard_rows = sorted([r for r in out_rows if r['hard']], key=lambda r: ([x['die'] for x in dies].index(r['die']), -(r['iter_h'] or 0), -r['fails']))
    res = dict(schema='opentallas.gaps.die_element_table.v2', generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               generator=str(Path(__file__).resolve()), lanes_last_3h=sorted(lanes), units=[u['unit'] for u in units],
               clients=len(clients), dies=[dict(design=d['design'], die=d['die'], sources=d['sources']) for d in dies],
               summary=summ, rows=out_rows,
               hard=[dict(die=r['die'], element=r['element'], stage=r['stage'], iter_h=r['iter_h'], fails=r['fails'], reason=r['hard_reason'])
                     for r in hard_rows],
               unattached_recent=[dict(die=a, element=b) for a, b in unattached])
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str))

    # ---- markdown ----
    esc = lambda s: str(s if s is not None else '').replace('|', '/').replace('\n', ' ')
    L = [f"# Die element table ({res['generated']})", '',
         f"Generator `{res['generator']}` (v2, ELEMENT-TABLE 10-18); JSON `{OUT_JSON}`.",
         'Owner = live job, else lane files modified in the last 3 h that name the element, running ot-run clients, systemd units. '
         'Live = a closure-loop route, a ref_gate, or a bench client naming the element (or, for a parent, one of its children).', '',
         '| Die | elements | CLOSED+native | live (route/gate/bench) | open, owner named | IDLE-NO-OWNER | PHY | hard to iterate |',
         '|---|---|---|---|---|---|---|---|']
    for k, v in summ.items():
        L.append(f"| {k} | {v['total']} | {v['closed+native']} | {v['live']} | {v['open-with-owner']} | {v['IDLE-NO-OWNER']} | {v['n/a']} | {v['hard']} |")
    L += ['', 'Stages: ' + '; '.join(f"**{k}** " + ', '.join(f'{s} {n}' for s, n in sorted(v['stages'].items())) for k, v in summ.items()), '']
    L += ['## Open elements: is there a version routing or in STA?', '',
          '| Die | open | live now | routed version exists (native/STA owed) | NO version routed or in STA | of which IDLE-NO-OWNER |',
          '|---|---|---|---|---|---|']
    for d in dies:
        rs = [r for r in out_rows if r['die'] == d['die'] and r['version']]
        cv = collections.Counter(r['version'] for r in rs)
        nv = [r for r in rs if r['version'].startswith('NO')]
        L.append(f"| {d['die']} | {len(rs)} | {cv.get('live now (route/gate/bench)', 0)} | {cv.get('routed version exists (native/STA owed)', 0)} | "
                 f"{len(nv)} | {sum(1 for r in nv if r['bucket'] == 'IDLE-NO-OWNER')} |")
    L.append('')
    for d in dies:
        nv = [r for r in out_rows if r['die'] == d['die'] and (r['version'] or '').startswith('NO')]
        L.append(f"- **{d['die']}** no version ({len(nv)}): " + (', '.join(f"`{r['element']}` [{r['stage']}; owner {r['owner'][:40]}; last {r['last_activity']}]" for r in nv) or 'none'))
    L.append('')
    L += ['## IDLE-NO-OWNER (open, nothing live, no 3-h lane names it)', '']
    for d in dies:
        idle = [r for r in out_rows if r['die'] == d['die'] and r['bucket'] == 'IDLE-NO-OWNER']
        L.append(f"- **{d['die']}** ({len(idle)}): " + (', '.join(f"`{r['element']}` [{r['stage']}; parent {r['parent']}; last {r['last_activity']}]" for r in idle) or 'none'))
    L += ['', '## Hard to iterate (one iteration > ~3 h, or >= 3 failed verdicts)', '',
          '| die | element | stage | iteration (h) | failed verdicts | reason |', '|---|---|---|---|---|---|']
    for r in hard_rows:
        L.append(f"| {r['die']} | {esc(r['element'])} | {esc(r['stage'])} | {r['iter_h'] if r['iter_h'] else '?'} | {r['fails']} | {esc(r['hard_reason'])[:280]} |")
    L.append('')
    order = {'die': 0, 'IDLE-NO-OWNER': 1, 'open-with-owner': 2, 'live': 3, 'closed+native': 4, 'n/a': 5}
    for d in dies:
        L += [f"## {d['die']} ({d['design']})", '', 'Sources: ' + esc('; '.join(f'{k}: {v}' for k, v in d['sources'].items())), '',
              '| element | kind | parent | stage | live job | owner | last activity | reason / note |', '|---|---|---|---|---|---|---|---|']
        rs = [r for r in out_rows if r['die'] == d['die']]
        for r in sorted(rs, key=lambda r: (order.get(r['bucket'], 9), r['parent'] != '(die)', r['parent'], r['element'])):
            L.append(f"| {esc(r['element'])} | {r['kind']} | {esc(r['parent'])} | {esc(r['stage'])} | {esc(r['live'])[:120]} | "
                     f"{esc(r['owner'])[:90]} | {r['last_activity']} | {esc(r['reason'])[:180]} |")
        L.append('')
    L += [f"## Unattached recent work ({len(unattached)}): live or 24-h jobs in a die namespace that match no current element", '',
          'A successor the die case does not bind yet, or obsolete work.', '']
    for k in [d['die'] for d in dies]:
        u = sorted(b for a, b in unattached if a == k)
        if u: L.append(f"- **{k}** ({len(u)}): " + ', '.join(u))
    OUT_MD.write_text('\n'.join(L) + '\n')
    if not ARGS.quiet:
        print('\n'.join(L[:12]))
        for d in dies:
            idle = [r['element'] for r in out_rows if r['die'] == d['die'] and r['bucket'] == 'IDLE-NO-OWNER']
            print(f"IDLE-NO-OWNER {d['die']} ({len(idle)}): " + ', '.join(idle))
        print('hard:', len(hard_rows), 'unattached:', len(unattached))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-ssh', action='store_true', help='use cached die_inputs/ instead of fetching from ot-epyc4')
    ap.add_argument('--quiet', action='store_true')
    ARGS = ap.parse_args()
    main()
