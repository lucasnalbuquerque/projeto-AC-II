#!/usr/bin/env python3
"""
Arquitetura de Computadores II

Grupo: Lucas Nóbrega Albuquerque e Luiz Manoel Barbosa Ramalho

Segunda Avaliacao - Etapa 1

Cada linha do arquivo de programa contem uma palavra de 6 bits:

F0 F1 ENA ENB INVA INC
X0 X1 X2  X3  X4   X5

Uso:
    python3 ula.py [programa.txt] [saida.txt] [--A 1] [--B 1]
"""

import argparse
import sys

# portas logicas

def AND(x, y):
    return x & y


def OR(x, y):
    return x | y


def XOR(x, y):
    return x ^ y


def NOT(x):
    return 1 - x


# ULA de 1 bit

def ula(a, b, f0, f1, ena, enb, inva, inc):
    """retorna (S, vai_um) para as entradas.

    - entrada A: passa por AND com ENA e depois XOR com INVA.
    - entrada B: passa por AND com ENB.
    - decodificador (F0, F1) habilita uma das linhas da unidade logica ou o somador completo:
        00 -> A AND B
        01 -> A OR B
        10 -> NOT B
        11 -> A + B (somador completo)
    - o sinal INC e o 'vem-um' do somador completo.
    - a saida S e o OR das quatro linhas (apenas uma ta habilitada).
    """
    # condicionamento das entradas
    a_ = XOR(AND(a, ena), inva)
    b_ = AND(b, enb)

    # decodificador 2x4
    en_and = AND(NOT(f0), NOT(f1))
    en_or = AND(NOT(f0), f1)
    en_notb = AND(f0, NOT(f1))
    en_soma = AND(f0, f1)

    # unidade logica
    s_and = AND(en_and, AND(a_, b_))
    s_or = AND(en_or, OR(a_, b_))
    s_notb = AND(en_notb, NOT(b_))

    # somador completo
    vem_um = inc
    soma = XOR(XOR(a_, b_), vem_um)
    vai_um = OR(AND(a_, b_), AND(vem_um, XOR(a_, b_)))
    s_soma = AND(en_soma, soma)

    # saida: OR das linhas
    s = OR(OR(s_and, s_or), OR(s_notb, s_soma))
    return s, vai_um

# leitura e execucao do programa

def ler_programa(caminho):
    instrucoes = []
    with open(caminho, "r", encoding="utf-8") as f:
        for n, linha in enumerate(f, start=1):
            palavra = linha.strip()
            if not palavra:
                continue
            if len(palavra) != 6 or any(c not in "01" for c in palavra):
                raise ValueError(f"Linha {n}: '{palavra}' nao eh uma palavra valida de 6 bits")
            instrucoes.append(palavra)
    return instrucoes


def executar(instrucoes, a, b, log):
    pc = 0  # contador de programa: linha em execucao (comeca em 1 ao executar)
    ir = ""  # registrador de instrucao

    log.write(f"A = {a}, B = {b}\n")
    log.write("Inicio\n")
    log.write("=" * 60 + "\n")

    while pc < len(instrucoes):
        ir = instrucoes[pc]  # busca
        pc += 1  # PC = numero da linha em execucao

        f0, f1, ena, enb, inva, inc = (int(c) for c in ir)
        s, vai_um = ula(a, b, f0, f1, ena, enb, inva, inc)

        log.write(f"IR = {ir}\n")
        log.write(f"PC = {pc}\n")
        log.write(f"A = {a}\n")
        log.write(f"B = {b}\n")
        log.write(f"S = {s}\n")
        log.write(f"Vai-um = {vai_um}\n")
        log.write("-" * 60 + "\n")

    log.write("Fim\n")


def main():
    ap = argparse.ArgumentParser(description="ULA de 1 bit da Mic-1 (Etapa 1)")
    ap.add_argument("programa", nargs="?", default="programa_etapa1.txt")
    ap.add_argument("saida", nargs="?", default="saida_etapa1.txt")
    ap.add_argument("--A", type=int, choices=(0, 1), default=1, help="valor de A")
    ap.add_argument("--B", type=int, choices=(0, 1), default=1, help="valor de B")
    args = ap.parse_args()

    try:
        instrucoes = ler_programa(args.programa)
    except (OSError, ValueError) as e:
        sys.exit(f"Erro: {e}")

    with open(args.saida, "w", encoding="utf-8") as log:
        executar(instrucoes, args.A, args.B, log)

    print(f"{len(instrucoes)} instrucoes executadas. Log em '{args.saida}'.")


if __name__ == "__main__":
    main()