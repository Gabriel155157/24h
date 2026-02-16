import requests
import os

class AnalisePremium:
    def __init__(self):
        self.URL_API = "https://locabot.online/api_bacbo.php"
        self.historico_completo = []
        
        # --- PARÂMETROS DE IA ANALYST ---
        self.ASSERTIVIDADE_ALVO = 95.0  # Busca sinais de 95% a 100%
        self.MIN_OCORRENCIAS = 8        # O padrão deve ter se repetido 7x+
        self.MAX_LOOKBACK = 100         # Analisa as últimas 100 rodadas para peso
        self.TAMANHO_PADRAO = [2, 4, 6, 8] # Analisa múltiplos tamanhos de sequência

    def atualizar_banco(self):
        try:
            response = requests.get(self.URL_API, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.historico_completo = []
                for x in data:
                    p = str(x.get('pedra', '')).strip().lower()
                    cor = 'P' if p == 'player' else 'B' if p == 'banker' else 'T' if p == 'tie' else None
                    if cor: self.historico_completo.append(cor)
        except: pass

    def prever(self):
        if len(self.historico_completo) < 50: return None
        
        melhor_sinal = None
        
        for n in self.TAMANHO_PADRAO:
            padrao_atual = self.historico_completo[:n]
            
            # Análise de Probabilidade Histórica
            ocorrencias = 0
            vitorias_p = 0
            vitorias_b = 0
            empates = 0
            recencia_check = [] # Verifica se o padrão ainda está ganhando agora

            # Varredura do Mercado
            for i in range(1, len(self.historico_completo) - n - 1):
                if self.historico_completo[i : i+n] == padrao_atual:
                    ocorrencias += 1
                    proximo = self.historico_completo[i-1]
                    
                    if proximo in ['P', 'T']: vitorias_p += 1
                    if proximo in ['B', 'T']: vitorias_b += 1
                    if proximo == 'T': empates += 1
                    
                    # Salva os últimos 3 resultados desse padrão
                    if len(recencia_check) < 3:
                        res_final = 'P' if proximo in ['P', 'T'] else 'B'
                        recencia_check.append(res_final)

            if ocorrencias >= self.MIN_OCORRENCIAS:
                prob_p = (vitorias_p / ocorrencias) * 100
                prob_b = (vitorias_b / ocorrencias) * 100
                
                # Critério Sniper: 95% ou 100%
                if prob_p >= self.ASSERTIVIDADE_ALVO:
                    previsao, final_prob = 'P', prob_p
                elif prob_b >= self.ASSERTIVIDADE_ALVO:
                    previsao, final_prob = 'B', prob_b
                else: continue

                # FILTRO DE IA: Se o padrão perdeu nas últimas 2 vezes que apareceu, ele está "morto"
                if len(recencia_check) >= 2:
                    if recencia_check.count(previsao) < 1: continue

                return {
                    "cor": previsao,
                    "prob": round(final_prob, 1),
                    "amostra": ocorrencias,
                    "empate": round((empates / ocorrencias) * 100, 1),
                    "gatilho": "-".join(padrao_atual[::-1])
                }
        return None
