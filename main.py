import argparse
import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import browser_cookie3
import coloredlogs
import requests
from bs4 import BeautifulSoup
from colorama import Back, Fore, Style, init
from pyfiglet import Figlet

# --- CONSTANTES ---
LOG_DIR = "logs_dmstk"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "Courses")
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0'

# --- CONFIGURACIÓN DEL LOGGER ---
logger = logging.getLogger('Dmstk-Downloader')

# ISO 639-1 → 639-2 (agregar más si es necesario.)
ISO_639_1_TO_2 = {
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "it": "ita",
    "pt": "por",
    "de": "deu",
    "tr": "tur",
    "ru": "rus",
    "id": "ind",
    "ro": "rom",
    "ja": "jpn",
    "ar": "ara",
    "nl": "nld",
    "pl": "pol",
    "sv": "swe",
    "fi": "fin",
    "no": "nor",
    "da": "dan",
    "cs": "ces",
    "el": "ell",
    "hi": "hin",
    "th": "tha",
    "vi": "vie"
}


def setup_logging():
    """Configura el logger para la consola y un archivo."""
    log_level = logging.INFO
    log_format = '[%(asctime)s] [%(name)s] [%(funcName)s:%(lineno)d] [%(levelname)s]: %(message)s'
    log_date_format = '%d-%m-%Y %H:%M:%S'
    log_styles = {
        'info': {'color': 'white'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'bold': True, 'color': 'red'}
    }

    # Crear directorio de logs si no existe
    os.makedirs(LOG_DIR, exist_ok=True)

    log_filename = f"{time.strftime('%d-%m-%Y_%H-%M-%S')}.log"
    log_filepath = os.path.join(LOG_DIR, log_filename)

    coloredlogs.install(level=log_level, logger=logger, fmt=log_format, datefmt=log_date_format, level_styles=log_styles)

    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    formatter = logging.Formatter(log_format, datefmt=log_date_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def banner():
    """Imprime un banner estilizado en la consola."""
    init(autoreset=True)
    font = Figlet(font='slant')
    print(Fore.RED + Style.BRIGHT + font.renderText('Dmstk-Dl'))
    print(Back.RED + Style.BRIGHT + "Created by alphaDRM")
    print()

# --- FUNCIONES AUXILIARES ---

def iso639_2(lang: str) -> str:
    return ISO_639_1_TO_2.get(lang.lower(), lang.lower())


def sanitize_and_trim_filename(name: str, base_path: str, limite: int = 200, temp_suffix_len: int = 18) -> str:
    """
    Limpia un nombre de archivo de caracteres no válidos y lo recorta si la ruta completa
    excede un límite de longitud.

    Args:
        name (str): Nombre original del archivo o carpeta.
        base_path (str): Ruta base donde se almacenará el archivo.
        limite (int, optional): Límite máximo de caracteres para la ruta completa. Por defecto 200.

    Returns:
        str: Nombre limpio y recortado si es necesario.
    """
    # 1. Limpiar caracteres no válidos
    cleaned_name = re.sub(r'[<>:"/\\|?*]', '', name).strip()

    # 2. Calcular longitud total
    ruta_base = os.path.abspath(base_path)
    ruta_completa = os.path.join(ruta_base, cleaned_name)

    if len(ruta_completa) <= (limite - temp_suffix_len):
        return cleaned_name.rstrip(".")

    # 3. Calcular cuánto espacio hay para el nombre del archivo
    base_len = len(os.path.join(ruta_base, ""))
    espacio_disponible = limite - base_len - temp_suffix_len

    # 4. Recortar el nombre y devolver
    nombre_recortado = cleaned_name[:espacio_disponible].rstrip(".")

    return nombre_recortado


def validate_and_format_url(url: str) -> Optional[str]:
    """Valida y formatea la URL del curso de Domestika."""
    regex = r"(https://www\.domestika\.org/.+?/courses/\d+-[-\w]+)(/course)?/?$"
    match = re.match(regex, url)
    if match:
        return match.group(1) + "/course"
    return None


def create_session(browser: str, cookie_file: Optional[str] = None) -> Optional[requests.Session]:
    """
    Crea una sesión. Si se pasa cookie_file, carga desde JSON.
    Si no, intenta cargar desde el navegador especificado.
    """
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    # --- OPCIÓN A: Cargar desde archivo JSON ---
    if cookie_file:
        if not os.path.exists(cookie_file):
            logger.error(f"El archivo de cookies '{cookie_file}' no existe.")
            return None

        try:
            logger.info(f"Cargando cookies desde archivo: {cookie_file}")
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)

            # Soporte para formato lista (EditThisCookie) o dict simple
            jar = requests.cookies.RequestsCookieJar()

            if isinstance(cookies_data, list):
                for cookie in cookies_data:
                    if 'name' in cookie and 'value' in cookie:
                        jar.set(
                            cookie['name'],
                            cookie['value'],
                            domain=cookie.get('domain', '.domestika.org'),
                            path=cookie.get('path', '/')
                        )
            elif isinstance(cookies_data, dict):
                for name, value in cookies_data.items():
                    jar.set(name, value, domain='.domestika.org', path='/')
            else:
                logger.error("Formato JSON de cookies no reconocido (debe ser dict o lista).")
                return None

            session.cookies.update(jar)
            return session

        except json.JSONDecodeError:
            logger.error(f"El archivo '{cookie_file}' no es un JSON válido.")
            return None
        except Exception as e:
            logger.error(f"Error inesperado leyendo cookies: {e}")
            return None

    # --- OPCIÓN B: Cargar desde Navegador (Código original) ---
    try:
        cookie_fn = getattr(browser_cookie3, browser)
        cj = cookie_fn(domain_name="domestika")
        session.cookies.update({cookie.name: cookie.value for cookie in cj})
        return session
    except (AttributeError, browser_cookie3.BrowserCookieError) as e:
        logger.error(f"No se pudieron cargar las cookies para '{browser}': {e}")
        logger.error("Asegúrate de haber iniciado sesión en ese navegador o usa el argumento --cookies.")
        return None


# --- FUNCIONES DE SCRAPING Y DESCARGA ---

def extract_initial_props(unit_link: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Extrae el objeto JSON __INITIAL_PROPS__ de la página de una unidad."""
    try:
        response = session.get(unit_link)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        script_tag = soup.find('script', string=re.compile(r"window\.__INITIAL_PROPS__"))

        if not script_tag:
            logger.warning("No se encontró el script __INITIAL_PROPS__ en la página.")
            return None

        match = re.search(r"JSON\.parse\('(.+?)'\);", script_tag.string)
        if match:
            json_string = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
            return json.loads(json_string)

    except requests.exceptions.RequestException as e:
        logger.warning(f"No tienes acceso a esta lección o hubo un error de red: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar el JSON de INITIAL_PROPS: {e}")

    return None


def find_audio_file(save_dir: str, file_name: str, audio: str) -> str | None:
    audio = audio.lower()

    for f in os.listdir(save_dir):
        if not f.lower().endswith(".m4a"):
            continue

        if not f.startswith(file_name + "."):
            continue

        # archivo.es.m4a / archivo.es_la.m4a
        lang_part = f[len(file_name) + 1 : -4].lower()

        if lang_part == audio or lang_part.startswith(audio) or audio.startswith(lang_part):
            return os.path.join(save_dir, f)

    return None


def download_video(url: str, save_dir: str, file_name: str, quality: str, langs: list, audios: list):
    """
    Descarga video con múltiples subtítulos y audios, y los une con FFmpeg dinámicamente.
    """
    os.makedirs(save_dir, exist_ok=True)
    output_file = os.path.join(save_dir, file_name + '.mp4')

    if os.path.exists(output_file):
        logger.warning(f"El archivo '{file_name}.mp4' ya existe.")
        return

    logger.info(f"Descargando video: '{file_name}'")

    # --- 1. Construcción dinámica del comando N_m3u8DL-RE ---
    command = [
        'N_m3u8DL-RE',
        '-sv', f'res={quality}|720|540|360',
        '--save-dir', save_dir,
        '--save-name', file_name,
        # '--no-log', # Opcional: para limpiar la salida
        url
    ]

    # Añadir cada idioma de subtítulo solicitado
    if langs:
        langs_param = '|'.join(langs)
        command += ['-ss', f'lang={langs_param}:for=all']

    # Añadir cada idioma de audio solicitado
    if audios:
        audio_param = '|'.join(audios)
        command += ['-sa', f'lang={audio_param}:for=all']

    try:
        process = subprocess.run(command, check=False)

        if process.returncode != 0:
            logger.error(f"Error en descarga base de '{file_name}'.")
            return

        # --- 2. Lógica de Unión (Merging) con FFmpeg ---
        # Si no hay audios extra que unir, terminamos aquí (asumiendo que N_m3u8DL-RE ya muxó el video)
        # Pero si el script original separaba los audios .m4a, necesitamos unirlos.

        if not audios:
            logger.info(f"Archivo {file_name} descargado (sin audios extra).")
            return

        video_path = os.path.join(save_dir, f"{file_name}.mp4") # O el nombre que genere RE
        # A veces RE genera .mkv o .ts si hay muchas pistas, asegurar extensión:
        if not os.path.exists(video_path):
             # Intentar buscar el archivo base generado si no es mp4 exacto
             found_videos = [f for f in os.listdir(save_dir) if f.startswith(file_name) and f.endswith(('.mp4', '.mkv', '.ts')) and 'tmp' not in f]
             if found_videos:
                 video_path = os.path.join(save_dir, found_videos[0])

        temp_path = os.path.join(save_dir, file_name + "_tmp.mp4")

        # Construcción dinámica del comando FFmpeg
        cmd_ffmpeg = ["ffmpeg", "-y", "-i", video_path]

        # Listas para gestionar los mapeos
        maps = ["-map", "0:v", "-map", "0:a"] # Mapeamos video y audio original
        metadata = []
        files_to_delete = []

        input_index = 1 # El video es el input 0
        audio_track_index = 1 # El audio original es track 0

        # Buscar y añadir cada audio extra
        audios_found = False
        for audio_lang in audios:
            audio_path = find_audio_file(save_dir, file_name, audio_lang)

            if audio_path and os.path.exists(audio_path):
                audios_found = True
                cmd_ffmpeg += ["-i", audio_path]
                files_to_delete.append(audio_path)

                # Mapear este nuevo input
                maps += ["-map", f"{input_index}:a"]

                # Definir metadata del track (título y lenguaje)
                lang_3 = iso639_2(audio_lang)
                metadata += [
                    f"-metadata:s:a:{audio_track_index}", f"language={lang_3}"
                    # f"-metadata:s:a:{audio_track_index}", f"title={audio_lang.upper()}"
                ]

                input_index += 1
                audio_track_index += 1
            else:
                logger.warning(f"No se encontró archivo de audio para: {audio_lang}")

        if not audios_found:
            logger.info("No se encontraron audios externos para unir. Se mantiene el archivo original.")
            return

        # Comando final concatenado
        cmd_join = (
            cmd_ffmpeg +
            maps +
            ["-c:v", "copy", "-c:a", "aac"] +
            metadata +
            ["-metadata", f"title={file_name}"] +
            [temp_path]
        )

        logger.info("Uniendo audios con FFmpeg...")
        process_audio = subprocess.run(cmd_join, check=False)

        if process_audio.returncode == 0:
            os.replace(temp_path, output_file)
            # Borrar los .m4a sueltos
            for f in files_to_delete:
                try:
                    os.remove(f)
                except OSError:
                    pass
            logger.info(f"Unión completada exitosamente: {file_name}")
        else:
            logger.error("Error al unir audios con ffmpeg.")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error inesperado en download_video: {e}")


def download_attachments(session: requests.Session, url: str, save_dir: str):
    """Descarga los recursos adicionales de un curso."""
    try:
        response = session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        file_links = soup.select('h3.material-item__title a[href]')

        if not file_links:
            logger.info("No se encontraron recursos adicionales para descargar.")
            return

        logger.info("Descargando recursos adicionales...")
        os.makedirs(save_dir, exist_ok=True)

        for link in file_links:
            file_url = link['href']
            file_response = session.get(file_url)

            if file_response.status_code == 200:
                path = urlparse(file_response.url).path
                filename = unquote(os.path.basename(path))
                file_path = os.path.join(save_dir, filename)

                logger.info(f" -> Descargando '{filename}'")
                with open(file_path, 'wb') as f:
                    f.write(file_response.content)
            else:
                logger.warning(f"No se pudo descargar el archivo de {file_url} (Status: {file_response.status_code})")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener la página de recursos: {e}")


def scrape_course(url: str, browser: str, cookie_file: str, quality: str, langs: list, audios: list):
    """Función principal que orquesta el proceso de scraping y descarga del curso."""
    session = create_session(browser, cookie_file)
    if not session:
        return

    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al acceder a la URL del curso: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # --- 1. Extraer Título y Portada ---
    title_element = soup.find('h1', class_=lambda c: c and ('course-header-new__title' in c or 'my-[10px]' in c))

    if not title_element:
        logger.error("No se pudo encontrar el título del curso.")
        return

    course_title = sanitize_and_trim_filename(title_element.text, DOWNLOAD_DIR)
    course_dir = os.path.join(DOWNLOAD_DIR, course_title)
    os.makedirs(course_dir, exist_ok=True)

    logger.info(f"CURSO: {course_title.upper()}")

    pattern = r'https://imgproxy\.domestika\.org/unsafe/s:\d+:\d+/rs:fill/ex:true/el:true/plain/src://course-covers/\d+/\d+/\d+/\d+-original\.(jpg|jpeg|png|webp|avif)\?\d+'
    cover_match = re.search(pattern, str(soup))
    if cover_match:
        cover_url = cover_match.group(0)
        ext = cover_match.group(1)  # grupo (jpg|jpeg|png|webp|avif)
        logger.info("Descargando imagen de portada...")
        logger.info(f"URL: {cover_url}")
        try:
            resp = session.get(cover_url)
            if resp.status_code == 200:
                with open(os.path.join(course_dir, f"cover.{ext}"), "wb") as f:
                    f.write(resp.content)
        except requests.exceptions.RequestException:
            logger.warning("No se pudo descargar la imagen de portada.")

    # --- 2. Procesar Unidades y Lecciones ---
    units = soup.find_all('li', class_='unit-item')
    if units:
        for unit in units:
            title_element = unit.select_one('h4.unit-item__title a')
            if not title_element:
                continue

            unit_title = sanitize_and_trim_filename(title_element.text, course_dir)
            unit_link = title_element['href']
            unit_dir = os.path.join(course_dir, unit_title)

            logger.info(f"\n--- PROCESANDO UNIDAD: {unit_title} ---")

            data = extract_initial_props(unit_link, session)
            if not data:
                continue

            # Lecciones en video de la unidad
            if data.get('videos') and isinstance(data['videos'], list):
                for i, lesson in enumerate(data['videos'], 1):
                    lesson_title = sanitize_and_trim_filename(lesson['video']['title'], course_dir)
                    file_name = f"{i:02d} - {lesson_title}"
                    download_video(lesson['video']['playbackURL'], unit_dir, file_name, quality, langs, audios)

            # Proyecto Final
            if data.get('video'):
                response = session.get(unit_link, allow_redirects=False)
                # print(response.headers.get("Location"))
                if response.status_code != 200:
                    logger.info("¡¡¡ SIN ACCESO AL PROYECTO FINAL !!!")
                else:
                    project_title = "Proyecto Final"
                    project_dir = os.path.join(course_dir, project_title)
                    download_video(data['video']['playbackURL'], project_dir, project_title, quality, langs, audios)

        # --- 3. Descargar Recursos Adicionales ---
        resources_tag = soup.find('li', string=lambda t: t and ('Recursos adicionales' in t or 'Additional Resources' in t))
        if resources_tag and resources_tag.find('a'):
            resources_link = resources_tag.find('a')['href']
            resources_dir = os.path.join(course_dir, 'Recursos Adicionales')
            download_attachments(session, resources_link, resources_dir)
        else:
            logger.info("!!! SIN ACCESO A RECURSOS !!!")


# --- INICIO DEL PROCESO ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dmstk-Downloader.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL del stream m3u8"
    )
    parser.add_argument(
        "-b", "--browser",
        help="Navegador para extraer las cookies.",
        choices=["firefox", "chrome", "edge", "brave"],
        default="firefox",
    )
    parser.add_argument(
        "-c", "--cookies",
        help="Cargar cookies de un archivo JSON.",
        default=None
    )
    parser.add_argument(
        "-q", "--quality",
        help="Resolución de video (ej: 1080, 720, 540).",
        default="1080",
    )
    parser.add_argument(
        "-l", "--lang",
        action="append",
        choices=ISO_639_1_TO_2.keys(),
        metavar="LANG",
        help="Subtítulos (2 letras). Ej: -l en -l pt",
    )
    parser.add_argument(
        "-a", "--audio",
        action="append",
        choices=ISO_639_1_TO_2.keys(),
        metavar="LANG",
        help="Audios extra (2 letras). Ej: -a en -a pt",
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="Muestra los idiomas disponibles."
    )

    args = parser.parse_args()

    if args.list_langs:
        print("Idiomas disponibles:\n")
        for k, iso3 in ISO_639_1_TO_2.items():
            print(f"  {k:<4} → {iso3:<4}")
        raise SystemExit(0)

    if not args.url:
        parser.error("el argumento 'url' es obligatorio (excepto con --list-langs)")

    # Definir defaults si el usuario no pone nada
    langs = args.lang if args.lang else ["es|es_la"] # Por defecto español
    audios = args.audio if args.audio else []  # Por defecto ninguno extra

    setup_logging()

    banner()

    validated_url = validate_and_format_url(args.url)
    if not validated_url:
        logger.error("La URL proporcionada no es válida. Formato esperado: https://www.domestika.org/.../courses/...")
    else:
        start_time = time.time()

        scrape_course(validated_url, args.browser, args.cookies, args.quality, langs, audios)

        end_time = time.time()
        elapsed_time = end_time - start_time
        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)

        print()

        logger.info("Proceso Finalizado.")
        logger.info(f'Duración total: {int(hours)}h {int(minutes)}m {int(seconds)}s.')
        print()
        logger.info("*** Created by alphaDRM ***")
