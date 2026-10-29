"""
Painel de sincronização de dados — Lucri & CWB Kids
Rode com: python painel.py
"""
import subprocess
import sys
import threading
import os
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS  = os.path.join(BASE_DIR, "scripts")
PYTHON   = sys.executable


def run_script(args, log):
    """Roda um script em thread separada e imprime output no widget de log."""
    # Insere -u (unbuffered) logo após o executável Python
    if len(args) >= 2 and args[0] == PYTHON:
        args = [args[0], "-u"] + list(args[1:])

    def target():
        log_append(log, f"▶ {' '.join(args[0:1] + args[2:])}\n", "cmd")  # omite -u no display
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"          # força UTF-8 em todo o subprocesso
            env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=BASE_DIR,
            )
            for line in proc.stdout:
                log_append(log, line)
            proc.wait()
            if proc.returncode == 0:
                log_append(log, "✔ Concluído.\n\n", "ok")
            else:
                log_append(log, f"✘ Erro (código {proc.returncode})\n\n", "err")
        except Exception as e:
            log_append(log, f"✘ {e}\n\n", "err")

    threading.Thread(target=target, daemon=True).start()


def log_append(log, text, tag=None):
    """Insere texto no log (thread-safe via after)."""
    def _insert():
        log.config(state="normal")
        log.insert("end", text, tag or "")
        log.see("end")
        log.config(state="disabled")
    log.after(0, _insert)


def build_ui():
    root = tk.Tk()
    root.title("Painel de Dados")
    root.resizable(True, True)
    root.state("zoomed")
    root.minsize(700, 400)

    # ── paleta simples ──────────────────────────────────────────────────────
    BG    = "#1e1e2e"
    CARD  = "#2a2a3e"
    ACC   = "#7c6af7"
    FG    = "#cdd6f4"
    MUTED = "#6c7086"
    OK    = "#a6e3a1"
    ERR   = "#f38ba8"
    CMD   = "#89b4fa"

    root.configure(bg=BG)
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame",    background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel",    background=BG,   foreground=FG,    font=("Segoe UI", 10))
    style.configure("Head.TLabel", background=BG, foreground=FG,    font=("Segoe UI", 11, "bold"))
    style.configure("Sub.TLabel",  background=CARD, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("Card.TLabel", background=CARD, foreground=FG,   font=("Segoe UI", 10))
    style.configure("TButton",   background=ACC,  foreground="#fff", font=("Segoe UI", 10, "bold"),
                    padding=(14, 8), relief="flat")
    style.map("TButton", background=[("active", "#6a59e0")])
    style.configure("TEntry",    fieldbackground="#313244", foreground=FG,
                    insertcolor=FG, font=("Segoe UI", 10))

    pad = dict(padx=18, pady=10)

    # ── container principal ─────────────────────────────────────────────────
    outer = ttk.Frame(root, padding=18)
    outer.pack(fill="both", expand=True)

    ttk.Label(outer, text="Painel de Dados", font=("Segoe UI", 14, "bold"),
              foreground=ACC, background=BG).pack(anchor="w", pady=(0, 10))

    # ── linha com cards (esquerda) + log (direita) ──────────────────────────
    sys.path.insert(0, SCRIPTS)
    from cwbkids_commons import parse_env
    from d1_metricas import d1_enabled
    backend_label = "Cloudflare D1" if d1_enabled(parse_env(os.path.join(BASE_DIR, ".env"))) else "Google Sheets"
    ttk.Label(outer, text=f"Destino das métricas: {backend_label}",
              foreground=MUTED, background=BG).pack(anchor="w", pady=(0, 8))

    body = ttk.Frame(outer)
    body.pack(fill="both", expand=True)

    # Coluna esquerda — cards com scroll
    left = ttk.Frame(body)
    left.pack(side="left", fill="both", expand=True)

    canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    main = ttk.Frame(canvas, padding=(0, 0, 12, 0))
    canvas_window = canvas.create_window((0, 0), window=main, anchor="nw")

    def on_frame_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(e):
        canvas.itemconfig(canvas_window, width=e.width)

    main.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    def on_mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    # Coluna direita — log
    log_frame = ttk.Frame(body, padding=(12, 0, 0, 0))
    log_frame.pack(side="right", fill="both", expand=True)

    ttk.Label(log_frame, text="Log", font=("Segoe UI", 9, "bold"), foreground=MUTED,
              background=BG).pack(anchor="w", pady=(0, 2))

    log = scrolledtext.ScrolledText(
        log_frame, state="disabled", width=38, height=10,
        bg="#181825", fg=FG, font=("Consolas", 9),
        relief="flat", bd=0, insertbackground=FG,
    )
    log.tag_config("ok",  foreground=OK)
    log.tag_config("err", foreground=ERR)
    log.tag_config("cmd", foreground=CMD)
    log.pack(fill="both", expand=True)

    # ── seção Meta Ads ───────────────────────────────────────────────────────
    def card(parent, title, subtitle=""):
        f = ttk.Frame(parent, style="Card.TFrame", padding=14)
        f.pack(fill="x", pady=(0, 10))
        ttk.Label(f, text=title, style="Card.TLabel",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        if subtitle:
            ttk.Label(f, text=subtitle, style="Sub.TLabel").pack(anchor="w", pady=(2, 6))
        return f

    # META ADS
    f_meta = card(main, "Meta Ads — Lucri e CWB Kids",
                  "Exporta JSON pela extensão, selecione aqui e clique em importar.")

    json_var = tk.StringVar()
    row_meta = ttk.Frame(f_meta, style="Card.TFrame")
    row_meta.pack(fill="x", pady=(4, 0))

    entry_json = ttk.Entry(row_meta, textvariable=json_var, width=44)
    entry_json.pack(side="left", padx=(0, 6))

    def pick_json():
        path = filedialog.askopenfilename(
            title="Selecionar JSON do Meta Ads",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
        )
        if path:
            json_var.set(path)

    ttk.Button(row_meta, text="Selecionar…", command=pick_json).pack(side="left", padx=(0, 6))

    def import_meta():
        path = json_var.get().strip()
        if not path:
            log_append(log, "⚠ Selecione um arquivo JSON primeiro.\n", "err")
            return
        run_script([PYTHON, os.path.join(SCRIPTS, "meta_from_extension.py"), path], log)

    ttk.Button(row_meta, text="Importar", command=import_meta).pack(side="left")

    # GOOGLE ADS
    f_gads = card(main, "Google Ads — Lucri e CWB Kids",
                  "Deixe as datas em branco para puxar dados de ontem.")

    row_dates = ttk.Frame(f_gads, style="Card.TFrame")
    row_dates.pack(fill="x", pady=(4, 0))

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    ttk.Label(row_dates, text="Início:", style="Card.TLabel").pack(side="left")
    date_start = ttk.Entry(row_dates, width=12)
    date_start.insert(0, yesterday)
    date_start.pack(side="left", padx=(4, 12))

    ttk.Label(row_dates, text="Fim:", style="Card.TLabel").pack(side="left")
    date_end = ttk.Entry(row_dates, width=12)
    date_end.insert(0, yesterday)
    date_end.pack(side="left", padx=(4, 14))

    def sync_gads():
        s = date_start.get().strip()
        e = date_end.get().strip()
        args = [PYTHON, os.path.join(SCRIPTS, "sync_google_ads.py")]
        if s:
            args.append(s)
        if e and e != s:
            args.append(e)
        run_script(args, log)

    ttk.Button(row_dates, text="Sincronizar", command=sync_gads).pack(side="left")

    # GA4 LUCRI
    f_ga4 = card(main, "GA4 — Páginas Lucri",
                 "LP padrão, LP curta, TypeForm e página de obrigado.")

    row_ga4 = ttk.Frame(f_ga4, style="Card.TFrame")
    row_ga4.pack(fill="x", pady=(4, 0))

    ttk.Label(row_ga4, text="Início:", style="Card.TLabel").pack(side="left")
    ga4_start = ttk.Entry(row_ga4, width=12)
    ga4_start.insert(0, yesterday)
    ga4_start.pack(side="left", padx=(4, 12))

    ttk.Label(row_ga4, text="Fim:", style="Card.TLabel").pack(side="left")
    ga4_end = ttk.Entry(row_ga4, width=12)
    ga4_end.insert(0, yesterday)
    ga4_end.pack(side="left", padx=(4, 14))

    def sync_ga4():
        s = ga4_start.get().strip()
        e = ga4_end.get().strip()
        args = [PYTHON, os.path.join(SCRIPTS, "lucri_ga4_sheet_sync.py")]
        if s:
            args.append(s)
        if e and e != s:
            args.append(e)
        run_script(args, log)

    ttk.Button(row_ga4, text="Sincronizar", command=sync_ga4).pack(side="left")

    # GA4 QUIZ LUCRI
    f_quiz = card(main, "GA4 — Quiz LP Lucri",
                  "Contagem por etapa: nome, WhatsApp, empresa, faturamento, desafio.")

    row_quiz = ttk.Frame(f_quiz, style="Card.TFrame")
    row_quiz.pack(fill="x", pady=(4, 0))

    ttk.Label(row_quiz, text="Início:", style="Card.TLabel").pack(side="left")
    quiz_start = ttk.Entry(row_quiz, width=12)
    quiz_start.insert(0, yesterday)
    quiz_start.pack(side="left", padx=(4, 12))

    ttk.Label(row_quiz, text="Fim:", style="Card.TLabel").pack(side="left")
    quiz_end = ttk.Entry(row_quiz, width=12)
    quiz_end.insert(0, yesterday)
    quiz_end.pack(side="left", padx=(4, 14))

    def sync_quiz():
        s = quiz_start.get().strip()
        e = quiz_end.get().strip()
        args = [PYTHON, os.path.join(SCRIPTS, "lucri_ga4_quiz_sync.py")]
        if s:
            args.append(s)
        if e and e != s:
            args.append(e)
        run_script(args, log)

    ttk.Button(row_quiz, text="Sincronizar", command=sync_quiz).pack(side="left")

    # GA4 QUIZ TYPEFORM LUCRI
    f_quiz_tf = card(main, "GA4 — Quiz TypeForm Lucri",
                     "Etapas: nome, whatsapp, empresa, dor, quem_cuida, faturamento, orcamento + desfechos.")

    row_quiz_tf = ttk.Frame(f_quiz_tf, style="Card.TFrame")
    row_quiz_tf.pack(fill="x", pady=(4, 0))

    ttk.Label(row_quiz_tf, text="Início:", style="Card.TLabel").pack(side="left")
    quiz_tf_start = ttk.Entry(row_quiz_tf, width=12)
    quiz_tf_start.insert(0, yesterday)
    quiz_tf_start.pack(side="left", padx=(4, 12))

    ttk.Label(row_quiz_tf, text="Fim:", style="Card.TLabel").pack(side="left")
    quiz_tf_end = ttk.Entry(row_quiz_tf, width=12)
    quiz_tf_end.insert(0, yesterday)
    quiz_tf_end.pack(side="left", padx=(4, 14))

    def sync_quiz_tf():
        s = quiz_tf_start.get().strip()
        e = quiz_tf_end.get().strip()
        args = [PYTHON, os.path.join(SCRIPTS, "lucri_ga4_typeform_quiz_sync.py")]
        if s:
            args.append(s)
        if e and e != s:
            args.append(e)
        run_script(args, log)

    ttk.Button(row_quiz_tf, text="Sincronizar", command=sync_quiz_tf).pack(side="left")

    # NUVEMSHOP CWB KIDS
    f_nuvem = card(main, "Nuvemshop — CWB Kids",
                   "Pedidos e sessões via CSV exportado manualmente.")

    # Linha 1: pedidos/receita por data
    row_nuvem_api = ttk.Frame(f_nuvem, style="Card.TFrame")
    row_nuvem_api.pack(fill="x", pady=(4, 2))

    ttk.Label(row_nuvem_api, text="Início:", style="Card.TLabel").pack(side="left")
    nuvem_start = ttk.Entry(row_nuvem_api, width=12)
    nuvem_start.insert(0, yesterday)
    nuvem_start.pack(side="left", padx=(4, 12))

    ttk.Label(row_nuvem_api, text="Fim:", style="Card.TLabel").pack(side="left")
    nuvem_end = ttk.Entry(row_nuvem_api, width=12)
    nuvem_end.insert(0, yesterday)
    nuvem_end.pack(side="left", padx=(4, 14))

    def sync_nuvem_api():
        s = nuvem_start.get().strip()
        e = nuvem_end.get().strip()
        args = [PYTHON, os.path.join(SCRIPTS, "cwbkids_nuvemshop_sheet_sync.py")]
        if s:
            args.append(s)
        if e and e != s:
            args.append(e)
        run_script(args, log)

    ttk.Button(row_nuvem_api, text="Sincronizar pedidos", command=sync_nuvem_api).pack(side="left")

    # Linha 2: sessões via CSV
    row_nuvem_csv = ttk.Frame(f_nuvem, style="Card.TFrame")
    row_nuvem_csv.pack(fill="x", pady=(2, 0))

    csv_nuvem_var = tk.StringVar()
    ttk.Entry(row_nuvem_csv, textvariable=csv_nuvem_var, width=36).pack(side="left", padx=(0, 6))

    def pick_csv_nuvem():
        path = filedialog.askopenfilename(
            title="Selecionar CSV de Visitas ou Pedidos (Nuvemshop)",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if path:
            csv_nuvem_var.set(path)

    ttk.Button(row_nuvem_csv, text="Selecionar…", command=pick_csv_nuvem).pack(side="left", padx=(0, 6))

    def import_nuvem_sessoes():
        path = csv_nuvem_var.get().strip()
        if not path:
            log_append(log, "⚠ Selecione um arquivo CSV primeiro.\n", "err")
            return
        run_script([PYTHON, os.path.join(SCRIPTS, "cwbkids_nuvemshop_sessoes_sync.py"), path], log)

    ttk.Button(row_nuvem_csv, text="Importar CSV", command=import_nuvem_sessoes).pack(side="left")

    # LEADS
    f_leads = card(main, "Leads Qualificados — Lucri",
                   "Puxa direto do Notion e atualiza Meta Ads + Google Ads.")

    def sync_leads():
        run_script([PYTHON, os.path.join(SCRIPTS, "lucri_crm_notion_sync.py"), "--apply"], log)

    ttk.Button(f_leads, text="Sincronizar leads", command=sync_leads).pack(anchor="w", pady=(4, 0))

    ttk.Button(log_frame, text="Verificar bancos",
               command=lambda: run_script([PYTHON, os.path.join(SCRIPTS, "diagnostico_metricas.py")], log)).pack(anchor="se", pady=(6, 0))

    ttk.Button(log_frame, text="Limpar log",
               command=lambda: (log.config(state="normal"),
                                log.delete("1.0", "end"),
                                log.config(state="disabled"))).pack(anchor="se", pady=(6, 0))

    root.mainloop()


if __name__ == "__main__":
    build_ui()
