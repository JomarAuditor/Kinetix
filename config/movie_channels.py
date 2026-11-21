"""Official YouTube movie channels — curated from https://github.com/SuperAB123/Free-Official-Youtube-Content."""

OFFICIAL_MOVIE_CHANNELS = [
    # ── General / multi-genre ─────────────────────────────────────────────────
    {"channel_id": "UCGBzBkV-MinlBvHBzZawfLQ", "name": "Movie Central",          "type": "general"},
    {"channel_id": "UCNcUc5v0Kt5afE_jcbbZUBQ", "name": "Artflix Movie Classics", "type": "general"},
    {"channel_id": "UCgzOk7BrZ_REdrDXOhGIGqQ", "name": "Wu Tang Collection",     "type": "general"},

    # ── Classics / public domain ──────────────────────────────────────────────
    {"channel_id": "UCNcUc5v0Kt5afE_jcbbZUBQ", "name": "Artflix Movie Classics",  "type": "classics"},
    {"channel_id": "UCqr3f8lLBpxlqzPMwkEBHvg", "name": "Public Domain Movies",    "type": "classics"},
    {"channel_id": "UCMPcX8U4iDTlZZw5KHy37NQ", "name": "PizzaFlix",               "type": "classics"},

    # ── Horror ────────────────────────────────────────────────────────────────
    {"channel_id": "UC5I2hjZYiW9gZPVkvzM8_Cw", "name": "SCREAM FACTORY",          "type": "horror"},
    {"channel_id": "UCfJWbJZXWzMH8_sKhh9HfOg", "name": "Kings of Horror",         "type": "horror"},
    {"channel_id": "UC9z4J-1s1B3ekSbpeFdO75A", "name": "Vulture",                 "type": "horror"},
    {"channel_id": "UCHgm6IUmnTV2aAMMCSPq8zA", "name": "A Touch of Evil",          "type": "horror"},
    {"channel_id": "UC951AqujycbBI083GmKRY3A", "name": "New Castle After Dark",    "type": "horror"},

    # ── Action / martial arts ─────────────────────────────────────────────────
    {"channel_id": "UCgzOk7BrZ_REdrDXOhGIGqQ", "name": "Wu Tang Collection",      "type": "action"},
    {"channel_id": "UCjhDbm_8kMcCJn5PuBFPWVQ", "name": "Fastbreak Films",         "type": "action"},

    # ── Western ───────────────────────────────────────────────────────────────
    {"channel_id": "UC4scSuFqxZG-YV6tQAShB3Q", "name": "Grjngo Western Movies",   "type": "western"},
    {"channel_id": "UCc7lMU8nS9ViE-5cDEvqsgw", "name": "Grjngo Western Series",   "type": "western"},

    # ── Bollywood / Indian ────────────────────────────────────────────────────
    {"channel_id": "UCbgpnRPAWb0GSV80Qm3HlQw", "name": "Goldmines Bollywood",     "type": "bollywood"},
    {"channel_id": "UCRNqPbIpCZn-X8mfzTEHMcw", "name": "Goldmines Telefilms",     "type": "bollywood"},
    {"channel_id": "UCq5LYKrjnLcQQ2Qxm62rF9Q", "name": "Rajshri Movies",          "type": "bollywood"},
    {"channel_id": "UCULnXEDuUQSHvNi5a4IwSHw", "name": "Shemaroo Movies",         "type": "bollywood"},
    {"channel_id": "UCKq2FGFaJCMUqMkTCqsLMAw", "name": "Pen Multiplex",           "type": "bollywood"},

    # ── Family ────────────────────────────────────────────────────────────────
    {"channel_id": "UCUj-MIbPFJMVoVf7VJKqkkg", "name": "Air Bud TV",              "type": "family"},
    {"channel_id": "UCwnrONnJESwWb5SWqI6WQVA", "name": "WowKidz Movies",          "type": "family"},

    # ── Korean / Asian ────────────────────────────────────────────────────────
    {"channel_id": "UCO4rxfML-5ED-mJwV3CXPJQ", "name": "Korean Classic Film",     "type": "asian"},
    {"channel_id": "UCUpbgPbDccjoB9PxI-nI7oA", "name": "Wu Tang (HK)",            "type": "asian"},
    {"channel_id": "UCOsFUU8EtJGDd6-AouF_MwQ", "name": "Cinema Mei Ah HK",        "type": "asian"},

    # ── International / other ─────────────────────────────────────────────────
    {"channel_id": "UCGMPbEQMF-9lRazAFzLv2Jg", "name": "Mosfilm English",         "type": "international"},
    {"channel_id": "UCEBMvhXBBbOhpGLhPcbBFxg", "name": "CineMo Filipino",         "type": "international"},
]

# Categories: map to channel types and display name
MOVIE_CATEGORIES = {
    "popular": {
        "name": "Popular Free Movies",
        "channel_types": ["general"],
    },
    "horror": {
        "name": "Horror Movies",
        "channel_types": ["horror"],
    },
    "action": {
        "name": "Action & Martial Arts",
        "channel_types": ["action"],
    },
    "classics": {
        "name": "Classic Movies",
        "channel_types": ["classics"],
    },
    "western": {
        "name": "Western Movies",
        "channel_types": ["western"],
    },
    "bollywood": {
        "name": "Bollywood Movies",
        "channel_types": ["bollywood"],
    },
    "family": {
        "name": "Family & Kids Movies",
        "channel_types": ["family"],
    },
    "asian": {
        "name": "Asian & World Cinema",
        "channel_types": ["asian", "international"],
    },
}


def get_channels_for_category(category: str) -> list:
    """Return channels matching the given category, falling back to 'popular'."""
    cat_info = MOVIE_CATEGORIES.get(category) or MOVIE_CATEGORIES["popular"]
    channel_types = set(cat_info["channel_types"])
    return [ch for ch in OFFICIAL_MOVIE_CHANNELS if ch["type"] in channel_types]


def get_all_channel_ids() -> list:
    return [ch["channel_id"] for ch in OFFICIAL_MOVIE_CHANNELS]
