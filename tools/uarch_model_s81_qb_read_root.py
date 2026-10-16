"""Sizing-first QB SRAM read-output root candidate; no physical adoption."""
import hashlib
from pathlib import Path

SOURCE = 'rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv'
SOURCE_SHA256 = '8bbde3ed38fd6d94ae99821c11d73e0f009881e084a35476206990a98c2294d1'


def model(root=None):
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    if hashlib.sha256((root / SOURCE).read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('QB source changed: regenerate the actual clock-root census')
    return dict(schema='opentallas.s81.qb-read-root-candidate.v1', enabled_by_default=False,
      source=dict(path=SOURCE, sha256=SOURCE_SHA256), replicas=4, macs_per_cycle=0,
      storage=dict(macros_per_replica=1, words=128, bits_per_word=256,
                   physical_bytes_per_replica=4096, production_words_per_replica=96),
      memory_ports_per_replica=dict(read_bytes_per_cycle=32, write_bytes_per_cycle=32,
                    simultaneous_read_write='different rows only; original collision assertions retained'),
      boundary_bits_per_replica=dict(inputs=562, outputs=256, clock_pins=2, reset_pins=1),
      clock_partition=dict(core='input capture plus actual SRAM clock; proposed move from Wcentre to real Scentre entry', read='existing256 read-output FFs only', historical_read_ff=256,historical_core_ff=547,historical_macro_clock_sinks=1,
            added_clock_pins_per_replica=1, removed_registers=0, added_registers=0,
            same_ideal_period_ps=833.333333333, ideal_phase_ps=0,
            delivery='real separate N-centre read clock; phi-R per measured physical root',
            cross_root_checks='ordinary related-root setup and hold retained, including SRAM->read FF'),
      calendar=dict(added_cycles=0, unchanged_bank_read_stages=2,
                    token_latency_delta_cycles=0, bandwidth_delta_bytes_per_cycle=0,
                    proof='actual128row256bit1030check lockstep PASS; stoppedreadclock mutant FAILcheck513; fullparent fourbank native QB PASS345800bitchecks/384words and stoppedreadroot FAILcycle623'),
      floorplan=dict(historical_outline_um=[142.56,86.4], candidate_outline_um=None,
            area_delta_um2=None, pg_derating=None, assigned_die_slots=None),
      routing=dict(N_output_bits=256, S_input_bits=512, W_control_bits=50,
            minimum_two_track_M5_length_um=512*0.096,
            actual_tracks_after_power_and_clock=None, all_incident_cuts=None),
      measured_failure=dict(b5_TT_setup_ps=28.79,b5_FF_hold_ps=-14.70,DRC=0,
            output_clock_ps=118.14,reference_input_median_clock_ps=151.0896,
            historical_native_launch_ps=219.4,historical_native_capture_ps=242.9, historical_native_capture_over=512, b5_native_launch_ps=150.9,b5_native_capture_ps=139.4,b5_native_spread_ps=65.2,
            interpretation='partition is a candidate; changing the median alone cannot qualify it'),
      qualification=dict(actual_area=False, actual_pins=False, all_incident_cuts=False,
            die_slot=False, native_launch_220=False, native_capture_190=False,
            per_root_spread_80=False, TT_setup=False, FF_hold=False, DRC0=False,
            physical_admissible=False))
