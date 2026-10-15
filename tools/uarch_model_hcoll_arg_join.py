#!/usr/bin/env python3
"""Pre-build native SW ARGMAX selected-mechanism composition model."""
import json

def model():
 return {'scope':'selected actual SW issuer/control/qslots/ARGMAX/writer plus8VMbanks; no full-q3 claim',
 'group':96,'read_cycles':24,'lines_per_read_cycle':4,'program_rows':64,
 'native_VM_banks':8,'native_VM_SRAMs':24,'program_SRAMs':3,
 'cycles_relative_first_executed_word':{'arg_start':0,'VM_request_first':1,'VM_request_last':24,
 'source_capture_first':11,'source_capture_last':34,'ARG_input_first':14,'ARG_input_last':37,
 'ARG_input_sampling_last':37,'flush':38,'publish':44,'ARG_source_capture':45,'RGX_writer_capture':48,
 'SRAM_low_commit':53,'SRAM_high_commit':54,'native_readback_request':56,'halt_row':63,'halt_pulse_relative_start':66,'readback_response_relative_start':67},
 'runtime_arbitration':False,'golden_arrays':'expected operands/results only, never internal DUT service',
 'area':'unmeasured','physical_qualification':False}
if __name__=='__main__': print(json.dumps(model(),indent=2))
