#!/usr/bin/env python3
"""Source structural extension to the unified uarch model; no rate repricing."""
import json
from pathlib import Path

def model():
    dw=128
    ff=16*dw+16*3+16+8*dw+8+3+1+2+8+12+8
    return dict(schema='opentallas.s81.return-bank8-model.v1', macs_per_cycle=0,
      memory_bytes_per_cycle=0, sram_macros=0, incoming_records_per_cycle=8,
      input_record_bits_per_cycle=8*(dw+8+1), output_bits_per_cycle=8*(dw+1),
      leaf_input_pins=1170,leaf_output_pins=1048,leaf_pins=2218,
      leaf_declared_ff=ff, leaves_per_128b_slice=4, total_vm_leaves=16,
      total_vm_declared_ff=16*ff,old_slice_declared_ff=12582,
      added_ff_per_slice=4*ff-12582, outline_um=[129.6,129.6],
      leaf_area_um2=129.6**2, logic_fit='UNMEASURED; native mapped area required',
      mux_cost='16 entries x 8 sources x128 bits OR-mask selectors; lane invariant removes cross-lane matrix',
      maximum_data_ports_per_face=512, pin_pitch_um=.192,nominal_face_slots=675,
      extra_cycle=0, storage_edge='E9',release_edge='E10',
      row_output_control='8 conditionally clocked parity registers; registered mask/token row enables; 257 mappedparityloads inclfeedback and128enableloads perrow',
      release_prediction='stage9 prepare metadata; compute from next valid/groups AFTER current release and arrivals',
      completeness_peer_bits=48, peer_requirement='four 12-bit registered tokens (valid/group3/rowcomplete8); E10 localreduction after registered flags; local AND inside each leaf',
      production_budget='8 rows/leaf/edge;32 rows/slice/edge; no stalls/ready/credits',
      qualification=False, open=['native CTS/TT/FF/DRC','global bank-to-lane and lane-to-router exact pins/ages','bounded compact peer token placement','actual rsched stage9 integration','canonical compiler/runtime composition'])
if __name__=='__main__':
    out=Path(__file__).resolve().parents[2]/'results/uarch/s81_return_bank8_1015/model.json'
    out.write_text(json.dumps(model(),indent=2)+'\n')
    print(out)
