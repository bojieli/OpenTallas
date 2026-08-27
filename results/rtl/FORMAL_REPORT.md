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
- `rtl/formal/f_schedule_controller.sv`: `9de51a7b31379005a70b4b6b6b2d226159012289a4f96771e49685a829d51a04`
- `rtl/formal/f_skid_buffer.sv`: `fb0a6b160dd39781b7ec44af682a1a007a2b15c08bdba46a8c867d5fa5ea835b`
- `rtl/formal/f_stage_controller.sv`: `888edab61653f0e8ed04183e8b1f0d8b883bce8310df9fcfab1ff92ade87fd83`
- `rtl/formal/f_sync_level.sv`: `304bec4966c687b109d9d00cbe18a99382b4e5f343c3b880f4575a4ed569adab`
- `rtl/lib/ot_async_fifo.sv`: `5fa7bec8374b40b618187c469e7721afae147e9f0d202abfc56f5bcb444bfbf2`
- `rtl/lib/ot_cdc_mailbox.sv`: `f3fecaea6089477d6349144d76406e5dbd90740e127067301c352c3ebdbe2e76`
- `rtl/lib/ot_reset_sync.sv`: `489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd`
- `rtl/lib/ot_skid_buffer.sv`: `4837dc61b4a89a53e68b05f16b46e1717e79f4817bf5b812afba0dc3cd32008a`
- `rtl/lib/ot_sync_level.sv`: `4a358fdbdc353c8295c58037887cb442c5b3ba2eb4f27ccd7c513d770727cc93`
- `rtl/ot_credit_manager.sv`: `8711520a3eb35b6c780c287b5c2ade88ef059384426c513d80a1584b20a0018a`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_route_mask.sv`: `9da491e18f276a5d6be5c3cf07288bc78d2c75d57d3e4e830b3ea7ce967c4542`
- `rtl/ot_schedule_controller.sv`: `5e9c16d4fea3d6980d1a1310c7470b75d312a03af306db473df264ba39ef76dc`
- `rtl/ot_stage_controller.sv`: `3247c350d23c22fa6bf038c0a13a34bc64fc2050fb3417a7758b729b7afcc0b0`
- `spec/VERIFICATION_PLAN.md`: `f6f0cec6430c70b4b61d7cfe14c070212de0bd48bfa99fe6de691568ddd1d208`
- `spec/verification.json`: `1ef9077d39db2f5306ba1e56c19fcb8d83babaa3bfebdc8e0f87e359562a3c86`
- `tools/rtl_campaign.py`: `529060e83f614d51fe96218fedf7a966c7575d633298f1a7952c9ed0651fe98b`
