import logging
from pymongo import MongoClient

# Conectar ao MongoDB (localhost na porta padrão 27017)
client = MongoClient("mongodb://localhost:27017/")
db = client['EcoJourneyDB']
colecao = db['EcoJourney']

print('Olá, seja bem-vindo(a) à EcoJourney!')

# Configuração de log
logging.basicConfig(filename='eco_journey.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Estruturas de Dados
missao_diaria = ["Economize 10 litros de água", "Use bicicleta por 30 minutos", "Recicle 5 objetos"]
missao_mensal = ["Utilizar energia solar", "Utilizar transporte elétrico 15 dias do mês", "Ajudar uma ONG de energia sustentavel"]

recompensas = [
    {"nome": "Chaveiro de folha (impressora 3D)", "custo": 400},
    {"nome": "Camiseta da EcoJourney", "custo": 800},
    {"nome": "Ecobag", "custo": 1200}
]

nivel_pontuacao = [0, 150, 300, 800, 1500]

# Ranking fictício com top 5 usuários (nome e pontos)
ranking = [
    {"nome": "GreenWarrior", "pontos": 1000},
    {"nome": "EcoChampion", "pontos": 950},
    {"nome": "Sustentável", "pontos": 900},
    {"nome": "NatureLover", "pontos": 850},
    {"nome": "PlanetaAmigo", "pontos": 800},
]

def cadastro_usuario():
    logging.info("Solicitando cadastro de usuário.")
    user = input("Digite um nome de usuário: ")
    senha = input("Digite uma senha: ")
    pontos = 10  # Bônus de 10 pontos ao criar a conta
    if salvar_usuario(user, senha, pontos):
        print(f"Bem-vindo(a), {user}! Você recebeu 10 pontos de boas-vindas. Pontuação inicial: {pontos}")
        return user, senha, pontos
    return None, None, None

def login_usuario():
    while True:
        try:
            user = input("Insira seu usuário: ")
            senha = input("Insira sua senha: ")
            usuario = colecao.find_one({"usuario": user, "senha": senha})
            if usuario:
                logging.info(f"Usuário {user} logado com sucesso.")
                return user, usuario['pontos']
            else:
                raise ValueError("Usuário ou senha incorretos. Tente novamente.")
        except ValueError as erro:
            print(erro)
            logging.warning("Tentativa de login falhou.")

def calcular_nivel(pontos):
    for i, limite in enumerate(nivel_pontuacao):
        if pontos < limite:
            return i, limite - pontos
    return len(nivel_pontuacao), 0

def salvar_usuario(user, senha, pontos):
    if colecao.find_one({"usuario": user}):
        print("Usuário já cadastrado. Faça login.")
        logging.info(f"Usuário {user} já existe no banco de dados.")
        return False
    nivel, _ = calcular_nivel(pontos)
    colecao.insert_one({
        "usuario": user,
        "senha": senha,
        "pontos": pontos,
        "nivel": nivel,
        "missoes_completas": [],
        "recompensas_resgatadas": [],
        "posicao_ranking": None  # Atualizado ao exibir ranking
    })
    logging.info(f"Usuário {user} salvo no banco de dados com nível {nivel}.")
    return True

def atualizar_usuario(user, pontos, missao=None, recompensa=None):
    usuario = colecao.find_one({"usuario": user})
    if usuario:
        nivel, _ = calcular_nivel(pontos)
        update_data = {"$set": {"pontos": pontos, "nivel": nivel}}
        if missao:
            update_data["$push"] = {"missoes_completas": missao}
        if recompensa:
            update_data.setdefault("$push", {})["recompensas_resgatadas"] = recompensa
        colecao.update_one({"usuario": user}, update_data)
        logging.info(f"Usuário {user} atualizado: pontos={pontos}, nível={nivel}.")
    else:
        logging.warning(f"Tentativa de atualizar usuário {user} que não existe no banco.")

def exibir_loja(pontos, user):
    print("\n--- Loja de Recompensas ---")
    for i, recompensa in enumerate(recompensas, start=1):
        print(f"{i}. {recompensa['nome']} - {recompensa['custo']} pontos")
    
    escolha = input("Digite o número da recompensa que deseja resgatar ou pressione Enter para voltar: ")
    if escolha.isdigit():
        escolha = int(escolha) - 1
        if 0 <= escolha < len(recompensas):
            recompensa = recompensas[escolha]
            if pontos >= recompensa['custo']:
                pontos -= recompensa['custo']
                print(f"Parabéns! Você resgatou: {recompensa['nome']}. Pontos restantes: {pontos}")
                atualizar_usuario(user, pontos, recompensa=recompensa['nome'])
            else:
                print("Pontos insuficientes para resgatar esta recompensa.")
        else:
            print("Opção inválida.")
    return pontos

def exibir_nivel(pontos):
    nivel, falta = calcular_nivel(pontos)
    print(f"\nSeu nível atual: {nivel}")
    if nivel < len(nivel_pontuacao):
        print(f"Pontos para o próximo nível ({nivel + 1}): {falta}")
    else:
        print("Você já está no nível máximo!")
    logging.info(f"Exibido nível {nivel} para o usuário com {pontos} pontos.")

def chave_ordenacao(usuario):
    """Função para retornar a chave de ordenação (pontos)"""
    return usuario["pontos"]

def exibir_ranking(pontos, user):
    print("\n--- Ranking de Referência ---")
    
    # Exibir os 5 usuários do ranking de referência
    for i, usuario in enumerate(ranking, start=1):
        print(f"{i}. {usuario['nome']} - {usuario['pontos']} pontos")
    
    # Recuperar todos os usuários do banco de dados ordenados por pontos em ordem decrescente
    usuarios_banco = list(colecao.find().sort("pontos", -1))
    
    # Combinar os rankings (referência + banco)
    ranking_total = ranking + [{"nome": u["usuario"], "pontos": u["pontos"]} for u in usuarios_banco]
    
    # Remover duplicatas (priorizando os do ranking de referência) e ordenar por pontos
    usuarios_unicos = {}
    for usuario in ranking_total:
        if usuario["nome"] not in usuarios_unicos:
            usuarios_unicos[usuario["nome"]] = usuario
    
    ranking_ordenado = sorted(usuarios_unicos.values(), key=chave_ordenacao, reverse=True)
    
    # Calcular a posição do usuário logado
    posicao = next((i + 1 for i, u in enumerate(ranking_ordenado) if u['nome'] == user), len(ranking_ordenado) + 1)
    
    # Atualizar a posição no banco de dados
    colecao.update_one({"usuario": user}, {"$set": {"posicao_ranking": posicao}})
    
    print(f"\nSua pontuação atual: {pontos} pontos.")
    print(f"Você está na posição {posicao} do ranking.\n")
    logging.info(f"Usuário {user} está na posição {posicao} do ranking com {pontos} pontos.")



def missao_pontos(user, pontos):
    nivel, _ = calcular_nivel(pontos)
    missoes_diarias = missao_diaria[:min(3 + max(0, nivel - 3), len(missao_diaria))]
    missoes_mensais = missao_mensal[:min(3 + max(0, nivel - 3), len(missao_mensal))]

    print("\nMissões Diárias:")
    for i, missao in enumerate(missoes_diarias, start=1):
        print(f"{i}. {missao}")
    
    print("\nMissões Mensais:")
    for i, missao in enumerate(missoes_mensais, start=1):
        print(f"{i + len(missoes_diarias)}. {missao}")

    try:
        escolha = int(input("Escolha uma missão para completar: "))
        if 1 <= escolha <= len(missoes_diarias):
            pontos += 10
            missao = missoes_diarias[escolha - 1]
        elif len(missoes_diarias) < escolha <= len(missoes_diarias) + len(missoes_mensais):
            pontos += 50
            missao = missoes_mensais[escolha - len(missoes_diarias) - 1]
        else:
            print("Escolha inválida.")
            return pontos
        print(f"Parabéns! Você completou a missão '{missao}' e agora tem {pontos} pontos.")
        atualizar_usuario(user, pontos, missao=missao)
        return pontos
    except ValueError:
        logging.error("Erro: entrada inválida para seleção de missão.")
        print("Entrada inválida. Escolha um número válido.")
        return pontos

def main():
    user, senha, pontos = cadastro_usuario()
    if user is None:
        user, pontos = login_usuario()
    while True:
        print("\n1. Completar Missão\n2. Exibir Loja de Recompensas\n3. Ver Nível\n4. Exibir Ranking\n5. Sair")
        escolha = input("Escolha uma opção: ")
        if escolha == "1":
            pontos = missao_pontos(user, pontos)
        elif escolha == "2":
            pontos = exibir_loja(pontos, user)
        elif escolha == "3":
            exibir_nivel(pontos)
        elif escolha == "4":
            exibir_ranking(pontos, user)
        elif escolha == "5":
            print("Até logo!")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
