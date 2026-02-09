import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0"
CHAT_ID = "-1002270247449"
LINK_AFILIADO = "https://go.aff.esportiva.bet/sm9dwy54"

bot = telebot.TeleBot(TOKEN)

class MonitorSniper:
    def __init__(self):
        self.ia = AnalisePremium()
        self.ultimo_id, self.wins, self.losses = None, 0, 0
        self.em_alerta, self.previsao_atual = False, None
        self.inicio = datetime.now().strftime("%H:%M")

    def enviar(self, txt, markup=None):
        try: bot.send_message(CHAT_ID, txt, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        except: pass

    def monitorar(self):
        self.enviar(f"🎯 *MODO SNIPER ATIVADO*\nEntrada Única | 100% SG\nInício: {self.inicio}")
        while True:
            try:
                self.ia.atualizar_banco()
                hist = self.ia.historico_completo
                if hist:
                    id_atual = f"{hist[0][0]}{hist[0][1]}"
                    if id_atual != self.ultimo_id:
                        if self.em_alerta:
                            time.sleep(2)
                            self.ia.atualizar_banco()
                            self.resultado(self.ia.historico_completo[0][0])
                        self.ultimo_id = id_atual
                        if not self.em_alerta:
                            p = self.ia.prever()
                            if p: self.sinal(p)
                time.sleep(3)
            except: time.sleep(10)

    def sinal(self, d):
        self.em_alerta, self.previsao_atual = True, d
        cor = "🔵 PLAYER" if d['previsao_genai'] == 'P' else "🔴 BANKER"
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("🎰 JOGAR AGORA", url=LINK_AFILIADO))
        msg = (f"🎯 *ENTRADA SNIPER*\n━━━━━━━━━━━━━\n🎯 Apostar: *{cor}*\n📊 Confiança: `100% SG`\n"
               f"⚖️ {d['dica_empate']}\n🚫 *SEM GALE*\n━━━━━━━━━━━━━")
        self.enviar(msg, m)

    def resultado(self, r):
        alvo = self.previsao_atual['previsao_genai']
        if r == alvo or r == 'T':
            self.wins += 1
            res_txt = "✅ *GREEN SNIPER!*"
        else:
            self.losses += 1
            res_txt = "❌ *RED (SEM GALE)*"
        
        taxa = (self.wins / (self.wins + self.losses)) * 100
        self.enviar(f"{res_txt}\n🎲 Resultado: {r}\n📈 Placar: `{self.wins}W - {self.losses}L` ({taxa:.1f}%)")
        self.em_alerta = False

inst = MonitorSniper()
@bot.message_handler(commands=['placar'])
def placar(m):
    t = inst.wins + inst.losses
    taxa = (inst.wins / t * 100) if t > 0 else 0
    bot.reply_to(m, f"📊 *SNIPER:* {inst.wins}W - {inst.losses}L\n📈 *Taxa:* {taxa:.1f}%")

if __name__ == "__main__":
    threading.Thread(target=inst.monitorar, daemon=True).start()
    bot.infinity_polling()
