#!/usr/bin/env python3
"""Pre-build explicit ENGRAM238 control in real256/native512 catalogue."""
import json

def model(banks=19):
 if not 1<=banks<=32:raise ValueError('hostframe address capacity exceeded')
 return {'operation_bits':256,'meaningful_operation_bits':238,'zero_reserved_bits':18,
  'operations_per_word':2,'native_macro':'ot_sram_1r1w_64x512_m1_r2c2','native_macro_count':banks,
  'capacity_cycles':banks*128,'nine_node_component_catalogue_macros':9*banks,
  'nine_node_component_catalogue_clock_roots':9*(1+2*banks),
  'selection_mux_onebit2to1_equivalents':512*(banks-1),'current_Engram_operations':2424,'final_profile_fit_claim':False,
  'host_targets':[120,121,122,123],'configuration':'raw256, address=controlordinal=global512word*2+half; completepairs required',
  'descriptor':'base12 even aligned,limit13 exclusivecontrolcycles,loops1; no protected223/c7a1 truncation',
  'host_descriptor_launch_gap_edges':64*banks+2,'host_word_gap_edges':2,
  'raw_launch_to_control_output_edges':6,'raw_launch_to_consumer_edges':7,
  'LCP_producer_FF_to_control_edges_analytical':8,'LCP_producer_FF_to_consumer_edges_analytical':9,
  'timing_anchor':'localrawlaunch is alreadyHIGH before its capture edge; overlay rawFFQ atLCP+1 capturedLCP+2',
  'pipeline':'registeredread -> actualSRAM -> memoryleafQ -> perbankinputcaptureQ -> selected512Q -> low/high256Q',
  'native_read_request_period_edges':2,'native_read_bytes_per_request':64,'sustained_catalogue_bytes_per_cycle':32,
  'clock_roots':{'controller':1,'native_memory':banks,'bank_input_capture':banks},
  'controller_register_upper_bound':4000+64*banks,'native_memory_root_output_FFs_each':512,
  'bank_capture_FFs_each':512,'all_roots_sink_bound_below15000':True,
  'mux':'banks-to1 x512b selectedregisteredword;256b registeredhalf output',
  'boundary':'rawhost256capture,256registeredcontroloutput, independentlycapturednativebankfaces',
  'area_floorplan':'actualnativeSRAM macros + RTL flops/mux; not mapped/routed; no assignedslot fit claim',
  'elastic_queue':0,'runtime_ready_credit':False,'macs_per_cycle':0,
  'normative_scope':'opt-in typed ENGRAM control programme, notunchanged G25 A.HBM orHBMSTG/LIST',
  'qualification':'nativecomponent andactual9nodejoin pending; no productionprice/timing qualification'}
if __name__=='__main__':print(json.dumps(model(),indent=2))
