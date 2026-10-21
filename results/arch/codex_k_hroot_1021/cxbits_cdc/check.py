import json,sys,pathlib
root=pathlib.Path(__file__).parent.resolve();sys.path.insert(0,str(root/'tools/ref_tile'));import gray_fifo_cdc_constraints as G
spec=dict(kind='tile',clock='multiple_cts_roots',top='cxbits_cdc',sources=['rtl/link/ot_link_afifo.sv','rtl/lib/ot_reset_sync.sv','qkc_afifo_bits_1021.sv','top.sv'],clock_relationship=dict(kind='independent_clock_families',periods_ps=dict(core=833.333,host=1000.0)),clock_entry_domains=dict(core=dict(ratio=[1,1],ports=['wclk'],inputs=['rst_n','wr','wdata'],outputs=['wfull','wfreed','ovf']),host=dict(ratio=[1000000,833333],ports=['rclk'],inputs=['rd'],outputs=['rempty','rcount','q','q_v'])))
# First preserve the reserved attribute diagnostic as an expected policy refusal.
r=dict(spec);r['sources']=[x if x!='qkc_afifo_bits_1021.sv' else 'reserved_source.sv' for x in spec['sources']]
try:G._elaborate_sources(r,root);raise AssertionError('reserved-attribute mutant unexpectedly accepted')
except G.GrayFifoError as e:(root/'reserved_refusal.txt').write_text(str(e)+'\n')
try:
 d=G.lint(spec,root);(root/'cdc.json').write_text(json.dumps(d,indent=2)+'\n');print('CDC_PASS')
except Exception as e:
 (root/'cdc_refusal.txt').write_text(type(e).__name__+': '+str(e)+'\n');print('CDC_REFUSED',e);raise
