import bibliotecas as B
from choco import gestionar_chocolatey
from main import buscar_app_seguro
import threading

# Configuración para ocultar ventanas de consola en Windows

def obtener_startup_info():
    if B.os.name == 'nt':
        si = B.subprocess.STARTUPINFO()
        si.dwFlags |= B.subprocess.STARTF_USESHOWWINDOW
        return si
    return None

class Api:
    def __init__(self):
        self._window = None
        self.choco_path = None
        self.installed_cache = set()
        self._refresh_cache()

    def set_window(self, window):
        self._window = window

    def _refresh_cache(self):
        # Carga aplicaciones instaladas para mostrar el estado correcto
        try:
            # En Chocolatey 2.4.3+, "choco list" muestra solo paquetes locales por defecto
            # El flag -lo fue removido
            res = B.subprocess.run(
                ["choco", "list"], 
                capture_output=True, text=True, creationflags=B.subprocess.CREATE_NO_WINDOW
            )
            # Parsear el formato de salida: "nombrePaquete version"
            self.installed_cache = set()
            for line in res.stdout.splitlines():
                line = line.strip()
                # Saltar líneas de cabecera y footer
                if not line or line.startswith('Chocolatey') or 'packages installed' in line:
                    continue
                # Extraer el nombre del paquete (primera palabra antes del espacio)
                parts = line.split()
                if parts:
                    self.installed_cache.add(parts[0].lower())
            
        except Exception as e:
            self.installed_cache = set()

    # Métodos llamados desde JS

    def refresh_installed(self):
        # Refresca la lista de paquetes instalados
        self._refresh_cache()
        return {"status": "success", "count": len(self.installed_cache)}

    def check_choco(self):
        self.choco_path = gestionar_chocolatey()
        if self.choco_path:
            return {"status": "success", "path": self.choco_path}
        return {"status": "error", "message": "Chocolatey no detectado"}

    def buscar(self, query):
        if not query: 
            return []
        
        # Usar la función de main.py
        results = buscar_app_seguro(query)
        
        if results == -1:
            return []
        
        # Adaptar formato para el frontend (agregar safe_id y estado instalado)
        resultados = []
        for app in results:
            pkg_id = app['id'].lower()
            safe_id = pkg_id.replace('.', '_').replace(' ', '_')
            is_installed = pkg_id in self.installed_cache
            
            resultados.append({
                "id": pkg_id,
                "safe_id": safe_id,
                "nombre": app['nombre'],
                "version": app['version'],
                "installed": is_installed,
                "icon": app.get('icon', ''),
                "descripcion": app['descripcion'][:100] + "..." if len(app['descripcion']) > 100 else app['descripcion']
            })
        
        return resultados

    def instalar(self, pkg_id, safe_id):
        if not self.choco_path:
            self.choco_path = gestionar_chocolatey()
        
        # Ejecutar en hilo para no congelar la barra de progreso
        threading.Thread(target=self._proceso_instalacion, args=(pkg_id, safe_id), daemon=True).start()

    def desinstalar(self, pkg_id, safe_id):
        # Desinstala un paquete y actualiza el cache
        if not self.choco_path:
            self.choco_path = gestionar_chocolatey()
        
        # Ejecutar en hilo para no congelar la barra de progreso
        threading.Thread(target=self._proceso_desinstalacion, args=(pkg_id, safe_id), daemon=True).start()

    def _proceso_instalacion(self, pkg_id, safe_id):
        try:
            cmd = [self.choco_path, "install", pkg_id, "-y", "--no-progress"]
            
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
                    self._window.evaluate_js(f"actualizarBarra('{safe_id}', 30, 'Descargando...')")
                elif "Installing" in line:
                    self._window.evaluate_js(f"actualizarBarra('{safe_id}', 60, 'Instalando...')")
                elif "Verifying" in line:
                    self._window.evaluate_js(f"actualizarBarra('{safe_id}', 80, 'Verificando...')")

            process.wait()

            if process.returncode == 0 or process.returncode == 3010: # 3010 es reinicio pendiente (éxito)
                self.installed_cache.add(pkg_id.lower())
                self._window.evaluate_js(f"finInstalacion('{safe_id}', true)")
            else:
                self._window.evaluate_js(f"finInstalacion('{safe_id}', false)")

        except Exception as e:
            print(e)
            self._window.evaluate_js(f"finInstalacion('{safe_id}', false)")

    def _proceso_desinstalacion(self, pkg_id, safe_id):
        try:
            cmd = [self.choco_path, "uninstall", pkg_id, "-y", "--no-progress"]
            
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
                    self._window.evaluate_js(f"actualizarBarra('{safe_id}', 50, 'Desinstalando...')")
                elif "Success" in line or "successfully" in line:
                    self._window.evaluate_js(f"actualizarBarra('{safe_id}', 80, 'Finalizando...')")

            process.wait()

            if process.returncode == 0:
                # Actualizar cache localmente
                self.installed_cache.discard(pkg_id.lower())
                self._window.evaluate_js(f"finDesinstalacion('{safe_id}', true)")
            else:
                self._window.evaluate_js(f"finDesinstalacion('{safe_id}', false)")

        except Exception as e:
            print(e)
            self._window.evaluate_js(f"finDesinstalacion('{safe_id}', false)")

# FRONTEND (HTML/JS/CSS) para webview
html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        body { font-family: 'Outfit', sans-serif; user-select: none; }
        
        .glass { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); }
        .custom-scrollbar::-webkit-scrollbar { width: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
        
        .app-card { transition: all 0.2s ease; }
        .app-card:hover { transform: translateY(-2px); border-color: #3b82f6; background: rgba(30, 41, 59, 0.8); }

        /* Animación de la barra */
        .progress-container { background: rgba(0,0,0,0.3); border-radius: 99px; overflow: hidden; height: 8px; width: 100%; }
        .progress-fill { height: 100%; background: #3b82f6; width: 0%; transition: width 0.5s ease; border-radius: 99px; }
    </style>
</head>
<body class="bg-[#0f172a] text-slate-200 min-h-screen custom-scrollbar flex flex-col">

    <div class="max-w-3xl mx-auto p-6 w-full flex-1 flex flex-col">
        <header class="flex items-center gap-4 mb-8 justify-between">
            <div class="flex items-center gap-4 flex-1">
                <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
                    <i class="fas fa-microchip text-xl"></i>
                </div>
                <div class="flex-1">
                    <h1 class="text-2xl font-bold text-white">PKGestor</h1>
                    <p id="status" class="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-slate-600"></span> Iniciando motor...
                    </p>
                </div>
            </div>
            <button onclick="refrescarCache()" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all active:scale-95 flex items-center gap-2" title="Refrescar paquetes instalados">
                <i class="fas fa-sync-alt"></i> Actualizar
            </button>
        </header>

        <div class="glass p-2 rounded-2xl mb-6 flex items-center shadow-xl sticky top-2 z-10">
            <i class="fas fa-search ml-4 text-slate-400"></i>
            <input type="text" id="searchInput" placeholder="Buscar app (ej: chrome, vlc)..." 
                   class="w-full bg-transparent p-3 outline-none text-slate-200 placeholder:text-slate-500"
                   onkeypress="if(event.key === 'Enter') realizarBusqueda()">
            <button onclick="realizarBusqueda()" class="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-xl font-bold text-sm transition-all active:scale-95">
                Buscar
            </button>
        </div>

        <div id="loading" class="hidden flex justify-center py-10">
            <i class="fas fa-circle-notch fa-spin text-blue-500 text-3xl"></i>
        </div>

        <div id="results" class="grid gap-3 pb-4"></div>
    </div>

    <script>
        async function init() {
            const res = await window.pywebview.api.check_choco();
            const statusEl = document.getElementById('status');
            if (res.status === 'success') {
                statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Sistema Listo';
                statusEl.className = 'text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-2';
            } else {
                statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-500"></span> Error de Motor';
                statusEl.className = 'text-[10px] font-bold uppercase tracking-widest text-red-400 flex items-center gap-2';
            }
        }

        async function realizarBusqueda() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;

            const resultsDiv = document.getElementById('results');
            const loading = document.getElementById('loading');
            
            resultsDiv.innerHTML = '';
            loading.classList.remove('hidden');

            const apps = await window.pywebview.api.buscar(query);
            loading.classList.add('hidden');

            if (apps.length === 0) {
                resultsDiv.innerHTML = '<div class="text-center py-10 text-slate-500">No se encontraron resultados</div>';
                return;
            }

            apps.forEach(app => {
                // Estado del botón: Instalado (con opción de desinstalar) o Instalar
                // Estilo "Calmado": Fondo muy sutil, borde coloreado, texto coloreado, glow suave
                const actionContent = app.installed 
                    ? `<button onclick="iniciarDesinstalacion('${app.id}', '${app.safe_id}')" class="bg-red-500/10 hover:bg-red-500/20 border border-red-500/50 text-red-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(239,68,68,0.1)] hover:shadow-[0_0_20px_rgba(239,68,68,0.3)] transition-all active:scale-95 w-32 flex items-center gap-2 justify-center backdrop-blur-md"><i class="fas fa-trash"></i> Eliminar</button>`
                    : `<button onclick="iniciarInstalacion('${app.id}', '${app.safe_id}')" class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/50 text-blue-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(59,130,246,0.1)] hover:shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all active:scale-95 w-32 backdrop-blur-md">Instalar</button>`;

                const iconHtml = app.icon 
                    ? `<img src="${app.icon}" class="w-12 h-12 rounded-lg object-contain bg-white/5 p-1" onerror="this.onerror=null; this.src=''; this.parentElement.innerHTML='<i class=\\'fas fa-microchip text-2xl text-slate-500\\'></i>';">`
                    : `<div class="w-12 h-12 bg-slate-700/30 rounded-lg flex items-center justify-center"><i class="fas fa-microchip text-xl text-slate-500"></i></div>`;

                const card = `
                    <div class="glass p-5 rounded-2xl app-card group relative overflow-hidden" id="card-${app.safe_id}">
                        <div class="flex justify-between items-center gap-4">
                            <div class="shrink-0">
                                ${iconHtml}
                            </div>
                            <div class="flex-1">
                                <h3 class="text-lg font-bold text-white leading-tight">${app.nombre}</h3>
                                <div class="flex items-center gap-2 mt-1 mb-2">
                                    <span class="text-[10px] bg-slate-700/50 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-600/30">v${app.version}</span>
                                    <span class="text-[10px] text-slate-500 font-mono">ID: ${app.id}</span>
                                </div>
                                <p class="text-slate-400 text-xs leading-relaxed line-clamp-2">${app.descripcion}</p>
                            </div>
                            
                            <div id="action-area-${app.safe_id}" class="flex flex-col items-end justify-center h-full">
                                ${actionContent}
                            </div>
                        </div>
                    </div>
                `;
                resultsDiv.innerHTML += card;
            });
        }

        function iniciarInstalacion(realId, safeId) {
            const actionArea = document.getElementById(`action-area-${safeId}`);
            
            // Reemplazar botón por barra de progreso
            actionArea.innerHTML = `
                <div class="w-40 flex flex-col items-end">
                    <span id="status-text-${safeId}" class="text-[10px] text-blue-400 font-bold mb-1 uppercase tracking-wider">Iniciando...</span>
                    <div class="progress-container">
                        <div id="bar-${safeId}" class="progress-fill"></div>
                    </div>
                </div>
            `;
            
            // Llamar a Python
            window.pywebview.api.instalar(realId, safeId);
        }

        function iniciarDesinstalacion(realId, safeId) {
            const actionArea = document.getElementById(`action-area-${safeId}`);
            
            // Reemplazar botón por barra de progreso
            actionArea.innerHTML = `
                <div class="w-40 flex flex-col items-end">
                    <span id="status-text-${safeId}" class="text-[10px] text-red-400 font-bold mb-1 uppercase tracking-wider">Eliminando...</span>
                    <div class="progress-container">
                        <div id="bar-${safeId}" class="progress-fill" style="background: #ef4444;"></div>
                    </div>
                </div>
            `;
            
            // Llamar a Python
            window.pywebview.api.desinstalar(realId, safeId);
        }

        // Llamado desde Python para mover la barra
        function actualizarBarra(safeId, percent, text) {
            const bar = document.getElementById(`bar-${safeId}`);
            const label = document.getElementById(`status-text-${safeId}`);
            if (bar && label) {
                bar.style.width = percent + '%';
                label.innerText = text;
            }
        }

        // Llamado desde Python al terminar instalación
        function finInstalacion(safeId, exito) {
            const actionArea = document.getElementById(`action-area-${safeId}`);
            if (exito) {
                actualizarBarra(safeId, 100, 'Completado');
                setTimeout(() => {
                    actionArea.innerHTML = `<button onclick="iniciarDesinstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-red-500/10 hover:bg-red-500/20 border border-red-500/50 text-red-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(239,68,68,0.1)] hover:shadow-[0_0_20px_rgba(239,68,68,0.3)] transition-all active:scale-95 w-32 flex items-center gap-2 justify-center backdrop-blur-md"><i class="fas fa-trash"></i> Eliminar</button>`;
                    document.getElementById(`card-${safeId}`).style.borderColor = "#10b981";
                }, 800);
            } else {
                actionArea.innerHTML = `<button onclick="iniciarInstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-xs font-bold w-32">Reintentar</button>`;
                alert("Error en la instalación. Verifica tu conexión o intenta ejecutar como Administrador.");
            }
        }

        // Llamado desde Python al terminar desinstalación
        function finDesinstalacion(safeId, exito) {
            const actionArea = document.getElementById(`action-area-${safeId}`);
            if (exito) {
                actualizarBarra(safeId, 100, 'Eliminado');
                setTimeout(() => {
                    actionArea.innerHTML = `<button onclick="iniciarInstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/50 text-blue-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(59,130,246,0.1)] hover:shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all active:scale-95 w-32 backdrop-blur-md">Instalar</button>`;
                    document.getElementById(`card-${safeId}`).style.borderColor = "rgba(255, 255, 255, 0.05)";
                }, 800);
            } else {
                actionArea.innerHTML = `<button onclick="iniciarDesinstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-xs font-bold w-32 flex items-center gap-2 justify-center"><i class="fas fa-trash"></i> Reintentar</button>`;
                alert("Error en la desinstalación. Intenta ejecutar como Administrador.");
            }
        }

        async function refrescarCache() {
            const btn = event.target.closest('button');
            const icon = btn.querySelector('i');
            icon.classList.add('fa-spin');
            
            const res = await window.pywebview.api.refresh_installed();
            
            icon.classList.remove('fa-spin');
            
            if (res.status === 'success') {
                // Recargar resultados si hay una búsqueda activa
                const searchInput = document.getElementById('searchInput');
                if (searchInput.value) {
                    realizarBusqueda();
                }
            }
        }

        window.addEventListener('pywebviewready', init);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    api = Api()
    window = B.webview.create_window(
        'PKGestor',
        html=html,
        width=600,
        height=800,
        resizable=False,
        js_api=api
    )
    api.set_window(window)
    B.webview.start(debug=False)