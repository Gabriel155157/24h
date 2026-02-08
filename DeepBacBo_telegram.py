import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES ---
TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0"
CHAT_ID = "-1002270247449"
LINK_AFILIADO = "https://go.aff.esportiva.bet/sm9dwy54"

bot = telebot.TeleBot(TOKEN)

class MonitorBacbo:
    def __init__(self):
        self.ia = AnalisePremium()
        self.ultimo_id = None
        self.wins, self.losses, self.sg, self.g1 = 0, 0, 0, 0
        self.em_alerta = False
        self.previsao_atual = None
        self.gale_ativo = False
        self.inicio_sessao = datetime.now().strftime("%d/%m %H:%M")

    def enviar_msg(self, texto, markup=None):
        try: bot.send_message(CHAT_ID, texto, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        except: pass

    def monitorar(self):
        self.enviar_msg(f"✅ *DeepBacbo IA ONLINE*\nSessão: {self.inicio_sessao}\nMonitorando 24h...")
        
        while True:
            try:
                self.ia.atualizar_banco()
                hist = self.ia.historico_completo
                if not hist: 
                    time.sleep(5)
                    continue

                id_atual = f"{hist[0][0]}{hist[0][1]}"

                if id_atual != self.ultimo_id:
                    if self.em_alerta:
                        # Pequeno delay para a API estabilizar a cor real
                        time.sleep(2)
                        self.ia.atualizar_banco()
                        self.processar_resultado(self.ia.historico_completo[0][0])
                    
                    self.ultimo_id = id_atual
                    if not self.em_alerta:
                        previsao = self.ia.prever()
                        if previsao: self.enviar_sinal(previsao)

                time.sleep(3)
            except Exception as e:
                time.sleep(10)

    def enviar_sinal(self, dados):
        self.em_alerta = True
        self.previsao_atual = dados
        cor = "🔵 AZUL" if dados['previsao_genai'] == 'P' else "🔴 VERMELHO"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🎰 JOGAR NA ESPORTIVA BET", url=LINK_AFILIADO))
        
        msg = (
            f"⚡ *ENTRADA CONFIRMADA* ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Apostar em: *{cor}*\n"
            f"📊 Confiança: `{dados['probabilidade_genai']}%`\n"
            f"⚖️ {dados['dica_empate']}\n"
            f"🔄 Proteção: *Até G1*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Aguarde o resultado...*"
        )
        self.enviar_msg(msg, markup)

    def processar_resultado(self, resultado):
        alvo = self.previsao_atual['previsao_genai']
        
        if resultado == alvo or resultado == 'T':
            if self.gale_ativo: self.g1 += 1
            else: self.sg += 1
            self.wins += 1
            self.finalizar_ciclo(f"✅ *GREEN! {'G1' if self.gale_ativo else 'DE PRIMEIRA'}*", resultado)
        elif not self.gale_ativo:
            self.gale_ativo = True
            self.enviar_msg("🔄 *Entrando no GALE 1...*")
        else:
            self.losses += 1
            self.finalizar_ciclo("❌ *RED CONFIRMADO*", resultado)

    def finalizar_ciclo(self, status, pedra):
        # Tradução real para o placar
        nomes = {'P': 'Azul', 'B': 'Vermelho', 'T': 'Empate'}
        pedra_txt = nomes.get(pedra, "Desconhecido")
        
        total = self.wins + self.losses
        taxa = (self.wins / total * 100) if total > 0 else 0
        
        msg = (
            f"{status}\n"
            f"🎲 Resultado: *{pedra_txt}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Wins: `{self.wins}` (SG:{self.sg} | G1:{self.g1})\n"
            f"❌ Reds: `{self.losses}`\n"
            f"📈 Assertividade: `{taxa:.1f}%`"
        )
        self.enviar_msg(msg)
        self.em_alerta, self.gale_ativo, self.previsao_atual = False, False, None

instancia = MonitorBacbo()

@bot.message_handler(commands=['placar'])
def placar(m):
    total = instancia.wins + instancia.losses
    taxa = (instancia.wins / total * 100) if total > 0 else 0
    bot.reply_to(m, f"📊 *PLACAR:* {instancia.wins}W - {instancia.losses}L\n📈 *Taxa:* {taxa:.1f}%\n🔥 *Sinais SG:* {instancia.sg}", parse_mode="Markdown")

if __name__ == "__main__":
    t = threading.Thread(target=instancia.monitorar)
    t.daemon = True
    t.start()
    bot.infinity_polling()
