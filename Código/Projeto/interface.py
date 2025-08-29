import tkinter as tk
from tkinter import ttk
from main import main
import sys
import os
import threading
from pathlib import Path
import logging
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)
projeto_dir = Path(__file__).parent.resolve()


# Redirecionamento de saída
class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, string):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, string)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self):
        pass


# Função principal chamada com ano e mês
def executar_main_com_data(ano, mes):
    relatorio_path = projeto_dir / "RESULT" / "RELATORIO_NPP.txt"
    try:
        ano = int(ano)
        mes = int(mes)
        main(ano, mes)

        # Mostrar relatório
        if os.path.exists(relatorio_path):
            with open(relatorio_path, "r", encoding="utf-8") as f:
                conteudo = f.read()
                terminal_output.configure(state="normal")
                terminal_output.insert(
                    tk.END,
                    "\n\n--- Resultados guardados na pasta RESULT ---\n\n\n--- Conteúdo do RELATÓRIO_NPP.txt ---\n",
                )
                terminal_output.insert(tk.END, conteudo)
                terminal_output.configure(state="disabled")
        else:
            terminal_output.insert(tk.END, "\nArquivo de relatório não encontrado.")
    except ValueError:
        terminal_output.insert(tk.END, "Erro: ano e mês devem ser números válidos.\n")


def iniciar_processamento():
    ano = ano_var.get()
    mes = mes_var.get()
    threading.Thread(target=executar_main_com_data, args=(ano, mes)).start()


# Criação da Janela
root = tk.Tk()
root.title("Calculadora de Absorção de CO₂ - Oeiras, Lisboa, Portugal")
root.configure(bg="white")
root.geometry("1000x900")
root.grid_columnconfigure(0, weight=3)
root.grid_columnconfigure(1, weight=1)

icon_path = projeto_dir / "img" / "image-logo.ico"
root.iconbitmap(icon_path)

# titulo
titulo_label = tk.Label(
    root,
    text="Calculadora de Absorção de CO₂ - Oeiras, Lisboa, Portugal",
    font=("Helvetica", 18, "bold"),
    bg="white",
)
titulo_label.grid(row=0, column=0, columnspan=2, pady=(20, 10))

# forms
form_frame = tk.Frame(root, bg="white")
form_frame.grid(row=1, column=0, sticky="nw", padx=20)

# Ano
ttk.Label(form_frame, text="Ano:").grid(
    row=0, column=0, padx=(400, 10), pady=5, sticky="e"
)
ano_var = tk.StringVar()
ano_box = ttk.Combobox(form_frame, textvariable=ano_var, values=["2024"], width=10)
ano_box.grid(row=0, column=1, padx=5, pady=5, sticky="w")
ano_box.current(0)

# Mês
ttk.Label(form_frame, text="Mês:").grid(
    row=1, column=0, padx=(400, 10), pady=5, sticky="e"
)
mes_var = tk.StringVar()
mes_box = ttk.Combobox(
    form_frame, textvariable=mes_var, values=[str(i) for i in range(1, 13)], width=10
)
mes_box.grid(row=1, column=1, padx=5, pady=5, sticky="w")
mes_box.current(0)

# Botão
ttk.Button(form_frame, text="Iniciar", command=iniciar_processamento).grid(
    row=2, column=0, padx=(400, 10), columnspan=2, pady=10
)

# imagem isel
try:
    img_path = projeto_dir / "img" / "ISEL-Logotipo.png"
    if img_path.exists():
        imagem = Image.open(img_path)
        imagem = imagem.resize((285, 108))
        foto = ImageTk.PhotoImage(imagem)
        label_imagem = tk.Label(root, image=foto, bg="white")
        label_imagem.image = foto
        label_imagem.grid(row=1, column=1, rowspan=5, padx=0, pady=25, sticky="ne")
    else:
        logger.warning(f"Imagem não encontrada em: {img_path}")
except Exception as e:
    print(f"Erro ao carregar imagem: {e}")

# t34minal output
output_frame = tk.Frame(root, bg="white")
output_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=0, sticky="nsew")

# Scrollbar
scrollbar = tk.Scrollbar(output_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Caixa de texto
terminal_output = tk.Text(
    output_frame,
    height=44,
    width=110,
    bg="#f5f5f5",
    fg="black",
    wrap="word",
    yscrollcommand=scrollbar.set,
)
terminal_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
terminal_output.configure(state="disabled")

scrollbar.config(command=terminal_output.yview)

# Redirecionar stdout e stderr
sys.stdout = TextRedirector(terminal_output, "stdout")
sys.stderr = TextRedirector(terminal_output, "stderr")

# Iniciar loop
root.mainloop()
