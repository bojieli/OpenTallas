"""Generate a production64-MAC comparison around the actual native source."""
import json,re,pathlib
base=pathlib.Path('.')
src=(base/'rtl/test/tb_qwen_a0_safe_outland.sv').read_text()
m=json.load(open('native/manifest.json'))
ports=[]
for line in open('native/candidate.v'):
 mm=re.match(r'(input|output) \\(.+) ;',line)
 if mm:ports.append((mm[1],mm[2]))
assert len(ports)>2000
conn=[]
for direction,name in ports:
 root=name.split('[')[0]
 sig={'rst_n':'rs','tile_id':"16'd0",'tap':'tap','n_a':'na','n_b':'nb','t_out':'ut','n_y':'un','tie_hi':'uhi','tie_lo':'ulo'}.get(root,'rclock' if root=='ck_tx0' else 'ck' if root.startswith('ck') else None)
 assert sig is not None,name
 bit=re.search(r'\[(\d+)\]',name)
 if bit:sig="1'b0" if root=='tile_id' else sig+'['+bit[1]+']'
 conn.append('.\\'+name+' ('+sig+')')
dut='qfd_tile_nk_regroot5_reset_native dut (\n'+',\n'.join(conn)+'\n);'
src=src.replace('tb_qwen_a0_safe_outland','tb_qwen_a0_reset_native')
start=src.index('initial begin #0.2;');end=src.index('reg ck=0',start)
src=src[:start]+src[end:]
start=src.index('qfd_tile_nk_rp2_romleaf_rr #');end=src.index('genvar p,b;',start)
src=src[:start]+dut+'\n'+src[end:]
line='    dut.u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.g_rb[b].g_single.g_col[p].u_leaf.u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;'
assert line in src;src=src.replace(line,'')
unrolled=[]
for p in range(2):
 for b in range(5):
  name=f'u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.g_rb\\[{b}\\].g_single.g_col\\[{p}\\].u_leaf'
  unrolled.append(f'initial begin #0.1; for(integer row=0;row<512;row++)for(integer bitn=0;bitn<2128;bitn++) dut.\\{name} .u_rom.arr[row][bitn]=((row*17+bitn*13+{p}*31+{b}*7)%29)<14; end')
src=src.replace('function automatic [378:0] command', '\n'.join(unrolled)+'\nfunction automatic [378:0] command')
# Numeric proof repeats all five real operations after warm reset. The original
# source has no handshakes; static200-edge first GO is explicit, not minimum.
src=src.replace('for(cyc=0;cyc<6500;cyc=cyc+1)begin','for(cyc=0;cyc<13040;cyc=cyc+1)begin\n  if(cyc==6500) rs=0;\n  if(cyc==6540) rs=1;')
src=src.replace('if(cyc>=200 && (cyc-200)%1200==0 && cyc<6200)', 'if((cyc%6540)>=200 && ((cyc%6540)-200)%1200==0 && (cyc%6540)<6200)')
src=src.replace('command((cyc-200)/1200)','command(((cyc%6540)-200)/1200)')
src=src.replace('if(cyc>100)begin','if((cyc%6540)>100 && rs)begin')
src=src.replace('ROMLEAF_PARENT_NK_NATIVE_PASS','A0_RESET_NATIVE_NUMERIC_PASS')
leaf=next(r['leaf'] for r in m['leaf_endpoints'] if r['clock']=='ck_tx0')
# Mutants alter the actual new native wire, not a mirrored test model.
src=src.replace('reg ck=0',f"initial begin #0.2; if(MUT==41) force dut.\\a0_reset_leaf_{leaf:02d}_q = 1'b0; if(MUT==42) force dut.\\a0_reset_face1_q = rs; end\nreg ck=0")
src=src.replace('reg [507:0] tap=0;', 'reg run_tx0=1; wire rclock=ck & run_tx0;\nreg [507:0] tap=0;')
src=src.replace('repeat(8)@(negedge ck);rs=1;', 'repeat(8)@(negedge ck);rs=1; repeat(12)@(negedge ck); #0.2;rs=0;repeat(8)@(negedge ck);#0.2;rs=1;repeat(12)@(negedge ck);#0.7;rs=0;repeat(8)@(negedge ck);#0.1;rs=1;')
src=src.replace('if(cyc==6500) rs=0;', 'if(cyc==6500) rs=0;\n  if(cyc==6503) run_tx0=0;\n  if(cyc==6517) run_tx0=1;')
monitor=['reg [2:0] reset_face_expected;', 'always @(posedge ck) reset_face_expected <= {reset_face_expected[1:0],rs};', 'integer reset_trace_checks=0;', 'integer reset_sample_count=0; always @(posedge ck) reset_sample_count=reset_sample_count+1;']
for n in sorted({r['leaf'] for r in m['leaf_endpoints']}):
 clock=next(r['clock'] for r in m['leaf_endpoints'] if r['leaf']==n)
 clk='rclock' if clock=='ck_tx0' else 'ck'
 monitor += [f'reg reset_expected_{n}; always @(posedge {clk}) reset_expected_{n} <= reset_face_expected[2];', f'always @(negedge ck) if(reset_sample_count>8) begin reset_trace_checks=reset_trace_checks+1; if(dut.\\a0_reset_leaf_{n:02d}_q !== reset_expected_{n}) $fatal(1,"A0_RESET_TRACE_FAIL leaf{n} clock{clock} sample%0d",reset_sample_count); end']
src=src.replace('integer cyc,errors=0', '\n'.join(monitor)+'\ninteger cyc,errors=0')
src=src.replace('$display("A0_RESET_NATIVE_NUMERIC_PASS', '$display("A0_RESET_TRACE_PASS checks%0d",reset_trace_checks);\n $display("A0_RESET_NATIVE_NUMERIC_PASS')
(base/'native/tb_numeric.sv').write_text(src)
print('A0_NATIVE_BENCH_GENERATED',len(ports),'ports; TX-clock reset leaf',leaf)
