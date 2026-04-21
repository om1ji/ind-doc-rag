import http.server
import json
import os
import urllib.parse


class DocsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _list_files(self) -> list[str]:
        return sorted(f for f in os.listdir("/docs") if f.endswith(".md"))

    def do_GET(self):
        # Получаем имя файла из пути: /opp-1.md → opp-1.md
        path = urllib.parse.unquote(self.path.lstrip("/").split("?")[0])

        if not path:
            # GET / — список файлов
            files = self._list_files()
            body = json.dumps(files, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        # Защита от path traversal
        safe = os.path.basename(path)
        fp = f"/docs/{safe}"

        if os.path.isfile(fp):
            body = open(fp, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        else:
            files = self._list_files()
            body = json.dumps(
                {"error": f"Not found: '{safe}'", "available": files},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 8000), DocsHandler)
    print("Docs API listening on :8000")
    server.serve_forever()
