import json,copy,sys
base=json.load(open('/home/ubuntu/wt/sdie-0600/results/physical/die_iter_1012/s81/canonical_widehub_1015/vmc_26b/hub_layout.json'))
SU=(5184.0,7339.68); HCW=3676.32; HCT=9627.12*6/11; HCS=9627.12*5/11
def lay(name,blocks,band,order):
    L=copy.deepcopy(base); L['source']='S-DIE hub v3 study /tmp/sdie-v3/mk_layouts.py ('+name+')'; L['order']=order
    L['blocks'].update(blocks); L['band_blocks']=band; L.pop('corridor',None) if False else None
    json.dump(L,open('/tmp/sdie-v3/lay/%s.json'%name,'w'),indent=1)
# Codex candidate c74342891 homes (folded HC split hc_t low 6 rows / hc_s high 5 rows; wfc/host/sseq not homed there -> next to collective/SU)
lay('c743',{'sp_vm':[10000,16000,5037.0,4600.8,True],'sp_su_s':[10000,8500,SU[0],SU[1],True],
 'sp_hc_t':[17800,9500,HCW,HCT,True],'sp_hc_s':[17800,9500+HCT,HCW,HCS,True],
 'sp_capture':[11900,20643.2,1727.976,561.576,False],'sp_gather':[11900,21248,1727.976,1045.416,False],'sp_pq':[11900,22550,1672.248,449.256,False],
 'sp_collective':[15636,11500,1727.976,2721.576,False],'sp_host':[15636,11300,1727.976,129.576,False],'sp_wfc':[15636,14300,1727.976,328.296,False,'MY'],
 'sp_sseq':[10000,15880,1727.976,88.536,False],
 'bk_collector':[14500,21000,5270.376,881.256,True],'bk_selector':[14500,22000,5270.376,321.816,True]},
 {'bk_selector':[14500,22000,5270.376,321.816,'R0',{'vd':'S','iSW':'W','c_cmd':'W'}],'bk_collector':[14500,21000,5270.376,881.256,'R0',{'vd':'S','cSW':'W','c_cmd':'W'}]},
 'Codex c74342891 child-hub preview homes')
def v3(name,street=(12600,300),x0=10300,hcx=17750,bky=3200):
    sy,sw=street; top=sy+sw; vmx=x0
    b={'sp_vm':[vmx,top,5037.0,4600.8,True],'sp_su_s':[x0,sy-SU[1],SU[0],SU[1],True],
     'sp_capture':[vmx+1654.56,top+4600.8+21.6,1727.976,561.576,False],'sp_gather':[vmx+1654.56,top+4600.8+626.4,1727.976,1045.416,False],
     'sp_pq':[vmx+1654.56,top+4600.8+2103.84,1672.248,449.256,False],
     'sp_collective':[15700,top,1727.976,2721.576,False],'sp_host':[15700,top+2743.2,1727.976,129.576,False],
     'sp_wfc':[15700,top+2894.4,1727.976,328.296,False,'MY'],'sp_sseq':[15700,top+3250,1727.976,88.536,False],
     'sp_hc_s':[hcx,top,HCW,HCS,True],'sp_hc_t':[hcx,sy-HCT,HCW,HCT,True],
     'bk_selector':[x0,bky,5270.376,321.816,True],'bk_collector':[x0,bky+343.4,5270.376,881.256,True]}
    band={'bk_selector':[x0,bky,5270.376,321.816,'R0',{'vd':'N','iSW':'W','c_cmd':'N'}],'bk_collector':[x0,bky+343.4,5270.376,881.256,'R0',{'vd':'N','cSW':'W','c_cmd':'N'}]}
    lay(name,b,band,'v3 street: VM over SU (W), collective+host+wfc+sseq centre N of street, HC_S N / HC_T S of street (E); link street y%.0f+%.0f; bk pair under SU near SW svc'%(sy,sw))
v3('v3a')
v3('v3b',street=(12500,432))
