import requests

class AnalisePremium:
    def __init__(self):
        self.historico_completo = []
        self.URL_API = "https://locabot.online/api_bacbo.php"
        
        # --- CONFIGURAÇÕES MODO SNIPER (SEM GALE) ---
        self.ASSERTIVIDADE_MINIMA = 10.0  # Só aceita 100% de acerto inicial
        self.AMOSTRA_MINIMA = 6           # Padrão deve ter ocorrido ao menos 6 vezes
        self.TAMANHO_MAX_PADRAO = 4      

    def atualizar_banco(self):
        try:
            response = requests.get(self.URL_API, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.historico_completo = []
                for x in data:
                    tipo = str(x.get('pedra', '')).strip().lower()
                    cor = 'P' if tipo == 'player' else 'B' if tipo == 'banker' else 'T' if tipo == 'tie' else None
                    if cor: self.historico_completo.append((cor, int(x.get('numero', 0))))
        except: pass

    def prever(self):
        if len(self.historico_completo) < 50: return None
        
        for tamanho in range(self.TAMANHO_MAX_PADRAO, 1, -1):
            padrao_atual = self.historico_completo[:tamanho]
            txt_gatilho = "-".join([f"{c}" for c, n in padrao_atual[::-1]])
            
            total, win_p, win_b, tie_count = 0, 0, 0, 0
            for i in range(1, len(self.historico_completo) - tamanho - 1):
                if self.historico_completo[i : i + tamanho] == padrao_atual:
                    total += 1
                    proximo = self.historico_completo[i-1][0]
                    if proximo in ['P', 'T']: win_p += 1
                    if proximo in ['B', 'T']: win_b += 1
                    if proximo == 'T': tie_count += 1

            if total >= self.AMOSTRA_MINIMA:
                if (win_p / total) * 100 == 100.0: previsao = 'P'
                elif (win_b / total) * 100 == 100.0: previsao = 'B'
                else: continue

                return {
                    "previsao_genai": previsao,
                    "probabilidade_genai": 100.0,
                    "gatilho": txt_gatilho,
                    "dica_empate": f"CUBRA EMPATE ({(tie_count/total)*100:.0f}%)"
                }
        return None
