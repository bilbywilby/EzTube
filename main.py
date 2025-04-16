import PySimpleGUI as sg
from config.settings import Config
from core.queue_manager import DownloadQueueManager
from gui.main_window import MainWindow
from utils.dependencies import check_and_update_dependencies

def main():
    # Initialize configuration
    config = Config()
    
    # Check dependencies
    check_and_update_dependencies()
    
    # Create queue manager
    queue_manager = DownloadQueueManager(config)
    
    # Create and run main window
    main_window = MainWindow(config, queue_manager)
    main_window.run()

if __name__ == '__main__':
    main()
