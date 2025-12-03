# scraper.py
# Run this hourly (GitHub Actions will run it). It produces data/data.json

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
VMAN_KEYWORDS = ["viman nagar", "vimannagar", "viman_nagar", "viman-nagar", "viman"]

INSTAGRAM_TAGS = [
    "vimannagar", "viman_nagar", "vimannagarpune", "viman_nagar_pune", "vimannagarnews",
    "vimannagarissues", "vimannagarproblems", "puneproblems", "puneissues", "punegarbage"
]

NEWS_PAGES = [
    "https://timesofindia.indiatimes.com/city/pune",
    "https://punemirror.com",
    "https://www.lokmat.com/pune/"
]

def mentions_viman(text):
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in VMAN_KEYWORDS)

def classify(text):
    t = (text or "").lower()
    if any(w in t for w in ["garbage", "trash", "waste", "sweeper", "bin", "dump"]):
        return "Garbage"
    if any(w in t for w in ["light", "streetlight", "no light", "dark", "flicker", "lamp post"]):
        return "Streetlights"
    if any(w in t for w in ["bus", "pmpml", "delay", "missed", "bus stop"]):
        return "Bus Delays"
    if any(w in t for w in ["rob", "theft", "attack", "harass", "unsafe", "snatch"]):
        return "Safety"
    return "Social Media"

def fetch_pmc():
    results = []
    urls = [
        "https://sanitation.vdiscovery.in/api/complaints?city=Pune",
        "https://sanitation.vdiscovery.in/api/complaints"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
            elif isinstance(data, list):
                items = data
            else:
                items = []
                for v in data.values():
                    if isinstance(v, list):
                        items = v
                        break
            for it in items:
                addr = it.get("address") or it.get("location") or ""
                desc = it.get("complaint_remarks") or it.get("remarks") or it.get("complaint_type") or ""
                title = it.get("title") or ""
                text = " ".join([str(title), str(desc), str(addr)])
                if mentions_viman(text):
                    lat = it.get("latitude") or it.get("lat") or None
                    lon = it.get("longitude") or it.get("lon") or None
                    try:
                        lat = float(lat) if lat else None
                        lon = float(lon) if lon else None
                    except:
                        lat, lon = None, None
                    results.append({
                        "Category": classify(text),
                        "Description": text,
                        "Source": "PMC",
                        "lat": lat,
                        "lon": lon,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            if results:
                return results
        except Exception:
            continue
    return results

def fetch_reddit(limit=80):
    url = f"https://www.reddit.com/r/pune/new.json?limit={limit}"
    results = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", {}).get("children", []):
                d = item.get("data", {})
                full = (d.get("title") or "") + " " + (d.get("selftext") or "")
                if mentions_viman(full):
                    results.append({
                        "Category": classify(full),
                        "Description": full,
                        "Source": "Reddit",
                        "lat": None,
                        "lon": None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
    except Exception:
        pass
    return results

def fetch_instagram(tags, max_per_tag=5):
    results = []
    for tag in tags:
        try:
            url = f"https://www.instagram.com/explore/tags/{tag}/"
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            meta = soup.find("meta", property="og:description")
            if meta and meta.get("content"):
                cont = meta.get("content")
                if mentions_viman(cont):
                    results.append({
                        "Category": classify(cont),
                        "Description": cont,
                        "Source": f"Instagram #{tag}",
                        "lat": None,
                        "lon": None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            # image alt texts
            alts = [img.get("alt") for img in soup.find_all("img") if img.get("alt")]
            added = 0
            for alt in alts:
                if added >= max_per_tag:
                    break
                if mentions_viman(alt):
                    results.append({
                        "Category": classify(alt),
                        "Description": alt,
                        "Source": f"Instagram #{tag}",
                        "lat": None,
                        "lon": None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    added += 1
        except Exception:
            continue
    return results

def fetch_news():
    results = []
    for url in NEWS_PAGES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            text = r.text
            # find sentences with viman nagar
            hits = re.findall(r'([^.?!]{20,200}?(?:viman nagar|vimannagar)[^.?!]{0,200})', text, flags=re.I)
            for h in hits:
                clean = " ".join(h.split())
                results.append({
                    "Category": classify(clean),
                    "Description": clean,
                    "Source": "News",
                    "lat": None,
                    "lon": None,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception:
            continue
    return results

def main():
    all_records = []
    all_records.extend(fetch_pmc())
    all_records.extend(fetch_reddit())
    all_records.extend(fetch_instagram(INSTAGRAM_TAGS, max_per_tag=4))
    all_records.extend(fetch_news())

    # Deduplicate by description text
    seen = set()
    dedup = []
    for r in all_records:
        key = (r.get("Description","").strip()[:200])
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        dedup.append(r)

    # Save file
    out_path = "data/data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(dedup)} records to {out_path}")

if __name__ == "__main__":
    main()
