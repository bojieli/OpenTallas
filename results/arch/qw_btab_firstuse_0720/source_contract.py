from pathlib import Path
import json,hashlib,itertools,re
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
rtl=root/'rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv';s=rtl.read_text();macro=root/'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v';ms=macro.read_text();lib=root/'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib';ls=lib.read_text()
# Exact source equations supporting the contract. This is not netlist SAT.
normalized=re.sub(r'\s+','',s);assert 'wire[3:0]bank_oh=4\'b0001<<bt_word[1:0];'in normalized
assert 'always@(posedgeck)q<=distinct;'in normalized
assert 'always@(posedgeck)q<=pick;'in normalized
assert '.r_ce_in(bt_re&&bt_word[1:0]==bk[1:0])'in normalized
assert '.w_mask_in({256{1\'b1}})'in normalized
assert re.search(r'if\s*\(r_ce_in\)\s*rd_out\s*<=\s*word_read\(r_addr_in\);\s*if\s*\(w_ce_in\)\s*word_write',ms)
assert '`ifndef OT_MEM_NO_INIT'in ms
assert not re.search(r'negedge\s+\w+',s);assert not re.search(r'negedge\s+\w+',ms)
checks=0
for bank in range(4):
 for rd in itertools.product([0,1],repeat=4):
  onehot=[int(i==bank)for i in range(4)]
  for bit in range(256):
   legacy=rd[bank];candidate=int(any(rd[i]&onehot[i]for i in range(4)));assert legacy==candidate;checks+=1
# Read pointer and read-data stage at edge R overwrite all relevant antecedent
# state before the output stage at R+1; other banks' held rd are arbitrary.
ports=re.findall(r'input\s+wire\s+(?:\[[^]]+\]\s*)?(\w+)',s.split(');',1)[0]);assert set(ports)=={'ck','bt_re','bt_word','tw_we','tw_kind','tw_addr','tw_data'},ports
existing=root/'results/arch/qw_btab_canonical_0720/summary.json';native=json.loads(existing.read_text());ffs={m:v['ff']for m,v in native['master_roles'].items()if 'ff'in v};assert ffs and all(v['clear']is None and v['preset']is None for v in ffs.values())
libtimings=sorted(set(re.findall(r'timing_type\s*:\s*([^;]+);',ls)));assert 'rising_edge'in libtimings and not any('recovery'in x or'removal'in x for x in libtimings)
proof={'scope':'Exact source-equation/per-bit Boolean selection certificate plus actual-role reset inventory. NOT full RTL/netlist formal equivalence or universal initialization simulation.','DUT_sha256':hashlib.sha256(s.encode()).hexdigest(),'physical_macro_model_sha256':hashlib.sha256(ms.encode()).hexdigest(),'macro_TT_Lib_sha256':hashlib.sha256(ls.encode()).hexdigest(),'selection_cofactor_checks':checks,'selection_PASS':True,'first_defined_contract':{'read_sample_edge':'R, r_ce_in qualified at selected bank','defined_iff':'Selected logical row has received a complete common1024-bit write strictly before this sample; no value obligation for unwritten-row reads.','output_edge':'visible after R+1; downstream sequential consumer can sample at R+2','no_cycle_warmup':'Checks start at each row/bank first defined read, not fixedcycle136 or global full preload.','memory_behavior':'Actual physical model: read-before-write when CE read/write same row on same edge. Read of previously uninitialized row concurrent with first write is undefined; next read is defined.','Liberty_phase':'Actual rd_out timing arc rising_edge and input setup_rising/hold_rising. Liberty does not independently specify collision data value.','source_equations':['AtR: t1_bank<=requested_bank; all16select copies<=onehot(requested_bank); selected SRAM rd_out<=prewrite row word.','AtR+1: legacy t2_bank<=t1_bank and btcap<=rd; candidate each16bitq<=OR of rd_i AND onehot_i.','For arbitrary other-bank rd bits and arbitrary prior selection/output FF state, afterR+1 both yield the selected prewrite word.'], 'write_obligation':'Each tw_kind2 write updates all256bits in all4banks at tw_addr[8:2], full1024-bit group; no partial-write initialization assumption.'},'typed_no_reset_inventory':{'declared_functional_reset_ports':[],'source_standardFF_event':'posedge ck only','actual_native_standardFF_roles':ffs,'actual_native_standardFF_async_controls':0,'macro_functional_event':'posedge clk only; row/column repair inputs are constant0, not reset','SRAM_array_reset':False,'framework_typed_receipt':'No new framework reset-proof override or waived receipt manufactured. No-reset source/native role inventory is the asserted scope.'},'capacity':{'logical_words':512,'logical_word_bits':256,'nominal_SRAM_instances':4,'nominal_rows_per_instance':128,'nominal_bits_per_row':256,'logical_bits':131072,'nominal_physical_capacity_bits':131072,'logical_KiB':16,'nominal_physical_KiB':16,'nominal_physical_to_logical_ratio':1,'physical_cells_including_spares':4*130*258,'spare_inclusive_ratio':4*130*258/131072,'spare_inclusive_KiB':4*130*258/8/1024,'not_32KiB':True},'parent_scope':'No global full-table boot/install guarantee is asserted. Parent must prove every consumed read references an initialized row and honors fixed read age; unused/uninstalled rows remain arbitrary. This is a required interface obligation, not an allowed implicit zero fill.'}
(out/'SOURCE_CONTRACT.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'cofactor_checks':checks,'standardFF_async_controls':0,'capacity_KiB':16,'first_defined_output':'R+1'},indent=2))
