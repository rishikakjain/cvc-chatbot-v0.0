"""
explain_ge_area — translates GE area codes and plain-language terms into
human-readable descriptions for the CVC chatbot.

Supports CSU Breadth, IGETC, and Cal-GETC codes, plus common plain-language
phrases a student might type ("science with a lab", "english comp", etc.).
"""

from __future__ import annotations

# Canonical GE area definitions. Each entry covers all three frameworks
# where the area exists, plus plain-language aliases for fuzzy matching.
_GE_AREAS: list[dict] = [
    {
        "codes": ["A1", "1C"],
        "aliases": ["oral communication", "speech", "public speaking", "communication"],
        "title": "Oral Communication / Speech",
        "description": (
            "Courses in this area develop your ability to communicate clearly when speaking. "
            "Typical courses include Public Speaking, Interpersonal Communication, or Speech. "
            "CSU Breadth: A1 | IGETC/Cal-GETC: 1C"
        ),
    },
    {
        "codes": ["A2", "1A"],
        "aliases": ["english comp", "english composition", "writing", "written communication", "composition", "english"],
        "title": "Written Communication / English Composition",
        "description": (
            "This area covers college-level writing skills — reading critically, constructing arguments, "
            "and writing clear essays. Nearly all transfer students need this. "
            "CSU Breadth: A2 | IGETC/Cal-GETC: 1A"
        ),
    },
    {
        "codes": ["A3", "1B"],
        "aliases": ["critical thinking", "logic", "reasoning", "argument"],
        "title": "Critical Thinking",
        "description": (
            "Courses in this area teach you to analyze arguments, identify logical fallacies, "
            "and reason through complex problems. Often combined with philosophy or writing courses. "
            "CSU Breadth: A3 | IGETC/Cal-GETC: 1B"
        ),
    },
    {
        "codes": ["B1", "5A"],
        "aliases": ["physical science", "physics", "chemistry", "earth science", "astronomy"],
        "title": "Physical Science",
        "description": (
            "Covers the non-living physical world — physics, chemistry, earth science, astronomy, oceanography. "
            "Many of these courses have a companion lab (B3/5C). "
            "CSU Breadth: B1 | IGETC/Cal-GETC: 5A"
        ),
    },
    {
        "codes": ["B2", "5B"],
        "aliases": ["life science", "biology", "biology lab", "bio", "living science"],
        "title": "Life Science / Biology",
        "description": (
            "Covers living organisms — biology, botany, zoology, anatomy, physiology, environmental science. "
            "Many of these courses have a companion lab (B3/5C). "
            "CSU Breadth: B2 | IGETC/Cal-GETC: 5B"
        ),
    },
    {
        "codes": ["B3", "5C"],
        "aliases": ["lab", "science lab", "laboratory", "lab science", "science with lab", "lab requirement"],
        "title": "Science Laboratory",
        "description": (
            "A hands-on lab component that accompanies a B1 or B2 science course. "
            "Some courses include the lab built-in; others are separate lab sections you take alongside lecture. "
            "CSU Breadth: B3 | IGETC/Cal-GETC: 5C"
        ),
    },
    {
        "codes": ["B4", "2A"],
        "aliases": ["math", "mathematics", "quantitative reasoning", "statistics", "calculus", "algebra", "precalculus"],
        "title": "Mathematics / Quantitative Reasoning",
        "description": (
            "College-level math — statistics, calculus, precalculus, linear algebra, or other quantitative courses. "
            "Check the specific course's prerequisite — some require prior math coursework. "
            "CSU Breadth: B4 | IGETC/Cal-GETC: 2A"
        ),
    },
    {
        "codes": ["C1", "3A"],
        "aliases": ["arts", "art", "music", "theater", "dance", "film", "studio art", "performing arts", "fine arts"],
        "title": "Arts",
        "description": (
            "Covers creative and performing arts — art history, music appreciation, theater, film, studio art. "
            "CSU Breadth: C1 | IGETC/Cal-GETC: 3A"
        ),
    },
    {
        "codes": ["C2", "3B"],
        "aliases": ["humanities", "literature", "history of art", "philosophy", "languages", "foreign language", "literature"],
        "title": "Humanities",
        "description": (
            "Covers human culture through literature, philosophy, languages, and history of art. "
            "CSU Breadth: C2 | IGETC/Cal-GETC: 3B"
        ),
    },
    {
        "codes": ["D", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "4", "4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H", "4I", "4J"],
        "aliases": ["social science", "sociology", "psychology", "economics", "political science", "history", "anthropology", "geography", "social studies"],
        "title": "Social Sciences",
        "description": (
            "Covers human society and behavior — psychology, sociology, political science, economics, history, "
            "anthropology, and more. The D area has several sub-areas (D1–D9) and IGETC 4 has sub-areas (4A–4J). "
            "CSU Breadth: D (various sub-areas) | IGETC/Cal-GETC: 4 (various sub-areas)"
        ),
    },
    {
        "codes": ["E", "E1"],
        "aliases": ["lifelong learning", "wellness", "health", "physical education", "kinesiology", "pe"],
        "title": "Lifelong Understanding / Self-Development",
        "description": (
            "Covers health, wellness, physical education, and personal development. "
            "CSU Breadth: E | IGETC: not required | Cal-GETC: not required"
        ),
    },
    {
        "codes": ["F"],
        "aliases": ["ethnic studies", "race", "diversity", "chicano", "african american studies", "asian american"],
        "title": "Ethnic Studies",
        "description": (
            "Required for CSU graduation (not part of IGETC or Cal-GETC). Covers the history, culture, "
            "and experiences of ethnic groups in the United States. "
            "CSU Breadth: F | IGETC: not applicable | Cal-GETC: not applicable"
        ),
    },
]

# Framework overviews — returned when a student asks about a framework by name
_FRAMEWORKS: dict[str, str] = {
    "igetc": (
        "**IGETC (Intersegmental General Education Transfer Curriculum)** is a set of general education courses "
        "that satisfies lower-division GE requirements for *both* UC and CSU systems. "
        "If you complete IGETC before transferring, your transfer school won't make you take additional lower-division GE courses. "
        "It covers 7 broad areas (English, Math, Arts & Humanities, Social Sciences, Physical & Biological Sciences, Languages). "
        "Not all CSU majors accept IGETC — check with your counselor."
    ),
    "csu breadth": (
        "**CSU GE Breadth** (also called 'CSUGE' or 'CSU Breadth') is the California State University's own GE pattern. "
        "It's an alternative to IGETC and is accepted at all 23 CSU campuses. "
        "It covers areas A–F. Unlike IGETC, it doesn't satisfy UC GE requirements. "
        "Most students transferring to a CSU use this pattern."
    ),
    "csuge": (
        "**CSU GE Breadth** (also called 'CSUGE' or 'CSU Breadth') is the California State University's own GE pattern. "
        "It's an alternative to IGETC and is accepted at all 23 CSU campuses. "
        "It covers areas A–F. Unlike IGETC, it doesn't satisfy UC GE requirements. "
        "Most students transferring to a CSU use this pattern."
    ),
    "cal-getc": (
        "**Cal-GETC (California General Education Transfer Curriculum)** is a unified GE pattern that replaced "
        "the old IGETC pattern starting Fall 2025. It is accepted at both UC and CSU campuses. "
        "Cal-GETC uses similar area codes to IGETC (1A, 1B, 2A, 3A, 3B, 4, 5A, 5B, 5C). "
        "If you're starting in Fall 2025 or later, Cal-GETC is the recommended pattern."
    ),
    "calgetc": (
        "**Cal-GETC (California General Education Transfer Curriculum)** is a unified GE pattern that replaced "
        "the old IGETC pattern starting Fall 2025. It is accepted at both UC and CSU campuses. "
        "Cal-GETC uses similar area codes to IGETC (1A, 1B, 2A, 3A, 3B, 4, 5A, 5B, 5C). "
        "If you're starting in Fall 2025 or later, Cal-GETC is the recommended pattern."
    ),
    "ge": (
        "**General Education (GE)** requirements are a set of courses all transfer students need to complete "
        "before transferring to a 4-year university. They ensure you have broad knowledge across subjects "
        "like English, math, science, arts, and social sciences. "
        "There are three main patterns: CSU GE Breadth (for CSU transfers), IGETC (older UC/CSU pattern), "
        "and Cal-GETC (new unified pattern starting Fall 2025). Ask your counselor which fits your transfer goal."
    ),
}


def explain_ge_area(query: str) -> dict:
    """
    Explain a GE area code or plain-language term.

    Args:
        query: A GE area code (e.g. "B2", "5A", "1A") or plain-language phrase
               (e.g. "science with a lab", "what is IGETC?").

    Returns:
        dict with keys:
          - matched (bool): whether a match was found
          - title (str): short label for the area
          - description (str): plain-language explanation
          - codes (list[str]): all codes that map to this area
    """
    q = query.strip().lower()

    # Check framework-level questions first
    for keyword, description in _FRAMEWORKS.items():
        if keyword in q:
            return {
                "matched": True,
                "title": keyword.upper(),
                "description": description,
                "codes": [],
            }

    # Try exact code match (case-insensitive)
    q_upper = q.upper()
    for area in _GE_AREAS:
        if q_upper in [c.upper() for c in area["codes"]]:
            return {
                "matched": True,
                "title": area["title"],
                "description": area["description"],
                "codes": area["codes"],
            }

    # Try alias / keyword match
    for area in _GE_AREAS:
        if any(alias in q for alias in area["aliases"]):
            return {
                "matched": True,
                "title": area["title"],
                "description": area["description"],
                "codes": area["codes"],
            }

    # No match — return helpful fallback
    return {
        "matched": False,
        "title": "Unknown GE Area",
        "description": (
            f"I don't recognize '{query}' as a GE area code or subject. "
            "Common GE areas include: Written Communication (A2/1A), Math (B4/2A), "
            "Physical Science (B1/5A), Life Science (B2/5B), Science Lab (B3/5C), "
            "Arts (C1/3A), Humanities (C2/3B), and Social Sciences (D/4). "
            "You can also ask me about IGETC, CSU Breadth, or Cal-GETC."
        ),
        "codes": [],
    }
