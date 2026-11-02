#!/usr/bin/env python3
"""Build a minimum native SOURCE13 collar/r10 boundary phase vehicle.

Actual producer definitions/calls and capture cells are used unchanged. Unrelated
arithmetic, Hleaf and VM0 are outside this component; controller-fault input is
explicit. This does not qualify a physical reset route or full numerical mission.
"""
import argparse,importlib.util,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/hbm_static'),str(ROOT/'tools/hbm_layer_vehicle')]
import sfu_images as images
import prepare_programme_local_move as move


def decl(text,name):
    m=re.search(r'^\s*wire(?:\s+\[[^\]]+\])?\s+'+re.escape(name)+r'\s*;',text,re.M)
    if not m:raise ValueError('actual wire declaration missing '+name)
    return m[0]


def module(name,ports,body):return 'module '+name+' (\n'+',\n'.join('    '+p for p in ports)+'\n);\n'+body+'\nendmodule\n'


def prepare(region,inputs,generated):
    hub=(inputs/(move.HUBS[region]+'.sv')).read_text();bod=(inputs/(move.BODS[region]+'.sv')).read_text()
    nhub=(generated/(move.HUBS[region]+'.sv')).read_text();nbod=(generated/(move.BODS[region]+'.sv')).read_text()
    target=118 if region=='NW' else 119;rt='rst_n_t352'if region=='NW'else'rst_n_t350'
    cfgports=['input wire clk','input wire rst_n','input wire '+rt]
    cfgports += ['input wire '+('['+str(w-1)+':0] 'if w>1 else'[0:0] ')+x.split('[')[0] for _,w,x in move.FORWARD]
    statuses=['output wire [4:0] observed_status']
    # Original source-side component and actual local two-face sink.
    producer_decls=re.findall(r'^\s*wire\s+\[[^\]]+\]\s+(?:w_u_col_sfu_Q_\w+|w_u_sfup_Q_q1_\w+)\s*;',hub,re.M)
    faultdecls=[decl(hub,move.HFAULT+'_q'),decl(hub,move.HFAULT+'_eq')]
    oldcalls=[move.call(hub,n)[2]for n in ['u_u_col_sfu_Q','u_u_sfup_Q_q1','u_bin_'+move.HFAULT]+['u_bout_'+x for x in move.OUTS]]
    oldbody='\n'.join([f"localparam [7:0] S_u_col_sfu_Q_tgt=8'd{target};",*producer_decls,*faultdecls,*oldcalls,'assign observed_status = {'+', '.join(reversed(move.STATUS))+'};'])
    oldhub=module('phase_old_hub_'+region,cfgports+['input wire [1:0] '+move.HFAULT,'output wire [1742:0] '+move.OUTS[0],'output wire [471:0] '+move.OUTS[1]]+statuses,oldbody)
    bcapture=[decl(bod,n+s)for n in [move.CTRL,move.IO]for s in ['_q','_eq']]
    faultwire='w_u_sfucore_Q_ctl_u_core_procdff_66891_Q'
    faultbody='wire [0:0] '+faultwire+' = controller_fault;'
    bports=['input wire clk','input wire rst_n','input wire [0:0] controller_fault','output wire [1741:0] control_data','output wire control_epoch','output wire [470:0] io_data','output wire io_epoch']
    expose='\n'.join(['assign control_data = '+move.CTRL+'_q;','assign control_epoch = '+move.CTRL+'_eq;','assign io_data = '+move.IO+'_q;','assign io_epoch = '+move.IO+'_eq;'])
    oldb=module('phase_old_bod_'+region,bports+['input wire [1742:0] '+move.CTRL,'input wire [471:0] '+move.IO,'output wire [1:0] '+move.FAULT], '\n'.join([*bcapture,faultbody,*[move.call(bod,n)[2]for n in ['u_bin_'+move.CTRL,'u_bin_'+move.IO,'u_bout_'+move.FAULT]],expose]))
    # Exact appended event fragments: no independent reimplementation of new gates.
    bstart=nbod.index('    wire [1742:0] '+move.OUTS[0]+';');bfrag=nbod[bstart:nbod.rfind('endmodule')]
    newb=module('phase_new_bod_'+region,bports+['input wire [279:0] prog_move_ingress_i','output wire [5:0] prog_move_status_o','input wire [1:0] prog_move_resets_i'], '\n'.join([*bcapture,faultbody,*[move.call(nbod,n)[2]for n in ['u_bin_'+move.CTRL,'u_bin_'+move.IO,'u_bout_'+move.FAULT]],bfrag,expose]))
    hstart=nhub.index('    wire [4:0] prog_status_q;');hfrag=nhub[hstart:nhub.rfind('endmodule')]
    newhub=module('phase_new_hub_'+region,cfgports+['output wire [279:0] prog_move_ingress_o','input wire [5:0] prog_move_status_i','output wire [1:0] prog_move_resets_o']+statuses, '\n'.join([*[decl(hub,n)for n in move.STATUS],hfrag,'assign observed_status = {'+', '.join(reversed(move.STATUS))+'};']))
    header=['input wire clk','input wire rst_hub','input wire rst_programme','input wire rst_bod','input wire cfg_v','input wire [11:0] cfg_addr','input wire [255:0] cfg_data','input wire desc_v','input wire launch_v','input wire [0:0] controller_fault','input wire [2:0] mutant','output wire [1741:0] old_control,new_control','output wire old_control_epoch,new_control_epoch','output wire [470:0] old_io,new_io','output wire old_io_epoch,new_io_epoch','output wire [4:0] old_status,new_status','output wire [63:0] old_writes,new_writes,old_reads,new_reads','output wire warm']
    cfgmap=', '.join('.'+x.split('[')[0]+'('+{'cfg_v':'cfg_v','cfg_target':"8'd"+str(target),'cfg_addr':'cfg_addr','cfg_data':'cfg_data','desc_v':'desc_v','launch_v':'launch_v'}[n]+')'for n,w,x in move.FORWARD)
    cfgnew=', '.join('.'+x.split('[')[0]+'('+{'cfg_v':'cfg_v','cfg_target':f"(mutant[1]?8'd116:8'd{target})",'cfg_addr':'cfg_addr','cfg_data':'cfg_data','desc_v':'desc_v','launch_v':'launch_v'}[n]+')'for n,w,x in move.FORWARD)
    raw='{launch_v, desc_v, cfg_data, cfg_addr, '+f"(mutant[1]?8'd116:8'd{target})"+', cfg_v}'
    body=f'''wire [1742:0] old_control_bus; wire [471:0] old_io_bus; wire [1:0] old_fault_bus;
wire [279:0] ingress; wire [5:0] status; wire [1:0] reset_delivery;
reg [1:0] delayed_hub,delayed_programme;
always @(posedge clk)begin delayed_hub<={{delayed_hub[0],rst_hub}};delayed_programme<={{delayed_programme[0],rst_programme}};end
wire [279:0] actual_ingress=mutant[0]?{{rst_hub,{raw}}}:ingress;
wire [1:0] actual_resets=mutant[2]?{{delayed_programme[1],delayed_hub[1]}}:reset_delivery;
phase_old_hub_{region} old_hub(.clk(clk),.rst_n(rst_hub),.{rt}(rst_programme),{cfgmap},.{move.HFAULT}(old_fault_bus),.{move.OUTS[0]}(old_control_bus),.{move.OUTS[1]}(old_io_bus),.observed_status(old_status));
phase_old_bod_{region} old_bod(.clk(clk),.rst_n(rst_bod),.controller_fault(controller_fault),.{move.CTRL}(old_control_bus),.{move.IO}(old_io_bus),.{move.FAULT}(old_fault_bus),.control_data(old_control),.control_epoch(old_control_epoch),.io_data(old_io),.io_epoch(old_io_epoch));
phase_new_hub_{region} new_hub(.clk(clk),.rst_n(rst_hub),.{rt}(rst_programme),{cfgnew},.prog_move_ingress_o(ingress),.prog_move_status_i(status),.prog_move_resets_o(reset_delivery),.observed_status(new_status));
phase_new_bod_{region} new_bod(.clk(clk),.rst_n(rst_bod),.controller_fault(controller_fault),.prog_move_ingress_i(actual_ingress),.prog_move_status_o(status),.prog_move_resets_i(actual_resets),.control_data(new_control),.control_epoch(new_control_epoch),.io_data(new_io),.io_epoch(new_io_epoch));
integer ow[0:43],nw[0:43],orr[0:43],nr[0:43];
for(genvar l=0;l<11;l=l+1)begin:g_l
 for(genvar p=0;p<4;p=p+1)begin:g_p
  localparam integer K=l*4+p;
  initial begin ow[K]=0;nw[K]=0;orr[K]=0;nr[K]=0;end
  always @(posedge clk)begin
   if(old_hub.u_u_sfup_Q_q1.g_leaf[l].u_leaf.g_page[p].u_program.w_ce_in)ow[K]=ow[K]+1;
   if(new_bod.u_u_sfup_Q_q1.g_leaf[l].u_leaf.g_page[p].u_program.w_ce_in)nw[K]=nw[K]+1;
   if(old_hub.u_u_sfup_Q_q1.g_leaf[l].u_leaf.g_page[p].u_program.r_ce_in)orr[K]=orr[K]+1;
   if(new_bod.u_u_sfup_Q_q1.g_leaf[l].u_leaf.g_page[p].u_program.r_ce_in)nr[K]=nr[K]+1;
  end
 end
end
reg [63:0] sw0,sw1,sr0,sr1;
always @*begin sw0=0;sw1=0;sr0=0;sr1=0;for(integer k=0;k<44;k=k+1)begin sw0=sw0+ow[k];sw1=sw1+nw[k];sr0=sr0+orr[k];sr1=sr1+nr[k];end end
assign old_writes=sw0;assign new_writes=sw1;assign old_reads=sr0;assign new_reads=sr1;
assign warm=(&old_hub.u_u_sfup_Q_q1.rb)&&old_hub.u_u_sfup_Q_q1.rbd1&&(&new_bod.u_u_sfup_Q_q1.rb)&&new_bod.u_u_sfup_Q_q1.rbd1&&old_hub.u_u_col_sfu_Q.rst_c_n&&new_bod.u_u_col_sfu_Q.rst_c_n;
'''
    return '\n'.join([oldhub,oldb,newhub,newb,module('phase_pair_'+region,header,body)])


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--event-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    event=json.loads((a.event_dir/'event.json').read_text())
    if (event['prototype_ingress_stages'],event['prototype_status_stages'],event['new_ingress_payload_bits'])!=(2,2,279):raise ValueError('this minimum phase vehicle qualifies only the actual direct-reset2/2 event; top relays are outside this vehicle')
    for row in event['source_inputs']:
        source=a.source_dir/(row['module']+'.sv')
        if __import__('hashlib').sha256(source.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('actual event/input source mismatch '+row['module'])
    a.out.mkdir(parents=True,exist_ok=True)
    text='\n'.join(prepare(region,a.source_dir,a.event_dir)for region in ['NW','NE']);(a.out/'phase_units.sv').write_text(text)
    ctl=[1,1<<511,1<<1022,1<<1741];io=[images.pack_io({'arithmetic_start':1,'scalar_enable':1}),images.pack_io({'drain_v':1,'drain_addr':37})]
    frames,need=images.collar_install(images.ctl_planes(ctl),images.io_planes(io));prm=images.prm_row(0,len(ctl),0,len(io))
    (a.out/'frames.mem').write_text(''.join(f'{(addr<<256)|value:067x}\n'for addr,value in frames));(a.out/'ctl.mem').write_text(images.hex_rows(ctl,1742));(a.out/'io.mem').write_text(images.hex_rows(io,471))
    (a.out/'fixture.json').write_text(json.dumps(dict(scope='Native programme FORMAT/PHASE component, no arithmetic/globalVM0/COPY/currentphysical qualification',regions=['NWtarget118reset352','NEtarget119reset350'],native_producer_copies=4,native_SRAMs=176,raw_SRAM_bits=176*512*256,declared_programme_soft_FF=4*22922,controller_fault_input='Explicit boundary input held0 in data-phase vehicle; independent-controller-fault global semantics remain unqualified',ingress_stages=2,status_stages=2,frames=len(frames),need=need,prm=hex(prm),ctl_rows=4,io_rows=2,clock_fs=833000,reset_test='66edge delivered-interface reset; not actual whole-parent R8/66 qualification',tests=['fullnative residentinstall and descriptor/launch ordering','warmrelaunch with no SRAMrewrite','resetduringinflight CFG, reject assumptions of retainedcommit, fullreinstallrecovery'],mutants=['sourcecapturebypass earlydelivery','wronglegacytarget116','c09 reset-as-datalosesasyncassertion']),indent=2)+'\n')
    (a.out/'fixture.vh').write_text(f'localparam integer NF={len(frames)};\nlocalparam [255:0] PRM=256\'h{prm:064x};\n')

if __name__=='__main__':main()
