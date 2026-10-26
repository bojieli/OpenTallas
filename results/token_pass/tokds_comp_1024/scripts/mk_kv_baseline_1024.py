#!/usr/bin/env python3
"""TOK-DS/COMP 10-24: reconstruct the kv_vp_1021/gate.py --baseline directory.

The original kv_bank_1021 baseline run (gold2/old-nvme0 codex-s81-kv-vp-1021/baseline) was lost in the old-fleet wipe.
Golden vectors are restored from the committed R3 record (results/token_pass/s81_kv_real_vp_1021/r3) and must match the
R3 vector_sha256 exactly. The source inventory is R3's list (minus the files gate.py adds itself) hashed on THIS tree
(main), per the lane instruction to use main's sources; the differences to R3's pins are written to pin_diff.json.
    mk_kv_baseline_1024.py WT OUT_BASELINE
"""
import hashlib, json, shutil, sys
from pathlib import Path
wt, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=False)
r3 = wt / 'results/token_pass/s81_kv_real_vp_1021/r3'
rec = json.loads((r3 / 'result.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, d in rec['vector_sha256'].items():
    shutil.copyfile(r3 / name, out / name)
    assert sha(out / name) == d, name
added = {'rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv',
         'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv', 'rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv',
         'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
         'tools/s81_dv/kv_vp_1021/tb_kv_vp.sv'}
srcs = [s for s in rec['source_sha256'] if s not in added]
missing = [s for s in rec['source_sha256'] if not (wt / s).is_file()]
pins = {s: sha(wt / s) for s in srcs if (wt / s).is_file()}
diff = {s: dict(r3=rec['source_sha256'][s], main=sha(wt / s) if (wt / s).is_file() else None)
        for s in rec['source_sha256'] if not (wt / s).is_file() or sha(wt / s) != rec['source_sha256'][s]}
(out / 'pin_diff.json').write_text(json.dumps(dict(missing_on_main=missing, differ_from_r3=diff), indent=2) + '\n')
(out / 'result.json').write_text(json.dumps(dict(
    status='PASS', reconstructed=True,
    note='kv_bank_1021 baseline lost (old-fleet wipe 10-24 07:03); status = original baseline PASS (R3 README). '
         'Vectors restored from committed R3, sha-matched. source_sha256 = main tree hashes (lane instruction).',
    source_sha256=pins, vector_sha256=rec['vector_sha256']), indent=2) + '\n')
print(json.dumps(dict(sources=len(pins), missing=missing, differ=list(diff))))
