"""
Static mapping of California Community Colleges to geographic regions.
Keys are lowercase college names matching college_locations.py.
"""

COLLEGE_REGIONS: dict[str, str] = {
    # Bay Area
    "berkeley city college":        "Bay Area",
    "cabrillo college":             "Bay Area",
    "canada college":               "Bay Area",
    "cañada college":               "Bay Area",
    "chabot college":               "Bay Area",
    "city college of san francisco": "Bay Area",
    "college of alameda":           "Bay Area",
    "college of marin":             "Bay Area",
    "college of san mateo":         "Bay Area",
    "contra costa college":         "Bay Area",
    "de anza college":              "Bay Area",
    "diablo valley college":        "Bay Area",
    "evergreen valley college":     "Bay Area",
    "foothill college":             "Bay Area",
    "gavilan college":              "Bay Area",
    "laney college":                "Bay Area",
    "las positas college":          "Bay Area",
    "los medanos college":          "Bay Area",
    "merritt college":              "Bay Area",
    "mission college":              "Bay Area",
    "monterey peninsula college":   "Bay Area",
    "napa valley college":          "Bay Area",
    "ohlone college":               "Bay Area",
    "san jose city college":        "Bay Area",
    "skyline college":              "Bay Area",
    "solano community college":     "Bay Area",
    "west valley college":          "Bay Area",

    # Sacramento / Sierra
    "american river college":       "Sacramento/Sierra",
    "butte college":                "Sacramento/Sierra",
    "cosumnes river college":       "Sacramento/Sierra",
    "folsom lake college":          "Sacramento/Sierra",
    "lake tahoe community college": "Sacramento/Sierra",
    "sacramento city college":      "Sacramento/Sierra",
    "santa rosa junior college":    "Sacramento/Sierra",
    "sierra college":               "Sacramento/Sierra",
    "woodland community college":   "Sacramento/Sierra",
    "yuba college":                 "Sacramento/Sierra",

    # North State
    "college of the redwoods":      "North State",
    "college of the siskiyous":     "North State",
    "feather river college":        "North State",
    "lassen community college":     "North State",
    "mendocino college":            "North State",
    "shasta college":               "North State",

    # Central Valley
    "bakersfield college":          "Central Valley",
    "cerro coso community college": "Central Valley",
    "college of the sequoias":      "Central Valley",
    "columbia college":             "Central Valley",
    "fresno city college":          "Central Valley",
    "madera community college":     "Central Valley",
    "merced college":               "Central Valley",
    "modesto junior college":       "Central Valley",
    "porterville college":          "Central Valley",
    "reedley college":              "Central Valley",
    "taft college":                 "Central Valley",
    "west hills college coalinga":  "Central Valley",
    "west hills college lemoore":   "Central Valley",

    # Central Coast
    "allan hancock college":        "Central Coast",
    "cuesta college":               "Central Coast",
    "hartnell college":             "Central Coast",
    "santa barbara city college":   "Central Coast",

    # Los Angeles Metro
    "antelope valley college":      "Los Angeles Metro",
    "cerritos college":             "Los Angeles Metro",
    "citrus college":               "Los Angeles Metro",
    "coastline community college":  "Los Angeles Metro",
    "college of the canyons":       "Los Angeles Metro",
    "compton college":              "Los Angeles Metro",
    "cypress college":              "Los Angeles Metro",
    "east los angeles college":     "Los Angeles Metro",
    "el camino college":            "Los Angeles Metro",
    "fullerton college":            "Los Angeles Metro",
    "glendale community college":   "Los Angeles Metro",
    "golden west college":          "Los Angeles Metro",
    "irvine valley college":        "Los Angeles Metro",
    "long beach city college":      "Los Angeles Metro",
    "los angeles city college":     "Los Angeles Metro",
    "los angeles harbor college":   "Los Angeles Metro",
    "los angeles mission college":  "Los Angeles Metro",
    "los angeles pierce college":   "Los Angeles Metro",
    "los angeles southwest college": "Los Angeles Metro",
    "los angeles trade technical college": "Los Angeles Metro",
    "los angeles trade-technical college": "Los Angeles Metro",
    "los angeles valley college":   "Los Angeles Metro",
    "moorpark college":             "Los Angeles Metro",
    "mt. san antonio college":      "Los Angeles Metro",
    "mt san antonio college":       "Los Angeles Metro",
    "orange coast college":         "Los Angeles Metro",
    "oxnard college":               "Los Angeles Metro",
    "pasadena city college":        "Los Angeles Metro",
    "rio hondo college":            "Los Angeles Metro",
    "saddleback college":           "Los Angeles Metro",
    "santa ana college":            "Los Angeles Metro",
    "santa monica college":         "Los Angeles Metro",
    "santiago canyon college":      "Los Angeles Metro",
    "ventura college":              "Los Angeles Metro",
    "west los angeles college":     "Los Angeles Metro",

    # Inland Empire
    "barstow community college":    "Inland Empire",
    "chaffey college":              "Inland Empire",
    "college of the desert":        "Inland Empire",
    "copper mountain college":      "Inland Empire",
    "crafton hills college":        "Inland Empire",
    "mt. san jacinto college":      "Inland Empire",
    "mt san jacinto college":       "Inland Empire",
    "palo verde college":           "Inland Empire",
    "riverside city college":       "Inland Empire",
    "san bernardino valley college": "Inland Empire",
    "victor valley college":        "Inland Empire",

    # San Diego
    "cuyamaca college":             "San Diego",
    "grossmont college":            "San Diego",
    "imperial valley college":      "San Diego",
    "miracosta college":            "San Diego",
    "palomar college":              "San Diego",
    "san diego city college":       "San Diego",
    "san diego mesa college":       "San Diego",
    "san diego miramar college":    "San Diego",
    "southwestern college":         "San Diego",
}

CA_REGIONS = [
    "Bay Area",
    "Los Angeles Metro",
    "San Diego",
    "Central Valley",
    "Central Coast",
    "Inland Empire",
    "Sacramento/Sierra",
    "North State",
]


def get_college_region(name: str) -> str:
    if not name:
        return "Other"
    return COLLEGE_REGIONS.get(name.lower().strip(), "Other")
