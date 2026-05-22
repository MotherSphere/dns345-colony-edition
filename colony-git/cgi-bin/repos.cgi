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

    # Owner: prefer the explicit `owner` file (written by repo-create.cgi
    # or backfilled manually); fall back to the passwd entry for the
    # repo's UID, then to "user". The Colony auth system uses htpasswd
    # accounts that have no system UID, so the file is the canonical source.
    owner=""
    if [ -f "$repo_dir/owner" ]; then
        owner=$(head -n 1 "$repo_dir/owner" 2>/dev/null)
    fi
    if [ -z "$owner" ]; then
        owner_uid=$(stat -c '%u' "$repo_dir" 2>/dev/null)
        owner=$(getent passwd "$owner_uid" 2>/dev/null | cut -d: -f1)
    fi
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

    # File count + dominant extension: read from languages-<HEAD>.json cache
    # if available (written by languages.cgi on first browse or by the
    # post-receive hook). Avoids a fresh ls-tree -r per repo per home view.
    file_count=0
    dominant_ext=""
    head_full=$(git_in "$repo_dir" rev-parse HEAD 2>/dev/null)
    cache_json="$repo_dir/colony-cache/languages-$head_full.json"
    if [ -n "$head_full" ] && [ -f "$cache_json" ]; then
        # Pull file_count + dominant ext via gawk: the dominant ext is the
        # key with the biggest byte count in the "extensions" object. We
        # only emit the extension string (with the leading dot), the SPA
        # turns that into a colored badge.
        ext_line=$(/ffp/bin/awk '
            BEGIN { fc = 0; total = 0; best_k = ""; best_v = 0 }
            {
                # Match "file_count":NUMBER
                if (match($0, /"file_count":[0-9]+/)) {
                    s = substr($0, RSTART + 13, RLENGTH - 13);
                    fc = s + 0;
                }
                # Extract extensions object body
                if (match($0, /"extensions":\{[^}]*\}/)) {
                    body = substr($0, RSTART + 14, RLENGTH - 15);
                    n = split(body, parts, ",");
                    for (i = 1; i <= n; i++) {
                        p = parts[i];
                        # Each part: "key":value
                        c = index(p, ":");
                        if (c == 0) continue;
                        k = substr(p, 1, c - 1);
                        v = substr(p, c + 1) + 0;
                        # Strip surrounding quotes from key
                        gsub(/^"|"$/, "", k);
                        if (v > best_v) { best_v = v; best_k = k; }
                    }
                }
            }
            END { print fc "\t" best_k }
        ' "$cache_json")
        file_count=${ext_line%%$'\t'*}
        dominant_ext=${ext_line#*$'\t'}
    fi

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
    printf '"size_bytes":%d,'         "${size_bytes:-0}"
    printf '"file_count":%d,'         "${file_count:-0}"
    printf '"dominant_ext":"%s"'      "$(json_escape_value "$dominant_ext")"
    printf '}'
done

printf ']\n'
