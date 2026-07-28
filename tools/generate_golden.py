"""Regenerate tests/golden/*.json.

Run through ``make golden``. Read the resulting diff before committing it — these files are
what the calling backend's cached charts were produced from.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from conftest import AS_OF, BIRTHS, BIRTHS_BY_KEY  # noqa: E402

from wrappers import chart, compat, dasha, panchanga, strength, yoga  # noqa: E402

PARTNER = BIRTHS_BY_KEY["busan_1978"]
GOLDEN_DIR = ROOT / "tests" / "golden"


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for birth in BIRTHS:
        yogas = yoga.compute(birth.utc, birth.lat, birth.lon)
        payload = {
            "note": birth.note,
            "input": {"utc": birth.utc.isoformat(), "lat": birth.lat, "lon": birth.lon},
            "chart": chart.compute(birth.utc, birth.lat, birth.lon),
            "dasha": dasha.compute(birth.utc, birth.lat, birth.lon, as_of=AS_OF),
            "panchanga": panchanga.compute(birth.utc, birth.lat, birth.lon),
            "strength": strength.compute(birth.utc, birth.lat, birth.lon),
            "compat_vs_busan_1978": compat.compute(
                birth.utc, birth.lat, birth.lon, PARTNER.utc, PARTNER.lat, PARTNER.lon
            ),
            "yoga": {
                "detected_count": yogas["detected_count"],
                "checked_count": yogas["checked_count"],
                "keys": [item["key"] for item in yogas["yogas"]],
            },
        }
        target = GOLDEN_DIR / f"{birth.key}.json"
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
