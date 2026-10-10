#!/usr/bin/env python3
"""Apply only the opt-in DYN repair to an immutable original campaign copy."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / 'src/rtl/hdc/v41x/ot_hdc_core_v41x.sv'
original = path.read_text()
anchor = '    parameter integer NSLOT = 1,           // position slots (1: the one-position core)\n'
assert original.count(anchor) == 1
updated = original.replace(anchor, anchor +
    '    parameter integer ROLLBACK_RING_DYN = 0, // one-position wavefront: eight compressor records\n')
anchor = '''        if (NSLOT > 1) begin
            //: MTP: the compressor slot ring of 8, the pooled pair's base, the Markov row
            dyn[db + 25] <= {b_pos[2:0], 2'b00};
            dyn[db + 26] <= {b_pos[2:1], 7'd0};
            dyn[db + 27] <= b_tok * 32;
        end'''
replacement = '''        if (NSLOT > 1 || ROLLBACK_RING_DYN != 0) begin
            // Ring storage is independent of the number of token slots. A
            // one-position wavefront still needs the current record and pair.
            dyn[db + 25] <= {b_pos[2:0], 2'b00};
            dyn[db + 26] <= {b_pos[2:1], 7'd0};
        end
        if (NSLOT > 1) begin
            dyn[db + 27] <= b_tok * 32;
        end'''
assert updated.count(anchor) == 1
updated = updated.replace(anchor, replacement)
path.write_text(updated)
(root / 'successor_source.json').write_text(json.dumps({
    'original_source_commit': 'cefb5aa18', 'repair_commit': 'aff63db74',
    'qualification': 'original reduced campaign14 successor; not native full-target qualification',
    'core_original_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'core_successor_sha256': hashlib.sha256(updated.encode()).hexdigest(),
    'engine_changes': 'ROLLBACK_RING_DYN default-off parameter and DYN25/26 conditional only',
    'golden_change': None,
}, indent=2) + '\n')
