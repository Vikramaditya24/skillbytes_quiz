"""
Deterministic educational content generation, one generator per subject.

Design: each subject either (a) has a parametrized numeric template (algebra,
geometry, mechanics, thermodynamics) where varying the numbers is what
creates volume and the question is genuinely computed - the "correct answer"
is mathematically derived, not hand-picked, and distractors are plausible
near-misses (off-by-one-step errors, common formula confusions); or (b) draws
from a curated fact bank (chemistry, biology, history, political science,
grammar, vocabulary) cycled through 2 phrasing variants to build volume
without repeating fact+phrasing combinations.

Nothing here calls an external API or LLM. Every question is fully
reproducible from (subject, chapter_index, question_index, RNG_SEED).
"""

import random


def _spread(chapter_idx: int, q_idx: int, lo: int, hi: int, stride: int = 1) -> int:
    """
    Deterministic value in [lo, hi] derived from (chapter_idx, q_idx), NOT
    from the shared RNG. Guarantees uniqueness across the ~17 questions in a
    single chapter (as long as hi-lo+1 >= 17): for a fixed chapter_idx, 17
    consecutive q_idx values map to 17 consecutive residues mod range_size,
    which cannot collide while range_size >= 17. Using rng.randint here
    instead would risk birthday-paradox collisions on small ranges (e.g. a
    9-value radius range with only ~4 draws already has >50% collision odds).
    `stride` decorrelates different parameters that share the same q_idx.
    """
    range_size = hi - lo + 1
    return lo + ((q_idx * stride + chapter_idx * 11) % range_size)


def _options(correct_value, distractors: list, rng: random.Random) -> tuple[list[dict], str]:
    """Shuffle correct_value in among distractors, return (options, correct_key)."""
    values = [correct_value] + distractors
    rng.shuffle(values)
    keys = ["A", "B", "C", "D"]
    correct_key = keys[values.index(correct_value)]
    options = [{"key": k, "text": str(v)} for k, v in zip(keys, values)]
    return options, correct_key


# ---------------------------------------------------------------------------
# Algebra - linear equations, solved for an integer x
# ---------------------------------------------------------------------------
def algebra_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    a = _spread(chapter_idx, q_idx, 2, 9, stride=3)
    x = _spread(chapter_idx, q_idx, -12, 12, stride=5)
    b = _spread(chapter_idx, q_idx, -15, 15, stride=7)
    c = a * x + b
    b_str = f" + {b}" if b >= 0 else f" - {abs(b)}"
    text = f"Solve for x: {a}x{b_str} = {c}"
    distractors = [x + 1, x - 1, -x if -x != x else x + 2]
    distractors = list(dict.fromkeys(d for d in distractors if d != x))[:3]
    while len(distractors) < 3:
        distractors.append(x + len(distractors) + 2)
    options, correct_key = _options(x, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Geometry - area/perimeter of simple shapes
# ---------------------------------------------------------------------------
def geometry_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    kind_cycle = 4
    shape = ["rectangle_area", "rectangle_perimeter", "triangle_area", "circle_area"][
        (chapter_idx + q_idx) % kind_cycle
    ]
    occurrence = q_idx // kind_cycle  # see mechanics_question for why: avoids spaced-index collisions
    if shape == "rectangle_area":
        l = _spread(chapter_idx, occurrence, 3, 20, stride=1)
        w = _spread(chapter_idx, occurrence, 3, 20, stride=4)
        correct = l * w
        text = f"What is the area of a rectangle with length {l} cm and width {w} cm?"
        distractors = [2 * (l + w), l + w, (l * w) + w]
    elif shape == "rectangle_perimeter":
        l = _spread(chapter_idx, occurrence, 3, 20, stride=1)
        w = _spread(chapter_idx, occurrence, 3, 20, stride=5)
        correct = 2 * (l + w)
        text = f"What is the perimeter of a rectangle with length {l} cm and width {w} cm?"
        distractors = [l * w, l + w, 2 * l]
    elif shape == "triangle_area":
        base = _spread(chapter_idx, occurrence, 4, 20, stride=1)
        height = _spread(chapter_idx, occurrence, 4, 20, stride=3)
        correct = (base * height) // 2 if (base * height) % 2 == 0 else base * height / 2
        text = f"What is the area of a triangle with base {base} cm and height {height} cm?"
        distractors = [base * height, base + height, (base * height) // 2 + base]
    else:  # circle_area, kept to integer-friendly radii using pi≈3.14 approximation stated in question
        r = _spread(chapter_idx, occurrence, 2, 20, stride=1)
        correct = round(3.14 * r * r, 2)
        text = f"Using pi ≈ 3.14, what is the area of a circle with radius {r} cm (in cm²)?"
        distractors = [round(2 * 3.14 * r, 2), round(3.14 * r, 2), round(3.14 * r * r) + r]
    distractors = list(dict.fromkeys(d for d in distractors if d != correct))[:3]
    while len(distractors) < 3:
        distractors.append(round(correct + len(distractors) + 3, 2))
    options, correct_key = _options(correct, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Mechanics - basic kinematics
# ---------------------------------------------------------------------------
def mechanics_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    kind_cycle = 3
    kind = ["velocity", "distance", "force"][(chapter_idx + q_idx) % kind_cycle]
    # Occurrence count of THIS kind within the chapter so far, not the raw
    # question index - the raw index is spaced by kind_cycle for any single
    # kind, and multiplying a spaced index by a stride that shares a factor
    # with kind_cycle collapses to a constant (see _spread's docstring risk).
    occurrence = q_idx // kind_cycle
    if kind == "velocity":
        a = _spread(chapter_idx, occurrence, 2, 8, stride=1)
        t = _spread(chapter_idx, occurrence, 2, 10, stride=3)
        correct = a * t
        text = f"A body starts from rest and accelerates at {a} m/s² for {t} seconds. What is its final velocity (m/s)?"
        distractors = [a + t, a * t + a, a * t - t]
    elif kind == "distance":
        u = _spread(chapter_idx, occurrence, 2, 6, stride=1)
        t = _spread(chapter_idx, occurrence, 2, 8, stride=3)
        correct = u * t
        text = f"An object moves at a constant velocity of {u} m/s for {t} seconds. What distance does it cover (m)?"
        distractors = [u + t, u * t + u, u * t - t if u * t - t > 0 else u * t + 2]
    else:
        m = _spread(chapter_idx, occurrence, 2, 10, stride=1)
        a = _spread(chapter_idx, occurrence, 2, 10, stride=3)
        correct = m * a
        text = f"What net force (in N) is needed to accelerate a {m} kg mass at {a} m/s² (F = ma)?"
        distractors = [m + a, m * a + m, m * a - a if m * a - a > 0 else m * a + 3]
    distractors = list(dict.fromkeys(d for d in distractors if d != correct))[:3]
    while len(distractors) < 3:
        distractors.append(correct + len(distractors) + 4)
    options, correct_key = _options(correct, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Thermodynamics - unit conversions
# ---------------------------------------------------------------------------
def thermodynamics_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    kind = (chapter_idx + q_idx) % 2
    c = _spread(chapter_idx, q_idx, -20, 100, stride=1)
    if kind == 0:
        correct = c + 273
        text = f"Convert {c}°C to Kelvin (K)."
        distractors = [c + 272, c + 274, c]
    else:
        correct = round(c * 9 / 5 + 32)
        text = f"Convert {c}°C to Fahrenheit (°F)."
        distractors = [c + 32, round(c * 5 / 9 + 32), correct + 9]
    distractors = list(dict.fromkeys(d for d in distractors if d != correct))[:3]
    while len(distractors) < 3:
        distractors.append(correct + len(distractors) + 5)
    options, correct_key = _options(correct, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Organic Chemistry - compound -> molecular formula fact bank
# ---------------------------------------------------------------------------
_CHEMISTRY_FACTS = [
    ("Methane", "CH4"), ("Ethane", "C2H6"), ("Ethanol", "C2H5OH"),
    ("Benzene", "C6H6"), ("Acetic acid", "CH3COOH"), ("Propane", "C3H8"),
    ("Butane", "C4H10"), ("Methanol", "CH3OH"), ("Glucose", "C6H12O6"),
    ("Acetone", "C3H6O"), ("Ethylene", "C2H4"), ("Acetylene", "C2H2"),
    ("Formaldehyde", "CH2O"), ("Toluene", "C7H8"), ("Propanol", "C3H7OH"),
    ("Formic acid", "HCOOH"), ("Chloroform", "CHCl3"), ("Phenol", "C6H5OH"),
    ("Acetaldehyde", "CH3CHO"), ("Cyclohexane", "C6H12"),
]
_CHEMISTRY_TEMPLATES = [
    "What is the molecular formula of {name}?",
    "Which molecular formula correctly represents {name}?",
]


def organic_chemistry_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_CHEMISTRY_FACTS)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_CHEMISTRY_FACTS)) % len(_CHEMISTRY_TEMPLATES)
    name, formula = _CHEMISTRY_FACTS[idx]
    text = _CHEMISTRY_TEMPLATES[template_idx].format(name=name)
    other_formulas = [f for n, f in _CHEMISTRY_FACTS if f != formula]
    distractors = rng.sample(other_formulas, 3)
    options, correct_key = _options(formula, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Cell Biology - organelle/structure -> function fact bank
# ---------------------------------------------------------------------------
_BIOLOGY_FACTS = [
    ("Mitochondria", "producing ATP (cellular energy)"),
    ("Ribosome", "synthesizing proteins"),
    ("Chloroplast", "carrying out photosynthesis"),
    ("Lysosome", "breaking down waste and cellular debris"),
    ("Nucleus", "storing genetic material (DNA)"),
    ("Golgi apparatus", "packaging and shipping proteins"),
    ("Endoplasmic reticulum", "synthesizing lipids and transporting proteins"),
    ("Cell membrane", "controlling what enters and exits the cell"),
    ("Vacuole", "storing water, nutrients, and waste"),
    ("Cytoskeleton", "providing structural support and enabling movement"),
    ("Cell wall", "providing rigidity and protection in plant cells"),
    ("Peroxisome", "breaking down fatty acids and detoxifying harmful substances"),
]
_BIOLOGY_TEMPLATES = [
    "Which cell structure is primarily responsible for {function}?",
    "The organelle responsible for {function} is the:",
]


def cell_biology_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_BIOLOGY_FACTS)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_BIOLOGY_FACTS)) % len(_BIOLOGY_TEMPLATES)
    name, function = _BIOLOGY_FACTS[idx]
    text = _BIOLOGY_TEMPLATES[template_idx].format(function=function)
    other_names = [n for n, f in _BIOLOGY_FACTS if n != name]
    distractors = rng.sample(other_names, 3)
    options, correct_key = _options(name, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Modern History - event -> year fact bank
# ---------------------------------------------------------------------------
_HISTORY_FACTS = [
    ("India's independence from British rule", 1947),
    ("the end of World War II", 1945),
    ("the start of World War I", 1914),
    ("the fall of the Berlin Wall", 1989),
    ("the first human Moon landing", 1969),
    ("the French Revolution's beginning", 1789),
    ("the founding of the United Nations", 1945),
    ("the dissolution of the Soviet Union", 1991),
    ("the signing of the Treaty of Versailles", 1919),
    ("the start of the Indian freedom movement's Quit India campaign", 1942),
    ("the invention of the World Wide Web", 1989),
    ("the abolition of slavery in the United States", 1865),
]
_HISTORY_TEMPLATES = [
    "In which year did {event} take place?",
    "{event_cap} occurred in which year?",
]


def modern_history_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_HISTORY_FACTS)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_HISTORY_FACTS)) % len(_HISTORY_TEMPLATES)
    event, year = _HISTORY_FACTS[idx]
    if template_idx == 0:
        text = _HISTORY_TEMPLATES[0].format(event=event)
    else:
        text = _HISTORY_TEMPLATES[1].format(event_cap=event[0].upper() + event[1:])
    distractors = list({year - 3, year + 2, year - 7, year + 5} - {year})
    distractors = rng.sample(distractors, 3)
    options, correct_key = _options(year, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Political Science - governance concept fact bank
# ---------------------------------------------------------------------------
_POLSCI_FACTS = [
    ("Democracy", "government in which power is held by the people, typically through elected representatives"),
    ("Monarchy", "government in which a single ruler holds power, often inherited"),
    ("Oligarchy", "government in which power rests with a small group of people"),
    ("Theocracy", "government in which religious leaders hold ruling authority"),
    ("Autocracy", "government in which one person holds absolute power"),
    ("Federalism", "a system in which power is divided between a central authority and constituent regions"),
    ("Bicameralism", "a legislative system with two separate chambers"),
    ("Separation of powers", "a principle dividing government into distinct branches with independent authority"),
    ("Unitary state", "a system in which a central government holds most political power"),
    ("Suffrage", "the right to vote in political elections"),
    ("Judicial review", "the power of courts to assess whether a law is consistent with the constitution"),
    ("Bipartisanship", "cooperation between two major political parties on an issue"),
]
_POLSCI_TEMPLATES = [
    "Which term describes {definition}?",
    "The term for {definition} is:",
]


def political_science_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_POLSCI_FACTS)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_POLSCI_FACTS)) % len(_POLSCI_TEMPLATES)
    term, definition = _POLSCI_FACTS[idx]
    text = _POLSCI_TEMPLATES[template_idx].format(definition=definition)
    other_terms = [t for t, d in _POLSCI_FACTS if t != term]
    distractors = rng.sample(other_terms, 3)
    options, correct_key = _options(term, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Grammar - part-of-speech identification fact bank
# ---------------------------------------------------------------------------
_GRAMMAR_SENTENCES = [
    ("She sang beautifully at the concert.", "beautifully", "Adverb"),
    ("The quick fox jumped over the fence.", "quick", "Adjective"),
    ("They ran to catch the bus.", "ran", "Verb"),
    ("The cat slept on the windowsill.", "cat", "Noun"),
    ("He placed the book under the table.", "under", "Preposition"),
    ("Wow, that was an amazing performance!", "Wow", "Interjection"),
    ("She works hard and studies every night.", "and", "Conjunction"),
    ("He finished his homework before dinner.", "He", "Pronoun"),
    ("The children played happily in the park.", "happily", "Adverb"),
    ("A tall building stood at the corner.", "tall", "Adjective"),
    ("The team celebrated their victory.", "celebrated", "Verb"),
    ("The teacher explained the lesson clearly.", "teacher", "Noun"),
    ("The dog barked loudly at the stranger.", "loudly", "Adverb"),
    ("She bought a fragile vase from the market.", "fragile", "Adjective"),
    ("They quietly closed the door behind them.", "closed", "Verb"),
    ("The mountain range stretched for miles.", "mountain", "Noun"),
    ("The keys were left inside the drawer.", "inside", "Preposition"),
    ("Ouch, that really hurt!", "Ouch", "Interjection"),
    ("He wanted tea but settled for coffee.", "but", "Conjunction"),
    ("They invited us to their wedding.", "They", "Pronoun"),
]
_GRAMMAR_TEMPLATES = [
    "In the sentence \"{sentence}\", what part of speech is the word '{word}'?",
    "Which part of speech best describes '{word}' in the sentence: \"{sentence}\"?",
]
_POS_OPTIONS = ["Noun", "Verb", "Adjective", "Adverb", "Preposition", "Conjunction", "Pronoun", "Interjection"]


def grammar_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_GRAMMAR_SENTENCES)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_GRAMMAR_SENTENCES)) % len(_GRAMMAR_TEMPLATES)
    sentence, word, correct_pos = _GRAMMAR_SENTENCES[idx]
    text = _GRAMMAR_TEMPLATES[template_idx].format(sentence=sentence, word=word)
    other_pos = [p for p in _POS_OPTIONS if p != correct_pos]
    distractors = rng.sample(other_pos, 3)
    options, correct_key = _options(correct_pos, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


# ---------------------------------------------------------------------------
# Vocabulary - synonym fact bank
# ---------------------------------------------------------------------------
_VOCAB_FACTS = [
    ("Benevolent", "Kind"), ("Meticulous", "Careful"), ("Eloquent", "Articulate"),
    ("Resilient", "Tough"), ("Candid", "Honest"), ("Ambiguous", "Unclear"),
    ("Diligent", "Hardworking"), ("Frugal", "Thrifty"), ("Gregarious", "Sociable"),
    ("Lucid", "Clear"), ("Meager", "Scant"), ("Novice", "Beginner"),
    ("Obsolete", "Outdated"), ("Prudent", "Sensible"), ("Reticent", "Reserved"),
    ("Tedious", "Boring"), ("Vivid", "Bright"), ("Zealous", "Enthusiastic"),
]
_VOCAB_TEMPLATES = [
    "Which word is closest in meaning to '{word}'?",
    "'{word}' most nearly means:",
]


def vocabulary_question(chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    idx = (chapter_idx * 17 + q_idx) % len(_VOCAB_FACTS)
    template_idx = ((chapter_idx * 17 + q_idx) // len(_VOCAB_FACTS)) % len(_VOCAB_TEMPLATES)
    word, synonym = _VOCAB_FACTS[idx]
    text = _VOCAB_TEMPLATES[template_idx].format(word=word)
    other_synonyms = [s for w, s in _VOCAB_FACTS if s != synonym]
    distractors = rng.sample(other_synonyms, 3)
    options, correct_key = _options(synonym, distractors, rng)
    return {"text": text, "options": options, "correct_option_key": correct_key}


GENERATORS = {
    "Algebra": algebra_question,
    "Geometry": geometry_question,
    "Mechanics": mechanics_question,
    "Thermodynamics": thermodynamics_question,
    "Organic Chemistry": organic_chemistry_question,
    "Cell Biology": cell_biology_question,
    "Modern History": modern_history_question,
    "Political Science": political_science_question,
    "Grammar": grammar_question,
    "Vocabulary": vocabulary_question,
}


def generate_question(subject_name: str, chapter_idx: int, q_idx: int, rng: random.Random) -> dict:
    """Dispatch to the subject-appropriate generator. Falls back defensively
    if a subject name doesn't match (shouldn't happen given SUBJECT_NAMES)."""
    generator = GENERATORS.get(subject_name)
    if generator is None:
        raise ValueError(f"no question generator registered for subject '{subject_name}'")
    return generator(chapter_idx, q_idx, rng)
