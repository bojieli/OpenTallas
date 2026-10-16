#!/usr/bin/env python3
"""S81 MTP binding: every released mtp.* tensor on an owning ROM die of the S81 array (stream mtp-dsbind-1010).

The S81 canonical binding (results/uarch/dsrom_s81_released_binding_20261004/canonical) leaves 2,401 mtp.* tensors
(7,932,874,632 B) unowned (auxiliary_obligations.json; auxiliary_owner_hooks.json asks for an auxiliary_map with
tensor / byte span / die / macro / row owners).  This tool writes that successor map; the canonical files stay
byte-identical.

Die set added to the S81 array (die count is not scarce: add dies, do not squeeze):
  P.k0..k3   4 DSpark PRIMARY dies (TP4 group; generator: layer1 recipe + --draft P, 1,792 pairs, 5 draft SerDes).
             Holds the non-expert matrices of mtp.0..2 (attention, router gate, shared expert), the hc mixes and
             vectors of the three blocks, and the mtp.0 seed projection (main_proj / main_norm).
             PAIR RULE: every matrix keeps the S81 allocator's L0 superrow runs (same superrow -> run grouping,
             same words a superrow, same rank row slices); each run goes to its own pair within its co-issued phase
             group (no two runs of one phase group share a pair), so the words any pair reads in one field phase are
             <= the L0 placement's: the measured L0 field phases of the draft blocks stay an upper bound.
             (The earlier P2 home -- 282 dense pairs on head dies h0..h3 -- puts ~8x the words a phase on each pair
             and has no room for the seed (669 > 631 pairs); results/arch/mtp_die_reprice_20261009.)
  D{A,B}.r0..4.k0..3   40 MD-2 draft dies (layer1 recipe + --draft A|B): routed experts, the selected whole-superrow
             rowpack results/uarch/dsrom_mtp_p2_20261009/rowpack.json.gz (image gate PASS, tools/dsrom_mtp_draft_images.py);
             5 row packages share each side/rank image.
  H.h0..h11  the 12 head dies (head631 recipe): markov_head.embed replicated (dense pairs after the globals share),
             markov_head.head vocab-split (die h: rows h*10,774.., engine e of 340: 32 rows in its 2 local ROM macros),
             confidence_head / final draft norm in the head CROM.

    python3 tools/dsrom_s81_mtp_binding.py --out results/uarch/dsrom_s81_mtp_binding_20261010
"""
from __future__ import annotations

import argparse
import collections
import functools
import gzip
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_1m_draft_blocks as D  # noqa: E402

CANON = ROOT / 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
ROWPACK = ROOT / 'results/uarch/dsrom_mtp_p2_20261009/rowpack.json.gz'
DEPTH = 8192                     # addresses a pair (two 4096-row macros deep x 2 banks)
PAIRS_LAYER1 = 1792              # m221pq / s81 layer1 full recipe
ADDR_BYTES_FP8 = 64              # one address = 2 banks x 32 data bytes (+ inline E8M0 carrier bits)
STAGES, TP, ROWS = 3, 4, 5
HEAD_DIES, HEAD_PAIRS, HEAD_GLOBAL_PAIRS = 12, 631, 211
MARKOV_ENGINES, MARKOV_ROWS_ENGINE = 340, 32
# co-issued phase groups of one DSpark block (the field reads every member of a group in one phase)
PHASE_GROUPS = (('wq_a', 'wkv'), ('wq_b.rows0', 'wq_b.rows4608'),
                ('wo_a.group0.rows0', 'wo_a.group0.rows768', 'wo_a.group1.rows0', 'wo_a.group1.rows768'),
                ('wo_b.rows0', 'wo_b.rows4608'), ('gate',), ('shared.w1', 'shared.w3'), ('shared.w2',))
ALIAS = {'attn.wq_a.weight': ['wq_a'], 'attn.wkv.weight': ['wkv'], 'attn.wq_b.weight': ['wq_b.rows0', 'wq_b.rows4608'],
         'attn.wo_a.weight': ['wo_a.group0.rows0', 'wo_a.group0.rows768', 'wo_a.group1.rows0', 'wo_a.group1.rows768'],
         'attn.wo_b.weight': ['wo_b.rows0', 'wo_b.rows4608'], 'ffn.gate.weight': ['gate'],
         'ffn.shared_experts.w1.weight': ['shared.w1'], 'ffn.shared_experts.w3.weight': ['shared.w3'],
         'ffn.shared_experts.w2.weight': ['shared.w2']}
HE = ('hc_attn_fn', 'hc_ffn_fn')
CROM = ('hc_attn_scale', 'hc_attn_base', 'hc_ffn_scale', 'hc_ffn_base', 'attn_norm.weight', 'ffn_norm.weight',
        'attn.q_norm.weight', 'attn.kv_norm.weight', 'attn.attn_sink', 'ffn.gate.bias', 'ffn.gate.bias_vl')
DTYPE_BYTES = {'F8_E4M3': 1, 'F8_E8M0': 1, 'I8': 1, 'BF16': 2, 'F32': 4}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nbytes(h):
    return math.prod(h['shape']) * DTYPE_BYTES[h['dtype']]


class Die:
    def __init__(self, die_id, kind, recipe, pairs, rank=None):
        self.id, self.kind, self.recipe, self.pairs, self.rank = die_id, kind, recipe, pairs, rank
        self.iv = collections.defaultdict(list)          # pair -> [(a0, a1, owner)]
        self.load = [0] * pairs
        self.rep = rank == 0 and (kind == 'head' or '.r0.' in die_id or kind == 'primary')

    def put(self, pair, a0, n, owner):
        assert 0 <= pair < self.pairs and 0 <= a0 and a0 + n <= DEPTH, (self.id, pair, a0, n)
        self.iv[pair].append((a0, a0 + n, owner))
        self.load[pair] = max(self.load[pair], a0 + n)

    def check(self):
        bad = 0
        for p, ivs in self.iv.items():
            ivs = sorted(ivs)
            bad += sum(1 for x, y in zip(ivs, ivs[1:]) if y[0] < x[1])
        return dict(die=self.id, pairs=self.pairs, used_pairs=len(self.iv), used_addresses=sum(b - a for v in self.iv.values() for a, b, _ in v),
                    max_pair_fill=max(self.load) if self.iv else 0, overlaps=bad)


@functools.lru_cache(None)
def l0_entries():
    out = {}
    with gzip.open(CANON / 'matrix_map.jsonl.gz', 'rt') as f:
        for ln in f:
            r = json.loads(ln)
            if r['layer'] != 0:
                break
            if r['expert'] is None:
                out[r['alias']] = r
    return out


def runs_of(ent):
    """L0 superrow runs as (superrow list, words a superrow); one run = one pair's contiguous block in L0."""
    for seg, pair, s0, cnt, stride, base, w in ent['plans']:
        yield dict(seg=seg, l0_pair=pair, superrows=[s0 + k * stride for k in range(cnt)], words=w, n=cnt * w)


def place_primary(dies, hdr, owners):
    """non-expert matrices of the three blocks + the seed projection on the 4 primary rank dies (rank-invariant)."""
    l0 = l0_entries()
    cur = [0] * PAIRS_LAYER1                      # stacking cursor a pair (identical on the 4 rank dies)
    stats = {}
    groups = []
    for st in range(STAGES):
        ents = {}
        for sub, als in ALIAS.items():
            for al in als:
                ents[al] = (f'mtp.{st}.{sub}', D._mtp_entry(l0[al], st) if al == 'gate' else l0[al])
        for g in PHASE_GROUPS:
            groups.append((st, g, [ents[a] for a in g]))
    # seed: main_proj rank slice (1,280 rows x K 15,360 FP8) as 640 superruns of 480 words, one phase group
    sp = hdr['mtp.0.main_proj.weight']['shape']
    rpr = sp[0] // TP
    seed_ent = dict(alias='main_proj', K=sp[1], format='fp8', rows=rpr,
                    rank_slices=[dict(rows=[r * rpr, (r + 1) * rpr], cols=[0, sp[1]]) for r in range(TP)],
                    plans=[[0, None, s, 1, 1, None, 2 * sp[1] // ADDR_BYTES_FP8] for s in range(rpr // 2)])
    groups.append((0, ('main_proj',), [('mtp.0.main_proj.weight', seed_ent)]))
    for st, g, members in groups:
        used = set()
        order = sorted(range(PAIRS_LAYER1), key=lambda p: (cur[p], p))      # least-stacked pairs first
        it = iter(order)
        gmax = 0
        l0pp = collections.Counter()
        for tensor, ent in members:
            for run in runs_of(ent):
                p = next(it)
                assert p not in used
                used.add(p)
                a0 = cur[p]
                dies[0].put(p, a0, run['n'], tensor)       # rank-invariant layout: one representative checked
                owners[tensor].append(dict(dies=[d.id for d in dies], rank_slice='per die rank k = rank_slices[k]',
                                           alias=ent['alias'], pair=p, addr=a0, addresses=run['n'],
                                           superrows=[run['superrows'][0], len(run['superrows']), (run['superrows'][1] - run['superrows'][0]) if len(run['superrows']) > 1 else 1],
                                           words_per_superrow=run['words'], l0_pair=run['l0_pair']))
                cur[p] = a0 + run['n']
                gmax = max(gmax, run['n'])
                if run['l0_pair'] is not None:
                    l0pp[run['l0_pair']] += run['n']
        l0m = max(l0pp.values()) if l0pp else None
        stats[f'mtp.{st}:' + '+'.join(g)] = dict(runs=len(used), max_addresses_a_pair_in_phase=gmax,
                                                  l0_max_addresses_a_pair_in_phase=l0m, pairs_distinct=True,
                                                  not_above_l0=(l0m is None or gmax <= l0m))
    # E8M0 block scales ride with their weight's words (the S81 element word carries 264 useful bits: 256 data + the
    # 8-bit UE8M0 exponent; wo_a is FP8+UE8M0 -> BF16_RNE at image build, as the L0 entry's conversion says)
    for tensor in list(owners):
        sc = tensor[:-len('weight')] + 'scale'
        if tensor.endswith('.weight') and sc in hdr and sc not in owners:
            owners[sc] = [dict(o, inline_with=tensor) for o in owners[tensor]]
    return stats, max(cur)


def place_vectors(dies, hdr, owners, providers):
    """hc mixes (HE banks, 8 pairs a block as L0) and CROM vectors, replicated on every primary rank die."""
    pv = {(p['kind'], p['layer']): p for p in json.loads((CANON / 'providers.json').read_text())}
    he0, cr0 = pv[('HE', 0)], pv[('CROM', 0)]
    for st in range(STAGES):
        dec = [dict(alias=a, tensor=f'mtp.{st}.{a}', bytes=nbytes(hdr[f'mtp.{st}.{a}']), rows=hdr[f'mtp.{st}.{a}']['shape'][0],
                    K=hdr[f'mtp.{st}.{a}']['shape'][1]) for a in HE]
        providers.append(dict(kind='HE', stage=f'mtp.{st}', dies=[d.id for d in dies], banks=he0['banks'],
                              words_per_bank=he0['words_per_bank'], useful_word_bits=he0['useful_word_bits'],
                              physical_leaf_depth=he0['physical_leaf_depth'], leaves=he0['banks'] * math.ceil(he0['words_per_bank'] / he0['physical_leaf_depth']),
                              declarations=dec, replicated_per_rank=True, template='S81 L0 HE provider (providers.json kind HE layer 0)'))
        assert sum(x['bytes'] for x in dec) == he0['banks'] * he0['words_per_bank'] * he0['useful_word_bits'] // 8
        cdec = []
        for a in CROM:
            t = f'mtp.{st}.{a}'
            cdec.append(dict(alias=a, tensor=t, dtype=hdr[t]['dtype'], elements=math.prod(hdr[t]['shape']), bytes=nbytes(hdr[t])))
        words = sum(math.ceil(x['bytes'] * 8 / cr0['useful_word_bits']) for x in cdec)
        providers.append(dict(kind='CROM', stage=f'mtp.{st}', dies=[d.id for d in dies], banks=1, words_per_bank=words,
                              useful_word_bits=cr0['useful_word_bits'], physical_leaf_depth=cr0['physical_leaf_depth'],
                              leaves=math.ceil(words / cr0['physical_leaf_depth']), declarations=cdec, replicated_per_rank=True,
                              template='S81 L0 CROM provider (full tensors replicated on each rank die; L0 holds rank slices)'))
        for x in dec + cdec:
            owners[x['tensor']].append(dict(dies=[d.id for d in dies], provider=f'{providers[-1 if x in cdec else -2]["kind"]}:mtp.{st}',
                                            bytes=x['bytes'], replicated_per_rank=True))
    t = 'mtp.0.main_norm.weight'
    providers.append(dict(kind='CROM', stage='seed', dies=[d.id for d in dies], banks=1,
                          words_per_bank=math.ceil(nbytes(hdr[t]) * 8 / 256), useful_word_bits=256, physical_leaf_depth=4096, leaves=1,
                          declarations=[dict(alias='main_norm', tensor=t, dtype=hdr[t]['dtype'], bytes=nbytes(hdr[t]))],
                          replicated_per_rank=True))
    owners[t].append(dict(dies=[d.id for d in dies], provider='CROM:seed', bytes=nbytes(hdr[t]), replicated_per_rank=True))


def place_experts(drafts, hdr, owners):
    rp = json.loads(gzip.open(ROWPACK).read())
    per = collections.defaultdict(list)
    for ph in rp['phases']:
        for s in ph['segments']:
            per[s['tensor']].append((ph['side'], s))
    cover = {}
    for tensor, ss in per.items():
        side = {x for x, _ in ss}
        assert len(side) == 1
        side = side.pop()
        dl = [d for d in drafts if d.kind == f'draft{side}']
        srs = sorted(s['superrow'] for _, s in ss)
        rows_rank = ss[0][1]['rank_slices'][0]['rows'][1] - ss[0][1]['rank_slices'][0]['rows'][0]
        assert srs == list(range(rows_rank // 2)), tensor                       # every paired row once a rank
        h, sc = hdr[tensor], hdr[tensor[:-6] + 'scale']
        assert ss[0][1]['rank_slices'][-1]['rows'][1] == h['shape'][0]
        rep = next(d for d in drafts if d.kind == f'draft{side}' and d.rep)   # images are rank/row-invariant in layout
        for _, s in ss:
            rep.put(s['pair'], s['base'], s['words'], tensor)
        w = sum(s['words'] for _, s in ss)
        # one address = 2 banks x (2 x (16 FP4 code bytes + 1 E8M0)) = 68 B; codes per rank = rows_rank x K/2 B
        code_b = rows_rank * h['shape'][1]
        K = 2 * h['shape'][1]
        assert w == rows_rank // 2 * math.ceil(K / 512) * 8 and w * 64 >= code_b, (tensor, w, code_b)   # K pads to 512
        own = dict(dies=[d.id for d in dl], rank_slice='die k = rank_slices[k]', side=side, row_replicas=ROWS,
                   segments=len(ss), addresses_a_die=w, layout='rowpack whole-superrow (scale bytes inline, E8M0)',
                   pairs=sorted({s['pair'] for _, s in ss}))
        owners[tensor].append(own)
        owners[tensor[:-6] + 'scale'].append(dict(own, inline_with=tensor))
        cover[tensor] = w
    return cover


def place_head(heads, hdr, owners, providers):
    emb = 'mtp.2.markov_head.embed.weight'
    hw = 'mtp.2.markov_head.head.weight'
    eb = nbytes(hdr[emb])
    e_pairs = math.ceil(eb / (DEPTH * ADDR_BYTES_FP8))
    e_addr = math.ceil(eb / ADDR_BYTES_FP8)
    p = HEAD_GLOBAL_PAIRS
    pp, left = p, e_addr
    while left:
        n = min(left, DEPTH)
        heads[0].put(pp, 0, n, emb)             # same layout on every head die
        pp += 1
        left -= n
    owners[emb].append(dict(dies=[d.id for d in heads], replicated_per_die=True, pairs=[p, p + e_pairs],
                            addresses=e_addr, layout='dense row-major BF16, 512 B a row (8 addresses), local lookup'))
    V = hdr[hw]['shape'][0]
    per_die = math.ceil(V / HEAD_DIES)
    rows_assigned = 0
    for h, d in enumerate(heads):
        r0, r1 = h * per_die, min(V, (h + 1) * per_die)
        eng = math.ceil((r1 - r0) / MARKOV_ROWS_ENGINE)
        assert eng <= MARKOV_ENGINES, (h, eng)
        owners[hw].append(dict(dies=[d.id], rows=[r0, r1], engines=eng, rows_an_engine=MARKOV_ROWS_ENGINE,
                               macros_an_engine=2, words_a_macro=256,
                               layout='engine e: rows r0 + 32e .. +32, alternating banks (ot_dsrom_markov_row local ROM)'))
        rows_assigned += r1 - r0
    assert rows_assigned == V
    for t in ('mtp.2.confidence_head.proj.weight', 'mtp.2.norm.weight'):
        owners[t].append(dict(dies=[d.id for d in heads], provider='CROM:head', bytes=nbytes(hdr[t]), replicated_per_die=True))
    providers.append(dict(kind='CROM', stage='head', dies=[d.id for d in heads], banks=1,
                          words_per_bank=sum(math.ceil(nbytes(hdr[t]) * 8 / 256) for t in ('mtp.2.confidence_head.proj.weight', 'mtp.2.norm.weight')),
                          useful_word_bits=256, physical_leaf_depth=4096, leaves=1, replicated_per_die=True,
                          declarations=[dict(tensor=t, bytes=nbytes(hdr[t])) for t in ('mtp.2.confidence_head.proj.weight', 'mtp.2.norm.weight')]))
    return dict(embed_pairs=e_pairs, markov_pairs_end=p + e_pairs, head_rows_a_die=per_die)


def build(out: Path):
    hdr = D._ckpt_headers(D.SNAP_DEFAULT)
    aux = json.loads((CANON / 'auxiliary_obligations.json').read_text())
    unowned = {t['tensor']: t for t in aux['tensors'] if t['tensor'].startswith('mtp.')}
    assert set(unowned) == set(hdr), 'released mtp.* headers != the canonical unowned list'
    for t, h in hdr.items():
        assert nbytes(h) == unowned[t]['source_storage_bytes'], t
    prim = [Die(f'P.k{k}', 'primary', 'layer1 full + --draft P', PAIRS_LAYER1, k) for k in range(TP)]
    drafts = [Die(f'D{s}.r{r}.k{k}', f'draft{s}', f'draft{s}', PAIRS_LAYER1, k) for s in 'AB' for r in range(ROWS) for k in range(TP)]
    heads = [Die(f'H.h{h}', 'head', 'head631', HEAD_PAIRS, h % TP) for h in range(HEAD_DIES)]
    owners = collections.defaultdict(list)
    providers = []
    pstats, pfill = place_primary(prim, hdr, owners)
    place_vectors(prim, hdr, owners, providers)
    ecover = place_experts(drafts, hdr, owners)
    hstats = place_head(heads, hdr, owners, providers)
    # ---- checks
    missing = sorted(set(hdr) - set(owners))
    extra = sorted(set(owners) - set(hdr))
    area_bad = []
    for sub, als in ALIAS.items():
        for st in range(STAGES):
            t = f'mtp.{st}.{sub}'
            # rank slices of every alias partition the released rows x cols exactly once (L0 rule, gate retargeted)
            l0 = l0_entries()
            area = 0
            for al in als:
                e = D._mtp_entry(l0[al], st) if al == 'gate' else l0[al]
                area += sum((s['rows'][1] - s['rows'][0]) * (s['cols'][1] - s['cols'][0]) for s in e['rank_slices'])
            if area != math.prod(hdr[t]['shape']):
                area_bad.append(t)
    die_checks = [d.check() for d in prim + drafts + heads if d.rep and d.iv]
    for c in die_checks:
        c['applies_to'] = ('all 4 primary rank dies' if c['die'].startswith('P.') else
                           'all 20 %s dies (5 rows x 4 ranks: rank-invariant layout)' % c['die'][:2] if c['die'].startswith('D') else 'all 12 head dies')
    overl = sum(c['overlaps'] for c in die_checks)
    cap_bad = [c for c in die_checks if c['max_pair_fill'] > DEPTH]
    head_markov_end = hstats['markov_pairs_end']
    verdict = dict(
        schema='opentallas.dsrom.S81.mtp-binding.v1',
        released_mtp_tensors=len(hdr), bound_tensors=len(set(owners) & set(hdr)), missing=missing, extra=extra,
        released_mtp_bytes=sum(nbytes(h) for h in hdr.values()),
        matrix_rank_slice_area_exact=not area_bad, area_failures=area_bad,
        expert_tensors_rowpack=len(ecover), address_overlaps=overl, capacity_failures=len(cap_bad),
        head_pairs_used=head_markov_end, head_pairs_recipe=HEAD_PAIRS,
        primary_max_pair_fill=pfill, primary_phase_groups=pstats,
        primary_phase_reads_not_above_l0=all(x['not_above_l0'] for x in pstats.values()),
        PASS=not missing and not extra and not area_bad and overl == 0 and not cap_bad and len(ecover) == 1152
             and head_markov_end <= HEAD_PAIRS and pfill <= DEPTH)
    bytes_by_home = collections.Counter()
    for t, os_ in owners.items():
        k = 'draft' if any(o.get('side') for o in os_) else 'head' if any(d.startswith('H.') for o in os_ for d in o['dies']) else 'primary'
        bytes_by_home[k] += nbytes(hdr[t])
    dieset = dict(
        schema='opentallas.dsrom.S81.mtp-die-set.v1',
        base='S81 canonical binding (unchanged): ' + str(CANON.relative_to(ROOT)),
        added=dict(primary=dict(count=TP, ids=[d.id for d in prim], recipe='tools/s81/s81_dies_recipe.py draftP (layer1 full + --draft P --mtp-links 5)',
                                role='DSpark primary TP4 group: mtp.0..2 attention / router / shared expert / hc / vectors + mtp.0 seed projection'),
                   draft=dict(count=2 * ROWS * TP, ids=[d.id for d in drafts], recipe='tools/s81/s81_dies_recipe.py draftA / draftB',
                              role='MD-2 P2 routed experts (5 row packages x 4 ranks x A/B; A sums the row experts in id order)')),
        head=dict(count=HEAD_DIES, ids=[d.id for d in heads], recipe='tools/s81/s81_dies_recipe.py head631 (--mtp-seq --mtp-links 5)',
                  mtp_content='Markov embed (replicated) + Markov head vocab share + confidence/norm CROM; pairs %d..%d of %d '
                              '(%d..%d spare: the former P2 primary reservation, now on P.k*)' % (HEAD_GLOBAL_PAIRS, head_markov_end, HEAD_PAIRS, head_markov_end, HEAD_PAIRS)),
        dies_added_vs_canonical=TP + 2 * ROWS * TP, bytes_by_home=dict(bytes_by_home),
        topology=dict(
            seed='accept on head h0 (dsfd_mtp_seq) -> board hop h0 -> P.k* (main_proj on the primary; main-hidden captures ride the stage link to the head group, then this hop)',
            blocks='P.k* run mtp.0 -> mtp.1 -> mtp.2 back to back (block st+1 on the dies holding block st output: no stage hop)',
            experts='P.k -> board SerDes -> DA.r.k (row r) -> UCIe -> DB.r.k; expert outputs return to DA, summed in id order, -> P.k',
            ucie_crossings_a_row={'mtp.0': 0, 'mtp.1': 2, 'mtp.2': 2},
            draft_head='P.k* -> board hop -> head group (lm_head sweep + Markov x 5 on H.h*)',
            board_hops_added_vs_P2_head_home=2))
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / 'auxiliary_map.jsonl.gz', 'wt') as f:
        for t in sorted(hdr):
            f.write(json.dumps(dict(tensor=t, shape=hdr[t]['shape'], dtype=hdr[t]['dtype'], bytes=nbytes(hdr[t]),
                                    shard=hdr[t]['file'], owners=owners[t]), separators=(',', ':')) + '\n')
    (out / 'providers.json').write_text(json.dumps(providers, indent=1) + '\n')
    (out / 'die_set.json').write_text(json.dumps(dieset, indent=1) + '\n')
    (out / 'die_checks.json').write_text(json.dumps(die_checks, indent=0) + '\n')
    src = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    verdict['inputs'] = {str(p.relative_to(ROOT)): sha(p) for p in (CANON / 'auxiliary_obligations.json', CANON / 'matrix_map.jsonl.gz',
                                                                  CANON / 'providers.json', ROWPACK, Path(__file__))}
    verdict['checkpoint_index_sha256'] = sha(D.SNAP_DEFAULT / 'model.safetensors.index.json')
    verdict['source_commit'] = src
    verdict['qualification'] = dict(storage_binding=verdict['PASS'], field_schedule_qualified=False, physical_qualified=False,
                                    note='storage owners are bound; primary pair rule preserves L0 per-phase pair reads; '
                                         'draft-die field schedule = rowpack (generated image bench pair 0 PASS); routes/STA of the added dies open')
    (out / 'verdict.json').write_text(json.dumps(verdict, indent=1) + '\n')
    return verdict


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    v = build(a.out)
    print(json.dumps({k: v[k] for k in v if k not in ('primary_phase_groups', 'inputs')}, indent=1))
    return 0 if v['PASS'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
