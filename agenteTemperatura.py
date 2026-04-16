import statistics

class AgenteTemperatura:
    def __init__(self, temperatura_atual, temperatura_desejada=25, margem=1, k=1, alfa=0, beta=0):
        self.k = k
        self.esta_temperatura_ideal = False
        self.temperatura_desejada = temperatura_desejada
        self.margem = margem
        self.estado_sistema = "desligado"
        self.ultima_acao = "desligar"
        self.temperaturas_anteriores = []
        self.temperatura_atual = temperatura_atual
        self.tempo_espera_restante = self.cal_tempo_espera_inicial(temperatura_atual)
        self.variacao_temperatura = 0
        self.episodio_ativo = False
        self.tipo_episodio = ""
        self.tempo_contador = 1
        self.t_inicio = 0
        self.taxas_resfriamento = []
        self.taxas_elevacao = []
        self.media_taxa_resfriamento = 0
        self.media_taxa_elevacao = 0
        self.alfa = alfa
        self.beta = beta
        self.sigma = 0

    def cal_tempo_espera_inicial(self, temperatura_atual):
        return round(self.k * abs(temperatura_atual - self.temperatura_desejada))
        
    
    def cal_tempo_espera_medio(self, percepcao):
        temp_atual = percepcao["temperatura_atual"]
        temp_desejada = percepcao["temperatura_desejada"]

        if self.estado_sistema == "ligado":
            taxa = self.taxa_resfriamento()

            if taxa > 0:
                return round((temp_atual - temp_desejada) / taxa)
            else:
                return self.cal_tempo_espera_inicial(temp_atual)

        else:
            taxa = self.taxa_elevacao()

            if taxa > 0:
                return round((temp_desejada - temp_atual) / taxa)
            else:
                return self.cal_tempo_espera_inicial(temp_atual)


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
        self.tempo_espera_restante = self.cal_tempo_espera_medio(percepcao)
        self.calcular_sigma()

        if len(self.temperaturas_anteriores) > 1:
            temp_anterior = self.temperaturas_anteriores[-2]
        else:
            temp_anterior = temp_atual

        limite_superior = self.calculo_limite_superior()
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

        elif temp_atual < limite_inferior and self.estado_sistema == "desligado":
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
            self.episodio_ativo = True
            if temp_atual < temp_anterior:
                if self.tipo_episodio == "elevacao":
                    self.aprendizado_termico()
                    self.tempo_contador = 1
                    self.tipo_episodio = "resfriamento"
                else:
                    self.tempo_contador += 1 
                    self.tipo_episodio = "resfriamento"

            if temp_atual > temp_anterior:
                if self.tipo_episodio == "resfriamento":
                    self.aprendizado_termico()
                    self.tempo_contador = 1
                    self.tipo_episodio = "elevacao"
                else:
                    self.tempo_contador += 1
                    self.tipo_episodio = "elevacao"
                
            return "manter"

    def agir(self, ambiente):
        for tempo in range(self.tempo_espera_restante):
            self.tempo_espera_restante -= 1 

        self.temperatura_atual = ambiente
        percepcao = self.perceber(ambiente)
        acao = self.decidir(percepcao)

        if acao == "ligar":
            self.estado_sistema = "ligado"
        elif acao == "desligar":
            self.estado_sistema = "desligado"

        self.ultima_acao = acao
        return acao

    def aprendizado_termico(self):
        if self.tempo_contador <= 0:
            return

        if self.tipo_episodio == "resfriamento":
            taxa = self.taxa_resfriamento()
            self.taxas_resfriamento.append(taxa)
            self.media_taxa_resfriamento = round(sum(self.taxas_resfriamento) / len(self.taxas_resfriamento), 2)

        elif self.tipo_episodio == "elevacao":
            taxa = self.taxa_elevacao()
            self.taxas_elevacao.append(taxa)
            self.media_taxa_elevacao = round(sum(self.taxas_elevacao) / len(self.taxas_elevacao), 2)

        self.episodio_ativo = False
        self.tipo_episodio = ""
        self.tempo_contador = 1
        self.t_inicio = 0

    def taxa_resfriamento(self):
        return (self.t_inicio - self.temperatura_desejada) / self.tempo_contador
    
    def taxa_elevacao(self): 
        return (self.temperatura_desejada - self.t_inicio) / self.tempo_contador

    def custo_situacao(self):
        J = abs(self.temperatura_atual - self.temperatura_desejada)

        if self.estado_sistema == "ligado":
            J = self.alfa * J + self.beta * 1
        else:
            J = self.alfa * J
        return J

    def calcular_sigma(self):
        if len(self.temperaturas_anteriores) > 1:
            self.sigma = statistics.pstdev(self.temperaturas_anteriores)
        else:
            self.sigma = 0

    def calculo_limite_superior(self):
        L = self.temperatura_desejada + 2*self.sigma
        return L
