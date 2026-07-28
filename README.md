# vedic-engine

A stateless HTTP API for sidereal (Vedic) astronomy calculations, built as a thin wrapper
around [PyJHora](https://pypi.org/project/PyJHora/) and the Swiss Ephemeris.

Give it an absolute UTC instant and a pair of coordinates; it returns positions, periods and
scores. It stores nothing, knows nothing about who is asking, and interprets nothing.

## Fixed parameters

These are hard-coded and have no request-level override. A chart computed today and the same
chart recomputed in two years must agree, so every response echoes `engine_version` and
`ayanamsa` for cache invalidation.

| Parameter | Value |
|---|---|
| Ayanamsa | Lahiri |
| Zodiac | Sidereal |
| Dasha system | Vimshottari (120-year cycle) |
| Time basis | **UTC only** |

There is no timezone database here. Resolving a birthplace and a wall-clock time into a UTC
instant is the caller's job — a naive timestamp is rejected with a `422` rather than guessed
at, because guessing shifts the ascendant by hours.

Latitudes beyond ±66.5° are rejected with a `422`: the underlying house calculation
(Placidus) is mathematically undefined above the polar circles, and a clear refusal beats a
mid-calculation crash.

## API

All calculation endpoints are `POST` and share one body shape:

```jsonc
{
  "utc": "1995-06-20T18:30:00Z",   // required, must carry an offset
  "lat": 40.7128,                  // required, -90..90
  "lon": -74.0060                  // required, -180..180
}
```

| Endpoint | Returns |
|---|---|
| `POST /v1/chart` | Rasi (D1) and navamsa (D9): ascendant, and per planet `sign`, `house`, `degree`, `retrograde` |
| `POST /v1/dasha` | Nine Vimshottari mahadashas with start/end, plus the period running at `as_of` (optional field, defaults to now) |
| `POST /v1/yoga` | Every detected yoga with its Sanskrit key, definition and classical effect |
| `POST /v1/panchanga` | Tithi, nakshatra (with pada), yoga, karana, Moon sign. Optional `target_date` evaluates at 00:00 UTC of that date |
| `POST /v1/strength` | Shadbala for the seven classical planets: `score_100`, `ratio`, `rupas`, `rank` |
| `POST /v1/compat` | Ashtakoota matching for two birth points (`{"a": {...}, "b": {...}}`): the 36-point total and all eight kutas |
| `GET /health` | Liveness plus the fixed parameters above |

Sanskrit keys (`raja_yoga`, `bhakoot`, …) are returned verbatim. Renaming them for an
audience is the caller's concern.

Interactive docs are served at `/docs`.

### Response conventions

- Signs are 0-indexed from Aries (`sign_index`) and also named (`sign`).
- Nakshatras and tithis use 1-based numbering, matching classical convention.
- Houses use whole-sign division: the ascendant's sign is house 1.
- `4xx` means the input was rejected; `5xx` means the calculation failed. Failure details go
  to the log, never into the response body.

### Known gaps

- `planets_involved` and `strength` on yoga entries are always empty/`null`. PyJHora reports
  yoga *presence* only; recovering participants would mean re-implementing all 284 yoga
  definitions, which is beyond a wrapper's remit.
- Planetary positions come from the Moshier ephemeris compiled into `pyswisseph` (no `.se1`
  data files are shipped). Accuracy is far finer than sign, nakshatra or pada boundaries,
  but it is not the full Swiss Ephemeris data set.
- Positions are *true* (geometric, `FLG_TRUEPOS`) rather than apparent — PyJHora's
  convention, common in Vedic software. The difference (annual aberration, ~20 arcsec)
  is far below any sign, nakshatra or pada boundary.
- `current` in the dasha response is computed here, not by PyJHora: its
  `get_running_dhasa_for_given_date` mutates module state on first call, shifting later
  results by minutes depending on call history. The mahadasha timeline still comes from
  PyJHora; the running antardasha is derived from it by the canonical proportional
  subdivision, which is the Vimshottari definition itself.

## Running it

```bash
make run          # build the image and serve on :8080
curl localhost:8080/health
```

```bash
curl -s localhost:8080/v1/chart \
  -H 'content-type: application/json' \
  -d '{"utc":"1995-06-20T18:30:00Z","lat":40.7128,"lon":-74.0060}'
```

The image is built for scale-to-zero container hosting: it reads `PORT`, runs as a non-root
user, and holds no connections open.

## Development

`pyswisseph` is a C extension with no Windows wheels, so all work happens in Docker.

```bash
make lint          # ruff
make test          # full suite in the dev image
make test-image    # same suite inside the pruned runtime image
make verify        # all three
make golden        # regenerate tests/golden/*.json
```

### How correctness is checked

`tests/test_cross_validation.py` recomputes the engine's answers a second way — ascendant
from `swe.houses_ex`, planet longitudes from `swe.calc_ut`, nakshatra and pada by dividing
the Moon's longitude directly, and the Vimshottari sequence from the Moon's nakshatra lord —
and compares. This validates the wrapper: ayanamsa applied, sidereal conversion, sign,
degree, house and nakshatra mapping.

It does **not** validate the ephemeris itself, since both paths read the same one. Spot
checks against an independent astrology implementation remain a manual step.

`tests/golden/*.json` freeze full output for five reference births (Korea 2, United States 1,
Europe 1, southern hemisphere 1). `tests/test_boundaries.py` covers midnight either side,
leap days, daylight-saving transition instants, high latitudes and the poles.
`tests/test_stateless.py` asserts the service source imports no database, storage or network
client and carries no user identifiers.

## License

AGPL-3.0-or-later. PyJHora and the Swiss Ephemeris are themselves AGPL-licensed, which is why
this service is a separate, independently deployed repository.
