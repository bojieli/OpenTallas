#!/usr/bin/env python3
"""Actual16XR/16ring-stops/16XFIN plus one native HEAD producer leaf.

Uses exact current bound transport ages, source XR parameters and the emitted
one-command/engine/cycle booking. The other79partial values are explicit
fixture boundary inputs timed by that static booking. No physical START or
regional-clock phase is inferred. Candidate PDSK is confined to this bench.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from head_norm_loop import generate_tb,replace_once
from head_norm_booking import encoded,literal
ROOT=Path(__file__).resolve().parents[3]


def delay(name,width,age,source,target):
    if type(age)is not int or age<0:raise ValueError('exact nonnegative bound age required')
    if age==0:return f'assign {target}={source};\n'
    return f'ot_hdc_delay #(.W({width}),.D({age}),.RESET(1)) {name}(.clk(clk),.rst_n(rst_n),.d({source}),.q({target}));\n'


def command_rows(booking,control,entry,origin,local_partial=116):
    # Also retain the old source programme as an immutable expected-failure
    # vehicle. It has the SAME98commands, only the legacy consecutive dates.
    sid={g['slice']:g['sid']for g in booking['groups']}
    old=[]
    for tier in ('N','S'):
        mask=sum(1<<s for sl,s in sid.items()if sl.endswith(tier))
        old.append(dict(engine='V'+tier,issue_vo_edge=origin,slice_mask=mask,target=0,leaf_mask=31,body=1|(480<<4),kind='GAIN'))
        t=origin+20
        for sl in sorted((s for s in sid if s.endswith(tier)),key=sid.get):
            for k in range(5):
                old.append(dict(engine='V'+tier,issue_vo_edge=t,slice_mask=1<<sid[sl],target=0,leaf_mask=1<<k,
                    body=7|(1008<<4)|((128+5*sid[sl]+k)<<14)|(2<<24),kind='NORMR',slice=sl,leaf=k))
                t+=1
            old.append(dict(engine='V'+tier,issue_vo_edge=t,slice_mask=1<<sid[sl],target=1,leaf_mask=0,body=booking['eps_bits'],kind='XFIN_GO',slice=sl));t+=1
    ent={(x['slice'],x['leaf']):x for x in entry['leaves']}
    out=[]
    for rows in (old,booking['rows']):
        seen=set();emits=[None]*80;words=[]
        for row in rows:
            key=(row['engine'],row['issue_vo_edge'])
            if key in seen:raise ValueError('unsupported multiissue')
            seen.add(key)
            payload=row['slice_mask']|(row['target']<<16)|(row['leaf_mask']<<21)|(row['body']<<26)
            words.append(payload|(row['issue_vo_edge']<<186)|(int(row['engine']=='VN')<<210))
            if row['kind']=='NORMR':
                sl,k=row['slice'],row['leaf'];index=5*sid[sl]+k
                emits[index]=row['issue_vo_edge']+control['paths'][sl]['xr_command_pin_edge']+ent[(sl,k)]['command_transport_edges']+local_partial
        if any(x is None for x in emits)or len(words)!=98:raise ValueError('complete98commands/80partial dates required')
        out.append((words,emits))
    return out


def network_tb(source,root,network,entry,returns,booking,control,beat):
    s=generate_tb(source)
    # Same production leaf-store addresses as lower_head, with explicit boot
    # preload. Move boot HLOAD/GAIN after the expanded1024row fixture writes.
    s=s.replace('R_GA = 0, R_GF = 16, R_CA = 32','R_GA = 480, R_GF = 16, R_CA = 1008')
    s=s.replace('img [0:159]','img [0:1023]').replace('reg [159:0] wr_ok','reg [1023:0] wr_ok')
    s=s.replace('r < 160','r < 1024').replace('cyc < 90','cyc < 522').replace('cyc == 180','cyc == 600').replace('cyc == 220 + 400 * blk','cyc == 650 + 400 * blk')
    a=s.index('        if (cyc == 240 + 400 * blk');b=s.index('        if (p_v) begin',a)
    s=s[:a]+'''        if (leaf_cv && leaf_cd[3:0]==4'd7) t_go=cyc;
'''+s[b:]
    s=replace_once(s,'.c_v(c_v), .c_d(c_d),','.c_v(leaf_cv), .c_d(leaf_cd),')
    s=s.replace("reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0, rb_v = 1'b0;", "reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0; wire rb_v;")
    s=s.replace("reg [31:0] rb_d = 0;",'wire [31:0] rb_d;')
    s=s.replace('if (cyc == 1200) begin','if (cyc == 4500) begin')
    sid={r['slice']:r['sid']for r in network['transport']['nx_boundary']}
    xr={r['slice']:r for r in network['xr_xfin']}
    ent={(r['slice'],r['leaf']):r for r in entry['leaves']}
    ret={(r['slice'],r['leaf']):r for r in returns['leaves']}
    leafsl=next(sl for sl,number in sid.items()if number==beat//5);leafk=beat%5
    # Actual captured source has no extra intra-leaf normalizer stations and
    # identical A/B rstd broadcast ages. Do not silently use this probe otherwise.
    for row in network['leaves']:
        if row['status']!='PASS_SOURCE_NORM_TRANSPORT':raise ValueError('unqualified norm source')
        if any(v for k,v in row['edges'].items()if not k.startswith('xr.rb')):
            raise ValueError('nonzero intra-leaf age requires explicit physical leaf adaptation')
        if len({v for k,v in row['edges'].items()if k.startswith('xr.rb')})!=1:raise ValueError('A/B rstd source phases differ')
    code='''    reg[31:0] partials[0:79],eps_mem[0:0];reg[210:0]cmds[0:97];reg[23:0]emit_edges[0:79];
    integer mode=1,mut=0;reg[31:0]actual_partial=0;reg actual_seen=0;
    initial begin
      if($value$plusargs("MODE=%d",mode))begin end
      if($value$plusargs("MUT=%d",mut))begin end
      $readmemh("partials.mem",partials);$readmemh("a_eps.mem",eps_mem);
      if(mode==0)begin $readmemh("commands0.mem",cmds);$readmemh("emits0.mem",emit_edges);end
      else begin $readmemh("commands1.mem",cmds);$readmemh("emits1.mem",emit_edges);end
    end
    wire[15:0]xrb_v,xflt,xfault,rfault,xrfault,oldfault,newfault;
    wire[31:0]xrb_d[0:15];wire[172:0]xeo[0:15],xwo[0:15],xwi[0:15],xei[0:15];
    wire[1103:0]ri_w[0:15],ri_e[0:15],ro_w[0:15],ro_e[0:15];wire[275:0]vi[0:15],vo[0:15];
    wire[172:0]rwi[0:15],rei[0:15],reo[0:15],rwo[0:15];
    wire[4:0]xf_valid[0:15],xf_start[0:15];wire[1379:0]xf_data[0:15];
    wire[4:0]xcv[0:15],opv[0:15];wire[159:0]xcd[0:15],opd[0:15];
    wire[4:0]npv[0:15];wire[159:0]npd[0:15];
    wire[4:0]pv_net[0:15];wire[159:0]pd_net[0:15];
    wire[31:0]xr_rbd[0:15];wire[15:0]xr_rbv;
    wire[74:0]nc[0:15],oc[0:15];
    integer nr=0,rerr=0,first_rb=-1,last_rb=-1,rr,egress_n=0;
    assign xrfault=(mode==0)?oldfault:newfault;
    assign xflt=xfault|rfault|xrfault;
    always@(posedge clk)begin
      if(p_v)begin actual_partial<=p_d;actual_seen<=1;end
      for(rr=0;rr<16;rr=rr+1)if(xrb_v[rr])begin
        nr=nr+1;if(first_rb<0)first_rb=cyc;last_rb=cyc;
        if(xrb_d[rr]!==rstd[0])begin rerr=rerr+1;$display("real xfin rstd mismatch slice%0d got%h want%h",rr,xrb_d[rr],rstd[0]);end
      end
      if(cyc>900 && mode==0 && (|xrfault))begin
        $display("BASELINE_HEAD_NORM FAIL actual_XR_partial_set_misaligned faults%h",xrfault);$finish;
      end
      if(cyc>900 && mode!=0 && (|xrfault))$fatal(1,"candidate actual XR fault %h",xrfault);
      if(ro_w[1][0]&&ro_w[1][3:1]==3'd2&&ro_w[1][20])begin
        egress_n=egress_n+1;
        if(ro_w[1][19:13]!==7'(BEAT))$fatal(1,"actual producer HEAD index differs");
        for(integer lane=0;lane<64;lane=lane+1)
          if(ro_w[1][21+16*lane+:16]!==ey[lane][31:16])$fatal(1,"actual producer HEAD data differs lane%0d",lane);
        $display("ACTUAL_HEAD_PUBLICATION beat%0d edge%0d payload%h",BEAT,cyc,ro_w[1][1044:21]);
      end
      if(cyc==4499 && mode==0)$fatal(1,"baseline source failure was not exposed");
      if(cyc==4499 && mode!=0 && egress_n!=1)$fatal(1,"actual HEAD publication missing/duplicated count%0d",egress_n);
    end
'''
    for sl,num in sorted(sid.items(),key=lambda x:x[1]):
        route=control['paths'][sl];entryport=route['entry_port']
        if entryport not in('ri_w','ri_e','vi'):raise ValueError('unknown actual controller entry face')
        x=xr[sl];master=x['xr_master'];params=dict(x['xr_params'])
        if master not in('ot_s81sl_xrt1','ot_s81sl_xrt3'):raise ValueError('unsupported actual XR source')
        for value in params.values():literal(value)
        xg_source=root/'rtl/dsrom_sys/s81_dv/slice'/f'{x["xg_master"]}.sv'
        stop=re.findall(r'\b(ot_s81sl_(?:rstop|rstopt)(?:_xo)?)\s+u_r\s*\(',xg_source.read_text())
        if len(stop)!=1:raise ValueError('one actual source ring-stop child required')
        code+=f'wire[185:0]pay{num};reg[185:0]payr{num};reg dlv{num};integer j{num};assign pay{num}=payr{num};\n'
        tier=int(sl.endswith('N'))
        code+=f'''always@*begin payr{num}=0;dlv{num}=0;
          for(j{num}=0;j{num}<98;j{num}=j{num}+1)if(cmds[j{num}][210]==1'b{tier} && cyc==int'(cmds[j{num}][209:186])+{route['xr_input_edge']}+1)begin
            payr{num}=cmds[j{num}][185:0];dlv{num}=1;end end
wire[1103:0]ctl{num}=(1104'(pay{num})<<21)|1104'd1;
'''
        for k in range(5):
            index=5*num+k;age=ret[(sl,k)]['partial_return_edges']
            src=f'p_v'if index==beat else f'(cyc==int\'(emit_edges[{index}])+1+((mut==1&&{index}==3)?1:0))'
            data='p_d'if index==beat else f'partials[{index}]'
            if index==beat:data=f'({data}^((mut==2)?32\'h00800000:32\'d0))'
            code+=f'wire[32:0]pp{index};\n'+delay(f'pr{index}',33,age,'{'+src+','+data+'}',f'pp{index}')
            code+=f'assign pv_net[{num}][{k}]=pp{index}[32];assign pd_net[{num}][{32*k}+:32]=pp{index}[31:0];\n'
        # Two existing-width parameter variants; only the selected candidate
        # drives the norm network, and the default master is never edited.
        for which in('old','new'):
            pa=dict(params)
            if which=='new':pa['PDSK']=booking['pdsk_parameter']
            paramtext=','.join('.'+k+'('+str(v)+')'for k,v in pa.items())
            pfx=f'{which}{num}'
            code+=f'wire {pfx}go,{pfx}md,{pfx}sv,{pfx}rbv;wire[31:0]{pfx}eps,{pfx}scale,{pfx}s,{pfx}rbd;wire[6:0]{pfx}si;\n'
            dv=[f'dlv{num}'if entryport==face else "1'b0"for face in('ri_w','ri_e','vi')]
            db=[f'ctl{num}[1075:1]'if entryport==face else "1075'd0"for face in('ri_w','ri_e')]
            vb=f'ctl{num}[275:1]'if entryport=='vi'else"275'd0"
            cv=f'opv[{num}]'if which=='old'else f'npv[{num}]';cd=f'opd[{num}]'if which=='old'else f'npd[{num}]'
            ports=f'''.clk(clk),.rst_n(rst_n),.sid(4'd{num}),.dl_ev({dv[0]}),.dl_e({db[0]}),.dl_wv({dv[1]}),.dl_w({db[1]}),.dl_vv({dv[2]}),.dl_vb({vb}),
.c_v({cv}),.c_d({cd}),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_net[{num}]),.p_d(pd_net[{num}]),
.rb_v({pfx}rbv),.rb_d({pfx}rbd),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),
.x_go({pfx}go),.x_mode({pfx}md),.x_eps({pfx}eps),.x_scale({pfx}scale),.x_sv({pfx}sv),.x_si({pfx}si),.x_s({pfx}s),.x_rbv(xrb_v[{num}]),.x_rbd(xrb_d[{num}]),
.is_v(),.is_d(),.cfg_v(),.cfg_d(),.ci_dir(),.ci_b(),.fault({which}fault[{num}])'''
            if master.endswith('3'):ports+=",.bi(1046'd0),.bo()"
            code+=f'{master} #({paramtext}) {pfx}({ports});\n'
        code+=f'''assign xcv[{num}]=(mode==0)?opv[{num}]:npv[{num}];assign xcd[{num}]=(mode==0)?opd[{num}]:npd[{num}];
assign xr_rbv[{num}]=(mode==0)?old{num}rbv:new{num}rbv;assign xr_rbd[{num}]=(mode==0)?old{num}rbd:new{num}rbd;
'''
        srcs={f: f'((mode==0)?old{num}{suffix}:new{num}{suffix})'for f,suffix in [('go','go'),('mode','md'),('eps','eps'),('s_v','sv'),('s_i','si'),('s','s')]}
        widths={'go':1,'mode':1,'eps':32,'s_v':1,'s_i':7,'s':32}
        for field,width in widths.items():
            code+=f'wire[{width-1}:0]xi_{field}{num};\n'+delay(f'ct_{field}{num}',width,x['edges'][field],srcs[field],f'xi_{field}{num}')
        code+=f'''ot_s81dv_xfin xf{num}(.clk(clk),.rst_n(rst_n),.sid(4'd{num}),.go(xi_go{num}),.mode(xi_mode{num}),.eps(xi_eps{num}),.s_v(xi_s_v{num}),.s_i(xi_s_i{num}),.s(xi_s{num}),
.wi_v(xwi[{num}][172]),.wi_h(xwi[{num}][171:168]),.wi_b(xwi[{num}][167:160]),.wi_d(xwi[{num}][159:0]),
.ei_v(xei[{num}][172]),.ei_h(xei[{num}][171:168]),.ei_b(xei[{num}][167:160]),.ei_d(xei[{num}][159:0]),
.eo_v(xeo[{num}][172]),.eo_h(xeo[{num}][171:168]),.eo_b(xeo[{num}][167:160]),.eo_d(xeo[{num}][159:0]),
.wo_v(xwo[{num}][172]),.wo_h(xwo[{num}][171:168]),.wo_b(xwo[{num}][167:160]),.wo_d(xwo[{num}][159:0]),
.rb_v(xrb_v[{num}]),.rb_d(xrb_d[{num}]),.e_v(),.e_c(),.e_hh(),.e_kk(),.e_dd(),.fault(xfault[{num}]));
{stop[0]} rs{num}(.clk(clk),.rst_n(rst_n),.sid(4'd{num}),.ri_w(ri_w[{num}]),.ri_e(ri_e[{num}]),.ro_w(ro_w[{num}]),.ro_e(ro_e[{num}]),.vi(vi[{num}]),.vo(vo[{num}]),
.xf_v(xf_valid[{num}]),.xf_s(xf_start[{num}]),.xf(xf_data[{num}]),.nx_wi(rwi[{num}]),.nx_ei(rei[{num}]),.nx_eo(reo[{num}]),.nx_wo(rwo[{num}]),
.g_v(),.g_fam(),.g_idx(),.g_d(),.dl_ev(),.dl_e(),.dl_wv(),.dl_w(),.dl_vv(),.dl_vb(),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[{num}]));
'''
        ep=next(z for z in network['transport']['xfin_endpoints']if z['slice']==sl)['edges']
        for tag,age,ins,outs in [('nwi',ep['nx_wi->wi'],f'rwi[{num}]',f'xwi[{num}]'),('nei',ep['nx_ei->ei'],f'rei[{num}]',f'xei[{num}]'),
            ('neo',ep['eo->nx_eo'],f'xeo[{num}]',f'reo[{num}]'),('nwo',ep['wo->nx_wo'],f'xwo[{num}]',f'rwo[{num}]')]:
            code+=delay(tag+str(num),173,age,ins,outs)
        if ep['rb->x_rb']!=0:raise ValueError('nonzero XFINreturn endpoint requires explicitadapter')
        if num!=beat//5:code+=f"assign xf_valid[{num}]=0;assign xf_start[{num}]=0;assign xf_data[{num}]=0;\n"
    for index,row in enumerate(network['transport']['nx_boundary']):
        num=row['sid'];port=row['port'];width=276 if port=='vi'else 1104
        if row['status']=='PASS':
            code+=delay('hop'+str(index),width,row['age_edges'],f'{row["from_port"]}[{row["from_sid"]}]',f'{port}[{num}]')
        elif row['status']in('EDGE_EXTERNAL','EDGE_CONSTANT'):
            code+=f"assign {port}[{num}]={width}'d0;\n"
        else:raise ValueError('unqualified NX boundary')
    forward=next(r for r in network['transport']['xf_forward']if r['slice']==leafsl and r['leaf']==leafk)
    code+='wire[277:0]xq_actual;\n'+delay('actual_xf',278,forward['xf_forward_edges'],'{xf_v,xf_s,xf}','xq_actual')
    mask=1<<leafk
    code+=f"assign xf_valid[{beat//5}]=xq_actual[277]?5'd{mask}:5'd0;assign xf_start[{beat//5}]=xq_actual[276]?5'd{mask}:5'd0;assign xf_data[{beat//5}]=1380'(xq_actual[275:0])<<{276*leafk};\n"
    code+='wire[32:0]actual_rb;\n'+delay('actual_rstd',33,ret[(leafsl,leafk)]['rb_broadcast_edges'],f'{{xr_rbv[{beat//5}],xr_rbd[{beat//5}]}}','actual_rb')
    code+='assign rb_v=actual_rb[32];assign rb_d=actual_rb[31:0];\n'
    code+='wire[160:0]actual_cmd;\n'+delay('actual_command',161,ent[(leafsl,leafk)]['command_transport_edges'],f'{{xcv[{beat//5}][{leafk}],xcd[{beat//5}]}}','actual_cmd')
    code+='wire leaf_cv=(cyc<900)?c_v:actual_cmd[160];wire[159:0]leaf_cd=(cyc<900)?c_d:actual_cmd[159:0];\n'
    first=s.index('    // Boundary stimulus dates');last=s.index('    // row image to write:',first)
    s=s[:first]+code+'\n'+s[last:]
    return s


def run(a):
    root=a.root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    network=json.loads(a.network.read_text());entry=json.loads(a.entry.read_text());returns=json.loads(a.returns.read_text());booking=json.loads(a.booking.read_text());control=json.loads(a.control.read_text())
    if network['verdict']!='PASS_SOURCE_NORM_NETWORK' or booking['adoption'] or not booking['die_owner_approval_required']:
        raise ValueError('explicit unadopted source-qualified candidate required')
    rd=out/'run';shutil.copytree(a.source_run,rd)
    if int((rd/'a_eps.mem').read_text().strip(),16)!=booking['eps_bits']:raise ValueError('actual fixture EPS differs from programme')
    for mode,(commands,emits)in enumerate(command_rows(booking,control,entry,booking['base_vo_edge'])):
        (rd/f'commands{mode}.mem').write_text(''.join(f'{v:053x}\n'for v in commands));(rd/f'emits{mode}.mem').write_text(''.join(f'{v:06x}\n'for v in emits))
    tb=network_tb((root/'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv').read_text(),root,network,entry,returns,booking,control,a.beat)
    (out/'tb.sv').write_text(tb)
    files=(root/'physical/hbm_norm_split_20261008/sources.f').read_text().split()
    files+=['rtl/hdc/v41x/ot_dsrom_su_add6.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv']
    files+=['physical/asap7_memory_macros_v2/'+m+'/'+m+'.v'for m in('ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_512x128_m4_r2c2','ot_sram_1r1w_512x128_m4_r0c0')]
    files+=['rtl/dsrom_sys/s81_dv/slice/'+n+'.sv'for n in('ot_s81sl_vn','ot_s81sl_vp','ot_s81sl_vq','ot_s81sl_aq12x','ot_s81sl_xrt','ot_s81sl_rstop','ot_s81sl_rstop_xo','ot_s81sl_rstopt','ot_s81sl_rstopt_xo')]
    files=list(dict.fromkeys(files));missing=[f for f in files if not(root/f).is_file()]
    if missing:raise ValueError('exact source closure missing '+str(missing))
    (out/'source_hashes.json').write_text(json.dumps({f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},indent=1)+'\n')
    (out/'booking.json').write_text(json.dumps(booking,indent=1)+'\n')
    cmd=['verilator','--binary','--timing','-O1','--build-jobs','4','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-GBEAT='+str(a.beat),'-GNORMR=1','-GVQ_XMEM=2',
         '--top-module','tb_s81sl_beat','-Mdir',str(out/'obj'),'--output-split','5000','--output-split-cfuncs','500','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0',*(str(root/f)for f in files),str(out/'tb.sv')]
    with(out/'build.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    results={}
    for name,mode,mut in [('legacy',0,0),('candidate',1,0),('shifted_partial',1,1),('corrupt_partial',1,2)]:
        with(out/(name+'.log')).open('w')as log:q=subprocess.run([str(out/'obj/Vtb_s81sl_beat'),'+MODE='+str(mode),'+MUT='+str(mut)],cwd=rd,stdout=log,stderr=subprocess.STDOUT)
        text=(out/(name+'.log')).read_text()
        if name=='legacy':ok=q.returncode==0 and 'BASELINE_HEAD_NORM FAIL actual_XR_partial_set_misaligned'in text
        elif name=='candidate':ok=q.returncode==0 and '\nPASS\n'in text and 'ACTUAL_HEAD_PUBLICATION'in text
        elif name=='shifted_partial':ok=q.returncode!=0 and 'candidate actual XR fault'in text
        else:ok=q.returncode!=0 and 'real xfin rstd mismatch'in text
        results[name]=dict(qualified=ok,rc=q.returncode,design_verdict='FAIL'if name=='legacy'else('PASS'if name=='candidate'else'CAUGHT'))
        if not ok:raise ValueError('actual component '+name+' failed; inspect '+str(out))
    record=dict(PASS=True,scope='ONE_NATIVE_PRODUCER_REAL16XR_16XFIN_38HOP_HEAD_PUBLICATION',results=results,
        pdsk_candidate=booking['pdsk_candidate'],control_span_delta_edges=booking['added_control_span_edges'],one_command_per_engine_per_edge=True,
        other79partial_values='explicit fixture boundary operands; static dates from emitted programme',
        physical_START_qualified=False,regional_clock_phase_qualified=False,adoption=False,full_token=False)
    (out/'verdict.json').write_text(json.dumps(record,indent=1)+'\n');print(json.dumps(record,indent=1))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in('network','entry','returns','booking','control','source-run','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--beat',type=int,default=37);run(p.parse_args())
