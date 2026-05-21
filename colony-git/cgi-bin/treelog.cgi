#!/ffp/bin/bash
# GET /colony-git/api/treelog?name=<repo>&ref=<ref>&path=<path>
# Same shape as tree.cgi but each entry also carries the LAST commit that
# touched it (or any descendant for trees).
#
# Output:
#   {
#     "ref":"master","path":"src",
#     "entries":[
#       {"name":"hello.py","type":"blob","mode":"100644","hash":"...","size":31,
#        "last_commit":{"hash":"26fe14","ts":1747767365,
#                       "author":"Lin","subject":"add test.txt"}}
#     ]
#   }
#
# Implementation: stream `git log <ref> --name-only` ONCE through awk,
# emitting one (top_entry, hash, ts, author, subject) line per top-level
# entry whose path appears under <path>/. We keep the FIRST occurrence
# (= newest, since log is reverse-chronological). Bash 4 associative array
# turns that into O(1) lookups in the ls-tree loop. Total cost: one git log
# + one ls-tree + bash assoc-array, vs. N git-log calls in the naive variant.

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
path=$(sanitize_path "$(qs_get path)")
repo_dir=$(resolve_repo "$name")

if [ -n "$path" ]; then
    target="${ref}:${path}/"
    prefix="${path}/"
else
    target="$ref"
    prefix=""
fi

CMAP="$REPOS_ROOT/.colony-git-cmap-$$"
trap 'rm -f "$CMAP"' EXIT

# Stream git log; awk emits one line per top-level entry under prefix.
# Field separator is TAB. Subject may contain TABs but git collapses them
# in single-line %s output - safe enough.
#
# Hard cap on commits walked: large/old repos with stable file sets touch
# their root entries within the recent N commits; walking ALL history is
# wasted work on ARMv5. Entries not touched in window stay last_commit:null
# (frontend renders blank time/msg gracefully).
HISTORY_LIMIT=${COLONY_GIT_TREELOG_LIMIT:-2000}
if [ -n "$path" ]; then
    log_cmd_path=( -- "$path" )
else
    log_cmd_path=()
fi

# bash 4.1 + set -u + empty array workaround: ${arr[@]+"${arr[@]}"}
git_in "$repo_dir" log "$ref" -n "$HISTORY_LIMIT" \
    --pretty=tformat:'>%h%x09%ct%x09%an%x09%s' \
    --name-only -m --no-renames \
    ${log_cmd_path[@]+"${log_cmd_path[@]}"} 2>/dev/null \
| /ffp/bin/awk -F'\t' -v prefix="$prefix" '
    BEGIN { commit=""; ts=""; auth=""; subj=""; }
    /^>/ {
        commit = substr($1, 2);
        ts     = $2;
        auth   = $3;
        # Subject may itself contain tabs from %s if the original message
        # had them, so glue fields 4..NF back together.
        subj = $4;
        for (i = 5; i <= NF; i++) subj = subj "\t" $i;
        next;
    }
    /^$/ { next }
    {
        p = $0;
        if (prefix != "") {
            if (substr(p, 1, length(prefix)) != prefix) next;
            p = substr(p, length(prefix)+1);
        }
        n = index(p, "/");
        top = (n > 0) ? substr(p, 1, n-1) : p;
        if (top == "") next;
        if (!(top in seen)) {
            seen[top] = commit "\t" ts "\t" auth "\t" subj;
        }
    }
    END {
        for (k in seen) print k "\t" seen[k];
    }
' > "$CMAP"

# Load commit map into bash assoc array.
declare -A LC_HASH LC_TS LC_AUTH LC_SUBJ
while IFS=$'\t' read -r nm hash tsval author subject; do
    [ -z "$nm" ] && continue
    LC_HASH[$nm]=$hash
    LC_TS[$nm]=$tsval
    LC_AUTH[$nm]=$author
    LC_SUBJ[$nm]=$subject
done < "$CMAP"

emit_headers
printf '{"ref":"%s","path":"%s","entries":[' \
    "$(json_escape_value "$ref")" \
    "$(json_escape_value "$path")"

first=1
git_in "$repo_dir" ls-tree -l "$target" 2>/dev/null | while read -r mode type hash size_and_name; do
    [ -z "$mode" ] && continue
    size=${size_and_name%%$'\t'*}
    fname=${size_and_name#*$'\t'}
    while [ "${size:0:1}" = " " ]; do size=${size:1}; done

    [ $first -eq 0 ] && printf ','
    first=0
    printf '{'
    printf '"name":"%s",'  "$(json_escape_value "$fname")"
    printf '"type":"%s",'  "$(json_escape_value "$type")"
    printf '"mode":"%s",'  "$(json_escape_value "$mode")"
    printf '"hash":"%s",'  "$(json_escape_value "$hash")"
    if [ "$type" = "blob" ] && [ "$size" != "-" ] && [ -n "$size" ]; then
        printf '"size":%d,'  "$size"
    else
        printf '"size":null,'
    fi

    lc_hash=${LC_HASH[$fname]:-}
    if [ -n "$lc_hash" ]; then
        printf '"last_commit":{"hash":"%s","ts":%d,"author":"%s","subject":"%s"}' \
            "$(json_escape_value "$lc_hash")" \
            "${LC_TS[$fname]:-0}" \
            "$(json_escape_value "${LC_AUTH[$fname]:-}")" \
            "$(json_escape_value "${LC_SUBJ[$fname]:-}")"
    else
        printf '"last_commit":null'
    fi
    printf '}'
done

printf ']}\n'
