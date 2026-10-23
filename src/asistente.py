import argparse
import json
import sys
from pathlib import Path

import analisis as a
from ia import ClienteOllama, ErrorIA

CARPETA_DATOS = Path("datos")
CARPETA_RESULTADOS = Path("resultados")
MAX_CONTEXTO = 9000

PROMPT = """Eres un asistente que responde preguntas sobre los resultados del análisis de una cuenta de TikTok.

Reglas:
- Responde solo con base en los datos entregados entre <datos> y </datos>. Si la respuesta no está ahí, di "No está en los datos".
- Cita las cifras o campos que usas.
- En caso de que se pregunte por los BIG FIVE para este perfil en especìfico, presénta los 5 rasgos del BIG FIVE como porcentajes, deben sumar %100 entre los 5.
- Responde en español y de forma breve.
- Si te piden inferir algo, limítate a describir cifras y textos que aparecen en los datos y cítalos. No atribuyas emociones, intenciones ni rasgos que no estén en el análisis.
- Para preguntas sobre el rasgo más alto, compara los puntajes del análisis léxico y de la estimación IA, di cuál es el mayor en cada uno e indica que son estimaciones exploratorias."""


def usuarios_disponibles():
    return sorted(p.stem.replace("salida_", "") for p in CARPETA_DATOS.glob("salida_*.json"))


def _leer(ruta):
    ruta = Path(ruta)
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def construir_contexto(usuario):
    datos = _leer(CARPETA_DATOS / f"salida_{usuario}.json")
    if datos is None:
        raise FileNotFoundError(f"No existe datos/salida_{usuario}.json. Primero corre src/scraper.py.")
    analisis = _leer(CARPETA_RESULTADOS / f"analisis_{usuario}.json")
    if analisis is None:
        analisis = a.analizar(datos, a.cargar_lexico(a.LEXICO_POR_DEFECTO))
    ia = _leer(CARPETA_RESULTADOS / f"ia_{usuario}.json")

    perfil = datos.get("perfil") or {}
    campos = ("usuario", "nombre", "seguidores", "siguiendo", "videos", "likes_totales",
              "biografia", "idioma", "region", "cuenta_creada")
    posts = [
        {
            "fecha": p.get("fecha"), "tipo": p.get("tipo"), "vistas": p.get("vistas"),
            "likes": p.get("likes"), "comentarios": p.get("comentarios"),
            "compartidos": p.get("compartidos"), "guardados": p.get("guardados"),
            "interacciones": p.get("interacciones"),
            "descripcion": (p.get("descripcion") or "")[:200], "hashtags": p.get("hashtags"),
        }
        for p in datos.get("publicaciones", [])
    ]
    # Las publicaciones van al final: si el texto excede MAX_CONTEXTO, el recorte
    # afecta a ellas y no al análisis ni a la estimación de la IA.
    contexto = {
        "perfil": {k: perfil.get(k) for k in campos},
        "analisis_lexico": analisis,
        "estimacion_ia": ia,
        "publicaciones": posts,
    }
    texto = json.dumps(contexto, ensure_ascii=False)
    if len(texto) > MAX_CONTEXTO:
        for p in posts:
            p["descripcion"] = p["descripcion"][:80]
        texto = json.dumps(contexto, ensure_ascii=False)
    return texto[:MAX_CONTEXTO]


def responder(cliente, contexto, historial, pregunta):
    mensajes = (
        [{"role": "system", "content": f"{PROMPT}\n<datos>\n{contexto}\n</datos>"}]
        + historial[-8:]
        + [{"role": "user", "content": pregunta}]
    )
    respuesta = cliente.chat(mensajes, temperatura=0.2)
    historial += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": respuesta}]
    return respuesta


def elegir_usuario(usuario):
    if usuario:
        return usuario.lstrip("@")
    disponibles = usuarios_disponibles()
    if not disponibles:
        sys.exit("No hay datos en datos/. Primero corre src/scraper.py.")
    if len(disponibles) == 1:
        return disponibles[0]
    print("Cuentas disponibles: " + ", ".join(disponibles))
    return input("¿Sobre cuál quieres preguntar? ").strip().lstrip("@")


def main():
    ap = argparse.ArgumentParser(description="Preguntas sobre los resultados, con una IA local (Ollama)")
    ap.add_argument("usuario", nargs="?", help="usuario analizado (sin @)")
    ap.add_argument("--pregunta", help="hace una sola pregunta y termina")
    ap.add_argument("--modelo", help="modelo de Ollama (por defecto el de .env o llama3.2)")
    args = ap.parse_args()

    usuario = elegir_usuario(args.usuario)
    try:
        contexto = construir_contexto(usuario)
    except FileNotFoundError as e:
        sys.exit(str(e))
    cliente = ClienteOllama(modelo=args.modelo)
    historial = []

    try:
        if args.pregunta:
            print(responder(cliente, contexto, historial, args.pregunta))
            return
        print(f"Asistente sobre @{usuario} (modelo: {cliente.modelo}). Escribe 'salir' para terminar.")
        while True:
            pregunta = input("\nPregunta: ").strip()
            if pregunta.lower() in ("salir", "exit", "q"):
                break
            if pregunta:
                print("\n" + responder(cliente, contexto, historial, pregunta))
    except ErrorIA as e:
        sys.exit(f"[error] {e}")
    except (EOFError, KeyboardInterrupt):
        print()


if __name__ == "__main__":
    main()