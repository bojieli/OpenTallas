"""Independent ownership/striping arithmetic and source-binding checks, CPU only."""
import collections
import hashlib
import json
from pathlib import Path
import generate as g

p = Path(__file__).resolve().parent
x = json.loads((p/'logical_residency.json').read_text())
assert x == g.generate(), 'Reproduction changed'
inventory = json.loads((p/'non_SM_source_inventory.json').read_text())
assert inventory['programme_sha256'] == x['source_pins']['results/rtl/w19_hbm_tp96_program_oreduce.json']
selected = json.loads((p/'selected_headers.json').read_text())
assert selected['index_sha256'] == inventory['checkpoint_index_sha256']
by_name = {t['tensor']:t for t in inventory['items']}
for name,t in selected['selected_tensors'].items():
    actual = by_name[name]
    for key in ('dtype','shape','data_offsets','shard'):
        assert t[key] == actual[key], (name,key)
    assert t['bytes'] == actual['stored_bytes']
# Inventory byte extents are independently checked against dtype, shape and offsets.
sizes = {'BF16':2, 'F32':4, 'F8_E4M3':1, 'F8_E8M0':1, 'I64':8, 'I32':4}
for t in inventory['items']:
    n = sizes[t['dtype']]
    for dim in t['shape']:
        n *= dim
    assert n == t['stored_bytes'] == t['data_offsets'][1]-t['data_offsets'][0], t['tensor']
cases = 0
for block in (1,8):
    for rows in (0,1,7,8,9,95,96,97,767,768,769,1040,2049):
        actual = collections.Counter((i//block)%96 for i in range(rows))
        assert g.counts(rows,block) == [actual[r] for r in range(96)]
        cases += 1
for rows in (524288,1048576):
    block = 8
    # Independent block iterator, no state/model construction or tensor reads.
    actual = [0]*96
    for start in range(0,rows,block*96):
        for r in range(96):
            actual[r] += max(0,min(block,rows-start-r*block))
    assert actual == g.counts(rows,block)
    cases += 1
for rows in (384006168,384016682):
    actual = [len(range(r,rows,96)) for r in range(96)]
    assert actual == g.counts(rows,1)
    cases += 1
for size in (0,1,127,128,129,255,256,257,511,512,513,4096,69939200):
    actual = [0]*4
    for offset in range(0,size,128):
        actual[(offset//128)%4] += 128
    assert actual == g.stripe_bytes(size)
    assert sum(actual) == ((size+127)//128)*128
    cases += 1
assert x['state']['total_rank_rows'] == [27320]*32+[27312]*32+[27288]*32
assert x['state']['reference_ckv_bytes'] == 5368709120
assert x['state']['reference_index_bytes'] == 1342177280
assert x['state']['replicated_window_reference_bytes_all_ranks'] == 1006632960
assert x['constants']['remaining_text_objects_bytes'] == 1807808
assert all(v is None for v in x['physical_non_sm_reservations'].values())
assert x['full_stack_fit'] is None and x['full_resident_address_width'] is None and not x['adoption']
print(f'PASS: reproducible ledger; 542 dtype/shape/offset extents; {cases} independent ownership/stripe cases; programme binding; pending physical gates preserved')
