# PC_H sr15 structural clock replacement

Replace sr14 boundary-only clock delay relative to internal register mass: full-domain physical trees preserve exact ck/hck ownership, actual macro clock coordinates, dedicated same-depth macro drivers, bounded physical leaves and equal stage budgets. Payload RTL, baseline and group landing ages are unchanged; no clock alias.

Safety checklist: two original domains stay separate. Each clock entry must resolve to one existing propagated clock; entries owned by the other clock are skipped, never relabeled. All FFs and actual SRAM clock entries in that domain receive the same complete buffer stage budget. Source payload and all program/token data edges are inherited from sr14. The physical change does not qualify the separate current parent baseline source. Both TT and FF clock and setup/hold results, actual geometry images and ROOT review remain mandatory.
