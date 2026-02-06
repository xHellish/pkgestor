# ---------------------------------------------------- #
# Bibliotecas
import bibliotecas as B
from choco import gestionar_chocolatey
from main import buscar_app_seguro
import threading

# ---------------------------------------------------- #
# Configuración para ocultar ventanas de consola en Windows
def obtener_startup_info():
    if B.os.name == 'nt':  # Si es Windows
        si = B.subprocess.STARTUPINFO()
        si.dwFlags |= B.subprocess.STARTF_USESHOWWINDOW
        return si
    return None

# ---------------------------------------------------- #
# Variables globales para mantener el estado
_window = None
choco_path = None
installed_cache = set()  # Conjunto de paquetes instalados

# ---------------------------------------------------- #
# Funciones internas

# Establece la referencia a la ventana de webview
def set_window(window):
    global _window
    _window = window

# Carga aplicaciones instaladas para mostrar el estado correcto
def _refresh_cache():
    global installed_cache
    try:
        # En Chocolatey 2.4.3+, "choco list" muestra solo paquetes locales por defecto
        # El flag -lo fue removido
        res = B.subprocess.run(
            ["choco", "list"], 
            capture_output=True, text=True, creationflags=B.subprocess.CREATE_NO_WINDOW
        )

        # Parsear el formato de salida: "nombrePaquete version"
        installed_cache = set()

        for line in res.stdout.splitlines():
            line = line.strip()

            # Saltar líneas de cabecera y footer
            if not line or line.startswith('Chocolatey') or 'packages installed' in line:
                
                continue

            # Extraer el nombre del paquete (primera palabra antes del espacio)
            parts = line.split()
            if parts:
                installed_cache.add(parts[0].lower())
        
    except Exception as e:
        installed_cache = set()

# Métodos llamados desde JS

def refresh_installed(*args):
    # Refresca la lista de paquetes instalados
    _refresh_cache()
    return {"status": "success", "count": len(installed_cache)}

def get_installed_packages(*args):
    # Retorna la lista de paquetes instalados con detalles
    try:
        # Usar "choco list" para obtener paquetes instalados con versiones
        res = B.subprocess.run(
            ["choco", "list"], 
            capture_output=True, text=True, creationflags=B.subprocess.CREATE_NO_WINDOW
        )
        
        packages = []
        for line in res.stdout.splitlines():
            line = line.strip()
            # Saltar líneas de cabecera y footer
            if not line or line.startswith('Chocolatey') or 'packages installed' in line:
                continue
            
            # Parsear formato: "nombrePaquete version"
            parts = line.split()
            if len(parts) >= 2:
                pkg_id = parts[0]
                version = parts[1]
                safe_id = pkg_id.replace('.', '_').replace(' ', '_')
                
                packages.append({
                    "id": pkg_id,
                    "safe_id": safe_id,
                    "nombre": pkg_id,
                    "version": version
                })
        
        return packages
    except Exception as e:
        print(f"[ERROR] get_installed_packages: {e}")
        return []

def check_choco(*args):
    # Verifica si Chocolatey está instalado y disponible
    global choco_path
    choco_path = gestionar_chocolatey()
    if choco_path:
        return {"status": "success", "path": choco_path}
    return {"status": "error", "message": "Chocolatey no detectado"}

def buscar(*args):
    # Busca aplicaciones en Chocolatey
    # Extraer el query correcto (args[0] es self cuando se usa type())
    query = args[0] if len(args) == 1 else args[1] if len(args) > 1 else None
    print(f"[DEBUG] buscar() called with query: {query}, args: {args}")
    if not query: 
        print("[DEBUG] Query is empty, returning empty list")
        return []
    
    # Usar la función de main.py
    results = buscar_app_seguro(query)
    print(f"[DEBUG] buscar_app_seguro returned: {type(results)}, length: {len(results) if isinstance(results, list) else 'N/A'}")
    
    if results == -1:
        print("[DEBUG] results == -1, returning empty list")
        return []
    
    # Adaptar formato para el frontend (agregar safe_id y estado instalado)
    resultados = []
    for app in results:
        pkg_id = app['id'].lower()
        safe_id = pkg_id.replace('.', '_').replace(' ', '_')
        is_installed = pkg_id in installed_cache
        
        resultados.append({
            "id": pkg_id,
            "safe_id": safe_id,
            "nombre": app['nombre'],
            "version": app['version'],
            "installed": is_installed,
            "icon": app.get('icon', ''),
            "descripcion": app['descripcion'][:100] + "..." if len(app['descripcion']) > 100 else app['descripcion']
        })
    
    print(f"[DEBUG] Returning {len(resultados)} results")
    return resultados

def instalar(*args):
    # Inicia la instalación de un paquete
    # Extraer parámetros correctos
    pkg_id = args[0] if len(args) == 2 else args[1] if len(args) > 2 else None
    safe_id = args[1] if len(args) == 2 else args[2] if len(args) > 2 else None
    global choco_path
    if not choco_path:
        choco_path = gestionar_chocolatey()
    
    # Ejecutar en hilo para no congelar la barra de progreso
    threading.Thread(target=_proceso_instalacion, args=(pkg_id, safe_id), daemon=True).start()

def desinstalar(*args):
    # Desinstala un paquete y actualiza el cache
    # Extraer parámetros correctos
    pkg_id = args[0] if len(args) == 2 else args[1] if len(args) > 2 else None
    safe_id = args[1] if len(args) == 2 else args[2] if len(args) > 2 else None
    global choco_path
    if not choco_path:
        choco_path = gestionar_chocolatey()
    
    # Ejecutar en hilo para no congelar la barra de progreso
    threading.Thread(target=_proceso_desinstalacion, args=(pkg_id, safe_id), daemon=True).start()

def _proceso_instalacion(pkg_id, safe_id):
    # Proceso de instalación de un paquete
    global installed_cache
    try:
        cmd = [choco_path, "install", pkg_id, "-y", "--no-progress"]

        process = B.subprocess.Popen(
            cmd, 
            stdout=B.subprocess.PIPE, 
            stderr=B.subprocess.STDOUT,
            text=True, 
            creationflags=B.subprocess.CREATE_NO_WINDOW,
            startupinfo=obtener_startup_info()
        )

        # Simulación de progreso basada en la salida de texto
        for line in process.stdout:
            if "Downloading" in line:
                _window.evaluate_js(f"actualizarBarra('{safe_id}', 30, 'Descargando...')")
            elif "Installing" in line:
                _window.evaluate_js(f"actualizarBarra('{safe_id}', 60, 'Instalando...')")
            elif "Verifying" in line:
                _window.evaluate_js(f"actualizarBarra('{safe_id}', 80, 'Verificando...')")

        process.wait()

        if process.returncode == 0 or process.returncode == 3010: # 3010 es reinicio pendiente (éxito)
            installed_cache.add(pkg_id.lower())
            _window.evaluate_js(f"finInstalacion('{safe_id}', true)")
        else:
            _window.evaluate_js(f"finInstalacion('{safe_id}', false)")

    except Exception as e:
        print(e)
        _window.evaluate_js(f"finInstalacion('{safe_id}', false)")

def _proceso_desinstalacion(pkg_id, safe_id):
    # Proceso de desinstalación de un paquete
    global installed_cache
    try:
        cmd = [choco_path, "uninstall", pkg_id, "-y", "--no-progress"]

        process = B.subprocess.Popen(
            cmd, 
            stdout=B.subprocess.PIPE, 
            stderr=B.subprocess.STDOUT,
            text=True, 
            creationflags=B.subprocess.CREATE_NO_WINDOW,
            startupinfo=obtener_startup_info()
        )

        # Monitorear el proceso
        for line in process.stdout:
            if "Uninstalling" in line:
                _window.evaluate_js(f"actualizarBarra('{safe_id}', 50, 'Desinstalando...')")
            elif "Success" in line or "successfully" in line:
                _window.evaluate_js(f"actualizarBarra('{safe_id}', 80, 'Finalizando...')")

        process.wait()

        if process.returncode == 0:
            # Actualizar cache localmente
            installed_cache.discard(pkg_id.lower())
            _window.evaluate_js(f"finDesinstalacion('{safe_id}', true)")
        else:
            _window.evaluate_js(f"finDesinstalacion('{safe_id}', false)")

    except Exception as e:
        print(e)
        _window.evaluate_js(f"finDesinstalacion('{safe_id}', false)")

# FRONTEND (HTML/JS/CSS) para webview
# Obtener la ruta absoluta del archivo HTML
import pathlib
html_path = pathlib.Path(__file__).parent / "webview" / "index.html"

if __name__ == "__main__":
    # Inicializar el caché de paquetes instalados
    _refresh_cache()
    
    # Crear un objeto API con todas las funciones
    api = type('Api', (), {
        'check_choco': check_choco,
        'buscar': buscar,
        'instalar': instalar,
        'desinstalar': desinstalar,
        'refresh_installed': refresh_installed,
        'get_installed_packages': get_installed_packages
    })()
    
    window = B.webview.create_window(
        'PKGestor',
        url=str(html_path.absolute()),
        width=1200,
        height=800,
        resizable=True,
        js_api=api
    )
    set_window(window)
    B.webview.start(debug=False)
