# S6C private ABI binder repair

Required failed-stage replay on immutable dsg6f c6520b2ee inputs. Both actual CLOSED S6C views bind with zero unmapped real pins after validating every actual private parent slice. The original source already emits x__est[0:0] and GRP_H i_ctl[193:0]; its frame builder retained the whole 13/271-bit producer widths. The repair makes frame pins describe the private interface and preserves strict pin_map. No RTL, view, source identity or timing boundary changes. Future GEN uses the same correction in masters().

The first saved-stage runner exited at missing KV.BINDINGS initialization; the successful replay calls the same _set_geometry(True) as bind_views --split. It ran at 8 GB under normal ot-run admission, unit oth-ubuntu-1730030-1792616651. Original failed GEN and its live worktree were not edited.

This is only the two-view saved binder stage. Whole-die strict bind, GEN completion, actual reticle/per-bit contracts, and health connection hp_fault_371.a at 406.8 um versus 405 um remain pending. Existing sqk2x5 diagnostic chains remain separate.
