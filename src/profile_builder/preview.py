from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser


def preview(output: Path, port: int = 8000, open_browser: bool = True) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(output.resolve()))
    requested=port; server=None
    for candidate in range(requested,min(requested+20,65536)):
        try: server=ThreadingHTTPServer(("localhost",candidate),handler); port=candidate; break
        except OSError: continue
    if server is None: raise OSError(f"No available preview port found from {requested} to {min(requested+19,65535)}")
    if port!=requested: print(f"Port {requested} is already in use.\nPreview started on {port}.\n")
    url = f"http://localhost:{port}/"
    print(f"Preview available at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPreview stopped.")
    finally:
        server.server_close()
