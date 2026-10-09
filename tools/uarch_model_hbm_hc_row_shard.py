"""Whole-row HC supply model; callable by the unified model."""
def model():
    return {"K":20480,"rows":24,"sublayers":80,"dies":96,
      "dtype":"F32","owner":"(sublayer*24+row)%96",
      "whole_rows_per_die_token":20,"weight_bytes_per_die_token":1638400,
      "macs_per_cycle":256,"required_production_clock_hz":900000000,
      "clock_qualification":"actual900MHzPLLserialdomain andCDCbinding pending; no833psclaim",
      "service_clock_hz":1200000000,"prefetch_row_us_min_at_serial":2.844444444,
      "serial_supply_us_per_die_token_min":56.888888889,"runs_per_row":80,
      "weight_bytes_per_cycle_compute":1024,"x_bytes_per_cycle_compute":512,
      "weight_supply_bytes_per_cycle":32,"prefetch_cycles_per_row_min":2560,"serial_supply_cycles_per_die_token_min":51200,
      "resident_weight_bytes":81920,"reserved_weight_bytes":131072,
      "weight_banks":8,"weight_bank_read_bits":1024,
      "request_boundary_bits":45,"response_boundary_bits":270,
      "routing_tracks_min":315,"replicas_per_die":1,
      "request_mux_inputs":8,"response_demux_outputs":8,
      "hc_area_mm2_estimate":0.8,"operand_sram_area_mm2":"unmeasured",
      "floorplan_slot_fit":"pending SRAM views and routing",
      "token_latency":"prefetch must schedule ahead; no overlap credit before measured schedule",
      "hbm_token_stream_cycles_at_3p85TBps":510.67,
      "exactness":"whole row, chunk8; no inter-die split accumulation",
      "physical_status":"not qualified"}

def sram_model():
    row=model()
    row.update({"data_macro":"ot_sram_1r1w_128x256_m1_r2c2",
      "data_macro_count":32,"check_macro_count":8,
      "reserved_operand_bytes_with_checks":163840,
      "live_row_check_bytes":3200,"read_latency_cycles":3,
      "secded_read_cycles":2,"secded_write_cycles":1,
      "extra_memory_pipeline_cycles_vs_window":1,
      "check_write":"10 active-high mask bits per returned sector, no RMW",
      "prefetch_done":"2560 unique sectors committed to macros",
      "physical_status":"macro instances present; views and SS/FF qualification pending",
      "added_latency_measurement":"pending full-shape successor gate"})
    return row
