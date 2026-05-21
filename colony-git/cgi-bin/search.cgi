#!/ffp/bin/bash
# GET /colony-git/api/search?name=<repo>&ref=<ref>
# Returns the full flat list of file paths reachable from <ref> for the
# "Go to file" client-side fuzzy filter.
#
# Output:
#   {"ref":"master","paths":["README.md","src/hello.py","src/test.txt"]}

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
repo_dir=$(resolve_repo "$name")

emit_headers
printf '{"ref":"%s","paths":[' "$(json_escape_value "$ref")"

first=1
git_in "$repo_dir" ls-tree -r --name-only "$ref" 2>/dev/null | while read -r p; do
    [ -z "$p" ] && continue
    [ $first -eq 0 ] && printf ','
    first=0
    printf '"%s"' "$(json_escape_value "$p")"
done

printf ']}\n'
