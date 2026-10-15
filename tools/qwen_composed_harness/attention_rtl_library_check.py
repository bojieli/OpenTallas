#!/usr/bin/env python3
"""Check native attention arithmetic provenance; not a full-token qualifier."""
import json
from pathlib import Path
import re
import subprocess
import sys


def check(directory):
    root = Path(directory)
    library = root / 'libot_qwen_tp8_attention_service.so'
    receipt = json.loads((root / 'receipt.json').read_text())
    if not receipt.get('hierarchical') or 'RTL' not in receipt.get('fp_units', ''):
        raise ValueError('missing actual RTL FP build receipt')
    manifest = (root / 'source.sha256').read_text()
    for unit in ('ot_hdc_fp32_add_lat.sv', 'ot_hdc_fp32_mul_lat.sv',
                 'ot_hdc_fastfp.sv', 'ot_qwen_tp8_attention_service.sv'):
        if not re.search(r'\b' + re.escape(unit) + r'$', manifest, re.M):
            raise ValueError('missing source-pinned actual RTL unit: ' + unit)
    if re.search(r'sim_nhb_fp_lat_dpi|sim_hdc_v41x_fastfp', manifest):
        raise ValueError('behavioral FP source in native attention build')
    symbols = subprocess.check_output(['nm', '-D', str(library)], text=True)
    if re.search(r'\b(?:nhb_fadd|nhb_fmul|ot_v41x_fadd|ot_v41x_fmul)\b', symbols):
        raise ValueError('behavioral FP symbol in native attention library')
    return {'scope': 'ATTENTION_RTL_ARITHMETIC_BUILD_ONLY',
            'library': str(library), 'status': 'PASS',
            'full_native_token_qualified': False,
            'static_production_schedule_qualified': False}


if __name__ == '__main__':
    try:
        print(json.dumps(check(sys.argv[1]), sort_keys=True))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('FAIL native attention library: ' + str(error), file=sys.stderr)
        sys.exit(1)
