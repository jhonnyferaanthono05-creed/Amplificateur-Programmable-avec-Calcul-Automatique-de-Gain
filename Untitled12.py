#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
PROJET 11 : Amplificateur programmable avec calcul automatique de gain
Auteur   : Projet CN GM4 2026
Objectif : Simuler un amplificateur non-inverseur, calculer le gain,
           détecter la saturation et visualiser les signaux.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math

# ─────────────────────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────────────────────
FS       = 10_000        # fréquence d'échantillonnage (Hz)
DURATION = 0.01          # durée du signal affiché (s)
T        = np.linspace(0, DURATION, int(FS * DURATION), endpoint=False)

# Séries E24 (résistances normalisées)
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
DECADES  = [1, 10, 100, 1_000, 10_000, 100_000]

def e24_nearest(value_ohm):
    """Retourne la valeur E24 la plus proche (en ohms)."""
    best = None
    best_err = float("inf")
    for decade in DECADES:
        for base in E24:
            candidate = base * decade
            err = abs(candidate - value_ohm) / value_ohm
            if err < best_err:
                best_err = err
                best = candidate
    return best

# ─────────────────────────────────────────────────────────────────────────────
#  Logique amplificateur
# ─────────────────────────────────────────────────────────────────────────────
def compute_gain(r1, r2):
    """Gain amplificateur non-inverseur : G = 1 + R2/R1"""
    if r1 <= 0:
        raise ValueError("R1 doit être > 0 Ω")
    return 1.0 + r2 / r1

def resistances_from_gain(gain_target, r1=10_000):
    """
    Calcule R2 pour atteindre le gain cible avec R1 fixée.
    Retourne aussi les valeurs E24 normalisées.
    """
    if gain_target < 1:
        raise ValueError("Le gain doit être ≥ 1 pour un ampli non-inverseur")
    r2_ideal = (gain_target - 1) * r1
    r1_e24   = e24_nearest(r1)
    r2_e24   = e24_nearest(r2_ideal) if r2_ideal > 0 else 0
    gain_e24 = 1 + r2_e24 / r1_e24
    return r1, r2_ideal, r1_e24, r2_e24, gain_e24

def generate_signal(freq, amplitude, signal_type="Sinusoïde"):
    """Génère le signal d'entrée."""
    if signal_type == "Sinusoïde":
        return amplitude * np.sin(2 * np.pi * freq * T)
    elif signal_type == "Carré":
        return amplitude * np.sign(np.sin(2 * np.pi * freq * T))
    elif signal_type == "Triangle":
        return amplitude * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * T))
    return amplitude * np.sin(2 * np.pi * freq * T)

def apply_amplifier(vin, gain, vcc):
    """Applique le gain et sature si nécessaire."""
    vout_ideal = vin * gain
    vout       = np.clip(vout_ideal, -vcc, vcc)
    saturated  = np.any(np.abs(vout_ideal) > vcc)
    saturation_ratio = np.mean(np.abs(vout_ideal) > vcc) * 100  # %
    return vout_ideal, vout, saturated, saturation_ratio

def vcc_required(amplitude, gain):
    """Tension d'alimentation minimale nécessaire."""
    return abs(amplitude * gain)

# ─────────────────────────────────────────────────────────────────────────────
#  Interface graphique
# ─────────────────────────────────────────────────────────────────────────────
class AmpliApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Amplificateur Programmable – Projet 11")
        self.configure(bg="#0d1117")
        self.resizable(True, True)
        self._build_ui()
        self.update_plot()

    # ── construction de l'UI ────────────────────────────────────────────────
    def _build_ui(self):
        # Palette de couleurs
        BG      = "#0d1117"
        PANEL   = "#161b22"
        ACCENT  = "#58a6ff"
        GREEN   = "#3fb950"
        RED     = "#f85149"
        YELLOW  = "#d29922"
        FG      = "#e6edf3"
        FG2     = "#8b949e"
        BORDER  = "#30363d"

        self.colors = dict(bg=BG, panel=PANEL, accent=ACCENT,
                           green=GREEN, red=RED, yellow=YELLOW,
                           fg=FG, fg2=FG2, border=BORDER)

        # ── En-tête ─────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=PANEL, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="⚡ AMPLIFICATEUR PROGRAMMABLE",
                 font=("Courier New", 16, "bold"),
                 bg=PANEL, fg=ACCENT).pack(side="left", padx=20)
        tk.Label(header, text="Amplificateur non-inverseur  |  Projet 11  |  CN GM4 2026",
                 font=("Courier New", 9),
                 bg=PANEL, fg=FG2).pack(side="right", padx=20)

        # ── Corps principal ──────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Colonne gauche : paramètres
        left = tk.Frame(body, bg=BG, width=320)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        # Colonne droite : graphique
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_params(left)
        self._build_graph(right)

        # ── Barre de statut ─────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Prêt")
        status_bar = tk.Frame(self, bg=PANEL, pady=5)
        status_bar.pack(fill="x", side="bottom")
        self.status_lbl = tk.Label(status_bar, textvariable=self.status_var,
                                   font=("Courier New", 9),
                                   bg=PANEL, fg=GREEN, anchor="w")
        self.status_lbl.pack(side="left", padx=15)

    def _section(self, parent, title):
        """Crée un cadre section avec titre."""
        C = self.colors
        frame = tk.LabelFrame(parent, text=f"  {title}  ",
                               font=("Courier New", 9, "bold"),
                               bg=C["panel"], fg=C["accent"],
                               bd=1, relief="flat",
                               highlightbackground=C["border"],
                               highlightthickness=1)
        frame.pack(fill="x", pady=4)
        return frame

    def _row(self, parent, label, widget_factory):
        """Ligne label + widget."""
        C = self.colors
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=8, pady=3)
        tk.Label(row, text=label, width=20, anchor="w",
                 font=("Courier New", 9), bg=C["panel"], fg=C["fg"]).pack(side="left")
        w = widget_factory(row)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _entry(self, parent, default, width=12):
        C = self.colors
        e = tk.Entry(parent, width=width,
                     font=("Courier New", 10),
                     bg="#1c2128", fg=C["fg"],
                     insertbackground=C["accent"],
                     relief="flat", bd=4)
        e.insert(0, default)
        return e

    def _build_params(self, parent):
        C = self.colors

        # ── MODE ─────────────────────────────────────────────────────────────
        sec = self._section(parent, "MODE DE SAISIE")
        self.mode_var = tk.StringVar(value="resistances")
        modes = [("Résistances R1, R2", "resistances"),
                 ("Gain cible",         "gain")]
        row = tk.Frame(sec, bg=C["panel"])
        row.pack(fill="x", padx=8, pady=4)
        for txt, val in modes:
            rb = tk.Radiobutton(row, text=txt, variable=self.mode_var, value=val,
                                command=self._toggle_mode,
                                font=("Courier New", 9),
                                bg=C["panel"], fg=C["fg"],
                                activebackground=C["panel"],
                                selectcolor=C["bg"])
            rb.pack(side="left", padx=6)

        # ── RÉSISTANCES ───────────────────────────────────────────────────────
        self.sec_r = self._section(parent, "RÉSISTANCES")
        self.e_r1 = self._row(self.sec_r, "R1 (Ω)",
                               lambda p: self._entry(p, "10000"))
        self.e_r2 = self._row(self.sec_r, "R2 (Ω)",
                               lambda p: self._entry(p, "90000"))

        # ── GAIN CIBLE ────────────────────────────────────────────────────────
        self.sec_g = self._section(parent, "GAIN CIBLE")
        self.e_gain_target = self._row(self.sec_g, "Gain souhaité",
                                        lambda p: self._entry(p, "10"))
        self.e_r1_base = self._row(self.sec_g, "R1 de base (Ω)",
                                    lambda p: self._entry(p, "10000"))
        self.sec_g.pack_forget()   # masqué par défaut

        # ── SIGNAL D'ENTRÉE ───────────────────────────────────────────────────
        sec_sig = self._section(parent, "SIGNAL D'ENTRÉE")
        self.e_freq = self._row(sec_sig, "Fréquence (Hz)",
                                 lambda p: self._entry(p, "500"))
        self.e_ampl = self._row(sec_sig, "Amplitude (V)",
                                 lambda p: self._entry(p, "0.1"))
        self.sig_type = tk.StringVar(value="Sinusoïde")
        row2 = tk.Frame(sec_sig, bg=C["panel"])
        row2.pack(fill="x", padx=8, pady=3)
        tk.Label(row2, text="Forme d'onde", width=20, anchor="w",
                 font=("Courier New", 9), bg=C["panel"], fg=C["fg"]).pack(side="left")
        cb = ttk.Combobox(row2, textvariable=self.sig_type,
                          values=["Sinusoïde", "Carré", "Triangle"],
                          state="readonly", width=14,
                          font=("Courier New", 9))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.update_plot())

        # ── ALIMENTATION ──────────────────────────────────────────────────────
        sec_pwr = self._section(parent, "ALIMENTATION")
        self.e_vcc = self._row(sec_pwr, "±Vcc (V)",
                                lambda p: self._entry(p, "15"))

        # ── BOUTON CALCULER ───────────────────────────────────────────────────
        tk.Button(parent, text="▶  CALCULER & AFFICHER",
                  command=self.update_plot,
                  font=("Courier New", 11, "bold"),
                  bg=C["accent"], fg=C["bg"],
                  activebackground="#79c0ff",
                  relief="flat", pady=8, cursor="hand2"
                  ).pack(fill="x", pady=8, padx=4)

        # ── RÉSULTATS ─────────────────────────────────────────────────────────
        sec_res = self._section(parent, "RÉSULTATS")
        self.lbl_gain   = self._result_label(sec_res, "Gain calculé")
        self.lbl_vout_p = self._result_label(sec_res, "Vout_pic (V)")
        self.lbl_vcc_m  = self._result_label(sec_res, "Vcc min. requis (V)")
        self.lbl_sat    = self._result_label(sec_res, "Saturation")
        self.lbl_r1e24  = self._result_label(sec_res, "R1 normalisée E24 (Ω)")
        self.lbl_r2e24  = self._result_label(sec_res, "R2 normalisée E24 (Ω)")
        self.lbl_gain24 = self._result_label(sec_res, "Gain avec E24")

    def _result_label(self, parent, label):
        C = self.colors
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=label + " :", width=24, anchor="w",
                 font=("Courier New", 8), bg=C["panel"], fg=C["fg2"]).pack(side="left")
        val = tk.Label(row, text="—", anchor="w",
                       font=("Courier New", 9, "bold"),
                       bg=C["panel"], fg=C["accent"])
        val.pack(side="left")
        return val

    def _build_graph(self, parent):
        C = self.colors
        self.fig = Figure(figsize=(7, 5.5), facecolor=C["bg"])
        self.ax1 = self.fig.add_subplot(311)
        self.ax2 = self.fig.add_subplot(312)
        self.ax3 = self.fig.add_subplot(313)
        self.fig.tight_layout(pad=2.5)

        canvas = FigureCanvasTkAgg(self.fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas = canvas

    # ── alternance de mode ───────────────────────────────────────────────────
    def _toggle_mode(self):
        if self.mode_var.get() == "resistances":
            self.sec_r.pack(fill="x", pady=4, after=None)
            self.sec_g.pack_forget()
        else:
            self.sec_g.pack(fill="x", pady=4, after=None)
            self.sec_r.pack_forget()
        # réordonne manuellement (pack après le mode)
        self._reorder_sections()

    def _reorder_sections(self):
        """Ré-empile les sections dans l'ordre."""
        pass  # géré par pack_forget / pack implicite

    # ── calcul et mise à jour ────────────────────────────────────────────────
    def update_plot(self, *_):
        C = self.colors
        try:
            freq  = float(self.e_freq.get())
            ampl  = float(self.e_ampl.get())
            vcc   = float(self.e_vcc.get())

            if self.mode_var.get() == "resistances":
                r1 = float(self.e_r1.get())
                r2 = float(self.e_r2.get())
                gain = compute_gain(r1, r2)
                r1_e24, r2_e24, gain_e24 = e24_nearest(r1), e24_nearest(r2), None
                gain_e24 = 1 + r1_e24 / r2_e24 if r2_e24 > 0 else 1.0
                # Recalcul cohérent
                gain_e24 = compute_gain(r1_e24, r2_e24)
            else:
                gain_target = float(self.e_gain_target.get())
                r1_base     = float(self.e_r1_base.get())
                r1, r2_ideal, r1_e24, r2_e24, gain_e24 = resistances_from_gain(gain_target, r1_base)
                r2   = r2_ideal
                gain = gain_target

            vin                           = generate_signal(freq, ampl, self.sig_type.get())
            vout_ideal, vout, sat, sat_pct = apply_amplifier(vin, gain, vcc)
            vcc_min                        = vcc_required(ampl, gain)

        except Exception as ex:
            messagebox.showerror("Erreur de saisie", str(ex))
            return

        # Mise à jour des labels résultats
        self.lbl_gain.config(  text=f"{gain:.4f}", fg=C["accent"])
        self.lbl_vout_p.config(text=f"{abs(ampl*gain):.4f} V", fg=C["accent"])
        self.lbl_vcc_m.config( text=f"±{vcc_min:.2f} V",
                                fg=C["red"] if vcc_min > vcc else C["green"])
        sat_text = f"OUI  ({sat_pct:.1f}% du signal)" if sat else "NON"
        self.lbl_sat.config(text=sat_text, fg=C["red"] if sat else C["green"])
        self.lbl_r1e24.config( text=f"{r1_e24:.0f} Ω", fg=C["fg"])
        self.lbl_r2e24.config( text=f"{r2_e24:.0f} Ω", fg=C["fg"])
        self.lbl_gain24.config(text=f"{gain_e24:.4f}", fg=C["yellow"])

        # Statut
        if sat:
            msg = f"⚠  SATURATION détectée : Vcc doit être ≥ ±{vcc_min:.2f} V"
            self.status_var.set(msg)
            self.status_lbl.config(fg=C["red"])
        else:
            self.status_var.set(f"✔  Signal amplifié sans saturation  |  Gain = {gain:.4f}  |  Vout_pic = {ampl*gain:.4f} V")
            self.status_lbl.config(fg=C["green"])

        # ── Graphiques ───────────────────────────────────────────────────────
        self._plot_signals(vin, vout_ideal, vout, gain, vcc, sat, C)
        self.canvas.draw()

    def _plot_signals(self, vin, vout_ideal, vout, gain, vcc, sat, C):
        for ax in (self.ax1, self.ax2, self.ax3):
            ax.clear()
            ax.set_facecolor(C["bg"])
            for spine in ax.spines.values():
                spine.set_edgecolor(C["border"])
            ax.tick_params(colors=C["fg2"], labelsize=7)
            ax.yaxis.label.set_color(C["fg2"])
            ax.xaxis.label.set_color(C["fg2"])
            ax.title.set_color(C["fg"])

        t_ms = T * 1000   # en ms pour l'affichage

        # — Graphique 1 : Signal d'entrée ─────────────────────────────────────
        self.ax1.plot(t_ms, vin, color=C["accent"], linewidth=1.2, label="Vin")
        self.ax1.set_ylabel("Tension (V)")
        self.ax1.set_title("Signal d'entrée  Vin", fontsize=9)
        self.ax1.axhline(0, color=C["border"], linewidth=0.5)
        leg1 = self.ax1.legend(fontsize=7, facecolor=C["panel"])
        for text in leg1.get_texts(): text.set_color(C["fg"])
        self.ax1.grid(True, color=C["border"], linewidth=0.4, alpha=0.5)

        # — Graphique 2 : Signal de sortie idéal vs saturé ────────────────────
        color_out = C["red"] if sat else C["green"]
        self.ax2.plot(t_ms, vout_ideal, color=C["yellow"], linewidth=1.0,
                      linestyle="--", alpha=0.7, label="Vout idéal (sans sat.)")
        self.ax2.plot(t_ms, vout, color=color_out, linewidth=1.4,
                      label="Vout réel")
        self.ax2.axhline( vcc, color=C["red"], linewidth=0.8, linestyle=":", alpha=0.8, label=f"+Vcc = +{vcc}V")
        self.ax2.axhline(-vcc, color=C["red"], linewidth=0.8, linestyle=":", alpha=0.8, label=f"−Vcc = −{vcc}V")
        self.ax2.set_ylabel("Tension (V)")
        sat_info = "  ⚠ SATURATION" if sat else ""
        self.ax2.set_title(f"Signal de sortie  Vout  (Gain = {gain:.3f}){sat_info}", fontsize=9)
        leg2 = self.ax2.legend(fontsize=7, facecolor=C["panel"])
        for text in leg2.get_texts(): text.set_color(C["fg"])
        self.ax2.grid(True, color=C["border"], linewidth=0.4, alpha=0.5)
        self.ax2.axhline(0, color=C["border"], linewidth=0.5)

        # — Graphique 3 : Diagnostic alimentation ────────────────────────────
        vcc_min_val = abs(np.max(np.abs(vout_ideal)))
        categories  = ["Vcc disponible\n(±V)", "Vcc minimum\nrequis (±V)"]
        values      = [vcc, vcc_min_val]
        bar_colors  = [C["green"], C["red"] if vcc_min_val > vcc else C["accent"]]

        bars = self.ax3.bar(categories, values, color=bar_colors,
                            width=0.4, edgecolor=C["border"], linewidth=0.8)
        for bar, val in zip(bars, values):
            self.ax3.text(bar.get_x() + bar.get_width() / 2,
                          bar.get_height() + max(values) * 0.02,
                          f"+-{val:.2f} V",
                          ha="center", va="bottom",
                          fontsize=9, color=C["fg"],
                          fontfamily="Courier New")

        self.ax3.axhline(vcc, color=C["yellow"], linewidth=1.0,
                         linestyle="--", alpha=0.8, label=f"Limite Vcc = +-{vcc}V")

        if vcc_min_val > vcc:
            msg, msg_color = "SATURATION - Augmenter Vcc !", C["red"]
        else:
            msg, msg_color = "OK - Pas de saturation", C["green"]

        self.ax3.text(0.5, 0.95, msg,
                      transform=self.ax3.transAxes,
                      ha="center", va="top",
                      fontsize=10, color=msg_color,
                      fontfamily="Courier New",
                      bbox=dict(boxstyle="round,pad=0.4",
                                facecolor=C["panel"],
                                edgecolor=msg_color, alpha=0.9))

        self.ax3.set_ylabel("Tension (V)")
        self.ax3.set_title("Diagnostic alimentation", fontsize=9)
        leg3 = self.ax3.legend(fontsize=7, facecolor=C["panel"])
        for text in leg3.get_texts(): text.set_color(C["fg"])
        self.ax3.grid(True, color=C["border"], linewidth=0.4, alpha=0.3, axis="y")
        self.ax3.set_ylim(0, max(values) * 1.35)

        self.fig.tight_layout(pad=2.0)


# ─────────────────────────────────────────────────────────────────────────────
#  Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = AmpliApp()
    app.mainloop()

