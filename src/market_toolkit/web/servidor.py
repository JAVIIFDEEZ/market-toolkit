"""Servidor HTTP local (solo biblioteca estándar) que sirve la página y la API JSON."""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from market_toolkit.web.aplicacion import Aplicacion, limpiar_json
from market_toolkit.web.pagina import PAGINA

# Acción de la URL (/api/<acción>) -> método de `Aplicacion`
ACCIONES = {
    "catalogo": "catalogo",
    "buscar": "buscar",
    "datos": "cargar_datos",
    "precios_csv": "precios_csv",
    "cartera": "crear_cartera",
    "correlacion": "correlacion",
    "montecarlo": "monte_carlo",
    "informe": "informe",
    "graficos": "graficos",
    "macro": "macro",
}
HOSTS_LOCALES = ("localhost", "127.0.0.1")


class Manejador(BaseHTTPRequestHandler):
    """Atiende la página (GET /) y las acciones de la API (POST /api/<acción>)."""

    aplicacion: Aplicacion

    def _responder(self, codigo, cuerpo: bytes, tipo: str):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _responder_json(self, codigo, datos):
        cuerpo = json.dumps(limpiar_json(datos), ensure_ascii=False).encode("utf-8")
        self._responder(codigo, cuerpo, "application/json; charset=utf-8")

    def _host_valido(self) -> bool:
        # Evita que otra web use el servidor local (DNS rebinding)
        host = self.headers.get("Host", "").split(":")[0]
        return host in HOSTS_LOCALES

    def do_GET(self):
        if not self._host_valido():
            self._responder_json(403, {"error": "Host no permitido."})
        elif self.path in ("/", "/index.html"):
            marca = "checked" if self.aplicacion.sin_red else ""
            pagina = PAGINA.replace("__SINTETICO__", marca)
            self._responder(200, pagina.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._responder_json(404, {"error": "No encontrado."})

    def do_POST(self):
        accion = self.path.removeprefix("/api/")
        metodo = ACCIONES.get(accion)
        tipo = self.headers.get("Content-Type", "")
        if not self._host_valido() or not tipo.startswith("application/json"):
            self._responder_json(403, {"error": "Petición no permitida."})
            return
        if metodo is None or not self.path.startswith("/api/"):
            self._responder_json(404, {"error": "Acción desconocida."})
            return
        try:
            longitud = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(longitud) or b"{}")
            resultado = getattr(self.aplicacion, metodo)(**datos)
        except Exception as error:  # Todo error se muestra en la página, sin tumbar el servidor
            self._responder_json(400, {"error": f"{type(error).__name__}: {error}"})
        else:
            self._responder_json(200, resultado)

    def log_message(self, formato, *argumentos):
        pass  # Sin una línea de registro por cada petición


def crear_servidor(puerto: int = 8000, aplicacion: Aplicacion | None = None) -> HTTPServer:
    """Crea el servidor (sin arrancarlo), escuchando solo en la máquina local."""

    class ManejadorConAplicacion(Manejador):
        pass

    ManejadorConAplicacion.aplicacion = aplicacion or Aplicacion()
    return HTTPServer(("127.0.0.1", puerto), ManejadorConAplicacion)


def servir(puerto: int = 8000, sin_red: bool = False, abrir_navegador: bool = True):
    """Arranca la interfaz web y la mantiene activa hasta pulsar Ctrl+C."""
    servidor = crear_servidor(puerto, Aplicacion(sin_red))
    direccion = f"http://localhost:{servidor.server_port}"
    print(f"market-toolkit: interfaz web en {direccion} (Ctrl+C para salir)")
    if abrir_navegador:
        webbrowser.open(direccion)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
