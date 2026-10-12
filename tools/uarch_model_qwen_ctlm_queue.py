"""Full-shape Qwen registered control-tile area/relay alternatives."""
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def model():
    rom = ROOT/'results/arch/qwen_kv_die_20261009/rom_r22k.json'
    evidence = json.loads(rom.read_text())
    die_w, die_h = evidence['die_um']
    base_w, base_h = 777.6, 1814.4
    upper_h = 4 * (388.8 + 2.16)
    variants = []
    for name, w in [('wide1036',1036.8),('wide1296',1296.0)]:
        h=2073.6
        extra=w-base_w
        interior=math.ceil(extra/430.56)
        # Conservative execution ceiling: four64-word descriptor programs
        # per layer plus embed/head, one forward and reverse boundary wait
        # per word. This bounds serial communication cost without claiming
        # all of these waits occur. Actual schedule composition gates adoption.
        crossing_cycles_bound=(36*4+2)*64*2*interior
        variants.append(dict(name=name,slot_um=[w,h],slot_mm2=w*h/1e6,
            hard_element_cycles_added=0,RTL_unchanged=True,registered_boundaries=True,
            replicas=1,MACs_per_cycle=0,compute_intensity_macs_per_byte=0,
            memory_ports_bytes_per_cycle=dict(program_copy_read=128,program_copy_write=8),
            boundary_bits_per_cycle=dict(me_snapshot_out=92,su_snapshot_in=57,
                layer_start_in=49,program_write_in=75,vm_write_out=553,vm_x_descriptor_out=53),
            routing_tracks=dict(existing_pin_density_limit_bits_per_um_per_layer=12,
                layers_per_face=2,minimum_S_capacity_tracks=int(2*w/.096),
                control_upper_bus_bits=28,port_element_request_bits=114,
                per_band_scale_bits=201,die_relay_pitch_um=430.56),
            replica_cost=dict(program_store_bits=64*1024,read_mux='64:1 x1024 unchanged',
                write_demux='64 word enables unchanged',fanout='existing registered reset and scale request copies unchanged'),
            area_bound_um2=base_w*base_h*.60,
            area_bound_basis='analytical60% base-slot sizing ceiling; not measured cell area',
            bound_utilization=(base_w*base_h*.60)/(w*h),
            floorplan=dict(old_tree_slot_h_um=3732.48,control_plus_four_upper_h_um=h+upper_h,
                vertical_fit=h+upper_h<=3732.48,
                extra_column_width_um=extra,preserve_external_relay_channel_um=259.2,
                required_recipe_change='widen tree/control spine column and shift eastern instances; retain259.2um relay channel',
                die_um=[die_w+extra,die_h],die_mm2=(die_w+extra)*die_h/1e6,
                added_die_mm2=extra*die_h/1e6,reticle_mm2=858,
                reticle_fit=(die_w+extra)*die_h/1e6<=858),
            latency=dict(clock_hz=1.2e9,hard_element_added_cycles=0,
                extra_station_budget_per_crossing=interior,
                conservative_token_added_cycles_bound=crossing_cycles_bound,
                conservative_token_added_ns_bound=crossing_cycles_bound/1.2,
                adoption_requires='actual relay inventory and static program composition; bound is not a rate claim'),
            adoption_holds=['actual controller-pair minimum exactness gate',
                'source-matched hardened pin views and die clock/relay context',
                'real widened recipe legality, routing-layer and pin-access checks',
                'measured TT setup>=0,FF hold>=0,DRC0 under unchanged constraints']))
    return dict(schema='opentallas.qwen.ctlm-deep-queue.v1',default_off=True,
        source=dict(rom_plan=str(rom.relative_to(ROOT)),sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                    RTL_sha256=hashlib.sha256((ROOT/'rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm.sv').read_bytes()).hexdigest()),
        model_precedes_variants=True,baseline_die_mm2=evidence['die_mm2'],variants=variants)
