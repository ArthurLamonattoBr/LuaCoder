import os
import shutil
import subprocess
import threading
import time
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageTk
from localizar_lua import encontrar_lua

arquivo_atual = None
root_path = None
autocomplete_window = None
autocomplete_listbox = None
autocomplete_start_index = None

keywords = ["function", "end", "if", "then", "else", "elseif", "for", "while", "do", "local", "return", "break"]
functions = ["print", "pairs", "ipairs", "next", "type", "tostring", "tonumber"]

def aplicar_syntax_highlight():
    text_editor.tag_remove("keyword", "1.0", END)
    text_editor.tag_remove("comment", "1.0", END)
    text_editor.tag_remove("string", "1.0", END)
    text_editor.tag_remove("number", "1.0", END)
    text_editor.tag_remove("function", "1.0", END)

    for palavra in keywords:
        start = "1.0"
        while True:
            pos = text_editor.search(rf'\\b{palavra}\\b', start, stopindex=END, regexp=True)
            if not pos:
                break
            end = f"{pos}+{len(palavra)}c"
            text_editor.tag_add("keyword", pos, end)
            start = end

    for palavra in functions:
        start = "1.0"
        while True:
            pos = text_editor.search(rf'\\b{palavra}\\b', start, stopindex=END, regexp=True)
            if not pos:
                break
            end = f"{pos}+{len(palavra)}c"
            text_editor.tag_add("function", pos, end)
            start = end

    start = "1.0"
    while True:
        pos = text_editor.search("--", start, stopindex=END)
        if not pos:
            break
        linha_fim = pos.split('.')[0] + ".end"
        text_editor.tag_add("comment", pos, linha_fim)
        start = linha_fim

    start = "1.0"
    while True:
        pos = text_editor.search(r'"', start, stopindex=END, regexp=True)
        if not pos:
            break
        end = text_editor.search(r'"', f"{pos}+1c", stopindex=END, regexp=True)
        if not end:
            break
        end = f"{end}+1c"
        text_editor.tag_add("string", pos, end)
        start = end

    start = "1.0"
    while True:
        pos = text_editor.search(r'\\b\\d+\\b', start, stopindex=END, regexp=True)
        if not pos:
            break
        end = f"{pos}+{len(text_editor.get(pos, f'{pos} wordend'))}c"
        text_editor.tag_add("number", pos, end)
        start = end

def delayed_highlight():
    time.sleep(0.2)
    root.after(0, aplicar_syntax_highlight)

def on_key_release(event):
    if event.keysym in ["Up", "Down", "Left", "Right", "BackSpace", "Return", "Tab"]:
        return
    threading.Thread(target=delayed_highlight, daemon=True).start()
    autocomplete(event)

def autocomplete(event):
    global autocomplete_window, autocomplete_listbox, autocomplete_start_index
    if autocomplete_window:
        autocomplete_window.destroy()
        autocomplete_window = None
        autocomplete_listbox = None

    pos = text_editor.index(INSERT)
    line, col = map(int, pos.split('.'))
    start_col = col
    while start_col > 0:
        char = text_editor.get(f"{line}.{start_col-1}")
        if not (char.isalnum() or char == "_"):
            break
        start_col -= 1
    palavra = text_editor.get(f"{line}.{start_col}", pos)
    if not palavra:
        return

    sugestoes = [k for k in keywords + functions if k.startswith(palavra)]
    if not sugestoes:
        return

    autocomplete_window = Toplevel(root)
    autocomplete_window.overrideredirect(True)
    autocomplete_window.attributes("-topmost", True)

    try:
        x, y, cx, cy = text_editor.bbox(f"{line}.{start_col}")
        x += root.winfo_rootx()
        y += root.winfo_rooty() + cy
        autocomplete_window.geometry(f"+{x}+{y}")
    except:
        autocomplete_window.destroy()
        autocomplete_window = None
        return

    autocomplete_listbox = Listbox(autocomplete_window, bg="black", fg="lime", selectbackground="gray", activestyle="none")
    for s in sugestoes:
        autocomplete_listbox.insert(END, s)
    autocomplete_listbox.pack()
    autocomplete_listbox.select_set(0)
    autocomplete_start_index = f"{line}.{start_col}"

def global_key_handler(event):
    global autocomplete_window, autocomplete_listbox, autocomplete_start_index
    if autocomplete_window and autocomplete_listbox:
        if event.keysym in ("Return", "Tab"):
            selecionado = autocomplete_listbox.get(autocomplete_listbox.curselection())
            text_editor.delete(autocomplete_start_index, INSERT)
            text_editor.insert(autocomplete_start_index, selecionado)
            autocomplete_window.destroy()
            autocomplete_window = None
            autocomplete_listbox = None
            return "break"
        elif event.keysym == "Escape":
            autocomplete_window.destroy()
            autocomplete_window = None
            autocomplete_listbox = None
            return "break"
        elif event.keysym == "Up":
            idx = autocomplete_listbox.curselection()[0]
            if idx > 0:
                autocomplete_listbox.selection_clear(0, END)
                autocomplete_listbox.select_set(idx - 1)
            return "break"
        elif event.keysym == "Down":
            idx = autocomplete_listbox.curselection()[0]
            if idx < autocomplete_listbox.size() - 1:
                autocomplete_listbox.selection_clear(0, END)
                autocomplete_listbox.select_set(idx + 1)
            return "break"

def montar_arvore(tree, caminho, pai=""):
    for child in tree.get_children(pai):
        tree.delete(child)
    try:
        itens = sorted(os.listdir(caminho), key=lambda x: (not os.path.isdir(os.path.join(caminho, x)), x.lower()))
    except PermissionError:
        return
    for item in itens:
        caminho_completo = os.path.join(caminho, item)
        node = tree.insert(pai, "end", text=item, open=False)
        if os.path.isdir(caminho_completo):
            montar_arvore(tree, caminho_completo, node)

def caminho_do_item(tree, item_id):
    partes = []
    while item_id:
        partes.insert(0, tree.item(item_id, "text"))
        item_id = tree.parent(item_id)
    return os.path.join(root_path, *partes)

def abrir_imagem(caminho_imagem):
    try:
        img_window = Toplevel(root)
        img_window.title(f"Visualizador de Imagem - {os.path.basename(caminho_imagem)}")
        img = Image.open(caminho_imagem)
        img_tk = ImageTk.PhotoImage(img)
        label = Label(img_window, image=img_tk)
        label.image = img_tk
        label.pack()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao abrir imagem:\\n{e}")
def limpar_selecao_e_editor():
    global arquivo_atual
    arquivo_atual = None
    tree.selection_remove(tree.selection())
    text_editor.config(state=NORMAL)
    text_editor.delete("1.0", END)
    root.title("Lua IDE")

def ao_clicar(event):
    global arquivo_atual
    selecionados = tree.selection()
    if not selecionados:
        return
    item_id = selecionados[0]
    caminho_completo = caminho_do_item(tree, item_id)
    if os.path.isfile(caminho_completo):
        ext = os.path.splitext(caminho_completo)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            abrir_imagem(caminho_completo)
            return
        try:
            with open(caminho_completo, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
            text_editor.config(state=NORMAL)
            text_editor.delete("1.0", END)
            text_editor.insert(END, conteudo)
            arquivo_atual = caminho_completo
            root.title(f"Lua IDE - {arquivo_atual}")
            aplicar_syntax_highlight()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo:\\n{e}")

def salvar_arquivo():
    global arquivo_atual
    if arquivo_atual:
        try:
            text_editor.config(state=NORMAL)
            conteudo = text_editor.get("1.0", END)
            with open(arquivo_atual, "w", encoding="utf-8") as f:
                f.write(conteudo)
            aplicar_syntax_highlight()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\\n{e}")
    else:
        salvar_como()

def salvar_como():
    global arquivo_atual
    caminho = filedialog.asksaveasfilename(defaultextension=".lua", filetypes=[("Arquivos Lua", "*.lua"), ("Todos os arquivos", "*.*")])
    if caminho:
        try:
            text_editor.config(state=NORMAL)
            conteudo = text_editor.get("1.0", END)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            arquivo_atual = caminho
            root.title(f"Lua IDE - {arquivo_atual}")
            aplicar_syntax_highlight()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\\n{e}")

def run_lua():
    lua_path = encontrar_lua()
    if not lua_path:
        messagebox.showerror("Erro", "Lua.exe não encontrado! Configure o caminho.")
        return
    with open("temp_script.lua", "w", encoding="utf-8") as f:
        f.write(text_editor.get("1.0", END))
    try:
        process = subprocess.run([lua_path, "temp_script.lua"], capture_output=True, text=True)
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, process.stdout + process.stderr)
        output_box.config(state=DISABLED)
    except Exception as e:
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, f"Erro ao executar Lua:\\n{e}")
        output_box.config(state=DISABLED)

def run_lua_comando():
    lua_path = encontrar_lua()
    if not lua_path:
        messagebox.showerror("Erro", "Lua.exe não encontrado! Configure o caminho.")
        return
    comando = terminal_entry.get()
    if not comando.strip():
        return
    try:
        process = subprocess.run([lua_path, "-e", comando], capture_output=True, text=True)
        output_box.config(state=NORMAL)
        output_box.insert(END, f">>> {comando}\\n{process.stdout}{process.stderr}\\n")
        output_box.see(END)
        output_box.config(state=DISABLED)
    except Exception as e:
        output_box.config(state=NORMAL)
        output_box.insert(END, f"Erro ao executar comando:\\n{e}\\n")
        output_box.see(END)
        output_box.config(state=DISABLED)

def criar_arquivo():
    selecionados = tree.selection()
    if selecionados:
        item_id = selecionados[0]
        caminho_selecionado = caminho_do_item(tree, item_id)
        pasta_destino = caminho_selecionado if os.path.isdir(caminho_selecionado) else os.path.dirname(caminho_selecionado)
    else:
        pasta_destino = root_path
    nome_arquivo = simpledialog.askstring("Criar arquivo", f"Nome do novo arquivo (com extensão) dentro de:\\n{pasta_destino}")
    if nome_arquivo:
        novo_caminho = os.path.join(pasta_destino, nome_arquivo)
        if os.path.exists(novo_caminho):
            messagebox.showerror("Erro", "Arquivo já existe.")
            return
        try:
            with open(novo_caminho, "w", encoding="utf-8") as f:
                f.write("")
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar arquivo:\\n{e}")

def excluir_item():
    item_id = tree.focus()
    if not item_id:
        messagebox.showwarning("Aviso", "Selecione um arquivo ou pasta para excluir.")
        return
    caminho = caminho_do_item(tree, item_id)
    resposta = messagebox.askyesno("Excluir", f"Tem certeza que quer excluir:\\n{caminho}?")
    if resposta:
        try:
            if os.path.isdir(caminho):
                shutil.rmtree(caminho)
            else:
                os.remove(caminho)
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir:\\n{e}")

def copiar_arquivo():
    item_id = tree.focus()
    if not item_id:
        messagebox.showwarning("Aviso", "Selecione um arquivo para copiar.")
        return
    caminho = caminho_do_item(tree, item_id)
    if os.path.isdir(caminho):
        messagebox.showwarning("Aviso", "Copiar pastas não está suportado ainda.")
        return
    pasta = os.path.dirname(caminho)
    nome = os.path.basename(caminho)
    nome_copy = nome + "_copy"
    novo_caminho = os.path.join(pasta, nome_copy)
    contador = 1
    while os.path.exists(novo_caminho):
        novo_caminho = os.path.join(pasta, f"{nome}_copy{contador}")
        contador += 1
    try:
        shutil.copy2(caminho, novo_caminho)
        montar_arvore(tree, root_path)
        limpar_selecao_e_editor()
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao copiar arquivo:\\n{e}")

def popup_menu(event):
    item_id = tree.identify_row(event.y)
    if item_id:
        tree.selection_set(item_id)
    else:
        tree.selection_remove(tree.selection())
    menu_popup.post(event.x_root, event.y_root)

def abrir_pasta_raiz():
    import platform
    if root_path:
        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(root_path)
            elif sistema == "Darwin":
                subprocess.Popen(["open", root_path])
            else:
                subprocess.Popen(["xdg-open", root_path])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta raiz:\\n{e}")
    else:
        messagebox.showwarning("Aviso", "Nenhuma pasta raiz selecionada.")

class MeuHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        def atualizar():
            montar_arvore(tree, root_path)
        root.after(100, atualizar)

def iniciar_watcher(path):
    observer = Observer()
    event_handler = MeuHandler()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    def observer_thread():
        try:
            while True:
                time.sleep(1)
        except:
            observer.stop()
        observer.join()
    threading.Thread(target=observer_thread, daemon=True).start()
root = Tk()
root.title("Lua IDE 🚀")

try:
    root.iconbitmap("lua.ico")
except:
    pass

root.geometry("1000x700")
root_path = filedialog.askdirectory(title="Selecione a pasta raiz")
if not root_path:
    root_path = os.getcwd()

frame_tree = Frame(root, width=300)
frame_tree.pack(side=LEFT, fill=Y)

tree = ttk.Treeview(frame_tree)
tree.pack(expand=True, fill=BOTH)

montar_arvore(tree, root_path)
tree.bind("<<TreeviewSelect>>", ao_clicar)
tree.bind("<Button-3>", popup_menu)

text_editor = Text(root, bg="black", fg="lime", insertbackground="white", undo=True)
text_editor.pack(side=TOP, expand=True, fill=BOTH)

text_editor.tag_configure("keyword", foreground="cyan")
text_editor.tag_configure("function", foreground="magenta")
text_editor.tag_configure("comment", foreground="gray")
text_editor.tag_configure("string", foreground="orange")
text_editor.tag_configure("number", foreground="yellow")

text_editor.bind("<KeyRelease>", on_key_release)
text_editor.bind("<KeyPress>", global_key_handler)

run_button = Button(root, text="Executar Script Lua", command=run_lua)
run_button.pack(pady=5)

output_box = Text(root, height=10, bg="black", fg="white", state=DISABLED)
output_box.pack(expand=False, fill=X)

terminal_frame = Frame(root)
terminal_frame.pack(fill=X, side=BOTTOM)

terminal_entry = Entry(terminal_frame, bg="black", fg="lime", insertbackground="white")
terminal_entry.pack(side=LEFT, fill=X, expand=True, padx=5, pady=5)

terminal_run_button = Button(terminal_frame, text="Rodar Comando Lua", command=run_lua_comando)
terminal_run_button.pack(side=RIGHT, padx=5, pady=5)

menu = Menu(root)
root.config(menu=menu)

arquivo_menu = Menu(menu, tearoff=0)
menu.add_cascade(label="Arquivo", menu=arquivo_menu)
arquivo_menu.add_command(label="Abrir pasta raiz no Explorer", command=abrir_pasta_raiz)
arquivo_menu.add_command(label="Salvar", command=salvar_arquivo)
arquivo_menu.add_command(label="Salvar Como", command=salvar_como)
arquivo_menu.add_separator()
arquivo_menu.add_command(label="Sair", command=root.quit)

menu_popup = Menu(root, tearoff=0)
menu_popup.add_command(label="Criar arquivo", command=criar_arquivo)
menu_popup.add_command(label="Excluir", command=excluir_item)
menu_popup.add_command(label="Copiar arquivo", command=copiar_arquivo)

iniciar_watcher(root_path)
root.mainloop()
