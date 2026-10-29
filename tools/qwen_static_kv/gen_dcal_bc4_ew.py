#!/usr/bin/env python3
"""KV-EMBWIN16 10-20: the bc4 KV link calendar tile (qkd_d2d_cal_seq_bc4.sv, gen_dcal_bc4.py) on a grown-embed-window pair
image d2d_cal_image_mu_ew<N>.svh (d2d_link_calendar --emb-window N).  The generated file differs from qkd_d2d_cal_seq_bc4.sv
ONLY in its `include line (the START table, token period and compile-time images); structure, ports, reset landing and
edges are byte-identical.  Refuses an image whose TXDP / seam stages / segment bases differ from the bc4 image (the seam
contract TXDP_K 22 and the boot STALE check stay valid).

    gen_dcal_bc4_ew.py 595
    gen_dcal_bc4_ew.py all      # regenerate EVERY committed qkd_d2d_cal_seq_bc4_<sfx>.sv fork from the current bc4

TOK-KV-DCAL-1 10-29: the forks are never hand-edited.  A bc4 change (gen_dcal_bc4.py from qkd_d2d_cal_seq_bootcfg.sv) is
followed by `gen_dcal_bc4_ew.py all`.  The tag may also carry the RoPE suffix (1627_r16_rope ->
d2d_cal_image_mu_ew1627_r16_rope.svh; that fork was previously copied by hand).  A NEW fork must pass the seam / segment
contract below.  `all` only refreshes forks that are already committed: a committed fork whose image differs from the bc4
image in the contract (today ew1627_r16_rope: K_TX / C_RX SEG2 9 -> 10, its STALE check reads its own include) is
refreshed include-only and its delta is printed, so a bc4 fix never stays out of a fork.
"""
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'rtl/qwen_sys/d2d_static_20261015'
# KV-PROG17 10-20: the tag may carry the r16 suffix (595_r16 -> d2d_cal_image_mu_ew595_r16.svh, the ATTN_R16 pair image:
# K RESULT +1 / STATUS +213 a layer, so only the K TX / C RX images, START and the token period differ)
# ('r16' alone = the priced window with the r16 shift: d2d_cal_image_mu_r16.svh -> qkd_d2d_cal_seq_bc4_r16.sv)
TAG_RE = r'(\d+(_r16(_rope)?)?|r16)'
NOT_FORKS = ('qkd_d2d_cal_seq_bc4_rom64.sv',)      # not an include fork: dcal_rom/build_rtl.py output
KEEP = ('D2D_TXDP_C', 'D2D_TXDP_K', 'D2D_CAL_C_TX_SEG1', 'D2D_CAL_C_TX_SEG2', 'D2D_CAL_C_RX_SEG1', 'D2D_CAL_C_RX_SEG2',
        'D2D_CAL_K_TX_SEG1', 'D2D_CAL_K_TX_SEG2', 'D2D_CAL_K_RX_SEG1', 'D2D_CAL_K_RX_SEG2', 'D2D_ADM_OFS', 'D2D_ADM_LEN',
        'D2D_FIRST_TOKEN')
INC = '`include "d2d_cal_image_mu.svh"'


def line(t, n):
    return re.search(rf'^localparam[^\n]*\b{n} = [^\n]*$', t, re.M).group(0)


def sfx_of(tag):
    return tag if tag == 'r16' else f'ew{tag}'


def tag_of_fork(path):
    """qkd_d2d_cal_seq_bc4_<sfx>.sv -> its generator tag (ew595_r16 -> 595_r16, r16 -> r16), None if not a tag."""
    sfx = path.name[len('qkd_d2d_cal_seq_bc4_'):-len('.sv')]
    tag = sfx if sfx == 'r16' else sfx[2:] if sfx.startswith('ew') else None
    return tag if tag is not None and re.fullmatch(TAG_RE, tag) else None


def generate(N, refresh=False):
    if not re.fullmatch(TAG_RE, N):
        raise SystemExit(f'gen_dcal_bc4_ew.py: tag {N!r}: <window>[_r16[_rope]], r16 or all expected')
    SFX = sfx_of(N)
    base, img = D / 'd2d_cal_image_mu.svh', D / f'd2d_cal_image_mu_{SFX}.svh'
    bt, it = base.read_text(), img.read_text()
    diff = [n for n in KEEP if line(bt, n) != line(it, n)]
    if diff and refresh:
        print(f'CONTRACT-DELTA {img.name}: {diff} differ from the bc4 image (committed fork, refreshed include-only)')
    elif diff:
        raise SystemExit(f'{img.name}: {diff} differ from the bc4 image (seam / segment / admission contract)')
    src = (D / 'qkd_d2d_cal_seq_bc4.sv').read_text()
    assert src.count(INC) == 1, 'bc4 source must include the MU image exactly once'
    out = D / f'qkd_d2d_cal_seq_bc4_{SFX}.sv'
    out.write_text(f'// KV-EMBWIN16: qkd_d2d_cal_seq_bc4.sv on {img.name} (tools/qwen_static_kv/gen_dcal_bc4_ew.py {N}); only the include differs.\n'
                   + src.replace(INC, f'`include "{img.name}"'))
    print(f'{out.relative_to(D.parents[2])}: include {img.name}')


def all_tags():
    forks = [f for f in sorted(D.glob('qkd_d2d_cal_seq_bc4_*.sv')) if f.name not in NOT_FORKS]
    bad = [f.name for f in forks if tag_of_fork(f) is None]
    if bad:
        raise SystemExit(f'gen_dcal_bc4_ew.py all: forks without a generator tag: {bad}')
    return [tag_of_fork(f) for f in forks]


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for t in (all_tags() if sys.argv[1] == 'all' else [sys.argv[1]]):
        generate(t, refresh=sys.argv[1] == 'all')
