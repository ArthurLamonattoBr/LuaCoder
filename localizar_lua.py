import os

def encontrar_lua():
    possiveis_caminhos = [
        r"C:\Program Files (x86)\Lua\5.1\lua.exe",
        r"C:\Program Files\Lua\5.1\lua.exe",
        r"C:\Lua\5.1\lua.exe",
        r"C:\Lua\5.3\lua.exe",
        r"C:\Lua\5.4\lua.exe",
        r"C:\ProgramData\chocolatey\bin\lua.exe",
    ]

    for caminho in possiveis_caminhos:
        if os.path.exists(caminho):
            return caminho

    # Tenta no PATH
    for dir in os.environ.get("PATH", "").split(";"):
        potencial = os.path.join(dir, "lua.exe")
        if os.path.exists(potencial):
            return potencial

    return None

