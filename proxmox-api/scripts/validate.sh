#!/usr/bin/env bash
# ============================================================
#  ProxAPI - Script de validation
#  Usage : ./validate.sh [BASE_URL] [USER] [PASSWORD] [VMID]
#  Ex    : ./validate.sh http://192.168.1.200:8080 root@pam secret 100
# ============================================================

BASE="${1:-http://localhost:8080}/api/v1"
PX_USER="${2:-root@pam}"
PX_PASS="${3:-votre_mot_de_passe}"
VMID="${4:-100}"
PASS=0; FAIL=0

GREEN="\033[0;32m"; RED="\033[0;31m"; CYAN="\033[0;36m"; NC="\033[0m"

ok()    { echo -e "${GREEN}  ✅ PASS${NC} - $1"; ((PASS++)); }
fail()  { echo -e "${RED}  ❌ FAIL${NC} - $1  →  $2"; ((FAIL++)); }
title() { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

check() {
    local r="$1" field="$2" label="$3"
    echo "$r" | grep -q "\"$field\"" && ok "$label" || fail "$label" "$r"
}

title "Health"
R=$(curl -sf "$BASE/health")
check "$R" "status" "GET /health"

title "Auth"
R=$(curl -sf -X POST "$BASE/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$PX_USER\",\"password\":\"$PX_PASS\"}")
check "$R" "access_token" "POST /login"
TOKEN=$(echo "$R" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Token absent - vérifier les credentials Proxmox${NC}"; exit 1
fi
AUTH="Authorization: Bearer $TOKEN"

title "Nœuds"
R=$(curl -sf -H "$AUTH" "$BASE/nodes")
echo "$R" | grep -q "\[" && ok "GET /nodes" || fail "GET /nodes" "$R"

title "VMs"
R=$(curl -sf -H "$AUTH" "$BASE/vms")
echo "$R" | grep -q "\[" && ok "GET /vms (liste)" || fail "GET /vms" "$R"

R=$(curl -sf -H "$AUTH" "$BASE/vms/$VMID")
check "$R" "name" "GET /vms/$VMID (détail)"

R=$(curl -sf -H "$AUTH" "$BASE/vms/$VMID/status")
check "$R" "status" "GET /vms/$VMID/status"

title "Recherche"
R=$(curl -sf -H "$AUTH" "$BASE/vms/search?status=stopped")
echo "$R" | grep -q "\[" && ok "GET /vms/search?status=stopped" || fail "search status" "$R"

R=$(curl -sf -H "$AUTH" "$BASE/vms/search?min_cpu=1")
echo "$R" | grep -q "\[" && ok "GET /vms/search?min_cpu=1" || fail "search min_cpu" "$R"

title "Snapshots"
R=$(curl -sf -H "$AUTH" "$BASE/vms/$VMID/snapshots")
echo "$R" | grep -q "\[" && ok "GET /vms/$VMID/snapshots" || fail "list snapshots" "$R"

R=$(curl -sf -X POST "$BASE/vms/$VMID/snapshots" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"snapname":"test-proxapi","description":"Snapshot validation script"}')
check "$R" "message" "POST /vms/$VMID/snapshots (create)"

R=$(curl -sf -X DELETE -H "$AUTH" "$BASE/vms/$VMID/snapshots/test-proxapi")
check "$R" "message" "DELETE /vms/$VMID/snapshots/test-proxapi"

title "Docs"
R=$(curl -sf "$(echo $BASE | sed 's|/api/v1||')/api/docs" -o /dev/null -w "%{http_code}")
[ "$R" = "200" ] && ok "GET /api/docs (Swagger)" || fail "Swagger inaccessible" "HTTP $R"

TOTAL=$((PASS+FAIL))
echo -e "\n${CYAN}━━━ Résultats ━━━${NC}"
echo -e "  Total : $TOTAL  |  ${GREEN}OK : $PASS${NC}  |  ${RED}KO : $FAIL${NC}"
[ $FAIL -eq 0 ] \
    && echo -e "\n${GREEN}✅ Tous les tests passent !${NC}\n" \
    || echo -e "\n${RED}❌ $FAIL test(s) en échec.${NC}\n"
