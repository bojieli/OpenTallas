from pathlib import Path
import re,json,hashlib,collections
base=Path('/srv/opentallas-scratch2/claude/closure-loop/s81be-gray-m7-c7cf30d5d/routes/s81be_gray_m7_c7cf30d5d/work/orfs');p=base/'results/asap7/opentallas_dsfd_vm_be_sl_asap7_s81ph_s81be_gray_m7_c7cf30d5d/base/1_2_yosys.v';text=p.read_text();mods={}
for m in re.finditer(r'^module\s+(\S+)\s*\(.*?^endmodule',text,re.M|re.S):
 name=m.group(1);cells=collections.Counter(re.findall(r'^  (\S+)\s+\S+\s*\(',m.group(0),re.M));mods[name]=cells
memo={}
def total(name):
 if name in memo:return memo[name]
 out=collections.Counter()
 for cell,count in mods[name].items():
  if cell in mods:
   for k,v in total(cell).items():out[k]+=count*v
  elif 'DFF' in cell:out[cell]+=count
 memo[name]=out;return out
out=dict(schema='opentallas.be_gray_actual_mapped_census.v1',source_commit='c7cf30d5d',netlist_path=str(p),netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),effective_define='-DSYNTHESIS -DOT_BE_RCDC_GRAY',top='dsfd_vm_be_sl',top_mapped_FF_by_master=dict(total('dsfd_vm_be_sl')),top_mapped_FF=sum(total('dsfd_vm_be_sl').values()),FIFO_modules=[dict(module=n,count_by_master=dict(total(n)),FF=sum(total(n).values())) for n in mods if 'rcdc_gray' in n],actual_synthesis_metrics=json.loads((base/'logs/asap7/opentallas_dsfd_vm_be_sl_asap7_s81ph_s81be_gray_m7_c7cf30d5d/base/1_synth.json').read_text()),physical_qualified=False,final_route_FF=None,old_CLOSED_replaced=False)
out['flattened_FIFO_FF_namespaces']={f'u_rc{i}':sum(1 for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if m.group(2).startswith('\\u_rc'+str(i)+'.')) for i in (0,1)}
out['conditioner_instances']=[dict(master=m.group(1),instance=m.group(2),connections=m.group(3)) for m in re.finditer(r'^  (DFFASR\S+)\s+(\S+)\s*\((.*?)\n  \);',text,re.M|re.S)]
out['ACK_output_buffers']=[dict(master=m.group(1),instance=m.group(2),connections=m.group(3)) for m in re.finditer(r'^  (BUF\S+)\s+(\S+)\s*\((.*?)\n  \);',text,re.M|re.S) if 'cdc_rst_ack' in m.group(3)]
out['mapped_conditioner_FF_per_leaf']=4
out['mapped_conditioner_FF_four_leaves']=16
out['exported_ACK_ports_per_leaf']=4
out['distinct_final_ACK_sources_per_leaf']=2
out['nominal_generic_conditioner_FF_four_leaves']=32
out['controller_capture_FF_for_16_exported_ACK_signals']=32
out['physical_controller_binding']=None
out['mapped_memory_to_selected_output_groups']=[dict(fifo=i,source_memory_FF=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if m.group(2).startswith('\\u_rc'+str(i)+'.u_gray.g_c') and '.mem[' in m.group(2)],capture_selected_output_FF=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if m.group(2).startswith('\\u_rc'+str(i)+'.u_gray.g_c') and '.od[' in m.group(2)]) for i in (0,1)]
out['first_pointer_synchronizer_FF']=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if re.search(r'\.(rp_gw1|wp_gr1)\[',m.group(2))]
out['second_pointer_synchronizer_FF']=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if re.search(r'\.(rp_gw2|wp_gr2)\[',m.group(2))]
out['first_online_synchronizer_FF']=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if re.search(r'\.(rd_w1|rr_w1|wd_r1|wr_r1)\$',m.group(2))]
out['second_online_synchronizer_FF']=[m.group(2) for m in re.finditer(r'^  (DFF\S+)\s+(\S+)\s*\(',text,re.M) if re.search(r'\.(rd_w2|rr_w2|wd_r2|wr_r2)\$',m.group(2))]
print(json.dumps(out,indent=2))
