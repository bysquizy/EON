"""Hardware detection: picks safe defaults so EON runs well on weak and strong PCs alike.

Nothing is installed or downloaded here; this only reads RAM and CPU core count locally.
"""
from __future__ import annotations

import os

TIERS = {
    "low": {"label": "Düşük kaynak", "context": 2048, "keep_alive": "0",
            "note": "Az RAM veya az çekirdek: bellek tasarruflu ayarlar, model yanıttan sonra hemen boşaltılır."},
    "balanced": {"label": "Dengeli", "context": 4096, "keep_alive": "3m",
                 "note": "Çoğu bilgisayar için hız ve bellek dengesi."},
    "high": {"label": "Güçlü", "context": 8192, "keep_alive": "5m",
             "note": "Bol RAM: geniş bağlam ve model bellekte biraz daha uzun tutulur."},
}

# Yaklaşık indirme boyutları (Ollama kütüphanesi); gerçek değer sürüme göre değişebilir.
MODELS = {
    "low": [("llama3.2:1b", "~1,3 GB", "Çok hafif ve hızlı"),
            ("gemma3:1b", "~0,8 GB", "En küçük, düşük RAM için")],
    "balanced": [("qwen3:4b", "~2,5 GB", "Genel kullanım için iyi denge"),
                 ("gemma3:4b", "~3,3 GB", "Çok dilli, kaliteli yanıtlar"),
                 ("llama3.2:3b", "~2 GB", "Hızlı ve hafif")],
    "high": [("qwen3:8b", "~5,2 GB", "Güçlü genel model"),
             ("gemma3:12b", "~8 GB", "Yüksek kalite, 16 GB RAM önerilir"),
             ("qwen3:14b", "~9 GB", "En yüksek kalite, 16 GB+ RAM")],
}


def pick_tier(ram_bytes, cores) -> str:
    if not isinstance(ram_bytes, (int, float)) or ram_bytes <= 0:
        return "balanced"
    gb = ram_bytes / 1073741824
    if gb < 6.5 or (isinstance(cores, int) and cores <= 2):
        return "low"
    if gb < 24:
        return "balanced"
    return "high"


def detect(ram_bytes=None, cores=None) -> dict:
    """Return the machine profile. Arguments exist only so tests can inject values."""
    if ram_bytes is None:
        from .productivity import system_memory_info
        ram_bytes = system_memory_info().get("total_bytes")
    if cores is None:
        cores = os.cpu_count() or 2
    tier = pick_tier(ram_bytes, cores)
    spec = TIERS[tier]
    models = list(MODELS[tier])
    if tier == "balanced" and ram_bytes and ram_bytes / 1073741824 >= 12:
        models.append(("qwen3:8b", "~5,2 GB", "12 GB+ RAM için daha güçlü seçenek"))
    return {
        "tier": tier,
        "label": spec["label"],
        "note": spec["note"],
        "ram_gb": round(ram_bytes / 1073741824, 1) if ram_bytes else None,
        "cores": cores,
        "defaults": {"context": spec["context"], "keep_alive": spec["keep_alive"]},
        "models": [{"name": n, "size": s, "why": w} for n, s, w in models],
    }
