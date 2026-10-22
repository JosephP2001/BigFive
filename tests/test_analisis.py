import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import analisis as a  # noqa: E402

LEX = a.cargar_lexico(a.LEXICO_POR_DEFECTO)


def post(i, vistas, likes, comentarios=1, compartidos=1, dia=1):
    return {
        "id": str(i), "vistas": vistas, "likes": likes,
        "interacciones": likes + comentarios + compartidos,
        "fecha": f"2026-10-{dia:02d} 12:00",
    }


class TestBigFive(unittest.TestCase):
    def test_texto_neutro_da_50(self):
        r = a.puntuar_big_five("mesa silla ventana", LEX)
        for rasgo in a.RASGOS:
            self.assertEqual(r["rasgos"][rasgo]["puntaje"], 50.0)

    def test_extraversion_sube(self):
        r = a.puntuar_big_five("Fiesta con amigos, celebramos juntos y bailamos", LEX)
        self.assertGreater(r["rasgos"]["extraversion"]["puntaje"], 50)

    def test_neuroticismo_baja_con_calma(self):
        r = a.puntuar_big_five("calma, paz y tranquilidad para descansar", LEX)
        self.assertLess(r["rasgos"]["neuroticismo"]["puntaje"], 50)

    def test_ignora_tildes_y_mayusculas(self):
        r = a.puntuar_big_five("CELEBRACIÓN", LEX)
        self.assertEqual(r["rasgos"]["extraversion"]["aciertos_alto"], 1)

    def test_confianza_crece_con_el_texto(self):
        corto = a.puntuar_big_five("hola", LEX)["confianza_texto"]
        largo = a.puntuar_big_five("palabra " * 400, LEX)["confianza_texto"]
        self.assertLess(corto, largo)
        self.assertEqual(largo, 1.0)


class TestIndices(unittest.TestCase):
    perfil = {"seguidores": 60000, "biografia": "bio"}

    def posts(self, vistas, likes):
        return [post(i, vistas, likes, dia=i + 1) for i in range(10)]

    def test_valor_en_rango(self):
        v = a.indice_valor(self.perfil, self.posts(1500, 40))
        self.assertTrue(0 <= v["valor"] <= 100)

    def test_valor_sube_con_mas_interaccion(self):
        bajo = a.indice_valor(self.perfil, self.posts(1500, 10))["valor"]
        alto = a.indice_valor(self.perfil, self.posts(1500, 120))["valor"]
        self.assertGreater(alto, bajo)

    def test_veracidad_requiere_minimo_de_publicaciones(self):
        self.assertIsNone(a.indice_veracidad(self.perfil, self.posts(1500, 40)[:2]))

    def test_veracidad_en_rango(self):
        v = a.indice_veracidad(self.perfil, self.posts(1500, 40))
        self.assertTrue(0 <= v["veracidad"] <= 100)

    def test_audiencia_sin_vistas_baja_la_veracidad(self):
        # 100 mil seguidores y casi nadie ve las publicaciones: señal débil de autenticidad
        perfil = {"seguidores": 100000, "biografia": "bio"}
        normal = a.indice_veracidad(perfil, self.posts(8000, 300))["veracidad"]
        raro = a.indice_veracidad(perfil, self.posts(50, 2))["veracidad"]
        self.assertGreater(normal, raro)

    def test_sin_publicaciones_con_vistas(self):
        self.assertIsNone(a.indice_valor(self.perfil, []))


class TestFlujo(unittest.TestCase):
    def test_analizar_con_salida_minima_del_scraper(self):
        datos = {
            "perfil": {"usuario": "demo", "seguidores": 500, "biografia": "Viajamos y exploramos"},
            "publicaciones": [post(i, 300, 15, dia=i + 1) for i in range(5)],
            "corpus_texto": "Viajamos y exploramos con amigos",
        }
        res = a.analizar(datos, LEX)
        self.assertEqual(res["usuario"], "demo")
        self.assertGreater(res["big_five"]["rasgos"]["apertura"]["puntaje"], 50)
        self.assertIsNotNone(res["valor"])


if __name__ == "__main__":
    unittest.main()
