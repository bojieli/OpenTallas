; benchmark generated from python API
(set-info :status unknown)
(declare-fun |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0| () Bool)
(declare-fun |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4| () Bool)
(declare-fun |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16| () Bool)
(declare-fun |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.ud[0][0]$_DFFE_PP___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.ud[0][256]$_DFFE_PP___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.ud[0][512]$_DFFE_PP___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.ud[0][768]$_DFFE_PP___0| () Bool)
(declare-fun |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.body[14]$_DFF_P___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0| () Bool)
(declare-fun |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0| () Bool)
(declare-fun canonical__rst_n__ot_rl1$_DFF_P___0 () Bool)
(declare-fun |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0| () Bool)
(declare-fun |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13| () Bool)
(declare-fun |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1| () Bool)
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5677 (or $x5616 $x5676)))
 (let (($x5678 (not $x5677)))
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5683 (ite $x5682 true $x5678)))
 (let (($x5681 (not true)))
 (let (($x5684 (ite $x5681 false $x5683)))
 (not $x5684)))))))))))
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5687 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4|)))
 (let (($x5688 (or $x5687 $x5676)))
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5690 (ite $x5682 true (not $x5688))))
 (let (($x5681 (not true)))
 (let (($x5691 (ite $x5681 false $x5690)))
 (not $x5691))))))))))
(assert
 (let (($x5653 (not |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32|)))
 (let (($x5635 (not |canonical__u_ot_pr_core.u.ud[0][0]$_DFFE_PP___0|)))
 (let (($x5663 (or $x5635 $x5653)))
 (let (($x5667 (and (and |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32| $x5663) |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
 (let (($x5665 (and (and (not |canonical__u_ot_pr_core.u.ud[0][256]$_DFFE_PP___0|) $x5663) |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
 (let (($x5668 (or $x5665 $x5667)))
 (let (($x5657 (not |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
 (let (($x5620 (not |canonical__u_ot_pr_core.u.ud[0][512]$_DFFE_PP___0|)))
 (let (($x5654 (or $x5620 $x5653)))
 (let (($x5658 (and (and (not |canonical__u_ot_pr_core.u.ud[0][768]$_DFFE_PP___0|) $x5654) $x5657)))
 (let (($x5661 (or $x5658 (and (and |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32| $x5654) $x5657))))
 (let (($x5651 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12|)))
 (let (($x5669 (or (or $x5651 $x5661) $x5668)))
 (let (($x5645 (not |canonical__u_ot_pr_core.u.body[14]$_DFF_P___0|)))
 (let (($x5672 (or (and |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12| $x5669) (and $x5645 $x5669))))
 (let (($x5673 (not $x5672)))
 (let (($x5674 (not $x5673)))
 (let (($x5622 (not |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))
 (let (($x5636 (or $x5635 $x5622)))
 (let (($x5640 (and (and |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0| $x5636) |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5638 (and (and (not |canonical__u_ot_pr_core.u.ud[0][256]$_DFFE_PP___0|) $x5636) |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5641 (or $x5638 $x5640)))
 (let (($x5626 (not |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5629 (and (and |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0| (or $x5620 $x5622)) $x5626)))
 (let (($x5623 (or $x5620 $x5622)))
 (let (($x5618 (not |canonical__u_ot_pr_core.u.ud[0][768]$_DFFE_PP___0|)))
 (let (($x5630 (or (and (and $x5618 $x5623) $x5626) $x5629)))
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5642 (or (or $x5616 $x5630) $x5641)))
 (let (($x5647 (or (and |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0| $x5642) (and $x5645 $x5642))))
 (let (($x5648 (not $x5647)))
 (let (($x5649 (not $x5648)))
 (and (distinct $x5649 $x5674) true))))))))))))))))))))))))))))))))))
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5676))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))))
(assert
 (let (($x5626 (not |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5626))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5680))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
(assert
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5616))))
(assert
 (let (($x5757 (and true (not (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))))
 (=> $x5757 |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
(assert
 (let (($x5622 (not |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5622))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5754 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5754))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
(assert
 (let (($x5651 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5651))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12|)))
(assert
 (let (($x5687 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5687))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4|)))
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5676))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))))
(assert
 (let (($x5626 (not |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5626))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
 (=> $x5779 |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
(assert
 (let (($x5657 (not |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5657))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
 (=> $x5779 |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5680))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
(assert
 (let (($x5754 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5754))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
(assert
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5616))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
(assert
 (let (($x5622 (not |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5622))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5653 (not |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5653))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
 (=> $x5779 |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32|)))
(assert
 (let (($x5777 (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5777))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))
(assert
 (let (($x5767 (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5767))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5676))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))))
(assert
 (let (($x5626 (not |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5626))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5680))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
(assert
 (let (($x5754 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5754))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
(assert
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5616))))
(assert
 (let (($x5757 (and true (not (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))))
 (=> $x5757 |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
(assert
 (let (($x5622 (not |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5622))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5651 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5651))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___12|)))
(assert
 (let (($x5687 (not |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5687))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |extra__u_ot_pr_core.u.rwr[0]$_DFF_PN0___4|)))
(assert
 (let (($x5676 (not |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5676))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.ub[0]$_DFF_PN0___0|)))))
(assert
 (let (($x5777 (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5777))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))
(assert
 (let (($x5767 (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5767))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))
(assert
 (let (($x5626 (not |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5626))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
 (=> $x5779 |canonical__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___0|)))
(assert
 (let (($x5657 (not |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5657))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
 (=> $x5779 |extra__u_ot_pr_core.u.un[0][1]$_DFFE_PN0P___16|)))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5680))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
(assert
 (let (($x5754 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5754))))
(assert
 (let (($x5750 (and true (not (not canonical__rst_n__ot_rl1$_DFF_P___0)))))
 (=> $x5750 |canonical__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___0|)))
(assert
 (let (($x5616 (not |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5616))))
(assert
 (let (($x5770 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[0]$_DFF_PN0___13|)))))
 (=> $x5770 |canonical__u_ot_pr_core.u.rwr[0]$_DFF_PN0___0|)))
(assert
 (let (($x5622 (not |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5622))))
(assert
 (let (($x5680 (not |canonical__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___0|)))
 (let (($x5682 (not $x5680)))
 (let (($x5740 (and true $x5682)))
 (=> $x5740 |canonical__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___0|)))))
(assert
 (let (($x5653 (not |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32|)))
 (let (($x5681 (not true)))
 (=> $x5681 $x5653))))
(assert
 (let (($x5779 (and true (not (not |extra__u_ot_pr_core.u.u_rr.rst_n[1]$_DFF_PN0___1|)))))
(=> $x5779 |extra__u_ot_pr_core.u.un[0][0]$_DFFE_PN0P___32|)))
(check-sat)
