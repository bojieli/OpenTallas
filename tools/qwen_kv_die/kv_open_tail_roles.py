#!/usr/bin/env python3
"""KV-FUNC-OPENS 10-19: exact OUTPUT_OPEN role contract for chain tails and duplicate faces of the static KV die.

Only the (master, port) types in ROLES are ever declared spare, per INSTANCE (full port), and only when every source
assertion, every generator assertion and every die-position check below holds on the exact bound die.  Everything else
(faults, aborts, admission/readiness certificates, STATUS/recovery observations: kc.kf, dcal.*, d2d recovery_cycles,
all qkd_host_root_admission outputs) stays OUTPUT_OPEN for the retirement/admission owner (lane KV-RETIRE).
KV-BIND4 10-19: rx_zero17 of the sfm d2d master (z17_dup) is a DUP face; recovery_cycles stays OPEN (STATUS owner).

Role kinds:
  TAIL   the last element of a linear generator chain: its forward output is a pure registered/wire copy of its chain
         input (source assertion) and the generator gives that position no successor (generator assertion); the die
         shows exactly the generator's chain end open per stack and every other element's port connected and read.
  DUP    a die export whose value is consumed INSIDE the tile, or carried and consumed on another die path (source
         assertions name the consumer); the export face itself is a legacy/duplicate face with no die peer.
All sources are pinned by SHA-256 (die-relative to the GEN7 source root); the bound die is pinned by SHA-256 in the
contract.  Any change refuses.  No fault, clock, reset or status output is in ROLES.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TILES = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv'
SFM = 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv'
ACTL = 'rtl/qwen_sys/split_20261014/qkd_native_attention_static_ctl.sv'
SOURCES = {
    TILES: 'df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97',
    'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv': '90f9a4ec6dbb0ee2e1d644ac0878566c709ba5a1ec68601a4d250a50fa4f98fe',
    'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv': 'f1840155fd8b51c18f5a478106eb3df3e9ea985bcd29c7d729769546d208139a',
    'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv': 'ed7fdbf48dd623a4f91736932aec6c2c5372a1b8cc57706a7b22e17f832a8503',
    'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv': '14d5d335fc805eb6a39850b05d827001dbca31091c3e9e5758b4ee5db7e0d7b8',
    'rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv': 'b2b1d1e72368059e32aedc071824779dcc68425284b53122fde623dae604511c',
    'rtl/qwen_sys/split_20261014/qkd_host_pc_slice.sv': '5a1cc9d9cab3dead2768d934999f938de75d3e96281328c5a1e4dc36fff2e1fa',
    'rtl/qwen_sys/host_20261013/qkd_host_ingest_station.sv': '28931dd981edaf460f2be7d928e3bea62ca8ea2cff8fa3ee72f78c36e96b460c',
    'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv': '1214151aa45994195dc498fa0d1e3932b75f0004f4a6aa3e1a7a7248e4f61a80',
    'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv': '713858300e2a534ca739afa5579d673f3acc0832cb97386d98a63f4adc53ae2a',
    'rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv': 'c18ebfbb33c9075efc3f621f5809f6f29c9cddb039dc934922867a32cd587a42',
    # KV-BIND4 10-19: the d2ds successor master qkd_d2d_static_sfm (CLOSED r7w_sfm2 view) + the attention RX codec that
    # recomputes the Z17 reserved-zero predicates from rx_payload (z17_dup)
    SFM: 'e17a16804b4125e5c171dc92e78366edb3d73a933195b3c0a4b619477ffb50d3',
    ACTL: 'f60cafbb806ceff8b24b84a1c4bc10f97343ac60afcfcfed17236e6690e5cc9e',
}
# the generator is a tool of the GEN7 tree (not of the binder's tools dir): pinned separately, checked by this prover only
# KV-BIND3 10-19: re-pinned (was a7063e6b..., 60ff34e3d).  Changes since: default-off OT_KV_GRP_PRIVATE0 / OT_KV_DCAL_FLT
# branches, port `scalar` clock/reset classing (only set by GRP_PRIVATE0), ASTK rc1 face-land rst_release 3 -> 5 (startup
# calendar only).  No PC / GRP chain-end text changed; GEN_ASSERT below still asserts the generator text.
GENERATOR = ('tools/qwen_kv_die/kv_static_die.py', '52192834fa4a3e4ebcf1b08ecfea5a0c26e23d3ec683282d0524434c26dd8cff')

PC = ('qkd_kvs_pc', 'qkd_kvs_pc_h')
GRP = ('qkd_kvs_grp', 'qkd_kvs_grp_h')
# (rel, module, [substrings that must occur in the module body])
ASSERT = {
    'pc_dup': [(TILES, m, ['assign pc__er = w_pc__er;', 'assign pc__completion_v = w_pc__completion_v;',
                           'assign pc__completion_we = w_pc__completion_we;', 'qkd_static_kv_pc_path_fan_nc_b',
                           '.er(w_pc__er)', '.completion_v(w_pc__completion_v)', '.completion_we(w_pc__completion_we)',
                           'w_pc__er[260:260]']) for m in PC] + [
        ('rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv', 'qkd_static_kv_pc_path_emb_nc_b',
         ['qkd_static_kv_pc_es_merge_b u_esm', '.completion_we(completion_we), .hcv(hcompletion_v), .hcw(hcompletion_we)',
          '.es(es_merged), .er(er)']),
        ('rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv', 'qkd_static_kv_pc_es_merge_b',
         ["wire [260:0] er_e = (own && MUT != 4) ? 261'd0 : er;", 'her[258:1] <= er[258:1];',
          'hcv <= sl && completion_v; hcw <= sl && completion_we;'])],
    'pc_ko_tail': [(TILES, m, ['assign pc__ko = w_pc__ko;', '.ko(w_pc__ko)', '.ki(pc__ki)']) for m in PC] + [
        ('rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv', 'qkd_ctrl_pc_sched_nc', ['.o_v(ko[0]), .o_d(ko[32:1])']),
        ('rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv', 'ot_qkvd_kcmd_tap', ['o_v <= i_v;', 'o_d <= i_d;'])],
    'tok_dup': [(TILES, m, ['assign y__tok = x__tok;', 'assign y__tep = x__tep;']) for m in GRP] + [
        (TILES, 'qkd_kvs_emb', ['assign px_tok = d2d__svc[109:92];', 'assign px_tep = d2d__svc[89:74];',
                                '.fill_token(d2d__svc[109:92])', '.fill_epoch(d2d__svc[89:74])'])],
    'odn_tail': [(TILES, 'qkd_kvs_grp_h', ['assign o_dn = {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};'])],
    'kg_dup': [(TILES, 'qkd_kvs_ctl', ['assign kg = {w_lprg__layer, w_lprg__epoch, w_lprg__kgo};'] +
                [f'assign o_hroot_{s} = ' for s in ('WS', 'WN', 'ES', 'EN')])],
    'hsl_tail': [('rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv', 'qkd_host_pc_slice_die',
                  ['bgo<=PINCAP?bgi_q:bgi;', '.fi(fi),.fo(fo)']),
                 ('rtl/qwen_sys/split_20261014/qkd_host_pc_slice.sv', 'qkd_host_pc_slice', ['.fi(fi),.fo(fo)']),
                 ('rtl/qwen_sys/host_20261013/qkd_host_ingest_station.sv', 'qkd_host_ingest_station',
                  ['assign fo={fod,fov};', 'fdq<=fi[290:1];fod<=fq[290:1];', 'fvq<=fi[0];fov<=fq[0];'])],
    'd2d_dup': [('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'ot_qwen_d2d_kvn_rx',
                 ['word_slot <= rx_slot; word_index <= rx_beat[1:0];',
                  "if (rx_event != rx_slot || (rx_event && bad)) fault <= 1'b1;"]),
                ('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'qkd_d2d_static_core',
                 ['assign att_rx_v = rxe[0]; assign att_rx_slot = rxs[0];', 'assign fault = endf | s_f | kvn_f;']),
                ('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv', 'ot_qwen_d2d_static_end',
                 ['rx_slot[i] <= r1v && r1p == i;', 'rx_event[k] = lrx_v && r2p == k;']),
                ('rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv', 'qkd_seq_core_static_s',
                 ['if (kvv != xk) f_arr <= 1;', "if (ktg[10:8] != 3'b010 || ktg[2:0] != ktag(kn_arr)) f_tag <= 1;",
                  'if (qv != q_exp) f_q <= 1;'])],
    # KV-BIND4: the same three d2d DUP faces on the sfm master (its own core / end; kvn_rx and seq consumer shared)
    'd2d_dup_sfm': [('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'ot_qwen_d2d_kvn_rx',
                     ['word_slot <= rx_slot; word_index <= rx_beat[1:0];',
                      "if (rx_event != rx_slot || (rx_event && bad)) fault <= 1'b1;"]),
                    (SFM, 'qkd_d2d_static_core_sfm',
                     ['assign att_rx_v = rxe[0]; assign att_rx_slot = rxs[0];', 'assign fault = endf | s_f | kvn_f;',
                      'ot_qwen_d2d_kvn_rx u_kvn']),
                    (SFM, 'ot_qwen_d2d_static_end_sfm',
                     ['rx_slot[i] <= r1v && r1p == i;', 'rx_event[k] = lrx_v && r2p == k;']),
                    (SFM, 'qkd_d2d_static_sfm', ['assign att_rx_slot = PR ? q_att_rx_slot : c_att_rx_slot;']),
                    ('rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv', 'qkd_seq_core_static_s',
                     ['if (kvv != xk) f_arr <= 1;', "if (ktg[10:8] != 3'b010 || ktg[2:0] != ktag(kn_arr)) f_tag <= 1;",
                      'if (qv != q_exp) f_q <= 1;'])],
    # rx_zero17 = registered OR17 of rx_payload on the SAME edge as the rx_payload pin register; the die's attention
    # tile reads rx_payload and its landed codec (record_ld) evaluates the same reserved-zero tests on it
    'z17_dup': [(SFM, 'qkd_d2d_static_sfm',
                 ['always @(posedge ck) q_rx_payload <= c_rx_payload;',
                  'assign c_rx_zero17[1] = |c_rx_payload[31:5];',
                  'assign c_rx_zero17[zz + 1] = |c_rx_payload[32*zz +: 32];',
                  'always @(posedge ck) q_rx_zero17 <= c_rx_zero17;', 'assign rx_zero17 = PR ? q_rx_zero17 : c_rx_zero17;']),
                (ACTL, 'qkd_native_attention_record_ld',
                 ['l_pl<=rx_payload;', 'data[511:19]==0', 'data[511:5]==0', 'legal(rk,rl,rb,l_pl[511:0])']),
                (ACTL, 'qkd_native_attention_static_ctl', ['qkd_native_attention_record_ld', '.rx_payload(rx_payload)']),
                ('rtl/qwen_sys/split_20261014/qkd_native_attention_programme.sv', 'qkd_native_attention_programme',
                 ['.rx_payload(rx_payload)']),
                (TILES, 'qkd_kvs_attn', ['qkd_native_attention_programme #(.MUT(0), .LAND(1)) u_attn'])],
}
GEN_ASSERT = {
    'pc_dup': ["            if BOOT:      # note s5.6", "                continue\n            bus(f'hes_{st}_{k}'",
               "bus(f'ler_{st}_{k}', 'kv_oneway', 261, [(pc, 'pc__er'), (s, 'ctrl_er')])"],
    'pc_ko_tail': ["rec['notes'].append(f'kc_{st}: last PC ko unconsumed (the strip parent left it open too)')",
                   "order = list(range(NPC)) if rev else list(range(NPC - 1, -1, -1))"],
    'odn_tail': ["peer=ch[j + 1] if j + 1 < len(ch) else None,"],
    'kg_dup': ["kg['consumers'] = [c for c in kg['consumers'] if c[0] not in ects]", "union.append(('KG',))"],
    'tok_dup': ["(('d2d', 'engine_result_token', 0, 18), ('tok', ('kvs_emb', 'px_tok'), 18, 0, 18, None)),"],
    'hsl_tail': [], 'd2d_dup': [], 'd2d_dup_sfm': [], 'z17_dup': [],
}
# (master, port) -> (role, kind)
ROLES = {
    **{(m, p): ('pc_dup', 'DUP') for m in PC for p in ('pc__er', 'pc__completion_v', 'pc__completion_we')},
    **{(m, 'pc__ko'): ('pc_ko_tail', 'TAIL') for m in PC},
    **{(m, p): ('tok_dup', 'DUP') for m in GRP for p in ('y__tok', 'y__tep')},
    ('qkd_kvs_grp_h', 'o_dn'): ('odn_tail', 'TAIL'),
    ('qkd_kvs_ctl', 'kg'): ('kg_dup', 'DUP'),
    ('qkd_host_pc_slice_die', 'bgo'): ('hsl_tail', 'TAIL'),
    ('qkd_host_pc_slice_die', 'fo'): ('hsl_tail', 'TAIL'),
    **{('qkd_d2d_static', p): ('d2d_dup', 'DUP') for p in ('att_rx_slot', 'kvn_word_slot', 'kvn_word_index')},
    **{('qkd_d2d_static_sfm', p): ('d2d_dup_sfm', 'DUP') for p in ('att_rx_slot', 'kvn_word_slot', 'kvn_word_index')},
    ('qkd_d2d_static_sfm', 'rx_zero17'): ('z17_dup', 'DUP'),
}
WHY = {
    'pc_dup': 'BOOT die: er/completion are consumed in-tile by qkd_static_kv_pc_es_merge_b (embedding endpoint er_e, '
              'boot-window her/hcv/hcw to the HOST slice) and er[260] rides o_grp; the generator skips the legacy '
              'ler/hcv/hcw die buses under BOOT, so the pc__er/pc__completion_* export faces have no die peer',
    'pc_ko_tail': 'kc command chain tail: ko = ot_qkvd_kcmd_tap registered copy of ki; generator chain order ends at '
                  'this PC (S stacks pc31, N stacks pc0)',
    'tok_dup': 'grp y__tok/y__tep are wire copies of x__tok/x__tep, the relayed qkd_kvs_emb px_tok/px_tep = '
               'd2d__svc[109:92]/[89:74], which qkd_kvs_emb consumes itself (u_rowtx fill_token/fill_epoch); '
               'no PC port takes the group pass on this die',
    'odn_tail': 'down control chain tail: o_dn is a wire rotation of i_ctl; the generator gives the chain-end group '
                '(grp_h) no o_dn peer',
    'kg_dup': 'ctl kg={layer,epoch,kgo} is also packed in o_hroot_* (KG union) and delivered to every ECTL via the '
              'hroot o_kg export; the generator removed the ECTL consumers from the ctl kg port',
    'hsl_tail': 'HOST slice boot chain (bgo = registered bgi) and ingest broadcast chain (fo = 2-edge registered fi) '
                'tails: every slot taps its own copy before forwarding; the last slot per stack has no successor',
    'd2d_dup': 'att_rx_slot / kvn_word_slot are the compiled-slot expectation (rx_slot) already checked against '
               'arrival in the end/slot link and kvn_rx (fault -> d2d fault); kvn_word_index = registered rx_beat[1:0], '
               'the consumer checks arrival edge (kvv != xk) and tag ordinal (ktag) itself',
    'd2d_dup_sfm': 'qkd_d2d_static_sfm (r7w_sfm2): as d2d_dup -- att_rx_slot / kvn_word_slot = compiled-slot expectation '
                   'checked in the sfm end + kvn_rx (fault -> d2d fault); kvn_word_index = registered rx_beat[1:0]',
    'z17_dup': 'rx_zero17[16:0] = registered OR17 of rx_payload (Z0 [31:19], Z1 [31:5], Z2..16 the 15 upper data words) '
               'on the rx_payload pin-register edge; the die attention tile reads rx_payload itself and its landed codec '
               'qkd_native_attention_record_ld evaluates the same reserved-zero tests (data[511:19]==0 / data[511:5]==0); '
               'the face is consumed only by the private Z17 receiver (codex/receiver-z17-private-1019, not hardened)',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def module_body(text, name):
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b.*?\bendmodule\b', text, re.S)
    if not m:
        raise ValueError(f'source module missing: {name}')
    return m.group(0)


def check_sources(root, pins=None):
    pins = dict(SOURCES, **(pins or {}))
    out = {}
    for rel, want in pins.items():
        if rel == GENERATOR[0]:
            continue
        got = sha(Path(root) / rel)
        if got != want:
            raise ValueError('open-tail role source changed; re-prove: ' + rel)
        out[rel] = got
    gwant = pins.get(GENERATOR[0], GENERATOR[1])
    gtext = (Path(root) / GENERATOR[0]).read_text()
    if sha(Path(root) / GENERATOR[0]) != gwant:
        raise ValueError('generator changed; re-prove chain ends: ' + GENERATOR[0])
    for role, items in ASSERT.items():
        for rel, mod, subs in items:
            body = module_body((Path(root) / rel).read_text(), mod)
            for s in subs:
                if s not in body:
                    raise ValueError(f'{role}: {rel}:{mod} lacks {s!r}')
        for s in GEN_ASSERT[role]:
            if s not in gtext:
                raise ValueError(f'{role}: generator lacks {s!r}')
    # tok/tep: no other use of x__tok/x__tep in the group tiles
    tiles = (Path(root) / TILES).read_text()
    for m in GRP:
        body = module_body(tiles, m)
        for x in ('x__tok', 'x__tep'):
            if len(re.findall(r'\b' + x + r'\b', body)) != 2:
                raise ValueError(f'{m}.{x} has another use; the y face is not a pure duplicate')
    return out, gwant


RELAY = re.compile(r'qkd_(?:rlys|rlysh0?|landsh0?)_\d+')


def derive(die_v, root=ROOT, existing=None, pins=None):
    srcs, gsha = check_sources(root, pins)
    tiles = P.parse_modules((Path(root) / TILES).read_text(), TILES)
    width_mods = {m.name: m for m in tiles}
    for rel in SOURCES:
        if rel.endswith('.sv'):
            for m in P.parse_modules((Path(root) / rel).read_text(), rel):
                width_mods.setdefault(m.name, m)
    nets, tin, tout, insts = P.parse_die(str(die_v))
    uses, drv = defaultdict(int), {}
    by_master = defaultdict(list)
    for m, inst, params, cm in insts:
        by_master[m].append((inst, params, cm))
        for pn, ex in cm.items():
            for b in (P.expr_bits(ex, nets) if ex else []) or []:
                if b[0] not in ('CONST', 'Z', 'UNDECL'):
                    uses[tuple(b)] += 1
        if RELAY.fullmatch(m):
            aa, bb = P.expr_bits(cm.get('a', ''), nets), P.expr_bits(cm.get('b', ''), nets)
            if aa and bb and len(aa) == len(bb):
                for a, b in zip(aa, bb):
                    drv[tuple(b)] = tuple(a)
    src_port = {}
    for m, inst, params, cm in insts:
        for pn, ex in cm.items():
            for k, b in enumerate((P.expr_bits(ex, nets) if ex else []) or []):
                src_port.setdefault(tuple(b), []).append((m, inst, pn, k))

    def is_open(cm, pn):
        return not cm.get(pn)

    def connected_read(cm, pn):
        bits = P.expr_bits(cm.get(pn, ''), nets) if cm.get(pn) else None
        return bool(bits) and all(b[0] in ('CONST',) or uses[tuple(b)] >= 2 for b in bits)

    def tail_name_ok(inst, prefix):
        mt = re.fullmatch(prefix + r'_(WS|WN|ES|EN)_(\d+)', inst)
        return bool(mt) and int(mt.group(2)) == (31 if mt.group(1)[1] == 'S' else 0)

    def traces_to(net_bits, master, port):
        """every bit follows same-index relay payload edges back to master.port"""
        for b in net_bits:
            b, seen = tuple(b), 0
            while b in drv and seen < 400:
                b, seen = drv[b], seen + 1
            if not any(x[0] == master and x[2] == port for x in src_port.get(b, [])):
                return False
        return True

    doc = json.loads(json.dumps(existing or dict(pads={}, instances={})))
    entries = doc.setdefault('instances', {})
    declared, refused = defaultdict(list), defaultdict(list)
    for (m, pn), (role, kind) in sorted(ROLES.items()):
        rows = by_master.get(m, [])
        opens = [(i, p_, c) for i, p_, c in rows if is_open(c, pn)]
        others = [(i, p_, c) for i, p_, c in rows if not is_open(c, pn)]
        ok, why = True, ''
        if kind == 'TAIL':
            if role == 'odn_tail':
                ok = all(connected_read(c, 'o_dn') for _, _, c in by_master.get('qkd_kvs_grp', []))
                why = 'a non-end group o_dn is open/unread'
            else:
                prefix = 'kvpc' if role == 'pc_ko_tail' else 'hsl'
                # the chain may mix master variants (pc / pc_h): count chain ends over every master of this role+port
                allopen = [i for (m2, p2), (r2, _) in ROLES.items() if r2 == role and p2 == pn
                           for i, _, c in by_master.get(m2, []) if is_open(c, pn)]
                stacks = sorted(re.fullmatch(prefix + r'_(WS|WN|ES|EN)_\d+', i).group(1) for i in allopen
                                if re.fullmatch(prefix + r'_(WS|WN|ES|EN)_\d+', i))
                ok = stacks == ['EN', 'ES', 'WN', 'WS'] and len(allopen) == 4 and \
                    all(tail_name_ok(i, prefix) for i, _, _ in opens) and \
                    all(connected_read(c, pn) for _, _, c in others)
                why = 'open set is not exactly the generator chain end per stack, or a non-end link is unread'
        elif role == 'tok_dup':
            port_x = pn.replace('y__', 'x__')
            src = 'px_tok' if pn == 'y__tok' else 'px_tep'
            ok = bool(rows) and all(c.get(port_x) and traces_to(P.expr_bits(c[port_x], nets), 'qkd_kvs_emb', src)
                                    for _, _, c in rows)
            why = 'x input does not trace through relays to qkd_kvs_emb.' + src
        elif role == 'z17_dup':
            # the duplicated source word itself must leave the d2d end and be read on the die
            ok = bool(rows) and all(connected_read(c, 'rx_payload') for _, _, c in rows)
            why = 'd2d rx_payload is open / unread on the die: rx_zero17 is not a duplicate of a consumed word'
        if not ok:
            refused[f'{m}.{pn}'] = why
            continue
        for inst, params, cm in opens:
            mod = width_mods.get(m)
            w = mod.width(pn, mod.env(params)) if mod else None
            if not w:
                refused[f'{m}.{pn}'] = 'width unknown'
                break
            ent = entries.setdefault(inst, dict(master=m, reason='', ports={}))
            if ent.get('master') != m:
                raise ValueError(f'{inst}: existing pad entry names another master')
            ent['ports'][pn] = [[0, w - 1]]
            ent['reason'] = ((ent['reason'] + '; ') if ent['reason'] else '') + f'KV-FUNC-OPENS {kind} {pn}: ' + WHY[role]
            declared[f'{m}.{pn}'].append(inst)
    doc['open_tail_contract'] = dict(
        die_sha256=sha(die_v), source_sha256=srcs, generator=dict(path=GENERATOR[0], sha256=gsha),
        ports={k: dict(instances=v, role=ROLES[tuple(k.split('.'))][0], kind=ROLES[tuple(k.split('.'))][1],
                       why=WHY[ROLES[tuple(k.split('.'))][0]]) for k, v in sorted(declared.items())},
        refused=dict(refused), types=len(declared), pins=sum(len(v) for v in declared.values()))
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--existing', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = derive(a.die_v, a.root, json.loads(a.existing.read_text()) if a.existing else None)
    a.out.write_text(json.dumps(d, indent=1) + '\n')
    c = d['open_tail_contract']
    print(json.dumps(dict(types=c['types'], pins=c['pins'], refused=c['refused'])))


if __name__ == '__main__':
    main()
