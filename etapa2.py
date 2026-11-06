"""
Arquitetura de Computadores II

Grupo: Lucas Nóbrega Albuquerque e Luiz Manoel Barbosa Ramalho

Segunda Avaliacao - Etapa 1

Tarefa 1: ULA de 32 bits com deslocador (SLL8, SRA1) e saidas N e Z. A ULA eh construida encadeando 32 ULAs de 1 bit (ula.py, Etapa 1), ligando o vai-um de cada bit ao vem-um do bit seguinte.
Tarefa 2: registradores da Mic-1, decodificador do barramento B (4 bits) e seletor do barramento C (9 bits).

Uso:
    python3 etapa2.py tarefa1 programa.txt saida.txt [--A 5] [--B 3]
    python3 etapa2.py tarefa2 programa.txt registradores.txt saida.txt
"""

import argparse
import sys

from ula import ula as ula_1bit

LARGURA = 32
MASCARA = (1 << LARGURA) - 1
BIT_SINAL = 1 << (LARGURA - 1)

# convencao do decodificador de 4 bits (barramento B): codigo -> registrador
DECODIFICADOR_B = {0: "MDR", 1: "PC", 2: "MBR", 3: "MBRU", 4: "SP", 5: "LV", 6: "CPP", 7: "TOS", 8: "OPC",}

# Convencao do seletor de 9 bits (barramento C): bit -> registrador
SELETOR_C = {8: "H", 7: "OPC", 6: "TOS", 5: "CPP", 4: "LV", 3: "SP", 2: "PC", 1: "MDR", 0: "MAR",}

# Ordem em que os registradores aparecem no log
ORDEM_LOG = ["H", "OPC", "TOS", "CPP", "LV", "SP", "MBR", "PC", "MDR", "MAR"]

# Utilidades

def com_sinal(valor, largura):
    # interpreta 'valor' como inteiro em complemento de dois.
    return valor - (1 << largura) if valor >> (largura - 1) else valor


def fmt(valor, largura):
    return f"{valor:0{largura}b} ({com_sinal(valor, largura)})"


def ler_palavras(caminho, tamanho):
    # le um arquivo com uma palavra binaria de 'tamanho' bits por linha.
    palavras = []
    with open(caminho, "r", encoding="utf-8") as f:
        for n, linha in enumerate(f, start=1):
            palavra = linha.strip()
            if not palavra:
                continue
            if len(palavra) != tamanho or any(c not in "01" for c in palavra):
                raise ValueError(
                    f"{caminho}, linha {n}: '{palavra}' nao e uma palavra "
                    f"valida de {tamanho} bits"
                )
            palavras.append(palavra)
    return palavras

# Tarefa 1: ULA de 32 bits + deslocador

def ula_32bits(a, b, f0, f1, ena, enb, inva, inc):
    # encadeia 32 ULAs de 1 bit. INC e o vem-um do bit menos significativo.
    s = 0
    vem_um = inc
    for i in range(LARGURA):
        bit_s, vem_um = ula_1bit((a >> i) & 1, (b >> i) & 1, f0, f1, ena, enb, inva, vem_um)
        s |= bit_s << i
    return s, vem_um  # vem_um aqui e o vai-um do bit mais significativo


def deslocador(s, sll8, sra1):
    # opera sobre a saida da ULA, depois que ela foi calculada.
    if sll8 and sra1:
        raise ValueError("SLL8 e SRA1 nao podem estar ativos ao mesmo tempo")
    if sll8:
        return (s << 8) & MASCARA
    if sra1:
        return (s >> 1) | (s & BIT_SINAL)  # preserva o bit de sinal
    return s


def ula_etapa2(palavra8, a, b):
    # executa uma palavra de controle de 8 bits.

    # ordem dos bits: SLL8 SRA1 F0 F1 ENA ENB INVA INC.
    # retorna (Sd, vai_um, N, Z).

    sll8, sra1, f0, f1, ena, enb, inva, inc = (int(c) for c in palavra8)
    s, vai_um = ula_32bits(a, b, f0, f1, ena, enb, inva, inc)
    sd = deslocador(s, sll8, sra1)
    n = sd >> (LARGURA - 1)
    z = 1 if sd == 0 else 0
    return sd, vai_um, n, z


def executar_tarefa1(palavras, a, b, log):
    log.write("ETAPA 2 - TAREFA 1: ULA de 32 bits com deslocador\n")
    log.write(f"A = {fmt(a, LARGURA)}\n")
    log.write(f"B = {fmt(b, LARGURA)}\n")
    log.write("Palavra de controle: SLL8 SRA1 F0 F1 ENA ENB INVA INC\n")
    log.write("=" * 78 + "\n")

    pc = 0
    ir = ""
    for ir in palavras:
        pc += 1
        sd, vai_um, n, z = ula_etapa2(ir, a, b)
        log.write(f"IR = {ir}\n")
        log.write(f"PC = {pc}\n")
        log.write(f"A  = {fmt(a, LARGURA)}\n")
        log.write(f"B  = {fmt(b, LARGURA)}\n")
        log.write(f"Sd = {fmt(sd, LARGURA)}\n")
        log.write(f"Vai-um = {vai_um}\n")
        log.write(f"N = {n}\n")
        log.write(f"Z = {z}\n")
        log.write("-" * 78 + "\n")
    log.write("Fim da execucao\n")


# Tarefa 2: registradores, decodificador e seletor

def ler_registradores(caminho):
    # le o estado inicial. Formato: uma linha 'NOME = bits' por registrador.
    regs = {}
    with open(caminho, "r", encoding="utf-8") as f:
        for n, linha in enumerate(f, start=1):
            linha = linha.split("#")[0].strip()
            if not linha:
                continue
            nome, _, valor = linha.replace(":", "=").partition("=")
            nome, valor = nome.strip().upper(), valor.strip()
            if nome not in ORDEM_LOG:
                raise ValueError(f"{caminho}, linha {n}: registrador '{nome}' desconhecido")
            largura = 8 if nome == "MBR" else LARGURA
            if not valor or len(valor) > largura or any(c not in "01" for c in valor):
                raise ValueError(
                    f"{caminho}, linha {n}: valor de {nome} deve ser binario "
                    f"com ate {largura} bits"
                )
            regs[nome] = int(valor, 2)
    faltando = [r for r in ORDEM_LOG if r not in regs]
    if faltando:
        raise ValueError(f"{caminho}: faltam os registradores {', '.join(faltando)}")
    return regs


def decodificador_b(codigo):
    # decodificador de 4 bits: habilita um de 9 registradores no barramento B.
    if codigo not in DECODIFICADOR_B:
        raise ValueError(f"codigo {codigo:04b} nao habilita nenhum registrador no barramento B")
    return DECODIFICADOR_B[codigo]


def seletor_c(bits9):
    # seletor de 9 bits: devolve os registradores habilitados para escrita.
    return [SELETOR_C[bit] for bit in range(8, -1, -1) if bits9[8 - bit] == "1"]


def valor_barramento_b(nome, regs):
    # valor colocado no barramento B (MBR estende o sinal, MBRU preenche com zeros).
    if nome == "MBR":
        mbr = regs["MBR"]
        return mbr | 0xFFFFFF00 if mbr & 0x80 else mbr
    if nome == "MBRU":
        return regs["MBR"]
    return regs[nome]


def executar_instrucao(ir, regs):
    # executa uma instrucao de 21 bits: ULA (8) | barramento C (9) | barramento B (4).
    ctrl_ula, ctrl_c, ctrl_b = ir[:8], ir[8:17], ir[17:]
    nome_b = decodificador_b(int(ctrl_b, 2))
    destinos = seletor_c(ctrl_c)

    a = regs["H"]
    b = valor_barramento_b(nome_b, regs)
    sd, vai_um, n, z = ula_etapa2(ctrl_ula, a, b)

    # a escrita ocorre so depois de a ULA operar com os valores atuais
    for nome in destinos:
        regs[nome] = sd

    return {
        "ula": ctrl_ula, "c": ctrl_c, "b": ctrl_b,
        "nome_b": nome_b, "destinos": destinos,
        "a": a, "b_valor": b, "sd": sd, "vai_um": vai_um, "n": n, "z": z,
    }


def escrever_registradores(log, regs, anteriores=None):
    for nome in ORDEM_LOG:
        largura = 8 if nome == "MBR" else LARGURA
        marca = ""
        if anteriores is not None and regs[nome] != anteriores[nome]:
            marca = "  <- alterado"
        log.write(f"  {nome:<3} = {fmt(regs[nome], largura)}{marca}\n")


def executar_tarefa2(instrucoes, regs, log):
    log.write("ETAPA 2 - TAREFA 2: registradores, barramento B e barramento C\n")
    log.write("Instrucao de 21 bits: ULA (8) | barramento C (9) | barramento B (4)\n")
    log.write("Valores em binario, com o inteiro em complemento de dois entre parenteses\n")
    log.write("=" * 78 + "\n")
    log.write("Estado inicial dos registradores:\n")
    escrever_registradores(log, regs)
    log.write("=" * 78 + "\n")

    for numero, ir in enumerate(instrucoes, start=1):
        inicio = dict(regs)
        try:
            r = executar_instrucao(ir, regs)
        except ValueError as e:
            sys.exit(f"Erro na instrucao {numero} ({ir}): {e}")

        log.write(f"INSTRUCAO {numero} de {len(instrucoes)}\n")
        log.write(f"IR = {ir}\n")
        log.write(f"ULA (SLL8 SRA1 F0 F1 ENA ENB INVA INC) = {r['ula']}\n")
        log.write(f"Barramento C (H OPC TOS CPP LV SP PC MDR MAR) = {r['c']}\n")
        log.write(f"Barramento B = {r['b']}\n")
        log.write(f"Registrador comandando o barramento B: {r['nome_b']}\n")
        escritos = ", ".join(r["destinos"]) if r["destinos"] else "nenhum"
        log.write(f"Registradores habilitados para escrita (barramento C): {escritos}\n")
        log.write("Registradores no inicio da instrucao:\n")
        escrever_registradores(log, inicio)
        log.write("ULA:\n")
        log.write(f"A(H) = {fmt(r['a'], LARGURA)}\n")
        log.write(f"B({r['nome_b']:<4}) = {fmt(r['b_valor'], LARGURA)}\n")
        log.write(f"Sd = {fmt(r['sd'], LARGURA)}\n")
        log.write(f"Vai-um = {r['vai_um']}   N = {r['n']}   Z = {r['z']}\n")
        log.write("Registradores no fim da instrucao:\n")
        escrever_registradores(log, regs, inicio)
        log.write("-" * 78 + "\n")

    log.write("Fim da execucao\n")


# Linha de comando

def inteiro_32(texto):
    # aceita decimal, 0x..., 0b... e negativos; devolve valor de 32 bits.
    return int(texto, 0) & MASCARA


def main():
    ap = argparse.ArgumentParser(description="Mic-1 - Etapa 2")
    sub = ap.add_subparsers(dest="tarefa", required=True)

    t1 = sub.add_parser("tarefa1", help="ULA de 32 bits com deslocador")
    t1.add_argument("programa", help="palavras de 8 bits, uma por linha")
    t1.add_argument("saida", help="arquivo de log")
    t1.add_argument("--A", type=inteiro_32, default=1, help="valor de A (padrao 1)")
    t1.add_argument("--B", type=inteiro_32, default=1, help="valor de B (padrao 1)")

    t2 = sub.add_parser("tarefa2", help="registradores e barramentos")
    t2.add_argument("programa", help="instrucoes de 21 bits, uma por linha")
    t2.add_argument("registradores", help="estado inicial dos registradores")
    t2.add_argument("saida", help="arquivo de log")

    args = ap.parse_args()

    try:
        if args.tarefa == "tarefa1":
            palavras = ler_palavras(args.programa, 8)
            with open(args.saida, "w", encoding="utf-8") as log:
                executar_tarefa1(palavras, args.A, args.B, log)
        else:
            instrucoes = ler_palavras(args.programa, 21)
            regs = ler_registradores(args.registradores)
            with open(args.saida, "w", encoding="utf-8") as log:
                executar_tarefa2(instrucoes, regs, log)
    except (OSError, ValueError) as e:
        sys.exit(f"Erro: {e}")

    print(f"Execucao concluida. Log em '{args.saida}'.")


if __name__ == "__main__":
    main()
