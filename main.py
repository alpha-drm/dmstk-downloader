import argparse
from bs4 import BeautifulSoup
import browser_cookie3
import time
import requests
import json
import logging
import coloredlogs
import os
import subprocess
import re
from urllib.parse import urlparse, unquote
from colorama import Fore, Back, Style, init
from pyfiglet import Figlet
from typing import Dict, Any, Optional

# --- CONSTANTES ---
LOG_DIR = "logs_dmstk"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "Courses")
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0'

# --- CONFIGURACIÓN DEL LOGGER ---
logger = logging.getLogger('Dmstk-Downloader')


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

def sanitize_and_trim_filename(name: str, base_path: str, limite: int = 200) -> str:
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
    cleaned_name = re.sub(r'[<>:"/\\|?*]', '_', name).strip()

    # 2. Calcular longitud total
    ruta_base = os.path.abspath(base_path)
    ruta_completa = os.path.join(ruta_base, cleaned_name)

    if len(ruta_completa) <= limite:
        return cleaned_name

    # 3. Calcular cuánto espacio hay para el nombre del archivo
    base_len = len(os.path.join(ruta_base, ""))
    espacio_disponible = limite - base_len

    # 4. Recortar el nombre y devolver
    nombre_recortado = cleaned_name[:espacio_disponible].rstrip()

    return nombre_recortado


def validate_and_format_url(url: str) -> Optional[str]:
    """Valida y formatea la URL del curso de Domestika."""
    regex = r"(https://www\.domestika\.org/.+?/courses/\d+-[-\w]+)(/course)?/?$"
    match = re.match(regex, url)
    if match:
        return match.group(1) + "/course"
    return None


def create_session(browser: str) -> Optional[requests.Session]:
    """Crea una sesión de requests con las cookies del navegador especificado."""
    try:
        # Usar getattr para obtener la función de cookies dinámicamente
        cookie_fn = getattr(browser_cookie3, browser)
        cj = cookie_fn(domain_name="domestika")
    except (AttributeError, browser_cookie3.BrowserCookieError) as e:
        logger.error(f"No se pudieron cargar las cookies para '{browser}': {e}")
        logger.error("Asegúrate de haber iniciado sesión en Domestika en ese navegador.")
        return None

    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    session.cookies.update({cookie.name: cookie.value for cookie in cj})
    return session


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


def download_video(url: str, save_dir: str, file_name: str, quality: str, lang: str):
    """Descarga un video usando N_m3u8DL-RE."""
    output_file = os.path.join(save_dir, file_name + '.mp4')
    
    if os.path.exists(output_file):
        logger.warning(f"El archivo '{file_name}.mp4' ya existe.")
        return

    os.makedirs(save_dir, exist_ok=True)
    
    logger.info(f"Descargando video: '{file_name}'")
    command = [
        'N_m3u8DL-RE',
        '-sv', f'res={quality}',
        url,
        '-ss', f'name={lang}',
        '--save-dir', save_dir,
        '--save-name', file_name
    ]
    
    try:
        process = subprocess.Popen(command)
        process.wait() 
        if process.returncode != 0:
            logger.error(f"Error al descargar '{file_name}'. Código de salida: {process.returncode}")
    except FileNotFoundError:
        logger.critical("'N_m3u8DL-RE' no se encontró. Asegúrate de que esté en tu PATH y sea ejecutable.")
        exit(1) # Terminar el script si la dependencia clave no está
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado con subprocess: {e}")


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


def scrape_course(url: str, browser: str, quality: str, lang: str):
    """Función principal que orquesta el proceso de scraping y descarga del curso."""
    session = create_session(browser)
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

    pattern = r'https://imgproxy\.domestika\.org/unsafe/s:\d+:\d+/rs:fill/ex:true/el:true/plain/src://course-covers/\d+/\d+/\d+/\d+-original\.jpg\?\d+'
    cover_match = re.search(pattern, str(soup))
    if cover_match:
        cover_url = cover_match.group(0)
        logger.info("Descargando imagen de portada...")
        try:
            resp = session.get(cover_url)
            if resp.status_code == 200:
                with open(os.path.join(course_dir, 'cover.jpg'), 'wb') as f:
                    f.write(resp.content)
        except requests.exceptions.RequestException:
            logger.warning("No se pudo descargar la imagen de portada.")

    # --- 2. Procesar Unidades y Lecciones ---
    units = soup.find_all('li', class_='unit-item')
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
                download_video(lesson['video']['playbackURL'], unit_dir, file_name, quality, lang)

        # Proyecto Final (si está en esta "unidad")
        if data.get('video'):
            project_title = sanitize_and_trim_filename(data.get('title', 'Proyecto Final'), course_dir)
            project_dir = os.path.join(course_dir, project_title)
            file_name = f"01 - {project_title}"
            download_video(data['video']['playbackURL'], project_dir, file_name, quality, lang)

    # --- 3. Descargar Recursos Adicionales ---
    resources_tag = soup.find('li', string=lambda t: t and ('Recursos adicionales' in t or 'Additional Resources' in t))
    if resources_tag and resources_tag.find('a'):
        resources_link = resources_tag.find('a')['href']
        resources_dir = os.path.join(course_dir, 'Recursos Adicionales')
        download_attachments(session, resources_link, resources_dir)


# --- INICIO DEL PROCESO ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script para descargar cursos de Dmstk.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("url", help="URL completa del curso a descargar.")
    parser.add_argument(
        "-b", "--browser",
        help="Navegador para extraer las cookies.",
        choices=["firefox", "chrome", "edge", "brave"],
        default="firefox",
    )
    parser.add_argument(
        "-q", "--quality",
        help="Resolución de video preferida (ej: 1080, 720).",
        default="1080",
    )
    parser.add_argument(
        "-l", "--lang",
        help="Idioma preferido para los subtítulos (ej: Español, English).",
        default="Español",
    )
    
    args = parser.parse_args()

    setup_logging()

    banner()

    validated_url = validate_and_format_url(args.url)
    if not validated_url:
        logger.error("La URL proporcionada no es válida. Formato esperado: https://www.domestika.org/.../courses/...")
    else:
        start_time = time.time()
        
        scrape_course(validated_url, args.browser, args.quality, args.lang)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)
        
        print()
        
        logger.info("Proceso Finalizado.")
        logger.info(f'Duración total: {int(hours)}h {int(minutes)}m {int(seconds)}s.')
        print()
        logger.info("*** Created by alphaDRM ***")
