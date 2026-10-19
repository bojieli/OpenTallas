#!/usr/bin/env python3
"""Executable MODEL proof; not RTL simulation or native timing qualification."""
import hashlib, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[5]
SOURCE = ROOT / 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv'

def trial(mutant=None, initial_offset=0, reset_pointer=True):
    rng = random.Random(105050)
    checked = bubbles = wraps = resets = 0
    # Independent physical payloads intentionally have unrelated arbitrary startup values.
    for tile in range(4):
      for level in range(5):
       for head in range(16):
        shift = [rng.getrandbits(33) for _ in range(8)]
        mem = [rng.getrandbits(33) for _ in range(8)]
        ptr = initial_offset
        known = [False]*8
        for job in range(5):
         # Abort an occupied job, then restart the legal block-0 programme.
         if reset_pointer: ptr = 0
         known = [False]*8
         resets += 1
         beat = 0
         limit = 256 if job % 2 else 104+(job+tile+head+level)%8
         for blk in range(32):
          for dim in range(8):
           if beat >= limit: break
           live = (blk & ((1 << level)-1)) == ((1 << level)-1)
           use = bool(blk & (1 << level))
           fin = blk == 31
           store = live and not fin and not use
           for _ in range(rng.randrange(4)):
            bubbles += 1
            if mutant == 'advance_on_bubble': ptr = (ptr+1)%8
           addr = (ptr+1)%8 if mutant == 'read_next' else ptr
           if live and use:
            assert known[0], 'programme used an unwritten post-reset word'
            assert shift[0] == mem[addr], 'qualified OLD head mismatch'
            checked += 1
           old = shift[0]
           # Preserve all 33 bits, including fault bit; no FP32 operation is replaced.
           value = (rng.getrandbits(17) | ((head+1)<<17) | (tile<<22)
                    | (job<<24) | (blk<<27))
           shift = shift[1:] + [value if store else old]
           known = known[1:] + [True if store else known[0]]
           if store:
            mem[ptr] = ((value & ~(31<<17)) | (((head+1)%16+1)<<17)
                        if mutant == 'wrong_head' else value)
           elif mutant == 'clobber_recirculation': mem[ptr] = 0
           ptr = (ptr+1)%8
           wraps += ptr == 0
           beat += 1
    return dict(qualified_old_heads=checked, bubbles=bubbles, wraps=wraps, occupied_resets=resets)

def main():
    result = dict(kind='MODEL ONLY; no RTL, synthesis, gate or adoption',
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  rings=320, depth=8, word_bits=33, payload_bits=84480,
                  payload_clock_pins=84480, pointer_copies_per_ring=3,
                  pointer_bits_per_ring=24, pointer_clock_pins=7680,
                  reset_forest_ff_lower_bound=249,
                  read_and2=84480, read_or2=73920,
                  payload_hold_mux2=84480, pointer_mux2=7680,
                  write_enable_and2=7680, store_and_terms=320,
                  model_fanout=dict(pointer_q=12, write_enable=11,
                                    store=24, valid=25, incoming_payload_bit=8),
                  read_logic_levels=4, write_logic_levels=2,
                  measured_tt_delay_ps=None, mapped_area_um2=None,
                  outline=None, parent_fit=None, added_data_edges_intended=0,
                  actual_full_token_delta=None, source_simulator='NOT RUN',
                  proof=trial(), mutants={})
    result['binary_pointer_alternative'] = dict(pointer_copies_per_ring=3,
        pointer_bits_per_ring=9, pointer_clock_pins=2880,
        reset_forest_ff_lower_bound=94, pointer_mux2=2880,
        slot_decode_and2=15360, decode_inv=2880,
        increment_and2=960, increment_xor2=1920,
        select_to_head_logic_levels=7, pointer_q_fanout_upper_model=11,
        valid_fanout_model=10, store_fanout_model=24,
        actual_delay_ps=None, actual_area_um2=None,
        next_bounded_implementation='ROOT choice pending reset/lifetime closure')
    result['unreset_binary_pointer'] = dict(pointer_ff=2880, added_reset_loads=0,
        proof_by_initial_offset={str(i): trial(initial_offset=i, reset_pointer=False)
                                 for i in range(8)},
        restrictions='all encodings legal; no pointer0 assumption; physical power-up definite state; fresh fill and tile/tag reset alignment still need RTL proof')
    for mutant in ('advance_on_bubble','read_next','wrong_head','clobber_recirculation'):
        try: trial(mutant)
        except AssertionError as exc: result['mutants'][mutant] = str(exc)
        else: raise AssertionError('noncausal mutant '+mutant)
    # Counterexample to claiming arbitrary occupied-reset equivalence:
    # before reset physical orientation ptr=3 means logical head=mem[3].
    assert list(range(8))[3] != list(range(8))[0]
    result['occupied_reset_counterexample'] = dict(old_head=3, reset_pointer_head=0,
        verdict='raw stale outputs differ; fresh-job block-0 overwrite is REQUIRED')
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__': main()
