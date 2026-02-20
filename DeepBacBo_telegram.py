import requests
import time
import telebot
import os
from datetime import datetime, timedelta
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES ---
TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0"
CHAT_ID = "-1002270247449"
LINK_AFILIADO = "https://go.aff.esportiva.bet/sm9dwy54"

bot = telebot.TeleBot(TOKEN)
ia = AnalisePremium()

class ContadorMensal:
    def __init__(self):
        self.arquivo = "placar_mensal.txt"
        self.wins = 0
        self.losses = 0
        self.data_reset = datetime.now()
        self.carregar()

    def carregar(self):
        if os.path.exists(self.arquivo):
            with open(self.arquivo, "r") as f:
                conteudo = f.read().split(",")
                if len(conteudo) == 3:
                    self.wins = int(conteudo[0])
                    self.losses = int(conteudo[1])
                    self.data_reset = datetime.strptime(conteudo[2], "%Y-%m-%d")
            
            # VERIFICA SE PASSARAM 30 DIAS
            if datetime.now() >= self.data_reset + timedelta(days=30):
                self.resetar()
        else:
            self.salvar()

    def salvar(self):
        with open(self.arquivo, "w") as f:
            f.write(f"{self.wins},{self.losses},{self.data_reset.strftime('%Y-%m-%d')}")

    def resetar(self):
        self.wins = 0
        self.losses = 0
        self.data_reset = datetime.now()
        self.salvar()

class MonitorSniper30Dias:
    def __init__(self):
        self.placar = ContadorMensal()
        self.ultimo_id = None
        self.em_alerta = False
        self.previsao_atual = None

    def enviar(self, txt, m=None):
        try: bot.send_message(CHAT_ID, txt, parse_mode="Markdown", reply_markup=m)
        except: pass

    def rodar(self):
        proximo_reset = (self.placar.data_reset + timedelta(days=30)).strftime("%d/%m/%y")
        self.enviar(f"💎 *SNIPER 30 DIAS ONLINE*\n📊 Placar acumulado até: {proximo_reset}")
        
        while True:
            try:
                ia.atualizar_banco()
                hist = ia.historico_completo
                if not hist: continue

                id_atual = f"{hist[0]}"
                if id_atual != self.ultimo_id:
                    if self.em_alerta:
                        self.verificar_resultado(hist[0])
                    
                    self.ultimo_id = id_atual
                    if not self.em_alerta:
                        p = ia.prever()
                        if p: self.disparar_sinal(p)
                time.sleep(3)
            except: time.sleep(10)

    def disparar_sinal(self, d):
        self.em_alerta = True
        self.previsao_atual = d
        cor = "🔵 PLAYER" if d['cor'] == 'P' else "🔴 BANKER"
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("🎰 ENTRAR NO JOGO", url=LINK_AFILIADO))
        
        msg = (f"🎯 *SINAL SNIPER CONFIRMADO*\n━━━━━━━━━━━━━━━━━━━━\n"
               f"🎰 Apostar: *{cor}*\n📊 Confiança: `{d['prob']}%`\n"
               f"🚫 *ENTRADA ÚNICA (SEM GALE)*\n━━━━━━━━━━━━━━━━━━━━")
        self.enviar(msg, m)

    def verificar_resultado(self, res):
        alvo = self.previsao_atual['cor']
        if res == alvo or res == 'T':
            self.placar.wins += 1
            res_txt = "✅ *GREEN SNIPER!*"
        else:
            self.placar.losses += 1
            res_txt = "❌ *RED*"
        
        self.placar.salvar()
        total = self.placar.wins + self.placar.losses
        taxa = (self.placar.wins / total) * 100
        
        msg = (f"{res_txt}\n\n📊 *RANKING MENSAL:* `{self.placar.wins}W - {self.placar.losses}L`\n"
               f"📈 *TAXA 30 DIAS:* `{taxa:.1f}%`")
        self.enviar(msg)
        self.em_alerta = False

if __name__ == "__main__":
    MonitorSniper30Dias().rodar()
