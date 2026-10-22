# TikTok Big Five (heurístico)

Proyecto académico en dos pasos:

1. **Extraer** de un perfil público de TikTok: seguidores, seguidos, biografía, las últimas publicaciones (descripción, hashtags, interacciones, enlaces de medios) y, opcionalmente, los videos e imágenes.
2. **Analizar** con un método heurístico y transparente: estimación Big Five a partir del texto, más un índice de *valor* (alcance e influencia) y uno de *veracidad* (autenticidad aparente de la cuenta).

Restricciones de origen: sin extensiones de navegador, sin APIs existentes, sin credenciales propias. El único dato de entrada es el usuario de la cuenta.

> Los resultados son estimaciones exploratorias con fórmulas abiertas. No son una evaluación psicológica ni una prueba de que una cuenta sea falsa. Ver `docs/metodologia.md`.

## Estructura

```
tiktok-bigfive/
├── README.md
├── RUNBOOK.md            procedimiento de instalación, operación y solución de problemas
├── requirements.txt
├── .gitignore
├── src/
│   ├── scraper.py        extracción (requests + Playwright)
│   ├── analisis.py       Big Five, valor y veracidad (solo biblioteca estándar)
│   └── lexico_es.json    diccionario editable para el Big Five
├── tests/
│   └── test_analisis.py
└── docs/
    └── metodologia.md    fórmulas, parámetros y limitaciones
```

Las carpetas `datos/`, `muestras/`, `media/`, `resultados/` y `.perfil_navegador/` se crean al ejecutar y están en el `.gitignore`: pueden contener información de terceros o cookies.

## Inicio rápido (Windows, cmd)

```bat
git clone <URL-del-repositorio>
cd tiktok-bigfive
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

python src\scraper.py nombre_usuario --visible
python src\analisis.py
```

Si aparece un captcha, se resuelve a mano en la ventana. El detalle completo, con verificaciones y solución de problemas, está en `RUNBOOK.md`.
