#!/ffp/bin/bash
# GET /colony-git/api/tree?name=<repo>&ref=<ref>&path=<path>
# Lists tree entries at <path> for <ref>. Path empty = repo root.
# Output:
#   {
#     "ref":"master","path":"src/foo",
#     "entries":[
#       {"name":"bar.rs","type":"blob","mode":"100644","hash":"...","size":1234},
#       {"name":"baz",   "type":"tree","mode":"040000","hash":"...","size":null}
#     ]
#   }

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
path=$(sanitize_path "$(qs_get path)")
repo_dir=$(resolve_repo "$name")

# Build the ls-tree target: ref:path/ if path is non-empty, ref otherwise.
# Trailing slash on path tells ls-tree to list the directory's contents
# rather than the directory entry itself.
if [ -n "$path" ]; then
    target="${ref}:${path}/"
    # strip any double-slash artifacts
    target=${target//\/\//\/}
else
    target="$ref"
fi

emit_headers
printf '{"ref":"%s","path":"%s","entries":[' \
    "$(json_escape_value "$ref")" \
    "$(json_escape_value "$path")"

# git ls-tree -l format: <mode> SP <type> SP <object> <TAB> <size>|"-" <TAB> <file>
# git 1.7.8 outputs size right-aligned padded; trim it.
first=1
git_in "$repo_dir" ls-tree -l "$target" 2>/dev/null | while read -r mode type hash size_and_name; do
    [ -z "$mode" ] && continue
    # size_and_name = "<size>\t<file>" where size may be "-" for non-blob.
    size=${size_and_name%%$'\t'*}
    fname=${size_and_name#*$'\t'}
    # trim leading whitespace from size
    size=${size##*( )}
    size=${size## }
    while [ "${size:0:1}" = " " ]; do size=${size:1}; done

    [ $first -eq 0 ] && printf ','
    first=0

    printf '{'
    printf '"name":"%s",' "$(json_escape_value "$fname")"
    printf '"type":"%s",' "$(json_escape_value "$type")"
    printf '"mode":"%s",' "$(json_escape_value "$mode")"
    printf '"hash":"%s",' "$(json_escape_value "$hash")"
    if [ "$type" = "blob" ] && [ "$size" != "-" ] && [ -n "$size" ]; then
        printf '"size":%d'  "$size"
    else
        printf '"size":null'
    fi
    printf '}'
done

printf ']}\n'
