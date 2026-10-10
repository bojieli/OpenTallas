#!/usr/bin/env python3
"""hgi-1010 (2026-10-10): vectors for tb_hgi_cp_die_mtp -- the MTP backend translator inside the CP die (MTP=1).

Image: one body per kernel kind (G23) and, for the per-layer kinds 3 (layer, 40 bodies), 7 (dsa, 5) and 8 (dsb, 5),
one body per layer / draft stage at the G26 stride KS (16-byte units).  Every body is a single CTL.END whose token is
VM[TOKB + id] = 1000 + id, id = kind (one-body kinds) or 100 * kind + L' (per-layer kinds), so each completion
names the body the sequencer ran.  The host AR entry is an END with token 999.
  python3 tools/hgi_mtp_cpdie_vectors.py   (writes rtl/hbm_accel/generic/tb/hgi_mtp_cpdie_{image,md,vm0}.mem)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_generic_iface as G  # noqa: E402
from hgi_seq_vectors import header, mdesc, record  # noqa: E402

KS = 4                       # body stride (records are 3 words: header + A)
TOKB = 0x9000
PER = {3: 40, 7: 5, 8: 5}


def end_rec(i):
    return record(header('CTL', 'END'), descs=dict(A=mdesc(space=1, fmt=0, base=TOKB + i, n=1)))


def main():
    words, kent, vm = [0], [0] * 11, {}          # word 0 unused: a kernel entry of 0 means "absent"
    # the host AR entry (an END with token 999), then the kernel bodies
    ar = len(words)
    vm[TOKB + 4000] = 999
    words += record(header('CTL', 'END'), descs=dict(A=mdesc(space=1, fmt=0, base=TOKB + 4000, n=1)))
    for k in range(11):
        while len(words) % KS:
            words.append(0)
        kent[k] = len(words)
        for L in range(PER.get(k, 1)):
            i = 100 * k + L if k in PER else k
            vm[TOKB + i] = 1000 + i
            body = end_rec(i)
            assert len(body) <= KS
            words += body + [0] * (KS - len(body))
    md = dict(magic=G.MAGIC, ver_minor=G.D_VERSION[1], ver_major=G.D_VERSION[0], n_words=G.NWORDS,
              cp_vocab=129280, cp_ctx_max=1 << 20, coll_group_size=96, entry_ar=ar,
              image_base=0x10, image_pages=1, mtp_kstride=KS, **{f'mtp_kernel_{k}': kent[k] for k in range(11)})
    mdw = G.d_pack(md)
    T = ROOT / 'rtl/hbm_accel/generic/tb'
    (T / 'hgi_mtp_cpdie_image.mem').write_text('\n'.join(f'{w:032X}' for w in words) + '\n')
    (T / 'hgi_mtp_cpdie_md.mem').write_text('\n'.join(f'{x:08X}' for x in mdw) + '\n')
    (T / 'hgi_mtp_cpdie_vm0.mem').write_text('\n'.join(f'{a:08X}{v:08X}' for a, v in sorted(vm.items())) + '\n')
    (T / 'hgi_mtp_cpdie_sizes.svh').write_text(f'localparam integer MTPV_NW = {len(words)}, MTPV_NVM = {len(vm)}, '
                                               f'MTPV_KS = {KS}, MTPV_TOKB = {TOKB};\n')
    print('image words', len(words), 'kent', kent, 'vm', len(vm))


if __name__ == '__main__':
    main()
