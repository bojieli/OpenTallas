import pathlib,json
r=pathlib.Path(__file__).parent
j=json.load(open(r/'r7w.readback.json'));rows=[x for x in j['cloned_flops'] if not x['has_async_pins']]
s=(r/'tb_r7w_lifecycle.sv').read_text();inject='initial begin #1;\n'+'\n'.join(f"dut.c{x['copy']}.QN=1'b1;"for x in rows)+'\nend\n'
s=s.replace('module tb;','module tb;\n'+inject)
s=s.replace('cal_start=(cyc==260);cal_seg=0;','cal_start=(cyc==260);cal_seg=1;')
s=s.replace('if(cyc==600)begin',"if(cyc==198 || cyc==199)begin cfg_tx_we=(cyc==198);cfg_rx_we=(cyc==199);cfg_addr=6'd32;cfg_data=32'd2;end\nif(cyc==600)begin")
(r/'tb_r7w_independent_init.sv').write_text(s)
