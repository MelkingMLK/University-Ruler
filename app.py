import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import glob

# --- CONFIGURAZIONE COLORI ---
COLORE_BARRE = "#083330"  # Verde scuro (Sfondo Intestazioni)
COLORE_SFONDO = "#e6d5af"  # Beige (Cornice esterna/Bordi)
COLORE_SFONDO_DATI = "#EAEBE4"  # rgb(234,235,228) - Sfondo interno Tabella
COLORE_DETTAGLI = "#18171E"  # Scuro
COLORE_TESTO_BARRE = "white"
COLORE_INSUBRIA = "#007260"  # Verde Insubria
COLORE_SELEZIONE = "#000000"  # Bordo Selezione

# --- COLORI STATI ---
STATO_SUPERATO = "#90EE90"  # Verde chiaro
STATO_RIFIUTATO = "#FFD700"  # Oro
STATO_NON_SUPERATO = "#FF4444"  # Rosso
STATO_MAI_PROVATO = "#DDDDDD"  # Grigio

# --- SCALA COLORI SFONDO INDICI ---
BG_BORDEAUX = "#800020"
BG_ROSSO = "#FF4444"
BG_ORO = "#FFD700"
BG_VERDE = "#90EE90"
BG_VERDE_BRILL = "#00FF00"

# Cartella dati
CARTELLA_SESSIONI = "sessioni_esami"
if not os.path.exists(CARTELLA_SESSIONI):
    os.makedirs(CARTELLA_SESSIONI)


class FlatHeader(tk.Canvas):
    def __init__(self, parent, text, width_px, command=None, info_command=None):
        super().__init__(parent, bg=COLORE_BARRE, height=30, highlightthickness=0)
        if width_px:
            self.configure(width=width_px)

        self.text_str = text
        self.command = command
        self.info_command = info_command
        self.bg_color = COLORE_BARRE

        self.bind("<Configure>", self.draw)
        self.bind("<Button-1>", self.on_click)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        self.create_rectangle(0, 0, w, h, fill=self.bg_color, outline="")

        text_x = w / 2 - 10 if self.info_command else w / 2
        self.create_text(text_x, h / 2, text=self.text_str, fill="white", font=("Arial", 10, "bold"))

        if self.info_command:
            icon_x = w - 15
            icon_y = h / 2
            r = 8
            self.create_oval(icon_x - r, icon_y - r, icon_x + r, icon_y + r, fill="white", outline="white")
            self.create_text(icon_x, icon_y, text="i", fill=COLORE_BARRE, font=("Times New Roman", 10, "bold italic"))

    def on_click(self, event):
        w = self.winfo_width()
        if self.info_command and event.x > w - 30:
            self.info_command()
        else:
            if self.command: self.command()


class CustomTable(tk.Frame):
    def __init__(self, parent, columns, on_select_callback=None, info_callback=None):
        super().__init__(parent, bg=COLORE_SFONDO_DATI)
        self.columns = columns
        self.on_select_callback = on_select_callback
        self.info_callback = info_callback
        self.data = []
        self.rows_frames = []
        self.selected_row_frame = None
        self.sort_reverse = False
        self.last_sort_col = None

        self.col_pixels = {
            "nome": 250, "gruppo": 120, "peso": 50, "tipo": 80,
            "difficolta": 60, "preparazione": 60, "voto_atteso": 80,
            "rapporto": 90, "storico": 150, "stato": 120
        }

        # HEADER FRAME
        self.header_frame = tk.Frame(self, bg="white")
        self.header_frame.pack(fill=tk.X, side=tk.TOP, pady=0)

        for col_key, col_name in columns:
            w = self.col_pixels.get(col_key, 100)

            is_expandable = (col_key == "nome")

            container = tk.Frame(self.header_frame, bg="white", height=30)
            if not is_expandable:
                container.configure(width=w)
                container.pack_propagate(False)
                container.pack(side=tk.LEFT, padx=(0, 1))
            else:
                container.pack(side=tk.LEFT, padx=(0, 1), fill=tk.X, expand=True)

            inf_cmd = self.info_callback if col_key == "rapporto" else None

            fh = FlatHeader(container, text=col_name, width_px=w if not is_expandable else None,
                            command=lambda c=col_key: self.sort_by(c),
                            info_command=inf_cmd)
            fh.pack(fill=tk.BOTH, expand=True)

        # BODY
        self.canvas = tk.Canvas(self, bg=COLORE_SFONDO_DATI, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORE_SFONDO_DATI)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _get_bg_color(self, col_key, val, item):
        DEFAULT_BG = COLORE_SFONDO_DATI

        if col_key == "stato":
            if val == "SUPERATO": return STATO_SUPERATO
            if val == "RIFIUTATO": return STATO_RIFIUTATO
            if val == "NON SUPERATO": return STATO_NON_SUPERATO
            return STATO_MAI_PROVATO

        if col_key not in ["difficolta", "preparazione", "rapporto"]: return DEFAULT_BG
        try:
            v = float(val)
        except ValueError:
            return DEFAULT_BG

        if col_key == "rapporto":
            if v < 1.0:
                return BG_ROSSO
            elif 1.0 <= v < 1.25:
                return BG_ORO
            elif 1.25 <= v < 2.0:
                return BG_VERDE
            return BG_VERDE_BRILL

        if col_key == "preparazione":
            if v == 0:
                return BG_BORDEAUX
            elif 1 <= v <= 5.75:
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

    def populate(self, data):
        self.data = data
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.rows_frames = []
        self.selected_row_frame = None

        for idx, item in enumerate(data):
            row_frame = tk.Frame(self.scrollable_frame, bg=COLORE_SFONDO_DATI, bd=2, relief="flat")
            row_frame.pack(fill=tk.X, anchor="nw", pady=1)
            self.rows_frames.append((row_frame, item))
            row_frame.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row(f, i))

            for col_key, _ in self.columns:
                val = item.get(col_key, "")
                if col_key == "rapporto" and "rapporto" not in item:
                    d = item.get("difficolta", 0);
                    p = item.get("preparazione", 0)
                    val = f"{(p / d):.2f}" if d > 0 else "100.00"
                elif col_key == "storico" and isinstance(val, list):
                    val = ", ".join(val)
                elif col_key == "stato":
                    concluso = item.get("concluso", False)
                    storico = item.get("storico_voti", [])
                    if concluso:
                        val = "SUPERATO"
                    elif not storico:
                        val = "MAI PROVATO"
                    else:
                        has_passed = any(str(v).isdigit() and int(v) >= 18 for v in storico if str(v).isdigit())
                        if "30L" in storico or "Approvato" in storico: has_passed = True
                        last = storico[-1]
                        last_bad = (last == "Insuff." or (str(last).isdigit() and int(last) < 18))
                        if has_passed:
                            val = "RIFIUTATO"
                        elif last_bad:
                            val = "NON SUPERATO"
                        else:
                            val = "MAI PROVATO"

                bg_color = self._get_bg_color(col_key, val, item)
                fg_color = "white" if bg_color == BG_BORDEAUX else "black"

                w = self.col_pixels.get(col_key, 100)
                is_expandable = (col_key == "nome")

                cell_container = tk.Frame(row_frame, bg=bg_color, height=25)

                if not is_expandable:
                    cell_container.configure(width=w)
                    cell_container.pack_propagate(False)
                    cell_container.pack(side=tk.LEFT, padx=(0, 1))
                else:
                    cell_container.pack(side=tk.LEFT, padx=(0, 1), fill=tk.X, expand=True)

                lbl = tk.Label(cell_container, text=str(val), bg=bg_color, fg=fg_color,
                               anchor="w", padx=5, font=("Arial", 9))
                lbl.pack(fill=tk.BOTH, expand=True)
                lbl.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row(f, i))
                cell_container.bind("<Button-1>", lambda e, f=row_frame, i=item: self.toggle_row(f, i))

    def toggle_row(self, frame, item):
        if self.selected_row_frame == frame:
            frame.config(relief="flat", bg=COLORE_SFONDO_DATI)
            self.selected_row_frame = None
            if self.on_select_callback: self.on_select_callback(None)
            return
        if self.selected_row_frame:
            self.selected_row_frame.config(relief="flat", bg=COLORE_SFONDO_DATI)
        self.selected_row_frame = frame
        frame.config(relief="solid", bd=2, bg="black")
        if self.on_select_callback: self.on_select_callback(item)

    def sort_by(self, col_key):
        if self.last_sort_col == col_key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False; self.last_sort_col = col_key

        def key_func(x):
            val = x.get(col_key, 0)
            if col_key == "rapporto":
                d = x.get("difficolta", 0);
                p = x.get("preparazione", 0)
                return (p / d) if d > 0 else 100.0
            try:
                return float(val)
            except:
                return str(val).lower()

        self.data.sort(key=key_func, reverse=self.sort_reverse)
        self.populate(self.data)


class GestoreEsamiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestore Esami - University Ruler v25")
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

        # TABELLA MAIN
        self.frame_center = tk.Frame(root, bg=COLORE_SFONDO, padx=20, pady=20)
        self.frame_center.pack(fill=tk.BOTH, expand=True)

        cols_def = [
            ("nome", "Materia"),
            ("tipo", "Tipo"), ("difficolta", "Diff"),
            ("preparazione", "Prep"), ("voto_atteso", "Voto Atteso")
        ]
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
        # MODIFICA: "Esame" -> "Scritto"
        self.combo_tipo = ttk.Combobox(input_frame, values=["Scritto", "Parziale", "Orale"], state="readonly", width=15)
        self.combo_tipo.current(0)
        self.combo_tipo.grid(row=0, column=3, padx=5, pady=5, sticky="w")

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

        tk.Label(input_frame, text="Voto Atteso:").grid(row=2, column=4, padx=5, pady=5, sticky="e")
        self.entry_voto_atteso = tk.Entry(input_frame, width=12)
        self.entry_voto_atteso.grid(row=2, column=5, padx=5, pady=5, sticky="w")
        self.entry_voto_atteso.bind("<FocusOut>", self.validate_voto_atteso)

        action_frame = tk.Frame(self.frame_bottom, bg=COLORE_SFONDO)
        action_frame.pack(fill=tk.X, pady=10)
        ttk.Button(action_frame, text="SALVA ESAME", command=self.aggiungi_esame).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="GESTISCI VOTI", command=self.apri_gestione_voti).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="ELIMINA ESAME", command=self.elimina_esame, style="Delete.TButton").pack(
            side=tk.LEFT, padx=5)
        # MODIFICA: Bottone rinominato
        ttk.Button(action_frame, text="CALCULATE", command=self.apri_pagina_calcolaute, style="Insubria.TButton").pack(
            side=tk.RIGHT, padx=5)

        self.aggiorna_lista_sessioni()

    def validate_voto_atteso(self, event):
        val = self.entry_voto_atteso.get().strip()
        if not val: return
        if not val.isdigit():
            self.entry_voto_atteso.delete(0, tk.END)
            self.entry_voto_atteso.insert(0, "18")
        else:
            v = int(val)
            if v < 18 or v > 31:
                self.entry_voto_atteso.delete(0, tk.END)
                self.entry_voto_atteso.insert(0, "18")

    def on_select_row(self, item):
        self.pulisci_input()
        if item is None: return
        self.entry_nome.insert(0, item["nome"])
        self.combo_tipo.set(item.get("tipo", "Scritto"))  # Default cambiato
        self.entry_gruppo.insert(0, item.get("gruppo", ""))
        self.spin_peso.delete(0, tk.END);
        self.spin_peso.insert(0, item.get("peso", 100))
        self.spin_diff.delete(0, tk.END);
        self.spin_diff.insert(0, item["difficolta"])
        self.spin_prep.delete(0, tk.END);
        self.spin_prep.insert(0, item["preparazione"])
        if item.get("voto_atteso"): self.entry_voto_atteso.insert(0, item["voto_atteso"])
        if item.get("concluso", False):
            self.entry_voto_atteso.config(state="disabled", bg="#DDDDDD")
        else:
            self.entry_voto_atteso.config(state="normal", bg="white")

    def pulisci_input(self):
        self.entry_nome.delete(0, tk.END)
        self.entry_gruppo.delete(0, tk.END)
        self.spin_peso.delete(0, tk.END);
        self.spin_peso.insert(0, "100")
        self.combo_tipo.current(0)
        self.spin_diff.delete(0, tk.END);
        self.spin_diff.insert(0, "0.00")
        self.spin_prep.delete(0, tk.END);
        self.spin_prep.insert(0, "0.00")
        self.entry_voto_atteso.config(state="normal", bg="white")
        self.entry_voto_atteso.delete(0, tk.END)

    def aggiorna_lista_sessioni(self):
        files = glob.glob(os.path.join(CARTELLA_SESSIONI, "*.json"))
        sessioni = [os.path.basename(f).replace(".json", "") for f in files]
        self.combo_sessioni['values'] = sessioni
        if sessioni:
            if not self.sessione_corrente or self.sessione_corrente not in sessioni:
                self.combo_sessioni.current(0)
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
                self.aggiorna_lista_sessioni()
                self.combo_sessioni.set(nome.strip())
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
            self.table.populate(self.dati_esami)
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
            diff_str = self.spin_diff.get().replace(",", ".")
            prep_str = self.spin_prep.get().replace(",", ".")
            peso_str = self.spin_peso.get().replace(",", ".")
            diff = float(diff_str) if diff_str else 0.0
            prep = float(prep_str) if prep_str else 0.0
            peso = float(peso_str) if peso_str else 100.0
        except ValueError:
            return messagebox.showerror("Errore", "Indici non validi.")

        tipo = self.combo_tipo.get()
        voto_atteso = self.entry_voto_atteso.get().strip()
        gruppo = self.entry_gruppo.get().strip()

        esame = next((e for e in self.dati_esami if e["nome"] == nome), None)
        if esame:
            esame.update({
                "difficolta": diff, "preparazione": prep, "tipo": tipo,
                "voto_atteso": voto_atteso, "gruppo": gruppo, "peso": peso
            })
        else:
            self.dati_esami.append({
                "nome": nome, "difficolta": diff, "preparazione": prep, "tipo": tipo,
                "voto_atteso": voto_atteso, "gruppo": gruppo, "peso": peso,
                "storico_voti": [], "concluso": False
            })
        self.salva_dati();
        self.table.populate(self.dati_esami);
        self.pulisci_input()

    def elimina_esame(self):
        if not self.table.selected_row_frame: return
        nome = self.entry_nome.get()
        self.dati_esami = [e for e in self.dati_esami if e["nome"] != nome]
        self.salva_dati();
        self.table.populate(self.dati_esami);
        self.pulisci_input()

    def apri_gestione_voti(self):
        nome_esame = self.entry_nome.get()
        esame = next((e for e in self.dati_esami if e["nome"] == nome_esame), None)
        if not esame: return messagebox.showwarning("Attenzione", "Seleziona un esame dalla tabella.")

        win = tk.Toplevel(self.root)
        win.title(f"Voti: {nome_esame}")
        win.geometry("500x500")
        win.configure(bg=COLORE_SFONDO)

        tree_voti = ttk.Treeview(win, columns=("esito",), show="headings", height=10)
        tree_voti.heading("esito", text="Esito")
        tree_voti.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        def ricarica():
            for i in tree_voti.get_children(): tree_voti.delete(i)
            for v in esame.get("storico_voti", []): tree_voti.insert("", tk.END, values=(v,))

        ricarica()

        frame_add = ttk.LabelFrame(win, text="Aggiungi")
        frame_add.pack(pady=10)
        entry_v = tk.Entry(frame_add, width=5)
        entry_v.pack(side=tk.LEFT, padx=5)

        def salva(esito, superato):
            esame["storico_voti"].append(esito)
            if superato:
                risposta = messagebox.askyesno("Esame Superato",
                                               f"Voto inserito: {esito}.\nVuoi accettare il voto e CONCLUDERE l'esame?")
                if risposta:
                    esame["concluso"] = True
                    esame["voto_atteso"] = ""
            self.salva_dati();
            self.table.populate(self.dati_esami);
            ricarica()
            self.on_select_row(esame)

        ttk.Button(frame_add, text="Voto Num.", command=lambda:
        salva(entry_v.get() if int(entry_v.get()) >= 18 else "Insuff.", int(entry_v.get()) >= 18)
        if entry_v.get().isdigit() else None).pack(side=tk.LEFT)
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
        win = tk.Toplevel(self.root)
        win.title("Spiegazione Fattibilità")
        win.geometry("550x450")
        win.configure(bg="white")

        tk.Label(win, text="INTERPRETAZIONE INDICE DI FATTIBILITÀ", bg="white", fg="black",
                 font=("Arial", 14, "bold")).pack(pady=15)

        frame = tk.Frame(win, bg="white", padx=20, pady=20, bd=2, relief="groove")
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(frame, text="Formula: Preparazione / Difficoltà", bg="white", fg="black",
                 font=("Arial", 11, "italic")).pack(pady=(0, 15))

        def add_row(color, range_txt, desc_txt):
            row = tk.Frame(frame, bg="white", pady=5)
            row.pack(fill=tk.X)
            tk.Frame(row, bg=color, width=25, height=25, bd=1, relief="solid").pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=range_txt, bg="white", fg="black", font=("Arial", 10, "bold"), width=12,
                     anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=desc_txt, bg="white", fg="black", font=("Arial", 10), anchor="w").pack(side=tk.LEFT,
                                                                                                      fill=tk.X)

        add_row(BG_ROSSO, "< 1.0", "ALTO RISCHIO: La difficoltà supera la tua preparazione.")
        add_row(BG_ORO, "1.0 - 1.25", "INCERTO: Preparazione appena sufficiente per la difficoltà.")
        add_row(BG_VERDE, "1.25 - 2.0", "BUONO: Sei ben preparato per affrontare l'esame.")
        add_row(BG_VERDE_BRILL, "> 2.0", "OTTIMO: La tua preparazione è molto superiore alla difficoltà.")

        tk.Label(win, text="Più è alto il valore, più sei al sicuro!", bg="white", fg="black", font=("Arial", 10)).pack(
            pady=10)

    def apri_pagina_calcolaute(self):
        if not self.dati_esami: return messagebox.showinfo("Info", "Nessun esame.")
        win = tk.Toplevel(self.root)
        win.title("Calcolaute")
        win.geometry("1100x600")
        win.configure(bg=COLORE_SFONDO)

        tk.Label(win, text="CLASSIFICA FATTIBILITÀ", bg=COLORE_SFONDO, fg=COLORE_INSUBRIA,
                 font=("Arial", 16, "bold")).pack(pady=15)

        cols_calc = [
            ("nome", "Materia"), ("gruppo", "Gruppo"), ("peso", "%"),
            ("difficolta", "Diff"), ("preparazione", "Prep"),
            ("rapporto", "Fattibilità"), ("storico", "Storico"), ("stato", "Stato")
        ]

        def get_ratio(e):
            d = e.get("difficolta", 0);
            p = e.get("preparazione", 0)
            return (p / d) if d > 0 else 100.0

        dati_ordinati = sorted(self.dati_esami, key=get_ratio, reverse=True)

        table_calc = CustomTable(win, cols_calc, info_callback=self.mostra_legenda)
        table_calc.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        table_calc.populate(dati_ordinati)


if __name__ == "__main__":
    root = tk.Tk()
    app = GestoreEsamiApp(root)
    root.mainloop()