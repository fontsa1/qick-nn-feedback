#!/usr/bin/env bash
cd "${REPO_ROOT:-$(dirname "$0")/../../../..}"
for s in 20260901 20260902 20260903 20260905; do
  ./"${PYTHON:-python}" -u campaign_v144/final/analysis/offline/map_trainrows.py --seed $s --capture campaign_v144/final/analysis/offline/trainrows/A_train_300000_300600.npz campaign_v144/final/analysis/offline/trainrows/B_train_300000_300600.npz > campaign_v144/final/analysis/offline/map_trainrows_s$s.log 2>&1
done
echo SEEDS DONE
