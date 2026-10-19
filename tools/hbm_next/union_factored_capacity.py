#!/usr/bin/env python3
"""LH-P3UNITS/UNIONVAR 10-19: program-store capacity check for the factored ordered-cardinality union variants.

Reads the committed P=3 whole-token images (MTP N6, MU N4), finds every main-model layer's IDX.UNION boundary and its two
expert loops, and inventories what must be RESIDENT for the factored scheme:
  * per-cardinality expert kernels: for each layer and c = 1..N, one copy of every loop-body record with its row count
    set to c (the only field that changes with c; checked by re-encoding);
  * the dispatcher metadata (both loop start-offset arrays + c, one SRAM word per union expert) and its D1/D2 tables;
  * the U-independent suffix (one per layer instead of 31 U variants).
against the installed/proposed stores, and prices boot installation and any per-layer load.  Native unit programme
lowering (HGI-1R record -> unit calendar words) does not exist yet, so per-c kernels are held as HGI-1R descriptors in a
dedicated dispatcher kernel store (SRAM macros); this is stated, not hidden.  Pure decode/arithmetic (light, local).

  union_factored_capacity.py --out results/arch/hbm_next_1019/cmtp/unionvar/factored/capacity.json
"""
import argparse, copy, hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_next import image_check as IC, isa_rows as IR

ROOT = Path(__file__).resolve().parents[2]
WH = ROOT / 'results/arch/hbm_next_1019/cmtp/p3/emitter/whole'
MACRO = dict(name='ot_sram_1r1w_1024x256_m2_r2c2', words=1024, bits=256, area_mm2=0.01231420968,
             tt_cq_ps=544.81, ff_cq_ps=450.74, ss_cq_ps_sensitivity=691.77)
CFG_BITS_PER_EDGE = 256          # one masked 256-b macro write per configuration edge (programme-target cfg bus width)
F_HZ = 1.2e9


def layers(image, meta):
    rows = IC.decode_all(image)
    groups = {}
    for row in rows:
        groups.setdefault(str(IC.seg_of(meta['token']['segments'], row[0])), []).append(row)
    out = []
    for lay, rr in groups.items():
        ui = [i for i, x in enumerate(rr) if x[1].unit == 'IDX' and x[1].op == 'UNION']
        if not ui:
            continue
        i = ui[0]; route = rr[i][1]
        N, k = route.desc['A'].m, route.desc['A'].n
        bodies, cur = [], None
        for off, r, rx, raw in rr[i + 1:]:
            if r.unit == 'CTL' and r.op == 'LOOP':
                cur = []
            elif r.unit == 'CTL' and r.op == 'ENDLOOP':
                bodies.append(cur); cur = None
            elif cur is not None:
                cur.append((r, rx, raw))
        assert len(bodies) == 2, (lay, len(bodies))
        suffix_bytes = sum(len(x[3]) for x in rr[i + 1:])
        out.append(dict(layer=lay, N=N, k=k, bodies=bodies, suffix_bytes=suffix_bytes))
    return out


def kernel_bytes(body, c):
    """Encode one c-variant of a loop body: x rows (A.m) = c; every other field unchanged."""
    total = 0
    for r, rx, raw in body:
        v = copy.deepcopy(r)
        if 'A' in v.desc and v.unit == 'SM':
            v.desc['A'] = dataclass_replace(v.desc['A'], m=c)
        b = IR.encode(v, rx)
        assert len(b) == len(raw), 'c changes only a field, never the record length'
        total += len(b)
    return total


def dataclass_replace(x, **kw):
    import dataclasses
    return dataclasses.replace(x, **kw)


def mode_inventory(tag, img, meta):
    L = layers(img, meta)
    N = L[0]['N']
    shapes = set()
    kern = 0
    recs = 0
    for l in L:
        for b in l['bodies']:
            shapes.add(tuple((r.unit, r.op, tuple(sorted((k, (v.m, v.n)) for k, v in r.desc.items()))) for r, _, _ in b))
            for c in range(1, N + 1):
                kern += kernel_bytes(b, c); recs += len(b)
    return dict(mode=tag, image_sha256=hashlib.sha256(img).hexdigest(), union_layers=len(L), N=N, topk=L[0]['k'],
                loop_body_records=[len(b) for b in L[0]['bodies']], distinct_body_shapes=len(shapes),
                kernel_records_all_layers=recs, kernel_bytes_all_layers=kern,
                kernel_bytes_one_layer=kern // len(L), suffix_bytes_per_layer_max=max(l['suffix_bytes'] for l in L),
                suffix_bytes_all_layers=sum(l['suffix_bytes'] for l in L), U_max=N * L[0]['k'])


def macros(bits):
    return math.ceil(bits / (MACRO['words'] * MACRO['bits']))


def main(a):
    modes = []
    for tag, sub, name in (('mtp_N6', 'mtp_N6', 'mtp_N6_token.hgi1r'), ('mu_N4', 'mu_N4', 'mu_N4_token.hgi1r')):
        img = (WH / sub / name).read_bytes(); meta = json.loads((WH / sub / 'emitter.json').read_text())
        modes.append(mode_inventory(tag, img, meta))
    m6 = modes[0]
    # ---- dispatcher-side stores (ot_hnx_union_prefix): exact
    meta_word_bits = 5 + 32 + 32                      # {c, P2, P1} per union expert
    meta_bits_layer = m6['U_max'] * meta_word_bits
    dtab_bits = 2 * 16 * 24 + 2 * 32 + 3 * 12          # D1/D2[c] 24 b, B1, G, KB1/KB2/KBT (flops, < 2 kb)
    # per-layer D tables: identical for every union layer iff the body shapes are identical (checked)
    kernel_bits = max(m['kernel_bytes_all_layers'] for m in modes) * 8
    kernel_bits_both = sum(m['kernel_bytes_all_layers'] for m in modes) * 8
    kstore_macros = macros(kernel_bits_both)
    boot_edges_kernels = math.ceil(kernel_bits_both / CFG_BITS_PER_EDGE)
    u_only_bank = 10158080
    res = dict(
        schema='hnx.unionvar.factored.capacity.v1',
        status='capacity verdict for the factored scheme; native unit-programme lowering absent (stated)',
        macro=MACRO, modes=modes,
        dispatcher=dict(
            metadata=dict(word_bits=meta_word_bits, words_per_layer=m6['U_max'], bits_per_layer=meta_bits_layer,
                          store='1 x %s (U<=128 words used of 1024; overwritten each layer, read only after union done)'
                                % MACRO['name'],
                          macros=1, area_mm2=MACRO['area_mm2'], safe_design='> 2 kb -> SRAM macro (item 5)',
                          port_schedule='write port: IDX tap phase only (<= 1 write/edge); read port: dispatch phase only '
                                        '(1 read per launch, READ->CAP->FORM->WAIT, >= 4 edges apart)'),
            duration_tables=dict(bits=dtab_bits, store='flops (< 2 kb), cfg idle-only, statically indexed by c via '
                                 'registered one-hot select', per_layer_reload='none if all union layers share body '
                                 'shapes (distinct_body_shapes == 2 per mode); else a 40-entry table in the kernel store'),
        ),
        kernel_store=dict(
            content='per (layer, c = 1..N, loop-body record) HGI-1R descriptor, both modes resident (MTP N6 + MU N4)',
            bits_mtp=modes[0]['kernel_bytes_all_layers'] * 8, bits_mu=modes[1]['kernel_bytes_all_layers'] * 8,
            bits_both=kernel_bits_both, macros=kstore_macros, area_mm2=kstore_macros * MACRO['area_mm2'],
            utilisation=kernel_bits_both / (kstore_macros * MACRO['words'] * MACRO['bits']),
            alternative_one_mode_macros=macros(kernel_bits),
            boot_install_edges=boot_edges_kernels, boot_install_us=boot_edges_kernels / F_HZ * 1e6,
            per_layer_load_edges=0, per_token_load_edges=0,
            note='all 40 layers x N kernels resident from boot: no pre-layer load, no runtime code generation; '
                 'the dispatcher sends (kref = KB[loop] + c - 1, slot) and the unit fetches the descriptor locally'),
        suffix=dict(u_only_bank_bytes=u_only_bank, factored_bytes_mtp=modes[0]['suffix_bytes_all_layers'],
                    factored_bytes_mu=modes[1]['suffix_bytes_all_layers'],
                    note='factored: one U-independent suffix per layer (loop trip counts come from the dispatcher), '
                         'held where the baseline whole-token image is held (no new capacity vs the baseline image)'),
        installed_native_stores=[
            dict(store='VM programme calendar (ot_vms_calendar_static via hfd_hgi_vm_calendar_static)', count=4,
                 words=1024, bits=256, payload_bits='146..187',
                 verdict='NOT USED for per-c kernels: no HGI-1R -> calendar lowering exists, so its per-c word count '
                         'is not derivable; claiming fit would be unproven'),
            dict(store='static programme targets (ot_static_program_target PCW=10)', rows=1024,
                 verdict='per-c kernel descriptors could be armed as base/limit/loops ranges (desc-only rearm reuses a '
                         'resident image); same lowering gap'),
            dict(store='legacy HGI-1 credit CP ring', bytes=65536, verdict='excluded (credit/ready; not static)'),
        ],
        verdict='',
    )
    ok = kstore_macros <= 8 and m6['U_max'] <= 128 and dtab_bits < 2048
    res['verdict'] = ('FITS (proposed dedicated stores): metadata 1 macro, kernels %d macros (%.1f%% used, %.4f mm2), '
                      'tables %d flop bits; boot install %d edges (%.2f us, once); per-layer load 0. Installed generic-die '
                      'unit programme stores NOT proven to hold per-c kernels (lowering absent).'
                      % (kstore_macros, 100 * res['kernel_store']['utilisation'], res['kernel_store']['area_mm2'],
                         dtab_bits, boot_edges_kernels, res['kernel_store']['boot_install_us'])) if ok else 'DOES NOT FIT'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(res['verdict'])
    for m in modes:
        print(m['mode'], 'layers', m['union_layers'], 'N', m['N'], 'body records', m['loop_body_records'],
              'shapes', m['distinct_body_shapes'], 'kernel bytes', m['kernel_bytes_all_layers'],
              'suffix bytes', m['suffix_bytes_all_layers'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    main(ap.parse_args())
