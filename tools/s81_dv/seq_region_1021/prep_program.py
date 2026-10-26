from pathlib import Path
import re,sys,json
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
s=Path('rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_seq_host.sv').read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('dsdv_seq_host #(', 'dsdv_seq_host_r2_bw #(')
s=re.sub(r'\bdut\.u_l([012])\b',r'dut.u_c.u_l\1',s)
replace('LVS = LVO + RL, LJ = 2, LKD = 3, LR = 6 + RL, LS = 9, LCW = 3, LCF = 6',
        'LVS = LVO + RL + 2, LJ = 4, LKD = 5, LR = 8 + RL, LS = 9, LCW = 3, LCF = 8')
replace('DV_S = LS + 5', 'DV_S = LS + 9')
# The LK -> SQ landing adds two edges before job acceptance. Present the request
# two phases earlier, and align the independent golden issuer to that actual arrival.
replace('launch0 = cyc + D + 9;', 'launch0 = cyc + D + 7;')
replace('t + D - 3 == launch0', 't + D - 5 == launch0')
# Four explicit regional reset stages plus the existing three local stages.
# All output checks stay active. Drive known beats at the first legal edge,
# then start random traffic; nothing is suppressed at the receivers.
replace('if (t + LR < NMAX) begin', """if (t == 8) begin
            a = {V{1'b0}}; a[0] = 1'b1; a[3:1] = 3'd3; a[64:32] = 33'h123456789;
            AN[t + LR - 1] = a; vi_s <= a;
            a[64:32] = 33'h155555555; AS[t + LR - 1] = a; vi_n <= a;
            narr = narr + 2;
            $display("SEQ_REGION_FIRST_LEGAL_INPUT edge=%0d expected_output=%0d", t, t + LR - 1);
        end
        if (t > 8 && t + LR < NMAX) begin""")

tb=out/'tb_seq_region_program.sv';tb.write_text(s)
s=Path('rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_c_bench.sh').read_text()
f=re.search(r'F="(.*?)"\ngrep',s,re.S).group(1).replace('$U','rtl/dsrom_sys/s81_dv/unit').replace('$R/','').split()
f=[x for x in f if x not in ['rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv','rtl/dsrom_sys/s81_dv/unit/test/dsdv_seq_host_bw.sv']]
f+=['rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_n32.sv','rtl/common/landed_parent/ot_pl_land_rst_copy.sv','rtl/dsrom_sys/s81_dv/unit/r2/dsdv_seq_host_c_r2_lp.sv','rtl/dsrom_sys/s81_dv/unit/r2/dsdv_seq_host_r2_bw.sv',str(tb)]
(out/'files.txt').write_text('\n'.join(dict.fromkeys(f))+'\n')
(out/'calendar_changes.json').write_text(json.dumps({'service_completion_rows':'+4 edges','host_to_issuer_request':'+2 edges, phase scheduled two earlier','job_command_return':'+2 edges','kit_done_return':'+2 edges','southbound_command_output':'+2 edges','rung_each_direction':'+2 edges','config_cw':'+2 edges','SQ_VC_loop':'unchanged','host_ingest':'unchanged','boot_release_extra_edges':4,'total_reset_release_edges':7,'earliest_legal_rung_input_edge':8,'first_legal_inputs':'Known north and south beats at edge 8, every output check active','status':'Needs actual behavioral positive; these are source-derived expectations.'},indent=2)+'\n')
