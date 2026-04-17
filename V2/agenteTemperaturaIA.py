from dataclasses import dataclass, field
from math import ceil
from typing import List, Optional, Dict, Any


@dataclass
class Ambiente:
    """
    Representa o ambiente monitorado pelo agente.
    """
    temperatura_atual: float
    temperatura_desejada: float
    sistema_ligado: bool = False


@dataclass
class EpisodioTermico:
    """
    Representa um episódio térmico.

    tipo:
        - 'resfriamento'
        - 'elevacao'
    """
    tipo: str
    temperatura_inicio: float
    tempo_inicio: int
    temperatura_fim: Optional[float] = None
    tempo_fim: Optional[int] = None

    def encerrar(self, temperatura_fim: float, tempo_fim: int) -> None:
        self.temperatura_fim = temperatura_fim
        self.tempo_fim = tempo_fim

    @property
    def duracao(self) -> int:
        if self.tempo_fim is None:
            return 0
        return self.tempo_fim - self.tempo_inicio


class AgenteTemperatura:
    """
    Agente inteligente para controle de temperatura.

    Regras implementadas:
    1. Verifica se ainda está em espera.
    2. Percebe o ambiente somente quando não há espera.
    3. Armazena leitura na memória.
    4. Atualiza aprendizado térmico ao concluir episódios.
    5. Calcula o custo atual.
    6. Calcula limite superior de acionamento.
    7. Liga o sistema se Ta > L.
    8. Calcula espera durante resfriamento.
    9. Desliga o sistema quando Ta <= L e estiver ligado.
    10. Calcula espera durante elevação.
    11. Mantém estado quando não houver motivo para mudança.
    12. Executa ação e atualiza histórico.
    """

    def __init__(
        self,
        temperatura_desejada: float,
        sigma: float,
        alpha: float,
        beta: float,
        k: float = 1.0,
    ) -> None:
        # Parâmetros
        self.temperatura_desejada = temperatura_desejada
        self.sigma = sigma
        self.alpha = alpha
        self.beta = beta
        self.k = k

        # Estado interno
        self.estado_atual = "DESLIGADO"
        self.tempo_espera_restante = 0
        self.tempo_atual = 0
        self.ultima_acao = "MANTER"

        # Memória
        self.temperaturas_anteriores: List[float] = []
        self.historico: List[Dict[str, Any]] = []

        # Episódios e aprendizado
        self.episodio_atual: Optional[EpisodioTermico] = None
        self.taxas_resfriamento: List[float] = []
        self.taxas_elevacao: List[float] = []

    @property
    def limite_superior(self) -> float:
        """
        Regra 6:
            L = Td + 3σ
        """
        return self.temperatura_desejada + 3 * self.sigma

    @property
    def media_resfriamento(self) -> Optional[float]:
        if not self.taxas_resfriamento:
            return None
        return sum(self.taxas_resfriamento) / len(self.taxas_resfriamento)

    @property
    def media_elevacao(self) -> Optional[float]:
        if not self.taxas_elevacao:
            return None
        return sum(self.taxas_elevacao) / len(self.taxas_elevacao)

    def verificar_espera(self) -> bool:
        """
        Regra 1:
        Se tempo_espera_restante > 0, não faz nova leitura.
        Apenas reduz o contador e mantém o estado atual.

        Retorno:
            True  -> ainda estava em espera
            False -> não estava em espera
        """
        if self.tempo_espera_restante > 0:
            self.tempo_espera_restante -= 1
            self.tempo_atual += 1

            self._registrar_historico(
                temperatura=None,
                custo=None,
                acao="MANTER",
                observacao="Agente em espera; nenhuma nova leitura realizada.",
            )
            return True

        return False

    def perceber(self, ambiente: Ambiente) -> Dict[str, Any]:
        """
        Regra 2:
        Realiza nova percepção do ambiente.
        """
        percepcao = {
            "Ta": ambiente.temperatura_atual,
            "Td": ambiente.temperatura_desejada,
            "estado_sistema": "LIGADO" if ambiente.sistema_ligado else "DESLIGADO",
        }
        return percepcao

    def armazenar_leitura(self, temperatura: float) -> None:
        """
        Regra 3:
        Toda leitura realizada deve ser registrada na memória.
        """
        self.temperaturas_anteriores.append(temperatura)

    def atualizar_aprendizado_termico(self, temperatura_atual: float) -> None:
        """
        Regra 4:
        Após registrar a leitura, verifica se algum episódio térmico foi concluído.
        Se terminar, atualiza as médias aprendidas.
        """
        if self.episodio_atual is None:
            return

        Td = self.temperatura_desejada
        episodio = self.episodio_atual

        if episodio.tipo == "resfriamento" and temperatura_atual <= Td:
            episodio.encerrar(temperatura_fim=temperatura_atual, tempo_fim=self.tempo_atual)
            taxa = self._calcular_taxa_resfriamento(episodio)
            if taxa is not None:
                self.taxas_resfriamento.append(taxa)
            self.episodio_atual = None

        elif episodio.tipo == "elevacao" and temperatura_atual >= Td:
            episodio.encerrar(temperatura_fim=temperatura_atual, tempo_fim=self.tempo_atual)
            taxa = self._calcular_taxa_elevacao(episodio)
            if taxa is not None:
                self.taxas_elevacao.append(taxa)
            self.episodio_atual = None

    def _calcular_taxa_resfriamento(self, episodio: EpisodioTermico) -> Optional[float]:
        """
        Aprendizado das taxas térmicas:
            r↓ = (Tinício - Td) / Δt
        """
        dt = episodio.duracao
        if dt <= 0:
            return None

        Td = self.temperatura_desejada
        return (episodio.temperatura_inicio - Td) / dt

    def _calcular_taxa_elevacao(self, episodio: EpisodioTermico) -> Optional[float]:
        """
        Aprendizado das taxas térmicas:
            r↑ = (Td - Tinício) / Δt
        """
        dt = episodio.duracao
        if dt <= 0:
            return None

        Td = self.temperatura_desejada
        return (Td - episodio.temperatura_inicio) / dt


    def calcular_custo(self, temperatura_atual: float) -> float:
        """
        Regra 5:
            J = α|Ta - Td| + β C_ligado

        Consideração:
            C_ligado = 1 se o sistema estiver ligado, senão 0.
        """
        c_ligado = 1 if self.estado_atual == "LIGADO" else 0
        return self.alpha * abs(temperatura_atual - self.temperatura_desejada) + self.beta * c_ligado

    def decidir(self, temperatura_atual: float) -> str:
        """
        Decide a ação com base nas regras:
        - Regra 7: se Ta > L, ligar ou manter ligado
        - Regra 9: se Ta <= L e sistema ligado, desligar
        - Regra 11: caso contrário, manter
        """
        L = self.limite_superior

        # Regra 7
        if temperatura_atual > L:
            if self.estado_atual == "DESLIGADO":
                return "LIGAR"
            return "MANTER"

        # Regra 9
        if temperatura_atual <= L and self.estado_atual == "LIGADO":
            return "DESLIGAR"

        # Regra 11
        return "MANTER"

    def calcular_tempo_espera_resfriamento(self, temperatura_atual: float) -> int:
        """
        Regra 8:
        Caso 1: existe média de decaimento aprendida
            tempo_espera = ceil((Ta - Td) / r̄↓)

        Caso 2: não existe média aprendida
            tempo_espera = ceil(k(Ta - Td))
        """
        excesso = temperatura_atual - self.temperatura_desejada
        if excesso <= 0:
            return 0

        media = self.media_resfriamento
        if media is not None and media > 0:
            return max(1, ceil(excesso / media))

        return max(1, ceil(self.k * excesso))

    def calcular_tempo_espera_elevacao(self, temperatura_atual: float) -> int:
        """
        Regra 10:
        Caso 1: existe média de elevação aprendida
            tempo_espera = ceil((Td - Ta) / r̄↑)

        Caso 2: não existe média aprendida
            tempo_espera = ceil(k(Td - Ta))
        """
        falta = self.temperatura_desejada - temperatura_atual
        if falta <= 0:
            return 0

        media = self.media_elevacao
        if media is not None and media > 0:
            return max(1, ceil(falta / media))

        return max(1, ceil(self.k * falta))

    def agir(self, ambiente: Ambiente, acao: str, temperatura_atual: float, custo: float) -> None:
        """
        Regra 12:
        Executa a ação no ambiente e atualiza o histórico.
        """
        if acao == "LIGAR":
            ambiente.sistema_ligado = True
            self.estado_atual = "LIGADO"
            self._iniciar_ou_trocar_episodio("resfriamento", temperatura_atual)

            self.tempo_espera_restante = self.calcular_tempo_espera_resfriamento(temperatura_atual)

        elif acao == "DESLIGAR":
            ambiente.sistema_ligado = False
            self.estado_atual = "DESLIGADO"
            self._encerrar_se_resfriamento(temperatura_atual)
            self._iniciar_ou_trocar_episodio("elevacao", temperatura_atual)

            if temperatura_atual < self.temperatura_desejada:
                self.tempo_espera_restante = self.calcular_tempo_espera_elevacao(temperatura_atual)
            else:
                self.tempo_espera_restante = 0

        else:  # MANTER
            if self.estado_atual == "LIGADO":
                ambiente.sistema_ligado = True
                self._iniciar_ou_trocar_episodio("resfriamento", temperatura_atual)
                self.tempo_espera_restante = self.calcular_tempo_espera_resfriamento(temperatura_atual)

            else:
                ambiente.sistema_ligado = False

                if temperatura_atual < self.temperatura_desejada:
                    self._iniciar_ou_trocar_episodio("elevacao", temperatura_atual)
                    self.tempo_espera_restante = self.calcular_tempo_espera_elevacao(temperatura_atual)
                else:
                    self.tempo_espera_restante = 0

        self.ultima_acao = acao

        self._registrar_historico(
            temperatura=temperatura_atual,
            custo=custo,
            acao=acao,
            observacao="Ação executada e estado atualizado.",
        )

    def passo(self, ambiente: Ambiente) -> str:
        """
        Executa um ciclo completo do agente.
        """
        # Regra 1
        if self.verificar_espera():
            return "MANTER"

        # Avança o tempo quando houver leitura
        self.tempo_atual += 1

        # Regra 2
        percepcao = self.perceber(ambiente)
        temperatura_atual = percepcao["Ta"]

        # Regra 3
        self.armazenar_leitura(temperatura_atual)

        # Regra 4
        self.atualizar_aprendizado_termico(temperatura_atual)

        # Regra 5
        custo = self.calcular_custo(temperatura_atual)

        # Regras 7, 9 e 11
        acao = self.decidir(temperatura_atual)

        # Regra 12
        self.agir(ambiente, acao, temperatura_atual, custo)

        return acao

    def _iniciar_ou_trocar_episodio(self, tipo: str, temperatura_atual: float) -> None:
        """
        Inicia um episódio, se necessário, ou troca o tipo do episódio atual.
        """
        if self.episodio_atual is None:
            self.episodio_atual = EpisodioTermico(
                tipo=tipo,
                temperatura_inicio=temperatura_atual,
                tempo_inicio=self.tempo_atual,
            )
            return

        if self.episodio_atual.tipo != tipo:
            self.episodio_atual = EpisodioTermico(
                tipo=tipo,
                temperatura_inicio=temperatura_atual,
                tempo_inicio=self.tempo_atual,
            )

    def _encerrar_se_resfriamento(self, temperatura_atual: float) -> None:
        """
        Encerra episódio de resfriamento se ele estiver em andamento.
        """
        if self.episodio_atual is not None and self.episodio_atual.tipo == "resfriamento":
            self.episodio_atual.encerrar(
                temperatura_fim=temperatura_atual,
                tempo_fim=self.tempo_atual,
            )
            taxa = self._calcular_taxa_resfriamento(self.episodio_atual)
            if taxa is not None:
                self.taxas_resfriamento.append(taxa)
            self.episodio_atual = None

    def _registrar_historico(
        self,
        temperatura: Optional[float],
        custo: Optional[float],
        acao: str,
        observacao: str,
    ) -> None:
        self.historico.append(
            {
                "tempo": self.tempo_atual,
                "temperatura": temperatura,
                "temperatura_desejada": self.temperatura_desejada,
                "limite_superior": self.limite_superior,
                "estado_atual": self.estado_atual,
                "acao": acao,
                "tempo_espera_restante": self.tempo_espera_restante,
                "custo": custo,
                "media_resfriamento": self.media_resfriamento,
                "media_elevacao": self.media_elevacao,
                "episodio_atual": self.episodio_atual.tipo if self.episodio_atual else None,
                "observacao": observacao,
            }
        )

    def resumo(self) -> Dict[str, Any]:
        return {
            "tempo_atual": self.tempo_atual,
            "estado_atual": self.estado_atual,
            "temperatura_desejada": self.temperatura_desejada,
            "limite_superior": self.limite_superior,
            "tempo_espera_restante": self.tempo_espera_restante,
            "ultima_acao": self.ultima_acao,
            "media_resfriamento": self.media_resfriamento,
            "media_elevacao": self.media_elevacao,
            "leituras_registradas": len(self.temperaturas_anteriores),
            "episodios_resfriamento": len(self.taxas_resfriamento),
            "episodios_elevacao": len(self.taxas_elevacao),
        }

    def exibir_historico(self) -> None:
        for registro in self.historico:
            print(registro)

if __name__ == "__main__":
    ambiente = Ambiente(
        temperatura_atual=30.0,
        temperatura_desejada=24.0,
        sistema_ligado=False,
    )

    agente = AgenteTemperatura(
        temperatura_desejada=24.0,
        sigma=1.0,
        alpha=2.0,
        beta=1.0,
        k=1.0,
    )

    temperaturas_simuladas = [
        30.0, 29.5, 28.8, 27.9, 26.5, 25.0, 24.2,
        23.7, 23.5, 23.8, 24.1, 24.7, 25.2, 26.0
    ]

    for instante, temp in enumerate(temperaturas_simuladas, start=1):
        ambiente.temperatura_atual = temp
        acao = agente.passo(ambiente)

        print(f"Instante: {instante}")
        print(f"Temperatura atual: {temp:.2f} °C")
        print(f"Ação: {acao}")
        print(f"Estado do sistema: {agente.estado_atual}")
        print(f"Tempo de espera restante: {agente.tempo_espera_restante}")
        print(f"Média de resfriamento: {agente.media_resfriamento}")
        print(f"Média de elevação: {agente.media_elevacao}")
        print(f"Resumo: {agente.resumo()}")
        print("-" * 60)

    print("\nHISTÓRICO FINAL")
    agente.exibir_historico()