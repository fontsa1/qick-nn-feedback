#!/bin/bash
# S2: arch_aug.py (augmentation with a fitted replay-channel model) on each board's v1.44 replay. No board access.
# Board A writes s2/arch_aug_v144.json, board B s2/board_B/arch_aug_v144_B.json; each run takes about 17 minutes.
cd "${REPO_ROOT:-$(dirname "$0")/..}"
export PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=6 TF_NUM_INTRAOP_THREADS=6
PY="${PYTHON:-python}"   # set PYTHON to your environment's interpreter, e.g. PYTHON=.venv/bin/python
S=campaign_v144/final/analysis/s2
for B in A B; do
  $PY $S/s2_prep_v144.py $B > $S/prep_$B.log 2>&1
  if [ $B = A ]; then O=$S; Y=$S/y20k.npy; J=$O/arch_aug_v144.json; else O=$S/board_B; Y=$S/y20k_B.npy; J=$O/arch_aug_v144_B.json; fi
  mkdir -p $O
  AUG_LOOP_X=campaign_v144/final/analysis/replay20k_$B.npy AUG_LOOP_Y=$Y AUG_T4_CLEAN=$S/${B}_axi_probs20k.npy \
  AUG_OUT=$J AUG_PRED=$O/preds $PY campaign_v140L1/arch_aug.py > $O/run.log 2>&1 < /dev/null
  echo "rc=$?" >> $O/run.log
done
