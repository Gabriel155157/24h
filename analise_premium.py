import requests
import os

class AnalisePremium:
    def __init__(self):
        self.historico_completo = []
        self.URL_API = "https://locabot.online/api_bacbo.php"
        self.arquivo_log = "padroes_vencedores.txt"
        self.padroes_ouro = self._carregar_padroes_ouro()

        # --- CONFIGURAÇÕES DE ALTA ASSERTIVIDADE ---
        self.ASSERTIVIDADE_MINIMA = 80.0
        self.AMOSTRA_MINIMA = 5
        self.TAMANHO_MAX_PADRAO = 5
        self.EVITAR_SURF = True

    def _carregar_padroes_ouro(self):
        if not os.path.exists(self.arquivo_log): return set()
        with open(self.arquivo_log, "r") as f:
            return set(linha.strip() for if linha.strip())

    def _salvar_padrao_ouro(self, txt_gatilho):
        if txt_gatilho not in self.padroes_ouro:
            self.padroes_ouro.add(txt_gatilho)
            with open(self.arquivo_log, "a") as f:
                f.write(f"{txt_gatilho}\n")
            return True
        return False

    def gerar_barra(self, percentual):
        blocos = int(percentual / 10)
        return "█" * blocos + "░" * (10 - blocos)

    def atualizar_banco(self):
        try:
            response = requests.get(self.URL_API, timeout=5)
            if response.status_code != 200: return
            data = response.json()
            if not data: return
            
            self.historico_completo = []
            for x in data:
                # NORMALIZAÇÃO BLINDADA: Remove espaços e ignora maiúsculas
                tipo_bruto = str(x.get('pedra', '')).strip().lower()
                
                if tipo_bruto == 'player': cor = 'P'
                elif tipo_bruto == 'banker': cor = 'B'
                elif tipo_bruto == 'tie': cor = 'T'
                else: continue # Se o dado for inválido, pula a rodada em vez de inventar empate
                
                num = int(x.get('numero', 0))
                self.historico_completo.append((cor, num))
        except Exception as e:
            print(f"Erro banco: {e}")

    def prever(self):
        if len(self.historico_completo) < 50: return None
        
        # ANTI-SURF
        ultima_cor = self.historico_completo[0][0]
        repeticoes = 0
        for i in range(len(self.historico_completo)):
            if self.historico_completo[i][0] == ultima_cor: repeticoes += 1
            else: break
        if repeticoes >= 5: return None

        melhor_sinal = None
        maior_prob = 0

        for tamanho in range(2, self.TAMANHO_MAX_PADRAO + 1):
            padrao_atual = self.historico_completo[:tamanho]
            txt_gatilho = "-".join([f"{c}{n}" for c, n in padrao_atual[::-1]])
            
            total = 0
            stats_p = {'sg': 0, 'g1': 0}
            stats_b = {'sg': 0, 'g1': 0}
            ties = 0
            ultimos_res = []

            for i in range(1, len(self.historico_completo) - tamanho - 2):
                if self.historico_completo[i : i + tamanho] == padrao_atual:
                    total += 1
                    res = self.historico_completo[i-1][0]
                    gale = self.historico_completo[i-2][0] if i >= 2 else None
                    
                    if res in ['P', 'T']: stats_p['sg'] += 1
                    elif gale in ['P', 'T']: stats_p['g1'] += 1
                    
                    if res in ['B', 'T']: stats_b['sg'] += 1
                    elif gale in ['B', 'T']: stats_b['g1'] += 1
                    
                    if res == 'T': ties += 1
                    ultimos_res.append('P' if res in ['P','T'] or (res not in ['P','T'] and gale in ['P','T']) else 'B')

            if total >= self.AMOSTRA_MINIMA:
                prob_p = ((stats_p['sg'] + stats_p['g1']) / total) * 100
                prob_b = ((stats_b['sg'] + stats_b['g1']) / total) * 100
                
                if prob_p >= self.ASSERTIVIDADE_MINIMA and prob_p > prob_b:
                    previsao, prob_f, stats = 'P', prob_p, stats_p
                elif prob_b >= self.ASSERTIVIDADE_MINIMA and prob_b > prob_p:
                    previsao, prob_f, stats = 'B', prob_b, stats_b
                else: continue

                p_sg = (stats['sg'] / total) * 100
                if p_sg < 20.0: continue
                if len(ultimos_res) >= 2 and (ultimos_res[0] != previsao and ultimos_res[1] != previsao): continue

                if prob_f > maior_prob:
                    maior_prob = prob_f
                    is_sniper = (p_sg >= 100.0 and total >= 6)
                    p_tie = (ties / total) * 100
                    
                    melhor_sinal = {
                        "previsao_genai": previsao,
                        "probabilidade_genai": round(prob_f, 1),
                        "gatilho": txt_gatilho,
                        "grafico": f"{'💎 SNIPER' if is_sniper else '🔥 FORTE'}\nSG: {self.gerar_barra(p_sg)} {p_sg:.0f}%\nG1: {self.gerar_barra((stats['g1']/total)*100)} {(stats['g1']/total)*100:.0f}%",
                        "dica_empate": f"COBRIR EMPATE ({p_tie:.0f}%)",
                        "is_sniper": is_sniper
                    }
        return melhor_sinal
