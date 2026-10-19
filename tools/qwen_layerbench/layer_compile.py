#!/usr/bin/env python3
"""LAYERBENCH-QWEN 2026-10-18 (TOK.QW.BENCH.1): layer-programme compiler for the Qwen3-8B ROM split dies
(compute dv2f14bn + KV/system kvs14c), the pass the layer bench loads its images from.

    layer_compile.py --out DIR --compute-stages C.json --kv-stages K.json --compute-die-v die.v [--compute-lanes fwd_lanes.json]
                     [--token-path TP] [--link-handoff H]
                     [--compute-commit 0a9c93921] [--kv-commit f05f9338f] [--txl 6] [--phy 5]

C.json / K.json are the die-RUN relay tables (opentallas.die_relay_stages.v1, role die_plan, coverage complete):
tools/qwen_layerbench/netlist_relay_stages.py walks the GEN netlist of each die (compute die.v reproduces the
generator's own export digest exactly; the KV case never exported one).  From them and the compiler's priced static
schedule (results/arch/token_path_20261009/qwen_rom.json, the 36-layer token path every Qwen link calendar is compiled
from) this pass emits, fail closed:

 1. relay_schedule/{compute,kv}_compiled.json[.gz]: OT_RELAY_SCHEDULE tables (role compiled_schedule) = the die table
    with every seam bus this pass scheduled substituted by the stage count the calendars were compiled with, and
    relay_check_{compute,kv}.json = tools/die_relay_check.py run against the die-run table (so the die chain's
    'RELAY_CHECK SKIPPED' becomes a real check: OT_RELAY_SCHEDULE=<compiled table>).
 2. d2d/: D2D calendars compiled with the REAL die stages (TOKEN-XDIE-QWEN F4): seam ages read from the die tables
    (compute landed n = 1 lanes: age = landing K; plain relays: one edge a flop), per-port producer capture latency
    TXD (= the qfd_d2d_static / qkd_d2d_static TXDP parameter vector), the attention-window extension X that makes the
    link calendar meet the kvs14c attention programme's FIXED ages (qkd_attn_cal_gen RX_CMD / SERVICE_END, read from
    the KV RTL at --kv-commit), the L1 decode-layer image (cal_L1/), the full 36-layer + token-run (L0) + admission
    program (program/, via tools/qwen_split/d2d_link_calendar.py --profile program on the X-extended token path) and
    its RTL include d2d_cal_image.svh (tools/qwen_split/d2d_cal_seq_image.py).
 3. kv_programme/: the kvs14c u_lprg (qkd_static_kv_layer_programme, boot-loaded over cfg_we/addr/data) boot image
    boot.hex + layer_programme_image.svh + layer_roots.json, compiled on the program calendar of 2 by
    tools/qwen_static_kv/layer_roots_from_link.py.
 4. compute_programme/: what the compute-die controllers load, with the parts no compiler emits recorded as gaps:
    sys_face_events.json (qfd_sys_face T calendar from the compiled program; L KVSLOT / VIS from the compiled
    exchange) and gaps.json (module, port, what is missing).
 + findings.json (bundle-age mismatches, RTL-baked constants that disagree with the compiled ones) and manifest.json
   (sha256 of every emitted file, the inputs and their sha256, source commits).

Compute seam ages (QW-L1SEAM 10-19): ONE source with the strict bind -- tools/qwen_split/record_bundles.py seam_stages on
the compute GEN die.v + fwd_lanes.json (lane cycles: forwarded E + 1, plain n, direct 0), the function DIE_PARAM_AUDIT (e)
checks the bound TXDP with.  The compute bundle selectors and the CS_*/SC_* stage map are record_bundles' own; the die
table's relay HOP counts (a one-frame landing = 1 hop, 2 edges) are never seam ages.  The compute die table is annotated
with those ages (age_edges) before the relay check, so die_relay_check's torn-bundle check reads them too.

Bundles: a static record crosses the die as one bundle (valid + slot + kind + beat + payload); its members must reach
the consumer on ONE age or the record is torn (TOKEN-XDIE-QWEN F5 / F6).  The calendars are compiled at every
bundle's MAX member age (the age the record is complete); a bundle whose members differ is a finding, and the compiled
relay schedule carries the max for every member, so die_relay_check FAILS on exactly those lanes until the die lands
whole bundles.  This is reported, never hidden.
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
import die_relay_stages as DRS   # noqa: E402
import die_relay_check as DRC    # noqa: E402
import d2d_link_calendar as L    # noqa: E402
import record_bundles as RB      # noqa: E402

CONSUMER = 'tools/qwen_layerbench/layer_compile.py'
# producer codec edges + PR = 1 pin flops: ONE definition, tools/qwen_split/d2d_link_calendar.py (QXF-LINK), the same the
# strict-bind DIE_PARAM_AUDIT (e) derives the bound TXDP from (QW-L1SEAM 10-19)
N59_TX, N59_X3, KV_CODEC, PINREG_EXT = L.N59_TX, L.N59_X3, L.KV_CODEC, L.PINREG_EXT

# seam bundles: name -> (side, [(src_inst, src_port, dst_inst)]) ; selection by src pin + destination instance.
# QW-L1SEAM 10-19: the compute side is NOT listed here -- it is tools/qwen_split/record_bundles.py COMPILER_BUNDLES +
# SEAM_SINGLE (the bundles the GEN lands whole and strict bind audits), so the compiler and the bind cannot diverge.
COMPUTE_SEAM = tuple(RB.COMPILER_BUNDLES) + tuple(RB.SEAM_SINGLE)
BUNDLES = {
    **{b: ('qwen_compute', [(s, sp, d) for s, sp, d, _ in {**RB.BUNDLES, **RB.SEAM_SINGLE}[b]]) for b in COMPUTE_SEAM},
    'K.rx_record': ('qwen_kv', [('d2d_kv', p, 'kvs_attn') for p in ('att_rx_v', 'att_rx_kind', 'att_rx_beat', 'rx_payload')]),
    'K.tx_slot':   ('qwen_kv', [('d2d_kv', p, 'kvs_attn') for p in ('att_tx_slot', 'att_tx_kind', 'att_tx_beat')]),
    'K.tx_record': ('qwen_kv', [('kvs_attn', p, 'd2d_kv') for p in ('attn__tx_valid', 'attn__tx_payload')]),
}
# calendar stage names (xdie_exchange_cal.py --stages order) -> the bundle whose compiled age they take
# (compute part = record_bundles.SEAM_STAGE_OF, the strict-bind TXDP audit's map)
STAGE_OF = dict(RB.SEAM_STAGE_OF, KS_RXV='K.rx_record', KS_RXP='K.rx_record', KS_TXS='K.tx_slot', KS_TXK='K.tx_slot',
                KS_TXB='K.tx_slot', SK_TXV='K.tx_record', SK_TXP='K.tx_record')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_show(commit, path):
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'layer_compile: git show {commit}:{path}: {r.stderr.strip()[:200]}')
    return r.stdout


def bus_age(b):
    a = b.get('age_edges', b['stages'] if 'age_basis' not in b else None)
    return a


def compute_seam(die_v, lanes=None):
    """QW-L1SEAM 10-19: the compute D2D seam ages AS BUILT, from the SAME source the strict bind's DIE_PARAM_AUDIT (e)
    and RECORD_BUNDLE_AUDIT use: record_bundles.seam_stages(die.v, fwd_lanes.json) (lane cycles per member: forwarded
    lane E + 1, plain relay n, direct 0).  The relay table's 'stages' are HOP counts (a one-frame landing is 1 hop but
    2 edges), so they are never used as compute seam ages.  -> (stages {CS_TXS..SC_X3}, {(src_inst, src_port, dst_inst):
    cycles}, record).  Fail closed on any problem (missing member, unreadable lane, torn bundle)."""
    die_v = Path(die_v)
    if lanes is None and (die_v.parent / 'fwd_lanes.json').exists():
        lanes = die_v.parent / 'fwd_lanes.json'
    st, rec, problems = RB.seam_stages(die_v, lanes)
    if problems or st is None:
        raise SystemExit('layer_compile: compute seam (record_bundles.seam_stages) of ' f'{die_v}: ' + '; '.join(problems))
    bset = {b: {**RB.BUNDLES, **RB.SEAM_SINGLE}[b] for b in COMPUTE_SEAM}
    _, info, _ = RB.netlist_members(die_v.read_text(), bset)
    per_key = {}
    for b in rec['bundles'].values():
        for bid, c in b['members'].items():
            (s, sp), d = info[bid]['key'].split('->')[0].split('.'), info[bid]['key'].split('->')[1].split('.')[0]
            per_key[(s, sp, d)] = c
    return st, per_key, rec


def annotate_seam_ages(doc, seam):
    """the compute die-run table with every seam member's age_edges set to its record_bundles lane cycles (age_edges is
    not part of the table digest), so die_relay_check's torn-bundle check (tools/die_record_bundles.py) reads the same
    ages as the strict bind.  -> (doc copy, [(bus, table age, seam age)] where the exporter's age differed)."""
    d = json.loads(json.dumps(doc))
    diff = []
    for b in d['buses']:
        k = (b['src']['inst'], b['src']['port'], b['dst']['inst'])
        if k in seam:
            old = b.get('age_edges', b['stages'])
            if old != seam[k]:
                diff.append((b['id'], old, seam[k]))
            b['age_edges'], b['age_basis'] = seam[k], 'record_bundles.seam_stages lane cycles (strict-bind source)'
    return d, diff


def bundle_ages(tables, seam=None):
    """-> {bundle: dict(members=[{bus, stages, age}], age=max, consistent)}; fail closed on a missing member.
    seam: {bid: lane cycles} of the compute die (compute_seam): REQUIRED for the compute bundles (one source of truth)."""
    out = {}
    for name, (design, sel) in BUNDLES.items():
        T = tables[design]
        mem = []
        for si, sp, di in sel:
            bs = T.match(src_inst=si, src_port=sp, dst_inst=di)
            if not bs:
                raise SystemExit(f'layer_compile: bundle {name}: no die bus {si}.{sp} -> {di}.* in the {design} table')
            for b in bs:
                if design == 'qwen_compute':
                    if seam is None:
                        raise SystemExit('layer_compile: compute seam ages come only from record_bundles.seam_stages '
                                         '(--compute-die-v): never from relay hop counts')
                    k = (b['src']['inst'], b['src']['port'], b['dst']['inst'])
                    if k not in seam:
                        raise SystemExit(f'layer_compile: bundle {name}: {b["id"]} is not a seam member of the compute '
                                         f'die.v (record_bundles): table and netlist disagree')
                    mem.append(dict(bus=b['id'], stages=b['stages'], age=seam[k], width=b['width'],
                                    age_source='record_bundles.seam_stages'))
                    continue
                a = bus_age(b)
                if a is None:
                    raise SystemExit(f'layer_compile: bundle {name}: {b["id"]} is a landed lane without a land-plan age '
                                     f'(K {b.get("landing_k")}): needs land_plan.json')
                mem.append(dict(bus=b['id'], stages=b['stages'], age=a, width=b['width']))
        ages = sorted({m['age'] for m in mem})
        out[name] = dict(design=design, members=mem, age=max(ages), consistent=len(ages) == 1, ages=ages)
    return out


def kv_codec_edges(tile_rtl):
    """Read the implemented codec from the source-pinned attention tile, never an environment default."""
    tile = re.search(r'module\s+qkd_kvs_attn\b(.*?)endmodule', tile_rtl, re.S)
    if not tile:
        raise SystemExit('layer_compile: qkd_kvs_attn tile not found')
    inst = re.search(r'qkd_native_attention_programme\s*#\((.*?)\)\s*u_attn\s*\(', tile.group(1), re.S)
    if not inst:
        raise SystemExit('layer_compile: qkd_kvs_attn native attention programme not found')
    land = re.search(r'\.LAND\(([^)]+)\)', inst.group(1))
    # The historical programme has no LAND override and its RTL default is zero.
    value = land.group(1).strip() if land else '0'
    if value not in ('0', '1'):
        raise SystemExit(f'layer_compile: unsupported attention LAND value {value!r}')
    return 1 + int(value)


def kv_programme_constants(kv_commit):
    t = git_show(kv_commit, 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv')
    m = re.search(r'qkd_attn_cal_gen\s*#\(([^)]*(?:\([^)]*\)[^)]*)*)\)\s*u_attn_cal', t)
    if not m:
        raise SystemExit('layer_compile: qkd_kvs_attn u_attn_cal parameters not found in the KV RTL')
    prm = dict(re.findall(r'\.(\w+)\((\d+)\)', m.group(1)))
    rx, se, st = int(prm['RX_CMD']), int(prm['SERVICE_END']), int(prm['STRETCH'])
    if st != 1:
        raise SystemExit(f'layer_compile: qkd_attn_cal_gen STRETCH {st}: only the STRETCH = 1 TX_FIRST law is known')
    return dict(RX_CMD=rx, SERVICE_END=se, STRETCH=st, TX_FIRST=rx + 2 + se - 31, KV_CODEC=kv_codec_edges(t),
                source=f'{kv_commit}:rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv u_attn_cal',
                law='TX_FIRST = RX_CMD + 2 + SERVICE_END - 31 (qkd_attn_cal_gen STRETCH = 1; TOKEN-XDIE-QWEN measured)')


D2D_RTL = 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'
D2D_IMAGE = 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'


def txdp_bound(rtl, image, end):
    """TXDP the die master of END ('C' compute / 'K' KV) actually elaborates with, from source text.

    Pre-QXF-LINK RTL hard-wires a literal vector in the core instance (PR ? {p3, p2, p1, p0}); from 6ef1a097f the wrapper
    takes TXDP as a REQUIRED parameter (default 32'd0 refuses elaboration) and the die GEN binds D2D_TXDP_<END> of the
    committed calendar image (kv_static.compiled_txdp).  Returns (ports [p0..p3], source tag); never a default."""
    core, top = {'C': ('qfd_d2d_static_core', 'qfd_d2d_static'), 'K': ('qkd_d2d_static_core', 'qkd_d2d_static')}[end]
    m = re.search(core + r"\s*#\([^;]*?\.TXDP\(PR \? \{8'd(\d+), 8'd(\d+), 8'd(\d+), 8'd(\d+)\}", rtl, re.S)
    if m:
        return [int(x) for x in m.groups()][::-1], 'rtl_literal'       # {p3, p2, p1, p0} -> [p0..p3]
    if not re.search(r'module\s+' + top + r"\s*#\([^)]*parameter\s*\[31:0\]\s*TXDP\s*=\s*32'd0\b", rtl, re.S):
        raise SystemExit(f'layer_compile: {top}: neither a literal PR TXDP nor a required TXDP parameter')
    if image is None:
        raise SystemExit(f'layer_compile: {top} takes a required TXDP but no calendar image was found at the commit')
    m = re.search(r"localparam\s*\[31:0\]\s*D2D_TXDP_" + end + r"\s*=\s*32'h([0-9a-fA-F]{8})\s*;", image)
    if not m:
        raise SystemExit(f'layer_compile: {D2D_IMAGE}: no D2D_TXDP_{end}')
    v = int(m.group(1), 16)
    return [(v >> (8 * b)) & 0xff for b in range(4)], 'image_parameter'


def git_show_opt(commit, path):
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def rtl_txdp(compute_commit, kv_commit=None, compute_params=None):
    """bound TXDP per end: the compute master from the compute die's source commit, the KV master from the KV die's.
    A required-parameter compute master takes the compute GEN's die.v.params.json qfd_d2d_static.TXDP when given
    (QLB-GEN assignment), else the committed image D2D_TXDP_C."""
    out, src = {}, {}
    for end, commit in (('C', compute_commit), ('K', kv_commit or compute_commit)):
        rtl = git_show(commit, D2D_RTL)
        if end == 'C' and compute_params and not re.search(
                r"qfd_d2d_static_core\s*#\([^;]*?\.TXDP\(PR \?", rtl, re.S):
            v = json.loads(Path(compute_params).read_text()).get('masters', {}).get('qfd_d2d_static', {}).get('TXDP')
            if v is None:
                raise SystemExit(f'layer_compile: {compute_params} assigns no qfd_d2d_static TXDP')
            out[end] = [(int(v) >> (8 * i)) & 0xff for i in range(4)]
            src[end] = f'{compute_params} qfd_d2d_static.TXDP (die_parameter)'
            continue
        out[end], kind = txdp_bound(rtl, git_show_opt(commit, D2D_IMAGE), end)
        src[end] = f'{commit}:{D2D_RTL if kind == "rtl_literal" else D2D_IMAGE} ({kind})'
    return out, src


def compile_stages(ba):
    return {k: ba[b]['age'] for k, b in STAGE_OF.items()}


def txd_of(S, kv_codec=KV_CODEC):
    raw_c = L.producer_txd(S)['C']           # the same function DIE_PARAM_AUDIT (e) checks the bound TXDP with
    raw_k = [S['KS_TXS'] + kv_codec + S['SK_TXP'], 2, 1, 1]
    return dict(C=raw_c, K=raw_k), {e: [x + p for x, p in zip(v, PINREG_EXT[e])] for e, v in (('C', raw_c), ('K', raw_k))}


def extension(w, txd, S, kvp, txl, phy):
    """attn_kv extension X (edges) so the RESULT slots meet the KV programme's fixed TX_FIRST (xdie_exchange_cal law)"""
    txl_p, phy_p, phy_c = txl + 2, phy + 2, phy + 2
    q0 = sum(w[:3])
    arr_cmd = q0 + txd['C'][0] - 1 + txl + phy_c
    t_cmd_prog = arr_cmd + 2 + S['KS_RXV']
    r0_need = t_cmd_prog + (kvp['TX_FIRST'] - kvp['RX_CMD']) - S['KS_TXS']
    r0_priced = q0 + w[3] - (txl_p + phy_p + 3) - 33
    return dict(X=r0_need - r0_priced, q0=q0, arr_cmd=arr_cmd, cmd_at_programme=t_cmd_prog, r0_needed=r0_need,
                r0_priced=r0_priced, kv_run=t_cmd_prog - kvp['RX_CMD'] - 1)


def extend_token_path(tp, X):
    """copy of the token path with L<n>.attn_kv lengthened by X[L] edges; groups / totals re-timed (serial path)"""
    d = json.loads(json.dumps(tp))
    nodes = {n['id']: n for n in d['nodes']}
    shift = 0.0
    for g in d['groups']:
        g['start'] = float(g['start']) + shift
        x = float(X.get(g['id'], 0))
        if x:
            nodes[f"{g['id']}.attn_kv"]['cycles'] = float(nodes[f"{g['id']}.attn_kv"]['cycles']) + x
            g['cycles'] = float(g['cycles']) + x
        g['end'] = g['start'] + float(g['cycles'])
        shift += x
    d['totals'] = dict(d['totals'], cycles=float(d['totals']['cycles']) + shift,
                       compiled_extension=dict(X, note='attn_kv windows lengthened by layer_compile.py (exposed latency)'))
    return d


def sys_face_events(prog_cal, svh, S, ex, txd, n59_land_edges):
    """qfd_sys_face T calendar (the run_sys_face_bench.sh token timeline from the compiled program) + the L events
    this compiler can place (KVSLOT before each x3 slot, VIS / complete after the last RESULT lands)."""
    img = Path(svh).read_text()
    iv = lambda n: int(re.search(rf'{n} = (\d+)', img).group(1))
    v = int(re.search(r"D2D_CAL_START = 720'h([0-9a-f]+)", img).group(1), 16)
    st = [(v >> (20 * i)) & ((1 << 20) - 1) for i in range(36)]
    period, first = iv('D2D_TOKEN_PERIOD'), iv('D2D_FIRST_TOKEN')
    prog = prog_cal['program']
    c0, l0 = 3, prog['layers'][0]['start']
    emb = prog['emb_send'][0]
    T = [(c0, 5, 128), (c0 + emb, 0, 0), (c0 + l0, 0, 1 | 64), (c0 + l0 + 2, 1, 3)]
    T += [(c0 + st[i], 0, (i + 1) | 64) for i in range(1, 36)]
    T += [(c0 + period - 40 - c0, 0, 37 | 256), (period, 1, 4)]
    tab = prog_cal['messages']
    kv = sorted((t for t in tab if t.get('seg', 0) == 0 and t['src'] == 'C' and t['tx_port'] == 3), key=lambda t: t['cyc'])
    r = sorted((t for t in tab if t.get('seg', 0) == 0 and t['src'] == 'K' and t['tx_port'] == 0), key=lambda t: t['cyc'])
    kvslot = [(kv[i]['cyc'] + S['CS_X3S'] - 3, 3, i) for i in range(4)]
    t31 = r[31]['arrive'] + 2 + S['CS_RXV']
    vis = t31 + 4 + n59_land_edges + 2
    Lev = kvslot + [(vis, 4, 0), (vis + 2, 4, 1)]
    return dict(first_token=first - c0, d2d_first_token=first, go_ofs=c0, T=T, L_compiled=Lev,
                L_missing=['QSLOT (class 2): no compiler relation for native59 q_slot vs the qkv result landing'],
                E_missing=['E calendar (EMBW / FILL): the KV embedding provider row timing is not compiled here'],
                land_edges_used=n59_land_edges)


def write_json(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, indent=1) + '\n')


def run(cmd, log):
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    Path(log).write_text(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f'layer_compile: {" ".join(cmd[:2])} failed (rc {r.returncode}): see {log}\n{r.stdout[-800:]}{r.stderr[-800:]}')
    return r.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--compute-stages', required=True); ap.add_argument('--kv-stages', required=True)
    ap.add_argument('--token-path', default='results/arch/token_path_20261009/qwen_rom.json')
    ap.add_argument('--link-handoff', default='results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json')
    ap.add_argument('--compute-params', help='compute die.v.params.json (TXDP as the die elaborates it)')
    ap.add_argument('--compute-die-v', required=True,
                    help='compute GEN die.v (the strict-bind input): the compute seam ages are record_bundles.seam_stages of it')
    ap.add_argument('--compute-lanes', help='compute fwd_lanes.json (default: next to --compute-die-v)')
    ap.add_argument('--compute-commit', default='0a9c93921'); ap.add_argument('--kv-commit', default='f05f9338f')
    ap.add_argument('--txl', type=int, default=6); ap.add_argument('--phy', type=int, default=5)
    ap.add_argument('--n59-land-edges', type=int, default=8,
                    help='qfd_native59_dv_service LAND_EDGES the die binds (dv2f14bn: default 8; see gaps)')
    ap.add_argument('--gz-over', type=int, default=4_000_000, help='write a compiled table gzipped above this many bytes')
    ap.add_argument('--kv-die-v', help='KVR-DERIVE: the bound KV die netlist (die_bound.v): instance bindings checked')
    ap.add_argument('--kv-case-die-v', help='KVR-DERIVE: the KV case die.v (+ .params.json): straps / relay clocks checked')
    ap.add_argument('--kv-static-model', help='HKV-DIE2: CASE/static_model.json (kv_die.py case): recompute the KV static '
                    'parameters (hub AP_OFS/FR_OFS, ASTK e_after_header, attention fault latencies, seq KVN bundle) on '
                    '--kv-stages and FAIL a finding where they disagree (tools/qwen_kv_die/kv_static_params.py)')
    ap.add_argument('--kv-fwd-lanes', help='RUN/fwd_lanes.json: landed lane ages for buses whose netlist age is not a stage count')
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    findings, gaps = [], []
    docs = {'qwen_compute': DRS.load(a.compute_stages), 'qwen_kv': DRS.load(a.kv_stages)}
    for k, d in docs.items():
        if d['role'] != 'die_plan' or d['coverage'] != 'complete':
            raise SystemExit(f'layer_compile: {k} table must be a complete die_plan export')
    tables = {k: DRS.Table(d) for k, d in docs.items()}
    seam_st, seam_key, seam_rec = compute_seam(a.compute_die_v, a.compute_lanes)
    docs['qwen_compute'], seam_diff = annotate_seam_ages(docs['qwen_compute'], seam_key)
    tables['qwen_compute'] = DRS.Table(docs['qwen_compute'])
    if seam_diff:
        findings.append(dict(id='SEAM_AGE_SOURCE', severity='INFO', owner='QW-L1SEAM',
                             what=f'{len(seam_diff)} compute seam buses: the die table age (relay hops / exporter age_fields) '
                                  'differs from the as-built lane cycles; compiled with record_bundles.seam_stages (the '
                                  'strict-bind DIE_PARAM_AUDIT / RECORD_BUNDLE_AUDIT source)',
                             lanes=[f'{i}: table {o} -> seam {n}' for i, o, n in seam_diff]))
    ba = bundle_ages(tables, seam_key)
    for n, b in ba.items():
        if not b['consistent']:
            findings.append(dict(id=f'BUNDLE_AGE {n}', severity='FAIL', owner='die lead (LAND_CROSS / KV seam)',
                                 what=f'{n} members reach the consumer at different ages {b["ages"]}: the static record is torn',
                                 lanes=[f"{m['bus']}: stages {m['stages']} age {m['age']}" for m in b['members']],
                                 fix=f'land the whole bundle at age {b["age"]} (pad the shorter members) or re-plan the seam'))
    S = compile_stages(ba)
    if {k: S[k] for k in seam_st} != seam_st:          # cannot happen unless STAGE_OF and record_bundles diverge
        raise SystemExit(f'layer_compile: compiled compute stages {S} != record_bundles.seam_stages {seam_st}')
    kvp = kv_programme_constants(a.kv_commit)
    raw, txd = txd_of(S, kv_codec=kvp['KV_CODEC'])
    hard, hard_src = rtl_txdp(a.compute_commit, a.kv_commit, a.compute_params)
    for e in ('C', 'K'):
        if hard[e] != txd[e]:
            findings.append(dict(id=f'TXDP {e}', severity='FAIL', owner='Q-LINK / die leads',
                                 what=f'{"qfd" if e == "C" else "qkd"}_d2d_static binds TXDP {hard[e]} (ports 0..3; '
                                      f'{hard_src[e]}); the die stages need {txd[e]}',
                                 fix=('commit this pass\'s d2d/d2d_cal_image.svh (D2D_TXDP_' + e + ') as the production image and '
                                      're-GEN the die' if hard_src[e].endswith('(image_parameter)') else
                                      'make TXDP a parameter of the die master set from this compiler (d2d/txdp.svh), '
                                      'or re-harden with the compiled vector')))
    # ------------------------------------------------------------------ windows / extension X
    tp = json.load(open(ROOT / a.token_path))
    _, lay = L.program_profile(a.txl + 2, a.phy + 2, str(ROOT / a.token_path), host_stages=0, st_ofs=40,
                               handoff=str(ROOT / a.link_handoff))
    win = {k: [lay['windows'][k][o] for o in ('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv')] for k in ('L0', 'L1_35')}
    ex = {k: extension(w, txd, S, kvp, a.txl, a.phy) for k, w in win.items()}
    X = {'L0': ex['L0']['X'], **{f'L{i}': ex['L1_35']['X'] for i in range(1, 36)}}
    if ex['L0']['X'] < 0:
        findings.append(dict(id='L0_WINDOW', severity='INFO', owner='Q-LINK + KV',
                             what=f"L0 (token run) priced attn_kv {win['L0'][3]} is {-ex['L0']['X']} edges LONGER than the "
                                  f"fixed KV service needs (TX_FIRST {kvp['TX_FIRST']}): compiled with the window shortened",
                             note='TOKEN-XDIE-QWEN F7 (222 at the stimulus codecs); the cold-fill price is not in the RTL service'))
    d2d = out / 'd2d'; d2d.mkdir(exist_ok=True)
    (d2d / 'txdp.svh').write_text(
        '// GENERATED by tools/qwen_layerbench/layer_compile.py: D2D producer capture latency per TX port (PR = 1)\n'
        f"localparam [31:0] QFD_D2D_TXDP = {{8'd{txd['C'][3]}, 8'd{txd['C'][2]}, 8'd{txd['C'][1]}, 8'd{txd['C'][0]}}};\n"
        f"localparam [31:0] QKD_D2D_TXDP = {{8'd{txd['K'][3]}, 8'd{txd['K'][2]}, 8'd{txd['K'][1]}, 8'd{txd['K'][0]}}};\n"
        + ''.join(f'localparam integer {k} = {v};\n' for k, v in S.items()))
    # L1 decode-layer image (segment 0, the 35 chained layers)
    w1 = list(win['L1_35']); w1[3] += X['L1']
    for st_ofs in range(40, 49):
        msgs, _ = L.layer_msgs(0, 0, w1, a.txl + 2, a.phy + 2, st_ofs)
        try:
            imgs, table, _ = L.compile_cal(msgs, a.txl, a.phy + 2, 0, txd)
            break
        except SystemExit as e:
            last = e
    else:
        raise last
    c1 = d2d / 'cal_L1'; c1.mkdir(exist_ok=True)
    for k, v in imgs.items():
        (c1 / f'cal_{k}.memh').write_text('\n'.join(f'{x:08x}' for x in v + [0] * (L.NE - len(v))) + '\n')
    r = [t for t in table if t['src'] == 'K' and t['tx_port'] == 0]
    assert r[0]['cyc'] == ex['L1_35']['r0_needed'], (r[0]['cyc'], ex['L1_35'])
    write_json(c1 / 'calendar.json', dict(schema='opentallas.qwen_layerbench.d2d_layer.v1', layer='L1..L35 (segment 0)',
                                          txl=a.txl, phy=a.phy, phy_compiled=a.phy + 2, pinreg=True, txd=txd, raw_txd=raw,
                                          stages=S, status_ofs=st_ofs, windows_priced=dict(zip(('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv'), win['L1_35'])),
                                          attn_extend_X=X['L1'], extension=ex['L1_35'], kv_programme=kvp,
                                          entries={k: len(v) for k, v in imgs.items()}, messages=table))
    # full program (token run incl. L0 + 35 layers + admission) on the X-extended token path
    prog = d2d / 'program'; prog.mkdir(exist_ok=True)
    tpx = d2d / 'token_path_compiled.json'
    write_json(tpx, extend_token_path(tp, X))
    host = tables['qwen_kv'].match(src_inst='host', src_port='record_tx', dst_inst='d2d_kv')
    host_stages = max(b['stages'] for b in host) if host else None
    if host_stages is None:
        raise SystemExit('layer_compile: KV host.record_tx -> d2d_kv bus missing (HOST stages)')
    run([sys.executable, 'tools/qwen_split/d2d_link_calendar.py', '--out', str(prog.resolve()), '--txl', str(a.txl), '--phy', str(a.phy),
         '--profile', 'program', '--txd-c', ','.join(map(str, raw['C'])), '--txd-k', ','.join(map(str, raw['K'])),
         '--host-stages', str(host_stages), '--link-handoff', a.link_handoff, '--pinreg', '--token-path', str(tpx.resolve())],
        d2d / 'program.log')
    run([sys.executable, 'tools/qwen_split/d2d_cal_seq_image.py', str(prog.resolve()), str((d2d / 'd2d_cal_image.svh').resolve())],
        d2d / 'image.log')
    pc = json.loads((prog / 'calendar.json').read_text())
    import gzip
    with gzip.open(str(tpx) + '.gz', 'wt') as f:          # kept compressed (reproducible: committed token path + X)
        f.write(tpx.read_text())
    tpx.unlink()
    # ------------------------------------------------------------------ KV layer programme (u_lprg boot image)
    kvo = out / 'kv_programme'
    run([sys.executable, 'tools/qwen_static_kv/layer_roots_from_link.py', str(prog.resolve()), str(kvo.resolve())], out / 'kv_programme.log')
    # ------------------------------------------------------------------ compute-die programme
    cpo = out / 'compute_programme'; cpo.mkdir(exist_ok=True)
    write_json(cpo / 'sys_face_events.json', sys_face_events(pc, d2d / 'd2d_cal_image.svh', S, ex, txd, a.n59_land_edges))
    land = tables['qwen_compute'].match(src_inst='native59', src_port='dr_o')
    gaps += [
        dict(module='qfd_tt_ctlm_dv (qfd_tt_ctlm_head_static program store + qfd_dv_cmd_cal) via qfd_sys_face config ROM rows 0..1031',
             port='sys_face ROM / dh pw,dw (program copy)', missing='the deployment PW1024 + DW8 program image of a Qwen layer '
             '(ME program rows, XPF, DV slice-command calendar entries + CALD descriptor): no committed compiler emits it; every '
             'bench and layer_roots_from_link.py use tools/qwen_split/sys_face_image.py bench_program() (a deterministic filler)'),
        dict(module='qfd_native59_dv_service', port='parameter LAND_EDGES (+ NATIVE_PROFILE, LAND_QUALIFIED)',
             missing=f'dv2f14bn binds the default LAND_EDGES 8 (NATIVE_PROFILE 0); the dr_o return chain is '
                     f'{[(b["id"], b["stages"], b.get("landing_k")) for b in land]} relay instances to the W5 slice (a landed '
                     'lane n > 1: E = K mod 8) then the W5..E5 chain -- the compiled value needs the die land plan'),
        dict(module='qfd_sys_face', port='L calendar class 2 QSLOT (q_slot / q_slot_beat to native59)',
             missing='no compiler relation between the Q seat-bank commit (dd_i Q landings from the W5 slices) and q_slot; '
                     'the xdie vehicle drives it as a declared stimulus'),
        dict(module='qfd_sys_face', port='E calendar (EMBW / FILL)', missing='embedding row slots not compiled by this pass'),
        dict(module='dv2f14bn landed lanes (57 buses, n > 1)', port='ot_qfd_land K straps',
             missing='land_plan.json (lane age E per landing) is not produced by the dv2f14bn chain; E = K mod 8 only, so '
                     'no compiler can schedule those buses (incl. dvs_W5.dd_wo -> native59.dd_i and native59.dr_o)'),
        dict(module='qfd_native59_dv_service / qkd_native_attention_static_ctl', port='CMD -> Q beat 0 spacing',
             missing='TOKEN-XDIE-QWEN F1: native59 needs >= 1 idle slot after CMD, the KV static ctl needs Q contiguous; '
                     'compiled here with the production gap 0 (KV side) -- one side must change its compiled gap'),
    ]
    # ------------------------------------------------------------------ compiled relay schedules + die_relay_check
    rs = out / 'relay_schedule'; rs.mkdir(exist_ok=True)
    checks = {}
    for design, short in (('qwen_compute', 'compute'), ('qwen_kv', 'kv')):
        sched, used = {}, {}
        for n, b in ba.items():
            if b['design'] != design:
                continue
            for m in b['members']:
                sched[m['bus']] = m['stages'] + (b['age'] - m['age'])
                used.setdefault(m['bus'], []).append(f'{n} (calendar age {b["age"]})')
        cdoc = DRS.compiled(docs[design], CONSUMER, used_by=used, scheduled=sched, loaded_from=Path(a.compute_stages if short == 'compute' else a.kv_stages).name)
        txt = json.dumps(cdoc, separators=(',', ':'))
        p = rs / (f'{short}_compiled.json.gz' if len(txt) > a.gz_over else f'{short}_compiled.json')
        DRS.write(p, cdoc)
        rep = DRC.check(docs[design], DRS.load(p))     # compute: the seam-annotated die table (record_bundles ages)
        write_json(rs / f'relay_check_{short}.json', rep)
        checks[short] = dict(verdict=rep['verdict'], fails=rep['fails'], stage_diffs=rep['stage_diffs'], schedule=p.name)
    ksp = None
    if a.kv_static_model:                        # HKV-DIE2 10-19: stage-derived KV static parameters on THIS kv table
        sys.path.insert(0, str(ROOT / 'tools/qwen_kv_die'))
        import kv_static_params as KSP
        ksp = KSP.run(json.load(open(a.kv_static_model)), docs['qwen_kv'],
                      json.load(open(a.kv_fwd_lanes)) if a.kv_fwd_lanes else None, attn=True,   # HKV-DIE3: + ATTN_CALENDAR
                      die_v=a.kv_die_v, case_die_v=a.kv_case_die_v)       # KVR-DERIVE: bindings / straps / relay clocks
        write_json(out / 'kv_static_params.json', ksp)
        for f in ksp['fails']:
            findings.append(dict(id=f'KV_STATIC_PARAMS {f["id"]}', severity='FAIL', owner='KV die lead (HKV-DIE)',
                                 what=f['what'], **({'fix': f['fix']} if f.get('fix') else {})))
    write_json(out / 'findings.json', dict(findings=findings, gaps=gaps, relay_check=checks, bundles=ba))
    # ------------------------------------------------------------------ manifest
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'manifest.json')
    man = dict(schema='opentallas.qwen_layerbench.compile_manifest.v1', tool=CONSUMER,
               command=['python3', CONSUMER] + list(argv if argv is not None else sys.argv[1:]),
               tool_sha256=sha(__file__), source_commits=dict(compute=a.compute_commit, kv=a.kv_commit),
               inputs={k: dict(path=str(v), sha256=sha(ROOT / v if not Path(v).is_absolute() else v))
                       for k, v in (('compute_stages', a.compute_stages), ('kv_stages', a.kv_stages),
                                    ('token_path', a.token_path), ('link_handoff', a.link_handoff),
                                    ('compute_die_v', a.compute_die_v))
                       + ((('compute_lanes', seam_rec['source'].split(' + ')[1]),) if ' + ' in seam_rec['source'] else ())},
               compute_seam=dict(stages=seam_st, source='record_bundles.seam_stages', rule=seam_rec['rule']),
               die_table_digests={k: d['digest'] for k, d in docs.items()},
               layers=dict(L1=dict(X=X['L1'], period_compiled=next(l['cycles'] for l in pc['program']['layers'] if l['id'] == 'L1')),
                           L0=dict(X=X['L0'], start=pc['program']['layers'][0]['start']),
                           head='no D2D traffic (compute-only; terminal RESULT is in the token run segment 1); ME programme = gap'),
               stages=S, txd=txd, kv_programme=kvp, relay_check={k: v['verdict'] for k, v in checks.items()},
               **({'kv_static_params': dict(status=ksp['status'], table_digest=ksp['table_digest'],
                                            ahub_ages=ksp['params'].get('ahub_ages'), seq_kvn=ksp['params'].get('seq_kvn'),
                                            attn_fault_lane_max=(ksp['params'].get('attn_fault') or {}).get('lane_latency_max'),
                                            # KVR-DERIVE 10-19: the attention-path static ages THIS table needs vs the
                                            # closed tiles' hard ages the die binds (any difference is a FAIL finding)
                                            static_schedule={k: (ksp['params'].get('static_schedule') or {}).get(k)
                                                             for k in ('schedule', 'tile_ages')})}
                  if ksp else {}),
               findings=[f['id'] for f in findings], gaps=len(gaps),
               files={str(p.relative_to(out)): sha(p) for p in files})
    write_json(out / 'manifest.json', man)
    print(json.dumps(dict(stages=S, txd=txd, X=dict(L0=X['L0'], L1=X['L1']), relay_check={k: v['verdict'] for k, v in checks.items()},
                          findings=[f['id'] for f in findings], gaps=len(gaps), files=len(files))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
