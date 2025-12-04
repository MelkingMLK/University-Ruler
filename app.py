import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import glob
import datetime
import copy

# --- CONFIGURAZIONE COLORI ---
COLORE_BARRE = "#083330"  # Verde scuro header
COLORE_SFONDO = "#e6d5af"  # Beige sfondo app
COLORE_SFONDO_DATI = "#EAEBE4"  # Sfondo righe normali
COLORE_SFONDO_STORICO = "#D3D3D3"  # Grigio per le righe "tendina" (storico)
COLORE_DETTAGLI = "#18171E"  # Scuro
COLORE_TESTO_BARRE = "white"
COLORE_INSUBRIA = "#007260"  # Verde Insubria (frecce)
COLORE_SELEZIONE = "#000000"  # Bordo Selezione

# --- COLORI STATI ---
STATO_SUPERATO = "#90EE90"  # Verde chiaro
STATO_RIFIUTATO = "#FFD700"  # Oro
STATO_NON_SUPERATO = "#FF4444"  # Rosso
STATO_MAI_PROVATO = "#DDDDDD"  # Grigio

# --- SCALA COLORI SFONDO INDICI ---
BG_BORDEAUX = "#800020"  # 0.00 - 0.25 (Critico)
BG_ROSSO = "#FF4444"  # 0.26 - 0.49 (Pericolo)
BG_ORO = "#FFD700"  # 0.50 - 0.69 (Incerto)
BG_VERDE = "#90EE90"  # 0.70 - 0.89 (Sicuro)
BG_VERDE_BRILL = "#00FF00"  # 0.90 - 1.00 (Blindato)

# Cartella dati
CARTELLA_SESSIONI = "sessioni_esami"
if not os.path.exists(CARTELLA_SESSIONI):
    os.makedirs(CARTELLA_SESSIONI)


# --- FUNZIONI LOGICHE ---
def calcola_indice_avanzato(item):
    try:
        p_base = float(item.get("preparazione", 0))
        d_base = float(item.get("difficolta", 0))
        data_str = item.get("data", "")

        giorni_mancanti = 0
        is_passato = False
        is_futuro = False

        if data_str:
            try:
                giorno, mese, anno = map(int, data_str.split('/'))
                data_esame = datetime.date(anno, mese, giorno)
                oggi = datetime.date.today()

                if data_esame < oggi:
                    is_passato = True
                else:
                    is_futuro = True
                    giorni_mancanti = (data_esame - oggi).days
            except ValueError:
                pass

        if is_passato and not is_futuro:
            return 0.0, "PASSATO"

        BONUS_DAILY_PERC = 0.5
        MALUS_INSICUREZZA_PERC = 30.0

        fattore_bonus = giorni_mancanti * (BONUS_DAILY_PERC / 100)
        p_eff = p_base * (1 + fattore_bonus)
        p_eff = min(10.0, p_eff)

        gap_perc = (10.0 - p_base) / 10.0
        fattore_malus = gap_perc * (MALUS_INSICUREZZA_PERC / 100)
        d_eff = d_base * (1 + fattore_malus)

        idx = (p_eff - d_eff + 10) / 20
        idx_finale = max(0.0, min(1.0, idx))
        return idx_finale, f"{idx_finale:.2f}"
    except Exception:
        return 0.0, "ERR"


class FlatHeader(tk.Canvas):
    def __init__(self, parent, text, width_px, command=None, info_command=None, extra_btn=None):
        super().__init__(parent, bg=COLORE_BARRE, height=30, highlightthickness=0)
        if width_px: self.configure(width=width_px)
        self.text_str = text
        self.command = command
        self.info_command = info_command
        self.extra_btn = extra_btn
        self.bind("<Configure>", self.draw)
        self.bind("<Button-1>", self.on_click)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width();
        h = self.winfo_height()
        self.create_rectangle(0, 0, w, h, fill=COLORE_BARRE, outline="")

        text_x = w / 2 - 10 if self.info_command else w / 2
        self.create_text(text_x, h / 2, text=self.text_str, fill="white", font=("Arial", 10, "bold"))

        if self.info_command:
            icon_x = w - 15;
            icon_y = h / 2;
            r = 8
            self.create_oval(icon_x - r, icon_y - r, icon_x + r, icon_y + r, fill="white", outline="white")
            self.create_text(icon_x, icon_y, text="i", fill=COLORE_BARRE, font=("Times New Roman", 10, "bold italic"))

        if self.extra_btn:
            btn_x = w - 15
            btn_txt = self.extra_btn.get('text', '+')
            r = 9
            self.create_oval(btn_x - r, h / 2 - r, btn_x + r, h / 2 + r, fill=COLORE_INSUBRIA, outline="white")
            self.create_text(btn_x, h / 2, text=btn_txt, fill="white", font=("Courier", 12, "bold"))

    def on_click(self, event):
        w = self.winfo_width()
        if self.info_command and event.x > w - 30:
            self.info_command()
        elif self.extra_btn and event.x > w - 30:
            if self.extra_btn.get('command'):
                self.extra_btn['command']()
        elif self.command:
            self.command()


class CustomTable(tk.Frame):
    def __init__(self, parent, columns, on_select_callback=None, info_callback=None, toggle_view_callback=None,
                 is_expanded=False):
        super().__init__(parent, bg=COLORE_SFONDO_DATI)
        self.columns = columns
        self.on_select_callback = on_select_callback
        self.info_callback = info_callback
        self.toggle_view_callback = toggle_view_callback
        self.is_expanded = is_expanded

        self.data = []
        self.rows_frames = []
        self.selected_row_frame = None
        self.expanded_groups = set()

        self.col_pixels = {
            "nome": 220, "gruppo": 100, "peso": 50, "tipo": 80, "data": 90,
            "difficolta": 60, "preparazione": 90, "progresso": 80,
            "voto_atteso": 80, "voto_preso": 80, "rapporto": 90,
            "probabilita": 100,  # Larghezza nuova colonna
            "storico": 150, "stato": 120
        }

        # HEADER
        self.header_frame = tk.Frame(self, bg="white")
        self.header_frame.pack(fill=tk.X, side=tk.TOP, pady=0)
        for col_key, col_name in columns:
            w = self.col_pixels.get(col_key, 100)
            is_expandable = (col_key == "nome")
            container = tk.Frame(self.header_frame, bg="white", height=30)
            if not is_expandable:
                container.configure(width=w);
                container.pack_propagate(False);
                container.pack(side=tk.LEFT, padx=(0, 1))
            else:
                container.pack(side=tk.LEFT, padx=(0, 1), fill=tk.X, expand=True)

            inf_cmd = self.info_callback if col_key == "rapporto" else None

            extra_btn_config = None
            if col_key == "nome" and self.toggle_view_callback:
                sym = "-" if self.is_expanded else "+"
                extra_btn_config = {'text': sym, 'command': self.toggle_view_callback}

            fh = FlatHeader(container, text=col_name, width_px=w if not is_expandable else None,
                            command=None, info_command=inf_cmd, extra_btn=extra_btn_config)
            fh.pack(fill=tk.BOTH, expand=True)

        self.scrollbar_spacer = tk.Frame(self.header_frame, bg="white", width=15)
        self.scrollbar_spacer.pack(side=tk.RIGHT, fill=tk.Y)

        # BODY CANVAS
        self.canvas = tk.Canvas(self, bg=COLORE_SFONDO_DATI, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORE_SFONDO_DATI)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        if event.width > 0:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _get_bg_color(self, col_key, val, item, is_history=False):
        if is_history and col_key not in ["difficolta", "preparazione", "rapporto", "probabilita", "stato"]:
            return COLORE_SFONDO_STORICO

        DEFAULT_BG = COLORE_SFONDO_STORICO if is_history else COLORE_SFONDO_DATI

        if col_key == "stato":
            if val == "SUPERATO": return STATO_SUPERATO
            if val == "RIFIUTATO": return STATO_RIFIUTATO
            if val == "NON SUPERATO": return STATO_NON_SUPERATO
            return STATO_MAI_PROVATO

        # --- GESTIONE COLORI INDICE E PROBABILITÀ ---
        # Applicare lo stesso colore per entrambi
        if col_key == "rapporto" or col_key == "probabilita":
            # Per probabilità dobbiamo calcolare il valore numerico da zero per sicurezza
            # se il valore passato è una stringa %
            check_val = 0.0

            if col_key == "rapporto":
                if val == "PASSATO" or val == "ERR": return "#CCCCCC"
                try:
                    check_val = float(val)
                except:
                    return DEFAULT_BG
            else:  # probabilita
                if val == "-" or val == "ERR": return "#CCCCCC"
                try:
                    # Toglie il % e divide per 100
                    check_val = float(val.replace('%', '')) / 100
                except:
                    return DEFAULT_BG

            if check_val <= 0.25:
                return BG_BORDEAUX
            elif 0.26 <= check_val <= 0.49:
                return BG_ROSSO
            elif 0.50 <= check_val <= 0.69:
                return BG_ORO
            elif 0.70 <= check_val <= 0.89:
                return BG_VERDE
            else:
                return BG_VERDE_BRILL

        if col_key not in ["difficolta", "preparazione"]: return DEFAULT_BG
        try:
            v = float(val)
        except ValueError:
            return DEFAULT_BG

        # --- FIX BUG PREPARAZIONE < 1 ---
        if col_key == "preparazione":
            if v < 1.0:
                return BG_BORDEAUX  # Corretto da v == 0
            elif 1.0 <= v <= 5.75:
                return BG_ROSSO
            elif 6 <= v <= 6.75:
                return BG_ORO
            elif 7 <= v <= 8.75:
                return BG_VERDE
            elif 9 <= v <= 10:
                return BG_VERDE_BRILL

        if col_key == "difficolta":
            if v <= 1.0:
                return BG_VERDE_BRILL
            elif 1.0 < v <= 4.0:
                return BG_VERDE
            elif 4.0 < v <= 6.0:
                return BG_ORO
            elif 6.0 < v <= 9.0:
                return BG_ROSSO
            elif v > 9.0:
                return BG_BORDEAUX
        return DEFAULT_BG

    def toggle_group(self, group_name):
        if group_name in self.expanded_groups:
            self.expanded_groups.remove(group_name)
        else:
            self.expanded_groups.add(group_name)
        self.populate(self.data)

    def populate(self, data):
        self.data = data
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.rows_frames = []
        self.selected_row_frame = None

        groups = {}
        for item in data:
            nome = item.get("nome", "Sconosciuto")
            if nome not in groups: groups[nome] = []
            groups[nome].append(item)

        processed_names = set()
        for main_item in data:
            nome = main_item.get("nome", "Sconosciuto")
            if nome in processed_names: continue
            processed_names.add(nome)

            group_items = groups[nome]
            parent_item = group_items[-1]
            history_items = group_items[:-1]

            self._draw_row(parent_item, is_history=False, has_children=(len(history_items) > 0))

            if nome in self.expanded_groups and len(history_items) > 0:
                for hist_item in reversed(history_items):
                    self._draw_row(hist_item, is_history=True, has_children=False)

    def _determine_status(self, item):
        if item.get("stato_esame"): return item["stato_esame"]
        storico = item.get("storico_voti", [])
        concluso = item.get("concluso", False)
        if not storico: return "MAI PROVATO"
        last = storico[-1]
        is_suff = False
        if str(last).isdigit():
            if int(last) >= 18: is_suff = True
        elif last in ["30L", "Approvato"]:
            is_suff = True
        if not is_suff: return "NON SUPERATO"
        if concluso: return "SUPERATO"
        return "RIFIUTATO"

    def _draw_row(self, item, is_history, has_children):
        row_frame = tk.Frame(self.scrollable_frame, bg=COLORE_SFONDO_DATI, bd=0)
        row_frame.pack(fill=tk.X, anchor="nw", pady=1)
        self.rows_frames.append((row_frame, item))
        row_frame.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row_selection(f, i))

        nome_esame = item.get("nome", "")
        is_expanded = nome_esame in self.expanded_groups

        for col_key, _ in self.columns:
            val = item.get(col_key, "")

            # --- CALCOLI VALORI ---
            idx_val, str_idx = calcola_indice_avanzato(item)

            if col_key == "rapporto":
                val = str_idx

            elif col_key == "probabilita":
                if str_idx == "PASSATO":
                    val = "-"
                elif str_idx == "ERR":
                    val = "ERR"
                else:
                    # idx_val è 0.0 - 1.0
                    val = f"{idx_val * 100:.2f}%"

            elif col_key == "voto_preso":
                storico = item.get("storico_voti", [])
                val = storico[-1] if storico else "-"
            elif col_key == "storico" and isinstance(val, list):
                val = ", ".join(val)
            elif col_key == "progresso":
                val = f"{val}%"
            elif col_key == "stato":
                val = self._determine_status(item)

            bg_color = self._get_bg_color(col_key, val, item, is_history)
            fg_color = "black"
            if bg_color == BG_BORDEAUX: fg_color = "white"
            if is_history and fg_color == "black": fg_color = "#444444"

            w = self.col_pixels.get(col_key, 100)
            is_expandable = (col_key == "nome")

            cell_container = tk.Frame(row_frame, bg=bg_color, height=26)

            if not is_expandable:
                cell_container.configure(width=w);
                cell_container.pack_propagate(False)
                cell_container.pack(side=tk.LEFT, padx=(0, 1))
            else:
                cell_container.pack(side=tk.LEFT, padx=(0, 1), fill=tk.X, expand=True)

            if col_key == "nome":
                inner_frame = tk.Frame(cell_container, bg=bg_color)
                inner_frame.pack(fill=tk.BOTH, expand=True)

                if not is_history and has_children:
                    symbol = "▼" if is_expanded else "▶"
                    lbl_arrow = tk.Label(inner_frame, text=symbol, bg=bg_color, fg=COLORE_INSUBRIA,
                                         font=("Arial", 10, "bold"), cursor="hand2")
                    lbl_arrow.pack(side=tk.LEFT, padx=(5, 5))
                    lbl_arrow.bind("<Button-1>", lambda e, n=nome_esame: self.toggle_group(n))
                elif is_history:
                    tk.Label(inner_frame, text="   ↳", bg=bg_color, fg="#666").pack(side=tk.LEFT)

                lbl_text = tk.Label(inner_frame, text=str(val), bg=bg_color, fg=fg_color, anchor="w",
                                    font=("Arial", 9, "bold" if not is_history else "italic"))
                lbl_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

                lbl_text.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row_selection(f, i))
                inner_frame.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row_selection(f, i))
            else:
                lbl = tk.Label(cell_container, text=str(val), bg=bg_color, fg=fg_color, anchor="w", padx=5,
                               font=("Arial", 9))
                lbl.pack(fill=tk.BOTH, expand=True)
                lbl.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row_selection(f, i))

            cell_container.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row_selection(f, i))

            if col_key == "voto_preso" and item.get("storico_voti"):
                ToolTip(cell_container, "Storico:\n" + "\n".join(item["storico_voti"]))

            # Tooltip su Fattibilità e Probabilità
            if (col_key == "rapporto" or col_key == "probabilita") and val not in ["PASSATO", "ERR", "-"]:
                try:
                    ToolTip(cell_container, f"Indice Reale: {idx_val:.4f}")
                except:
                    pass

            # --- TOOLTIP PESO SU STATO ---
            if col_key == "stato":
                peso = item.get("peso", 100)
                ToolTip(cell_container, f"Peso: {peso}%")

    def toggle_row_selection(self, frame, item):
        if self.selected_row_frame == frame:
            frame.config(relief="flat", bd=0, bg=COLORE_SFONDO_DATI)
            self.selected_row_frame = None
            if self.on_select_callback: self.on_select_callback(None)
            return
        if self.selected_row_frame:
            try:
                self.selected_row_frame.config(relief="flat", bd=0, bg=COLORE_SFONDO_DATI)
            except:
                pass
        self.selected_row_frame = frame
        frame.config(relief="solid", bd=2, bg=COLORE_SELEZIONE)
        if self.on_select_callback: self.on_select_callback(item)


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget;
        self.text = text;
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip);
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_rootx() + 20;
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget);
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, bg="#ffffe0", relief=tk.SOLID, bd=1, font=("Arial", 9)).pack(
            ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window: self.tip_window.destroy(); self.tip_window = None


class GestoreEsamiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestore Esami - University Ruler v47 Final (Probability)")
        self.root.geometry("1200x750")
        self.root.configure(bg=COLORE_SFONDO)

        self.sessione_corrente = None
        self.dati_esami = []

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabel", background=COLORE_SFONDO, foreground=COLORE_DETTAGLI, font=("Arial", 10))
        self.style.configure("TLabelframe", background=COLORE_SFONDO, foreground=COLORE_DETTAGLI)
        self.style.configure("TLabelframe.Label", background=COLORE_SFONDO, foreground=COLORE_DETTAGLI,
                             font=("Arial", 10, "bold"))
        self.style.configure("TButton", background=COLORE_BARRE, foreground=COLORE_TESTO_BARRE, borderwidth=1,
                             font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", COLORE_DETTAGLI)], foreground=[("active", "white")])
        self.style.configure("Delete.TButton", background="#800020", foreground="white")
        self.style.map("Delete.TButton", background=[("active", "#a00000")])
        self.style.configure("Insubria.TButton", background=COLORE_INSUBRIA, foreground="white",
                             font=("Arial", 11, "bold"))
        self.style.map("Insubria.TButton", background=[("active", "#005a4d")])

        # HEADER
        self.frame_top = tk.Frame(root, bg=COLORE_BARRE, pady=10, padx=10)
        self.frame_top.pack(fill=tk.X)
        tk.Label(self.frame_top, text="GESTIONE SESSIONI", bg=COLORE_BARRE, fg=COLORE_TESTO_BARRE,
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)
        self.combo_sessioni = ttk.Combobox(self.frame_top, state="readonly", width=30)
        self.combo_sessioni.pack(side=tk.LEFT, padx=10)
        self.combo_sessioni.bind("<<ComboboxSelected>>", self.carica_sessione)
        ttk.Button(self.frame_top, text="Nuova Sessione", command=self.crea_sessione).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.frame_top, text="Elimina Sessione", command=self.elimina_sessione, style="Delete.TButton").pack(
            side=tk.LEFT, padx=5)

        # TABELLA
        self.frame_center = tk.Frame(root, bg=COLORE_SFONDO, padx=20, pady=20)
        self.frame_center.pack(fill=tk.BOTH, expand=True)
        cols_def = [("nome", "Materia"), ("tipo", "Tipo"), ("data", "Data"), ("difficolta", "Diff"),
                    ("preparazione", "Prep"), ("progresso", "Progresso"), ("voto_atteso", "Voto Atteso")]
        self.table = CustomTable(self.frame_center, cols_def, on_select_callback=self.on_select_row)
        self.table.pack(fill=tk.BOTH, expand=True)

        # INPUT AREA
        self.frame_bottom = tk.Frame(root, bg=COLORE_SFONDO, pady=10)
        self.frame_bottom.pack(fill=tk.X, padx=20, pady=10)
        input_frame = ttk.LabelFrame(self.frame_bottom, text="Dati Esame")
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(input_frame, text="Materia:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_nome = tk.Entry(input_frame, width=30)
        self.entry_nome.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Tipo:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.combo_tipo = ttk.Combobox(input_frame, values=["Scritto", "Parziale", "Orale"], state="readonly", width=15)
        self.combo_tipo.current(0);
        self.combo_tipo.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Data (gg/mm/aaaa):").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.entry_data = tk.Entry(input_frame, width=15)
        self.entry_data.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Gruppo (Opz.):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_gruppo = tk.Entry(input_frame, width=20)
        self.entry_gruppo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Peso %:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.spin_peso = tk.Spinbox(input_frame, from_=0, to=100, increment=5, width=10)
        self.spin_peso.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Difficoltà:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.spin_diff = tk.Spinbox(input_frame, from_=0.0, to=10.0, increment=0.25, format="%.2f", width=10)
        self.spin_diff.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Preparazione:").grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.spin_prep = tk.Spinbox(input_frame, from_=0.0, to=10.0, increment=0.25, format="%.2f", width=10)
        self.spin_prep.grid(row=2, column=3, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Progresso %:").grid(row=2, column=4, padx=5, pady=5, sticky="e")
        self.spin_prog = tk.Spinbox(input_frame, from_=0, to=100, increment=5, width=8)
        self.spin_prog.grid(row=2, column=5, padx=5, pady=5, sticky="w")

        tk.Label(input_frame, text="Voto Atteso:").grid(row=2, column=6, padx=5, pady=5, sticky="e")
        self.entry_voto_atteso = tk.Entry(input_frame, width=8)
        self.entry_voto_atteso.grid(row=2, column=7, padx=5, pady=5, sticky="w")
        self.entry_voto_atteso.bind("<FocusOut>", lambda e: self.validate_generic_grade(e.widget))

        action_frame = tk.Frame(self.frame_bottom, bg=COLORE_SFONDO)
        action_frame.pack(fill=tk.X, pady=10)
        ttk.Button(action_frame, text="SALVA ESAME", command=self.aggiungi_esame).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="GESTISCI VOTI", command=self.apri_gestione_voti).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="ELIMINA ESAME", command=self.elimina_esame, style="Delete.TButton").pack(
            side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="CALCULATE", command=self.apri_pagina_calcolaute, style="Insubria.TButton").pack(
            side=tk.RIGHT, padx=5)

        self.aggiorna_lista_sessioni()

    def validate_generic_grade(self, widget):
        val = widget.get().strip()
        if not val: return
        if not val.isdigit():
            widget.delete(0, tk.END)
        else:
            v = int(val)
            if v < 0 or v > 32: widget.delete(0, tk.END)

    def on_select_row(self, item):
        self.pulisci_input()
        if item is None: return
        self.entry_nome.insert(0, item["nome"])
        self.combo_tipo.set(item.get("tipo", "Scritto"))
        self.entry_gruppo.insert(0, item.get("gruppo", ""))
        self.entry_data.insert(0, item.get("data", ""))
        self.spin_peso.delete(0, tk.END);
        self.spin_peso.insert(0, item.get("peso", 100))
        self.spin_diff.delete(0, tk.END);
        self.spin_diff.insert(0, item["difficolta"])
        self.spin_prep.delete(0, tk.END);
        self.spin_prep.insert(0, item["preparazione"])
        if item.get("voto_atteso"): self.entry_voto_atteso.insert(0, item["voto_atteso"])

        prog = item.get("progresso", 0)
        self.spin_prog.delete(0, tk.END);
        self.spin_prog.insert(0, prog)
        if int(prog) >= 100:
            self.spin_prog.config(state="disabled")
        else:
            self.spin_prog.config(state="normal")

        if item.get("concluso", False):
            self.entry_voto_atteso.config(state="disabled", bg="#DDDDDD")
        else:
            self.entry_voto_atteso.config(state="normal", bg="white")

    def pulisci_input(self):
        self.entry_nome.delete(0, tk.END)
        self.entry_gruppo.delete(0, tk.END)
        self.entry_data.delete(0, tk.END)
        self.spin_peso.delete(0, tk.END);
        self.spin_peso.insert(0, "100")
        self.combo_tipo.current(0)
        self.spin_diff.delete(0, tk.END);
        self.spin_diff.insert(0, "0.00")
        self.spin_prep.delete(0, tk.END);
        self.spin_prep.insert(0, "0.00")
        self.spin_prog.config(state="normal");
        self.spin_prog.delete(0, tk.END);
        self.spin_prog.insert(0, "0")
        self.entry_voto_atteso.config(state="normal", bg="white");
        self.entry_voto_atteso.delete(0, tk.END)

    def aggiorna_lista_sessioni(self):
        files = glob.glob(os.path.join(CARTELLA_SESSIONI, "*.json"))
        sessioni = [os.path.basename(f).replace(".json", "") for f in files]
        self.combo_sessioni['values'] = sessioni
        if sessioni:
            if not self.sessione_corrente or self.sessione_corrente not in sessioni:
                self.combo_sessioni.current(0);
                self.carica_sessione(None)
        else:
            self.combo_sessioni.set('');
            self.sessione_corrente = None;
            self.dati_esami = [];
            self.table.populate([])

    def crea_sessione(self):
        nome = simpledialog.askstring("Nuova Sessione", "Inserisci nome:")
        if nome:
            percorso = os.path.join(CARTELLA_SESSIONI, f"{nome.strip()}.json")
            if not os.path.exists(percorso):
                with open(percorso, 'w') as f:
                    json.dump([], f)
                self.aggiorna_lista_sessioni();
                self.combo_sessioni.set(nome.strip());
                self.carica_sessione(None)
            else:
                messagebox.showerror("Errore", "Esiste già.")

    def elimina_sessione(self):
        if not self.sessione_corrente: return
        if messagebox.askyesno("Conferma", f"Eliminare {self.sessione_corrente}?"):
            try:
                os.remove(os.path.join(CARTELLA_SESSIONI, f"{self.sessione_corrente}.json"))
            except OSError:
                pass
            self.sessione_corrente = None;
            self.dati_esami = [];
            self.pulisci_input();
            self.aggiorna_lista_sessioni()

    def carica_sessione(self, event):
        nome = self.combo_sessioni.get()
        if not nome: return
        self.sessione_corrente = nome
        try:
            with open(os.path.join(CARTELLA_SESSIONI, f"{nome}.json"), 'r') as f:
                self.dati_esami = json.load(f)
            self.table.populate(self.dati_esami);
            self.pulisci_input()
        except:
            self.aggiorna_lista_sessioni()

    def salva_dati(self):
        if self.sessione_corrente:
            with open(os.path.join(CARTELLA_SESSIONI, f"{self.sessione_corrente}.json"), 'w') as f:
                json.dump(self.dati_esami, f, indent=4)

    def aggiungi_esame(self):
        if not self.sessione_corrente: return messagebox.showwarning("Attenzione", "Crea una sessione.")
        nome = self.entry_nome.get().strip()
        if not nome: return messagebox.showerror("Errore", "Nome mancante.")
        try:
            diff = float(self.spin_diff.get().replace(",", ".")) if self.spin_diff.get() else 0.0
            prep = float(self.spin_prep.get().replace(",", ".")) if self.spin_prep.get() else 0.0
            peso = float(self.spin_peso.get().replace(",", ".")) if self.spin_peso.get() else 100.0
            prog_val = self.spin_prog.get()
            prog = int(prog_val) if prog_val and prog_val.isdigit() else 0
        except ValueError:
            return messagebox.showerror("Errore", "Indici non validi.")

        tipo = self.combo_tipo.get();
        data = self.entry_data.get().strip()
        voto_atteso = self.entry_voto_atteso.get().strip();
        gruppo = self.entry_gruppo.get().strip()

        esame_target = None
        if self.table.selected_row_frame:
            for row, item in self.table.rows_frames:
                if row == self.table.selected_row_frame: esame_target = item; break
        else:
            candidates = [e for e in self.dati_esami if e["nome"] == nome]
            if candidates: esame_target = candidates[-1]

        if esame_target and esame_target.get("progresso", 0) >= 100: prog = esame_target["progresso"]

        if esame_target:
            esame_target.update({
                "nome": nome,
                "difficolta": diff, "preparazione": prep, "tipo": tipo, "data": data,
                "voto_atteso": voto_atteso, "gruppo": gruppo, "peso": peso, "progresso": prog
            })
        else:
            self.dati_esami.append({
                "nome": nome, "difficolta": diff, "preparazione": prep, "tipo": tipo, "data": data,
                "voto_atteso": voto_atteso, "gruppo": gruppo, "peso": peso, "progresso": prog,
                "storico_voti": [], "concluso": False
            })
        self.salva_dati();
        self.table.populate(self.dati_esami);
        self.pulisci_input()

    def elimina_esame(self):
        if not self.table.selected_row_frame: return
        esame_da_rimuovere = None
        for row, item in self.table.rows_frames:
            if row == self.table.selected_row_frame: esame_da_rimuovere = item; break
        if esame_da_rimuovere:
            self.dati_esami.remove(esame_da_rimuovere)
            self.salva_dati();
            self.table.populate(self.dati_esami);
            self.pulisci_input()

    def apri_gestione_voti(self):
        esame = None
        if self.table.selected_row_frame:
            for row, item in self.table.rows_frames:
                if row == self.table.selected_row_frame: esame = item; break
        if not esame: return messagebox.showwarning("Attenzione", "Seleziona un esame dalla tabella.")

        win = tk.Toplevel(self.root);
        win.title(f"Voti: {esame['nome']}")
        win.geometry("500x500");
        win.configure(bg=COLORE_SFONDO)

        tree_voti = ttk.Treeview(win, columns=("esito",), show="headings", height=10)
        tree_voti.heading("esito", text="Esito")
        tree_voti.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        def ricarica():
            for i in tree_voti.get_children(): tree_voti.delete(i)
            for v in esame.get("storico_voti", []): tree_voti.insert("", tk.END, values=(v,))

        ricarica()

        frame_add = ttk.LabelFrame(win, text="Aggiungi");
        frame_add.pack(pady=10)
        entry_v = tk.Entry(frame_add, width=5);
        entry_v.pack(side=tk.LEFT, padx=5)
        entry_v.bind("<FocusOut>", lambda e: self.validate_generic_grade(e.widget))

        def crea_copia_esame(esame_orig):
            nuovo = copy.deepcopy(esame_orig)
            nuovo["data"] = "";
            nuovo["preparazione"] = 0.0;
            nuovo["progresso"] = 0
            nuovo["voto_atteso"] = "";
            nuovo["storico_voti"] = [];
            nuovo["concluso"] = False
            if "stato_esame" in nuovo: del nuovo["stato_esame"]
            return nuovo

        def salva(esito, superato):
            esame["storico_voti"].append(esito)
            entry_v.delete(0, tk.END)
            nuovo_tentativo_creato = False
            if not superato:
                risp = messagebox.askyesno("Nuovo Tentativo",
                                           f"Esito: {esito}.\nVuoi creare subito una nuova scheda per il prossimo appello\nmantenendo questa nello storico?")
                if risp:
                    esame["concluso"] = True
                    esame["stato_esame"] = "NON SUPERATO"
                    nuovo_esame = crea_copia_esame(esame)
                    self.dati_esami.append(nuovo_esame)
                    nuovo_tentativo_creato = True
                else:
                    messagebox.showinfo("Info", "Progresso resettato al 20%.")
                    esame["progresso"] = 20
            else:
                risposta = messagebox.askyesno("Esame Superato", f"Voto: {esito}.\nAccetti il voto e CONCLUDI l'esame?")
                if risposta:
                    esame["concluso"] = True;
                    esame["voto_atteso"] = ""
                    esame["stato_esame"] = "SUPERATO"
                else:
                    risp_refuse = messagebox.askyesno("Voto Rifiutato",
                                                      "Hai rifiutato il voto.\nVuoi creare una nuova scheda per il prossimo appello?")
                    if risp_refuse:
                        esame["concluso"] = True
                        esame["stato_esame"] = "RIFIUTATO"
                        nuovo_esame = crea_copia_esame(esame)
                        self.dati_esami.append(nuovo_esame)
                        nuovo_tentativo_creato = True
                    else:
                        messagebox.showinfo("Info", "Progresso resettato al 20%.")
                        esame["progresso"] = 20

            self.salva_dati();
            self.table.populate(self.dati_esami);
            ricarica()
            if nuovo_tentativo_creato:
                self.on_select_row(None)
            else:
                self.on_select_row(esame)

        ttk.Button(frame_add, text="Voto Num.", command=lambda:
        salva(entry_v.get(), int(entry_v.get()) >= 18) if entry_v.get().isdigit() else None).pack(side=tk.LEFT)
        ttk.Button(frame_add, text="Approvato", command=lambda: salva("Approvato", True)).pack(side=tk.LEFT)

        def rimuovi():
            sel = tree_voti.selection()
            if sel:
                val = tree_voti.item(sel[0])['values'][0]
                esame["storico_voti"].remove(str(val))
                self.salva_dati();
                self.table.populate(self.dati_esami);
                ricarica()

        ttk.Button(win, text="Elimina Voto", style="Delete.TButton", command=rimuovi).pack(pady=5)

    def mostra_legenda(self):
        win = tk.Toplevel(self.root);
        win.title("Spiegazione Fattibilità");
        win.geometry("600x600");
        win.configure(bg="white")
        tk.Label(win, text="INDICE DI FATTIBILITÀ (0.00 - 1.00)", bg="white", fg="black",
                 font=("Arial", 14, "bold")).pack(pady=15)
        frame = tk.Frame(win, bg="white", padx=20, pady=20, bd=2, relief="groove");
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        desc_formule = (
            "FORMULE UTILIZZATE:\n\n1. Bonus Tempo (P. Effettiva):\n   P_eff = P_base * (1 + Giorni * 0.005)\n\n"
            "2. Malus Insicurezza (D. Effettiva):\n   Gap = (10 - P_base) / 10\n   D_eff = D_base * (1 + Gap * 0.30)\n\n"
            "3. Indice Finale (0.0 - 1.0):\n   Indice = (P_eff - D_eff + 10) / 20"
        )
        tk.Label(frame, text=desc_formule, bg="white", fg="black", justify="left", font=("Courier New", 10),
                 relief="solid", bd=1, padx=10, pady=10).pack(pady=(0, 20), fill=tk.X)

        def add_row(color, range_txt, label_txt, desc_txt):
            row = tk.Frame(frame, bg="white", pady=5);
            row.pack(fill=tk.X)
            tk.Frame(row, bg=color, width=25, height=25, bd=1, relief="solid").pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=range_txt, bg="white", fg="black", font=("Arial", 10, "bold"), width=10,
                     anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=label_txt, bg="white", fg="black", font=("Arial", 10, "bold"), width=10,
                     anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=desc_txt, bg="white", fg="black", font=("Arial", 9), anchor="w").pack(side=tk.LEFT,
                                                                                                     fill=tk.X)

        add_row(BG_BORDEAUX, "0.00-0.25", "CRITICO", "Impossibile. Serve studio intensivo.")
        add_row(BG_ROSSO, "0.26-0.49", "PERICOLO", "Rischio alto di bocciatura.")
        add_row(BG_ORO, "0.50-0.69", "INCERTO", "Esito dubbio (50/50).")
        add_row(BG_VERDE, "0.70-0.89", "SICURO", "Molto probabile superarlo.")
        add_row(BG_VERDE_BRILL, "0.90+", "BLINDATO", "Successo quasi garantito.")

    def apri_pagina_calcolaute(self):
        if not self.dati_esami: return messagebox.showinfo("Info", "Nessun esame.")
        win = tk.Toplevel(self.root);
        win.title("Calcolaute - Previsionale");
        win.geometry("1100x600");
        win.configure(bg=COLORE_SFONDO)
        tk.Label(win, text="PREVISIONALE ESAMI", bg=COLORE_SFONDO, fg=COLORE_INSUBRIA, font=("Arial", 16, "bold")).pack(
            pady=15)

        # Stato visualizzazione salvato nel Toplevel
        win.show_results = False  # Default: nascondi esiti

        def toggle_view():
            win.show_results = not win.show_results
            render_table()

        def render_table():
            # 1. Colonne dinamiche
            base_cols = [("nome", "Materia"), ("difficolta", "Diff"), ("preparazione", "Prep"),
                         ("rapporto", "Fattibilità"), ("probabilita", "Probabilità")]
            extra_cols = [("voto_preso", "Voto Preso"), ("stato", "Stato")]

            final_cols = base_cols + (extra_cols if win.show_results else [])

            # 2. Cleanup
            for widget in win.winfo_children():
                if isinstance(widget, CustomTable):
                    widget.destroy()

            # 3. Ordinamento
            groups = {}
            for item in self.dati_esami:
                nome = item.get("nome", "Sconosciuto")
                if nome not in groups: groups[nome] = []
                groups[nome].append(item)

            def get_group_score(nome_gruppo):
                items = groups[nome_gruppo]
                active_item = items[-1]
                val, _ = calcola_indice_avanzato(active_item)
                return val

            sorted_names = sorted(groups.keys(), key=get_group_score, reverse=True)
            dati_ordinati = []
            for nome in sorted_names:
                dati_ordinati.extend(groups[nome])

            # 4. Crea Tabella passando il callback
            table_calc = CustomTable(
                win,
                final_cols,
                info_callback=self.mostra_legenda,
                toggle_view_callback=toggle_view,
                is_expanded=win.show_results
            )
            table_calc.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            table_calc.populate(dati_ordinati)

        # Render iniziale
        render_table()


if __name__ == "__main__":
    root = tk.Tk()
    app = GestoreEsamiApp(root)
    root.mainloop()