"""Turn raw OCR text from a prescription into structured medicine entries.

The parser is intentionally heuristic: prescriptions have no fixed format, so
it looks for the signals that show up on almost every one (dosage form,
strength, frequency, duration) and leaves everything else as free-text notes.
"""

import re

WORD_RE = re.compile(r"[A-Za-z\u0600-\u06FF]")

NUMBERED_LINE_RE = re.compile(r"^\s*(?:rx\s*)?(?:\d{1,2}\s*[\.\)\-:,]\s*)", re.IGNORECASE)
BULLET_RE = re.compile(r"^[\s\u2022\u25cf\-\*\u00b7]+")

FORM_RE = re.compile(
    r"\b(tabs?|tablets?|caps?|capsules?|syr|syrups?|susp(?:ension)?|"
    r"drops?|cream|ointment|gel|inj(?:ection)?|spray|inhaler|"
    r"supp(?:ository|ositories)?|sachets?|solution|lotion|patch)\b",
    re.IGNORECASE,
)

FORM_NAMES = {
    "tab": "Tablet",
    "tabs": "Tablet",
    "tablet": "Tablet",
    "tablets": "Tablet",
    "cap": "Capsule",
    "caps": "Capsule",
    "capsule": "Capsule",
    "capsules": "Capsule",
    "syr": "Syrup",
    "syrup": "Syrup",
    "syrups": "Syrup",
    "susp": "Suspension",
    "suspension": "Suspension",
    "drop": "Drops",
    "drops": "Drops",
    "cream": "Cream",
    "ointment": "Ointment",
    "gel": "Gel",
    "inj": "Injection",
    "injection": "Injection",
    "spray": "Spray",
    "inhaler": "Inhaler",
    "supp": "Suppository",
    "sachet": "Sachet",
    "sachets": "Sachet",
    "solution": "Solution",
    "lotion": "Lotion",
    "patch": "Patch",
}

STRENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|i\.u\.|1u|lu|%|units?)\b",
    re.IGNORECASE,
)

DOSE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*"
    r"(tabs?|tablets?|caps?|capsules?|puffs?|drops?|ml|teaspoons?|tsp|"
    r"sachets?|supp(?:ository|ositories)?|units?)\b",
    re.IGNORECASE,
)

SCHEDULE_RE = re.compile(r"\b([0-2])\s*[-/]\s*([0-2])\s*[-/]\s*([0-2])\b")
EVERY_RE = re.compile(
    r"\bevery\s*(\d+)\s*(hours?|hrs?|h|days?)\b", re.IGNORECASE
)
Q_HOURS_RE = re.compile(r"\bq\s?(\d{1,2})\s?h\b", re.IGNORECASE)
TIMES_PER_DAY_RE = re.compile(
    r"\b(\d+)\s*(?:x|\u00d7)\s*(?:a|per|/)?\s*(?:day|daily)\b", re.IGNORECASE
)
N_TIMES_RE = re.compile(
    r"\b(\d+)\s*(?:x|\u00d7|times?)\s*(?:a|per|/)?\s*(?:day|daily)\b",
    re.IGNORECASE,
)
MULTIPLIER_RE = re.compile(r"\b(\d+)\s*(?:x|\u00d7)\s*(\d+)\b", re.IGNORECASE)
WORD_FREQUENCY_RE = re.compile(
    r"\b(once|twice|thrice|three times|four times)\s*(?:a|per|/)?\s*(?:day|daily)?\b",
    re.IGNORECASE,
)
ABBREVIATION_RE = re.compile(
    r"\b(od|bd|bid|tds|tid|qid|qds|q\d|qhs|nocte|mane|prn|sos|stat|b\.?d\.?|t\.?i\.?d\.?|q\.?i\.?d\.?)\b",
    re.IGNORECASE,
)

ABBREVIATION_NAMES = {
    "od": "Once daily",
    "bd": "Twice daily",
    "bid": "Twice daily",
    "b.d.": "Twice daily",
    "bd.": "Twice daily",
    "tds": "Three times daily",
    "tid": "Three times daily",
    "t.i.d.": "Three times daily",
    "tid.": "Three times daily",
    "qid": "Four times daily",
    "qds": "Four times daily",
    "q.i.d.": "Four times daily",
    "qid.": "Four times daily",
    "q4": "Every 4 hours",
    "qhs": "At bedtime",
    "nocte": "At bedtime",
    "mane": "In the morning",
    "prn": "As needed",
    "sos": "As needed",
    "stat": "Immediately (single dose)",
}

DURATION_RE = re.compile(
    r"\b(?:for|x|\u00d7)?\s*(\d+)\s*(days?|d|weeks?|wks?|w|months?|mos?)\b",
    re.IGNORECASE,
)

INSTRUCTION_PATTERNS = (
    (re.compile(r"\bafter\s+(?:a\s+)?meals?\b", re.IGNORECASE), "After meals"),
    (re.compile(r"\bbefore\s+(?:a\s+)?meals?\b", re.IGNORECASE), "Before meals"),
    (
        re.compile(r"\b(?:on\s+an?\s+)?empty\s+stomach\b", re.IGNORECASE),
        "On an empty stomach",
    ),
    (re.compile(r"\bwith\s+(?:a\s+)?food\b", re.IGNORECASE), "With food"),
    (
        re.compile(r"\bbefore\s+breakfast\b", re.IGNORECASE),
        "Before breakfast",
    ),
    (re.compile(r"\bat\s+bed\s?time\b", re.IGNORECASE), "At bedtime"),
    (re.compile(r"\bas\s+needed\b", re.IGNORECASE), "As needed"),
    (re.compile(r"\bapply\s+topically\b", re.IGNORECASE), "Apply topically"),
    (re.compile(r"\bin\s+each\s+eye\b", re.IGNORECASE), "In each eye"),
    (re.compile(r"\bin\s+each\s+nostril\b", re.IGNORECASE), "In each nostril"),
    (re.compile(r"\bsublingual(?:ly)?\b", re.IGNORECASE), "Sublingually"),
)

HEADER_RE = re.compile(
    r"^(dr\.?|doctor|clinic|hospital|medical|center|centre|pharmacy|patient|"
    r"name|age|sex|gender|date|address|phone|tel|mobile|diagnosis|"
    r"complaint|history|signature|signed|rx|prescription|no\.?)\b",
    re.IGNORECASE,
)

# Section markers: medicines live between "Rx" and the closing notes.
RX_START_RE = re.compile(r"^\s*(?:rx|r/|prescription)\s*[:.\-]?\s*$", re.IGNORECASE)
SECTION_STOP_RE = re.compile(
    r"^\s*(advice|notes?|follow[\s-]?up|investigations?|lab\s+tests?|"
    r"signature|signed|pharmacist|this\s+prescription|valid\s+for|"
    r"diet|instructions?\s+to\s+patient)\b",
    re.IGNORECASE,
)

# Words that show a line belongs to a letterhead/footer rather than a medicine.
LETTERHEAD_RE = re.compile(
    r"\b(clinic|hospital|medical\s+cent(?:er|re)|pharmacy|consultant|specialist|"
    r"street|st\.|road|rd\.|building|floor|suite|tel|telephone|fax|email|"
    r"www\.|http|license|registration)\b",
    re.IGNORECASE,
)

DATE_RE = re.compile(
    r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}|"
    r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
    re.IGNORECASE,
)


def _clean(value):
    value = re.sub(r"\s+", " ", value or "")
    return value.strip(" .,;:-\u2013\u2014|")


def _normalize_strength(value):
    match = STRENGTH_RE.search(value or "")
    if not match:
        return ""

    number, unit = match.group(1), match.group(2).lower()
    unit = {
        "i.u.": "IU",
        "iu": "IU",
        "1u": "IU",
        "lu": "IU",
        "unit": "units",
        "units": "units",
    }.get(unit, unit)
    if unit not in ("%",):
        unit = f" {unit}"

    return f"{number}{unit}".strip()


def _normalize_duration(value):
    if not value:
        return ""

    number, unit = value
    unit = unit.lower()
    singular = unit.rstrip("s")

    if singular.startswith("d"):
        label = "day"
    elif singular.startswith("w"):
        label = "week"
    else:
        label = "month"

    return f"{number} {label}{'' if number == '1' else 's'}"


def _find_frequency(line):
    match = SCHEDULE_RE.search(line)
    if match:
        return match.group(0).replace("/", "-").replace(" ", "")

    match = EVERY_RE.search(line)
    if match:
        unit = match.group(2).lower()
        unit = "hours" if unit.startswith(("h", "hour")) else "days"
        return f"Every {match.group(1)} {unit}"

    match = Q_HOURS_RE.search(line)
    if match:
        return f"Every {match.group(1)} hours"

    match = N_TIMES_RE.search(line) or TIMES_PER_DAY_RE.search(line)
    if match:
        return f"{match.group(1)} times daily"

    match = MULTIPLIER_RE.search(line)
    if match:
        return f"{match.group(1)} \u00d7 {match.group(2)} / day"

    match = WORD_FREQUENCY_RE.search(line)
    if match:
        word = match.group(1).lower()
        if word == "once":
            return "Once daily"
        if word == "twice":
            return "Twice daily"
        if word == "thrice":
            return "Three times daily"
        return word.title()

    match = ABBREVIATION_RE.search(line)
    if match:
        abbr = match.group(1).lower().replace(".", "")
        return ABBREVIATION_NAMES.get(abbr) or ABBREVIATION_NAMES.get(match.group(1).lower(), "")

    if re.search(r"\bdaily\b", line, re.IGNORECASE):
        return "Once daily"

    return ""


def _find_duration(line):
    for match in DURATION_RE.finditer(line):
        number, unit = match.group(1), match.group(2)
        # Ignore things like "500 mg" or "12 hours" that are not durations.
        if not number:
            continue
        return _normalize_duration((number, unit))
    return ""


def _find_instructions(line):
    found = []

    for pattern, label in INSTRUCTION_PATTERNS:
        if pattern.search(line) and label not in found:
            found.append(label)

    return ", ".join(found)


def _find_dose(line):
    match = DOSE_RE.search(line)
    if not match:
        return ""

    quantity, unit = match.group(1), match.group(2).lower()
    unit = FORM_NAMES.get(unit.rstrip("s"), FORM_NAMES.get(unit, unit))
    if unit in ("Tablet", "Capsule", "Drop", "Puff", "Sachet", "Suppository"):
        unit = unit if quantity == "1" else unit + "s"
    elif unit in ("Teaspoon", "Tsp"):
        unit = "tsp"

    return f"{quantity} {unit.lower()}"


def _find_form(line):
    match = FORM_RE.search(line)
    if not match:
        return ""

    token = match.group(1).lower()
    token = token.rstrip("s") if token not in FORM_NAMES else token
    return FORM_NAMES.get(token, FORM_NAMES.get(match.group(1).lower(), ""))


def _clean_name(value):
    value = NUMBERED_LINE_RE.sub(" ", value)
    value = BULLET_RE.sub(" ", value)
    value = re.sub(r"^\s*rx\s*[:\-]?\s*", " ", value, flags=re.IGNORECASE)
    value = STRENGTH_RE.sub(" ", value)
    value = FORM_RE.sub(" ", value)

    # Remove timing phrases that belong to the instructions, not the name.
    for pattern, _label in INSTRUCTION_PATTERNS:
        value = pattern.sub(" ", value)

    # Drop OCR noise and stray separators/quantities left behind.
    value = re.sub(r"\s+[-\u2013\u2014~]\s*\d+\s*$", " ", value)
    value = re.sub(r"[~^`_]+", " ", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:x|\u00d7)\s*\d+\b", " ", value)
    value = re.sub(r"\b(?:for|every|daily|once|twice)\b.*$", " ", value, flags=re.IGNORECASE)
    value = _clean(value)

    return value


def _is_header(line):
    stripped = line.strip()
    if not stripped:
        return True
    if not WORD_RE.search(stripped):
        return True

    if HEADER_RE.match(stripped):
        # "Rx" alone, "Dr. X", "Date: ..." etc. are never medicine lines.
        return True

    # A line that is only a date or a phone number.
    without_date = DATE_RE.sub("", stripped)
    if not WORD_RE.search(without_date):
        return True

    return False


def _extract_patient(text):
    patient = {}

    match = re.search(
        r"\bpatient(?:\s*name)?\s*[:\-]\s*(.+?)"
        r"(?=\s{2,}|\s+age\b|\s+sex\b|\s+gender\b|\n|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        patient["name"] = _clean(match.group(1))

    match = re.search(r"\bage\s*[:\-]\s*(\d{1,3})\b", text, re.IGNORECASE)
    if match:
        patient["age"] = f"{match.group(1)} years"

    match = DATE_RE.search(text)
    if match:
        patient["date"] = match.group(0)

    match = re.search(
        r"\bdr\.?\s+([A-Z][A-Za-z.\-']+(?:\s+[A-Z][A-Za-z.\-']+){0,3})",
        text,
    )
    if match:
        patient["doctor"] = f"Dr. {_clean(match.group(1))}"

    return patient


def parse_prescription(raw_text):
    """Parse raw OCR text into medicines plus a little patient context."""

    text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    medicines = []
    seen = set()

    # When the prescription has an explicit "Rx" line, only read below it.
    start = 0
    for index, line in enumerate(lines):
        if RX_START_RE.match(line):
            start = index + 1
            break

    for line in lines[start:]:
        if not line:
            continue

        if SECTION_STOP_RE.match(line):
            break

        if _is_header(line) or LETTERHEAD_RE.search(line):
            continue

        strength = _normalize_strength(line)
        form = _find_form(line)
        dose = _find_dose(line)
        frequency = _find_frequency(line)
        duration = _find_duration(line)
        instructions = _find_instructions(line)

        # Timing-only instructions still imply a once-daily schedule.
        if not frequency and instructions in ("Before breakfast", "At bedtime"):
            frequency = "Once daily"

        # A medicine line must carry at least one dosage signal.
        if not any((strength, form, dose, frequency, duration)):
            continue

        # Name is whatever comes before the first dash/pipe separated block.
        name = _clean_name(re.split(r"\s+[-\u2013\u2014|]\s+|\t+", line)[0])

        if len(name) < 2 or not WORD_RE.search(name):
            continue

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        medicines.append(
            {
                "name": name[:80],
                "strength": strength,
                "form": form,
                "dose": dose,
                "frequency": frequency,
                "duration": duration,
                "instructions": instructions,
                "raw": line[:300],
            }
        )

    return {
        "medicines": medicines,
        "patient": _extract_patient(text),
        "line_count": len([line for line in lines if line]),
    }
