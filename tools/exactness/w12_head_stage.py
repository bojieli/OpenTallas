#!/usr/bin/env python3
"""Usage (source root, QWEN_O4_TP / QWEN_O4_GROUPS / HDC_KV_FMT / HDC_SU_WIDTH set): w12_head_stage.py PREP DIE DIR.
token-exact 2026-10-09: the head stage dir's program / segments for a restored W12 head image: source image program at
the env HDC_SU_WIDTH (FP.profile_lm_head over the prep geometry) + head_rom.json geometry; writes into DIR."""
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import hdc_qwen_fullshape_program_w12 as FP
prep, die, d = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
rec = next(r for r in json.loads((prep / 'prep.json').read_text())['images'] if r['kind'] == 'head' and r['die'] == die)
m = rec['layout'][0]
geo = {"name": "lm_head", "base": 0, "rows": m['rows'], "columns": 4096, "split": m['split'], "k_per_split": m['k_per_split'],
       "rounds": m['rounds'], "scale_base": 0}
prog = FP.profile_lm_head(die, dict(geo), 0)
d.mkdir(parents=True, exist_ok=True)
(d / 'program.hex').write_text('\n'.join(prog['program_hex']) + '\n')
(d / 'segments.hex').write_text('\n'.join(prog['descriptor_hex']) + '\n')
(d / 'head_rom.json').write_text(json.dumps({"geometry": geo, "code_words": m['code_span_words'], "scale_words": m['scale_span_words'],
                                             "restored_by": "token-exact 2026-10-09 from prep.json"}, indent=1) + '\n')
print(d, len(prog['program_hex']))
