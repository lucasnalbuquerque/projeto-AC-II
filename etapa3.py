"""
Arquitetura de Computadores II - UFPB-CI-DSC
Segunda Avaliacao - Projeto Mic-1 - Etapa 3

microinstrucoes de 23 bits (ULA 8 | barramento C 9 | memoria 2 | barramento B 4), com os bits de memoria WRITE e READ.

le instrucoes da IJVM (ILOAD x, DUP, BIPUSH byte), traduz cada uma em microinstrucoes e executa na Mic-1.

Uso:
    python3 etapa3.py
    python3 etapa3.py --modo ijvm   [instrucoes] [registradores] [dados] [saida]
    python3 etapa3.py --modo tarefa1 [microinstrucoes] [registradores] [dados] [saida]
"""

import argparse
import sys

import etapa2
from etapa2 import (DECODIFICADOR_B, LARGURA, MASCARA, ORDEM_LOG, SELETOR_C, executar_instrucao, fmt, ler_palavras, ler_registradores)

# Palavras de controle da ULA (SLL8 SRA1 F0 F1 ENA ENB INVA INC)
ULA_B = "00110100" # Sd = B     (ENA=0: A fica zerado, soma passa B)
ULA_B_MAIS_1 = "00110101" # Sd = B + 1
ULA_A = "00111000" # Sd = A     (ENB=0: B fica zerado)
ULA_A_MAIS_1 = "00111001" # Sd = A + 1

BIT_DE_REGISTRADOR_B = {nome: codigo for codigo, nome in DECODIFICADOR_B.items()}
BIT_DE_REGISTRADOR_C = {nome: bit for bit, nome in SELETOR_C.items()}

SEM_MEMORIA, LEITURA, ESCRITA, ESPECIAL = "00", "01", "10", "11"

# Memoria de dados

def ler_memoria(caminho):
    """Cada linha do arquivo e uma palavra de 32 bits; o endereco e o indice da linha."""
    return [int(p, 2) for p in ler_palavras(caminho, LARGURA)]


def escrever_memoria(log, mem, anterior=None):
    for endereco, valor in enumerate(mem):
        marca = ""
        if anterior is not None and valor != anterior[endereco]:
            marca = "  <- alterada"
        log.write(f"  [{endereco}] = {fmt(valor, LARGURA)}{marca}\n")


# Execucao de uma microinstrucao de 23 bits

def endereco_valido(regs, mem):
    endereco = regs["MAR"]
    if endereco >= len(mem):
        raise ValueError(
            f"MAR = {endereco} aponta para fora da memoria de dados "
            f"(enderecos 0 a {len(mem) - 1})"
        )
    return endereco


def executar_micro(ir, regs, mem):
   # Executa uma microinstrucao. A memoria so e acessada depois da ULA e da escrita nos registradores do barramento C.
    ctrl_ula, ctrl_c, ctrl_mem, ctrl_b = ir[:8], ir[8:17], ir[17:19], ir[19:]
    write, read = int(ctrl_mem[0]), int(ctrl_mem[1])

    # Caso especial (fetch do BIPUSH): WRITE = READ = 1.
    # Os 8 primeiros bits vao para o MBR e H = MBR (preenchido com zeros), sem passar pela ULA.
    if write and read:
        byte = int(ctrl_ula, 2)
        regs["MBR"] = byte
        regs["H"] = byte
        return {"especial": True, "byte": byte, "memoria": "fetch: MBR <- byte; H <- MBR (zeros a esquerda)"}

    r = executar_instrucao(ctrl_ula + ctrl_c + ctrl_b, regs)
    r["especial"] = False
    r["memoria"] = "nenhuma"
    if write:
        endereco = endereco_valido(regs, mem)
        mem[endereco] = regs["MDR"]
        r["memoria"] = f"WRITE: dados[{endereco}] <- MDR = {fmt(regs['MDR'], LARGURA)}"
    elif read:
        endereco = endereco_valido(regs, mem)
        regs["MDR"] = mem[endereco]
        r["memoria"] = f"READ: MDR <- dados[{endereco}] = {fmt(regs['MDR'], LARGURA)}"
    return r


# Traducao IJVM -> microinstrucoes

def palavra(ula, destinos, memoria, reg_b):
    c = ["0"] * 9
    for nome in destinos:
        c[8 - BIT_DE_REGISTRADOR_C[nome]] = "1"
    return ula + "".join(c) + memoria + f"{BIT_DE_REGISTRADOR_B[reg_b]:04b}"


def traduzir(op, arg):
    # Devolve a lista de (texto da microinstrucao, palavra de 23 bits).
    # Quando ENB = 0 o barramento B nao entra na ULA; usa-se 0000 (MDR).
    if op == "ILOAD":
        micros = [("H = LV", palavra(ULA_B, ["H"], SEM_MEMORIA, "LV"))]
        micros += [("H = H+1", palavra(ULA_A_MAIS_1, ["H"], SEM_MEMORIA, "MDR"))] * arg
        micros += [
            ("MAR = H; rd", palavra(ULA_A, ["MAR"], LEITURA, "MDR")),
            ("MAR = SP = SP+1; wr", palavra(ULA_B_MAIS_1, ["SP", "MAR"], ESCRITA, "SP")),
            ("TOS = MDR", palavra(ULA_B, ["TOS"], SEM_MEMORIA, "MDR")),
        ]
        return micros
    if op == "DUP":
        return [
            ("MAR = SP = SP+1", palavra(ULA_B_MAIS_1, ["SP", "MAR"], SEM_MEMORIA, "SP")),
            ("MDR = TOS; wr", palavra(ULA_B, ["MDR"], ESCRITA, "TOS")),
        ]
    if op == "BIPUSH":
        return [
            ("SP = MAR = SP+1", palavra(ULA_B_MAIS_1, ["SP", "MAR"], SEM_MEMORIA, "SP")),
            ("fetch", f"{arg:08b}" + "0" * 9 + ESPECIAL + "0000"),
            ("MDR = TOS = H; wr", palavra(ULA_A, ["MDR", "TOS"], ESCRITA, "MDR")),
        ]
    raise ValueError(f"instrucao desconhecida: {op}")


def ler_instrucoes(caminho):
# Linhas como 'ILOAD 1', 'DUP', 'BIPUSH 00110011' (binario de 8 bits, ou decimal/0x.. entre 0 e 255).
    instrucoes = []
    with open(caminho, "r", encoding="utf-8") as f:
        for n, linha in enumerate(f, start=1):
            texto = linha.split("#")[0].strip()
            if not texto:
                continue
            partes = texto.upper().split()
            op = partes[0]
            try:
                if op == "DUP" and len(partes) == 1:
                    arg = None
                elif op == "ILOAD" and len(partes) == 2:
                    arg = int(partes[1], 0)
                    if arg < 0:
                        raise ValueError
                elif op == "BIPUSH" and len(partes) == 2:
                    t = partes[1]
                    arg = int(t, 2) if len(t) == 8 and set(t) <= {"0", "1"} else int(t, 0)
                    if not -128 <= arg <= 255:
                        raise ValueError
                    arg &= 0xFF
                else:
                    raise ValueError
            except ValueError:
                raise ValueError(f"{caminho}, linha {n}: instrucao invalida '{texto}'")
            rotulo = op if arg is None else f"{op} {arg}" if op == "ILOAD" else f"{op} {arg:08b}"
            instrucoes.append((op, arg, rotulo))
    return instrucoes


# Log

def escrever_tabela(log, ini, fim):
    log.write(f"  {'Reg':<4} {'Inicio':<46} Fim\n")
    for nome in ORDEM_LOG:
        largura = 8 if nome == "MBR" else LARGURA
        marca = "  *" if ini[nome] != fim[nome] else ""
        log.write(f"  {nome:<4} {fmt(ini[nome], largura):<46} {fmt(fim[nome], largura)}{marca}\n")


def escrever_micro(log, titulo, ir, r, ini, regs):
    log.write(f"{titulo}\n")
    log.write(f"IR = {ir}\n")
    log.write(f"  ULA = {ir[:8]}   C = {ir[8:17]}   MEM (WRITE READ) = {ir[17:19]}   B = {ir[19:]}\n")
    if r["especial"]:
        log.write("Instrucao especial (WRITE = READ = 1): nao usa a ULA nem os barramentos\n")
        log.write(f"  Byte do argumento = {r['byte']:08b} ({r['byte']})\n")
    else:
        extra = "" if ir[5] == "1" else "  (ENB = 0: nao entra na ULA)"
        log.write(f"Registrador comandando o barramento B: {r['nome_b']}{extra}\n")
        escritos = ", ".join(r["destinos"]) if r["destinos"] else "nenhum"
        log.write(f"Registradores habilitados para escrita (barramento C): {escritos}\n")
        log.write(f"  A = {fmt(r['a'], LARGURA)}   B = {fmt(r['b_valor'], LARGURA)}\n")
        log.write(f"  Sd = {fmt(r['sd'], LARGURA)}   Vai-um = {r['vai_um']}   N = {r['n']}   Z = {r['z']}\n")
    log.write(f"Memoria: {r['memoria']}\n")
    log.write("Registradores (* = alterado):\n")
    escrever_tabela(log, ini, regs)


def cabecalho(log, titulo, regs, mem):
    log.write(titulo + "\n")
    log.write("Microinstrucao de 23 bits: ULA (8) | barramento C (9) | memoria WRITE READ (2) | barramento B (4)\n")
    log.write("Valores em binario, com o inteiro em complemento de dois entre parenteses\n")
    log.write("=" * 100 + "\n")
    log.write("Memoria de dados antes da execucao:\n")
    escrever_memoria(log, mem)
    log.write("Registradores antes da execucao:\n")
    for nome in ORDEM_LOG:
        log.write(f"  {nome:<4} = {fmt(regs[nome], 8 if nome == 'MBR' else LARGURA)}\n")
    log.write("=" * 100 + "\n")


# Modos de execucao

def executar_tarefa1(micros, regs, mem, log):
    cabecalho(log, "ETAPA 3 - TAREFA 1: microinstrucoes com acesso a memoria", regs, mem)
    for n, ir in enumerate(micros, start=1):
        ini, mem_ini = dict(regs), list(mem)
        try:
            r = executar_micro(ir, regs, mem)
        except ValueError as e:
            sys.exit(f"Erro na microinstrucao {n} ({ir}): {e}")
        escrever_micro(log, f"MICROINSTRUCAO {n} de {len(micros)}", ir, r, ini, regs)
        log.write("Memoria de dados apos a microinstrucao:\n")
        escrever_memoria(log, mem, mem_ini)
        log.write("-" * 100 + "\n")
    log.write("Fim da execucao\n")


def executar_ijvm(instrucoes, regs, mem, log):
    cabecalho(log, "ETAPA 3 - ENTREGAVEL: instrucoes da IJVM traduzidas em microinstrucoes", regs, mem)
    for n, (op, arg, rotulo) in enumerate(instrucoes, start=1):
        micros = traduzir(op, arg)
        mem_ini = list(mem)
        log.write(f"INSTRUCAO {n} de {len(instrucoes)}: {rotulo}  ({len(micros)} microinstrucoes)\n")
        log.write("-" * 100 + "\n")
        for k, (texto, ir) in enumerate(micros, start=1):
            ini = dict(regs)
            try:
                r = executar_micro(ir, regs, mem)
            except ValueError as e:
                sys.exit(f"Erro na instrucao {n} ({rotulo}), microinstrucao {k} ({texto}): {e}")
            escrever_micro(log, f"Microinstrucao {n}.{k}: {texto}", ir, r, ini, regs)
            log.write("\n")
        log.write(f"Memoria de dados apos a instrucao {n} ({rotulo}):\n")
        escrever_memoria(log, mem, mem_ini)
        log.write("=" * 100 + "\n")
    log.write("Fim da execucao\n")


PADROES = {
    "ijvm": ("instrucoes.txt", "registradores_etapa3_tarefa1.txt", "dados_etapa3_tarefa1.txt", "saida_etapa3.txt"),
    "tarefa1": ("microinstrucoes_etapa3_tarefa1.txt", "registradores_etapa3_tarefa1.txt", "dados_etapa3_tarefa1.txt", "saida_etapa3_tarefa1.txt"),
}


def main():
    ap = argparse.ArgumentParser(description="Mic-1 - Etapa 3")
    ap.add_argument("--modo", choices=PADROES, default="ijvm",
                    help="ijvm (entregavel, padrao) ou tarefa1 (microinstrucoes)")
    ap.add_argument("programa", nargs="?")
    ap.add_argument("registradores", nargs="?")
    ap.add_argument("dados", nargs="?")
    ap.add_argument("saida", nargs="?")
    args = ap.parse_args()

    programa, registradores, dados, saida = (dado or padrao for dado, padrao in zip((args.programa, args.registradores, args.dados, args.saida), PADROES[args.modo]))

    try:
        regs = ler_registradores(registradores)
        mem = ler_memoria(dados)
        if args.modo == "tarefa1":
            micros = ler_palavras(programa, 23)
            with open(saida, "w", encoding="utf-8") as log:
                executar_tarefa1(micros, regs, mem, log)
        else:
            instrucoes = ler_instrucoes(programa)
            with open(saida, "w", encoding="utf-8") as log:
                executar_ijvm(instrucoes, regs, mem, log)
    except (OSError, ValueError) as e:
        sys.exit(f"Erro: {e}")

    print(f"Execucao concluida. Log em '{saida}'.")


if __name__ == "__main__":
    main()
