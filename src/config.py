"""Carga del config.yaml con validación temprana.

Un error de configuración debe fallar aquí, con un mensaje claro, y no
tres módulos más adelante con un KeyError incomprensible.
"""
from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_TOP = ["owner", "delivery", "universe", "fred_series", "feeds", "scoring", "model", "movers"]
ASSET_BUCKETS = ["indices", "etfs_regionales", "etfs_sectoriales", "renta_fija",
                 "commodities", "fx", "acciones_vigiladas"]


class ConfigError(Exception):
    pass


def load(path: str = "config.yaml") -> dict:
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(full):
        raise ConfigError(f"No encuentro {full}. ¿Estás corriendo desde la raíz del proyecto?")
    with open(full, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    missing = [k for k in REQUIRED_TOP if k not in cfg]
    if missing:
        raise ConfigError(f"Faltan secciones en config.yaml: {', '.join(missing)}")

    for bucket in ASSET_BUCKETS:
        for asset in cfg["universe"].get(bucket, []):
            if "t" not in asset or "n" not in asset:
                raise ConfigError(f"Activo mal definido en universe.{bucket}: {asset} "
                                  "(necesita 't' = ticker y 'n' = nombre)")

    for feed in cfg["feeds"]:
        if not feed.get("u", "").startswith("http"):
            raise ConfigError(f"Feed sin URL válida: {feed.get('n')}")

    # normaliza claves de tier a enteros (YAML puede leerlas como str)
    cfg["scoring"]["tier_weight"] = {int(k): float(v)
                                     for k, v in cfg["scoring"]["tier_weight"].items()}
    return cfg


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v


def all_assets(cfg: dict) -> list[dict]:
    """Aplana el universo en una sola lista con su bucket de origen."""
    out = []
    for bucket in ASSET_BUCKETS:
        for a in cfg["universe"].get(bucket, []):
            out.append({**a, "bucket": bucket})
    return out
