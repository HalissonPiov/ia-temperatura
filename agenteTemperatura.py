class AgenteTemperatura:

    def __init__(self, temperatura_desejada=25, margem=1, k=1):
        self.k = k
        self.esta_temperatura_ideal = False
        self.temperatura_desejada = temperatura_desejada
        self.margem = margem
        self.estado_sistema = "desligado"
        self.ultima_acao = "desligar"
        self.temperaturas_anteriores = []
        self.temperatura_atual = self.temperatura_desejada
        self.tempo_espera_restante = self.cal_tempo_espera()
        self.variacao_temperatura = 0
        self.episodio_ativo = False
        self.tipo_episodio = ""
        self.tempo_contador = 0
        self.t_inicio = 0
        self.taxas_resfriamento = []
        self.taxas_elevacao = []
        self.media_taxa_resfriamento = 0
        self.media_taxa_elevacao = 0

    def cal_tempo_espera(self):
        tempo_espera = self.k * abs(self.temperatura_atual - self.temperatura_desejada)
        return tempo_espera

    def perceber(self, ambiente):
        return {
            "temperatura_atual": ambiente,
            "temperatura_desejada": self.temperatura_desejada,
            "estado_sistema": self.estado_sistema
        }

    def decidir(self, percepcao):
        temp_atual = percepcao["temperatura_atual"]
        temp_desejada = percepcao["temperatura_desejada"]

        self.temperaturas_anteriores.append(temp_atual)

        if len(self.temperaturas_anteriores) > 1:
            temp_anterior = self.temperaturas_anteriores[-2]
        else:
            temp_anterior = temp_atual

        limite_superior = temp_desejada + self.margem
        limite_inferior = temp_desejada - self.margem

        if temp_atual > limite_superior:
            if self.episodio_ativo and self.tipo_episodio == "elevacao":
                self.aprendizado_termico()

            self.tipo_episodio = "resfriamento"

            if self.episodio_ativo:
                self.tempo_contador += 1
                return "manter"
            else:
                self.episodio_ativo = True
                self.t_inicio = temp_atual
                self.tempo_contador = 1
                return "ligar"

        elif temp_atual < limite_inferior and self.estado_sistema == "ligado":
            if self.episodio_ativo and self.tipo_episodio == "resfriamento":
                self.aprendizado_termico()
            return "desligar"

        elif self.estado_sistema == "desligado" and temp_atual > temp_anterior:
            if self.episodio_ativo and self.tipo_episodio == "resfriamento":
                self.aprendizado_termico()
            self.tipo_episodio = "elevacao"

            if self.episodio_ativo:
                self.tempo_contador += 1
            else:
                self.episodio_ativo = True
                self.t_inicio = temp_atual
                self.tempo_contador = 1

            return "manter"

        elif limite_inferior <= temp_atual <= limite_superior and self.estado_sistema == "ligado":
            if self.episodio_ativo and self.tipo_episodio == "resfriamento":
                self.aprendizado_termico()
            self.esta_temperatura_ideal = True
            return "desligar"

        else:
            if self.episodio_ativo and self.tipo_episodio == "elevacao":
                self.aprendizado_termico()
            self.esta_temperatura_ideal = True
            return "manter"

    def agir(self, ambiente):
        if self.tempo_espera_restante > 0:
            self.tempo_espera_restante -= 1
            return "manter"

        self.temperatura_atual = ambiente
        percepcao = self.perceber(ambiente)
        acao = self.decidir(percepcao)

        if acao == "ligar":
            self.estado_sistema = "ligado"
        elif acao == "desligar":
            self.estado_sistema = "desligado"

        self.ultima_acao = acao
        self.tempo_espera_restante = self.cal_tempo_espera()
        return acao

    def aprendizado_termico(self):
        if self.tempo_contador <= 0:
            return

        if self.tipo_episodio == "resfriamento":
            taxa = (self.t_inicio - self.temperatura_desejada) / self.tempo_contador
            self.taxas_resfriamento.append(taxa)
            self.media_taxa_resfriamento = round(sum(self.taxas_resfriamento) / len(self.taxas_resfriamento), 2)

        elif self.tipo_episodio == "elevacao":
            taxa = (self.temperatura_atual - self.t_inicio) / self.tempo_contador
            self.taxas_elevacao.append(taxa)
            self.media_taxa_elevacao = round(sum(self.taxas_elevacao) / len(self.taxas_elevacao), 2)

        self.episodio_ativo = False
        self.tipo_episodio = ""
        self.tempo_contador = 0
        self.t_inicio = 0

if __name__ == "__main__":
    agente = AgenteTemperatura(temperatura_desejada=25, margem=1)

    temperaturas_simuladas = [25.0, 25.5, 26.0, 26.1, 26.5, 25.8, 24.5, 24.0, 23.8, 24.2, 25.0]

    print("Iniciando simulação...\n")
    print(f"Temperatura desejada: {agente.temperatura_desejada}°C")
    print(f"Margem de tolerância: ±{agente.margem}°C\n")

    for temp in temperaturas_simuladas:
        acao = agente.agir(temp)
        print(f"Ambiente: {temp}°C -> Ação: {acao.upper():<8} | Estado: {agente.estado_sistema.upper()}")

    print("\nTaxas de resfriamento:", agente.taxas_resfriamento)
    print("Média taxa de resfriamento:", agente.media_taxa_resfriamento)
    print("Taxas de elevação:", agente.taxas_elevacao)
    print("Média taxa de elevação:", agente.media_taxa_elevacao)