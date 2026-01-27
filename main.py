# ------------------------------------------------------- #
# Imports
import bibliotecas as B

# ------------------------------------------------------- #
# Funciones

# Buscar una app en Chocolatey usando la API OData, que es muy estable para buscar software real
def buscar_app_seguro(nombre_app):
    
    url = f"https://community.chocolatey.org/api/v2/Search()?$filter=IsLatestVersion&searchTerm='{nombre_app}'&targetFramework='net45'&includePrerelease=false"
    
    try:
        response = B.requests.get(url, timeout=10)
        if response.status_code != 200:
            return -1

        # Parsear el XML con manejo de Namespaces
        root = B.ET.fromstring(response.content)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',  # Atom namespace
            'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',  # Data Services namespace
            'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'  # Metadata namespace
        }

        resultados = []
        
        # Buscar cada entrada de aplicación
        for entry in root.findall('atom:entry', ns):
            properties = entry.find('m:properties', ns)
            
            # El ID real es el title de atom, d:Title es el nombre legible  
            pkg_id = entry.find('atom:title', ns).text if entry.find('atom:title', ns) is not None else "N/A"
            title = properties.find('d:Title', ns).text if properties.find('d:Title', ns) is not None else pkg_id
            desc = properties.find('d:Description', ns).text if properties.find('d:Description', ns) is not None else ""
            url_proyecto = properties.find('d:ProjectUrl', ns).text if properties.find('d:ProjectUrl', ns) is not None else "No disponible"

            resultados.append({
                "nombre": title,
                "id": pkg_id,
                "version": properties.find('d:Version', ns).text if properties.find('d:Version', ns) is not None else "N/A",
                "descripcion": desc,
                "url": url_proyecto,
                "icon": properties.find('d:IconUrl', ns).text if properties.find('d:IconUrl', ns) is not None else ""
            })

        return resultados if resultados else -1

    except Exception as e:
        print(f"Error de conexión: {e}")
        return -1

if __name__ == "__main__":
    # Test
    query = input("Escribe la App que buscas: ")
    apps = buscar_app_seguro(query)

    if apps != -1:
        print(f"\nResultados para '{query}':")
        print("-" * 50)
        for app in apps[:8]: # Limitamos a los mejores 8
            print(f"{app['nombre']} (v{app['version']})")
            print(f"ID: {app['id']}")
            print(f"Instalar: choco install {app['id']} -y")
            print(f"Proyecto: {app['url']}")
            print(f"Info: {app['descripcion']}\n")
    else:
        print("No se encontraron resultados o el servidor está ocupado.")






