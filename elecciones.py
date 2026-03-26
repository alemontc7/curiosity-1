import os
import json
import time
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("ENDPOINT")
INTERVAL = int(os.getenv("INTERVAL_SECONDS", "300"))  # default 5 min
DURATION = int(os.getenv("DURATION_SECONDS", "18000")) # default 1 hour
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "computo_snapshots.json")

def get_cookie():
    """Always reads fresh from .env — update .env when cookie expires."""
    load_dotenv(override=True)
    return os.getenv("COOKIE")

def fetch_snapshot(session: requests.Session) -> dict | None:
    cookie = get_cookie()
    if not cookie:
        print("  [ERROR] No COOKIE found in .env")
        return None

    headers = {
        "Cookie": cookie,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://computo.oep.org.bo/",
    }

    try:
        r = session.get(ENDPOINT, headers=headers, timeout=15)

        if r.status_code == 403 or r.status_code == 401:
            print(f"  [AUTH ERROR] {r.status_code} — update COOKIE in .env and press Enter to retry...")
            input()
            return fetch_snapshot(session)  # retry with fresh cookie

        if r.status_code != 200:
            print(f"  [HTTP ERROR] {r.status_code} — skipping this snapshot")
            return None

        data = r.json()
        return data

    except requests.exceptions.Timeout:
        print("  [TIMEOUT] Request timed out — skipping")
        return None
    except requests.exceptions.JSONDecodeError:
        print("  [PARSE ERROR] Response is not valid JSON — skipping")
        return None
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
        return None

def extract_summary(raw: dict) -> dict:
    """Flatten the nested JSON into a clean flat dict for easy analysis."""
    snapshot = {
        "timestamp": datetime.datetime.now().isoformat(),
        "server_fecha": raw.get("fecha"),
    }

    # Tabla (aggregate stats)
    for row in raw.get("tabla", []):
        key = row["nombre"].strip().lower().replace(" ", "_")
        snapshot[f"tabla_{key}"] = {
            "valor": row.get("valor"),
            "porcentaje": row.get("porcentaje"),
        }

    # Extract key scalars for quick access
    tabla = {r["nombre"].strip(): r for r in raw.get("tabla", [])}
    snapshot["actas_computadas"]  = tabla.get("Total Actas Computadas",  {}).get("valor")
    snapshot["actas_habilitadas"] = tabla.get("Total Actas Habilitadas", {}).get("valor")
    snapshot["pct_actas"]         = tabla.get("Total Actas Computadas",  {}).get("porcentaje")
    snapshot["votos_validos"]     = tabla.get("Votos Válidos",           {}).get("valor")

    # Grafica (per-party results)
    snapshot["partidos"] = {}
    for party in raw.get("grafica", []):
        sigla = party.get("sigla", "").strip()
        if not sigla:
            continue
        snapshot["partidos"][sigla] = {
            "nombre": party.get("nombre", "").strip(),
            "votos": party.get("valor"),
            "pct": party.get("porcien"),
        }

    return snapshot

def compute_delta(prev: dict, curr: dict) -> dict:
    """Compute marginal vote share between two snapshots."""
    if not prev or not curr:
        return {}

    delta = {}
    prev_valid = prev.get("votos_validos", 0) or 0
    curr_valid = curr.get("votos_validos", 0) or 0
    new_valid = curr_valid - prev_valid

    if new_valid <= 0:
        return {"new_valid_votes": 0}

    delta["new_valid_votes"] = new_valid
    delta["new_actas"] = (curr.get("actas_computadas") or 0) - (prev.get("actas_computadas") or 0)

    for sigla, curr_party in curr.get("partidos", {}).items():
        prev_party = prev.get("partidos", {}).get(sigla, {})
        curr_votos = curr_party.get("votos") or 0
        prev_votos = prev_party.get("votos") or 0
        new_votos = curr_votos - prev_votos
        marginal_pct = (new_votos / new_valid * 100) if new_valid > 0 else None
        delta[sigla] = {
            "new_votes": new_votos,
            "marginal_pct": round(marginal_pct, 4) if marginal_pct is not None else None,
        }

    return delta

def save(snapshots: list, output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2)

def main():
    print(f"Computo poller starting")
    print(f"  Endpoint : {ENDPOINT}")
    print(f"  Interval : {INTERVAL}s")
    print(f"  Duration : {DURATION}s (~{DURATION//60} min)")
    print(f"  Output   : {OUTPUT_FILE}")
    print()

    output_path = Path(OUTPUT_FILE)
    # Load existing data if resuming
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            snapshots = json.load(f)
        print(f"  Resuming — loaded {len(snapshots)} existing snapshots")
    else:
        snapshots = []

    session = requests.Session()
    start_time = time.time()
    poll_count = 0
    no_change_streak = 0

    while time.time() - start_time < DURATION:
        poll_count += 1
        now = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = int(time.time() - start_time)
        remaining = DURATION - elapsed
        print(f"[{now}] Poll #{poll_count} — {elapsed}s elapsed, {remaining}s remaining")

        raw = fetch_snapshot(session)

        if raw:
            summary = extract_summary(raw)
            prev = snapshots[-1] if snapshots else None
            summary["delta"] = compute_delta(prev, summary)

            new_votes = summary["delta"].get("new_valid_votes", -1)
            if new_votes == 0:
                no_change_streak += 1
                print(f"  [NO CHANGE] streak {no_change_streak}/3")
                if no_change_streak >= 3:
                    print("  [EXIT] 3 consecutive snapshots with no new votes — cómputo detenido.")
                    save(snapshots, OUTPUT_FILE)
                    return
            else:
                no_change_streak = 0

            snapshots.append(summary)
            save(snapshots, OUTPUT_FILE)

            # Print quick status
            aupp = summary["partidos"].get("A-UPP", {})
            apb  = summary["partidos"].get("APB-SUMATE", {})
            marg = summary["delta"].get("A-UPP", {}).get("marginal_pct")
            print(f"  Actas: {summary['actas_computadas']}/{summary['actas_habilitadas']} "
                  f"({summary['pct_actas']}%)")
            print(f"  A-UPP: {aupp.get('votos'):,} ({aupp.get('pct')}%) | "
                  f"APB: {apb.get('votos'):,} ({apb.get('pct')}%)")
            if marg is not None:
                flag = " <-- ABOVE AVG" if marg > 41.5 else ""
                print(f"  Marginal A-UPP this interval: {marg:.3f}%{flag}")
        else:
            print("  No data this poll — will retry next interval")

        print()

        # Sleep in small chunks so Ctrl+C is responsive
        sleep_until = time.time() + INTERVAL
        while time.time() < sleep_until and time.time() - start_time < DURATION:
            time.sleep(1)

    print(f"Done. {len(snapshots)} snapshots saved to {OUTPUT_FILE}")
    print("Paste the contents of that file here for full analysis.")

if __name__ == "__main__":
    main()