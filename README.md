# PKGestor

PKGestor es una herramienta de gestión de paquetes de software para Windows moderna y eficiente. Actúa como una interfaz gráfica de usuario (GUI) elegante para **Chocolatey**, el gestor de paquetes por línea de comandos más popular de Windows. El objetivo principal del proyecto es democratizar y simplificar la instalación, actualización y eliminación de software, eliminando la necesidad de interactuar con la consola y ofreciendo una experiencia visual fluida y amigable.

## Arquitectura Técnica

El proyecto sigue una arquitectura híbrida que combina la potencia de Python en el backend con la flexibilidad de las tecnologías web en el frontend.

### Backend (Python):
- Se utiliza **pywebview** para crear una ventana de aplicación nativa que renderiza contenido web.
- Se integra directamente con el CLI de **Chocolatey** (`choco.exe`) mediante el módulo `subprocess` para ejecutar comandos de instalación y desinstalación de forma silenciosa y controlada.
- Implementa un cliente HTTP optimizado (`requests`) que consulta la API OData v2 de la comunidad de Chocolatey. Parsea respuestas XML (Atom feeds) para obtener metadatos ricos (iconos, versiones, descripciones) sin depender de comandos de búsqueda locales lentos.
- Emplea `threading` para ejecutar operaciones pesadas (descargas e instalaciones) en segundo plano, manteniendo la interfaz siempre interactiva y evitando bloqueos ("freezes").

### Interfaz Frontend (Web Techs):
Construida con **HTML5** y **Tailwind CSS**, presentando un diseño moderno con estética **Glassmorphism** (fondos translúcidos, desenfoques, sombras suaves).
- Para la interactividad, **JavaScript** gestiona la lógica de la vista, comunicándose asíncronamente con el backend de Python para actualizar barras de progreso, estados de instalación y resultados de búsqueda en tiempo real.
- En experiencia de usuario se incluye micro-interacciones, animaciones de carga y retroalimentación visual inmediata ante acciones del usuario.

## Funcionalidades Clave

- **Búsqueda Inteligente**: Permite encontrar software en el repositorio comunitario de Chocolatey con resultados detallados.
- **Gestión de Ciclo de Vida**: Instalación y desinstalación de programas con un solo clic (One-Click Install).
- **Feedback en Tiempo Real**: Visualización del progreso de descarga e instalación mediante barras dinámicas.
- **Autogestión**: El sistema detecta automáticamente si Chocolatey está instalado; si no lo está, intenta instalarlo y configurarlo sin intervención del usuario.
- **Cache de Estado**: Mantiene un registro local de las aplicaciones instaladas para mostrar correctamente los estados (Instalar vs. Eliminar) al realizar búsquedas.

## Requisitos de Ejecución

- **Portable**: No requiere tener Python instalado, ya que se distribuye como un ejecutable (`.exe`).
- **Permisos**: Debe ejecutarse con **permisos de Administrador** para poder instalar y desinstalar programas en el sistema.

## Generar el Ejecutable (.exe)

Si decides hacer un fork del proyecto o quieres compilarlo tú mismo, sigue estos pasos para generar el archivo `.exe`:

1.  **Instalar PyInstaller**:
    Asegúrate de tener instalada la librería en tu entorno de Python:
    ```bash
    pip install pyinstaller
    ```

2.  **Construir el proyecto**:
    Ejecuta el siguiente comando en la raíz del proyecto para usar la configuración predefinida:
    ```bash
    pyinstaller PKGestor.spec
    ```

3.  **Localizar el archivo**:
    Una vez finalizado el proceso, encontrarás el ejecutable `PKGestor.exe` dentro de la carpeta `dist`.

    > **Nota**: El archivo `.spec` ya está configurado para incluir el icono, ocultar la consola y empaquetarlo todo en un solo archivo.
