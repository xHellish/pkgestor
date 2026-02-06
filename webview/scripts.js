async function init() {
    const res = await window.pywebview.api.check_choco();
    const statusEl = document.getElementById('status');
    if (res.status === 'success') {
        statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Sistema Listo';
        statusEl.className = 'text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-2';

        // Cargar paquetes instalados al iniciar
        await cargarPaquetesInstalados();
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
            : `<button onclick="iniciarInstalacion('${app.id}', '${app.safe_id}')" class="bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/50 text-purple-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(139,92,246,0.1)] hover:shadow-[0_0_20px_rgba(139,92,246,0.3)] transition-all active:scale-95 w-32 backdrop-blur-md">Instalar</button>`;

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
            <span id="status-text-${safeId}" class="text-[10px] text-purple-400 font-bold mb-1 uppercase tracking-wider">Iniciando...</span>
            <div class="progress-container">
                <div id="bar-${safeId}" class="progress-fill"></div>
            </div>
        </div>
    `;

    // Llamar a Python
    window.pywebview.api.instalar(realId, safeId);
}

function iniciarDesinstalacion(realId, safeId) {
    // Intentar encontrar el action-area (desde búsqueda)
    const actionArea = document.getElementById(`action-area-${safeId}`);

    // Si no existe, es desde el panel de instalado
    const installedCard = document.getElementById(`installed-${safeId}`);

    if (actionArea) {
        // Reemplazar botón por barra de progreso (desde búsqueda)
        actionArea.innerHTML = `
            <div class="w-40 flex flex-col items-end">
                <span id="status-text-${safeId}" class="text-[10px] text-red-400 font-bold mb-1 uppercase tracking-wider">Eliminando...</span>
                <div class="progress-container">
                    <div id="bar-${safeId}" class="progress-fill" style="background: #ef4444;"></div>
                </div>
            </div>
        `;
    } else if (installedCard) {
        // Reemplazar toda la tarjeta con barra de progreso (desde panel instalados)
        installedCard.innerHTML = `
            <div class="flex items-center justify-between gap-3">
                <div class="flex-1">
                    <span id="status-text-${safeId}" class="text-xs text-red-400 font-bold uppercase tracking-wider">Eliminando...</span>
                </div>
                <div class="flex-1">
                    <div class="progress-container">
                        <div id="bar-${safeId}" class="progress-fill" style="background: #ef4444;"></div>
                    </div>
                </div>
            </div>
        `;
    }

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
            document.getElementById(`card-${safeId}`).style.borderColor = "#8b5cf6";

            // Recargar lista de paquetes instalados
            cargarPaquetesInstalados();
        }, 800);
    } else {
        actionArea.innerHTML = `<button onclick="iniciarInstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-xs font-bold w-32">Reintentar</button>`;
        alert("Error en la instalación. Verifica tu conexión o intenta ejecutar como Administrador.");
    }
}

// Llamado desde Python al terminar desinstalación
function finDesinstalacion(safeId, exito) {
    const actionArea = document.getElementById(`action-area-${safeId}`);
    const installedCard = document.getElementById(`installed-${safeId}`);

    if (actionArea) {
        // Desinstalación desde búsqueda
        if (exito) {
            actualizarBarra(safeId, 100, 'Eliminado');
            setTimeout(() => {
                actionArea.innerHTML = `<button onclick="iniciarInstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/50 text-purple-400 px-5 py-2 rounded-xl text-sm font-bold shadow-[0_0_10px_rgba(139,92,246,0.1)] hover:shadow-[0_0_20px_rgba(139,92,246,0.3)] transition-all active:scale-95 w-32 backdrop-blur-md">Instalar</button>`;
                document.getElementById(`card-${safeId}`).style.borderColor = "rgba(255, 255, 255, 0.05)";

                // Recargar lista de paquetes instalados
                cargarPaquetesInstalados();
            }, 800);
        } else {
            actionArea.innerHTML = `<button onclick="iniciarDesinstalacion('${safeId.replace(/_/g, '.')}', '${safeId}')" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-xs font-bold w-32 flex items-center gap-2 justify-center"><i class="fas fa-trash"></i> Reintentar</button>`;
            alert("Error en la desinstalación. Intenta ejecutar como Administrador.");
        }
    } else if (installedCard) {
        // Desinstalación desde panel de instalados
        if (exito) {
            actualizarBarra(safeId, 100, 'Eliminado');
            // Animar y eliminar la tarjeta
            setTimeout(() => {
                installedCard.style.opacity = '0';
                installedCard.style.transform = 'translateX(20px)';
                installedCard.style.transition = 'all 0.3s ease';

                setTimeout(() => {
                    installedCard.remove();

                    // Verificar si quedan paquetes, si no mostrar mensaje
                    const installedDiv = document.getElementById('installed-packages');
                    if (installedDiv.children.length === 0) {
                        installedDiv.innerHTML = '<div class="text-center py-10 text-slate-500 text-sm">No hay paquetes instalados</div>';
                    }

                    // Actualizar resultados de búsqueda si hay una búsqueda activa
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput.value) {
                        realizarBusqueda();
                    }
                }, 300);
            }, 800);
        } else {
            // Mostrar error y restaurar botón
            installedCard.innerHTML = `
                <div class="flex items-center justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <h4 class="font-bold text-red-400 text-sm">Error al desinstalar</h4>
                        <span class="text-[10px] text-slate-400">Ejecuta como administrador</span>
                    </div>
                    <button onclick="location.reload()" 
                        class="bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/50 text-purple-400 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                </div>
            `;
        }
    }
}

async function cargarPaquetesInstalados() {
    const installedDiv = document.getElementById('installed-packages');
    const loading = document.getElementById('loading-installed');

    loading.classList.remove('hidden');
    installedDiv.innerHTML = '';

    const packages = await window.pywebview.api.get_installed_packages();
    loading.classList.add('hidden');

    if (packages.length === 0) {
        installedDiv.innerHTML = '<div class="text-center py-10 text-slate-500 text-sm">No hay paquetes instalados</div>';
        return;
    }

    packages.forEach(pkg => {
        const card = `
            <div class="installed-card" id="installed-${pkg.safe_id}">
                <div class="flex items-center justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <h4 class="font-bold text-white text-sm truncate">${pkg.nombre}</h4>
                        <span class="text-[10px] text-slate-400 font-mono">v${pkg.version}</span>
                    </div>
                    <button onclick="iniciarDesinstalacion('${pkg.id}', '${pkg.safe_id}')" 
                        class="bg-red-500/10 hover:bg-red-500/20 border border-red-500/50 text-red-400 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5"
                        title="Desinstalar ${pkg.nombre}">
                        <i class="fas fa-trash text-xs"></i>
                    </button>
                </div>
            </div>
        `;
        installedDiv.innerHTML += card;
    });
}

async function refrescarCache() {
    const btn = event.target.closest('button');
    const icon = btn.querySelector('i');
    icon.classList.add('fa-spin');

    const res = await window.pywebview.api.refresh_installed();

    icon.classList.remove('fa-spin');

    if (res.status === 'success') {
        // Recargar paquetes instalados
        await cargarPaquetesInstalados();

        // Recargar resultados si hay una búsqueda activa
        const searchInput = document.getElementById('searchInput');
        if (searchInput.value) {
            realizarBusqueda();
        }
    }
}

window.addEventListener('pywebviewready', init);
