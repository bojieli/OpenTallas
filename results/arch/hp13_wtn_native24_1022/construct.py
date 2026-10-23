import pathlib,json,ctlm6_bound_macro as B
p=pathlib.Path('.')
rtl,helpers,record=B.build((p/'wtn.json').read_bytes(),'qfd_tt_ctlm_dv_wtn','qfd_tt_ctlm_dv_wtn_native32',load_cap=24,transparent_inverters=True,retain_mux=True,shared_helpers=True,retain_all_comb=True,fuse_ao=True)
(p/'qfd_tt_ctlm_dv_wtn_native32.sv').write_text(rtl)
(p/'wtn_native_helpers.sv').write_text('\n'.join(helpers)+'\n')
(p/'construct_record.json').write_text(json.dumps(record,indent=2)+'\n')
print('CONSTRUCT_PASS',record['original_cells'],record['final_cells'],record['passes'])
