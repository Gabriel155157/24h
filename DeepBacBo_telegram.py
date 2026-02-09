import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES ---
TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0"
CHAT_ID = "-1002270247449"
LINK = "https://go.aff.esportiva.bet/sm9dwy54"

bot = telebot.TeleBot(TOKEN)

class IASniper:
    def __init__(self):
        self.ia = AnalisePremium()
        self.ultimo_id, self.wins, self.losses = None, 0, 0
        self.em_alerta, self.previsao_atual = False, None

    def enviar(self, txt, m=None):
        try: bot.send_message(CHAT_ID, txt, parse_mode="Markdown", reply_markup=m, disable_web_page_preview=True)
        except: pass

    def monitorar(self):
        self.enviar("💎 *IA DATA ANALYST ATIVADA*\n_Monitorando probabilidades sniper 24h..._")
        while True:
            try:
                self.ia.atualizar_banco()
                hist = self.ia.ia_historico = self.ia.historico_completo
                if hist:
                    # Gera ID único baseado nas duas últimas pedras para evitar duplicidade
                    id_atual = "".join(hist[:2]) 
                    if id_atual != self.ultimo_id:
                        if self.em_alerta:
                            time.sleep(4) # Espera o mercado atualizar
                            self.ia.atualizar_banco()
                            self.validar(self.ia.historico_completo[0])
                        
                        self.ultimo_id = id_atual
                        if not self.em_alerta:
                            p = self.ia.prever()
                            if p: self.disparar(p)
                time.sleep(3)
            except: time.sleep(10)

    def disparar(self, d):
        self.em_alerta, self.previsao_atual = True, d
        cor_txt = "🔵 PLAYER" if d['cor'] == 'P' else "🔴 BANKER"
        
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("🎰 ENTRAR NO JOGO", url=LINK))
        
        msg = (
            f"🎯 *ENTRADA SNIPER CONFIRMADA*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 Apostar: *{cor_txt}*\n"
            f"📊 Probabilidade: `{d['prob']}%` ({d['amostra']}x)\n"
            f"⚖️ Proteção: *CUBRA EMPATE ({d['empate']}%)*\n"
            f"🚫 Estratégia: *ENTRADA ÚNICA (SEM GALE)*\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        self.enviar(msg, m)

    def validar(self, res):
        alvo = self.previsao_atual['cor']
        if res == alvo or res == 'T':
            self.wins += 1
            status = "✅ *GREEN SNIPER!* 🎯"
        else:
            self.losses += 1
            status = "❌ *RED (SEM GALE)*"
        
        taxa = (self.wins / (self.wins + self.losses)) * 100
        msg = (f"{status}\n\n🎲 Resultado: *{res}*\n"
               f"📈 Placar: `{self.wins}W - {self.losses}L` | `{taxa:.1f}%` Accuracy")
        self.enviar(msg)
        self.em_alerta = False

bot_sniper = IASniper()

@bot.message_handler(commands=['placar'])
def cmd_placar(m):
    t = bot_sniper.wins + bot_sniper.losses
    tx = (bot_sniper.wins / t * 100) if t > 0 else 0
    bot.reply_to(m, f"📊 *ESTATÍSTICAS SNIPER*\n✅ Wins: {bot_sniper.wins}\n❌ Reds: {bot_sniper.losses}\n📈 Taxa: {tx:.1f}%")

if __name__ == "__main__":
    threading.Thread(target=bot_sniper.monitorar, daemon=True).start()
    bot.infinity_polling()
