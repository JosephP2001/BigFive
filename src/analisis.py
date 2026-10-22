#!/usr/bin/env python3

import argparse
import csv
import glob
import json
import math
import re
import statistics
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
LEXICO_POR_DEFECTO = RAIZ / "lexico_es.json"
CARPETA_RESULTADOS = Path("resultados")

RASGOS = ["apertura", "responsabilidad", "extraversion", "amabilidad", "neuroticismo"]

# --- parámetros ajustables (justificados en docs/metodologia.md) ---
SUAVIZADO = 3                    # pseudo-aciertos: acerca el puntaje a 50 si hay poca evidencia
PALABRAS_CONFIANZA_TOTAL = 300   # con este número de palabras la confianza del texto llega a 1
TASA_REFERENCIA = 0.10           # tasa de interacción que se considera "muy alta"
LOG_VISTAS_MAX = 6.0             # log10(1 + vistas) = 6  ->  1 millón de vistas
LOG_SEGUIDORES_MAX = 7.0         # log10(1 + seguidores) = 7  ->  10 millones
COBERTURA_REFERENCIA = 0.05      # vistas medianas / seguidores considerada "sana"
LIKES_RANGO_PLAUSIBLE = (0.01, 0.20)
MINIMO_PUBLICACIONES = 3


# ---------------------------------------------------------------- texto

def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes (la ñ pasa a n, igual en texto y en léxico)."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list:
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def cargar_lexico(ruta) -> dict:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    lexico = {}
    for rasgo in RASGOS:
        entrada = datos[rasgo]
        lexico[rasgo] = {
            "alto": [normalizar(x) for x in entrada["alto"]],
            "bajo": [normalizar(x) for x in entrada["bajo"]],
        }
    return lexico


def coincidencias(tokens: list, raices: list) -> list:
    """Palabras del texto que empiezan con alguna de las raíces del léxico."""
    return [t for t in tokens if any(t.startswith(r) for r in raices)]


def puntuar_big_five(texto: str, lexico: dict) -> dict:
    """
    Por rasgo: puntaje = 50 + 50 * (alto - bajo) / (alto + bajo + SUAVIZADO).
    Sin evidencia el puntaje es 50; con mucha evidencia tiende a 0 o 100.
    """
    tokens = tokenizar(texto)
    n = len(tokens)
    rasgos = {}
    for r in RASGOS:
        alto = coincidencias(tokens, lexico[r]["alto"])
        bajo = coincidencias(tokens, lexico[r]["bajo"])
        a, b = len(alto), len(bajo)
        puntaje = 50 + 50 * (a - b) / (a + b + SUAVIZADO)
        rasgos[r] = {
            "puntaje": round(puntaje, 1),
            "aciertos_alto": a,
            "aciertos_bajo": b,
            "palabras_alto": sorted(set(alto)),
            "palabras_bajo": sorted(set(bajo)),
        }
    return {
        "palabras_analizadas": n,
        "confianza_texto": round(min(1.0, n / PALABRAS_CONFIANZA_TOTAL), 2),
        "rasgos": rasgos,
    }


# ---------------------------------------------------------------- indices

def _mediana(xs: list) -> float:
    return statistics.median(xs) if xs else 0.0


def _con_vistas(posts: list) -> list:
    return [p for p in posts if p.get("vistas")]


def indice_valor(perfil: dict, posts: list):
    """Valor = 100 * (0.40 * interacción + 0.35 * alcance + 0.25 * seguidores)."""
    usables = _con_vistas(posts)
    if not usables:
        return None
    vistas_med = _mediana([p["vistas"] for p in usables])
    tasa_med = _mediana([p.get("interacciones", 0) / p["vistas"] for p in usables])
    seguidores = (perfil or {}).get("seguidores", 0)

    c_tasa = min(tasa_med / TASA_REFERENCIA, 1.0)
    c_alcance = min(math.log10(1 + vistas_med) / LOG_VISTAS_MAX, 1.0)
    c_seg = min(math.log10(1 + seguidores) / LOG_SEGUIDORES_MAX, 1.0)
    valor = 100 * (0.40 * c_tasa + 0.35 * c_alcance + 0.25 * c_seg)
    return {
        "valor": round(valor, 1),
        "vistas_mediana": round(vistas_med),
        "tasa_interaccion_mediana": round(tasa_med, 4),
        "componentes": {
            "interaccion": round(c_tasa, 2),
            "alcance": round(c_alcance, 2),
            "seguidores": round(c_seg, 2),
        },
    }


def _intervalos_dias(posts: list) -> list:
    fechas = []
    for p in posts:
        try:
            fechas.append(datetime.strptime(p["fecha"], "%Y-%m-%d %H:%M"))
        except (KeyError, ValueError, TypeError):
            continue
    fechas.sort()
    return [(b - a).total_seconds() / 86400 for a, b in zip(fechas, fechas[1:])]


def indice_veracidad(perfil: dict, posts: list):
    """
    Autenticidad aparente de la cuenta (no mide honestidad de la persona):
    Veracidad = 100 * (0.35 * cobertura + 0.25 * coherencia + 0.25 * regularidad + 0.15 * perfil).
    """
    usables = _con_vistas(posts)
    if len(usables) < MINIMO_PUBLICACIONES:
        return None
    seguidores = max((perfil or {}).get("seguidores", 0), 1)

    cobertura = _mediana([p["vistas"] for p in usables]) / seguidores
    c_cobertura = min(cobertura / COBERTURA_REFERENCIA, 1.0)

    tasa_likes = _mediana([p.get("likes", 0) / p["vistas"] for p in usables])
    bajo, alto = LIKES_RANGO_PLAUSIBLE
    if bajo <= tasa_likes <= alto:
        c_coherencia = 1.0
    elif tasa_likes < bajo:
        c_coherencia = tasa_likes / bajo
    else:
        c_coherencia = max(0.0, 1 - (tasa_likes - alto) / alto)

    intervalos = _intervalos_dias(posts)
    if len(intervalos) >= 3 and statistics.mean(intervalos) > 0:
        cv = statistics.pstdev(intervalos) / statistics.mean(intervalos)
        c_regularidad = 1 / (1 + cv)
    else:
        c_regularidad = 0.5  # neutro: faltan datos

    c_perfil = 1.0 if (perfil or {}).get("biografia") else 0.5

    veracidad = 100 * (0.35 * c_cobertura + 0.25 * c_coherencia + 0.25 * c_regularidad + 0.15 * c_perfil)
    return {
        "veracidad": round(veracidad, 1),
        "cobertura_vistas_seguidores": round(cobertura, 4),
        "likes_sobre_vistas_mediana": round(tasa_likes, 4),
        "componentes": {
            "cobertura": round(c_cobertura, 2),
            "coherencia": round(c_coherencia, 2),
            "regularidad": round(c_regularidad, 2),
            "perfil": round(c_perfil, 2),
        },
    }


# ---------------------------------------------------------------- flujo

def texto_de(datos: dict) -> str:
    if datos.get("corpus_texto"):
        return datos["corpus_texto"]
    partes = [(datos.get("perfil") or {}).get("biografia") or ""]
    partes += [p.get("descripcion") or "" for p in datos.get("publicaciones", [])]
    return "\n".join(t for t in partes if t.strip())


def analizar(datos: dict, lexico: dict) -> dict:
    perfil = datos.get("perfil") or {}
    posts = datos.get("publicaciones") or []
    big5 = puntuar_big_five(texto_de(datos), lexico)
    avisos = ["Estimación heurística y exploratoria; no es una evaluación psicológica."]
    if big5["palabras_analizadas"] < 100:
        avisos.append("Texto corto (menos de 100 palabras): los puntajes Big Five son poco fiables.")
    if len(posts) < 10:
        avisos.append(f"Solo {len(posts)} publicaciones disponibles.")
    valor = indice_valor(perfil, posts)
    veracidad = indice_veracidad(perfil, posts)
    if veracidad is None:
        avisos.append(f"Veracidad no calculada: se necesitan al menos {MINIMO_PUBLICACIONES} publicaciones con vistas.")
    return {
        "usuario": perfil.get("usuario"),
        "analizado_el": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "big_five": big5,
        "valor": valor,
        "veracidad": veracidad,
        "avisos": avisos,
    }


def expandir(patrones: list) -> list:
    if not patrones:
        patrones = ["datos/salida_*.json"]
    archivos = []
    for pat in patrones:
        archivos += sorted(glob.glob(pat)) or [pat]  # cmd de Windows no expande comodines
    return archivos


def main() -> None:
    ap = argparse.ArgumentParser(description="Análisis heurístico Big Five + valor + veracidad")
    ap.add_argument("archivos", nargs="*", help="salida_<usuario>.json (por defecto datos/salida_*.json)")
    ap.add_argument("--lexico", default=str(LEXICO_POR_DEFECTO), help="léxico JSON alternativo")
    args = ap.parse_args()

    lexico = cargar_lexico(args.lexico)
    archivos = expandir(args.archivos)
    CARPETA_RESULTADOS.mkdir(exist_ok=True)

    filas = []
    for ruta in archivos:
        try:
            datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[error] no se pudo leer {ruta}: {e}")
            continue
        res = analizar(datos, lexico)
        usuario = res["usuario"] or Path(ruta).stem.replace("salida_", "")
        (CARPETA_RESULTADOS / f"analisis_{usuario}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        b = res["big_five"]["rasgos"]
        fila = {
            "usuario": usuario,
            "valor": (res["valor"] or {}).get("valor", ""),
            "veracidad": (res["veracidad"] or {}).get("veracidad", ""),
            **{r: b[r]["puntaje"] for r in RASGOS},
            "palabras": res["big_five"]["palabras_analizadas"],
            "confianza_texto": res["big_five"]["confianza_texto"],
        }
        filas.append(fila)
        print(f"\n@{usuario}")
        print(f"  valor: {fila['valor']}   veracidad: {fila['veracidad']}   (confianza del texto: {fila['confianza_texto']})")
        print("  Big Five: " + "  ".join(f"{r[:4]}={b[r]['puntaje']}" for r in RASGOS))
        for r in RASGOS:
            if b[r]["palabras_alto"] or b[r]["palabras_bajo"]:
                print(f"    {r}: suben {b[r]['palabras_alto']}  bajan {b[r]['palabras_bajo']}")
        for aviso in res["avisos"][1:]:
            print(f"  [aviso] {aviso}")

    if not filas:
        sys.exit("No se analizó ningún archivo. Primero corre src/scraper.py.")

    with open(CARPETA_RESULTADOS / "resumen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nResultados en {CARPETA_RESULTADOS}/ (analisis_<usuario>.json y resumen.csv)")


if __name__ == "__main__":
    main()