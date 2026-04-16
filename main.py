import time
from agenteTemperatura import AgenteTemperatura

if __name__ == "__main__":
    agente = AgenteTemperatura(temperatura_atual=29, temperatura_desejada=25, margem=1, alfa=3, beta=0.5)

    temperaturas_simuladas = [25.0, 25.5, 26.0, 26.1, 26.5, 25.8, 24.5, 24.0, 23.8, 24.2, 25.0]

    print("Iniciando simulação...\n")
    print(f"Temperatura desejada: {agente.temperatura_desejada}°C")
    print(f"Margem de tolerância: ±{agente.margem}°C\n")

    for temp in temperaturas_simuladas:
        acao = agente.agir(temp)
        print(f"Ambiente: {temp}°C -> Ação: {acao.upper():<8} | Estado: {agente.estado_sistema.upper()}")
        time.sleep(1)

    print("\nTaxas de resfriamento:", agente.taxas_resfriamento)
    print("Média taxa de resfriamento:", agente.media_taxa_resfriamento)
    print("Taxas de elevação:", agente.taxas_elevacao)
    print("Média taxa de elevação:", agente.media_taxa_elevacao)

    custo = agente.custo_situacao()
    print(f"Custo atual: {custo:.2f}")

    print(f"Sigma atual: {agente.sigma:.2f}")
    print(f"Limite superior calculado: {agente.calculo_limite_superior():.2f}")