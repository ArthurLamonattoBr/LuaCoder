import os
import shutil
import subprocess
import threading
import time
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog
from localizar_lua import encontrar_lua

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

arquivo_atual = None
root_path = None

def montar_arvore(tree, caminho, pai=""):
    print(f"[DEBUG] Montando árvore em: {caminho}")
    for child in tree.get_children():
        tree.delete(child)

    try:
        itens = sorted(os.listdir(caminho), key=lambda x: (not os.path.isdir(os.path.join(caminho, x)), x.lower()))
    except PermissionError:
        print(f"[DEBUG] Sem permissão para acessar: {caminho}")
        return

    for item in itens:
        caminho_completo = os.path.join(caminho, item)
        if os.path.isdir(caminho_completo):
            node = tree.insert(pai, "end", text=item, open=False)
            montar_arvore(tree, caminho_completo, node)
        else:
            tree.insert(pai, "end", text=item, open=False)

def caminho_do_item(tree, item_id):
    partes = []
    while item_id:
        partes.insert(0, tree.item(item_id, "text"))
        item_id = tree.parent(item_id)
    caminho = os.path.join(root_path, *partes)
    print(f"[DEBUG] Caminho do item: {caminho}")
    return caminho

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
        print("[DEBUG] Nenhum item selecionado")
        return

    item_id = selecionados[0]
    caminho_completo = caminho_do_item(tree, item_id)
    print(f"[DEBUG] Arquivo selecionado: {caminho_completo}")

    if os.path.isfile(caminho_completo):
        try:
            with open(caminho_completo, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
            text_editor.config(state=NORMAL)
            text_editor.delete("1.0", END)
            text_editor.insert(END, conteudo)
            arquivo_atual = caminho_completo
            root.title(f"Lua IDE - {arquivo_atual}")
            print(f"[DEBUG] Conteúdo do arquivo carregado")
        except Exception as e:
            print(f"[ERRO] Falha ao abrir arquivo: {e}")
            messagebox.showerror("Erro", f"Erro ao abrir arquivo:\n{e}")

def salvar_arquivo():
    global arquivo_atual
    if arquivo_atual:
        try:
            text_editor.config(state=NORMAL)
            conteudo = text_editor.get("1.0", END)
            with open(arquivo_atual, "w", encoding="utf-8") as f:
                f.write(conteudo)
            print(f"[DEBUG] Arquivo salvo: {arquivo_atual}")
            messagebox.showinfo("Salvar", f"Arquivo salvo: {arquivo_atual}")
        except Exception as e:
            print(f"[ERRO] Falha ao salvar arquivo: {e}")
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\n{e}")
    else:
        print("[DEBUG] Arquivo atual indefinido, chamando salvar_como()")
        salvar_como()

def salvar_como():
    global arquivo_atual
    caminho = filedialog.asksaveasfilename(
        defaultextension=".lua",
        filetypes=[("Arquivos Lua", "*.lua"), ("Todos os arquivos", "*.*")]
    )
    if caminho:
        try:
            text_editor.config(state=NORMAL)
            conteudo = text_editor.get("1.0", END)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            arquivo_atual = caminho
            root.title(f"Lua IDE - {arquivo_atual}")
            print(f"[DEBUG] Arquivo salvo como: {arquivo_atual}")
            messagebox.showinfo("Salvar", f"Arquivo salvo: {arquivo_atual}")
        except Exception as e:
            print(f"[ERRO] Falha ao salvar arquivo com outro nome: {e}")
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\n{e}")
    else:
        print("[DEBUG] Salvamento como cancelado pelo usuário")

def run_lua():
    print("[DEBUG] Executando script Lua")
    lua_path = encontrar_lua()
    if not lua_path:
        print("[ERRO] Lua.exe não encontrado")
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
        print("[DEBUG] Script Lua executado com sucesso")
    except Exception as e:
        print(f"[ERRO] Falha ao executar Lua: {e}")
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, f"Erro ao executar Lua:\n{e}")
        output_box.config(state=DISABLED)

def run_lua_comando():
    print("[DEBUG] Executando comando Lua no terminal")
    lua_path = encontrar_lua()
    if not lua_path:
        print("[ERRO] Lua.exe não encontrado para comando")
        messagebox.showerror("Erro", "Lua.exe não encontrado! Configure o caminho.")
        return

    comando = terminal_entry.get()
    if not comando.strip():
        print("[DEBUG] Comando vazio, nada para executar")
        return

    try:
        process = subprocess.run([lua_path, "-e", comando], capture_output=True, text=True)
        output_box.config(state=NORMAL)
        output_box.insert(END, f">>> {comando}\n{process.stdout}{process.stderr}\n")
        output_box.see(END)
        output_box.config(state=DISABLED)
        print(f"[DEBUG] Comando Lua executado: {comando}")
    except Exception as e:
        print(f"[ERRO] Falha ao executar comando Lua: {e}")
        output_box.config(state=NORMAL)
        output_box.insert(END, f"Erro ao executar comando:\n{e}\n")
        output_box.see(END)
        output_box.config(state=DISABLED)

def criar_arquivo():
    print("[DEBUG] Criando novo arquivo")
    selecionados = tree.selection()
    if selecionados:
        item_id = selecionados[0]
        caminho_selecionado = caminho_do_item(tree, item_id)
        if os.path.isdir(caminho_selecionado):
            pasta_destino = caminho_selecionado
        else:
            pasta_destino = os.path.dirname(caminho_selecionado)
    else:
        print("[DEBUG] Nenhum item selecionado, criando na pasta raiz")
        pasta_destino = root_path

    nome_arquivo = simpledialog.askstring("Criar arquivo", f"Nome do novo arquivo (com extensão) dentro de:\n{pasta_destino}")
    if nome_arquivo:
        novo_caminho = os.path.join(pasta_destino, nome_arquivo)
        if os.path.exists(novo_caminho):
            print(f"[ERRO] Arquivo já existe: {novo_caminho}")
            messagebox.showerror("Erro", "Arquivo já existe.")
            return
        try:
            with open(novo_caminho, "w", encoding="utf-8") as f:
                f.write("")
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
            print(f"[DEBUG] Arquivo criado: {novo_caminho}")
            messagebox.showinfo("Criar arquivo", f"Arquivo criado: {novo_caminho}")
        except Exception as e:
            print(f"[ERRO] Falha ao criar arquivo: {e}")
            messagebox.showerror("Erro", f"Falha ao criar arquivo:\n{e}")
    else:
        print("[DEBUG] Criação de arquivo cancelada pelo usuário")

def excluir_item():
    print("[DEBUG] Excluindo item selecionado")
    item_id = tree.focus()
    if not item_id:
        print("[WARN] Nenhum item selecionado para exclusão")
        messagebox.showwarning("Aviso", "Selecione um arquivo ou pasta para excluir.")
        return
    caminho = caminho_do_item(tree, item_id)

    resposta = messagebox.askyesno("Excluir", f"Tem certeza que quer excluir:\n{caminho}?")
    if resposta:
        try:
            if os.path.isdir(caminho):
                shutil.rmtree(caminho)
            else:
                os.remove(caminho)
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
            print(f"[DEBUG] Item excluído: {caminho}")
            messagebox.showinfo("Excluir", "Item excluído com sucesso.")
        except Exception as e:
            print(f"[ERRO] Falha ao excluir item: {e}")
            messagebox.showerror("Erro", f"Falha ao excluir:\n{e}")
    else:
        print("[DEBUG] Exclusão cancelada pelo usuário")

def copiar_arquivo():
    print("[DEBUG] Copiando arquivo selecionado")
    item_id = tree.focus()
    if not item_id:
        print("[WARN] Nenhum arquivo selecionado para copiar")
        messagebox.showwarning("Aviso", "Selecione um arquivo para copiar.")
        return
    caminho = caminho_do_item(tree, item_id)
    if os.path.isdir(caminho):
        print("[WARN] Tentativa de copiar pasta (não suportado)")
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
        print(f"[DEBUG] Arquivo copiado para: {novo_caminho}")
        messagebox.showinfo("Copiar arquivo", f"Arquivo copiado para:\n{novo_caminho}")
    except Exception as e:
        print(f"[ERRO] Falha ao copiar arquivo: {e}")
        messagebox.showerror("Erro", f"Falha ao copiar arquivo:\n{e}")

def popup_menu(event):
    item_id = tree.identify_row(event.y)
    if item_id:
        tree.selection_set(item_id)
    else:
        tree.selection_remove(tree.selection())
    menu_popup.post(event.x_root, event.y_root)

# Função pra abrir a pasta raiz no explorer/gerenciador de arquivos
def abrir_pasta_raiz():
    import platform
    if root_path:
        sistema = platform.system()
        print(f"[DEBUG] Abrindo pasta raiz no Explorer: {root_path} no sistema: {sistema}")
        try:
            if sistema == "Windows":
                os.startfile(root_path)
            elif sistema == "Darwin":  # MacOS
                subprocess.Popen(["open", root_path])
            else:  # Linux e outros
                subprocess.Popen(["xdg-open", root_path])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta raiz:\n{e}")
    else:
        messagebox.showwarning("Aviso", "Nenhuma pasta raiz selecionada.")

# Watchdog para monitorar mudanças fora do app e atualizar árvore
class MeuHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        print(f"[WATCHDOG] Evento detectado: {event.event_type} em {event.src_path}")
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

    thread = threading.Thread(target=observer_thread, daemon=True)
    thread.start()
    print("[DEBUG] Watchdog iniciado")

root = Tk()
root.title("Lua Coder 🚀")

try:
    root.iconbitmap("lua.ico")
    print("[DEBUG] Ícone carregado com sucesso")
except Exception as e:
    print(f"[WARN] Não conseguiu carregar o ícone: {e}")

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

text_editor = Text(root, bg="black", fg="lime", insertbackground="white")
text_editor.pack(side=TOP, expand=True, fill=BOTH)

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

# Menu popup do botão direito
menu_popup = Menu(root, tearoff=0)
menu_popup.add_command(label="Criar arquivo", command=criar_arquivo)
menu_popup.add_command(label="Excluir", command=excluir_item)
menu_popup.add_command(label="Copiar arquivo", command=copiar_arquivo)

iniciar_watcher(root_path)

root.mainloop()
