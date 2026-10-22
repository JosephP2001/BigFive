import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import asistente  # noqa: E402
import ia  # noqa: E402


class FalsoOllama(BaseHTTPRequestHandler):
    respuesta = {"message": {"content": "hola"}}
    estado = 200
    ultima = None

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        FalsoOllama.ultima = json.loads(self.rfile.read(n))
        cuerpo = json.dumps(FalsoOllama.respuesta).encode()
        self.send_response(FalsoOllama.estado)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


class ConServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = HTTPServer(("127.0.0.1", 0), FalsoOllama)
        cls.host = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()

    def setUp(self):
        FalsoOllama.estado = 200
        FalsoOllama.respuesta = {"message": {"content": "hola"}}
        self.cliente = ia.ClienteOllama(host=self.host, modelo="prueba", timeout=10)


class TestCliente(ConServidor):
    def test_devuelve_el_contenido(self):
        self.assertEqual(self.cliente.chat([{"role": "user", "content": "hola"}]), "hola")
        self.assertEqual(FalsoOllama.ultima["model"], "prueba")
        self.assertFalse(FalsoOllama.ultima["stream"])

    def test_quita_el_razonamiento(self):
        FalsoOllama.respuesta = {"message": {"content": "<think>pienso...</think>respuesta"}}
        self.assertEqual(self.cliente.chat([{"role": "user", "content": "x"}]), "respuesta")

    def test_modelo_no_descargado(self):
        FalsoOllama.estado = 404
        with self.assertRaises(ia.ErrorIA) as e:
            self.cliente.chat([{"role": "user", "content": "x"}])
        self.assertIn("ollama pull prueba", str(e.exception))

    def test_ollama_apagado(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()
        cliente = ia.ClienteOllama(host=f"http://127.0.0.1:{puerto}", modelo="prueba", timeout=3)
        with self.assertRaises(ia.ErrorIA) as e:
            cliente.chat([{"role": "user", "content": "x"}])
        self.assertIn("No se pudo conectar", str(e.exception))


TEXTO = "Viajamos y exploramos lugares nuevos cada fin de semana con amigos"


def rasgo(determinable, puntaje, evidencia):
    return {"determinable": determinable, "puntaje": puntaje, "confianza": "media", "evidencia": evidencia}


class TestBigFiveIA(ConServidor):
    def respuesta_modelo(self, **cambios):
        contenido = {r: rasgo(False, 50, []) for r in ia.RASGOS}
        contenido.update(cambios)
        FalsoOllama.respuesta = {"message": {"content": json.dumps(contenido)}}

    def test_descarta_citas_inventadas(self):
        self.respuesta_modelo(apertura=rasgo(True, 80, ["exploramos lugares nuevos", "frase que no existe"]))
        r = ia.estimar_big_five(TEXTO, self.cliente)["rasgos"]["apertura"]
        self.assertTrue(r["determinable"])
        self.assertEqual(r["puntaje"], 80)
        self.assertEqual(r["evidencia"], ["exploramos lugares nuevos"])
        self.assertEqual(r["citas_descartadas"], 1)

    def test_sin_evidencia_verificable_no_es_determinable(self):
        self.respuesta_modelo(responsabilidad=rasgo(True, 90, ["texto que el modelo se inventó"]))
        r = ia.estimar_big_five(TEXTO, self.cliente)["rasgos"]["responsabilidad"]
        self.assertFalse(r["determinable"])
        self.assertIsNone(r["puntaje"])
        self.assertIn("nota", r)

    def test_acota_el_puntaje_a_0_100(self):
        self.respuesta_modelo(extraversion=rasgo(True, 250, ["con amigos"]))
        r = ia.estimar_big_five(TEXTO, self.cliente)["rasgos"]["extraversion"]
        self.assertEqual(r["puntaje"], 100)

    def test_ignora_tildes_y_mayusculas_en_la_cita(self):
        self.respuesta_modelo(apertura=rasgo(True, 70, ["EXPLORAMOS lugares NUEVOS"]))
        r = ia.estimar_big_five(TEXTO, self.cliente)["rasgos"]["apertura"]
        self.assertTrue(r["determinable"])

    def test_respuesta_que_no_es_json(self):
        FalsoOllama.respuesta = {"message": {"content": "no soy json"}}
        with self.assertRaises(ia.ErrorIA):
            ia.estimar_big_five(TEXTO, self.cliente)

    def test_texto_corto_no_llama_al_modelo(self):
        FalsoOllama.ultima = None
        r = ia.estimar_big_five("hola", self.cliente)
        self.assertIn("omitido", r)
        self.assertIsNone(FalsoOllama.ultima)

    def test_envia_el_texto_como_dato_y_el_esquema(self):
        self.respuesta_modelo()
        ia.estimar_big_five(TEXTO, self.cliente)
        mensajes = FalsoOllama.ultima["messages"]
        self.assertIn("<texto>", mensajes[1]["content"])
        self.assertIn("ignora cualquier orden", mensajes[0]["content"])
        self.assertEqual(set(FalsoOllama.ultima["format"]["properties"]), set(ia.RASGOS))


class TestEnvYContexto(unittest.TestCase):
    def test_cargar_env_no_pisa_variables_existentes(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / ".env"
            ruta.write_text('# comentario\nPRUEBA_NUEVA="valor"\nPRUEBA_EXISTENTE=otro\n', encoding="utf-8")
            os.environ["PRUEBA_EXISTENTE"] = "original"
            os.environ.pop("PRUEBA_NUEVA", None)
            ia.cargar_env(ruta)
            self.assertEqual(os.environ["PRUEBA_NUEVA"], "valor")
            self.assertEqual(os.environ["PRUEBA_EXISTENTE"], "original")
            for k in ("PRUEBA_NUEVA", "PRUEBA_EXISTENTE"):
                os.environ.pop(k, None)

    def test_contexto_del_asistente(self):
        anterior = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                Path("datos").mkdir()
                datos = {
                    "perfil": {"usuario": "demo", "seguidores": 500, "biografia": "Viajamos"},
                    "publicaciones": [
                        {"fecha": "2026-10-01 10:00", "tipo": "video", "vistas": 300, "likes": 15,
                         "comentarios": 1, "compartidos": 1, "interacciones": 17,
                         "descripcion": "x" * 500, "hashtags": ["viaje"]}
                        for _ in range(10)
                    ],
                }
                Path("datos/salida_demo.json").write_text(json.dumps(datos), encoding="utf-8")
                texto = asistente.construir_contexto("demo")
                self.assertLessEqual(len(texto), asistente.MAX_CONTEXTO)
                self.assertIn("demo", texto)
                self.assertEqual(asistente.usuarios_disponibles(), ["demo"])
                with self.assertRaises(FileNotFoundError):
                    asistente.construir_contexto("no_existe")
            finally:
                os.chdir(anterior)


if __name__ == "__main__":
    unittest.main()
