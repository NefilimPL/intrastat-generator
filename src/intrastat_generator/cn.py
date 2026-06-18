from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .config import STATUS_MISSING, STATUS_OK, STATUS_UNCERTAIN
from .models import CnDecision, TariffEntry
from .text import norm_key, tokens

try:
    from rapidfuzz import fuzz, process  # type: ignore
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False
    fuzz = None  # type: ignore
    process = None  # type: ignore
    import difflib

class CnResolver:
    """Dobór CN bez ręcznego słownika produktów.

    Kolejność:
    1. Reguły klasyfikacyjne po typie towaru i materiale opisanym/założonym w nazwie.
    2. Fuzzy matching po pozycjach taryfy działu 94 oraz dodatkowych kodach 99.
    3. Brak kodu, jeżeli wynik nie spełnia progu lub kodu nie ma w taryfie.
    """

    def __init__(self, tariff_entries: List[TariffEntry], confident_threshold: float, uncertain_threshold: float):
        self.tariff_entries = tariff_entries
        self.confident_threshold = float(confident_threshold)
        self.uncertain_threshold = float(uncertain_threshold)
        self.valid_codes = {e.code for e in tariff_entries}
        self.relevant_entries = [e for e in tariff_entries if e.code.startswith("94") or e.code.startswith("99")]
        self._fuzzy_texts = [self._normalize_for_fuzzy(f"{e.path_text} {e.description}") for e in self.relevant_entries]

    @staticmethod
    def _normalize_for_fuzzy(value: str) -> str:
        s = norm_key(value)
        s = re.sub(r"[^A-Z0-9 ]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def resolve(self, description: str) -> CnDecision:
        rule = self._rule_based(description)
        if rule:
            code, confidence, method, note = rule
            if code in self.valid_codes:
                return self._with_status(code, confidence, method, self._entry_text(code), note)
            return CnDecision("", STATUS_MISSING, 0.0, method, "", f"Reguła wskazała {code}, ale kodu nie ma w wczytanej taryfie")

        fuzzy_decision = self._tariff_fuzzy(description)
        if fuzzy_decision.code and fuzzy_decision.confidence >= self.uncertain_threshold and fuzzy_decision.code in self.valid_codes:
            return self._with_status(fuzzy_decision.code, fuzzy_decision.confidence, fuzzy_decision.method, fuzzy_decision.matched_text, fuzzy_decision.note)

        best = fuzzy_decision
        if best.code:
            return CnDecision("", STATUS_MISSING, best.confidence, "brak pewnego dopasowania", best.matched_text,
                              f"Najlepsze dopasowanie {best.code} miało tylko {best.confidence:.1f}%, poniżej progu {self.uncertain_threshold:.1f}%")
        return CnDecision("", STATUS_MISSING, 0.0, "brak", "", "Nie znaleziono żadnego pasującego kodu w taryfie")

    def _with_status(self, code: str, confidence: float, method: str, matched_text: str, note: str) -> CnDecision:
        status = STATUS_OK if confidence >= self.confident_threshold else STATUS_UNCERTAIN
        return CnDecision(code, status, round(float(confidence), 2), method, matched_text, note)

    def _entry_text(self, code: str) -> str:
        for e in self.tariff_entries:
            if e.code == code:
                return e.path_text
        return ""

    def _rule_based(self, description: str) -> Optional[Tuple[str, float, str, str]]:
        s = norm_key(description)
        t = tokens(description)

        # Siedzenia. Tu bez kartoteki materiałowej część decyzji pozostaje niepewna.
        if "FOTEL" in t and "OBROTOWY" in t:
            return "94013900", 86.0, "reguła: fotel obrotowy", "Siedzenie obrotowe, materiał ramy niepewny; wymaga kontroli, dlatego żółty wynik"
        if "FOTEL" in t and "OGRODOWY" in t:
            return "94017100", 86.0, "reguła: fotel ogrodowy", "Założono siedzenie tapicerowane/z poduszką na ramie metalowej; wymaga kontroli"
        if "HOKER" in t or "KRZESLO" in t:
            if any(x in s for x in ["WELUR", "WELUROWE", "TAPIC", "TK.", "TK ", "ECO", "BEZ", "SZARE", "CZARNE"]):
                return "94017100", 86.0, "reguła: krzesło/hoker", "Założono siedzenie tapicerowane na ramie metalowej; wymaga kontroli materiału ramy"
            return "94017900", 82.0, "reguła: krzesło/hoker", "Brak informacji o tapicerce; założono pozostałe siedzenie na ramie metalowej"
        if "TABORET" in t or "LAWKA" in t:
            if any(x in s for x in ["TK", "ECO", "SAFARI", "WELUR", "TAPIC"]):
                return "94016100", 86.0, "reguła: taboret/ławka", "Założono siedzenie tapicerowane na ramie drewnianej; wymaga kontroli"
            return "94016900", 82.0, "reguła: taboret/ławka", "Brak informacji o tapicerce; założono pozostałe siedzenie drewniane"
        if "FOTEL" in t:
            return "", 0.0, "reguła: fotel bez danych", "Nie można bezpiecznie ustalić typu fotela/ramy z samego opisu"

        # Meble kuchenne.
        if "KUCH" in s or "LIVIA" in t:
            return "94034090", 92.0, "reguła: mebel kuchenny", "Element/mebel kuchenny drewniany lub z płyty"

        # Meble biurowe.
        if "BIURKO" in t:
            return "94033011", 95.0, "reguła: biurko", "Biurko drewniane lub z płyty"

        # Meble sypialniane.
        if "SZAFA" in t or ("SZAFKA" in t and "NOCNA" in t) or ("STOLIK" in t and "NOCNY" in t):
            return "94035000", 94.0, "reguła: sypialnia", "Mebel drewniany/z płyty w rodzaju stosowanych w sypialni"

        # Przedpokój, wieszak, szafka na buty, szafka z lustrem i ogólne cabinet/high cabinet.
        if "PRZEDPOKOJ" in t or "WIESZAK" in t or "BUTY" in t or "HALL" in t or "LUSTREM" in t or "CABINET" in t:
            return "94036090", 92.0, "reguła: pozostały mebel drewniany", "Pozostały mebel drewniany/z płyty"

        # Szafka bez oznaczenia kuchni/sypialni traktowana jako mebel pokojowy/salonowy.
        if "SZAFKA" in t:
            return "94036010", 92.0, "reguła: szafka pokojowa", "Szafka drewniana/z płyty, bez cech kuchni/sypialni/przedpokoju"

        # Salon, pokój dzienny, jadalnia.
        living_words = {"RTV", "KOMODA", "LAWA", "STOL", "STOLIK", "MEBLOSCIANKA", "WITRYNA", "REGAL"}
        if living_words.intersection(t):
            return "94036010", 95.0, "reguła: salon/jadalnia", "Mebel drewniany/z płyty w rodzaju stosowanych w pokojach stołowych i salonach"

        # Typowy zapis mebli skrzyniowych bez słowa KOMODA, np. 2D1S, 3D3S.
        if re.search(r"\b\d+D(?:\d*S)?\b|\b\d+S\b", s):
            return "94036010", 90.0, "reguła: układ drzwi/szuflad", "Opis zawiera układ typu 2D1S/3D3S, czyli typowy mebel skrzyniowy pokojowy"

        # Angielskie nazwy szafek, które nie mówią o pomieszczeniu.
        if "CABINET" in t:
            return "94036090", 88.0, "reguła: cabinet", "Pozostały mebel drewniany/z płyty, opis nie wskazuje jednoznacznie pomieszczenia"

        return None

    def _tariff_fuzzy(self, description: str) -> CnDecision:
        if not self.relevant_entries:
            return CnDecision("", STATUS_MISSING, 0.0, "brak taryfy", "", "Nie załadowano pozycji działu 94/99 z taryfy")
        query = self._normalize_for_fuzzy(description)
        if HAS_RAPIDFUZZ:
            result = process.extractOne(query, self._fuzzy_texts, scorer=fuzz.WRatio)  # type: ignore[union-attr]
            if result:
                _text, score, idx = result
                entry = self.relevant_entries[idx]
                return CnDecision(entry.code, STATUS_UNCERTAIN, float(score), "fuzzy taryfa", entry.path_text, "Najlepsze podobieństwo do opisu taryfy")
        else:
            best_idx = 0
            best_score = -1.0
            for i, txt in enumerate(self._fuzzy_texts):
                score = difflib.SequenceMatcher(None, query, txt).ratio() * 100
                if score > best_score:
                    best_score = score
                    best_idx = i
            entry = self.relevant_entries[best_idx]
            return CnDecision(entry.code, STATUS_UNCERTAIN, best_score, "fuzzy taryfa", entry.path_text, "Najlepsze podobieństwo do opisu taryfy")
        return CnDecision("", STATUS_MISSING, 0.0, "brak", "", "Nie znaleziono dopasowania")


