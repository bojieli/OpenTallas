"""Explicit proposed released-vocabulary partition for the twelve MTP head dies.

All A/B source rows and local Markov rows must derive from this manifest. This
does not repurpose historical round-robin images without regenerating them.
"""
import json
import math
from pathlib import Path


def manifest(head_dies=12, vocab=129280):
    bundles = math.ceil(vocab/(head_dies*128))
    dies = []
    seen = []
    for die in range(head_dies):
        first, end = vocab*die//head_dies, vocab*(die+1)//head_dies
        blocks = []
        for bundle in range(bundles):
            row0 = first + bundle*128
            rows = []
            for a in range(4):
                base = row0 + a*32
                valid = min(32, max(0, end-base))
                rows.append(dict(A=a, local_A=bundle*4+a, global_row0=base,
                    VALID_ROWS=valid, valid_mask=(1 << valid)-1,
                    source_rows=[base, base+valid],
                    Markov_local_row0=0, Markov_local_row_count=32,
                    padding='invalid; image weights zero; never participates in argmax'))
                seen.extend(range(base, base+valid))
            blocks.append(dict(bundle=bundle, global_row0=row0,
                B_source_rows=[row0, min(end, max(row0, row0+128))],
                B_VALID_ROWS=min(128, max(0, end-row0)), A=rows))
        dies.append(dict(die=die, source_rows=[first,end], valid_rows=end-first,
            bundles=blocks, physical_A=4*bundles, local_Markov_engines=4*bundles,
            local_Markov_ROM4096=8*bundles))
    assert seen == list(range(vocab)), 'row partition must be complete, unique and ascending'
    return dict(schema='opentallas.mtp-head-semantic-rows.v1', adopted=False,
        head_dies=head_dies, released_vocab=vocab, uniform_bundles_per_die=bundles,
        physical_A_per_die=4*bundles, row_identity='global released tensor vocabulary row',
        source='original MTP plan twelve head dies; released vocabulary129280',
        mapping='balanced contiguous vocabulary slices; explicit uniform padded bundle capacity',
        image_requirements=['regenerate A and B images using the same global source rows',
            'regenerate local K256 Markov row images using each A source_rows',
            'head/Markov join and argmax must carry global_row0 and VALID_ROWS',
            'historical round-robin field allocation is not this semantic mapping'],
        qualification='proposed semantic binding; actual regenerated images and connected RTL gate required', dies=dies)


if __name__ == '__main__':
    out = Path(__file__).resolve().parents[1]/'results/arch/mtp_head_semantic_rows_20261009/manifest.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest(), indent=2)+'\n')
