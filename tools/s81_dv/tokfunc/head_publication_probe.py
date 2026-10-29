#!/usr/bin/env python3
"""Real 80-VQ/16-ring-stop HEAD publication on retained source transport.

Inputs are the released HEAD normalized BF16 vector and previously measured
16-XFIN RSTD dates relative to an explicit source-book origin. VN arithmetic
is a golden boundary here; the native37 feedback probe qualifies that path
separately. No physical START or source-plan adoption is inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def delay(name, width, age, src, dst):
    if type(age) is not int or age < 0:
        raise ValueError('exact nonnegative source delay required')
    if age == 0:
        return f'assign {dst}={src};\n'
    return (f'ot_hdc_delay #(.W({width}),.D({age}),.RESET(1)) {name}'
            f'(.clk(clk),.rst_n(rst_n),.d({src}),.q({dst}));\n')


def publication_closure(network):
    """NX-only endpoint extraction may omit real middle-column V bodies."""
    rows = {(r['sid'], r['port']): r for r in network['transport']['nx_boundary']}
    missing = []
    for north_sid in range(1, 16, 2):
        row = rows.get((north_sid, 'vi'), {})
        if row.get('status') != 'PASS' or row.get('from_sid') != north_sid-1 or row.get('from_port') != 'vo':
            missing.append(dict(source_sid=north_sid-1, destination_sid=north_sid,
                destination_port='vi', actual_driver=row.get('driver'),
                actual_driver_ports=row.get('drv_ports'), last_bound_age_edges=row.get('age_edges'),
                missing_global_beats=list(range(5*(north_sid-1), 5*(north_sid-1)+5))))
    return missing


def generate(root, network, returns, dates, slots, qdelays):
    missing = publication_closure(network)
    if missing:
        raise ValueError('HEAD80 publication transport is incomplete: actual non-ring-stop V bodies required; '
                         + json.dumps(missing, sort_keys=True))
    if len(slots) != 5 or sorted(slots) != list(range(5)) or len(qdelays) != 16 or any(not 0 <= v < 256 for v in qdelays):
        raise ValueError('existing five slots and sixteen8bit release delays required')
    for d in (network, returns):
        for key in ('die_sha256', 'source_asbuilt_sha256'):
            if d[key] != dates[key]:
                raise ValueError('one exact selected source graph required')
    rs = {int(k): v for k, v in dates['slice_rstd_edges'].items()}
    if set(rs) != set(range(16)) or dates['physical_START_qualified']:
        raise ValueError('retained16component relative dates required')
    leaves = {(r['slice'], r['leaf']): r for r in returns['leaves']}
    forwards = {(r['slice'], r['leaf']): r for r in network['transport']['xf_forward']}
    sid = {r['slice']: r['sid'] for r in network['transport']['nx_boundary']}
    qword = sum(v << (8*k) for k, v in enumerate(qdelays))
    code = '''`timescale 1ns/100fs
module tb_head_publication;
reg clk=0; always #0.4165 clk=~clk;
integer cyc=0,mut=0; reg rst_n=0;
reg[15:0]gold[0:5119];reg[79:0]seen=0;integer received=0,errors=0,dup=0;
initial begin $readmemh("gold.mem",gold);if($value$plusargs("MUT=%d",mut))begin end end
always@(posedge clk)begin cyc<=cyc+1;if(cyc==10)rst_n<=1;end
wire[1103:0]ri_w[0:15],ri_e[0:15],ro_w[0:15],ro_e[0:15];
wire[275:0]vi[0:15],vo[0:15];wire[4:0]xv[0:15],xs[0:15];wire[1379:0]xd[0:15];
wire[15:0]stop_fault,qrel_fault;wire[79:0]vq_fault;
wire[15:0]released;
integer idx,j;
always@(posedge clk)begin
 if(ro_w[1][0]&&ro_w[1][3:1]==3'd2&&ro_w[1][20])begin
  idx=int'(ro_w[1][19:13]);received=received+1;
  $display("PUB beat%0d edge%0d",idx,cyc);
  if(idx>=80)errors=errors+1;else begin
   if(seen[idx])begin dup=dup+1;errors=errors+1;end seen[idx]=1;
   for(j=0;j<64;j=j+1)if(ro_w[1][21+16*j+:16]!==gold[64*idx+j])errors=errors+1;
  end
 end
 if(cyc==2300)begin
  $display("HEAD_PUBLICATION received%0d unique%0d errors%0d duplicates%0d stopfault%h vqfault%h qrelfault%h",received,$countones(seen),errors,dup,stop_fault,vq_fault,qrel_fault);
  if(received==80&&seen=={80{1'b1}}&&errors==0&&stop_fault==0&&vq_fault==0&&qrel_fault==0)$display("PASS");
  else $fatal(1,"HEAD_PUBLICATION FAIL");$finish;
 end
end
'''
    files = set()
    for sl, number in sorted(sid.items(), key=lambda x: x[1]):
        xr = next(r for r in network['xr_xfin'] if r['slice'] == sl)
        source = (root/'rtl/dsrom_sys/s81_dv/slice'/f'{xr["xg_master"]}.sv').read_text()
        stops = re.findall(r'\b(ot_s81sl_(?:rstop|rstopt)(?:_xo)?)\s+u_r\s*\(', source)
        if len(stops) != 1:
            raise ValueError('one actual source ring-stop required')
        stop = stops[0]; files.add('rtl/dsrom_sys/s81_dv/slice/'+stop+'.sv')
        code += f'''ot_s81sl_rstd_release #(.DELAYS(128'd{qword})) rel{number}(.clk(clk),.rst_n(rst_n),.sid(4'd{number}),
.i_v(cyc=={rs[number]}),.i_d(32'h3f800000),.o_v(released[{number}]),.o_d(),.fault(qrel_fault[{number}]));
{stop} st{number}(.clk(clk),.rst_n(rst_n),.sid(4'd{number}),.ri_w(ri_w[{number}]),.ri_e(ri_e[{number}]),.ro_w(ro_w[{number}]),.ro_e(ro_e[{number}]),.vi(vi[{number}]),.vo(vo[{number}]),
.xf_v(xv[{number}]),.xf_s(xs[{number}]),.xf(xd[{number}]),.nx_wi(),.nx_ei(),.nx_eo(173'd0),.nx_wo(173'd0),
.g_v(),.g_fam(),.g_idx(),.g_d(),.dl_ev(),.dl_e(),.dl_wv(),.dl_w(),.dl_vv(),.dl_vb(),.ci_dir(3'd0),.ci_b(1104'd0),.fault(stop_fault[{number}]));
'''
        for k in range(5):
            index = 5*number+k
            ret = leaves[sl, k]; fwd = forwards[sl, k]
            if ret['status'] != 'PASS' or fwd['status'] != 'PASS':
                raise ValueError('unqualified VQ source transport')
            code += f'wire[7:0]yv{index};wire[127:0]yd{index}[0:8];wire[2:0]yi{index}[0:8];assign yd{index}[0]=0;assign yi{index}[0]=0;\n'
            for part in range(8):
                # XR returned-rstd input/output2 + source-qualified native VN
                # first y18; the exact selected leaf broadcast delay follows.
                code += delay(f'yp{index}_{part}', 1, 20+ret['rb_broadcast_edges']+part,
                              f'released[{number}]', f'yv{index}[{part}]')
                vals = ','.join(f'gold[{index*64+part*8+lane}]' for lane in reversed(range(8)))
                if index == 37 and part == 0:
                    vals = f'({{{vals}}}^((mut==1)?128\'d1:128\'d0))'
                else:
                    vals = '{'+vals+'}'
                code += f'assign yd{index}[{part+1}]=yd{index}[{part}]|({{128{{yv{index}[{part}]}}}}&{vals});assign yi{index}[{part+1}]=yi{index}[{part}]|(yv{index}[{part}]?3\'d{part}:3\'d0);\n'
            code += f'''wire fv{index},fs{index};wire[275:0]fd{index};wire[277:0]fr{index};
ot_s81sl_vq #(.AQ_XMEM(2)) vq{index}(.clk(clk),.rst_n(rst_n),.y_v(|yv{index}),.y_i(yi{index}[8]),.y(yd{index}[8]),.u_v(1'b0),.u_i(3'd0),.u(256'd0),.sid(4'd{number}),.k(3'd{slots[k]}),
.m_v(cyc==1000),.m_q(1'b0),.m_b(1'b1),.m_i(8'd{128+index}+((mut==2&&{index}==0)?8'd1:8'd0)),.um_v(1'b0),.um_q(1'b0),.um_b(1'b0),.um_i(8'd0),.xf_v(fv{index}),.xf_s(fs{index}),.xf(fd{index}),.fault(vq_fault[{index}]));
'''
            code += delay(f'fw{index}', 278, fwd['xf_forward_edges'], f'{{fv{index},fs{index},fd{index}}}', f'fr{index}')
            code += f'assign xv[{number}][{k}]=fr{index}[277];assign xs[{number}][{k}]=fr{index}[276];assign xd[{number}][{276*k}+:276]=fr{index}[275:0];\n'
    for index, r in enumerate(network['transport']['nx_boundary']):
        width = 276 if r['port'] == 'vi' else 1104
        target = f'{r["port"]}[{r["sid"]}]'
        if r['status'] == 'PASS':
            code += delay('link'+str(index), width, r['age_edges'], f'{r["from_port"]}[{r["from_sid"]}]', target)
        elif r['status'] in ('EDGE_EXTERNAL', 'EDGE_CONSTANT'):
            code += f"assign {target}={width}'d0;\n"
        else:
            raise ValueError('unqualified source ring boundary')
    return code+'endmodule\n', files


def run(a):
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    root = a.root.resolve()
    network = json.loads(a.network.read_text()); returns = json.loads(a.returns.read_text()); dates = json.loads(a.dates.read_text())
    slots = [int(v) for v in a.slots.split(',')]; qdelays = [int(v) for v in a.qdelays.split(',')]
    gold = []
    for f in (a.xa, a.xb):
        for word in f.read_text().split():
            w = int(word, 16); gold.extend((w >> (16*k)) & 65535 for k in range(16))
    if len(gold) != 5120:
        raise ValueError('actual released HEAD normalized5120BF16 required')
    (out/'gold.mem').write_text(''.join(f'{v:04x}\n' for v in gold))
    tb, extra = generate(root, network, returns, dates, slots, qdelays)
    (out/'tb.sv').write_text(tb)
    files = (root/'physical/hbm_norm_split_20261008/sources.f').read_text().split()
    files += ['rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv',
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v', *extra]
    files = list(dict.fromkeys(files))
    record = dict(scope='80_NATIVE_VQ_16_ACTUAL_RINGSTOP_SOURCE_PUBLICATION_ONLY',
        golden_input='actual released5120BF16HEADnorm; native37subset compared separately',
        dates='retained16XFIN relative component output dates, no physicalSTART',slots=slots,qdelays=qdelays,
        source_hashes={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},
        all80_arithmetic_qualified=False,physical_START_qualified=False,adoption=False,full_token=False)
    (out/'inputs.json').write_text(json.dumps(record,indent=1)+'\n')
    cmd=['verilator','--binary','--timing','-O1','--build-jobs','4','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
        '--top-module','tb_head_publication','-Mdir',str(out/'obj'),'--output-split','5000','--output-split-cfuncs','500',
        '-MAKEFLAGS','OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0',*[str(root/f) for f in files],str(out/'tb.sv')]
    with (out/'build.log').open('w') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'run.log').open('w') as f:
        result=subprocess.run([str(out/'obj/Vtb_head_publication'),'+MUT=0'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
    print((out/'run.log').read_text()); raise SystemExit(result.returncode)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('network','returns','dates','xa','xb','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--slots',default='0,1,2,3,4')
    p.add_argument('--qdelays',default=','.join(['0']*16));run(p.parse_args())
