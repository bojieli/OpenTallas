"""Source-exact reset-cone diagnostic; not a full PHY/boot receipt."""
import hashlib
import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent
S = D / 'source'
source = {p.name: p.read_text() for p in S.glob('*.sv')}


def module(file, name):
    match = re.search(r'\bmodule\s+' + name + r'\b.*?endmodule', source[file], re.S)
    assert match, name
    return match[0]


bound = source['s81p_serdes__t13_bound.sv']
pattern = re.compile(r'ot_dp_rrelay\s+(\w+)\s*\(\.clk\(([^)]+)\),\s*\.d\(([^)]+)\),\s*\.q\(([^)]+)\)\)\s*;')
relays = []
for match in pattern.finditer(bound):
    relays.append(dict(instance=match[1], clock=match[2], d=match[3], q=match[4],
                       line=bound[:match.start()].count('\n') + 1, source=match[0]))
assert len(relays) == 144 and all(r['clock'] == 'clk' for r in relays)
by_q = {r['q']: r for r in relays}


def trace(q):
    chain = []
    while q != 'arst_n':
        assert q in by_q and q not in [x['q'] for x in chain]
        chain.append(by_q[q])
        q = by_q[q]['d']
    return list(reversed(chain))


path = trace('rst_n_t42')
assert len(path) == 7 and 'wire rst_n = rst_n_t42;' in bound
col = source['ot_pdie_serdes_col.sv']
reset_lines = [line.strip() for line in col.splitlines()
               if line.strip().startswith('always @(posedge') and 'rs_' in line and 'negedge rst' in line]
assert len(reset_lines) == 2
assert all(f'.ck_{name}(pma_rck)' in col for name in ('syn', 'dly', 'chn', 'out'))
lp = source['ot_s81_kp4_dec_native_flat_lp.sv']
pads = {}
for name in ('root', 'syn', 'dly', 'chn', 'out'):
    match = re.search(r'ot_pl_pad\s*#\([^;]+?\)\s+u_lpr_' + name + r'\s*\([^;]+;', lp)
    assert match, name
    pads[name] = match[0]
assert '.N(1)' in pads['root'] and all('.N(2)' in pads[n] for n in ('syn', 'dly', 'chn', 'out'))

primitive_text = '\n'.join([
    module('bind_cells.sv', 'ot_dp_rsync_s2'),
    module('bind_cells.sv', 'ot_dp_rrelay'),
    module('ot_pl_land.sv', 'ot_pl_pad'),
    module('ot_s81_kp4_common.sv', 'ot_s81_kp4_rst')])
names = ['die_root'] + [r['q'] for r in relays] + ['rn_t', 'rn_r']
names += [f'enc_leaf[{i}]' for i in range(4)]
names += [f'syn_leaf[{i}]' for i in range(3)] + ['out_leaf[0]']
domains = [0] * (1 + len(relays)) + [0, 1] + [0] * 4 + [1] * 4
assert len(names) == len(domains)
body = [f'module cone(input wire clk, pma_rck, external_rst_n, output wire [{len(names)-1}:0] obs);',
        'wire die_root;', 'ot_dp_rsync_s2 source_die_root(.clk(clk),.async_rst_n(external_rst_n),.sync_rst_n(die_root));',
        'wire arst_n = die_root;', 'wire ' + ','.join(r['q'] for r in relays) + ';']
body += [r['source'] for r in relays]
body += ['wire rst = rst_n_t42;', 'reg [1:0] rs_t, rs_r;'] + reset_lines
body += ['wire rn_t = rs_t[1], rn_r = rs_r[1];',
         'wire [3:0] enc_leaf;',
         'ot_s81_kp4_rst #(.NL(4)) encoder_reset(.clk(clk),.rst_n(rn_t),.rs_n(enc_leaf));',
         'wire ck_syn=pma_rck, ck_dly=pma_rck, ck_chn=pma_rck, ck_out=pma_rck;',
         'wire rst_n=rn_r;', 'wire lpr_root,lpr_syn,lpr_dly,lpr_chn,lpr_out;']
body += list(pads.values())
body += ['wire [2:0] syn_leaf; wire [0:0] out_leaf;',
         'ot_s81_kp4_rst #(.NL(3)) syn_reset(.clk(ck_syn),.rst_n(lpr_syn),.rs_n(syn_leaf));',
         'ot_s81_kp4_rst #(.NL(1)) out_reset(.clk(ck_out),.rst_n(lpr_out),.rs_n(out_leaf));']
body += [f'assign obs[{i}] = {name};' for i, name in enumerate(names)] + ['endmodule']
(D / 'reset_cone.sv').write_text('`timescale 1ps/1fs\n' + primitive_text + '\n' + '\n'.join(body) + '\n')

tb = r'''`timescale 1ps/1fs
module tb;
parameter real PMA_PHASE_PS=0;
reg clk=0, pma_rck=0, pma_enable=1, external_rst_n=1, measure=0;
always #416.5 clk=~clk;
initial begin #(PMA_PHASE_PS); forever begin #416.5; if(pma_enable) pma_rck=~pma_rck; else pma_rck=0; end end
wire [@LAST@:0] obs;
cone dut(.clk(clk),.pma_rck(pma_rck),.external_rst_n(external_rst_n),.obs(obs));
integer cur[0:@LAST@], longest[0:@LAST@];
genvar g;
generate for(g=0;g<@COUNT@;g=g+1)begin:counter
  wire selected_clock = @DOMAIN_EXPR@;
  always @(posedge selected_clock) if(measure)begin
    if(obs[g] === 1'b0)begin cur[g]=cur[g]+1; if(cur[g]>longest[g])longest[g]=cur[g]; end
    else cur[g]=0;
  end
end endgenerate
task clear;
integer i;
begin measure=0; for(i=0;i<@COUNT@;i=i+1)begin cur[i]=0;longest[i]=0;end measure=1;end
endtask
task report_case(input integer mode,input integer held);
integer i,mn,txmn,rxmn;
begin
 measure=0;mn=100000;txmn=100000;rxmn=100000;
 for(i=0;i<@COUNT@;i=i+1)begin
  if(longest[i]<mn)mn=longest[i];
  if(@DOMAIN_TEST@)begin if(longest[i]<rxmn)rxmn=longest[i];end
  else if(longest[i]<txmn)txmn=longest[i];
 end
 $display("RESET_CASE phase=%0.3f mode=%0d held=%0d minimum=%0d core_min=%0d rx_min=%0d rn_r_low=%0d rx_leaf_low=%0d",PMA_PHASE_PS,mode,held,mn,txmn,rxmn,longest[@RNR@],longest[@RXLEAF@]);
 if(mode<=1 && mn<64)$fatal(1,"running-clock contract width failed");
 if(mode==2 && mn>=64)$fatal(1,"short-reset negative not caught");
 if(mode==3 && (mn>=64 || longest[@RNR@]!=2 || longest[@RXLEAF@]!=2))$fatal(1,"stopped-clock scope negative did not expose two-edge RX pulse");
end endtask
task pulse(input integer mode,input integer held);
begin
 @(negedge clk);clear();external_rst_n=0;
 repeat(held)@(negedge clk);
 external_rst_n=1;
 repeat(40)@(negedge clk);
 if(mode==3)begin
  $display("STOPPED_STATE rn_r=%b rx_leaf=%b",dut.rn_r,dut.out_leaf[0]);
  if(dut.rn_r!==0 || dut.out_leaf[0]!==1)$fatal(1,"async versus synchronous reset distinction absent");
  pma_enable=1;repeat(40)@(negedge clk);
 end
 report_case(mode,held);
end endtask
initial begin
 #1;pulse(0,64);pulse(1,64);pulse(2,61);
 @(negedge pma_rck);pma_enable=0;pulse(3,64);
 $display("RESET_SCOPE_DIAGNOSTIC_COMPLETE clock_period_ps=833; no full PHY/boot/adoption claim");$finish;
end
endmodule
'''
rx = [i for i, domain in enumerate(domains) if domain]
condition_g = '(' + ' || '.join(f'g=={i}' for i in rx) + ')'
condition_i = '(' + ' || '.join(f'i=={i0}' for i0 in rx) + ')'
replacements = {'LAST': len(names)-1, 'COUNT': len(names), 'DOMAIN_EXPR': condition_g + ' ? pma_rck : clk',
                'DOMAIN_TEST': condition_i, 'RNR': names.index('rn_r'), 'RXLEAF': names.index('out_leaf[0]')}
for key, value in replacements.items():
    tb = tb.replace('@'+key+'@', str(value))
(D / 'tb.sv').write_text(tb)
manifest = {'scope': 'Source-exact selected reset-cone composition only; not full PHY, boot or publication proof.',
            'source_host_path': 'intel2:/srv/opentallas-scratch2/claude/codex-serdes-lec/replay1/kit/rtl',
            'source_sha256': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in S.glob('*.sv')},
            'core_path': path, 'relays': len(relays), 'observations': names, 'observation_clock': domains,
            'conditional_assumption': 'Both clk and pma_rck run at nominal833ps during reset; the stopped pma_rck test deliberately removes this unsupported guarantee.',
            'not_claimed': ['No soft module list extension or reset64 binding','No RTL/clock/mission-cycle change','No full boot/PHY correctness or FIFO corruption proof']}
(D / 'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
print('prepared',len(relays),'actual source relays;',len(names),'observations')
