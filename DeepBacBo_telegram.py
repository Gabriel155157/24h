import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES DO BOT ---
# Substitua pelos seus dados reais
TOKEN = "7088974821:AAFx0xVtzEnbHleQU7J66wEfVmPtghnRHs0"
CHAT_ID = "-1002270247449"
LINK_AFILIADO = "https://go.aff.esportiva.bet/sm9dwy54"

bot = telebot.TeleBot(TOKEN)

class MonitorBacbo:
    def __init__(self):
        self.ia = AnalisePremium()
        self.ultimo_id = None
        self.wins = 0
        self.losses = 0
        self.sg = 0
        self.g1 = 0
        self.em_alerta = False
        self.previsao_atual = None
        self.gale_ativo = False
        self.inicio_sessao = datetime.now().strftime("%d/%m %H:%M")

    def enviar_msg(self, texto, markup=None):
        try:
            bot.send_message(CHAT_ID, texto, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def monitorar(self):
        print("🚀 Monitorando via API para Telegram...")
        self.enviar_msg(f"✅ *DeepBacbo IA ONLINE*\n\n🕒 *Início:* {self.inicio_sessao}\n📟 *Status:* Monitorando 24h via GitHub\n\n_Aguardando padrão de alta assertividade..._")

        while True:
            try:
                self.ia.atualizar_banco()
                historico = self.ia.historico_completo
                
                if not historico:
                    time.sleep(5)
                    continue

                # ID único baseado na última pedra (Cor + Número)
                id_rodada_atual = f"{historico[0][0]}{historico[0][1]}"

                if id_rodada_atual != self.ultimo_id:
                    resultado_cor = historico[0][0] # P, B ou T
                    
                    if self.em_alerta:
                        self.processar_resultado(resultado_cor)

                    self.ultimo_id = id_rodada_atual
                    
                    if not self.em_alerta:
                        previsao = self.ia.prever()
                        if previsao:
                            self.enviar_sinal(previsao)

                time.sleep(3)
            except Exception as e:
                print(f"Erro no loop: {e}")
                time.sleep(10)

    def enviar_sinal(self, dados):
        self.em_alerta = True
        self.previsao_atual = dados
        cor_emoji = "🔵 PLAYER" if dados['previsao_genai'] == 'P' else "🔴 BANKER"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🎰 JOGAR AGORA", url=LINK_AFILIADO))

        msg = (
            f"🎯 *SINAL CONFIRMADO*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 Jogo: *Bac Bo*\n"
            f"🎯 Entrada: *{cor_emoji}*\n"
            f"📊 Confiança: `{dados['probabilidade_genai']}%`\n"
            f"⚖️ {dados['dica_empate']}\n"
            f"🔄 Proteção: Até G1\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Aguarde o resultado...*"
        )
        self.enviar_msg(msg, markup)

    def processar_resultado(self, resultado):
        alvo = self.previsao_atual['previsao_genai']
        
        # Vitória no Alvo ou Empate (Tie)
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
            f"📈 Taxa: `{taxa:.1f}%`"
        )
        self.enviar_msg(msg)
        self.em_alerta, self.gale_ativo, self.previsao_atual = False, False, None

# --- COMANDO DE PLACAR ---
instancia = MonitorBacbo()
@bot.message_handler(commands=['placar'])
def cmd_placar(message):
    total = instancia.wins + instancia.losses
    taxa = (instancia.wins / total * 100) if total > 0 else 0
    bot.reply_to(message, f"📊 *PLACAR:* {instancia.wins}W - {instancia.losses}L\n📈 *Taxa:* {taxa:.1f}%")

if __name__ == "__main__":
    threading.Thread(target=instancia.monitorar, daemon=True).start()
    bot.infinity_polling()
