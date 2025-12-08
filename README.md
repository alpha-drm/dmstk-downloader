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
> Los gestores de descargas o extensiones utilizan el mismo método para descargar vídeos de una página. Esta herramienta sólo automatiza el proceso de un usuario haciendo esto manualmente en un navegador.

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

- Tener acceso a los cursos.
- [git](https://git-scm.com/) (para clonar el repositorio)
- [Python >=3.11](https://python.org/) (Añadirlo al PATH durante la instalación)
- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases)
- [ffmpeg](https://ffmpeg.org/)

## Instalación

### Windows

- Crear una carpeta llamada `tools` o el nombre que quieran en en el disco `C:\`, dentro copiar los ejecutables (N_m3u8DL-RE, ffmpeg) y por último agregar la ruta de la carpeta al `PATH` del sistema.

- Opcional: copiar los ejecutables directamente en el directorio raíz del proyecto, no necesitas agregarlo al `PATH` del sistema.

Estructura final: `C:\tools`

```bash
C:\tools
   |── ffmpeg.exe
   └── N_m3u8DL-RE.exe
```

#### Clonar el proyecto

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
pip install -r requirements.txt
```

### Cookies

> [!IMPORTANT]
> Estar logueado en la plataforma, usar `firefox` preferiblemente.

El script utiliza cookies para autenticación y lo extrae automáticamente. Opcional: especificar de que navegador extraer las cookies con el argumento `-b` o `--browser`.

Opciones:

- `firefox` Default, recomendado.
- `chrome`
- `edge`
- `brave`

## Instrucciones de uso

```bash
python main.py <url> [opciones]
```
Opciones:
- `-b`, `--browser` Navegador de donde extraer las cookies {firefox, chrome, edge, brave}
- `-q`, `--quality` Resolución de video (ej: 1080, 720). Default: 1080
- `-l`, `--lang` Idioma para los subtítulos (ej: Español, English). Default: Español
- `-h`, `--help` Ayuda

Ejemplos:

Descargar usando las cookies del navegador por defecto `firefox`:
```bash
python main.py https://www.domestika.org/es/courses/3414-gimnasio-de-escritura-de-la-hoja-en-blanco-a-la-practica-cotidiana/course
```

Descargar usando las cookies de otro navegador:
```bash
python main.py https://www.domestika.org/es/courses/3414-gimnasio-de-escritura-de-la-hoja-en-blanco-a-la-practica-cotidiana/course --browser edge
```

Descargar una calidad específica. Default: 1080
```bash
python main.py https://www.domestika.org/es/courses/3414-gimnasio-de-escritura-de-la-hoja-en-blanco-a-la-practica-cotidiana/course -q 720
```

Descargar subtítulo con un lenguaje específico si está disponible. Default: Español
```bash
python main.py https://www.domestika.org/es/courses/3414-gimnasio-de-escritura-de-la-hoja-en-blanco-a-la-practica-cotidiana/course -l English
```

## Estructura de archivos

Los cursos se descargan en la carpeta `Courses` con la siguiente estructura:

```bash
Courses/
└── Course_Name/
    └── Section/
        ├── 01 - video.mp4
        └── 01 - subtitle.es.srt
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