#!/ffp/bin/bash
# GET /colony-git/api/commit?name=<repo>&hash=<sha>
# Returns one commit's metadata + diff body + stat.
#
# Output:
#   {
#     "hash":"...","short":"...","date":"...","author":"...","author_email":"...",
#     "subject":"...","body":"...","parents":["..."],
#     "stat":"<git show --stat output>",
#     "diff":"<git show -p output>"
#   }
#
# Both stat and diff are emitted as JSON strings (newlines escaped). The
# frontend tokenizes the diff client-side to render colored +/-/ctx lines.
# Server-side parsing would be neater but doubles the awk surface for a
# trivial client win.

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
repo_dir=$(resolve_repo "$name")

hash_raw=$(qs_get hash)
# Allow short hashes (>= 4 chars) or full; reject anything not hex.
case "$hash_raw" in
    *[!A-Fa-f0-9]*|"" ) emit_error "invalid hash" 400 ;;
esac
if [ "${#hash_raw}" -lt 4 ]; then
    emit_error "hash too short" 400
fi

# Resolve to full SHA. If git can't (unknown rev), 404.
hash=$(git_in "$repo_dir" rev-parse --verify "$hash_raw" 2>/dev/null)
[ -z "$hash" ] && emit_error "commit not found" 404
short=${hash:0:7}

# Metadata (single line, tab-separated, parents space-separated).
meta=$(git_in "$repo_dir" log -1 "$hash" \
    --format='%an%x09%ae%x09%ci%x09%P%x09%s' 2>/dev/null)
saved_ifs=$IFS
IFS=$'\t'
set -- $meta
author=${1:-}
email=${2:-}
date=${3:-}
parents_raw=${4:-}
subject=${5:-}
IFS=$saved_ifs

# Body (everything after the subject) via separate call - %b only.
body=$(git_in "$repo_dir" log -1 "$hash" --format='%b' 2>/dev/null \
    | /ffp/bin/awk '
        BEGIN { ORS = ""; first = 1 }
        {
            gsub(/\\/, "\\\\"); gsub(/"/, "\\\"");
            gsub(/\t/, "\\t"); gsub(/\r/, "");
            if (!first) print "\\n";
            first = 0;
            print $0;
        }')

# --stat + diff: capture via gawk JSON-escape. We use diff-tree (not show)
# because git 1.7.8's `show --format=` still prints commit headers - diff-tree
# starts with the bare hash on line 1 which awk's NR==1 skip drops cleanly.
escape_to_json_var() {
    /ffp/bin/awk '
        BEGIN { ORS = ""; first = 1 }
        NR == 1 { next }   # skip diff-tree leading hash line
        {
            gsub(/\\/, "\\\\"); gsub(/"/, "\\\"");
            gsub(/\t/, "\\t"); gsub(/\r/, "");
            if (!first) print "\\n";
            first = 0;
            print $0;
        }'
}

stat_esc=$(git_in "$repo_dir" diff-tree --stat --root --no-color "$hash" 2>/dev/null | escape_to_json_var)
diff_esc=$(git_in "$repo_dir" diff-tree -p --root --no-color "$hash" 2>/dev/null | escape_to_json_var)

# Parents JSON array.
parents_json='['
if [ -n "$parents_raw" ]; then
    pfirst=1
    for p in $parents_raw; do
        [ $pfirst -eq 0 ] && parents_json="$parents_json,"
        pfirst=0
        parents_json="$parents_json\"$(json_escape_value "$p")\""
    done
fi
parents_json="$parents_json]"

emit_headers
printf '{'
printf '"hash":"%s",'         "$(json_escape_value "$hash")"
printf '"short":"%s",'        "$(json_escape_value "$short")"
printf '"author":"%s",'       "$(json_escape_value "$author")"
printf '"author_email":"%s",' "$(json_escape_value "$email")"
printf '"date":"%s",'         "$(json_escape_value "$date")"
printf '"subject":"%s",'      "$(json_escape_value "$subject")"
printf '"body":"%s",'         "$body"
printf '"parents":%s,'        "$parents_json"
printf '"stat":"%s",'         "$stat_esc"
printf '"diff":"%s"'          "$diff_esc"
printf '}\n'
