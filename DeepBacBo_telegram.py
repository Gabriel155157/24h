import requests
import time
import telebot
import threading
from datetime import datetime
from analise_premium import AnalisePremium

# --- CONFIGURAÇÕES DO BOT ---
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
            bot.send_message(CHAT_ID, texto, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def monitorar(self):
        print("🚀 Monitorando via API para Telegram...")
        self.enviar_msg(f"✅ *DeepBacbo IA ONLINE*\n\n🕒 *Início:* {self.inicio_sessao}\n📟 *Status:* Monitorando 24h\n\n_Envie /placar para consultar estatísticas._")

        while True:
            try:
                self.ia.atualizar_banco()
                historico = self.ia.historico_completo
                
                if not historico:
                    time.sleep(5)
                    continue

                id_rodada_atual = f"{historico[0][0]}{historico[0][1]}"

                if id_rodada_atual != self.ultimo_id:
                    resultado_cor = historico[0][0]
                    
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
        
        # Define cor e emoji corretamente
        if dados['previsao_genai'] == 'P':
            cor_nome = "AZUL (PLAYER)"
            emoji = "🔵"
        else:
            cor_nome = "VERMELHO (BANKER)"
            emoji = "🔴"
        
        # Criando o botão com link de afiliado
        markup = telebot.types.InlineKeyboardMarkup()
        botao = telebot.types.InlineKeyboardButton("🎰 JOGAR AGORA", url=LINK_AFILIADO)
        markup.add(botao)
        
        msg = (
            f"✅ *SINAL CONFIRMADO*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 Jogo: *Bac Bo*\n"
            f"🎯 Entrada: {emoji} *{cor_nome}*\n"
            f"📊 Confiança: `{dados['probabilidade_genai']}%`\n"
            f"⚖️ Proteção: *CUBRA O EMPATE*\n"
            f"🔄 Martingale: *Até G1*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Aguarde o resultado...*"
        )
        self.enviar_msg(msg, markup=markup)

    def processar_resultado(self, resultado):
        alvo = self.previsao_atual['previsao_genai']
        
        if resultado == alvo or resultado == 'T':
            if self.gale_ativo:
                self.g1 += 1
                tipo = "GREEN NO GALE 1 🔄"
            else:
                self.sg += 1
                tipo = "GREEN DE PRIMEIRA 🔥"
            
            self.wins += 1
            self.finalizar_ciclo(f"✅ *VITÓRIA: {tipo}*", resultado)
        
        elif not self.gale_ativo:
            self.gale_ativo = True
            self.enviar_msg("⚠️ *Atenção: Entrando no G1...*")
        
        else:
            self.losses += 1
            self.finalizar_ciclo("❌ *RED CONFIRMADO*", resultado)

    def finalizar_ciclo(self, status, pedra):
        pedra_nome = "Azul" if pedra == 'P' else "Vermelho" if pedra == 'B' else "Empate"
        total = self.wins + self.losses
        assertividade = (self.wins / total * 100) if total > 0 else 0
        
        msg = (
            f"{status}\n"
            f"🎲 Resultado: *{pedra_nome}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *PLACAR ACUMULADO*\n"
            f"✅ Wins: `{self.wins}` (SG: {self.sg} | G1: {self.g1})\n"
            f"❌ Reds: `{self.losses}`\n"
            f"📈 Taxa: `{assertividade:.1f}%`"
        )
        self.enviar_msg(msg)
        self.em_alerta = False
        self.gale_ativo = False
        self.previsao_atual = None

# --- INICIALIZAÇÃO DO SISTEMA ---
instancia_monitor = MonitorBacbo()

@bot.message_handler(commands=['placar'])
def responder_placar(message):
    total = instancia_monitor.wins + instancia_monitor.losses
    assertividade = (instancia_monitor.wins / total * 100) if total > 0 else 0
    
    msg_placar = (
        f"📊 *ESTATÍSTICAS DA SESSÃO*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Wins Totais: `{instancia_monitor.wins}`\n"
        f"   ↳ Direto (SG): {instancia_monitor.sg}\n"
        f"   ↳ No Gale (G1): {instancia_monitor.g1}\n\n"
        f"❌ Reds Totais: `{instancia_monitor.losses}`\n"
        f"📈 Assertividade: `{assertividade:.1f}%`\n"
        f"🕒 Início: {instancia_monitor.inicio_sessao}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, msg_placar, parse_mode="Markdown")

if __name__ == "__main__":
    # Inicia o monitoramento em uma thread separada
    thread_monitor = threading.Thread(target=instancia_monitor.monitorar)
    thread_monitor.daemon = True
    thread_monitor.start()
    
    # Inicia a escuta de comandos
    print("🤖 Bot de sinais e comandos ativado...")
    bot.infinity_polling()
