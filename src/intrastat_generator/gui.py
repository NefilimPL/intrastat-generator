from __future__ import annotations

import os
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:
    tk = None  # type: ignore
    filedialog = None  # type: ignore
    messagebox = None  # type: ignore
    ttk = None  # type: ignore

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    HAS_DND = True
except Exception:
    DND_FILES = None  # type: ignore
    TkinterDnD = None  # type: ignore
    HAS_DND = False

from .cn import HAS_RAPIDFUZZ
from .config import DEFAULT_CONFIG, DICT_DIR_NAME, OUTPUT_DIR_NAME, VOIVODESHIPS, app_name, load_json
from .paths import format_config_path, log_exception, resolve_path
from .service import GeneratorService
from .text import norm_text, parse_yes_no, safe_float, yes_no
from .transport import RouteCostManager
from .version import get_version

APP_NAME = app_name(get_version())


def format_gui_path(value: str | Path) -> str:
    text = str(value).strip().strip('"')
    if not text:
        return ""
    return format_config_path(Path(text))


def path_from_drop_data(root: tk.Tk, data: str) -> str:  # type: ignore[name-defined]
    try:
        items = root.tk.splitlist(data)
        if items:
            return str(items[0])
    except Exception:
        pass
    return data.strip().strip("{}").strip('"')

class App:
    def __init__(self):
        if tk is None:
            raise RuntimeError("Tkinter nie jest dostępny w tym Pythonie.")
        self.service = GeneratorService()
        self.route_config = self.service.load_route_cost_config()
        base_cls = TkinterDnD.Tk if HAS_DND else tk.Tk
        self.root = base_cls()
        self.root.title(APP_NAME)
        self.root.geometry("1020x700")
        self.root.minsize(900, 620)

        self.msg_queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.xml_var = tk.StringVar()
        self.tariff_var = tk.StringVar(value=format_gui_path(self.service.guess_tariff_path()))
        self.tariff_year_var = tk.StringVar()
        self.tariff_year_values: Dict[str, str] = {}
        self.dict_dir_var = tk.StringVar(value=format_gui_path(resolve_path(self.service.config.get("dict_dir", DICT_DIR_NAME), self.service.base_dir)))
        self.delivery_var = tk.StringVar(value=self.service.config.get("default_delivery_terms", ""))
        self.transaction_var = tk.StringVar(value=self.service.config.get("default_transaction_type", "11"))
        self.transport_var = tk.StringVar(value=self.service.config.get("default_transport_type", ""))
        self.stat_mode_var = tk.StringVar(value=self.service.config.get("statistical_value_mode", "blank"))
        self.origin_var = tk.StringVar(value=self.service.config.get("origin_voivodeship", self.route_config.get("origin_voivodeship", "podkarpackie")))
        self.allocation_var = tk.StringVar(value=self.service.config.get("transport_allocation_basis", self.route_config.get("allocation_basis", "invoice_value")))
        self.open_folder_var = tk.BooleanVar(value=bool(self.service.config.get("auto_open_output_folder", False)))
        self.hide_dict_var = tk.BooleanVar(value=bool(self.service.config.get("hide_dictionary_sheets", False)))
        self.confident_var = tk.StringVar(value=str(self.service.config.get("cn_confident_threshold", 90.0)))
        self.uncertain_var = tk.StringVar(value=str(self.service.config.get("cn_uncertain_threshold", 80.0)))
        self.progress_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="Gotowy")
        self._build_ui()
        self._refresh_tariff_years()
        self.root.after(120, self._poll_queue)

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=APP_NAME, font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))
        info = "Przeciągnij XML deklaracji/Subiekta do pierwszego pola. Taryfa jest zapamiętywana w config.json. Słowniki XML są wczytywane z folderu slowniki i folderu programu."
        if not HAS_DND:
            info += "  Uwaga: przeciąganie nie działa bez tkinterdnd2 — użyj przycisków Wybierz."
        ttk.Label(frm, text=info, wraplength=960).pack(anchor="w", pady=(0, 8))

        fields = ttk.LabelFrame(frm, text="Pliki")
        fields.pack(fill="x", pady=(0, 10))
        self._file_row(fields, "XML deklaracji/Subiekta", self.xml_var, self._select_xml, 0)
        self._file_row(fields, "Taryfa CN / taryfa.txt", self.tariff_var, self._select_tariff, 1)
        ttk.Label(fields, text="Rocznik taryfy").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.tariff_year_combo = ttk.Combobox(fields, textvariable=self.tariff_year_var, state="disabled", width=18)
        self.tariff_year_combo.grid(row=2, column=1, sticky="w", padx=10, pady=8)
        ttk.Button(fields, text="Odśwież roczniki", command=self._refresh_tariff_years).grid(row=2, column=2, padx=10, pady=8)
        self._dir_row(fields, "Folder słowników XML", self.dict_dir_var, self._select_dict_dir, 3)

        options = ttk.LabelFrame(frm, text="Ustawienia domyślne dla brakujących danych")
        options.pack(fill="x", pady=(0, 10))
        for col in range(6):
            options.columnconfigure(col, weight=1)

        delivery_values = self.service.dict_codes_for_gui("002")
        transaction_values = self.service.dict_codes_for_gui("004")
        transport_values = self.service.dict_codes_for_gui("005")

        ttk.Label(options, text="Warunki dostawy").grid(row=0, column=0, sticky="w", **pad)
        self.delivery_combo = ttk.Combobox(options, textvariable=self.delivery_var, values=delivery_values, state="normal", width=12)
        self.delivery_combo.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(options, text="Rodzaj transakcji").grid(row=0, column=2, sticky="w", **pad)
        self.transaction_combo = ttk.Combobox(options, textvariable=self.transaction_var, values=transaction_values, state="normal", width=12)
        self.transaction_combo.grid(row=0, column=3, sticky="ew", **pad)

        ttk.Label(options, text="Rodzaj transportu").grid(row=0, column=4, sticky="w", **pad)
        self.transport_combo = ttk.Combobox(options, textvariable=self.transport_var, values=transport_values, state="normal", width=12)
        self.transport_combo.grid(row=0, column=5, sticky="ew", **pad)

        ttk.Label(options, text="Wartość statystyczna").grid(row=1, column=0, sticky="w", **pad)
        ttk.Combobox(options, textvariable=self.stat_mode_var, state="readonly", values=["blank", "copy_invoice_when_required", "copy_invoice_always", "subtract_foreign_transport_by_route"]).grid(row=1, column=1, columnspan=2, sticky="ew", **pad)

        ttk.Label(options, text="CN pewny od %").grid(row=1, column=3, sticky="w", **pad)
        ttk.Entry(options, textvariable=self.confident_var, width=10).grid(row=1, column=4, sticky="ew", **pad)
        ttk.Entry(options, textvariable=self.uncertain_var, width=10).grid(row=1, column=5, sticky="ew", **pad)

        ttk.Label(options, text="Województwo startowe").grid(row=2, column=0, sticky="w", **pad)
        ttk.Combobox(options, textvariable=self.origin_var, values=VOIVODESHIPS, state="normal", width=18).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Label(options, text="Podział kosztu").grid(row=2, column=2, sticky="w", **pad)
        ttk.Combobox(options, textvariable=self.allocation_var, values=["mass_net", "invoice_value"], state="readonly", width=14).grid(row=2, column=3, sticky="ew", **pad)
        ttk.Button(options, text="Edytuj koszty transportu", command=self._open_transport_cost_editor).grid(row=2, column=4, columnspan=2, sticky="ew", **pad)

        checks = ttk.Frame(frm)
        checks.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(checks, text="Otwórz folder po generowaniu", variable=self.open_folder_var).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(checks, text="Ukryj arkusze słownikowe w XLSX", variable=self.hide_dict_var).pack(side="left")
        ttk.Label(checks, text="  Drugi próg: CN niepewny od %, poniżej tego puste/czerwone.").pack(side="left", padx=(12, 0))

        actions = ttk.Frame(frm)
        actions.pack(fill="x", pady=(0, 10))
        self.generate_btn = ttk.Button(actions, text="Generuj XLSX", command=self._generate_clicked)
        self.generate_btn.pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Odśwież listy słowników", command=self._refresh_dictionary_combos).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Otwórz folder programu", command=lambda: self._open_folder(self.service.base_dir)).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Otwórz folder wyników", command=lambda: self._open_folder(resolve_path(self.service.config.get("output_dir", OUTPUT_DIR_NAME), self.service.base_dir))).pack(side="left")

        progress_frame = ttk.Frame(frm)
        progress_frame.pack(fill="x", pady=(0, 10))
        ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100).pack(fill="x", side="left", expand=True, padx=(0, 10))
        ttk.Label(progress_frame, textvariable=self.status_var, width=52).pack(side="right")

        log_frame = ttk.LabelFrame(frm, text="Log")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=14, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log("Program uruchomiony.")
        self.log(f"Folder programu: {self.service.base_dir}")
        self.log(f"Folder słowników: {self.dict_dir_var.get()}")
        self.log(f"Drag & drop: {'TAK' if HAS_DND else 'NIE - zainstaluj tkinterdnd2'}")
        self.log(f"Fuzzy RapidFuzz: {'TAK' if HAS_RAPIDFUZZ else 'NIE - używam difflib'}")

    def _file_row(self, parent: ttk.LabelFrame, label: str, var: tk.StringVar, command: Callable[[], None], row: int) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        ent = ttk.Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(parent, text="Wybierz", command=command).grid(row=row, column=2, padx=10, pady=8)
        self._enable_drop(ent, var)

    def _dir_row(self, parent: ttk.LabelFrame, label: str, var: tk.StringVar, command: Callable[[], None], row: int) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        ent = ttk.Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(parent, text="Wybierz", command=command).grid(row=row, column=2, padx=10, pady=8)
        self._enable_drop(ent, var)

    def _enable_drop(self, widget: Any, var: tk.StringVar) -> None:
        if not HAS_DND:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event: var.set(format_gui_path(path_from_drop_data(self.root, event.data))))
        except Exception:
            pass

    def _open_transport_cost_editor(self) -> None:
        self._save_options_to_config()
        self.route_config = self.service.load_route_cost_config()

        win = tk.Toplevel(self.root)
        win.title("Tabela kosztów transportu poza Polską")
        win.geometry("1080x680")
        win.minsize(960, 580)
        win.transient(self.root)

        top = ttk.Frame(win, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Województwo startowe").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        origin_var = tk.StringVar(value=self.route_config.get("origin_voivodeship", self.origin_var.get()))
        ttk.Combobox(top, textvariable=origin_var, values=VOIVODESHIPS, state="normal", width=22).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(top, text="Podział kosztu na pozycje").grid(row=0, column=2, sticky="w", padx=18, pady=4)
        allocation_var = tk.StringVar(value=self.route_config.get("allocation_basis", self.allocation_var.get()))
        ttk.Combobox(top, textvariable=allocation_var, values=["mass_net", "invoice_value"], state="readonly", width=16).grid(row=0, column=3, sticky="w", padx=6, pady=4)
        use_cap_var = tk.StringVar(value=yes_no(self.route_config.get("use_invoice_cap", True)))
        ttk.Label(top, text="Limit % kosztu").grid(row=0, column=4, sticky="w", padx=18, pady=4)
        max_share_var = tk.StringVar(value=str(self.route_config.get("max_transport_share_pct", 8.0)))
        ttk.Entry(top, textvariable=max_share_var, width=8).grid(row=0, column=5, sticky="w", padx=6, pady=4)
        ttk.Combobox(top, textvariable=use_cap_var, values=["TAK", "NIE"], state="readonly", width=6).grid(row=0, column=6, sticky="w", padx=6, pady=4)
        ttk.Label(top, text="Koszt = koszt zagranicznego odcinka jednego TIR-a. Limit % zabezpiecza przed potraktowaniem małej wysyłki jako pełnego TIR-a.", wraplength=1000).grid(row=1, column=0, columnspan=7, sticky="w", padx=6, pady=(4, 0))

        tree_frame = ttk.Frame(win, padding=(10, 0, 10, 6))
        tree_frame.pack(fill="both", expand=True)
        columns = ("active", "country", "zone", "cost", "trucks", "maxpct", "default", "note")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        headers = {
            "active": "Aktywna",
            "country": "Kraj",
            "zone": "Część kraju / strefa",
            "cost": "Koszt poza PL 1 TIR PLN",
            "trucks": "Liczba transportów",
            "maxpct": "Max % faktur",
            "default": "Domyślna",
            "note": "Uwagi",
        }
        widths = {"active": 80, "country": 70, "zone": 150, "cost": 150, "trucks": 125, "maxpct": 110, "default": 90, "note": 360}
        for c in columns:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c], anchor="w")
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        def insert_route(r: Dict[str, Any]) -> None:
            tree.insert("", "end", values=(
                yes_no(r.get("active", True)),
                norm_text(r.get("country", "")).upper(),
                norm_text(r.get("zone", "STANDARD")).upper(),
                str(int(round(safe_float(r.get("foreign_cost_pln", 0))))),
                str(safe_float(r.get("truck_count", 1))),
                str(safe_float(r.get("max_correction_pct", self.route_config.get("max_transport_share_pct", 8.0)), 8.0)),
                yes_no(r.get("default", False)),
                norm_text(r.get("note", "")),
            ))

        for route in self.route_config.get("routes", []):
            insert_route(route)

        form = ttk.LabelFrame(win, text="Edycja zaznaczonego wiersza", padding=10)
        form.pack(fill="x", padx=10, pady=(0, 10))
        active_var = tk.StringVar(value="TAK")
        country_var = tk.StringVar()
        zone_var = tk.StringVar(value="STANDARD")
        cost_var = tk.StringVar(value="0")
        trucks_var = tk.StringVar(value="1")
        max_pct_var = tk.StringVar(value=str(self.route_config.get("max_transport_share_pct", 8.0)))
        default_var = tk.StringVar(value="NIE")
        note_var = tk.StringVar()
        fields = [
            ("Aktywna", active_var, ["TAK", "NIE"], 0),
            ("Kraj", country_var, None, 1),
            ("Strefa", zone_var, None, 2),
            ("Koszt 1 TIR", cost_var, None, 3),
            ("Liczba transportów", trucks_var, None, 4),
            ("Max %", max_pct_var, None, 5),
            ("Domyślna", default_var, ["TAK", "NIE"], 6),
        ]
        for label, var, values, col in fields:
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="w", padx=5, pady=3)
            if values:
                ttk.Combobox(form, textvariable=var, values=values, state="readonly", width=14).grid(row=1, column=col, sticky="ew", padx=5, pady=3)
            else:
                ttk.Entry(form, textvariable=var, width=16).grid(row=1, column=col, sticky="ew", padx=5, pady=3)
        ttk.Label(form, text="Uwagi").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(form, textvariable=note_var).grid(row=3, column=0, columnspan=7, sticky="ew", padx=5, pady=3)
        for col in range(7):
            form.columnconfigure(col, weight=1)

        def load_selected(_event: Any = None) -> None:
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            active_var.set(vals[0])
            country_var.set(vals[1])
            zone_var.set(vals[2])
            cost_var.set(vals[3])
            trucks_var.set(vals[4])
            max_pct_var.set(vals[5])
            default_var.set(vals[6])
            note_var.set(vals[7])

        def apply_selected() -> None:
            sel = tree.selection()
            if not sel:
                messagebox.showwarning(APP_NAME, "Zaznacz wiersz do edycji.", parent=win)
                return
            country = country_var.get().strip().upper()
            if not country:
                messagebox.showwarning(APP_NAME, "Kod kraju nie może być pusty.", parent=win)
                return
            tree.item(sel[0], values=(
                active_var.get(),
                country,
                zone_var.get().strip().upper() or "STANDARD",
                str(int(round(safe_float(cost_var.get(), 0)))),
                str(max(0.0, safe_float(trucks_var.get(), 1))),
                str(max(0.0, safe_float(max_pct_var.get(), safe_float(max_share_var.get(), 8.0)))),
                default_var.get(),
                note_var.get().strip(),
            ))

        def add_row() -> None:
            tree.insert("", "end", values=("TAK", "DE", "STANDARD", "0", "1", str(max_share_var.get() or "8"), "NIE", "Nowa trasa"))

        def delete_row() -> None:
            sel = tree.selection()
            if not sel:
                return
            for item_id in sel:
                tree.delete(item_id)

        def reset_defaults() -> None:
            if not messagebox.askyesno(APP_NAME, "Zastąpić całą tabelę domyślną listą krajów/stref?", parent=win):
                return
            for item_id in tree.get_children():
                tree.delete(item_id)
            for route in RouteCostManager.default_config().get("routes", []):
                insert_route(route)

        def collect_routes() -> List[Dict[str, Any]]:
            routes: List[Dict[str, Any]] = []
            for item_id in tree.get_children():
                vals = tree.item(item_id, "values")
                routes.append({
                    "active": parse_yes_no(vals[0]),
                    "country": norm_text(vals[1]).upper(),
                    "zone": norm_text(vals[2]).upper() or "STANDARD",
                    "foreign_cost_pln": safe_float(vals[3], 0.0),
                    "truck_count": max(0.0, safe_float(vals[4], 1.0)),
                    "max_correction_pct": max(0.0, safe_float(vals[5], safe_float(max_share_var.get(), 8.0))),
                    "default": parse_yes_no(vals[6]),
                    "note": norm_text(vals[7]),
                })
            return routes

        def save_and_close(close: bool = True) -> None:
            cfg = {
                "origin_voivodeship": origin_var.get().strip().lower() or "podkarpackie",
                "allocation_basis": allocation_var.get().strip() or "invoice_value",
                "use_invoice_cap": parse_yes_no(use_cap_var.get()),
                "max_transport_share_pct": max(0.0, safe_float(max_share_var.get(), 8.0)),
                "routes": collect_routes(),
            }
            self.service.save_route_cost_config(cfg)
            self.route_config = self.service.load_route_cost_config()
            self.origin_var.set(self.route_config.get("origin_voivodeship", "podkarpackie"))
            self.allocation_var.set(self.route_config.get("allocation_basis", "invoice_value"))
            self.log("Zapisano tabelę kosztów transportu.")
            if close:
                win.destroy()

        tree.bind("<<TreeviewSelect>>", load_selected)
        buttons = ttk.Frame(win, padding=(10, 0, 10, 10))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Zastosuj zmiany w wierszu", command=apply_selected).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dodaj wiersz", command=add_row).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Usuń wiersz", command=delete_row).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Przywróć domyślną listę", command=reset_defaults).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Zapisz", command=lambda: save_and_close(False)).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Zapisz i zamknij", command=lambda: save_and_close(True)).pack(side="right", padx=(8, 0))


    def _select_xml(self) -> None:
        p = filedialog.askopenfilename(title="Wybierz XML deklaracji", filetypes=[("XML", "*.xml"), ("Wszystkie pliki", "*.*")])
        if p:
            self.xml_var.set(format_gui_path(p))

    def _select_tariff(self) -> None:
        p = filedialog.askopenfilename(title="Wybierz taryfa.txt", filetypes=[("TXT", "*.txt"), ("Wszystkie pliki", "*.*")])
        if p:
            self.tariff_var.set(format_gui_path(p))
            self._refresh_tariff_years()

    def _select_dict_dir(self) -> None:
        p = filedialog.askdirectory(title="Wybierz folder słowników XML")
        if p:
            self.dict_dir_var.set(format_gui_path(p))
            self._save_options_to_config()
            self._refresh_dictionary_combos()

    def _refresh_dictionary_combos(self) -> None:
        self._save_options_to_config()
        self.delivery_combo.configure(values=self.service.dict_codes_for_gui("002"))
        self.transaction_combo.configure(values=self.service.dict_codes_for_gui("004"))
        self.transport_combo.configure(values=self.service.dict_codes_for_gui("005"))
        self.log("Odświeżono listy domyślnych wartości ze słowników XML.")

    def _refresh_tariff_years(self) -> None:
        previous_year = self._selected_tariff_year() or norm_text(self.service.config.get("tariff_year", ""))
        self.tariff_year_values = {}
        tariff = Path(self.tariff_var.get().strip().strip('"'))
        if not str(tariff) or not tariff.exists():
            self.tariff_year_combo.configure(values=[], state="disabled")
            self.tariff_year_var.set("")
            return
        try:
            options = self.service.tariff_year_options(tariff)
        except Exception as exc:
            self.tariff_year_combo.configure(values=[], state="disabled")
            self.tariff_year_var.set("")
            self.log(f"Nie udało się odczytać roczników taryfy: {exc}")
            return
        labels = [label for label, _year in options]
        self.tariff_year_values = dict(options)
        if not labels:
            self.tariff_year_combo.configure(values=[], state="disabled")
            self.tariff_year_var.set("")
            return
        selected = previous_year if previous_year in [year for _label, year in options] else self.service.resolve_tariff_year(tariff)
        selected_label = next((label for label, year in options if year == selected), labels[0])
        self.tariff_year_combo.configure(values=labels, state="readonly")
        self.tariff_year_var.set(selected_label)

    def _selected_tariff_year(self) -> str:
        return self.tariff_year_values.get(self.tariff_year_var.get(), "")

    def _save_options_to_config(self) -> None:
        tariff_path = format_gui_path(self.tariff_var.get())
        dict_dir = format_gui_path(self.dict_dir_var.get()) or DICT_DIR_NAME
        selected_tariff_year = self._selected_tariff_year()
        tariff = Path(tariff_path.strip('"'))
        if str(tariff) and tariff.exists():
            selected_tariff_year = self.service.tariff_year_config_value(tariff, selected_tariff_year)
        self.tariff_var.set(tariff_path)
        self.dict_dir_var.set(dict_dir)
        self.service.config["tariff_path"] = tariff_path
        self.service.config["tariff_year"] = selected_tariff_year
        self.service.config["dict_dir"] = dict_dir
        self.service.config["default_delivery_terms"] = self.delivery_var.get().strip().upper()
        self.service.config["default_transaction_type"] = self.transaction_var.get().strip()
        self.service.config["default_transport_type"] = self.transport_var.get().strip()
        self.service.config["statistical_value_mode"] = self.stat_mode_var.get().strip()
        self.service.config["origin_voivodeship"] = self.origin_var.get().strip().lower() or "podkarpackie"
        self.service.config["transport_allocation_basis"] = self.allocation_var.get().strip() or "invoice_value"
        self.service.config["transport_use_invoice_cap"] = bool(self.route_config.get("use_invoice_cap", True))
        self.service.config["transport_max_share_pct"] = safe_float(self.route_config.get("max_transport_share_pct", 8.0), 8.0)
        self.service.config["auto_open_output_folder"] = bool(self.open_folder_var.get())
        self.service.config["hide_dictionary_sheets"] = bool(self.hide_dict_var.get())
        try:
            self.service.config["cn_confident_threshold"] = float(str(self.confident_var.get()).replace(",", "."))
            self.service.config["cn_uncertain_threshold"] = float(str(self.uncertain_var.get()).replace(",", "."))
        except Exception:
            self.service.config["cn_confident_threshold"] = 90.0
            self.service.config["cn_uncertain_threshold"] = 80.0
        self.service.save_config()

    def _generate_clicked(self) -> None:
        input_xml = Path(self.xml_var.get().strip().strip('"'))
        tariff = Path(self.tariff_var.get().strip().strip('"'))
        if not str(input_xml) or not input_xml.exists():
            messagebox.showwarning(APP_NAME, "Wskaż poprawny plik XML deklaracji.")
            return
        if not str(tariff) or not tariff.exists():
            messagebox.showwarning(APP_NAME, "Wskaż poprawny plik taryfa.txt.")
            return
        self._refresh_tariff_years()
        self._save_options_to_config()
        self.generate_btn.config(state="disabled")
        self.progress_var.set(0)
        self.log("Start generowania...")
        t = threading.Thread(target=self._generate_worker, args=(input_xml, tariff), daemon=True)
        t.start()

    def _generate_worker(self, input_xml: Path, tariff: Path) -> None:
        try:
            self.service.config = load_json(self.service.config_path, DEFAULT_CONFIG)
            xlsx_path, summary = self.service.generate(input_xml, tariff, progress=self._progress_from_thread)
            self.msg_queue.put(("done", (xlsx_path, summary)))
        except Exception as exc:
            log_path = log_exception(self.service.base_dir, exc)
            self.msg_queue.put(("error", (str(exc), log_path)))

    def _progress_from_thread(self, percent: int, message: str) -> None:
        self.msg_queue.put(("progress", (percent, message)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "progress":
                    percent, message = payload
                    self.progress_var.set(percent)
                    self.status_var.set(message)
                    self.log(message)
                elif kind == "done":
                    xlsx_path, summary = payload
                    self.generate_btn.config(state="normal")
                    self.progress_var.set(100)
                    self.status_var.set("Gotowe")
                    self.log(f"Wygenerowano XLSX: {xlsx_path}")
                    self.log(f"Pozycji: {summary['items_count']}; słowników: {summary['dicts_count']}; taryfa pozycji: {summary['tariff_entries_count']}; czas: {summary['elapsed_seconds']:.2f} s")
                    self.log(f"CN puste/czerwone: {summary['missing_cn_count']}; CN żółte/niepewne: {summary['uncertain_cn_count']}")
                    messagebox.showinfo(APP_NAME, f"Gotowe.\n\nXLSX:\n{xlsx_path}\n\nCzas: {summary['elapsed_seconds']:.2f} s\nCN puste/czerwone: {summary['missing_cn_count']}\nCN żółte/niepewne: {summary['uncertain_cn_count']}")
                    if self.service.config.get("auto_open_output_folder"):
                        self._open_folder(Path(summary["output_dir"]))
                elif kind == "error":
                    self.generate_btn.config(state="normal")
                    msg, log_path = payload
                    self.status_var.set("Błąd")
                    self.log(f"BŁĄD: {msg}")
                    self.log(f"Log błędu: {log_path}")
                    messagebox.showerror(APP_NAME, f"Błąd generowania:\n{msg}\n\nSzczegóły zapisano w:\n{log_path}")
        except queue.Empty:
            pass
        self.root.after(120, self._poll_queue)

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {message}\n")
        self.log_text.see("end")

    def _open_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(path)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            self.log(f"Nie udało się otworzyć folderu: {exc}")

    def run(self) -> None:
        self.root.mainloop()


