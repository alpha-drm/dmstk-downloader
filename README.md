<div align="center">

# Dmstk Downloader

Herramienta `CLI` que permite a usuarios con suscripción descargar cursos para acceso offline, facilitando el estudio desde cualquier lugar y en cualquier momento sin necesidad de conexión a Internet.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![GitHub repo size](https://img.shields.io/github/repo-size/alpha-drm/dmstk-downloader)]()
![GitHub Repo stars](https://img.shields.io/github/stars/alpha-drm/dmstk-downloader)
![GitHub forks](https://img.shields.io/github/forks/alpha-drm/dmstk-downloader)
![GitHub watchers](https://img.shields.io/github/watchers/alpha-drm/dmstk-downloader)
![GitHub top language](https://img.shields.io/github/languages/top/alpha-drm/dmstk-downloader)
![GitHub Created At](https://img.shields.io/github/created-at/alpha-drm/dmstk-downloader)
![GitHub last commit](https://img.shields.io/github/last-commit/alpha-drm/dmstk-downloader)

</div>

> [!NOTE]
> Los gestores de descargas o extensiones utilizan el mismo método para descargar vídeos de una página. Esta herramienta solo automatiza el proceso que un usuario haría manualmente en un navegador.

## Características

- No evade sistemas de protección ni accede a contenido sin autorización.
- Requiere autenticación válida del usuario.
- Funciona desde la línea de comandos `CLI`.
- Descarga videos y otros recursos disponibles.
- Permite elegir la calidad de los videos.
- Permite elegir el idioma del subtítulo.
- Permite reanudar descargas interrumpidas.
- Organiza el contenido de forma estructurada.
- Ideal para uso personal y educativo en modo offline.

## Requisitos

- Tener acceso a la plataforma.
- [git](https://git-scm.com/) (Opcional, para clonar el repositorio)
- [Python >=3.11](https://www.python.org/downloads/)
  * *Importante:* Al instalar, marca la casilla `Add Python to PATH`
- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases)
  * Busca la versión para Windows (ej: win-x64.zip) y descarga el zip.
  * Extrae el archivo `N_m3u8DL-RE.exe`
- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/)
  * Busca la versión para Windows (Ej: ffmpeg-release-essentials) y descarga el zip.
  * Dentro del zip, entra a la carpeta bin y extrae el archivo `ffmpeg.exe`

## Instalación

### Windows

#### Clonar o descargar el proyecto

Desde una terminal clonar el proyecto usando `GIT`, o simplemente descargar el archivo `ZIP` del repositorio.

```bash
git clone https://github.com/alpha-drm/dmstk-downloader.git
```

Ir al directorio del proyecto

```bash
cd dmstk-downloader
```

#### Entorno virtual
  Es recomendable crear un entorno virtual para instalar los `requirements.txt` del proyecto

```bash
python -m venv env
```

  Activar el entorno virtual
```bash
env\Scripts\activate
```

#### Instalar las dependencias

```bash
python pip install -r requirements.txt
```

### Configurar Herramientas Externas (Importante)

#### Opción A: Añadirlas al PATH del sistema (recomendado)

1. Crear una carpeta llamada `tools` (o el nombre que prefieras) en el disco `C:\`, 
2. Copiar los ejecutables `N_m3u8DL-RE.exe` y `ffmpeg.exe` dentro de esa carpeta.
3. Agregar la ruta de la carpeta al `PATH` del sistema.

**Estructura final:**

```text
C:\tools
   |── ffmpeg.exe
   └── N_m3u8DL-RE.exe
```

#### Opción B: Método rápido (sin modificar el PATH)

* Copiar los ejecutables `N_m3u8DL-RE.exe` y `ffmpeg.exe` directamente en el directorio raíz del proyecto.
* No es necesario agregarlos al `PATH` del sistema.

**Estructura final:**

```text
dmstk-downloader/
├── env/
├── Courses/
├── main.py
├── requirements.txt
├── ffmpeg.exe           <-- Archivo pegado
└── N_m3u8DL-RE.exe      <-- Archivo pegado
```

```md
⚠️ Nota: La opción A es recomendable si usas estas herramientas en otros proyectos.
```

## Instrucciones de uso

> [!IMPORTANT]
> Antes de ejecutar el script debes estar logueado en la plataforma, usar `firefox` preferiblemente.

El script utiliza **cookies para autenticación** y soporta **dos métodos**:

### Método 1: Cookies automáticas desde el navegador (por defecto)

- El script extrae automáticamente las cookies del navegador.
- Se recomienda usar **`firefox`**.
- Puedes especificar el navegador con `-b` o `--browser`.

**Navegadores soportados:**
- `firefox` (default, recomendado)
- `chrome`
- `edge`
- `brave`

### Método 2: Cookies desde un archivo JSON (opcional)
- Puedes cargar las cookies manualmente desde un archivo JSON usando `-c` o `--cookies` seguido del nombre del archivo.
- Al usar este método no es necesario estar logueado en el navegador si ya tienes las cookies.
- Si se especifica --cookies, el argumento --browser se ignora.

**Puedes generar el archivo de cookies usando extensiones del navegador.**

**Extensiones recomendadas: exporta las cookies en formato JSON.**
- *Cookie-Editor*
- *cookies.txt*
- *Get cookies.txt LOCALLY*

### Comandos

Abre la terminal en la carpeta del proyecto (asegúrate de tener el entorno virtual activado):

```bash
python main.py <url> [opciones]
```

Opciones:
- `-b`, `--browser` Navegador para obtener las cookies {firefox, chrome, edge, brave}
- `-q`, `--quality` Resolución de video (ej: 1080, 720, 540). Default: 1080
- `-l`, `--lang` Idioma del subtítulo. (ej: es, en, pt, it, fr, de)
- `-a`, `--audio` Audio secundario para el video. Opcional (ej: es, en, pt, it, fr, de)
- `-h`, `--help` Ayuda

Ejemplos:

Descarga estándar con calidad 1080p, audio original, subtítulos en español y usando las cookies de `Firefox` (Default):
```bash
python main.py https://www.domestika.org/es/courses/5228-introduccion-a-la-programacion-con-python/course
```

Descarga usando un navegador diferente. (Posibles fallas en la extracción de cookies)
```bash
python main.py https://www.domestika.org/es/courses/5228-introduccion-a-la-programacion-con-python/course -b edge
```

Seleccionar la calidad del video. Default: 1080
```bash
python main.py https://www.domestika.org/es/courses/5228-introduccion-a-la-programacion-con-python/course -q 720
```

Seleccionar subtítulos. Ej: es, en, pt, it, fr, de. Default: Español (es).
```bash
python main.py https://www.domestika.org/es/courses/5228-introduccion-a-la-programacion-con-python/course -l en
```
Opcional: seleccionar un audio secundario a parte del audio original del curso. Ej: es, en, pt, it, fr, de.
```bash
python main.py https://www.domestika.org/es/courses/5228-introduccion-a-la-programacion-con-python/course -a en
```

## Estructura de archivos

El script creará automáticamente una carpeta llamada `Courses` y organizará todo por secciones:

```text
Courses/
└── Course_Name/
    └── Section/
        ├── 01 - video.mp4
        └── 01 - subtitle.es.srt (Subtítulos)
```

## Feedback

Para comentarios o reportes de errores utilizar [GitHub Issues](https://github.com/alpha-drm/dmstk-downloader/issues) 

## License

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](./LICENSE) para más detalles.

## Aviso Legal

Este proyecto tiene fines exclusivamente educativos y personales. El autor no se responsabiliza por el uso indebido de esta herramienta. El acceso y la descarga de contenidos están permitidos únicamente a usuarios con credenciales válidas y acceso legítimo a los cursos en la plataforma.

Es responsabilidad exclusiva del usuario:
- Cumplir con los Términos de Servicio y Condiciones de Uso de la plataforma.
- Respetar las leyes de derechos de autor, de propiedad intelectual y cualquier otra normativa local aplicable.
- Abstenerse de redistribuir, revender, publicar o compartir los contenidos descargados mediante este script.
- El propósito de esta herramienta es facilitar el acceso offline para usuarios autorizados, y no debe utilizarse con fines comerciales.