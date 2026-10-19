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
src=src.replace('reg ck=0,rs=0; always #0.5 ck=~ck;', 'reg tick=0; always #0.5 tick=~tick; reg clocks_run=1; wire ck=tick & clocks_run; reg rs=0;')
src=src.replace('reg [507:0] tap=0;', 'reg run_tx0=1; wire rclock=ck & run_tx0;\nreg [507:0] tap=0;')
src=src.replace('repeat(8)@(negedge ck);rs=1;', 'repeat(8)@(negedge ck);rs=1; repeat(12)@(negedge ck); #0.2;rs=0;repeat(8)@(negedge ck);#0.2;rs=1;repeat(12)@(negedge ck);#0.7;rs=0;repeat(8)@(negedge ck);#0.1;rs=1;')
src=src.replace('@(negedge ck);', '@(negedge tick);')
src=src.replace('if(cyc==6500) rs=0;', 'if(cyc==6500) rs=0;\n  if(cyc==6499) run_tx0=0;\n  if(cyc==6542) clocks_run=1; if(cyc==6547) run_tx0=1;')
monitor=['reg [2:0] reset_face_expected;', 'always @(posedge ck or negedge rs) if(!rs) reset_face_expected <= 0; else reset_face_expected <= {reset_face_expected[1:0],1\'b1};', 'integer reset_trace_checks=0;', 'integer reset_sample_count=0; always @(posedge ck) reset_sample_count=reset_sample_count+1;']
for n in sorted({r['leaf'] for r in m['leaf_endpoints']}):
 clock=next(r['clock'] for r in m['leaf_endpoints'] if r['leaf']==n)
 clk='rclock' if clock=='ck_tx0' else 'ck'
 monitor += [f'reg reset_expected_{n}; always @(posedge {clk} or negedge reset_face_expected[2]) if(!reset_face_expected[2]) reset_expected_{n} <= 0; else reset_expected_{n} <= 1;', f'always @(negedge tick) if(reset_sample_count>8) begin reset_trace_checks=reset_trace_checks+1; if(dut.\\a0_reset_leaf_{n:02d}_q !== reset_expected_{n}) $fatal(1,"A0_RESET_TRACE_FAIL leaf{n} clock{clock} sample%0d",reset_sample_count); end']
src=src.replace('integer cyc,errors=0', '\n'.join(monitor)+'\ninteger cyc,errors=0')
src=src.replace('$display("A0_RESET_NATIVE_NUMERIC_PASS', '$display("A0_RESET_TRACE_PASS checks%0d",reset_trace_checks);\n $display("A0_RESET_NATIVE_NUMERIC_PASS')
src=src.replace('tb_qwen_a0_reset_native','tb_qwen_a0_reset_native_r4')
src=src.replace('integer MUT=0;', 'integer MUT=0;integer FIRST_GO=16;initial if($value$plusargs("FIRST_GO=%d",FIRST_GO))begin end')
src=src.replace('(cyc%6540)>=200', '(cyc%6540)>=FIRST_GO').replace('((cyc%6540)-200)', '((cyc%6540)-FIRST_GO)')
src=src.replace('if((cyc%6540)>100 && rs)begin', 'if((cyc%6540)>12 && rs)begin')
old='if(expected_t!==ut || rn!==un || rhi!==uhi || rlo!==ulo)begin'
new='if(expected_t[513:512]!==ut[513:512] || ((expected_t[512]||ut[512]) && expected_t[511:0]!==ut[511:0]) || rn[513:512]!==un[513:512] || ((rn[512]||un[512]) && rn[511:0]!==un[511:0]) || rhi!==uhi || rlo!==ulo)begin'
assert old in src;src=src.replace(old,new)
src=src.replace('integer cyc,errors=0', 'integer idle_payload_differences=0;integer last_go=-1;integer first_result_seen=0;integer cyc,errors=0')
src=src.replace('tap[379:1]=command(((cyc%6540)-FIRST_GO)/1200);tap[0]=1;', 'tap[379:1]=command(((cyc%6540)-FIRST_GO)/1200);tap[0]=1;last_go=cyc;first_result_seen=0;')
src=src.replace('checks=checks+1;', 'checks=checks+1; if(!expected_t[512] && !ut[512] && expected_t[511:0]!==ut[511:0])idle_payload_differences=idle_payload_differences+1; if(ut[512] && !first_result_seen)begin first_result_seen=1;$display("A0_FIRST_VALID go%0d result%0d age%0d",last_go,cyc,cyc-last_go);end')
src=src.replace('$display("A0_RESET_TRACE_PASS', '$display("A0_IDLE_PAYLOAD_DIFFERENCES %0d",idle_payload_differences);\n $display("A0_RESET_TRACE_PASS')
src=src.replace('tb_qwen_a0_reset_native_r4','tb_qwen_a0_reset_native_r5')
src=src.replace('integer FIRST_GO=16;', 'integer FIRST_GO=19;')
src=src.replace('((cyc%6540)-FIRST_GO)', '((cyc%6540)-FIRST_GO-(cyc>=6540?4:0))')
src=src.replace('(cyc%6540)>=FIRST_GO', '(cyc%6540)>=(FIRST_GO+(cyc>=6540?4:0))')
src=src.replace('if((cyc%6540)>12 && rs)begin', 'begin')
start=src.index('qfd_tile_nk_rp1 ref_tile');end=src.index('\n',start)
src=src[:start]+src[start:end].replace('(ck)','(tick)')+src[end:]
src=src.replace('always @(posedge ck) rt_prev', 'always @(posedge tick) rt_prev')
src=src.replace("na[513:512]={1'b0,(cyc%11==0)};", "na[513:512]={1'b0,(((cyc>=32&&cyc<6400)||cyc>=6563)&&(cyc%11==0))};")
leaves=','.join('dut.\\a0_reset_leaf_%02d_q '%n for n in reversed(range(19)))
obs='wire [18:0] observed_leaf={'+leaves+'}; wire observed_ready=&observed_leaf; realtime last_ready=0; always @(posedge observed_ready)begin last_ready=$realtime;$display("A0_ALL_LEAVES_READY time%0.3f",$realtime);end\n'
obs+='always @(posedge ck)if(tap[0])$display("A0_GO_SAMPLE cyc%0d time%0.3f ready_age%0.3f",cyc,$realtime,$realtime-last_ready);\n'
src=src.replace('integer cyc,errors=0', 'integer cyc,errors=0')
src=src.replace('integer idle_payload_differences=0;',obs+'integer idle_payload_differences=0;')
(base/'native/tb_numeric_r5.sv').write_text(src)
print('A0_NATIVE_BENCH_GENERATED',len(ports),'ports; TX-clock reset leaf',leaf)
