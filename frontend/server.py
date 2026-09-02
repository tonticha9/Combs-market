"""
Server ndogo ya kuhudumia frontend (index.html) kwenye Railway.
Railway inatoa PORT kupitia environment variable - script hii inaisoma
na kuanzisha server kwenye port hiyo.
"""
import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 8080))

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Frontend server inaendesha kwenye port {PORT}")
    httpd.serve_forever()

