#!/ffp/bin/bash
# GET /colony-git/api/repos
# Lists all bare repos under REPOS_ROOT as JSON:
#   [{"name":"foo.git","description":"...","owner":"...",
#     "head_branch":"master","last_commit_at":"2026-05-20T...",
#     "last_commit_author":"...","last_commit_subject":"...",
#     "commit_count":42,"size_bytes":12345}]
#
# Owner = numeric UID's passwd entry; falls back to "unknown" since the
# D-Link NAS only has one user (squeezec) for the share root.

set -u
. "$(dirname "$0")/lib.sh"

emit_headers
printf '['

first=1
shopt -s nullglob 2>/dev/null || true
for repo_dir in "$REPOS_ROOT"/*.git; do
    [ -f "$repo_dir/HEAD" ] || continue
    name=$(basename "$repo_dir")

    # Description: first line of description file if not the default stub.
    desc=""
    if [ -f "$repo_dir/description" ]; then
        desc=$(head -n 1 "$repo_dir/description" 2>/dev/null)
        case "$desc" in
            "Unnamed repository"*|"") desc="" ;;
        esac
    fi

    # Owner: passwd entry for the dir's UID (best effort).
    owner_uid=$(stat -c '%u' "$repo_dir" 2>/dev/null)
    owner=$(getent passwd "$owner_uid" 2>/dev/null | cut -d: -f1)
    [ -z "$owner" ] && owner="user"

    # HEAD branch: git 1.7.8 has no --short flag; strip refs/heads/ ourselves.
    head_branch=$(git_in "$repo_dir" symbolic-ref HEAD 2>/dev/null) || head_branch=""
    head_branch=${head_branch#refs/heads/}
    [ -z "$head_branch" ] && head_branch="HEAD"

    # Last commit on HEAD: hash, ISO date, author, subject (tab-separated, single line).
    # Avoid here-string (<<<) - it needs tmpfs which is 9.7MB on this NAS.
    log_line=$(git_in "$repo_dir" log -1 --format='%H%x09%ci%x09%an%x09%s' HEAD 2>/dev/null) || log_line=""
    saved_ifs=$IFS
    IFS=$'\t'
    set -- $log_line
    last_hash=${1:-}
    last_date=${2:-}
    last_author=${3:-}
    last_subject=${4:-}
    IFS=$saved_ifs

    # Commit count (HEAD).
    commit_count=$(git_in "$repo_dir" rev-list --count HEAD 2>/dev/null) || commit_count=0

    # On-disk size (KB → bytes).
    size_kb=$(du -sk "$repo_dir" 2>/dev/null | awk '{print $1}')
    size_bytes=$((${size_kb:-0} * 1024))

    [ $first -eq 0 ] && printf ','
    first=0

    printf '{'
    printf '"name":"%s",'             "$(json_escape_value "$name")"
    printf '"description":"%s",'      "$(json_escape_value "$desc")"
    printf '"owner":"%s",'            "$(json_escape_value "$owner")"
    printf '"head_branch":"%s",'      "$(json_escape_value "$head_branch")"
    printf '"last_commit_hash":"%s",' "$(json_escape_value "${last_hash:-}")"
    printf '"last_commit_at":"%s",'   "$(json_escape_value "${last_date:-}")"
    printf '"last_commit_author":"%s",' "$(json_escape_value "${last_author:-}")"
    printf '"last_commit_subject":"%s",' "$(json_escape_value "${last_subject:-}")"
    printf '"commit_count":%d,'       "${commit_count:-0}"
    printf '"size_bytes":%d'          "${size_bytes:-0}"
    printf '}'
done

printf ']\n'
