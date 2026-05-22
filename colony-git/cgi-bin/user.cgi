#!/ffp/bin/bash
# GET /colony-git/api/user.cgi?name=<username>
# Returns the public profile of a Colony Git user:
#   { "username": "...",
#     "joined": 1716391200,    // unix seconds, or null if unknown
#     "repos": [ { name, description, last_commit_at, ... } ] }
#
# The repos array uses the same per-entry shape as repos.cgi but filtered
# to only the ones owned by the user. We re-walk the bare-repo directory
# rather than parsing repos.cgi output to keep the two endpoints independent.

set -u
. "$(dirname "$0")/lib.sh"

USERS_DIR=${COLONY_GIT_USERS_DIR:-/mnt/HD/HD_a2/ffp/etc/colony-git-users}

name=$(qs_get name)
case "$name" in
    ''|*[!A-Za-z0-9_-]*) emit_error "invalid username" 400 ;;
esac

# Try to read joined timestamp from the per-user sidecar file. The format
# is `key=value` lines; only `joined` is meaningful today, but the file
# is reserved for future fields (bio, email, etc).
joined=""
sidecar="$USERS_DIR/$name"
if [ -f "$sidecar" ]; then
    joined=$(/ffp/bin/awk -F= '$1 == "joined" { print $2; exit }' "$sidecar")
fi

emit_headers
printf '{'
printf '"username":"%s",' "$(json_escape_value "$name")"
if [ -n "$joined" ]; then
    case "$joined" in
        ''|*[!0-9]*) printf '"joined":null,' ;;
        *) printf '"joined":%d,' "$joined" ;;
    esac
else
    printf '"joined":null,'
fi
printf '"repos":['

first=1
shopt -s nullglob 2>/dev/null || true
for repo_dir in "$REPOS_ROOT"/*.git; do
    [ -f "$repo_dir/HEAD" ] || continue
    [ -f "$repo_dir/owner" ] || continue
    owner=$(head -n 1 "$repo_dir/owner" 2>/dev/null)
    [ "$owner" = "$name" ] || continue

    repo_name=$(basename "$repo_dir")

    desc=""
    if [ -f "$repo_dir/description" ]; then
        desc=$(head -n 1 "$repo_dir/description" 2>/dev/null)
        case "$desc" in
            "Unnamed repository"*|"") desc="" ;;
        esac
    fi

    head_branch=$(git_in "$repo_dir" symbolic-ref HEAD 2>/dev/null) || head_branch=""
    head_branch=${head_branch#refs/heads/}
    [ -z "$head_branch" ] && head_branch="HEAD"

    log_line=$(git_in "$repo_dir" log -1 --format='%H%x09%ci%x09%an%x09%s' HEAD 2>/dev/null) || log_line=""
    saved_ifs=$IFS
    IFS=$'\t'
    set -- $log_line
    last_hash=${1:-}
    last_date=${2:-}
    last_author=${3:-}
    last_subject=${4:-}
    IFS=$saved_ifs

    commit_count=$(git_in "$repo_dir" rev-list --count HEAD 2>/dev/null) || commit_count=0
    size_kb=$(du -sk "$repo_dir" 2>/dev/null | awk '{print $1}')
    size_bytes=$((${size_kb:-0} * 1024))

    [ $first -eq 0 ] && printf ','
    first=0

    printf '{'
    printf '"name":"%s",'             "$(json_escape_value "$repo_name")"
    printf '"description":"%s",'      "$(json_escape_value "$desc")"
    printf '"owner":"%s",'            "$(json_escape_value "$owner")"
    printf '"head_branch":"%s",'      "$(json_escape_value "$head_branch")"
    printf '"last_commit_hash":"%s",' "$(json_escape_value "$last_hash")"
    printf '"last_commit_at":"%s",'   "$(json_escape_value "$last_date")"
    printf '"last_commit_author":"%s",' "$(json_escape_value "$last_author")"
    printf '"last_commit_subject":"%s",' "$(json_escape_value "$last_subject")"
    printf '"commit_count":%d,'       "${commit_count:-0}"
    printf '"size_bytes":%d'          "${size_bytes:-0}"
    printf '}'
done

printf ']}\n'
