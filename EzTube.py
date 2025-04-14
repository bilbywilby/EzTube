import PySimpleGUI as sg
import yt_dlp
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import webbrowser
import logging
import traceback
import subprocess
import sys
import importlib.metadata
import json
from datetime import datetime
from queue import Queue, Empty
from PIL import Image
import io
import shutil
import re

# Configure logging
logging.basicConfig(filename='downloader.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    'download_dir': os.path.expanduser('~/Downloads'),
    'max_workers': 4,
    'default_format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
    'default_resolution': 'best',
    'default_audio_format': 'mp3',
    'include_metadata': True,
    'extract_thumbnail': True,
    'theme': 'DarkBlue',
    'use_ffmpeg': False,
    'auto_queue': False,
    'show_advanced': False
}


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return {**DEFAULT_CONFIG, **config}
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        sg.popup_error(f"Error saving configuration: {e}")


config = load_config()

# Apply theme
sg.theme(config.get('theme', 'DarkBlue'))

# --- Constants ---
FORMATS = ['mp4', 'mkv', 'webm', 'best']
RESOLUTIONS = ['240p', '360p', '480p', '720p', '1080p',
               '1080p60', '1440p', '1440p60', '2160p', '2160p60', 'best']
AUDIO_FORMATS = ['mp3', 'wav', 'flac', 'm4a', 'best']

# --- Dependency Check and Update ---


def check_and_update_dependencies():
    try:
        required_packages = ['yt-dlp', 'PySimpleGUI', 'pillow']
        for package in required_packages:
            try:
                version = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                install_package(package)
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'])
    except Exception as e:
        logging.error(f"Dependency check/update failed: {e}")
        sg.popup_error(f"Error checking/updating dependencies.\n{e}")


def install_package(package):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    except Exception as e:
        logging.error(f"Installation of {package} failed: {e}")
        sg.popup_error(f"Error installing {package}.\n{e}")

# --- Utility Functions ---


def check_disk_space(download_dir, required_space):
    total, used, free = shutil.disk_usage(download_dir)
    if free < required_space:
        sg.popup_error(
            f"Insufficient disk space in {download_dir}. Required: {required_space / (1024**3):.2f} GB, Available: {free / (1024**3):.2f} GB")
        return False
    return True


def update_progress(d, window):
    if d.get('total_bytes') and d.get('downloaded_bytes'):
        percent_complete = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
        window['PROGRESS'].update(percent_complete)
    elif d.get('_percent_str') != '---%':
        window['PROGRESS'].update(int(float(d['_percent_str'][:-1])))


def update_queue_display(window, queue):
    queue_list = [f"{i + 1}. {item['url']}" for i,
                 item in enumerate(list(queue.queue))]
    window['QUEUE_DISPLAY'].update('\n'.join(queue_list))


def log_to_gui(message, window):
    window['QUEUE_DISPLAY'].update(f"{message}\n", append=True)


def estimate_download_size(url, format_str, resolution_str):
    try:
        ydl_opts = {
            'format': f'bestvideo[height<={resolution_str.replace("p", "")}]+bestaudio/best[height<={resolution_str.replace("p", "")}]/best' if resolution_str != 'best' else 'best',
            'noplaylist': True,
            'quiet': True,
            'simulate': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'extractaudio': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if info_dict:
                return info_dict['filesize'] or info_dict['entries'][0]['filesize'] if 'entries' in info_dict else 0
            return 0
    except Exception:
        return 0

# --- Download Function ---


def download_video(queue_item, window):
    url = queue_item['url']
    download_dir = queue_item['download_dir']
    output_format = queue_item['output_format']
    resolution = queue_item['resolution']
    include_metadata = queue_item['include_metadata']
    download_subs = queue_item['download_subs']
    extract_audio = queue_item['extract_audio']
    audio_format = queue_item['audio_format']
    extract_thumbnail = queue_item['extract_thumbnail']
    use_ffmpeg = queue_item['use_ffmpeg']

    try:
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'format': f'bestvideo[height<={resolution.replace("p", "")}]+bestaudio/best[height<={resolution.replace("p", "")}]/best' if resolution != 'best' else 'best',
            'writesubtitles': download_subs,
            'writeautomaticsub': download_subs,
            'extractaudio': extract_audio,
            'audioformat': audio_format if extract_audio else None,
            'noplaylist': True,
            'write_info_json': True,
            'embedthumbnail': True,
            'embedmetadata': include_metadata,
            'merge_output_format': 'mkv' if use_ffmpeg else 'mp4',
            'progress_hooks': [lambda d: update_progress(d, window)],
            'quiet': True,
            'nocheckcertificate': False,
            'source_address': '0.0.0.0',
            'retries': 3,
            'fragment_retries': 3,
            'logtostderr': True,
            'extract_flat': 'in_playlist'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            ydl.download([url])

            if extract_thumbnail:
                try:
                    thumbnail_url = info_dict.get(
                        'thumbnail') or info_dict['entries'][0].get('thumbnail') if 'entries' in info_dict else None
                    if thumbnail_url:
                        thumbnail_data = ydl.urlopen(thumbnail_url).read()
                        thumbnail_image = Image.open(
                            io.BytesIO(thumbnail_data))
                        thumbnail_path = os.path.join(
                            download_dir, f"{info_dict['title']}.jpg")
                        thumbnail_image.save(thumbnail_path)
                except Exception as thumb_err:
                    logging.warning(f"Thumbnail extraction failed: {thumb_err}")

        window['STATUS'].update('Download Complete!')

    except Exception as e:
        error_message = f'An error occurred during download: {str(e)}'
        window['STATUS'].update(f'Error: {error_message}')
        sg.popup_error(error_message)
        logging.error(error_message + '\n' + traceback.format_exc())
    finally:
        window.write_event_value('-DOWNLOAD_FINISHED-', queue_item)


# --- GUI Layout ---
def create_main_window(show_advanced=False):
    basic_options = [
        [sg.Text("Enter the URL of the video or playlist to download:")],
        [sg.Input(key='URL', size=(60))],
        [sg.Text("Save to Directory:")],
        [sg.Input(default_text=config['download_dir'], key='DIR', size=(50)),
         sg.FolderBrowse()],
        [sg.Frame("Video Options", [
            [sg.Text("Select Format:"), sg.Combo(FORMATS, default_value=config['default_format'], key='FORMAT', size=(10))],
            [sg.Text("Select Resolution:"), sg.Combo(
                RESOLUTIONS, default_value=config['default_resolution'], key='RES', size=(10))],
            [sg.Checkbox('Download Subtitles', default=False, key='SUBS')],
        ])],
        [sg.Frame("Audio Options", [
            [sg.Checkbox('Extract Audio Only', default=False, key='AUDIO')],
            [sg.Text("Audio Format:"), sg.Combo(
                AUDIO_FORMATS, default_value=config['default_audio_format'], key='AUDIO_FORMAT', size=(10))],
        ])],
    ]

    advanced_options = [
        [sg.Frame("Advanced Options", [
            [sg.Checkbox('Include Metadata',
                           default=config['include_metadata'], key='METADATA')],
            [sg.Checkbox('Extract Thumbnail',
                           default=config['extract_thumbnail'], key='THUMBNAIL')],
            [sg.Checkbox('Use FFmpeg for merging',
                           default=config['use_ffmpeg'], key='USE_FFMPEG')],
        ])]
    ]

    buttons = [
        [sg.Button('Add to Queue', size=(12)), sg.Button(
            'Remove from Queue', size=(15)), sg.Button('Download Queue', size=(12)),
         sg.Button('Cancel', size=(10)), sg.Button('Preview', size=(10)), sg.Button('Settings', size=(10)),
         sg.Button('Show Advanced' if not show_advanced else 'Hide Advanced',
                    size=(12))],
    ]

    queue_display = [
        [sg.Multiline(size=(60, 5), key='QUEUE_DISPLAY', disabled=True)],
    ]

    progress_bar = [
        [sg.ProgressBar(100, orientation='h', size=(20, 20),
                        key='PROGRESS', bar_color=('#008000', '#FFFFFF'))],
        [sg.Image(key='THUMBNAIL_PREVIEW', size=(200, 200))],
        [sg.Text('', key='STATUS', size=(40, 1)]
    ]

    layout = basic_options + \
        (advanced_options if show_advanced else []) + \
        buttons + queue_display + progress_bar
    return sg.Window('YouTube Downloader', layout, icon='youtube.ico', finalize=True)


# --- Settings Window ---
def settings_window():
    settings_layout = [
        [sg.Text("Download Directory:")],
        [sg.Input(default_text=config['download_dir'],
                  key='download_dir', size=(50)), sg.FolderBrowse()],
        [sg.Text("Max Download Threads:")],
        [sg.Input(key='max_workers',
                  default_text=str(config['max_workers']), size=(5))],
        [sg.Text("Default Video Format:")],
        [sg.Combo(FORMATS, default_value=config['default_format'],
                  key='default_format', size=(10))],
        [sg.Text("Default Resolution:")],
        [sg.Combo(RESOLUTIONS, default_value=config['default_resolution'],
                  key='default_resolution', size=(10))],
        [sg.Text("Default Audio Format:")],
        [sg.Combo(AUDIO_FORMATS, default_value=config['default_audio_format'],
                  key='default_audio_format', size=(10))],
        [sg.Checkbox("Include Metadata", default=config['include_metadata'],
                       key='include_metadata')],
        [sg.Checkbox("Extract Thumbnail", default=config['extract_thumbnail'],
                       key='extract_thumbnail')],
        [sg.Checkbox("Use FFmpeg for merging",
                       default=config['use_ffmpeg'], key='use_ffmpeg')],
        [sg.Checkbox("Auto Add to Queue", default=config['auto_queue'],
                       key='auto_queue')],
        [sg.Text("GUI Theme:"), sg.Combo(sg.theme_list(), default_value=config['theme'],
                                        key='theme', size=(15))],
        [sg.Button('Save'), sg.Button('Cancel')]
    ]
    settings_window = sg.Window('Settings', settings_layout, modal=True)
    while True:
        event, values = settings_window.read(close=True)
        if event == 'Save':
            try:
                global config
                config.update({k: values[k] for k in values})
                config['max_workers'] = int(config['max_workers'])
                save_config(config)
                for key in config:
                    if key in window:
                        try:
                            window[key].update(value=config[key])
                        except:
                            pass
                sg.popup_auto_close("Settings saved!", auto_close_duration=2)
                sg.theme(config['theme'])
                window.close()
                window = create_main_window(
                    show_advanced=config['show_advanced'])
                break
            except ValueError:
                sg.popup_error("Invalid input.")
        if event == 'Cancel':
            break
    settings_window.close()


# --- Main Event Loop ---
if __name__ == '__main__':
    check_and_update_dependencies()
    download_queue = Queue()
    window = create_main_window(show_advanced=config['show_advanced'])

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == 'Cancel':
            break

        if event == 'Add to Queue':
            url = values['URL']
            download_dir = values['DIR']
            output_format = values['FORMAT']
            resolution = values['RES']
            include_metadata = values.get(
                'METADATA', config['include_metadata'])  # Use get() with default
            download_subs = values['SUBS']
            extract_audio = values['AUDIO']
            audio_format = values['AUDIO_FORMAT']
            extract_thumbnail = values.get(
                'THUMBNAIL', config['extract_thumbnail'])
            use_ffmpeg = values.get('USE_FFMPEG', config['use_ffmpeg'])

            if not url.strip():
                sg.popup_error("Please enter a valid URL.")
                continue

            estimated_size = estimate_download_size(
                url, output_format, resolution)
            if estimated_size and not check_disk_space(download_dir, estimated_size * 1.1):  # Add 10% buffer
                continue

            queue_item = {
                'url': url,
                'download_dir': download_dir,
                'output_format': output_format,
                'resolution': resolution,
                'include_metadata': include_metadata,
                'download_subs': download_subs,
                'extract_audio': extract_audio,
                'audio_format': audio_format,
                'extract_thumbnail': extract_thumbnail,
                'use_ffmpeg': use_ffmpeg
            }
            download_queue.put(queue_item)
            update_queue_display(window, download_queue)
            window['STATUS'].update("URL Added to Queue.")
            if config['auto_queue']:
                event = 'Download Queue'

        elif event == 'Remove from Queue':
            if not download_queue.empty():
                download_queue.get()
                update_queue_display(window, download_queue)
                window['STATUS'].update("Removed item from Queue.")
            else:
                sg.popup_error("The queue is empty.")

        elif event == 'Download Queue':
            if not download_queue.empty():
                window['STATUS'].update("Processing Download Queue...")
                with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
                    futures = []
                    while not download_queue.empty():
                        queue_item = download_queue.get()
                        futures.append(
                            executor.submit(download_video, queue_item, window))
                    for future in as_completed(futures):
                        try:
                            future.result()  # Get result (or exception)
                        except Exception as e:
                            logging.error(f"Download failed: {e}")
                            log_to_gui(f"Download failed: {e}", window)
                download_queue.queue.clear()
                update_queue_display(window, download_queue)
                window['STATUS'].update("Download Queue Finished!")
            else:
                sg.popup_error("Download queue is empty.")

        elif event == 'Preview':
            url = values['URL']
            if url.strip():
                try:
                    webbrowser.open_new_tab(url)
                except Exception as e:
                    sg.popup_error(f"Error opening URL: {e}")
                    logging.error(f"Error opening URL: {e}")
            else:
                sg.popup_error("Please enter a valid URL.")

        elif event == 'Settings':
            settings_window()

        elif event == 'Show Advanced' or event == 'Hide Advanced':
            config['show_advanced'] = not config['show_advanced']
            save_config(config)
            window.close()
            window = create_main_window(
                show_advanced=config['show_advanced'])

    window.close()