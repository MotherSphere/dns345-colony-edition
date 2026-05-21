#!/ffp/bin/bash
# GET /colony-git/api/commits?name=<repo>&ref=<ref>&limit=<N>&skip=<N>
# Returns log entries reachable from <ref> as JSON:
#   {
#     "ref":"master","skip":0,"limit":50,
#     "commits":[
#       {"hash":"...","short":"...","date":"...","author":"...",
#        "author_email":"...","subject":"..."}
#     ]
#   }
#
# limit defaults to 50, capped at 200. skip defaults to 0.

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
repo_dir=$(resolve_repo "$name")

limit_raw=$(qs_get limit)
limit=${limit_raw:-50}
case "$limit" in
    ''|*[!0-9]*) limit=50 ;;
esac
[ "$limit" -gt 200 ] && limit=200
[ "$limit" -lt 1 ] && limit=1

skip_raw=$(qs_get skip)
skip=${skip_raw:-0}
case "$skip" in
    ''|*[!0-9]*) skip=0 ;;
esac

emit_headers
printf '{"ref":"%s","skip":%d,"limit":%d,"commits":[' \
    "$(json_escape_value "$ref")" "$skip" "$limit"

# Use a unique field separator (RS, 0x1e) that can't appear in author/subject
# safely, and split on it. Tabs are technically allowed in commit messages
# but RS isn't.
first=1
git_in "$repo_dir" log "$ref" \
    --format='%H|%h|%ci|%an|%ae|%s' \
    --skip="$skip" -n "$limit" 2>/dev/null | while IFS='|' read -r hash short date author email subject; do
    [ -z "$hash" ] && continue

    [ $first -eq 0 ] && printf ','
    first=0

    printf '{'
    printf '"hash":"%s",'         "$(json_escape_value "$hash")"
    printf '"short":"%s",'        "$(json_escape_value "$short")"
    printf '"date":"%s",'         "$(json_escape_value "$date")"
    printf '"author":"%s",'       "$(json_escape_value "$author")"
    printf '"author_email":"%s",' "$(json_escape_value "$email")"
    printf '"subject":"%s"'       "$(json_escape_value "$subject")"
    printf '}'
done

printf ']}\n'
