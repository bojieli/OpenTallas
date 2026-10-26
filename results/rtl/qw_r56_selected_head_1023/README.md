# Selected r56 head source

Actual gold1 r56cxc p2/port_bind.json selects qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 from rtl/qwen_dv/headprep13/corepub39. It instantiates ot_qfd_tt_ctlm_static_hr_safe32_native32_1r with STAGE_ME=1 and SEGCAL=1. The leaf definition and helpers already exist on main at rtl/qwen_dv/headprep13/h16za/native32_1r_param.v and native32_helpers.sv. All three exact r56 source96d96401e blobs are byte-identical to maina970a5117; see SOURCE.json.

The actual selected parent is a real source module but physically unbound in r56 bind.json. It owes f16_auth, f16_obs, init_u0 inputs and f16_st/table_req outputs. Do not transfer leaf source-functional proof to parent or physical qualification.

The old token stage fixture attempts an absent behavioural safe32 family and the old generic landed LP. These are not the selected r56 parent. Current-main stock head passes131/131, while generic LP lockstep fails3317/27981 in the original TOK result; preserve it. Use the stage script supported --die-netlist continuation with the exact selected native32 leaf packet, not an import of old safe32 source or an edit to an abandoned LP. TOK lead owns this run.
