"""
Local preview server.

`python -m http.server` lets the browser cache index.html, so a rebuild can look
like it did nothing until you hard-reload. That wasted time twice. This serves
the document with no-store and lets the fingerprinted assets cache for a week.

    python serve.py [port]

Threaded on purpose. The page pulls about sixty image files, and a single
threaded server serialises them, which reads as the site hanging.
"""

import functools
import http.server
import pathlib
import socket
import sys

ROOT = pathlib.Path(__file__).parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123


class Handler(http.server.SimpleHTTPRequestHandler):
    # Keep-alive, so sixty images do not each pay for a new connection.
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        path = self.path.split("?", 1)[0]
        is_doc = path.endswith((".html", "/")) or "." not in path.rsplit("/", 1)[-1]
        if is_doc:
            self.send_header("Cache-Control", "no-store, must-revalidate")
        else:
            # build.py fingerprints css and js, and image names are stable.
            self.send_header("Cache-Control", "public, max-age=604800")
        super().end_headers()

    def handle_one_request(self):
        # A browser that navigates away mid-download aborts the socket. That is
        # normal and must not print a traceback or take the request loop down.
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self.close_connection = True

    def log_message(self, fmt, *args):
        status = str(args[1]) if len(args) > 1 else ""
        if not status.startswith(("2", "3")):
            super().log_message(fmt, *args)


class DualStackServer(http.server.ThreadingHTTPServer):
    """
    Listens on IPv6 and IPv4 at once.

    Windows resolves `localhost` to ::1 before 127.0.0.1. An IPv4-only bind
    therefore leaves http://localhost:PORT refusing connections even though the
    port is open, which looks exactly like the server being down.
    """

    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "IPPROTO_IPV6"):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def main() -> int:
    handler = functools.partial(Handler, directory=str(ROOT))
    try:
        server = DualStackServer(("::", PORT), handler)
    except OSError:
        # No usable IPv6 stack. Fall back to IPv4 on every interface.
        server = http.server.ThreadingHTTPServer(("", PORT), handler)
        server.daemon_threads = True
    print(f"serving {ROOT}")
    print(f"  http://localhost:{PORT}   (html: no-store, assets: 7d)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
