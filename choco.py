# -------------------------------------------------------- #
import bibliotecas as B

# -------------------------------------------------------- #
# Busca, instala (si falta) y devuelve la ruta de Chocolatey.
def gestionar_chocolatey():
    
    def es_admin():
        try:
            return B.ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def buscar_choco():
        # Busca en variable de entorno o ruta estándar
        install_path = B.os.environ.get('ChocolateyInstall', r'C:\ProgramData\chocolatey')
        path = B.os.path.join(install_path, 'bin', 'choco.exe')
        if B.os.path.exists(path):
            return path
        
        # Intenta en PATH
        path_shutil = B.shutil.which("choco")
        return path_shutil if path_shutil else None

    choco_path = buscar_choco()
    
    if not choco_path:
        print(B.colored("[Info] Chocolatey no detectado. Intentando instalación automática...", "yellow"))
        
        if not es_admin():
            print(B.colored("[Error] Se requieren permisos de ADMIN para instalar Chocolatey.", "red"))
            return None

        try:
            print(B.colored("[Info] Iniciando instalación de Chocolatey...", "yellow"))
            cmd = "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            B.subprocess.run(["powershell", "-Command", cmd], check=True, capture_output=True)
            choco_path = buscar_choco()
            if choco_path:
                print(B.colored("[Info] Chocolatey instalado correctamente.", "green"))
        except Exception as e:
            print(B.colored(f"[Error] Error crítico en la instalación: {e}", "red"))
            return None

    return choco_path

# -------------------------------------------------------- #
if __name__ == "__main__":
    path = gestionar_chocolatey()
    if path:
        print(B.colored(f"Chocolatey listo en: {path}", "green"))
    else:
        print(B.colored("No se pudo configurar Chocolatey.", "red"))



