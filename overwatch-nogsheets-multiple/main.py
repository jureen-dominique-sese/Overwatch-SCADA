"""
Overwatch SCADA - Main Application with Multi-Window Support
Allows opening multiple interfaces simultaneously
"""
import webview
import os
from api import OverwatchAPI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, 'static', 'html')


def get_html_path(filename):
    """Get absolute path for HTML file"""
    path = os.path.join(HTML_DIR, filename)
    return f"file://{path}"  # Add file:// protocol


class WindowManager:
    """Manages multiple application windows"""
    
    def __init__(self, api):
        self.api = api
        self.windows = {}
    
    def open_dashboard(self):
        """Open main dashboard window"""
        if 'dashboard' not in self.windows or not self.windows['dashboard']:
            self.windows['dashboard'] = webview.create_window(
                "Overwatch SCADA - Dashboard",
                url=get_html_path('index.html'),
                js_api=self.api,
                width=1200,
                height=800,
                resizable=True
            )
        return self.windows['dashboard']
    
    def open_map(self):
        """Open map interface window"""
        self.windows['map'] = webview.create_window(
            "Overwatch SCADA - Map",
            url=get_html_path('map.html'),
            js_api=self.api,
            width=1400,
            height=900,
            resizable=True
        )
        return self.windows['map']
    
    def open_stats(self):
        """Open statistics window"""
        self.windows['stats'] = webview.create_window(
            "Overwatch SCADA - Statistics",
            url=get_html_path('stats.html'),
            js_api=self.api,
            width=1200,
            height=800,
            resizable=True
        )
        return self.windows['stats']
    
    def open_logs(self):
        """Open logs window"""
        self.windows['logs'] = webview.create_window(
            "Overwatch SCADA - Logs",
            url=get_html_path('logs.html'),
            js_api=self.api,
            width=1300,
            height=850,
            resizable=True
        )
        return self.windows['logs']


def main():
    """Main application entry point"""
    # Initialize backend API
    api = OverwatchAPI()
    
    # Create window manager
    window_manager = WindowManager(api)
    
    # Create main dashboard window
    dashboard = window_manager.open_dashboard()
    
    # Optional: Open all windows at startup for multi-monitor setup
    # Uncomment the lines below to auto-open all interfaces
    # window_manager.open_map()
    # window_manager.open_stats()
    # window_manager.open_logs()
    
    # Start the application
    print("=" * 50)
    print("⚡ Overwatch SCADA System Starting")
    print("=" * 50)
    print(f"📂 HTML Directory: {HTML_DIR}")
    print(f"🌐 Dashboard: {get_html_path('index.html')}")
    print("=" * 50)
    
    # Start webview (blocking call)
    webview.start(debug=True)


if __name__ == "__main__":
    main()