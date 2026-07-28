"""Fixed calculation parameters — the single source of truth for this engine.

Everything here is deliberately hard-coded. The engine exposes no switches for ayanamsa or
dasha system: a chart computed today and the same chart recomputed in two years must match,
and callers cache results keyed by ``engine_version``. If a parameter below ever changes,
``ENGINE_VERSION`` must change with it.
"""

from __future__ import annotations

ENGINE_VERSION = "0.1.0"

#: Sidereal zero point. ``AYANAMSA_MODE`` is the PyJHora/Swiss Ephemeris identifier,
#: ``AYANAMSA`` is the lowercase name echoed in every response.
AYANAMSA = "lahiri"
AYANAMSA_MODE = "LAHIRI"

#: Dasha system. Vimshottari runs a 120-year cycle keyed to the Moon's nakshatra.
DASHA_SYSTEM = "vimshottari"
DASHA_CYCLE_YEARS = 120

#: Coordinate system: sidereal (fixed stars), not tropical.
ZODIAC = "sidereal"

#: The engine accepts UTC instants only. It has no timezone database and no opinion about
#: local time — resolving a birthplace to a UTC instant is entirely the caller's job.
TIME_BASIS = "utc"

# --- naming -----------------------------------------------------------------

#: Planet ids as used by PyJHora chart rows. 7 classical planets + the two lunar nodes.
PLANET_NAMES: dict[int, str] = {
    0: "Sun",
    1: "Moon",
    2: "Mars",
    3: "Mercury",
    4: "Jupiter",
    5: "Venus",
    6: "Saturn",
    7: "Rahu",
    8: "Ketu",
}

#: Planets that Shadbala is defined for (the nodes have no Shadbala).
SHADBALA_PLANETS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)

SIGN_NAMES: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

#: 27 nakshatras in standard Sanskrit spelling, index 0 = Ashwini.
#: PyJHora ships Tamil transliterations ("Karthigai" for Krittika); responses carry the
#: 1-based number as the stable key, and these names for readability.
NAKSHATRA_NAMES: tuple[str, ...] = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)

#: Vimshottari mahadasha lengths in years, keyed by planet id. Sums to 120.
VIMSHOTTARI_YEARS: dict[int, int] = {
    0: 6,    # Sun
    1: 10,   # Moon
    2: 7,    # Mars
    3: 17,   # Mercury
    4: 16,   # Jupiter
    5: 20,   # Venus
    6: 19,   # Saturn
    7: 18,   # Rahu
    8: 7,    # Ketu
}

#: The eight kutas of the North Indian (Ashtakoota) matching system and their maximum
#: points. They sum to 36 — the ``porutham_36`` ceiling.
ASHTAKOOTA_MAX: tuple[tuple[str, int], ...] = (
    ("varna", 1),
    ("vasya", 2),
    ("gana", 6),
    ("tara", 3),
    ("yoni", 4),
    ("graha_maitri", 5),
    ("bhakoot", 7),
    ("nadi", 8),
)

#: Index of each kuta inside PyJHora's ``Ashtakoota.compatibility_score()`` return list.
ASHTAKOOTA_RESULT_INDEX: dict[str, int] = {
    "varna": 0,
    "vasya": 1,
    "gana": 2,
    "tara": 3,
    "yoni": 4,
    "graha_maitri": 5,
    "bhakoot": 6,
    "nadi": 7,
}
ASHTAKOOTA_TOTAL_INDEX = 8

#: Supplementary South Indian poruthams PyJHora reports as booleans, and their result index.
SUPPLEMENTARY_PORUTHAM_INDEX: dict[str, int] = {
    "mahendra": 9,
    "vedha": 10,
    "rajju": 11,
    "sthree_dheerga": 12,
}
