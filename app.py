# app.py na RAIZ do repositório
import os, sys

# garante que a subpasta 'ifood_restaurant_suite_v2' esteja no path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.join(BASE_DIR, "ifood_restaurant_suite_v2")
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

# importa e executa o app real que está na subpasta
# (o arquivo original fica em ifood_restaurant_suite_v2/app.py)
import app as inner_app  # noqa: F401  -> apenas importar já roda o Streamlit
