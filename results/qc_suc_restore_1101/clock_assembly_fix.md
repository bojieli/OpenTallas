Source READY separately from macro-view adoption

bind.py kit-rtl previously emitted grid tap inputs but omitted planned early-core tap inputs. The fix emits each declared early-core clock and passes it into a private copy of the bound module, connected to the actual declared child clock pin before synthesis. It changes no data/reset connection, declared schedule, or source bind output. gen_phys.core_tap_rows now respects the existing paired physical_inst/physical_master alias.

Actual825/profile3_pad strict source canary covers all12SUtypes/60childclockpins. The actualsle_su_c wrapper generation completed with0unbound and8real coreclockconsumers. Smalltests cover actualconsumer/idempotence, inlinegroup, missing/duplicate rejection, and physicalalias with unchangedTT/FF schedule.

The source fix intentionally fails closed on unresolved declared children.14CBtypes expose an existing mismatch: e.g plan cbf_q11 u_t22/masterqfd_tile_nk_a0c versus actual native u_u_t_2_2/masterqfd_tile_nk_rp2_romleaf_rr. No spelling alias is applied; A0wrapper/native contract and eligible signed views must establish those cuts. This packet does not adopt the recovered SU-C macro views or claim FT traversal/timing closure.
