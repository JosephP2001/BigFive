import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import analisis as a
from ia import RASGOS, ClienteOllama, ErrorIA, estimar_big_five


def main():
    ap = argparse.ArgumentParser(description="Estimación Big Five con una IA local (Ollama)")
    ap.add_argument("archivos", nargs="*", help="salida_<usuario>.json (por defecto datos/salida_*.json)")
    ap.add_argument("--modelo", help="modelo de Ollama (por defecto el de .env o llama3.2)")
    args = ap.parse_args()

    cliente = ClienteOllama(modelo=args.modelo)
    lexico = a.cargar_lexico(a.LEXICO_POR_DEFECTO)
    a.CARPETA_RESULTADOS.mkdir(exist_ok=True)

    for ruta in a.expandir(args.archivos):
        try:
            datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[error] no se pudo leer {ruta}: {e}")
            continue
        usuario = (datos.get("perfil") or {}).get("usuario") or Path(ruta).stem.replace("salida_", "")
        texto = a.texto_de(datos)
        base = a.puntuar_big_five(texto, lexico)

        print(f"\n@{usuario}  (modelo: {cliente.modelo})")
        try:
            ia = estimar_big_five(texto, cliente)
        except ErrorIA as e:
            sys.exit(f"[error] {e}")

        salida = {
            "usuario": usuario,
            "estimado_el": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ia": ia,
            "linea_base_lexico": {r: base["rasgos"][r]["puntaje"] for r in RASGOS},
            "aviso": "Estimación exploratoria hecha por un modelo de lenguaje; no es una evaluación psicológica.",
        }
        (a.CARPETA_RESULTADOS / f"ia_{usuario}.json").write_text(
            json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if "omitido" in ia:
            print(f"  {ia['omitido']}")
            continue
        for r in RASGOS:
            x = ia["rasgos"][r]
            valor = f"{x['puntaje']} ({x['confianza']})" if x["determinable"] else "no determinable"
            print(f"  {r:<16} léxico={base['rasgos'][r]['puntaje']:>5}   IA={valor}")
            for cita in x["evidencia"]:
                print(f"      evidencia: \"{cita}\"")

    print(f"\nResultados en {a.CARPETA_RESULTADOS}/ (ia_<usuario>.json)")


if __name__ == "__main__":
    main()
