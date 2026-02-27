import atexit
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver


if getattr(sys, "frozen", False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))


app = Flask(__name__)

USUARIO_ESPORTIVA = os.environ.get("USUARIO_ESPORTIVA", "SEU_EMAIL_AQUI@gmail.com")
SENHA_ESPORTIVA = os.environ.get("SENHA_ESPORTIVA", "SUA_SENHA_AQUI")

ARQUIVO_MEMORIA = os.path.join(APPLICATION_PATH, "memoria_bacbo.json")
ARQUIVO_CREDENCIAIS = os.path.join(APPLICATION_PATH, "credenciais_esportiva.txt")
LIMITE_HISTORICO = 10000

historico_global = []
historico_lock = threading.Lock()
estado = {
    "inicio": datetime.now(timezone.utc).isoformat(),
    "ultima_atualizacao": None,
    "ultimo_erro": None,
    "falhas_consecutivas": 0,
}
stop_event = threading.Event()


def _salvar_json_atomico(path, dados):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    os.replace(tmp, path)


def carregar_memoria():
    global historico_global
    if not os.path.exists(ARQUIVO_MEMORIA):
        return

    try:
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            with historico_lock:
                historico_global = dados[:LIMITE_HISTORICO]
            print(f"🧠 Memória restaurada: {len(historico_global)} rodadas.")
    except Exception as exc:
        print(f"⚠️ Falha ao carregar memória: {exc}")


def salvar_memoria():
    with historico_lock:
        _salvar_json_atomico(ARQUIVO_MEMORIA, historico_global)


def atualizar_memoria(nova_leitura_invertida):
    global historico_global

    with historico_lock:
        if not historico_global:
            historico_global = nova_leitura_invertida[:LIMITE_HISTORICO]
            _salvar_json_atomico(ARQUIVO_MEMORIA, historico_global)
            return

        assinatura = historico_global[:8]
        novas_bolinhas = []
        achou_conexao = False

        for i in range(len(nova_leitura_invertida)):
            if nova_leitura_invertida[i:i + 8] == assinatura:
                novas_bolinhas = nova_leitura_invertida[:i]
                achou_conexao = True
                break

        if achou_conexao and novas_bolinhas:
            historico_global = novas_bolinhas + historico_global
        elif not achou_conexao:
            historico_global = nova_leitura_invertida

        historico_global = historico_global[:LIMITE_HISTORICO]
        _salvar_json_atomico(ARQUIVO_MEMORIA, historico_global)


def carregar_credenciais():
    usuario = USUARIO_ESPORTIVA
    senha = SENHA_ESPORTIVA

    if os.path.exists(ARQUIVO_CREDENCIAIS):
        with open(ARQUIVO_CREDENCIAIS, "r", encoding="utf-8") as f:
            linhas = f.read().splitlines()
        if len(linhas) >= 2:
            usuario = linhas[0].strip()
            senha = linhas[1].strip()
            print("✅ Credenciais lidas de arquivo.")

    return usuario, senha


def forcar_clique(driver, texto_botao):
    xpath = (
        "//*[(local-name()='button' or local-name()='a' or local-name()='span' or local-name()='div') "
        f"and contains(translate(., '{texto_botao.upper()}', '{texto_botao.lower()}'), '{texto_botao.lower()}')]"
    )
    elementos = driver.find_elements(By.XPATH, xpath)
    for el in reversed(elementos):
        if el.is_displayed():
            try:
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                continue
    return False


def login_esportiva_bet(driver):
    usuario, senha = carregar_credenciais()
    driver.set_window_size(1920, 1080)
    driver.get("https://esportiva.bet.br/")

    try:
        driver.delete_all_cookies()
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
    except Exception:
        pass

    time.sleep(5)

    for texto in ["ACEITAR TODOS", "ACEITAR", "ESCURO", "CLARO", "SALVAR", "CONFIRMAR", "SIM", "SIM"]:
        forcar_clique(driver, texto)
        time.sleep(0.7)

    abriu_login = forcar_clique(driver, "FAZER LOGIN") or forcar_clique(driver, "ENTRAR")
    if not abriu_login:
        raise RuntimeError("Botão de login não encontrado")

    input_user = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//input[@id='login' or @name='login' or @type='login']"))
    )
    input_user.clear()
    input_user.send_keys(usuario)

    input_pass = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @id='password' or @name='password']"))
    )
    input_pass.clear()
    input_pass.send_keys(senha)

    try:
        btn_entrar = driver.find_element(
            By.XPATH,
            "//button[@type='submit' and contains(translate(., 'ENTRAR', 'entrar'), 'entrar')]",
        )
        driver.execute_script("arguments[0].removeAttribute('disabled');", btn_entrar)
        driver.execute_script("arguments[0].click();", btn_entrar)
    except Exception:
        input_pass.send_keys(Keys.ENTER)

    for _ in range(15):
        time.sleep(1)
        pass_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
        if not pass_fields or not pass_fields[0].is_displayed():
            return

    raise RuntimeError("Login não foi confirmado")


def extrair_historico(driver):
    driver.switch_to.default_content()

    iframe_1 = driver.find_element(By.ID, "gameIframe")
    driver.switch_to.frame(iframe_1)
    game_container = driver.find_element(By.XPATH, "/html/body/game-container")
    shadow_root = driver.execute_script("return arguments[0].shadowRoot", game_container)
    iframe_2 = shadow_root.find_element(By.CSS_SELECTOR, "iframe")
    driver.switch_to.frame(iframe_2)
    iframe_3 = driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/iframe")
    driver.switch_to.frame(iframe_3)

    caixa_historico = driver.find_element(By.XPATH, "/html/body/div[4]/div/div/div[2]/div[6]/div/div[1]/div/div/div")

    script_extrator = """
    var caixa = arguments[0];
    var svgs = caixa.querySelectorAll('svg[data-type="roadItem"]');
    var dados = [];
    var achou_numero = false;

    for (var i=0; i<svgs.length; i++) {
        var svg = svgs[i];
        var textEl = svg.querySelector('text');
        if (!textEl) continue;
        var txt = textEl.textContent.trim();
        var num = parseInt(txt, 10);
        if (isNaN(num) || num < 2 || num > 12) continue;

        achou_numero = true;
        var cor = 'T';
        var nome = (svg.getAttribute('name') || '').toLowerCase();
        if (nome === 'player') cor = 'P';
        else if (nome === 'banker') cor = 'B';
        else if (nome === 'tie') cor = 'T';

        dados.push({
            pedra: cor === 'P' ? 'Player' : cor === 'B' ? 'Banker' : 'Tie',
            numero: num
        });
    }

    return {dados: dados, has_numbers: achou_numero};
    """

    return driver.execute_script(script_extrator, caixa_historico), caixa_historico


def motor_raspagem_24h():
    carregar_memoria()
    backoff = 10

    while not stop_event.is_set():
        driver = None
        try:
            driver = Driver(uc=True, headless2=True)
            login_esportiva_bet(driver)
            driver.get(
                "https://esportiva.bet.br/games/evolution/bac-bo?src=ltdpeqcvodvdbektdymjmebekd&utm_source=522592"
            )
            time.sleep(10)

            falhas_consecutivas = 0
            ciclo_inicio = time.time()

            while not stop_event.is_set():
                try:
                    resultado_js, caixa_historico = extrair_historico(driver)

                    if not resultado_js["has_numbers"]:
                        falhas_consecutivas += 1
                        try:
                            ActionChains(driver).move_to_element(caixa_historico).click().pause(0.5).click().perform()
                        except Exception:
                            driver.execute_script(
                                "var ev = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});"
                                "arguments[0].dispatchEvent(ev);",
                                caixa_historico,
                            )
                        if falhas_consecutivas >= 15:
                            driver.refresh()
                            time.sleep(15)
                            falhas_consecutivas = 0
                    else:
                        dados_invertidos = resultado_js["dados"][::-1]
                        atualizar_memoria(dados_invertidos)
                        estado["ultima_atualizacao"] = datetime.now(timezone.utc).isoformat()
                        estado["falhas_consecutivas"] = 0
                        falhas_consecutivas = 0

                    if time.time() - ciclo_inicio > 60 * 60:
                        raise RuntimeError("Reciclando driver após 1h para manter estabilidade")

                except Exception as exc:
                    falhas_consecutivas += 1
                    estado["falhas_consecutivas"] = falhas_consecutivas
                    estado["ultimo_erro"] = str(exc)
                    if falhas_consecutivas > 20:
                        raise

                time.sleep(1)

            backoff = 10

        except Exception as exc:
            estado["ultimo_erro"] = str(exc)
            print(f"⚠️ Motor reiniciando em {backoff}s. Motivo: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass


def shutdown_handler(*_):
    stop_event.set()


@app.route("/api_bacbo", methods=["GET"])
def get_api_bacbo():
    with historico_lock:
        dados = list(historico_global)
    return jsonify(dados)


@app.route("/", methods=["GET"])
def health_check():
    with historico_lock:
        total = len(historico_global)
    return jsonify(
        {
            "status": "online",
            "rodadas_acumuladas": total,
            "ultima_atualizacao": estado["ultima_atualizacao"],
            "falhas_consecutivas": estado["falhas_consecutivas"],
            "ultimo_erro": estado["ultimo_erro"],
        }
    )


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    atexit.register(stop_event.set)

    thread_raspagem = threading.Thread(target=motor_raspagem_24h, daemon=True)
    thread_raspagem.start()

    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
