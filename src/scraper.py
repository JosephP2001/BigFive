
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
RE_REHYDRATION = re.compile(
    r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    re.S,
)
RE_USUARIO = re.compile(r"^[A-Za-z0-9._]{2,24}$")
CARPETA_MUESTRAS = Path("muestras")
PERFIL_NAVEGADOR = Path(".perfil_navegador")  # sesión anónima del navegador
CARPETA_MEDIA = Path("media")  # solo se usa con --media
CARPETA_DATOS = Path("datos")  # salida_<usuario>.json

# Definición de "interacciones" usada en este trabajo:
# likes + comentarios + compartidos (guardados y vistas se reportan aparte).


# ---------------------------------------------------------------- utilidades

def limpiar_usuario(texto: str) -> str:
    return texto.strip().lstrip("@").strip("/")


def a_entero(valor) -> int:
    """TikTok a veces entrega los contadores como texto; los pasamos a int."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def a_fecha(ts) -> str:
    ts = a_entero(ts)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""


def guardar_muestra(nombre: str, contenido) -> None:
    CARPETA_MUESTRAS.mkdir(exist_ok=True)
    ruta = CARPETA_MUESTRAS / nombre
    if isinstance(contenido, str):
        ruta.write_text(contenido, encoding="utf-8")
    else:
        ruta.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"  [debug] guardado {ruta}")


# ---------------------------------------------------------------- paso 1: perfil

def descargar_html(usuario: str) -> str:
    resp = requests.get(
        f"https://www.tiktok.com/@{usuario}",
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text


def extraer_estado(html: str):
    """Devuelve el JSON incrustado en la página, o None si no se encuentra."""
    m = RE_REHYDRATION.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def extraer_perfil(estado: dict):
    """Saca seguidores, seguidos, etc. del JSON de la página."""
    scope = (estado or {}).get("__DEFAULT_SCOPE__", {})
    info = scope.get("webapp.user-detail", {}).get("userInfo")
    if not info:
        return None
    user = info.get("user", {})
    # statsV2 trae las cifras exactas (como texto); stats viene redondeado
    stats = info.get("statsV2") or info.get("stats", {})
    return {
        "usuario": user.get("uniqueId"),
        "nombre": user.get("nickname"),
        "verificado": user.get("verified"),
        "privada": user.get("privateAccount"),
        "biografia": user.get("signature") or "",
        "enlace_bio": (user.get("bioLink") or {}).get("link"),
        "idioma": user.get("language"),
        "region": user.get("region"),
        "cuenta_creada": a_fecha(user.get("createTime")),
        "seguidores": a_entero(stats.get("followerCount")),
        "siguiendo": a_entero(stats.get("followingCount")),
        "likes_totales": a_entero(stats.get("heartCount")),
        "videos": a_entero(stats.get("videoCount")),
    }


# ---------------------------------------------------------------- paso 2: posts

def extraer_medios(item: dict) -> dict:
    """Enlaces de video, portada e imágenes. Están firmados: caducan en horas."""
    video = item.get("video") or {}
    medios = {"video": None, "portada": video.get("cover") or None, "imagenes": []}
    if item.get("imagePost"):
        for img in (item["imagePost"].get("images") or []):
            lista = (img.get("imageURL") or {}).get("urlList") or []
            if lista:
                medios["imagenes"].append(lista[0])
    else:
        medios["video"] = video.get("playAddr") or video.get("downloadAddr") or None
    return medios


def normalizar_post(item: dict, usuario: str) -> dict:
    s = item.get("statsV2") or item.get("stats") or {}
    likes = a_entero(s.get("diggCount"))
    comentarios = a_entero(s.get("commentCount"))
    compartidos = a_entero(s.get("shareCount"))
    ts = a_entero(item.get("createTime"))
    es_imagen = bool(item.get("imagePost"))  # carrusel de fotos
    ruta = "photo" if es_imagen else "video"
    desc = item.get("desc") or ""
    hashtags = [t.get("hashtagName") for t in (item.get("textExtra") or []) if t.get("hashtagName")]
    if not hashtags:
        hashtags = re.findall(r"#(\w+)", desc)
    return {
        "id": item.get("id"),
        "tipo": "imagen" if es_imagen else "video",
        "url": f"https://www.tiktok.com/@{usuario}/{ruta}/{item.get('id')}",
        "fecha": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
        "_ts": ts,
        "descripcion": desc,
        "hashtags": hashtags,
        "musica": (item.get("music") or {}).get("title"),
        "duracion_seg": a_entero((item.get("video") or {}).get("duration")) or None,
        "fijado": bool(item.get("isPinnedItem")),
        "vistas": a_entero(s.get("playCount")),
        "likes": likes,
        "comentarios": comentarios,
        "compartidos": compartidos,
        "guardados": a_entero(s.get("collectCount")),
        "interacciones": likes + comentarios + compartidos,
        "medios": extraer_medios(item),
    }


def armar_posts(respuestas: list, usuario: str) -> list:
    """Junta las respuestas de item_list sin duplicados, de la más nueva a la más antigua."""
    vistos, posts = set(), []
    for r in respuestas:
        for it in r.get("itemList") or []:
            if it.get("id") in vistos:
                continue
            vistos.add(it.get("id"))
            posts.append(normalizar_post(it, usuario))
    posts.sort(key=lambda x: x["_ts"], reverse=True)
    return posts


def descargar_medios(contexto, posts: list, usuario: str) -> dict:
    """
    Descarga video o imágenes de cada publicación usando la sesión del propio
    navegador (cookies) y el encabezado Referer. Devuelve {id: [rutas]}.
    """
    carpeta = CARPETA_MEDIA / usuario
    carpeta.mkdir(parents=True, exist_ok=True)
    cabeceras = {"Referer": "https://www.tiktok.com/", "User-Agent": USER_AGENT}
    resultado = {}
    for p in posts:
        medios = p.get("medios") or {}
        pendientes = []
        if medios.get("video"):
            pendientes.append((f"{p['id']}", medios["video"], ".mp4"))
        else:
            for i, u in enumerate(medios.get("imagenes") or [], 1):
                pendientes.append((f"{p['id']}_{i}", u, ".jpg"))
        guardados = []
        for base, url, ext_defecto in pendientes:
            try:
                r = contexto.request.get(url, headers=cabeceras, timeout=60000)
                if not r.ok:
                    print(f"  [media] {base}: HTTP {r.status}")
                    continue
                tipo = (r.headers.get("content-type") or "").lower()
                ext = ".webp" if "webp" in tipo else ".png" if "png" in tipo else ext_defecto
                ruta = carpeta / f"{base}{ext}"
                ruta.write_bytes(r.body())
                guardados.append(str(ruta))
            except Exception as e:
                print(f"  [media] {base}: {e}")
        resultado[p["id"]] = guardados
    return resultado


def hay_captcha(pagina) -> bool:
    """Detecta un captcha visible en la página (no solo la palabra en el código)."""
    try:
        return pagina.locator('[id*="captcha" i], [class*="captcha" i]').count() > 0
    except Exception:
        return False


def obtener_posts(usuario: str, cantidad: int, visible: bool, debug: bool, espera: int, descargar: bool = False):
    """
    Abre el perfil en Chromium y captura la respuesta de /api/post/item_list.
    Si aparece un captcha, espera (hasta `espera` segundos) a que lo resuelvas
    tú a mano en la ventana. La sesión se guarda en .perfil_navegador/ para que
    no vuelva a pedirlo en cada ejecución.
    Devuelve (lista_de_posts, html_de_la_pagina).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "Falta Playwright. Instala con:\n"
            "  pip install playwright\n  playwright install chromium"
        )

    respuestas = []

    def al_responder(resp):
        if "/api/post/item_list" in resp.url:
            try:
                respuestas.append(resp.json())
            except Exception:
                pass  # respuesta vacía o no JSON: la ignoramos

    def contar_items() -> int:
        ids = set()
        for r in respuestas:
            for it in r.get("itemList") or []:
                ids.add(it.get("id"))
        return len(ids)

    enlaces = []
    captcha_visto = False
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            str(PERFIL_NAVEGADOR),
            headless=not visible,
            user_agent=USER_AGENT,
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )
        pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
        pagina.on("response", al_responder)
        pagina.goto(
            f"https://www.tiktok.com/@{usuario}",
            wait_until="domcontentloaded",
            timeout=45000,
        )

        # esperar publicaciones; en modo oculto no tiene sentido esperar un captcha
        limite = espera if visible else min(espera, 20)
        transcurrido, avisado, recargado = 0, False, False
        while transcurrido < limite and contar_items() == 0:
            pagina.wait_for_timeout(2000)
            transcurrido += 2
            if hay_captcha(pagina):
                captcha_visto = True
                if not avisado:
                    avisado = True
                    if visible:
                        print(f"  [captcha] resuélvelo en la ventana; espero hasta {limite} s ...")
                    else:
                        print("  [captcha] detectado; vuelve a correr con --visible para resolverlo.")
            elif captcha_visto and not recargado:
                # el captcha desapareció y aún no hay datos: recargar una vez
                recargado = True
                try:
                    pagina.reload(wait_until="domcontentloaded", timeout=45000)
                except Exception:
                    pass

        # bajar un poco si todavía faltan publicaciones
        for _ in range(6):
            if contar_items() == 0 or contar_items() >= cantidad:
                break
            pagina.mouse.wheel(0, 3000)
            pagina.wait_for_timeout(1800)

        archivos = {}
        if descargar and contar_items() > 0:
            print("Descargando medios ...")
            archivos = descargar_medios(contexto, armar_posts(respuestas, usuario)[:cantidad], usuario)

        html = pagina.content()
        if contar_items() == 0:
            enlaces = pagina.eval_on_selector_all(
                'a[href*="/video/"]', "els => els.map(e => e.href)"
            )
        contexto.close()

    if debug:
        for i, r in enumerate(respuestas, 1):
            guardar_muestra(f"{usuario}_item_list_{i}.json", r)

    posts = armar_posts(respuestas, usuario)
    for p in posts:
        if p["id"] in archivos:
            p["archivos"] = archivos[p["id"]]

    if not posts:
        if captcha_visto:
            print("  [aviso] el captcha impidió obtener publicaciones.")
        if enlaces:
            print("  [aviso] no se capturó item_list; solo se obtuvieron enlaces de videos.")
            unicos = list(dict.fromkeys(enlaces))[:cantidad]
            posts = [{"id": u.rstrip("/").split("/")[-1], "url": u} for u in unicos]
        return posts, html

    return posts[:cantidad], html


# ---------------------------------------------------------------- salida

def mostrar(perfil: dict, posts: list) -> None:
    print("\n=== PERFIL ===")
    if perfil:
        print(f"Usuario:     @{perfil['usuario']}  ({perfil['nombre']})")
        print(f"Seguidores:  {perfil['seguidores']:,}")
        print(f"Siguiendo:   {perfil['siguiendo']:,}")
        print(f"Videos:      {perfil['videos']:,}")
        print(f"Likes tot.:  {perfil['likes_totales']:,}")
        print(f"Bio:         {perfil['biografia'] or '(vacía)'}")
    else:
        print("No se pudo leer el perfil (revisa muestras/ con --debug).")

    print(f"\n=== ÚLTIMAS {len(posts)} PUBLICACIONES ===")
    if not posts:
        print("No se obtuvieron publicaciones.")
        return
    if "likes" not in posts[0]:
        for i, p in enumerate(posts, 1):
            print(f"{i:>2}. {p['url']}")
        return
    print(f"{'#':>2}  {'tipo':<6} {'fecha':<16} {'vistas':>10} {'likes':>9} {'coment.':>8} "
          f"{'compart.':>8} {'guard.':>8} {'interac.':>9}")
    for i, p in enumerate(posts, 1):
        print(f"{i:>2}  {p['tipo']:<6} {p['fecha']:<16} {p['vistas']:>10,} {p['likes']:>9,} "
              f"{p['comentarios']:>8,} {p['compartidos']:>8,} "
              f"{p['guardados']:>8,} {p['interacciones']:>9,}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Scraper académico de perfiles públicos de TikTok")
    ap.add_argument("usuario", nargs="?", help="usuario de TikTok (sin @)")
    ap.add_argument("-n", "--cantidad", type=int, default=10, help="publicaciones a traer (por defecto 10)")
    ap.add_argument("--visible", action="store_true", help="mostrar la ventana del navegador")
    ap.add_argument("--espera", type=int, default=120,
                    help="segundos a esperar (con --visible) para resolver un captcha a mano; por defecto 120")
    ap.add_argument("--media", action="store_true", help="descargar videos/imágenes a media/<usuario>/")
    ap.add_argument("--debug", action="store_true", help="guardar las respuestas crudas en muestras/")
    args = ap.parse_args()

    usuario = limpiar_usuario(args.usuario or input("Usuario de TikTok a analizar (sin @): "))
    if not RE_USUARIO.match(usuario):
        sys.exit("Usuario inválido: usa solo letras, números, punto y guion bajo.")

    # paso 1: perfil con requests
    perfil = None
    print(f"Leyendo perfil de @{usuario} ...")
    try:
        html = descargar_html(usuario)
        estado = extraer_estado(html)
        if args.debug and estado:
            guardar_muestra(f"{usuario}_estado.json", estado)
        perfil = extraer_perfil(estado) if estado else None
    except requests.RequestException as e:
        print(f"  [aviso] fallo con requests ({e}); se intentará con el navegador.")

    # paso 2: publicaciones con navegador (y respaldo para el perfil)
    print("Abriendo navegador para capturar publicaciones ...")
    posts, html_pw = obtener_posts(usuario, args.cantidad, args.visible, args.debug, args.espera, args.media)
    if perfil is None and html_pw:
        estado = extraer_estado(html_pw)
        perfil = extraer_perfil(estado) if estado else None

    mostrar(perfil, posts)

    CARPETA_DATOS.mkdir(exist_ok=True)
    salida = CARPETA_DATOS / f"salida_{usuario}.json"
    limpios = [{k: v for k, v in p.items() if not k.startswith("_")} for p in posts]
    # texto listo para análisis posterior: biografía + descripciones + hashtags
    partes = [perfil["biografia"]] if perfil and perfil.get("biografia") else []
    for p in limpios:
        partes.append(p.get("descripcion") or "")
    corpus = "\n".join(t for t in partes if t.strip())
    salida.write_text(
        json.dumps({"perfil": perfil, "publicaciones": limpios, "corpus_texto": corpus}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nResultado guardado en {salida}")


if __name__ == "__main__":
    main()
