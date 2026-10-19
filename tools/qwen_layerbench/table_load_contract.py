"""One explicit origin ledger for calendar-driven fixed table installs.

These are component timing/reservation prices, not a production-token model.
The93-edge table-port window starts at the loader input sample. The103-edge
caller reservation starts nine edges earlier at the explicit calendar range
start; its extra front/tail edges are not extra table-write-port occupancy.
"""
READ_SLOTS=88
LOADER_FIRST_PAYLOAD=3
LOADER_LAST_PAYLOAD=90
TARGET_WRITE_AFTER_PAYLOAD=1
TARGET_READ_AGE=2
LOADER_FIRST_READ_BOUND=92
LOADER_PORT_RESERVATION=93
RANGE_COMMAND_OUTPUT=8
COMMAND_TO_LOADER_SAMPLE=1
RANGE_TO_LOADER_SAMPLE=RANGE_COMMAND_OUTPUT+COMMAND_TO_LOADER_SAMPLE
RANGE_RESERVATION=103
RANGE_RESERVATION_EXTRA_VS_LOADER=RANGE_RESERVATION-LOADER_PORT_RESERVATION

def contract():
    return dict(schema='opentallas.qwen.fixed-table-load-timing.v1',
      qualification='component bounds only; production event composition unbound',
      read_slots=READ_SLOTS,loader_origin='start input sample',
      loader_first_payload=LOADER_FIRST_PAYLOAD,loader_last_payload=LOADER_LAST_PAYLOAD,
      loader_last_vm_write=LOADER_LAST_PAYLOAD+TARGET_WRITE_AFTER_PAYLOAD,
      loader_first_read_sample_bound=LOADER_FIRST_READ_BOUND,target_read_age=TARGET_READ_AGE,
      loader_write_port_reserved_edges=LOADER_PORT_RESERVATION,
      range_origin='explicit cal_mu range start input sample',
      range_command_output=RANGE_COMMAND_OUTPUT,range_loader_input=RANGE_TO_LOADER_SAMPLE,
      range_first_payload=RANGE_TO_LOADER_SAMPLE+LOADER_FIRST_PAYLOAD,
      range_last_payload=RANGE_TO_LOADER_SAMPLE+LOADER_LAST_PAYLOAD,
      range_loader_reservation_end=RANGE_TO_LOADER_SAMPLE+LOADER_PORT_RESERVATION,
      range_reserved_edges=RANGE_RESERVATION,
      range_extra_front_edges=RANGE_TO_LOADER_SAMPLE,
      range_extra_tail_edges=RANGE_RESERVATION-RANGE_TO_LOADER_SAMPLE-LOADER_PORT_RESERVATION,
      actual_table_write_port_delta_edges=0,
      production_critical_path_delta=None)
