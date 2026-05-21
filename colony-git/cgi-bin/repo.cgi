#!/ffp/bin/bash
# GET /colony-git/api/repo?name=<repo>
# Returns repo detail as JSON:
#   {
#     "name":"foo.git","description":"...","default_branch":"master",
#     "head":{"hash":"...","date":"...","author":"...","subject":"..."},
#     "branches":[{"name":"master","hash":"...","date":"...","author":"...","subject":"..."}],
#     "tags":[...same shape...],
#     "readme":{"path":"README.md","content":"..."}   // or null
#   }

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
repo_dir=$(resolve_repo "$name")

emit_headers

# --- description ---
desc=""
if [ -f "$repo_dir/description" ]; then
    desc=$(head -n 1 "$repo_dir/description" 2>/dev/null)
    case "$desc" in
        "Unnamed repository"*|"") desc="" ;;
    esac
fi

# --- default branch (HEAD) ---
default_branch=$(git_in "$repo_dir" symbolic-ref HEAD 2>/dev/null)
default_branch=${default_branch#refs/heads/}
[ -z "$default_branch" ] && default_branch="HEAD"

# --- HEAD commit info ---
log_line=$(git_in "$repo_dir" log -1 --format='%H%x09%ci%x09%an%x09%s' HEAD 2>/dev/null) || log_line=""
saved_ifs=$IFS
IFS=$'\t'
set -- $log_line
head_hash=${1:-}
head_date=${2:-}
head_author=${3:-}
head_subject=${4:-}
IFS=$saved_ifs

# --- emit branches[] and tags[] via for-each-ref ---
emit_ref_list() {
    local prefix=$1  # refs/heads or refs/tags
    local strip=${2:-} # prefix to strip from %(refname)
    local first=1 line ref hash date author subject

    git_in "$repo_dir" for-each-ref \
        --format='%(refname)|%(objectname)|%(committerdate:iso)|%(authorname)|%(subject)' \
        "$prefix" 2>/dev/null | while IFS='|' read -r ref hash date author subject; do
        [ -z "$ref" ] && continue
        ref=${ref#$strip}

        [ $first -eq 0 ] && printf ','
        first=0

        printf '{'
        printf '"name":"%s",'    "$(json_escape_value "$ref")"
        printf '"hash":"%s",'    "$(json_escape_value "$hash")"
        printf '"date":"%s",'    "$(json_escape_value "$date")"
        printf '"author":"%s",'  "$(json_escape_value "$author")"
        printf '"subject":"%s"'  "$(json_escape_value "$subject")"
        printf '}'
    done
}

# --- README detection: pick the first matching file at HEAD root ---
# Try common names in priority order, case-insensitive scan over root tree.
readme_path=""
readme_content=""
# git 1.7.8: ls-tree --name-only is supported.
# BusyBox grep doesn't accept -x; do the whole-line match in pure bash.
tree_entries=$(git_in "$repo_dir" ls-tree --name-only HEAD 2>/dev/null)
for candidate in README.md readme.md Readme.md README.markdown README README.txt readme; do
    saved_ifs=$IFS
    IFS=$'\n'
    for entry in $tree_entries; do
        if [ "$entry" = "$candidate" ]; then
            readme_path=$candidate
            break 2
        fi
    done
    IFS=$saved_ifs
done
IFS=$saved_ifs
if [ -n "$readme_path" ]; then
    # cap at 256 KB to avoid blowing JSON size
    readme_content=$(git_in "$repo_dir" show "HEAD:$readme_path" 2>/dev/null | /ffp/bin/head -c 262144)
fi

# --- LICENSE detection: same case-insensitive scan over root tree ---
license_path=""
for candidate in LICENSE LICENSE.md LICENSE.txt LICENCE LICENCE.md COPYING COPYING.md license license.md; do
    saved_ifs=$IFS
    IFS=$'\n'
    for entry in $tree_entries; do
        if [ "$entry" = "$candidate" ]; then
            license_path=$candidate
            break 2
        fi
    done
    IFS=$saved_ifs
done
IFS=$saved_ifs

# --- total commit count (HEAD) ---
total_commits=$(git_in "$repo_dir" rev-list --count HEAD 2>/dev/null) || total_commits=0

# --- emit JSON ---
printf '{'
printf '"name":"%s",'           "$(json_escape_value "$name")"
printf '"description":"%s",'    "$(json_escape_value "$desc")"
printf '"default_branch":"%s",' "$(json_escape_value "$default_branch")"
printf '"total_commits":%d,'    "${total_commits:-0}"
printf '"license_path":%s,'     "$([ -n "$license_path" ] && printf '"%s"' "$(json_escape_value "$license_path")" || printf 'null')"
printf '"head":{'
printf '"hash":"%s",'    "$(json_escape_value "$head_hash")"
printf '"date":"%s",'    "$(json_escape_value "$head_date")"
printf '"author":"%s",'  "$(json_escape_value "$head_author")"
printf '"subject":"%s"'  "$(json_escape_value "$head_subject")"
printf '},'
printf '"branches":['
emit_ref_list refs/heads/ refs/heads/
printf '],'
printf '"tags":['
emit_ref_list refs/tags/ refs/tags/
printf '],'
if [ -n "$readme_path" ]; then
    printf '"readme":{"path":"%s","content":"%s"}' \
        "$(json_escape_value "$readme_path")" \
        "$(json_escape_value "$readme_content")"
else
    printf '"readme":null'
fi
printf '}\n'
