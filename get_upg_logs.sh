#! /bin/bash
# Downloads all last tracebacks from requests
# Feel free to modify the request filters, count etc.
# The full curl command can be taken from the website, with right-click on the JSON from the request and selecting "Copy of cURL"

DIR_NAME="tracebacks_archive"
TMP_FILE="$(mktemp -t "XXXtracebacks.txt")"

mkdir -p "$DIR_NAME" || exit 1
cd "$DIR_NAME"

# 1. Get cookie from Firefox
# Firefox locks cookies database, so we first need to copy it.
# Need to have sqlite3 installed
# COOKIES="cooked.sqlite"
# cp ~/.mozilla/firefox/*.default-release/cookies.sqlite "$COOKIES"
# sess_id=$(sqlite3 "$COOKIES" 'SELECT * FROM moz_cookies WHERE host="upgrade.odoo.com";' | cut -d '|' -f 4)
# rm "$COOKIES"
sess_id="123456789"

# 2. Get logs
LIMIT=1000

curl --silent 'https://upgrade.odoo.com/web/dataset/search_read' -X POST -H 'Content-Type: application/json' -H 'Cookie: session_id='$sess_id'; frontend_lang=en_US; tz=Europe/Brussels' -H 'Sec-Fetch-Site: same-origin' --data-raw '{"jsonrpc":"2.0","method":"call","params":{"model":"upgrade.request","domain":["&", "&", "&", "&", ["state", "=", "done"], ["version_origin", "ilike","saas~16.1"], ["disabled_view_count",">",0],["actuator", "=", "meta"],["state","=","done"]],"fields":["id", "log_file_url", "contract" ],"limit":'$LIMIT',"sort":""}}' | jq '.result.records[]' > "$TMP_FILE"

# 3. Split tracebacks into separate files
awk '
/^\s+"id"/ {upreq_id = substr($2, 1, length($2)-1)}
/:/ {print $0 > upreq_id".txt"}
' "$TMP_FILE"

rm "$TMP_FILE"

# 4. Print newlines in-file
for file in *.txt; do
    sed -i 's/\\n/\n/g' $file
    cat $file | grep "log_file_url" | awk '{print $2}' | awk -F, '{print $1}'
    cat $file | grep "log_file_url" | awk '{print $2}' | awk -F, '{print $1}' | xargs -I {} wget {} -q -O $file
done