import json, sys

FILE = sys.argv[1] if len(sys.argv) > 1 else "computo_snapshots.json"

with open(FILE, encoding='utf-8') as f:
    snaps = json.load(f)

print(f"{'time':<8} {'actas%':<8} {'A-UPP%':<9} {'APB%':<8} {'MTS%':<7} {'marg_AUPP':<11} {'marg_APB'}")
print("-" * 72)

for s in snaps:
    t = s.get("server_fecha", s["timestamp"])[-8:-3]
    actas = s.get("pct_actas") or 0
    aupp = s["partidos"].get("A-UPP", {}).get("pct") or 0
    apb  = s["partidos"].get("APB-SUMATE", {}).get("pct") or 0
    mts  = s["partidos"].get("MTS", {}).get("pct") or 0
    d = s.get("delta", {})
    m_aupp = d.get("A-UPP", {}).get("marginal_pct")
    m_apb  = d.get("APB-SUMATE", {}).get("marginal_pct")
    m_aupp_s = f"{m_aupp:.2f}%" if m_aupp else "—"
    m_apb_s  = f"{m_apb:.2f}%"  if m_apb  else "—"
    print(f"{t:<8} {actas:<8.2f} {aupp:<9.3f} {apb:<8.3f} {mts:<7.3f} {m_aupp_s:<11} {m_apb_s}")

# Summary
valid_margs = [s["delta"]["A-UPP"]["marginal_pct"] for s in snaps if s.get("delta", {}).get("A-UPP", {}).get("marginal_pct")]
if valid_margs:
    avg = sum(valid_margs) / len(valid_margs)
    avg4 = sum(valid_margs[-4:]) / min(4, len(valid_margs))
    last = snaps[-1]
    last_votos = last["votos_validos"]
    last_actas = last["actas_computadas"]
    last_aupp  = last["partidos"]["A-UPP"]["votos"]
    total_actas = last["actas_habilitadas"]
    vpa = last_votos / last_actas
    rem = (total_actas - last_actas) * vpa
    needed = (0.40 * (last_votos + rem) - last_aupp) / rem * 100
    proj_avg  = (last_aupp + avg/100  * rem) / (last_votos + rem) * 100
    proj_rec  = (last_aupp + avg4/100 * rem) / (last_votos + rem) * 100
    print(f"\n--- proyección ---")
    print(f"tasa necesaria : {needed:.3f}%")
    print(f"media total    : {avg:.3f}%  → proyección: {proj_avg:.3f}%")
    print(f"media últimas 4: {avg4:.3f}%  → proyección: {proj_rec:.3f}%")
    print(f"actas restantes: {total_actas - last_actas}")