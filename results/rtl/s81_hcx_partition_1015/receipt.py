import pathlib,hashlib,json
r=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcp-partition-1015-v2');s=(r/'tools/s81_ftok/hcx_partition_gate.sh').read_text();files=s.split('src=(\n')[1].split('\n)')[0].split();files+=['tools/s81_ftok/hcx_projection_vectors.py','tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/s81_ftok/hcx_partition_gate.sh','results/rtl/s81_hcx_home_1014/fixture_L00_row0.tar.gz','pass/obj/Vtb_s81_hcx_projection_partition','run_boundary.py','boundary/summary.json']
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcx-native-1014');images={str(p.relative_to(b)):h(p) for p in (b/'resident_row0_full').iterdir() if p.is_file()}
for tag in ['L00','L24','L25','L39','M0R0','M1R0','M2R4']:
 for p in (b/'resident_boundary_final'/tag).iterdir():
  if p.is_file():images[str(p.relative_to(b))]=h(p)
out={'scope':'Exact deployed binary/source/fixture/fullresident image/expectedvector identities for14output arithmetic gate; clocks simulated at equal phase; no physical or end-to-end qualification','deployed_source_sha256':{f:h(r/f) for f in files},'resident_data_sha256':images,'source_root':str(r),'data_root':str(b),'mutant':'Same binary +MUT_STAGE replaces first staged4096bit beat in both attn/FFN by256BF16 1.0words; expected outputs unchanged. Both outputs mismatch and keep264cycle calendar.','clock_ABI':{'shell':'clk','memory_banks':'clk_bank[7:0]','lane8_children':'clk_lane[31:0]','tree':'clk_tree','new_independent_clock_input_bits':41,'parent_phi_minus_R_delivery':'UNQUALIFIED until actual per-child insertion, face placement and registered seam timing measured'}}
(r/'binary_source_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
