"""Source-preserving, composable ROM ingress transform of existing owned adapter seats."""
import argparse,pathlib,re,json,hashlib

def transform(src):
 def once(old,new):
  nonlocal src
  assert src.count(old)==1,(old,src.count(old));src=src.replace(old,new)
 src,n=re.subn(r'module\s+ot_qwen_\w+\s*#\(', 'module ot_qwen_rom_vm_ingress_adapter #(',src,count=1);assert n==1
 once('parameter integer ENABLE=0,','parameter integer ENABLE=0,\n    parameter integer ROM_INGRESS=0,')
 once('parameter integer NW=1633,','parameter integer NW=(ROM_INGRESS ? 865 : 1633),')
 once('parameter integer VX0=192,','parameter integer VX0=(ROM_INGRESS ? 208 : 192),')
 once('input wire [NR-1:0] read_en,','input wire [NR-1:0] raw_read_en,\n    input wire [NR-1:0] raw_read_zero,')
 once('input wire [NW-1:0] write_en,','input wire [NW-1:0] raw_write_en,')
 once('    import ot_gpu_w6_secded_pkg::*;', '''    import ot_gpu_w6_secded_pkg::*;
    // Raw intents exclude the admission lease: no request/grant circularity.
    wire [NR-1:0] read_en, zero_intent;
    wire [NW-1:0] write_en;
    genvar ingress;
    generate for(ingress=0;ingress<NR;ingress=ingress+1)begin:g_ingress_r
        wire me_seat=(ingress>=VX0 && ingress<VX0+NVX);
        assign read_en[ingress]=raw_read_en[ingress] && (!ROM_INGRESS || !me_seat || source_me_wanted);
        assign zero_intent[ingress]=ROM_INGRESS && raw_read_zero[ingress] && (!me_seat || source_me_wanted);
    end
    for(ingress=0;ingress<NW;ingress=ingress+1)begin:g_ingress_w
        assign write_en[ingress]=raw_write_en[ingress] && (!ROM_INGRESS || ingress>=784 || source_me_wanted);
    end endgenerate
    initial if(ROM_INGRESS && (NR!=2256 || NW!=865 || VX0!=208 || NVX!=2048 || HEAD_CACHE || W1_FRAME))
        $fatal(1,"ROM ingress candidate unsupported source geometry/fast path");''')
 once('wire [NR-1:0] ren,read_ue;','wire [NR-1:0] ren,read_ue,read_zero;')
 once('assign read_ue[seat]=decoded[65];assign ren[seat]=decoded[56];','assign read_ue[seat]=decoded[65];assign ren[seat]=decoded[56];\n        assign read_zero[seat]=ROM_INGRESS && decoded[57];')
 once('wire fast_empty=(state==CAP) && !(|read_en) && !(|write_en);','wire fast_empty=(state==CAP) && !(|read_en) && !(|zero_intent) && !(|write_en);')
 once("read_seat[k]<=encode64({7'b0,read_en[k],read_addr[k*24+:24],32'b0});", "read_seat[k]<=encode64({6'b0,zero_intent[k],read_en[k],read_addr[k*24+:24],32'b0});")
 once('if(ren[k])read_q[k*32+:32]<=raw[k*32+:32];', "if(ren[k] || read_zero[k])read_q[k*32+:32]<=read_zero[k] ? 32'b0 : raw[k*32+:32];")
 once('xpipe[k*32+:32]<=raw[(VX0+k)*32+:32];', "xpipe[k*32+:32]<=read_zero[VX0+k] ? 32'b0 : raw[(VX0+k)*32+:32];")
 once('xpipe_en<=ren[VX0+:NVX];','xpipe_en<=ren[VX0+:NVX] | read_zero[VX0+:NVX];')
 return src

def main():
 p=argparse.ArgumentParser();p.add_argument('--adapter-source',type=pathlib.Path,default=pathlib.Path('/home/ubuntu/OpenTallas/rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_finite_vm_adapter.sv'));p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-rom-ingress-20261007/generated'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 src=a.adapter_source.read_text();out=transform(src);(a.out/'ot_qwen_rom_vm_ingress_adapter.sv').write_text(out)
 (a.out/'manifest.json').write_text(json.dumps(dict(source=str(a.adapter_source),source_sha256=hashlib.sha256(src.encode()).hexdigest(),output_sha256=hashlib.sha256(out.encode()).hexdigest(),new_register_declarations=False,scope='Candidate existing-seat ingress transform; ROM bounds normalization external; native clocks and full backing extent unbound. ROM_INGRESS default0. Combined source transform is not a tested physical or whole-ROM join.'),indent=2)+'\n')
if __name__=='__main__':main()
