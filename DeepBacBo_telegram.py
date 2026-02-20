import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES DA SALA ---
TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0" # Seu Token
CHAT_ID = "-1002270247449"                             # Seu Chat ID
LINK_AFILIADO = "https://go.aff.esportiva.bet/sm9dwy54" # Seu Link

bot = telebot.TeleBot(TOKEN)
ia_premium = AnalisePremium()

class SalaSinais:
    def __init__(self):
        self.ultimo_id = None
        self.wins = 0
        self.losses = 0
        self.sg = 0
        self.g1 = 0
        self.em_alerta = False
        self.previsao_atual = None
        self.gale_ativo = False
        self.msg_alerta_id = None

    def enviar_msg(self, texto, markup=None):
        try:
            return bot.send_message(CHAT_ID, texto, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def monitorar(self):
        print("🚀 Sala de Sinais DeepBacbo Online...")
        self.enviar_msg("✅ *DeepBacbo IA ONLINE*\n📟 Monitorando sinais 24h...")

        while True:
            try:
                ia_premium.atualizar_banco()
                hist = ia_premium.historico_completo
                
                if not hist:
                    time.sleep(5)
                    continue

                # Identifica se houve uma nova rodada
                id_atual = f"{hist[0][0]}{hist[0][1]}"

                if id_atual != self.ultimo_id:
                    if self.em_alerta:
                        # Pequeno delay para a API estabilizar o resultado real
                        time.sleep(2)
                        ia_premium.atualizar_banco()
                        self.processar_resultado(ia_premium.historico_completo[0][0])

                    self.ultimo_id = id_atual
                    
                    if not self.em_alerta:
                        previsao = ia_premium.prever()
                        if previsao:
                            self.enviar_sinal(previsao)

                time.sleep(3)
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(10)

    def enviar_sinal(self, dados):
        self.em_alerta = True
        self.previsao_atual = dados
        cor_emoji = "🔵 AZUL (PLAYER)" if dados['previsao_genai'] == 'P' else "🔴 VERMELHO (BANKER)"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🎰 APOSTAR AGORA", url=LINK_AFILIADO))

        msg = (
            f"🎯 *SINAL CONFIRMADO*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 Jogo: *Bac Bo*\n"
            f"🎯 Entrada: *{cor_emoji}*\n"
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
            if self.gale_ativo:
                self.g1 += 1
                tipo = "GREEN NO G1! 🔄"
            else:
                self.sg += 1
                tipo = "GREEN DE PRIMEIRA! 🔥"
            
            self.wins += 1
            self.finalizar_ciclo(f"✅ *{tipo}*\nResultado: {resultado}")
        
        elif not self.gale_ativo:
            self.gale_ativo = True
            self.enviar_msg("🔄 *Entrando no GALE 1...*")
        
        else:
            self.losses += 1
            self.finalizar_ciclo(f"❌ *RED CONFIRMADO*\nResultado: {resultado}")

    def finalizar_ciclo(self, status):
        total = self.wins + self.losses
        taxa = (self.wins / total * 100) if total > 0 else 0
        msg = (
            f"{status}\n\n"
            f"📊 *PLACAR ATUAL:*\n"
            f"✅ Wins: {self.wins} (SG: {self.sg} | G1: {self.g1})\n"
            f"❌ Reds: {self.losses}\n"
            f"📈 Assertividade: `{taxa:.1f}%`"
        )
        self.enviar_msg(msg)
        self.em_alerta, self.gale_ativo, self.previsao_atual = False, False, None

# --- COMANDO DE PLACAR ---
instancia = SalaSinais()
@bot.message_handler(commands=['placar'])
def cmd_placar(message):
    total = instancia.wins + instancia.losses
    taxa = (instancia.wins / total * 100) if total > 0 else 0
    bot.reply_to(message, f"📊 *PLACAR:* {instancia.wins}W - {instancia.losses}L\n📈 *Taxa:* {taxa:.1f}%")

if __name__ == "__main__":
    threading.Thread(target=instancia.monitorar, daemon=True).start()
    bot.infinity_polling()
