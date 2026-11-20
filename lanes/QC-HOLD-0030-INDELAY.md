# QC input-delay class (QC-HOLD-0030, 11-20)

Source: newest constraint.sdc per QC type under kw43-wave-1109n qwen_compute items (6 gen hosts), lines set_input_delay -max N -clock vclk with N > 416.5 ps (50 percent of 833). Hard-core-bus column = the vclk delay covers b_hw_ctl_hc*_i[*], the bus that lands in u_cland_b_hw_ctl_hc*_i and feeds the hc hard cores (st_a / st_b).

| family | variants | max input delay ps (% of 833) | min | hard-core bus b_hw_ctl_hc* |
| slw_fw_v2 | 2 | 730 (88%) | 718 |  |
| coll_ft | 2 | 723 (87%) | 717 |  |
| sle_fw_v2 | 2 | 722 (87%) | 708 |  |
| slw_fw_v1 | 3 | 721 (87%) | 718 |  |
| sle_fw_v1 | 2 | 716 (86%) | 710 |  |
| sle_stm_v2 | 2 | 715 (86%) | 712 |  |
| coll_ftc | 1 | 714 (86%) | 714 |  |
| slw_stm_v2 | 2 | 713 (86%) | 709 |  |
| sle_hc2 | 3 | 711 (85%) | 672 |  |
| sle_stm_v1 | 2 | 711 (85%) | 710 |  |
| slw_stm_v3 | 1 | 710 (85%) | 710 |  |
| slw_fe_v2 | 2 | 709 (85%) | 690 |  |
| slw_stm_v1 | 3 | 708 (85%) | 686 |  |
| sle_st_b_v2 | 4 | 706 (85%) | 662 | yes |
| sle_st_b_v1 | 4 | 706 (85%) | 667 | yes |
| sle_fe_v3 | 1 | 706 (85%) | 706 |  |
| native59 | 1 | 706 (85%) | 706 |  |
| sle_stm_v3 | 1 | 702 (84%) | 702 |  |
| slw_fw_v3 | 1 | 702 (84%) | 702 |  |
| slw_hc2 | 3 | 701 (84%) | 594 |  |
| sle_ctl | 7 | 700 (84%) | 634 |  |
| sle_fe_v1 | 2 | 700 (84%) | 697 |  |
| sle_st_a_v2 | 4 | 697 (84%) | 666 | yes |
| slw_fe_v1 | 3 | 696 (84%) | 677 |  |
| slw_st_b_v2 | 4 | 693 (83%) | 664 | yes |
| sle_fw_v3 | 1 | 691 (83%) | 691 |  |
| sle_fe_v2 | 1 | 669 (80%) | 669 |  |
| slw_hc0 | 2 | 667 (80%) | 646 |  |
| slw_st_b_v1 | 3 | 667 (80%) | 660 | yes |
| slw_st_a_v2 | 2 | 665 (80%) | 648 | yes |
| sle_hc0 | 3 | 663 (80%) | 649 |  |
| sle_hc1 | 2 | 658 (79%) | 586 |  |
| slw_st_a_v1 | 3 | 640 (77%) | 639 | yes |
| sle_st_a_v1 | 3 | 639 (77%) | 632 | yes |
| sle_sc_v3 | 1 | 631 (76%) | 631 |  |
| slw_sc_v1 | 3 | 618 (74%) | 565 |  |
| slw_hc1 | 3 | 601 (72%) | 586 |  |
| slw_sc_v3 | 1 | 599 (72%) | 599 |  |
| sle_sc_v1 | 2 | 595 (71%) | 560 |  |
| slw_su_l0 | 3 | 586 (70%) | 577 |  |
| sle_su_l1 | 2 | 585 (70%) | 570 |  |
| sle_sc_v2 | 1 | 583 (70%) | 583 |  |
| slw_sc_v2 | 1 | 580 (70%) | 580 |  |
| sle_su_l0 | 2 | 571 (69%) | 559 |  |
| slw_su_l1 | 2 | 566 (68%) | 565 |  |
| slw_su_c | 2 | 552 (66%) | 531 |  |
| sle_su_c | 1 | 537 (64%) | 537 |  |
47 families; 106 of 131 variants over 416.5 ps
