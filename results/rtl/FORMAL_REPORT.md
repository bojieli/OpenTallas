# Public-tool RTL formal campaign

**Overall status:** PASS

This is reproducible methodology evidence for the checked public RTL. It is not product signoff, macro qualification, or proof beyond each recorded bound. CVC4 induction is claimed only where the table explicitly lists a depth.

| Harness | Yosys SAT BMC | CVC4 BMC | Covers | Induction | Result |
|---|---:|---:|---:|---:|---|
| `f_skid_buffer` | 24 | 12 | 8 | bounded only | PASS |
| `f_async_fifo` | 24 | 12 | 14 | bounded only | PASS |
| `f_cdc_mailbox` | 32 | 16 | 28 | bounded only | PASS |
| `f_sync_level` | 24 | 12 | 12 | bounded only | PASS |
| `f_credit_manager` | 24 | 7 | 10 | 8 | PASS |
| `f_power_controller` | 24 | 12 | 10 | 8 | PASS |
| `f_route_mask` | 24 | 7 | 8 | bounded only | PASS |
| `f_schedule_controller` | 24 | 8 | 10 | bounded only | PASS |
| `f_stage_controller` | 24 | 12 | 18 | bounded only | PASS |

## Solver qualification notes

- The independent configurations are Yosys internal SAT and Yosys SMT2 with CVC4 1.8.
- Z3 4.8.12 was locally non-terminating at useful bounds for these generated models; Ubuntu Boolector 1.5.118 is too old for the interaction. Neither is counted as pass evidence.
- Some CVC4 bounds are intentionally lower than SAT because solver cost rises sharply; the exact depths are part of the claim, not hidden campaign metadata.

## Source manifest

- `rtl/formal/f_async_fifo.sv`: `de23d05e6776da1e5741a0bf3158fba12de65988fc05bdcd83ea057ca10ffdf0`
- `rtl/formal/f_cdc_mailbox.sv`: `579892e4f3adedc32eaa1dd566aa6109ee46482fda6599e60e57f18925503638`
- `rtl/formal/f_credit_manager.sv`: `b7c18204473b8ed433766ceeeb551ac7d86c4dd863cf312bc9c7c7a08d1c5318`
- `rtl/formal/f_power_controller.sv`: `1c5aac3840038a87fbfecd86725281397b91410bc6ed6aec63a036a85eabfe4b`
- `rtl/formal/f_route_mask.sv`: `dbe5f1a77f20c2dfbf78b873117087f3f9c2bef917f2abe11cc44ebbbbf0d0d7`
- `rtl/formal/f_schedule_controller.sv`: `48f2d88c5af3007ac24f437be51fea16588e3f4fd66a563f3426a4788b36e5ae`
- `rtl/formal/f_skid_buffer.sv`: `fb0a6b160dd39781b7ec44af682a1a007a2b15c08bdba46a8c867d5fa5ea835b`
- `rtl/formal/f_stage_controller.sv`: `73b28c130e4ad71d9e645c199327156613d1a9140f480fb5afa0f6cc8cece69a`
- `rtl/formal/f_sync_level.sv`: `304bec4966c687b109d9d00cbe18a99382b4e5f343c3b880f4575a4ed569adab`
- `rtl/lib/ot_async_fifo.sv`: `18704d1313cc07a04642412e544da5dba26cd5bff349d75a479d64e8d02cdcb5`
- `rtl/lib/ot_cdc_mailbox.sv`: `f3fecaea6089477d6349144d76406e5dbd90740e127067301c352c3ebdbe2e76`
- `rtl/lib/ot_reset_sync.sv`: `489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd`
- `rtl/lib/ot_skid_buffer.sv`: `4837dc61b4a89a53e68b05f16b46e1717e79f4817bf5b812afba0dc3cd32008a`
- `rtl/lib/ot_sync_level.sv`: `e474cac6feeb0402ac7a4794cfc7e73508b5ef0254c991204b8946b92cd08fd6`
- `rtl/ot_credit_manager.sv`: `4d61c6121b85f599fecd891ac5b4faf234df55e065e17eb28f619968e8720449`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_route_mask.sv`: `9da491e18f276a5d6be5c3cf07288bc78d2c75d57d3e4e830b3ea7ce967c4542`
- `rtl/ot_schedule_controller.sv`: `07301550750eeaedceb8116ba9b97bd95fe0c17e84b536020bd0470e3029d826`
- `rtl/ot_stage_controller.sv`: `8a0eb66a48c8198211a34b04c465a715bfb9fc072854a4f70e27cfa4e3c11fef`
- `spec/VERIFICATION_PLAN.md`: `f6f0cec6430c70b4b61d7cfe14c070212de0bd48bfa99fe6de691568ddd1d208`
- `spec/verification.json`: `1ef9077d39db2f5306ba1e56c19fcb8d83babaa3bfebdc8e0f87e359562a3c86`
- `tools/rtl_campaign.py`: `88c7a4df57bb679d5351e50d8c55f264fcda9dc82980e4900723a56253700003`
