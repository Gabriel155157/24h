import requests
import os

class AnalisePremium:
    def __init__(self):
        self.historico_completo = []
        self.URL_API = "https://locabot.online/api_bacbo.php"
        self.arquivo_log = "padroes_vencedores.txt"
        self.padroes_ouro = self._carregar_padroes_ouro()

        # --- CONFIGURAÇÕES DE ALTA ASSERTIVIDADE (24H) ---
        self.ASSERTIVIDADE_MINIMA = 90.0  # Só entra se a chance for maior que 90%
        self.AMOSTRA_MINIMA = 5           # O padrão precisa ter aparecido pelo menos 8 vezes na história
        self.TAMANHO_MAX_PADRAO = 5      # Analisa padrões mais longos e complexos
        self.EVITAR_SURF = True           # Não aposta contra sequências maiores que 5

    def _carregar_padroes_ouro(self):
        if not os.path.exists(self.arquivo_log):
            return set()
        with open(self.arquivo_log, "r") as f:
            return set(linha.strip() for linha in f if linha.strip())

    def _salvar_padrao_ouro(self, txt_gatilho):
        if txt_gatilho not in self.padroes_ouro:
            self.padroes_ouro.add(txt_gatilho)
            with open(self.arquivo_log, "a") as f:
                f.write(f"{txt_gatilho}\n")
            return True
        return False

    def gerar_barra(self, percentual):
        blocos_cheios = int(percentual / 10)
        blocos_vazios = 10 - blocos_cheios
        return "█" * blocos_cheios + "░" * blocos_vazios

    def atualizar_banco(self):
        try:
            response = requests.get(self.URL_API, timeout=5)
            if response.status_code != 200: return
            data = response.json()
            if not data: return
            self.historico_completo = []
            for x in data:
                # Normaliza: Player(P), Banker(B), Tie(T)
                cor = 'P' if x['pedra'] == 'Player' else 'B' if x['pedra'] == 'Banker' else 'T'
                num = int(x['numero'])
                self.historico_completo.append((cor, num))
        except Exception: pass

    def prever(self):
        # Precisa de um histórico razoável para analisar
        if len(self.historico_completo) < 50: return None
        
        # --- PROTEÇÃO ANTI-SURF (Não apostar contra tendência forte) ---
        if self.EVITAR_SURF:
            ultima_cor = self.historico_completo[-1][0]
            repeticoes = 0
            for i in range(1, 10):
                if i < len(self.historico_completo) and self.historico_completo[-i][0] == ultima_cor:
                    repeticoes += 1
                else:
                    break
            # Se tiver mais de 5 cores iguais seguidas, o mercado está perigoso. Abortar.
            if repeticoes >= 5:
                return None

        # Loop para encontrar padrões
        melhor_sinal = None
        maior_probabilidade = 0

        for tamanho in range(2, self.TAMANHO_MAX_PADRAO + 1):
            padrao_atual = self.historico_completo[:tamanho]
            txt_gatilho = "-".join([f"{c}{n}" for c, n in padrao_atual[::-1]])
            
            total_encontrado = 0
            stats_p = {'sg': 0, 'g1': 0}
            stats_b = {'sg': 0, 'g1': 0}
            empates_count = 0
            
            # Lista para verificar como o padrão se comportou nas ÚLTIMAS vezes (Recência)
            ultimos_resultados = [] 

            limite_busca = len(self.historico_completo) - tamanho - 2
            
            for i in range(1, limite_busca):
                if self.historico_completo[i : i + tamanho] == padrao_atual:
                    total_encontrado += 1
                    
                    # Verifica o resultado que veio LOGO DEPOIS desse padrão no passado
                    resultado_real = self.historico_completo[i-1][0] # P, B ou T
                    resultado_gale = self.historico_completo[i-2][0] if i >= 2 else None
                    
                    # Contabiliza estatísticas
                    if resultado_real in ['P', 'T']: stats_p['sg'] += 1
                    elif resultado_gale in ['P', 'T']: stats_p['g1'] += 1
                    
                    if resultado_real in ['B', 'T']: stats_b['sg'] += 1
                    elif resultado_gale in ['B', 'T']: stats_b['g1'] += 1
                    
                    if resultado_real == 'T': empates_count += 1

                    # Registra quem ganhou nessa ocorrência para análise de tendência recente
                    vencedor = 'P' if resultado_real in ['P', 'T'] else 'B' 
                    # Se foi G1, conta também
                    if resultado_real not in ['P', 'T'] and resultado_gale in ['P', 'T']: vencedor = 'P'
                    if resultado_real not in ['B', 'T'] and resultado_gale in ['B', 'T']: vencedor = 'B'
                    
                    ultimos_resultados.append(vencedor)

            # --- FILTROS DE ASSERTIVIDADE ---
            if total_encontrado >= self.AMOSTRA_MINIMA:
                prob_p = ((stats_p['sg'] + stats_p['g1']) / total_encontrado) * 100
                prob_b = ((stats_b['sg'] + stats_b['g1']) / total_encontrado) * 100
                
                # Define a aposta sugerida
                if prob_p >= self.ASSERTIVIDADE_MINIMA and prob_p > prob_b:
                    previsao = 'P'
                    prob_final = prob_p
                    stats = stats_p
                elif prob_b >= self.ASSERTIVIDADE_MINIMA and prob_b > prob_p:
                    previsao = 'B'
                    prob_final = prob_b
                    stats = stats_b
                else:
                    continue # Nenhuma probabilidade atingiu a meta

                # --- FILTRO 1: SG deve ser dominante ---
                p_sg = (stats['sg'] / total_encontrado) * 100
                p_g1 = (stats['g1'] / total_encontrado) * 100
                if p_sg < 70.0: # Se depende muito de Gale, descarta
                    continue

                # --- FILTRO 2: Recência (O padrão morreu?) ---
                # Pega as últimas 3 vezes que esse padrão apareceu. 
                # Se a aposta sugerida perdeu nas últimas 2 ocorrências, o padrão está "frio".
                if len(ultimos_resultados) >= 2:
                    ultimas_ocorrencias = ultimos_resultados[:3] # As 3 mais recentes (o loop varre do passado pro presente, mas a lista pode estar invertida dependendo da logica, aqui assumimos ordem cronologica de inserção no loop ou ajustamos)
                    # Nota: No loop acima, estamos varrendo do presente para o passado?
                    # O loop original: `for i in range(1, limite_busca):` varre do início da lista (que é o presente/recente) para o fim (passado).
                    # Então `ultimos_resultados[0]` é a ocorrência mais recente encontrada no histórico passado.
                    
                    # Se na última vez que apareceu, deu a cor OPOSTA, perigo.
                    if ultimos_resultados[0] != previsao:
                        # Se errou 2 vezes seguidas recentemente, aborta.
                        if len(ultimos_resultados) > 1 and ultimos_resultados[1] != previsao:
                            continue 

                # Se passou por todos os filtros e é melhor que o sinal anterior encontrado
                if prob_final > maior_probabilidade:
                    maior_probabilidade = prob_final
                    
                    is_sniper = (p_sg >= 100.0 and total_encontrado >= 6) # Sniper agora exige 6 aparições perfeitas
                    if is_sniper: self._salvar_padrao_ouro(txt_gatilho)

                    p_tie = (empates_count / total_encontrado) * 100
                    label_ouro = "💎 PADRÃO OURO (SNIPER)" if is_sniper else "🔥 SINAL FORTE"
                    
                    info_sg = f"{p_sg:.0f}% ({stats['sg']}/{total_encontrado})"
                    info_g1 = f"{p_g1:.0f}% ({stats['g1']}/{total_encontrado})"

                    melhor_sinal = {
                        "previsao_genai": previsao,
                        "probabilidade_genai": round(prob_final, 1),
                        "gatilho": txt_gatilho,
                        "grafico": f"{label_ouro}\nSG: {self.gerar_barra(p_sg)} {info_sg}\nG1: {self.gerar_barra(p_g1)} {info_g1}",
                        "dica_empate": f"CUBRA EMPATE ({p_tie:.0f}%)",
                        "motivo": f"Padrão {txt_gatilho} apareceu {total_encontrado}x (SG Dominante).",
                        "cobrir": p_tie > 15,
                        "is_sniper": is_sniper
                    }

        return melhor_sinal
