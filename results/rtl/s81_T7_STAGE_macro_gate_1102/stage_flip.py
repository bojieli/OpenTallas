#!/usr/bin/env python3
"""UNAPPLIED T7 staging macro flip (TOK-DS-4). Accepts only the approved T7 bound hashes and changes exactly the two
u_eng g_stage2 ot_hdc_v41x_attn_staging instances from SRAM_MACRO(1'b0) to SRAM_MACRO(1'b1). Every other byte stays."""
import argparse, hashlib, json, sys
from pathlib import Path
ALLOWED = {
    '61c902f184b49e231c34de041d0f1832a4117749592f81fa3bf42d6ff4df504a': 'original T7 bound',
    'b30a42837e0839214c751a58848bfa095fe3d81d1a4311c1d72c14ef1668edf5': 'LAND-only cut (s81_T7_LAND_bound_cut_1102)',
    '43dc924ceeb0d58da324e485cc62c5690e88ef29555ac73e1c821fe7c9ed2d7d': 'PMEM+PVQ+LAND joint cut (s81_T7_LAND_bound_cut_1102)',
}
OLD = "ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) "
NEW = "ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b1), .TROWS(640)) "
INST = ('u_u_rsv_14_u_u_att_u_eng_g_stage2_u_stage0 (', 'u_u_rsv_14_u_u_att_u_eng_g_stage2_u_stage1 (')

def flip(text):
    h = hashlib.sha256(text.encode()).hexdigest()
    if h not in ALLOWED:
        raise ValueError('unapproved preimage hash ' + h[:8])
    lines = text.split('\n')
    hits = [i for i, l in enumerate(lines) if 'ot_hdc_v41x_attn_staging' in l]
    if len(hits) != 2:
        raise ValueError(f'staging instances {len(hits)} != 2')
    for i, inst in zip(hits, INST):
        if lines[i].strip() != (OLD + inst).strip():
            raise ValueError('unexpected staging line: ' + lines[i].strip()[:160])
        lines[i] = lines[i].replace(OLD, NEW)
    return '\n'.join(lines), h, [i + 1 for i in hits]

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--parent', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        sys.exit('refusing to overwrite ' + str(out))
    new, h, at = flip(Path(a.parent).read_text())
    out.write_text(new)
    print(json.dumps(dict(parent_sha256=h, parent=ALLOWED[h], lines=at, after_sha256=hashlib.sha256(new.encode()).hexdigest()), indent=1))
